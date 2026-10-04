from dataclasses import dataclass, field

import math
import bpy
import bmesh
import gpu
from gpu_extras.presets import draw_circle_2d
from bpy_extras import view3d_utils
from mathutils import Vector
from bpy.props import (CollectionProperty,FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty,)
from bpy.types import ( Operator, PropertyGroup,)
from gpu_extras.batch import batch_for_shader

# Retopology mesh helper
def get_retopo_mesh(context):
    mesh = context.scene.retopo.mesh
    if mesh is None or mesh.type != "MESH":
        return None
    return mesh

@dataclass
class RetopoGuideSpline:
    points: list[Vector] = field(default_factory=list)


@dataclass
class RetopoGuide:
    source: str = "ADD_STROKE"
    splines: list[RetopoGuideSpline] = field(default_factory=list)


class RetopoGuidePoint(PropertyGroup):
    co: FloatVectorProperty(size=3, subtype='XYZ')


class RetopoGuideSplineState(PropertyGroup):
    points: CollectionProperty(type=RetopoGuidePoint)


def store_strip_state(settings, points):
    settings.strip_points.clear()
    for point in points:
        point_state = settings.strip_points.add()
        point_state.co = (point.x, point.y, 0.0)


def load_strip_state(settings):
    return [
        Vector((point_state.co.x, point_state.co.y))
        for point_state in settings.strip_points
    ]

def store_guide_state(settings, guide):
    settings.guide_source = guide.source if guide else ""
    settings.guide_splines.clear()
    if guide is None:
        return
    for spline in guide.splines:
        state = settings.guide_splines.add()
        for point in spline.points:
            point_state = state.points.add()
            point_state.co = tuple(point)


def load_guide_state(settings):
    if not settings.guide_splines:
        return None
    guide = RetopoGuide(source=settings.guide_source or "ADD_STROKE")
    for spline_state in settings.guide_splines:
        points = [Vector(point_state.co) for point_state in spline_state.points]
        if len(points) >= 2:
            guide.splines.append( RetopoGuideSpline(points=points))
    return guide if guide.splines else None


def is_retopo_edit_context(context):
    """Return True when the registered retopo mesh is currently in Edit Mode."""
    mesh = get_retopo_mesh(context)
    return mesh is not None and mesh.type == 'MESH' and mesh.mode == 'EDIT'


# Retopo tool exit
def _retopo_switch_to_tweak(context):
    """Switch the 3D View back to Blender's default Tweak tool."""
    try:
        bpy.ops.wm.tool_set_by_id( name="builtin.select", space_type="VIEW_3D",)
    except RuntimeError:
        pass


def _retopo_is_view_navigation_event(event):
    """Return True when Blender's native View3D navigation should handle the event."""
    return ( event.type == "MIDDLEMOUSE" or ( event.type == "LEFTMOUSE" and event.alt))


def _retopo_draw_2d_lines(positions, color, width=2.0):
    """Draw 2D line segments using the standard retopo viewport style."""
    if not positions:
        return

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": positions})

    gpu.state.blend_set("ALPHA")

    try:
        gpu.state.line_width_set(width)
    except Exception:
        pass

    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)

    try:
        gpu.state.line_width_set(1.0)
    except Exception:
        pass

    gpu.state.blend_set("NONE")


# Guide analysis
@dataclass
class GuideSplineAnalysis:
    points: list[Vector] = field(default_factory=list)
    cumulative_lengths: list[float] = field(default_factory=list)
    length: float = 0.0


@dataclass
class GuideAnalysis:
    splines: list[GuideSplineAnalysis] = field(default_factory=list)

@dataclass
class SurfaceGenerationSettings:
    along_count: int


@dataclass
class SurfacePatch:
    vertices: list[Vector]
    faces: list[tuple[int, ...]]


EPSILON = 1e-6


def _clean_guide_points(points):
    """Remove consecutive duplicate points and duplicate closed endpoints."""
    cleaned = []
    for point in points:
        point = Vector(point)
        if not cleaned or (point - cleaned[-1]).length > EPSILON:
            cleaned.append(point)

    if len(cleaned) > 1 and (cleaned[0] - cleaned[-1]).length <= EPSILON:
        cleaned.pop()

    return cleaned


def analyze_guide(guide):
    """Convert raw guide splines into arc-length-aware solver data."""
    analysis = GuideAnalysis()
    if guide is None:
        return analysis

    for spline in guide.splines:
        points = _clean_guide_points(spline.points)
        if len(points) < 2:
            continue

        cumulative = [0.0]
        for index in range(1, len(points)):
            cumulative.append( cumulative[-1] + (points[index] - points[index - 1]).length)

        total_length = cumulative[-1]
        if total_length <= EPSILON:
            continue

        analysis.splines.append(
            GuideSplineAnalysis( points=points, cumulative_lengths=cumulative, length=total_length,)
        )

    return analysis


def sample_guide_spline(spline, count):
    """Uniformly sample one open guide spline by arc length."""
    count = max(2, int(count))
    points = spline.points
    cumulative = spline.cumulative_lengths

    samples = []
    for sample_index in range(count):
        distance = spline.length * sample_index / (count - 1)
        segment_index = 0

        while segment_index < len(points) - 2 and distance > cumulative[segment_index + 1]:
            segment_index += 1

        start = points[segment_index]
        end = points[segment_index + 1]
        start_distance = cumulative[segment_index]
        end_distance = cumulative[segment_index + 1]
        span = end_distance - start_distance
        factor = 0.0 if span <= EPSILON else (distance - start_distance) / span
        samples.append(start.lerp(end, factor))

    return samples


def interpolate_rows(row_a, row_b, factor):
    return [a.lerp(b, factor) for a, b in zip(row_a, row_b)]


def build_surface_patch(rows):
    """Convert a regular guide grid directly into quad topology."""
    if not rows or not rows[0]:
        return SurfacePatch(vertices=[], faces=[])

    column_count = len(rows[0])
    row_count = len(rows)
    if any(len(row) != column_count for row in rows):
        return SurfacePatch(vertices=[], faces=[])

    vertices = [Vector(point) for row in rows for point in row]
    faces = []

    for row_index in range(row_count - 1):
        next_row = row_index + 1
        for column_index in range(column_count - 1):
            next_column = column_index + 1

            a = row_index * column_count + column_index
            b = row_index * column_count + next_column
            c = next_row * column_count + next_column
            d = next_row * column_count + column_index
            faces.append((a, b, c, d))

    return SurfacePatch(vertices=vertices, faces=faces)


def generate_surface(guide_analysis, settings):
    """Generate a regular quad grid where each guide stroke becomes one main row."""
    if len(guide_analysis.splines) < 2:
        return None

    # Along is the number of internal cuts, not the number of segments.
    # Every stroke needs the two end samples plus the requested internal cuts.
    along_cuts = max(0, int(settings.along_count))
    sample_count = along_cuts + 2

    rows = [
        sample_guide_spline(spline, sample_count)
        for spline in guide_analysis.splines
    ]

    patch = build_surface_patch(rows)
    return patch if patch.faces else None


def commit_surface(context, main_object, patch):
    """Commit a generated patch and orient it toward the current viewport."""
    if not patch.vertices or not patch.faces:
        return False

    bm = bmesh.from_edit_mesh(main_object.data)
    world_to_local = main_object.matrix_world.inverted()

    new_vertices = [ bm.verts.new(world_to_local @ coordinate)
        for coordinate in patch.vertices
    ]

    for vertex in new_vertices:
        vertex.select = True

    new_faces = []
    for face_indices in patch.faces:
        try:
            new_faces.append( bm.faces.new([new_vertices[index] for index in face_indices]))
        except ValueError:
            continue

    if not new_faces:
        return False

    # Establish a consistent face-normal field first.
    bmesh.ops.recalc_face_normals(bm, faces=new_faces)
    bm.normal_update()

    # The guide winding depends on the direction the user drew the strokes.
    # For a retopo surface created from screen-space guides, orient the
    # new patch toward the current viewport so the visible side is front-facing.
    view_3d = context.space_data
    rv3d = getattr(view_3d, "region_3d", None) if view_3d else None
    if rv3d is not None:
        normal_matrix = main_object.matrix_world.to_3x3().inverted().transposed()
        average_normal = Vector((0.0, 0.0, 0.0))
        for face in new_faces:
            average_normal += normal_matrix @ face.normal

        if average_normal.length > EPSILON:
            average_normal.normalize()
            view_direction = ( rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))).normalized()

            # Positive dot means the face normal points into the scene,
            # i.e. away from the user. Flip the patch in that case.
            if average_normal.dot(view_direction) > 0.0:
                bmesh.ops.reverse_faces(bm, faces=new_faces)

    bm.normal_update()
    bm.verts.ensure_lookup_table()
    new_vertex_indices = [vertex.index for vertex in new_vertices]
    bmesh.update_edit_mesh( main_object.data, loop_triangles=True, destructive=True,)
    return True, new_vertex_indices


def _add_stroke_bridge_reference_edges(context, mesh, reference_edge_indices, new_vertex_indices, patch):
    """Bridge the generated strip to the originally selected boundary edge loop."""
    if not reference_edge_indices:
        return True

    bm = bmesh.from_edit_mesh(mesh.data)
    bm.edges.ensure_lookup_table()

    reference_edges = []
    for edge_index in reference_edge_indices:
        if edge_index < 0 or edge_index >= len(bm.edges):
            return False
        edge = bm.edges[edge_index]
        if not edge.is_valid:
            return False
        reference_edges.append(edge)

    # The generated strip has two long boundary rows. Each row contains
    # exactly the number of edges represented by the selected reference.
    boundary_edge_count = len(reference_edges)
    expected_columns = boundary_edge_count + 1

    if expected_columns < 2 or len(new_vertex_indices) < expected_columns * 2:
        return False

    # Reacquire the current BMesh vertices by index. commit_surface already
    # called update_edit_mesh(), so the old BMVert references are invalid.
    bm.verts.ensure_lookup_table()

    unique_vertex_rows = max(2, len(new_vertex_indices) // expected_columns)
    if unique_vertex_rows * expected_columns != len(new_vertex_indices):
        return False

    candidate_edges = []
    for row_index in (0, unique_vertex_rows - 1):
        start = row_index * expected_columns
        row_edges = []
        for column_index in range(expected_columns - 1):
            v0 = bm.verts[new_vertex_indices[start + column_index]]
            v1 = bm.verts[new_vertex_indices[start + column_index + 1]]
            edge = next((
                linked_edge
                for linked_edge in v0.link_edges
                if linked_edge.is_valid and linked_edge.other_vert(v0) == v1
            ), None)
            if edge is None or not edge.is_valid:
                row_edges = []
                break
            row_edges.append(edge)
        if len(row_edges) == boundary_edge_count:
            candidate_edges.append(row_edges)

    if not candidate_edges:
        return False

    reference_center = sum((edge.verts[0].co + edge.verts[1].co for edge in reference_edges), Vector((0.0, 0.0, 0.0)))
    reference_center /= max(1, boundary_edge_count * 2)

    def row_score(edges):
        center = sum((edge.verts[0].co + edge.verts[1].co for edge in edges), Vector((0.0, 0.0, 0.0)))
        center /= max(1, len(edges) * 2)
        return (center - reference_center).length_squared

    generated_edges = min(candidate_edges, key=row_score)

    for vert in bm.verts:
        if vert.is_valid:
            vert.select = False

    for edge in bm.edges:
        if edge.is_valid:
            edge.select = False

    for face in bm.faces:
        if face.is_valid:
            face.select = False

    for edge in reference_edges:
        edge.select = True
        edge.verts[0].select = True
        edge.verts[1].select = True

    for edge in generated_edges:
        edge.select = True
        edge.verts[0].select = True
        edge.verts[1].select = True

    bmesh.update_edit_mesh(mesh.data, loop_triangles=False, destructive=False,)

    previous_select_mode = context.scene.tool_settings.mesh_select_mode[:]
    context.scene.tool_settings.mesh_select_mode = (False, True, False)

    try:
        bpy.ops.mesh.bridge_edge_loops()
    except RuntimeError:
        context.scene.tool_settings.mesh_select_mode = previous_select_mode
        bmesh.update_edit_mesh(mesh.data, loop_triangles=False, destructive=False,)
        return False

    context.scene.tool_settings.mesh_select_mode = previous_select_mode
    bmesh.update_edit_mesh(mesh.data, loop_triangles=True, destructive=True,)
    return True


# RETOPO GUIDE / STRIP HELPERS
RETOPO_STRIP_EPSILON = 1e-5
RETOPO_GUIDE_MIN_POINT_DISTANCE = 2.0
RETOPO_STRIP_DEFAULT_RADIUS = 18.0
RETOPO_STRIP_COLOR = (1.0, 1.0, 1.0, 0.9)
ADD_STROKE_DEFAULT_ALONG = 3


def _retopo_strip_ray_cast(context, screen_position):
    """Ray cast from the 3D View onto visible mesh objects except the retopo mesh."""
    region = context.region
    rv3d = context.space_data.region_3d

    if region is None or rv3d is None:
        return None

    origin = view3d_utils.region_2d_to_origin_3d( region, rv3d, screen_position,)
    direction = view3d_utils.region_2d_to_vector_3d( region, rv3d, screen_position,).normalized()
    depsgraph = context.evaluated_depsgraph_get()
    retopo_mesh = get_retopo_mesh(context)

    best_distance = float("inf")
    best_hit = None

    for object in context.visible_objects:

        if object == retopo_mesh:
            continue

        if object.type != "MESH":
            continue

        try:
            evaluated = object.evaluated_get(depsgraph)
            inverse = evaluated.matrix_world.inverted()
            local_origin = inverse @ origin
            local_direction = (inverse.to_3x3() @ direction).normalized()
            hit, location, normal, face_index = evaluated.ray_cast(
                local_origin,
                local_direction,
                depsgraph=depsgraph,
            )
        except (AttributeError, RuntimeError, TypeError):
            continue

        if not hit:
            continue

        world_location = evaluated.matrix_world @ location
        distance = (world_location - origin).length

        if distance >= best_distance:
            continue

        world_normal = evaluated.matrix_world.to_3x3().inverted().transposed() @ normal

        if world_normal.length <= RETOPO_STRIP_EPSILON:
            continue

        world_normal.normalize()
        best_distance = distance
        best_hit = (world_location, world_normal)

    return best_hit


def _retopo_strip_add_screen_point(points, point):
    """Append a mouse point only when it moved far enough to matter."""
    point = Vector(point)

    if not points:
        points.append(point)
        return

    if (point - points[-1]).length < RETOPO_GUIDE_MIN_POINT_DISTANCE:
        return

    points.append(point)


def _retopo_strip_tangent(points, index):
    """Return a stable screen-space tangent for a sampled stroke point."""
    if index <= 0:
        tangent = points[1] - points[0]
    elif index >= len(points) - 1:
        tangent = points[-1] - points[-2]
    else:
        tangent = points[index + 1] - points[index - 1]

    if tangent.length <= RETOPO_STRIP_EPSILON:
        return None

    return tangent.normalized()


def _retopo_strip_build_preview(context, screen_points, radius, along_count):
    """Build a snapped single-row quad strip from a screen-space stroke."""
    if len(screen_points) < 2:
        return None

    along_count = max(1, int(along_count))

    total_length = 0.0
    for index in range(1, len(screen_points)):
        total_length += (screen_points[index] - screen_points[index - 1]).length

    if total_length <= RETOPO_STRIP_EPSILON:
        return None

    distances = [0.0]
    for index in range(1, len(screen_points)):
        distances.append( distances[-1] + (screen_points[index] - screen_points[index - 1]).length)

    samples = []
    for sample_index in range(along_count + 1):
        distance = total_length * sample_index / along_count
        segment_index = 0

        while ( segment_index < len(screen_points) - 2 and distance > distances[segment_index + 1]):
            segment_index += 1

        start = screen_points[segment_index]
        end = screen_points[segment_index + 1]
        start_distance = distances[segment_index]
        end_distance = distances[segment_index + 1]
        span = end_distance - start_distance
        factor = (
            0.0
            if span <= RETOPO_STRIP_EPSILON
            else (distance - start_distance) / span
        )
        samples.append(start.lerp(end, factor))

    screen_rows = [[], []]
    world_rows = [[], []]

    for row_index, row_offset in enumerate((-radius, radius)):
        for along_index, point in enumerate(samples):
            tangent = _retopo_strip_tangent(samples, along_index)
            if tangent is None:
                return None

            normal_2d = Vector((-tangent.y, tangent.x))
            screen_position = point + normal_2d * row_offset
            hit = _retopo_strip_ray_cast(context, screen_position)

            if hit is None:
                return None

            screen_rows[row_index].append(screen_position)
            world_rows[row_index].append(hit[0])

    vertices = [coordinate for row in world_rows for coordinate in row]
    faces = []
    columns = along_count + 1

    for column_index in range(columns - 1):
        next_column = column_index + 1

        a = column_index
        b = next_column
        c = columns + next_column
        d = columns + column_index
        faces.append((a, b, c, d))

    return vertices, faces, screen_rows


def _retopo_strip_commit(context, mesh, vertices, faces):
    """Commit a generated quad strip to the registered retopo mesh."""
    if not vertices or not faces:
        return False

    bm = bmesh.from_edit_mesh(mesh.data)
    world_to_local = mesh.matrix_world.inverted()

    new_vertices = [ bm.verts.new(world_to_local @ coordinate) for coordinate in vertices ]

    new_faces = []

    for face_indices in faces:
        try:
            new_faces.append( bm.faces.new([new_vertices[index] for index in face_indices]))
        except ValueError:
            continue

    if not new_faces:
        return False

    bmesh.ops.recalc_face_normals(bm, faces=new_faces)
    bm.normal_update()

    for vertex in new_vertices:
        vertex.select = True

    for face in new_faces:
        face.select = True
        for edge in face.edges:
            edge.select = True

    bmesh.update_edit_mesh( mesh.data, loop_triangles=True, destructive=True,)
    return True


def _draw_retopo_strip(operator):
    """Draw the current strip preview grid in screen space."""
    if not operator.preview_screen_rows:
        return

    positions = []

    rows = operator.preview_screen_rows
    columns = len(rows[0]) if rows else 0

    for row in rows:
        for index in range(columns - 1):
            positions.extend([
                (row[index].x, row[index].y),
                (row[index + 1].x, row[index + 1].y),
            ])

    for column in range(columns):
        for row in range(len(rows) - 1):
            positions.extend([
                (rows[row][column].x, rows[row][column].y),
                (rows[row + 1][column].x, rows[row + 1][column].y),
            ])

    if not positions:
        return

    _retopo_draw_2d_lines(positions, RETOPO_STRIP_COLOR, width=2.0)


def _retopo_draw_brush_cursor(operator):
    """Draw the standard retopo brush radius and center marker."""
    center = ( operator.resize_center
        if operator.resize_active
        else operator.cursor
    )
    radius = operator.radius

    gpu.state.blend_set("ALPHA")

    draw_circle_2d( center, (1.0, 1.0, 1.0, 0.9), radius, segments=64,)
    draw_circle_2d( center, (1.0, 1.0, 1.0, 0.9), 2.0, segments=16,)

    gpu.state.blend_set("NONE")


def _draw_add_strips_brush(operator):
    """Draw the strip preview and Blender-style brush radius indicator."""
    _draw_retopo_strip(operator)
    _retopo_draw_brush_cursor(operator)


# Add strips operator
class AllPie_OT_AddStrips(Operator):
    bl_idname = "cop.add_strips"
    bl_label = "Add Strips"
    bl_description = "Draw a stroke to create a snapped strip of quads"
    bl_options = {"REGISTER"}

    radius: FloatProperty(
        name="Radius", description="Half-width of the strip in screen pixels",
        default=RETOPO_STRIP_DEFAULT_RADIUS, min=2.0, max=200.0,
    )
    along_count: IntProperty(
        name="Along", description="Number of quad segments along the strip",
        default=6, min=1, max=200,
    )

    @classmethod
    def poll(cls, context):
        return is_retopo_edit_context(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "radius")
        layout.prop(self, "along_count")

    def _preview(self, context):
        result = _retopo_strip_build_preview( context, self.screen_points, self.radius, self.along_count,)

        if result is None:
            self.preview_vertices = []
            self.preview_faces = []
            self.preview_screen_rows = []
            return False

        vertices, faces, screen_rows = result
        self.preview_vertices = vertices
        self.preview_faces = faces
        self.preview_screen_rows = screen_rows

        return True

    def execute(self, context):
        mesh = get_retopo_mesh(context)
        if mesh is None:
            self.report({'WARNING'}, "Specify the mesh for retopology")
            return {'CANCELLED'}

        if not is_retopo_edit_context(context):
            self.report({'WARNING'}, "Retopology must be initialized in Edit Mode")
            return {'CANCELLED'}

        settings = context.scene.retopo
        self.screen_points = load_strip_state(settings)

        if len(self.screen_points) < 2:
            self.report({'WARNING'}, "Draw a strip stroke")
            return {'CANCELLED'}

        self.preview_vertices = []
        self.preview_faces = []
        self.preview_screen_rows = []

        if not self._preview(context):
            self.report({'WARNING'}, "Unable to generate a strip from the stroke")
            return {'CANCELLED'}

        # Push the undo boundary before changing the mesh so the Add Strips
        # operator remains the last registered operation for F9 / Adjust Last Operation.
        bpy.ops.ed.undo_push( message="Before Add Strips",)

        if not _retopo_strip_commit( context, mesh, self.preview_vertices, self.preview_faces,):
            self.report({'WARNING'}, "Generated strip is empty")
            return {'CANCELLED'}

        settings.strip_radius = self.radius
        settings.strip_along_count = self.along_count

        return {'FINISHED'}

    def _cleanup(self, context):
        if self.draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
            self.draw_handler = None

    def _cancel_stroke(self, context):
        self.screen_points.clear()
        self.preview_vertices.clear()
        self.preview_faces.clear()
        self.preview_screen_rows.clear()

    def invoke(self, context, event):
        if not self.poll(context):
            self.report({'WARNING'}, "Retopology must be initialized in Edit Mode")
            return {'CANCELLED'}

        settings = context.scene.retopo
        self.radius = settings.strip_radius
        self.along_count = settings.strip_along_count

        self.region = context.region
        self.rv3d = context.space_data.region_3d
        self.screen_points = []
        self.preview_vertices = []
        self.preview_faces = []
        self.preview_screen_rows = []
        self.drawing = False
        self.resize_active = False
        self.cursor = Vector((event.mouse_region_x, event.mouse_region_y))
        self.resize_center = self.cursor.copy()
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            _draw_add_strips_brush, (self,), "WINDOW", "POST_PIXEL",
            )

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self.poll(context):
            self._cleanup(context)
            return {'CANCELLED'}

        # Blender-style F brush radius control.
        if event.type == 'F' and event.value == 'PRESS' and not self.drawing:
            self.resize_active = True
            self.resize_center = Vector((event.mouse_region_x, event.mouse_region_y))
            self.resize_start_radius = self.radius
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if self.resize_active:
            if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                delta_x = event.mouse_region_x - self.resize_center.x
                self.radius = max(2.0, min(200.0, self.resize_start_radius + delta_x))
                self._preview(context)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                self.resize_active = False
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if event.type == 'ESC':
                self.radius = self.resize_start_radius
                self.resize_active = False
                self._cleanup(context)
                _retopo_switch_to_tweak(context)
                return {'CANCELLED'}

            if event.type == 'RIGHTMOUSE':
                self.radius = self.resize_start_radius
                self.resize_active = False
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            return {'RUNNING_MODAL'}

        # Viewport navigation. Pass these events through to Blender's
        # native View3D navigation, matching the other retopo brushes.
        if _retopo_is_view_navigation_event(event):
            return {'PASS_THROUGH'}

        # ESC exits the tool and returns to Tweak.
        if event.type == 'ESC':
            self._cancel_stroke(context)
            self._cleanup(context)
            _retopo_switch_to_tweak(context)
            return {'CANCELLED'}

        # RIGHT MOUSE cancels the current action or exits the tool.
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            if self.drawing:
                self.drawing = False
                self._cancel_stroke(context)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            self._cleanup(context)
            return {'CANCELLED'}

        if event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
            if event.ctrl:
                self.along_count = min(200, self.along_count + 1)
            else:
                self.radius = min(200.0, self.radius * 1.1)

            self._preview(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
            if event.ctrl:
                self.along_count = max(1, self.along_count - 1)
            else:
                self.radius = max(2.0, self.radius / 1.1)

            self._preview(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = Vector((event.mouse_region_x, event.mouse_region_y))
            self.cursor = point

            if _retopo_strip_ray_cast(context, point) is None:
                return {'RUNNING_MODAL'}

            self.screen_points.clear()
            self._cancel_stroke(context)
            self.screen_points.append(point)
            self.drawing = True
            return {'RUNNING_MODAL'}

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            point = Vector((event.mouse_region_x, event.mouse_region_y))
            self.cursor = point

            if self.drawing and _retopo_strip_ray_cast(context, point) is not None:
                _retopo_strip_add_screen_point(self.screen_points, point)
                self._preview(context)

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if not self.drawing:
                return {'RUNNING_MODAL'}

            self.drawing = False

            if len(self.screen_points) >= 2 and self._preview(context):
                settings = context.scene.retopo
                store_strip_state(settings, self.screen_points)
                self._cleanup(context)
                result = self.execute(context)

                if 'FINISHED' in result:
                    _retopo_switch_to_tweak(context)

                context.area.tag_redraw()
                return result

            self._cancel_stroke(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._cleanup(context)


# ADD STROKE GUIDE TOOL
def _draw_retopo_guides(operator):
    """Draw stored and current retopology guide strokes in screen space."""
    positions = []

    strokes = list(operator.completed_strokes)
    if operator.current_world_points:
        strokes.append(operator.current_world_points)

    region = operator.region
    rv3d = operator.rv3d

    if region is None or rv3d is None:
        return

    for stroke in strokes:
        if len(stroke) < 2:
            continue

        previous = view3d_utils.location_3d_to_region_2d( region, rv3d, stroke[0],)

        if previous is None:
            continue

        for point in stroke[1:]:
            current = view3d_utils.location_3d_to_region_2d( region, rv3d, point,)

            if current is None:
                previous = None
                continue

            if previous is None:
                previous = current
                continue

            positions.extend([ (previous.x, previous.y), (current.x, current.y), ])

            previous = current

    if not positions:
        return

    _retopo_draw_2d_lines(positions, RETOPO_STRIP_COLOR, width=2.0)


class AllPie_OT_AddStroke(Operator):
    bl_idname = "cop.add_stroke"
    bl_label = "Add Stroke"
    bl_description = "Draw multiple retopology guide strokes"
    bl_options = {"REGISTER", "UNDO"}

    cuts: IntProperty(
        name="Cuts", description="Number of internal cuts between the end boundaries",
        default=ADD_STROKE_DEFAULT_ALONG, min=0, max=200,
    )

    @classmethod
    def poll(cls, context):
        return is_retopo_edit_context(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "cuts")



    def _cleanup(self, context):
        if getattr(self, "draw_handler", None) is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove( self.draw_handler, "WINDOW",)
            except Exception:
                pass

            self.draw_handler = None

        if self.area is not None:
            self.area.tag_redraw()

    def _cancel_current_stroke(self):
        self.current_screen_points.clear()
        self.current_world_points.clear()
        self.drawing = False

    def _load_existing_guides(self, settings):
        self.completed_strokes = []

        if settings.guide_source != "ADD_STROKE":
            return

        guide = load_guide_state(settings)

        if guide is None:
            return

        for spline in guide.splines:
            self.completed_strokes.append([ point.copy() for point in spline.points ])

    def _get_reference_cuts(self, mesh):
        bm = bmesh.from_edit_mesh(mesh.data)
        selected_edge_count = sum(
            1 for edge in bm.edges
            if edge.is_valid and edge.select
        )

        if selected_edge_count <= 0:
            return ADD_STROKE_DEFAULT_ALONG

        # Selected reference edges define the number of internal cuts
        # between the two end boundaries of the generated surface.
        return max(0, selected_edge_count - 1)

    def _store_guides(self, context):
        guide = RetopoGuide(source="ADD_STROKE")

        for stroke in self.completed_strokes:
            if len(stroke) < 2:
                continue

            guide.splines.append( RetopoGuideSpline( points=[point.copy() for point in stroke]))

        store_guide_state(
            context.scene.retopo,
            guide if guide.splines else None,
        )

    def execute(self, context):
        mesh = get_retopo_mesh(context)

        if mesh is None:
            self.report( {'WARNING'}, "Specify the mesh for retopology",)
            return {'CANCELLED'}

        if not is_retopo_edit_context(context):
            self.report( {'WARNING'}, "Retopology must be initialized in Edit Mode",)
            return {'CANCELLED'}

        settings = context.scene.retopo
        guide = load_guide_state(settings)

        if guide is None:
            self.report( {'WARNING'}, "Draw a retopology guide",)
            return {'CANCELLED'}

        guide_analysis = analyze_guide(guide)

        if len(guide_analysis.splines) < 2:
            self.report( {'WARNING'}, "At least two guide strokes are required",)
            return {'CANCELLED'}

        surface_settings = SurfaceGenerationSettings(
            along_count=self.cuts,
        )

        patch = generate_surface( guide_analysis, surface_settings,)

        if patch is None:
            self.report( {'WARNING'}, "Unable to generate a surface from the guides",)
            return {'CANCELLED'}

        commit_result = commit_surface( context, mesh, patch,)
        if not commit_result:
            self.report( {'WARNING'}, "Generated surface is empty",)
            return {'CANCELLED'}

        _, new_vertex_indices = commit_result

        if self.reference_edge_indices:
            if not _add_stroke_bridge_reference_edges( context, mesh, self.reference_edge_indices, new_vertex_indices, patch,):
                self.report( {'WARNING'}, "Unable to bridge generated surface to the selected edges",)

        # Keep the guide data available for F9 regeneration, but make a new
        # Add Stroke session start empty instead of loading this surface.
        settings.guide_source = "LAST_SURFACE"

        return {'FINISHED'}

    def _add_surface(self, context):
        if len(self.completed_strokes) < 2:
            self.report( {'WARNING'}, "At least two guide strokes are required",)
            return {'RUNNING_MODAL'}

        self._store_guides(context)

        result = self.execute(context)

        if 'FINISHED' not in result:
            return {'RUNNING_MODAL'}

        self._cleanup(context)
        _retopo_switch_to_tweak(context)

        return result

    def invoke(self, context, event):
        if not self.poll(context):
            self.report( {'WARNING'}, "Retopology must be initialized in Edit Mode",)
            return {'CANCELLED'}

        self.area = context.area
        self.region = context.region
        self.rv3d = context.space_data.region_3d
        self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))

        settings = context.scene.retopo

        # Selected retopo edges are used only as a topology-density reference.
        # Selected edges define internal cuts; with no edge selection,
        # fall back to the default cut count.
        self.reference_edge_indices = [
            edge.index
            for edge in bmesh.from_edit_mesh(context.edit_object.data).edges
            if edge.is_valid and edge.select
        ]
        self.cuts = self._get_reference_cuts(context.edit_object)

        self.current_screen_points = []
        self.current_world_points = []
        self.completed_strokes = []
        self.drawing = False

        self._load_existing_guides(settings)

        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            _draw_retopo_guides, (self,), "WINDOW", "POST_PIXEL",
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self.poll(context):
            self._cleanup(context)
            return {'CANCELLED'}

        # F builds a surface from the completed guide strokes.
        # The Add Stroke operator owns the surface generation so Blender
        # gets one normal undo/F9 operation instead of a nested operator.
        if ( event.type == 'F' and event.value == 'PRESS' and not self.drawing):
            return self._add_surface(context)

        # Undo the most recently completed guide stroke.
        # Add Stroke keeps its own guide history so Ctrl+Z cannot undo
        # unrelated mesh edits while this modal tool is active.
        if ( event.type == 'Z' and event.value == 'PRESS' and event.ctrl):
            if self.drawing:
                self._cancel_current_stroke()
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if self.completed_strokes:
                self.completed_strokes.pop()
                self._store_guides(context)
                context.area.tag_redraw()

            return {'RUNNING_MODAL'}

        # ESC exits the guide tool and returns to Tweak.
        if event.type == 'ESC':
            self._cancel_current_stroke()
            self._cleanup(context)
            _retopo_switch_to_tweak(context)
            return {'CANCELLED'}

        # RMB cancels only the current stroke while drawing.
        # When idle, RMB exits the guide tool but preserves completed guides.
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            if self.drawing:
                self._cancel_current_stroke()
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            self._cleanup(context)
            return {'CANCELLED'}

        # Viewport navigation.
        if _retopo_is_view_navigation_event(event):
            return {'PASS_THROUGH'}

        # Mouse movement.
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            point = Vector(( event.mouse_region_x, event.mouse_region_y,))

            self.cursor = point

            if self.drawing:
                delta = ( point - self.current_screen_points[-1]
                    if self.current_screen_points
                    else point
                )

                if delta.length >= RETOPO_GUIDE_MIN_POINT_DISTANCE:
                    hit = _retopo_strip_ray_cast( context, point,)

                    if hit is not None:
                        self.current_screen_points.append(point)
                        self.current_world_points.append(hit[0])

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Start a new guide stroke.
        if ( event.type == 'LEFTMOUSE' and event.value == 'PRESS'):
            point = Vector(( event.mouse_region_x, event.mouse_region_y,))

            hit = _retopo_strip_ray_cast( context, point,)

            if hit is None:
                return {'RUNNING_MODAL'}

            self.current_screen_points = [point]
            self.current_world_points = [hit[0]]
            self.drawing = True

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Finish the current guide stroke.
        if ( event.type == 'LEFTMOUSE' and event.value == 'RELEASE'):
            if not self.drawing:
                return {'RUNNING_MODAL'}

            self.drawing = False

            if len(self.current_world_points) >= 2:
                self.completed_strokes.append([ point.copy() for point in self.current_world_points ])
                self._store_guides(context)

            self.current_screen_points.clear()
            self.current_world_points.clear()

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._cleanup(context)


# Init operator
class AllPie_OT_InitRetopo(Operator):
    bl_idname = "cop.init_retopo"
    bl_label = "Initialize Retopology"
    bl_description = "Initialize the active mesh for retopology"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return is_retopo_edit_context(context) or (
            context.mode == "EDIT_MESH"
            and context.active_object is not None
            and context.active_object.type == "MESH"
        )

    def execute(self, context):
        # Init Retopo is intentionally an Edit Mode entry point.
        # The user creates the mesh first, enters Edit Mode, then
        # invokes this operator from the AllPie retopology pie.
        if context.mode != "EDIT_MESH" or context.edit_object is None:
            self.report({"WARNING"}, "Enter Edit Mode on a mesh first")
            return {"CANCELLED"}

        obj = context.edit_object

        if obj.type != "MESH":
            self.report({"WARNING"}, "The active Edit Mode object must be a mesh")
            return {"CANCELLED"}

        # Register the exact mesh the user is currently editing.
        context.scene.retopo.mesh = obj
        context.scene.retopo.guide_source = ""
        context.scene.retopo.guide_splines.clear()

        tool_settings = context.scene.tool_settings

        # Viewport display
        obj.display_type = "SOLID"
        obj.show_wire = True
        obj.show_all_edges = True
        obj.show_in_front = False
        # Retopology overlay
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.overlay.show_retopology = True

        # Face-project snapping
        tool_settings.use_snap = True
        tool_settings.snap_elements = {"FACE_PROJECT"}
        tool_settings.use_snap_self = False
        tool_settings.use_snap_align_rotation = True
        tool_settings.use_snap_rotate = True
        tool_settings.use_snap_scale = True


        # Shrinkwrap: create/configure it, but never assign its target.
        shrinkwrap = next(
            (mod for mod in obj.modifiers
             if mod.type == "SHRINKWRAP"), None,
        )

        if shrinkwrap is None:
            shrinkwrap = obj.modifiers.new("Shrinkwrap", "SHRINKWRAP")

        shrinkwrap.wrap_method = "TARGET_PROJECT"
        shrinkwrap.wrap_mode = "OUTSIDE_SURFACE"
        shrinkwrap.show_on_cage = True

        # Mirror
        mirror = next(
            (mod for mod in obj.modifiers
             if mod.type == "MIRROR"),
            None,
        )

        if mirror is None:
            mirror = obj.modifiers.new("Mirror", "MIRROR")

        mirror.use_clip = True
        mirror.show_on_cage = True

        # Leave the user ready to use the custom retopology tools.
        _retopo_switch_to_tweak(context)

        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)

# Retopology properties
class RetopoSettings(PropertyGroup):
    strip_radius: FloatProperty(
        name="Strip Radius", description="Half-width of Add Strips in screen pixels",
        default=RETOPO_STRIP_DEFAULT_RADIUS, min=2.0, max=200.0,
    )
    strip_along_count: IntProperty(
        name="Strip Along", description="Number of quad segments along Add Strips",
        default=6, min=1, max=200,
    )
    strip_points: CollectionProperty(type=RetopoGuidePoint)
    guide_source: StringProperty(options={'HIDDEN'})
    guide_splines: CollectionProperty(type=RetopoGuideSplineState)
    mesh: PointerProperty( name="Retopo Mesh", type=bpy.types.Object, description="Retopology Mesh",)

# ============================================================
# Blender topology-relax algorithm, adapted for Edit Mode BMesh.
# Based on Blender's topology-relax step:
#   - corners (<= 2 neighbors) are not modified
#   - boundary vertices use boundary neighbors
#   - neighbor positions are averaged
#   - smoothed position is projected onto the vertex tangent plane
#   - result is scaled by brush factor
#   - Relax Slide alternate path performs 4 passes

def _relax_brush_falloff(distance, radius):
    """Simple radial brush falloff."""
    if radius <= EPSILON or distance >= radius:
        return 0.0

    x = max(0.0, 1.0 - distance / radius)
    return x * x


def _collect_relax_factors(context, mesh, bm, cursor, radius, strength):
    if radius <= EPSILON or strength <= 0.0:
        return {}

    region = context.region
    rv3d = context.space_data.region_3d

    if region is None or rv3d is None:
        return {}

    world_matrix = mesh.matrix_world
    factors = {}

    for vert in bm.verts:
        if not vert.is_valid:
            continue

        world_co = world_matrix @ vert.co
        screen = view3d_utils.location_3d_to_region_2d( region, rv3d, world_co,)

        if screen is None:
            continue

        distance = (screen - cursor).length

        if distance >= radius:
            continue

        falloff = _relax_brush_falloff( distance, radius,)
        factor = falloff * strength

        if factor > 0.0:
            factors[vert] = factor

    return factors


def _boundary_corner_normal( current_position, neighbors, positions,):
    """
    Compute the boundary normal used for a boundary vertex
    with exactly two boundary neighbors.
    """

    normal = Vector((0.0, 0.0, 0.0))

    for neighbor in neighbors:

        direction = ( positions[neighbor] - current_position)

        if direction.length <= EPSILON:
            continue

        normal += direction.normalized()

    if normal.length <= EPSILON:
        return None

    return normal.normalized()


def _relax_topology_pass( bm, factors,):
    """
    Perform one topology-relax pass.

    Every vertex is evaluated from the same position snapshot
    so updates do not propagate sequentially through the pass.
    """

    if not factors:
        return 0

    bm.normal_update()

    # Snapshot all vertex positions before calculating
    # any new positions.
    positions = { vert: vert.co.copy()
        for vert in bm.verts
        if vert.is_valid
    }

    new_positions = {}

    for vert, factor in factors.items():

        neighbors = [
            edge.other_vert(vert)
            for edge in vert.link_edges
        ]

        # Blender topology relax does not modify
        # corner vertices.
        if len(neighbors) <= 2:
            continue

        is_boundary = vert.is_boundary

        if is_boundary:
            # Boundary vertices only relax against
            # neighboring boundary vertices.
            neighbors = [
                neighbor
                for neighbor in neighbors
                if neighbor.is_boundary
            ]

        if not neighbors:
            continue

        current_position = positions[vert]

        # Average neighbor positions.
        smooth_position = sum( (positions[neighbor] for neighbor in neighbors),
            Vector((0.0, 0.0, 0.0)),
        ) / len(neighbors)

        # Determine the tangent-plane normal.
        if is_boundary and len(neighbors) == 2:

            normal = _boundary_corner_normal( current_position, neighbors, positions,)

            if normal is None:
                continue

        else:

            normal = vert.normal.copy()

            if normal.length <= EPSILON:
                continue

            normal.normalize()

        # Project the smoothing displacement onto
        # the tangent plane of the current vertex.
        delta = smooth_position - current_position
        delta -= normal * delta.dot(normal)
        new_positions[vert] = ( current_position + delta * min(1.0, factor))

    # Apply all calculated positions only after
    # the complete pass has been evaluated.
    moved = 0

    for vert, position in new_positions.items():

        if ( position - vert.co).length_squared <= EPSILON * EPSILON:
            continue

        vert.co = position
        moved += 1

    return moved


def _relax_brush_step( bm, factors,):
    """
    Blender Relax Slide's Shift/alternate behavior.

    Blender performs four topology-relax passes
    for each brush step.
    """

    return sum(
        _relax_topology_pass(bm, factors)
        for _ in range(4)
    )

def _draw_relax_brush(operator):
    _retopo_draw_brush_cursor(operator)

class AllPie_OT_RelaxTopology(Operator):
    bl_idname = "cop.relax_topology"
    bl_label = "Relax Topology"
    bl_description = "Relax retopology using Blender's topology-relax algorithm"
    bl_options = {"REGISTER"}

    radius: FloatProperty( name="Radius", description="Brush radius in screen pixels",
        default=50.0, min=5.0, max=500.0,
    )

    strength: FloatProperty( name="Strength", description="Relax strength per brush dab",
        default=0.35, min=0.0, max=1.0,
    )

    spacing: FloatProperty(
        name="Spacing", description="Distance between brush dabs as a fraction of radius",
        default=0.15, min=0.02, max=0.5,
    )

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and is_retopo_edit_context(context)
        )

    def _remove_draw_handler(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
        self.draw_handler = None

        if context.area:
            context.area.tag_redraw()

    def invoke(self, context, event):
        mesh = get_retopo_mesh(context)

        if mesh is None:
            self.report( {"WARNING"}, "Specify the mesh for retopology",)
            return {"CANCELLED"}

        self.mesh = mesh

        self.stroke_active = False
        self.stroke_changed = False
        # Blender-style F brush-size control state.
        self.resize_active = False

        self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))
        self.resize_center = self.cursor.copy()

        self.last_pressure = 1.0
        self.distance_since_dab = 0.0

        self.stroke_backup = {}

        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                _draw_relax_brush, (self,), "WINDOW", "POST_PIXEL",
                )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    def _capture_stroke_backup(self):
        bm = bmesh.from_edit_mesh(self.mesh.data)

        self.stroke_backup = {
            vert: vert.co.copy()
            for vert in bm.verts
            if vert.is_valid
        }

    def _restore_stroke(self):
        if not self.stroke_backup:
            return

        bm = bmesh.from_edit_mesh(self.mesh.data)

        for vert, position in self.stroke_backup.items():
            if vert.is_valid:
                vert.co = position

        bm.normal_update()

        bmesh.update_edit_mesh( self.mesh.data, loop_triangles=True, destructive=True,)

    # Dab
    def _apply_dab(self, context, cursor, pressure):
        
        bm = bmesh.from_edit_mesh(self.mesh.data)
        strength = ( self.strength * max(0.0, min(1.0, pressure)))
        factors = _collect_relax_factors( context, self.mesh, bm, cursor, self.radius, strength,)

        if not factors:
            return False

        moved = _relax_brush_step( bm, factors,)

        if moved == 0:
            return False

        bm.normal_update()
        bmesh.update_edit_mesh( self.mesh.data, loop_triangles=True, destructive=True,)

        return True

    # Stroke begin/end
    def _begin_stroke(self, context, event):

        self.stroke_active = True

        self.last_mouse = Vector(( event.mouse_region_x, event.mouse_region_y,))
        self.last_pressure = ( getattr(event, "pressure", 1.0) or 1.0)

        self.distance_since_dab = 0.0

        self._capture_stroke_backup()

        # First dab happens immediately.
        self.stroke_changed = self._apply_dab( context, self.last_mouse, self.last_pressure,)

    def _end_stroke(self):
        if self.stroke_changed:
            bpy.ops.ed.undo_push( message="Relax Topology Stroke",)

        self.stroke_active = False
        self.distance_since_dab = 0.0
        self.stroke_changed = False
        self.stroke_backup.clear()

    def _cancel_stroke(self):

        self._restore_stroke()

        self.stroke_active = False
        self.stroke_changed = False
        self.distance_since_dab = 0.0
        self.stroke_backup.clear()

    # Stroke interpolation
    def _process_mouse_segment( self, context, mouse_position, pressure,):
        start = self.last_mouse
        end = mouse_position

        delta = end - start
        segment_length = delta.length

        if segment_length <= EPSILON:
            self.last_mouse = end
            self.last_pressure = pressure
            return

        direction = delta / segment_length
        spacing = max( 2.0, self.radius * self.spacing,)

        remaining = segment_length
        travelled = 0.0
        current_position = start.copy()

        start_pressure = self.last_pressure

        while True:
            distance_to_dab = ( spacing - self.distance_since_dab)

            if remaining + EPSILON < distance_to_dab:
                self.distance_since_dab += remaining
                break

            current_position += ( direction * distance_to_dab)
            remaining -= distance_to_dab

            travelled += distance_to_dab

            t = travelled / segment_length

            dab_pressure = ( start_pressure + (pressure - start_pressure) * t)

            if self._apply_dab( context, current_position, dab_pressure,):
                self.stroke_changed = True

            self.distance_since_dab = 0.0

        self.last_mouse = end
        self.last_pressure = pressure

    # Brush size control (Blender F behavior)
    def _begin_radius_resize(self, event):
        self.resize_active = True
        self.resize_center = Vector(( event.mouse_region_x, event.mouse_region_y,))
        self.resize_start_radius = self.radius

    def _update_radius_resize(self, event):
        mouse_x = event.mouse_region_x
        start_x = self.resize_center.x

        # Blender's WM_OT_radial_control uses the horizontal mouse travel for
        # pixel brush size: moving right increases size and moving left
        # decreases it. The initial size is preserved at the starting point.
        delta_x = mouse_x - start_x

        self.radius = max( 5.0, min( 500.0, self.resize_start_radius + delta_x,),)

    def _cancel_radius_resize(self):
        self.radius = self.resize_start_radius
        self.resize_active = False

    # Modal
    def modal(self, context, event):

        # Blender-style F brush radius control.
        if event.type == "F" and event.value == "PRESS" and not self.stroke_active:
            self._begin_radius_resize(event)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if self.resize_active:
            if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
                self._update_radius_resize(event)
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                # LMB confirms the new brush radius, matching Blender's
                # radial control interaction.
                self.resize_active = False
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            if event.type == "ESC":
                self._cancel_radius_resize()
                self._remove_draw_handler(context)
                _retopo_switch_to_tweak(context)
                return {"CANCELLED"}

            if event.type == "RIGHTMOUSE":
                self._cancel_radius_resize()
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            return {"RUNNING_MODAL"}

        # Cancel current stroke / operator
        if event.type == "ESC":
            if self.stroke_active:
                self._cancel_stroke()

            self._remove_draw_handler(context)
            _retopo_switch_to_tweak(context)
            return {"CANCELLED"}

        if event.type == "RIGHTMOUSE":
            if self.stroke_active:
                self._cancel_stroke()
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            self._remove_draw_handler(context)
            return {"CANCELLED"}

        # Viewport navigation. Pass these events through to Blender's
        # native View3D navigation, matching the other retopo brushes.
        if _retopo_is_view_navigation_event(event):
            return {'PASS_THROUGH'}

        # Mouse movement
        if event.type in { "MOUSEMOVE", "INBETWEEN_MOUSEMOVE", }:

            mouse_position = Vector(( event.mouse_region_x, event.mouse_region_y,))

            self.cursor = mouse_position

            pressure = ( getattr(event, "pressure", 1.0) or self.last_pressure)

            if self.stroke_active:
                self._process_mouse_segment( context, mouse_position, max(0.0, min(1.0, pressure)),)
            else:
                self.last_mouse = mouse_position

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Stroke begin/end
        if event.type == "LEFTMOUSE":

            if event.value == "PRESS":
                self._begin_stroke( context, event,)

                return {"RUNNING_MODAL"}

            if event.value == "RELEASE":
                self._end_stroke()

                context.area.tag_redraw()

                return {"RUNNING_MODAL"}

        # Radius
        if event.type == "WHEELUPMOUSE":
            self.radius = min( 500.0, self.radius * 1.1,)

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        if event.type == "WHEELDOWNMOUSE":
            self.radius = max( 5.0, self.radius / 1.1,)

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}


classes = (
    RetopoGuidePoint,
    RetopoGuideSplineState,
    RetopoSettings,
    AllPie_OT_InitRetopo,
    AllPie_OT_AddStrips,
    AllPie_OT_RelaxTopology,
    AllPie_OT_AddStroke,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.retopo = PointerProperty(type=RetopoSettings)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.retopo

if __name__ == "__main__":
    register()
