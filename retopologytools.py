from dataclasses import dataclass, field

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
        bpy.ops.wm.tool_set_by_id(
            name="builtin.select",
            space_type="VIEW_3D",
        )
    except RuntimeError:
        pass


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
    across_count: int
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
    """Generate a regular quad grid between multiple open guide splines."""
    if len(guide_analysis.splines) < 2:
        return None

    across_count = max(1, int(settings.across_count))
    along_count = max(1, int(settings.along_count))
    sample_count = along_count + 1

    sampled_guides = [
        sample_guide_spline(spline, sample_count)
        for spline in guide_analysis.splines
    ]

    rows = []
    for guide_index in range(len(sampled_guides) - 1):
        row_start = sampled_guides[guide_index]
        row_end = sampled_guides[guide_index + 1]

        if guide_index == 0:
            rows.append([point.copy() for point in row_start])

        for step in range(1, across_count + 1):
            factor = step / across_count
            rows.append(interpolate_rows(row_start, row_end, factor))

    patch = build_surface_patch(rows)
    return patch if patch.faces else None


def commit_surface(context, main_object, patch):
    """Commit a generated patch and orient it toward the current viewport."""
    if not patch.vertices or not patch.faces:
        return False

    bm = bmesh.from_edit_mesh(main_object.data)
    world_to_local = main_object.matrix_world.inverted()

    new_vertices = [
        bm.verts.new(world_to_local @ coordinate)
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
    bmesh.update_edit_mesh( main_object.data, loop_triangles=True, destructive=True,)
    return True


# RETOPO GUIDE / STRIP HELPERS
RETOPO_STRIP_EPSILON = 1e-5
RETOPO_GUIDE_MIN_POINT_DISTANCE = 2.0
RETOPO_STRIP_DEFAULT_RADIUS = 18.0
RETOPO_STRIP_COLOR = (1.0, 1.0, 1.0, 0.9)


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
        distances.append(
            distances[-1] + (screen_points[index] - screen_points[index - 1]).length
        )

    samples = []
    for sample_index in range(along_count + 1):
        distance = total_length * sample_index / along_count
        segment_index = 0

        while (
            segment_index < len(screen_points) - 2
            and distance > distances[segment_index + 1]
        ):
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

    new_vertices = [
        bm.verts.new(world_to_local @ coordinate)
        for coordinate in vertices
    ]

    new_faces = []

    for face_indices in faces:
        try:
            new_faces.append(
                bm.faces.new([new_vertices[index] for index in face_indices])
            )
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

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": positions})

    gpu.state.blend_set("ALPHA")

    try:
        gpu.state.line_width_set(2.0)
    except Exception:
        pass

    shader.bind()
    shader.uniform_float("color", RETOPO_STRIP_COLOR)
    batch.draw(shader)

    try:
        gpu.state.line_width_set(1.0)
    except Exception:
        pass

    gpu.state.blend_set("NONE")


def _draw_add_strips_brush(operator):
    """Draw the strip preview and Blender-style brush radius indicator."""
    _draw_retopo_strip(operator)

    center = (
        operator.resize_center
        if operator.resize_active
        else operator.cursor
    )
    radius = operator.radius

    gpu.state.blend_set("ALPHA")

    draw_circle_2d(
        center,
        (1.0, 1.0, 1.0, 0.9),
        radius,
        segments=64,
    )

    draw_circle_2d(
        center,
        (1.0, 1.0, 1.0, 0.9),
        2.0,
        segments=16,
    )

    gpu.state.blend_set("NONE")


# Add strips operator
class AllPie_OT_AddStrips(Operator):
    bl_idname = "cop.add_strips"
    bl_label = "Add Strips"
    bl_description = "Draw a stroke to create a snapped strip of quads"
    bl_options = {"REGISTER", "UNDO"}

    radius: FloatProperty(
        name="Radius",
        description="Half-width of the strip in screen pixels",
        default=RETOPO_STRIP_DEFAULT_RADIUS,
        min=2.0,
        max=200.0,
    )
    along_count: IntProperty(
        name="Along",
        description="Number of quad segments along the strip",
        default=6,
        min=1,
        max=200,
    )

    @classmethod
    def poll(cls, context):
        return is_retopo_edit_context(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "radius")
        layout.prop(self, "along_count")

    def _preview(self, context):
        result = _retopo_strip_build_preview(
            context,
            self.screen_points,
            self.radius,
            self.along_count,
        )

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

        if not _retopo_strip_commit(
            context,
            mesh,
            self.preview_vertices,
            self.preview_faces,
        ):
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
            _draw_add_strips_brush,
            (self,),
            "WINDOW",
            "POST_PIXEL",
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
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.alt:
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

        previous = view3d_utils.location_3d_to_region_2d(
            region,
            rv3d,
            stroke[0],
        )

        if previous is None:
            continue

        for point in stroke[1:]:
            current = view3d_utils.location_3d_to_region_2d(
                region,
                rv3d,
                point,
            )

            if current is None:
                previous = None
                continue

            if previous is None:
                previous = current
                continue

            positions.extend([
                (previous.x, previous.y),
                (current.x, current.y),
            ])

            previous = current

    if not positions:
        return

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(
        shader,
        "LINES",
        {"pos": positions},
    )

    gpu.state.blend_set("ALPHA")

    try:
        gpu.state.line_width_set(2.0)
    except Exception:
        pass

    shader.bind()
    shader.uniform_float("color", RETOPO_STRIP_COLOR)
    batch.draw(shader)

    try:
        gpu.state.line_width_set(1.0)
    except Exception:
        pass

    gpu.state.blend_set("NONE")


class AllPie_OT_AddStroke(Operator):
    bl_idname = "cop.add_stroke"
    bl_label = "Add Stroke"
    bl_description = "Draw multiple retopology guide strokes"
    bl_options = {"REGISTER", "UNDO"}

    across_count: IntProperty(
        name="Across",
        description="Number of rows between neighboring guide strokes",
        default=3,
        min=1,
        max=200,
    )
    along_count: IntProperty(
        name="Along",
        description="Number of segments along each guide stroke",
        default=3,
        min=1,
        max=200,
    )

    @classmethod
    def poll(cls, context):
        return is_retopo_edit_context(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "across_count")
        layout.prop(self, "along_count")

    def _cleanup(self, context):
        if getattr(self, "draw_handler", None) is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(
                    self.draw_handler,
                    "WINDOW",
                )
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
            self.completed_strokes.append([
                point.copy()
                for point in spline.points
            ])

    def _store_guides(self, context):
        guide = RetopoGuide(source="ADD_STROKE")

        for stroke in self.completed_strokes:
            if len(stroke) < 2:
                continue

            guide.splines.append(
                RetopoGuideSpline(
                    points=[point.copy() for point in stroke]
                )
            )

        store_guide_state(
            context.scene.retopo,
            guide if guide.splines else None,
        )

    def execute(self, context):
        mesh = get_retopo_mesh(context)

        if mesh is None:
            self.report(
                {'WARNING'},
                "Specify the mesh for retopology",
            )
            return {'CANCELLED'}

        if not is_retopo_edit_context(context):
            self.report(
                {'WARNING'},
                "Retopology must be initialized in Edit Mode",
            )
            return {'CANCELLED'}

        settings = context.scene.retopo
        guide = load_guide_state(settings)

        if guide is None:
            self.report(
                {'WARNING'},
                "Draw a retopology guide",
            )
            return {'CANCELLED'}

        guide_analysis = analyze_guide(guide)

        if len(guide_analysis.splines) < 2:
            self.report(
                {'WARNING'},
                "At least two guide strokes are required",
            )
            return {'CANCELLED'}

        surface_settings = SurfaceGenerationSettings(
            across_count=self.across_count,
            along_count=self.along_count,
        )

        patch = generate_surface(
            guide_analysis,
            surface_settings,
        )

        if patch is None:
            self.report(
                {'WARNING'},
                "Unable to generate a surface from the guides",
            )
            return {'CANCELLED'}

        if not commit_surface(
            context,
            mesh,
            patch,
        ):
            self.report(
                {'WARNING'},
                "Generated surface is empty",
            )
            return {'CANCELLED'}

        settings.across_count = self.across_count
        settings.along_count = self.along_count

        # Keep the guide data available for F9 regeneration, but make a new
        # Add Stroke session start empty instead of loading this surface.
        settings.guide_source = "LAST_SURFACE"

        return {'FINISHED'}

    def _add_surface(self, context):
        if len(self.completed_strokes) < 2:
            self.report(
                {'WARNING'},
                "At least two guide strokes are required",
            )
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
            self.report(
                {'WARNING'},
                "Retopology must be initialized in Edit Mode",
            )
            return {'CANCELLED'}

        self.area = context.area
        self.region = context.region
        self.rv3d = context.space_data.region_3d
        self.cursor = Vector((
            event.mouse_region_x,
            event.mouse_region_y,
        ))

        settings = context.scene.retopo

        self.across_count = settings.across_count
        self.along_count = settings.along_count

        self.current_screen_points = []
        self.current_world_points = []
        self.completed_strokes = []
        self.drawing = False

        self._load_existing_guides(settings)

        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            _draw_retopo_guides,
            (self,),
            "WINDOW",
            "POST_PIXEL",
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
        if (
            event.type == 'F'
            and event.value == 'PRESS'
            and not self.drawing
        ):
            return self._add_surface(context)

        # Undo the most recently completed guide stroke.
        # Add Stroke keeps its own guide history so Ctrl+Z cannot undo
        # unrelated mesh edits while this modal tool is active.
        if (
            event.type == 'Z'
            and event.value == 'PRESS'
            and event.ctrl
        ):
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
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.alt:
            return {'PASS_THROUGH'}

        # Mouse movement.
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            point = Vector((
                event.mouse_region_x,
                event.mouse_region_y,
            ))

            self.cursor = point

            if self.drawing:
                delta = (
                    point - self.current_screen_points[-1]
                    if self.current_screen_points
                    else point
                )

                if delta.length >= RETOPO_GUIDE_MIN_POINT_DISTANCE:
                    hit = _retopo_strip_ray_cast(
                        context,
                        point,
                    )

                    if hit is not None:
                        self.current_screen_points.append(point)
                        self.current_world_points.append(hit[0])

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Start a new guide stroke.
        if (
            event.type == 'LEFTMOUSE'
            and event.value == 'PRESS'
        ):
            point = Vector((
                event.mouse_region_x,
                event.mouse_region_y,
            ))

            hit = _retopo_strip_ray_cast(
                context,
                point,
            )

            if hit is None:
                return {'RUNNING_MODAL'}

            self.current_screen_points = [point]
            self.current_world_points = [hit[0]]
            self.drawing = True

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Finish the current guide stroke.
        if (
            event.type == 'LEFTMOUSE'
            and event.value == 'RELEASE'
        ):
            if not self.drawing:
                return {'RUNNING_MODAL'}

            self.drawing = False

            if len(self.current_world_points) >= 2:
                self.completed_strokes.append([
                    point.copy()
                    for point in self.current_world_points
                ])
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
            (mod for mod in obj.modifiers if mod.type == "SHRINKWRAP"), None,
        )

        if shrinkwrap is None:
            shrinkwrap = obj.modifiers.new("Shrinkwrap", "SHRINKWRAP")

        shrinkwrap.wrap_method = "TARGET_PROJECT"
        shrinkwrap.wrap_mode = "OUTSIDE_SURFACE"
        shrinkwrap.show_on_cage = True

        # Mirror
        mirror = next(
            (mod for mod in obj.modifiers if mod.type == "MIRROR"),
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
    across_count: IntProperty(
        name="Across",
        description="Number of rows between neighboring guide strokes",
        default=3,
        min=1,
        max=200,
    )
    along_count: IntProperty(
        name="Along",
        description="Number of segments along each guide stroke",
        default=3,
        min=1,
        max=200,
    )
    strip_radius: FloatProperty(
        name="Strip Radius",
        description="Half-width of Add Strips in screen pixels",
        default=RETOPO_STRIP_DEFAULT_RADIUS,
        min=2.0,
        max=200.0,
    )
    strip_along_count: IntProperty(
        name="Strip Along",
        description="Number of quad segments along Add Strips",
        default=6,
        min=1,
        max=200,
    )
    strip_points: CollectionProperty(type=RetopoGuidePoint)
    guide_source: StringProperty(options={'HIDDEN'})
    guide_splines: CollectionProperty(type=RetopoGuideSplineState)
    mesh: PointerProperty(
        name="Retopo Mesh",
        type=bpy.types.Object,
        description="Mesh used for retopology",
    )

# ============================================================
# Blender topology-relax algorithm, adapted for Edit Mode BMesh.
# Based on Blender's topology-relax step:
#   - corners (<= 2 neighbors) are not modified
#   - boundary vertices use boundary neighbors
#   - neighbor positions are averaged
#   - smoothed position is projected onto the vertex tangent plane
#   - result is scaled by brush factor
#   - Relax Slide alternate path performs 4 passes
# ============================================================

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
    positions = {
        vert: vert.co.copy()
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
        smooth_position = sum(
            (positions[neighbor] for neighbor in neighbors),
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
    # Blender's radial brush-size control keeps the brush preview anchored
    # at the position where F was pressed while the mouse is dragged.
    center = operator.resize_center if operator.resize_active else operator.cursor
    radius = operator.radius
    gpu.state.blend_set("ALPHA")

    # Outer brush radius.
    draw_circle_2d( center, (1.0, 1.0, 1.0, 0.9), radius, segments=64,)
    # Center marker.
    draw_circle_2d( center, (1.0, 1.0, 1.0, 0.9), 2.0, segments=16,)

    gpu.state.blend_set("NONE")

class AllPie_OT_RelaxTopology(Operator):
    bl_idname = "cop.relax_topology"
    bl_label = "Relax Topology"
    bl_description = "Relax retopology using Blender's topology-relax algorithm"
    bl_options = {"REGISTER"}

    radius: FloatProperty( name="Radius",
        description="Brush radius in screen pixels",
        default=50.0,
        min=5.0,
        max=500.0,
    )

    strength: FloatProperty(
        name="Strength",
        description="Relax strength per brush dab",
        default=0.35,
        min=0.0,
        max=1.0,
    )

    spacing: FloatProperty(
        name="Spacing",
        description="Distance between brush dabs as a fraction of radius",
        default=0.15,
        min=0.02,
        max=0.5,
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
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.alt:
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


# STITCH
STITCH_CURSOR_RADIUS = 10.0
STITCH_MERGE_DISTANCE = 10.0  # screen-space pixels


def _stitch_find_target_vertex(operator, moving_vertex):
    bm = bmesh.from_edit_mesh(operator.mesh.data)

    moving_world = operator.mesh.matrix_world @ moving_vertex.co

    moving_screen = view3d_utils.location_3d_to_region_2d(
        operator.region,
        operator.rv3d,
        moving_world,
    )

    if moving_screen is None:
        return None

    best_vertex = None
    best_distance = STITCH_MERGE_DISTANCE

    for vert in bm.verts:

        if not vert.is_valid or vert == moving_vertex:
            continue

        world_position = operator.mesh.matrix_world @ vert.co

        screen_position = view3d_utils.location_3d_to_region_2d(
            operator.region,
            operator.rv3d,
            world_position,
        )

        if screen_position is None:
            continue

        distance = (screen_position - moving_screen).length

        if distance < best_distance:
            best_distance = distance
            best_vertex = vert

    return best_vertex


def _draw_stitch_cursor(operator):
    if operator is None or operator.region is None:
        return

    cursor = operator.cursor

    # Follow the moving vertex while native transform is active.
    if operator.stroke_active and operator.mesh is not None:

        try:
            bm = bmesh.from_edit_mesh(operator.mesh.data)

            moving_vertex = None

            for vert in bm.verts:
                if vert.is_valid and vert.select:
                    moving_vertex = vert
                    break

            if moving_vertex is not None:

                world_position = ( operator.mesh.matrix_world @ moving_vertex.co)

                screen_position = (
                    view3d_utils.location_3d_to_region_2d(
                        operator.region,
                        operator.rv3d,
                        world_position,
                    )
                )

                if screen_position is not None:
                    cursor = screen_position

        except Exception:
            pass

    gpu.state.blend_set("ALPHA")

    draw_circle_2d( cursor, (1.0, 1.0, 1.0, 0.9), STITCH_CURSOR_RADIUS, segments=32,)

    gpu.state.blend_set("NONE")


class AllPie_OT_StitchTopology(Operator):

    bl_idname = "cop.stitch_topology"
    bl_label = "Stitch Topology"
    bl_description = "Move and stitch vertices"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):

        mesh = get_retopo_mesh(context)

        if mesh is None:
            return {'CANCELLED'}

        if mesh.mode != 'EDIT':
            return {'CANCELLED'}

        self.mesh = mesh
        self.area = context.area
        self.region = context.region
        self.rv3d = context.space_data.region_3d

        self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))

        self.stroke_active = False
        self.cancel_transform = False
        self.exit_to_tweak = False

        self.draw_handler = (
            bpy.types.SpaceView3D.draw_handler_add(
                _draw_stitch_cursor,
                (self,),
                'WINDOW',
                'POST_PIXEL',
            )
        )

        context.window.cursor_set("PAINT_BRUSH")
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def _remove_draw_handler(self):

        if getattr(self, "draw_handler", None) is not None:

            try:
                bpy.types.SpaceView3D.draw_handler_remove( self.draw_handler, 'WINDOW',)
            except Exception:
                pass

            self.draw_handler = None

    def _cleanup(self, context):

        self._remove_draw_handler()

        self.stroke_active = False

        try:
            context.window.cursor_set("DEFAULT")
        except Exception:
            pass

        if self.area is not None:
            self.area.tag_redraw()

    def _begin_stroke(self, context, event):

        # Always force vertex selection mode.
        bpy.ops.mesh.select_mode(type="VERT")

        # Select the vertex under the mouse.
        result = bpy.ops.view3d.select(
            location=( event.mouse_region_x, event.mouse_region_y,),
            extend=False,
            deselect_all=True,
        )

        if "CANCELLED" in result:
            return False

        # Confirm a vertex was selected.
        bm = bmesh.from_edit_mesh(self.mesh.data)

        moving_vertex = None

        for vert in bm.verts:

            if vert.is_valid and vert.select:
                moving_vertex = vert
                break

        if moving_vertex is None:
            return False

        # Native Blender transform.
        result = bpy.ops.transform.translate(
            "INVOKE_DEFAULT",
            release_confirm=True,
            use_proportional_edit=False,
        )

        if "CANCELLED" in result:
            return False

        self.stroke_active = True
        self.cancel_transform = False

        return True

    def _is_transform_running(self, context):

        try:

            for operator in context.window.modal_operators:

                if operator.bl_idname == "TRANSFORM_OT_translate":
                    return True

        except Exception:
            pass

        return False

    def _finish_stroke(self):

        if self.cancel_transform:
            self.stroke_active = False
            return

        bm = bmesh.from_edit_mesh(self.mesh.data)

        moving_vertex = None

        for vert in bm.verts:

            if vert.is_valid and vert.select:
                moving_vertex = vert
                break

        if moving_vertex is None:
            self.stroke_active = False
            return

        # Find the nearest vertex to the moved vertex.
        target_vertex = _stitch_find_target_vertex( self, moving_vertex,)

        # Nothing close enough to stitch to.
        if target_vertex is None:
            self.stroke_active = False

            if self.area is not None:
                self.area.tag_redraw()

            return

        # Merge the moved vertex into the target vertex.
        bmesh.ops.pointmerge(
            bm,
            verts=[moving_vertex],
            merge_co=target_vertex.co.copy(),
            vert_target=target_vertex,
        )

        bmesh.update_edit_mesh( self.mesh.data, loop_triangles=False, destructive=True,)

        self.stroke_active = False

        if self.area is not None:
            self.area.tag_redraw()

    def modal(self, context, event):

        # Native transform is running.
        if self.stroke_active:

            # ESC cancels the native transform and exits Stitch.
            if event.type == 'ESC':
                self.cancel_transform = True
                self.exit_to_tweak = True

            # RMB cancels the native transform but keeps Stitch active.
            elif event.type == 'RIGHTMOUSE':
                self.cancel_transform = True

            if self._is_transform_running(context):
                return {'PASS_THROUGH'}

            should_exit = self.exit_to_tweak

            # Transform has finished.
            self._finish_stroke()

            if should_exit:
                self._cleanup(context)
                self.exit_to_tweak = False
                _retopo_switch_to_tweak(context)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

        # Exit Stitch.
        if event.type == 'ESC':

            self._cleanup(context)
            _retopo_switch_to_tweak(context)

            return {'CANCELLED'}

        if event.type == 'RIGHTMOUSE':

            self._cleanup(context)

            return {'CANCELLED'}

        # View navigation.
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.alt:
            return {'PASS_THROUGH'}

        # Keep cursor updated.
        if event.type == 'MOUSEMOVE':

            self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))

            if self.area is not None:
                self.area.tag_redraw()

        # Start Stitch.
        if ( event.type == 'LEFTMOUSE' and event.value == 'PRESS'):

            self._begin_stroke( context, event,)

            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._cleanup(context)


# FILL FACE TOOL
FILL_EDGE_PICK_RADIUS = 10.0
FILL_HOVER_COLOR = (1.0, 0.55, 0.05, 1.0)
FILL_FIRST_EDGE_COLOR = (1.0, 0.85, 0.15, 1.0)
FILL_EDGE_HIGHLIGHT_WIDTH = 3.0


# SCREEN SPACE EDGE PICKING
def _fill_point_segment_distance_squared(point, a, b):
    delta = b - a

    length_squared = delta.length_squared

    if length_squared <= 1e-12:
        return (point - a).length_squared

    t = point - a
    t = t.dot(delta) / length_squared
    t = max(0.0, min(1.0, t))

    closest = a + delta * t

    return (point - closest).length_squared


def _fill_pick_edge_index(context, mesh, cursor):
    """
    Find the closest visible projected boundary edge.

    Only the integer edge index leaves this function.
    No BMEdge reference is stored across modal events.
    """

    region = context.region
    space = context.space_data

    rv3d = (
        getattr(space, "region_3d", None)
        if space is not None
        else None
    )

    if region is None or rv3d is None:
        return None

    bm = bmesh.from_edit_mesh(mesh.data)

    bm.edges.ensure_lookup_table()
    bm.edges.index_update()

    world_matrix = mesh.matrix_world

    radius_squared = FILL_EDGE_PICK_RADIUS * FILL_EDGE_PICK_RADIUS

    best_edge_index = None
    best_distance_squared = radius_squared

    for edge in bm.edges:

        if not edge.is_valid:
            continue

        if edge.hide:
            continue

        # Fill is intentionally restricted to boundary edges.
        if not edge.is_boundary:
            continue

        v0 = edge.verts[0]
        v1 = edge.verts[1]

        if v0.hide or v1.hide:
            continue

        p0 = view3d_utils.location_3d_to_region_2d( region, rv3d, world_matrix @ v0.co,)
        p1 = view3d_utils.location_3d_to_region_2d( region, rv3d, world_matrix @ v1.co,)

        if p0 is None or p1 is None:
            continue

        distance_squared = _fill_point_segment_distance_squared( cursor, p0, p1,)

        if distance_squared < best_distance_squared:
            best_distance_squared = distance_squared
            best_edge_index = edge.index

    return best_edge_index


# SELECTION HELPERS
def _fill_clear_selection(bm):
    for vert in bm.verts:
        if vert.is_valid:
            vert.select = False

    for edge in bm.edges:
        if edge.is_valid:
            edge.select = False

    for face in bm.faces:
        if face.is_valid:
            face.select = False


def _fill_select_edge(bm, edge_index):
    bm.edges.ensure_lookup_table()

    if edge_index is None:
        return False

    if edge_index < 0 or edge_index >= len(bm.edges):
        return False

    edge = bm.edges[edge_index]

    if not edge.is_valid:
        return False

    _fill_clear_selection(bm)

    edge.select = True

    edge.verts[0].select = True
    edge.verts[1].select = True

    return True


def _fill_select_face(bm, face):
    if face is None or not face.is_valid:
        return

    _fill_clear_selection(bm)

    face.select = True

    for edge in face.edges:
        edge.select = True

    for vert in face.verts:
        vert.select = True


# EDGE HIGHLIGHT DRAWING
def _fill_draw_edge(operator, edge_index, color):
    if edge_index is None:
        return

    if operator.region is None:
        return

    if operator.rv3d is None:
        return

    bm = bmesh.from_edit_mesh(operator.mesh.data)

    bm.edges.ensure_lookup_table()

    if edge_index < 0 or edge_index >= len(bm.edges):
        return

    edge = bm.edges[edge_index]

    if not edge.is_valid:
        return

    world_matrix = operator.mesh.matrix_world

    p0 = view3d_utils.location_3d_to_region_2d( operator.region, operator.rv3d, world_matrix @ edge.verts[0].co,)
    p1 = view3d_utils.location_3d_to_region_2d( operator.region, operator.rv3d, world_matrix @ edge.verts[1].co,)

    if p0 is None or p1 is None:
        return

    positions = [ (p0.x, p0.y), (p1.x, p1.y), ]

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")

    batch = batch_for_shader( shader, "LINES", { "pos": positions, },)

    gpu.state.blend_set("ALPHA")

    try:
        gpu.state.line_width_set(FILL_EDGE_HIGHLIGHT_WIDTH)
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


def _draw_fill_edges(operator):
    if operator.first_edge is not None:
        _fill_draw_edge( operator, operator.first_edge, FILL_FIRST_EDGE_COLOR,)

    if ( operator.hover_edge is not None and operator.hover_edge != operator.first_edge):
        _fill_draw_edge( operator, operator.hover_edge, FILL_HOVER_COLOR,)


# FACE CREATION
def _fill_create_face(operator, first_edge_index, second_edge_index):
    """
    Create one quad between two boundary edges.

    The endpoint ordering is chosen by comparing the two possible
    pairings and selecting the one with the shortest side connections.
    """

    if first_edge_index is None or second_edge_index is None:
        return None

    if first_edge_index == second_edge_index:
        return None

    bm = bmesh.from_edit_mesh(operator.mesh.data)

    bm.edges.ensure_lookup_table()

    if first_edge_index < 0 or first_edge_index >= len(bm.edges):
        return None

    if second_edge_index < 0 or second_edge_index >= len(bm.edges):
        return None

    edge_a = bm.edges[first_edge_index]
    edge_b = bm.edges[second_edge_index]

    if not edge_a.is_valid or not edge_b.is_valid:
        return None

    # Both edges must remain boundary edges.
    if not edge_a.is_boundary or not edge_b.is_boundary:
        return None

    a0 = edge_a.verts[0]
    a1 = edge_a.verts[1]

    b0 = edge_b.verts[0]
    b1 = edge_b.verts[1]

    # The two edges must have four distinct endpoints.
    vertices = {a0, a1, b0, b1}

    if len(vertices) != 4:
        return None

    # Determine which orientation produces the shortest connecting edges.
    same_cost = ( (a0.co - b0.co).length_squared + (a1.co - b1.co).length_squared)
    cross_cost = ( (a0.co - b1.co).length_squared + (a1.co - b0.co).length_squared)

    if cross_cost < same_cost:
        b0, b1 = b1, b0

    try:
        face = bm.faces.new([ a0, a1, b1, b0, ])
    except ValueError:
        return None

    # Make sure the face normal field is valid.
    bmesh.ops.recalc_face_normals( bm, faces=[face],)
    bm.normal_update()

    # Orient the face toward the current viewport.
    if operator.rv3d is not None:
        normal_matrix = ( operator.mesh.matrix_world .to_3x3() .inverted() .transposed())

        world_normal = normal_matrix @ face.normal

        if world_normal.length > 1e-6:
            world_normal.normalize()

            view_direction = (
                operator.rv3d.view_rotation
                @ Vector((0.0, 0.0, -1.0))
            ).normalized()

            if world_normal.dot(view_direction) > 0.0:
                bmesh.ops.reverse_faces( bm, faces=[face],)

    bm.normal_update()

    _fill_select_face( bm, face,)

    bmesh.update_edit_mesh( operator.mesh.data, loop_triangles=True, destructive=True,)

    return face


# FILL FACE OPERATOR
class AllPie_OT_FillFace(Operator):

    bl_idname = "cop.fill_face"
    bl_label = "Fill Face"
    bl_description = "Select two boundary edges to create a quad face between them"

    # Do not use UNDO here.
    #
    # The modal operator stays alive while multiple faces are created.
    # We explicitly create one undo boundary before every face.

    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):

        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and is_retopo_edit_context(context)
        )

    # INVOKE
    def invoke(self, context, event):

        mesh = get_retopo_mesh(context)

        if mesh is None:
            self.report( {"WARNING"}, "Specify the mesh for retopology",)
            return {"CANCELLED"}

        if mesh.mode != "EDIT":
            self.report( {"WARNING"}, "Retopology mesh must be in Edit Mode",)
            return {"CANCELLED"}

        self.mesh = mesh

        self.area = context.area
        self.region = context.region
        self.rv3d = context.space_data.region_3d

        self.cursor = Vector((
            event.mouse_region_x,
            event.mouse_region_y,
        ))

        self.first_edge = None
        self.hover_edge = None

        self.previous_select_mode = tuple(
            context.scene.tool_settings.mesh_select_mode
        )

        self.selection_before = None

        bm = bmesh.from_edit_mesh(self.mesh.data)

        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()

        self.selection_before = {
            "verts": {
                vert.index
                for vert in bm.verts
                if vert.is_valid and vert.select
            },

            "edges": {
                edge.index
                for edge in bm.edges
                if edge.is_valid and edge.select
            },

            "faces": {
                face.index
                for face in bm.faces
                if face.is_valid and face.select
            },
        }

        self.created_faces = 0

        # Fill works in edge mode.
        bpy.ops.mesh.select_mode( type="EDGE")

        self.draw_handler = (
            bpy.types.SpaceView3D.draw_handler_add(
                _draw_fill_edges,
                (self,),
                "WINDOW",
                "POST_PIXEL",
            )
        )

        try:
            context.window.cursor_set("PAINT_BRUSH")
        except Exception:
            pass

        context.window_manager.modal_handler_add(self)

        self._update_hover(context)

        context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    # HOVER
    def _update_hover(self, context):

        self.hover_edge = _fill_pick_edge_index( context, self.mesh, self.cursor,)

        if self.area is not None:
            self.area.tag_redraw()

    # SELECT FIRST EDGE
    def _select_first_edge(self, edge_index):

        if edge_index is None:
            return False

        bm = bmesh.from_edit_mesh( self.mesh.data)
        success = _fill_select_edge( bm, edge_index,)

        if not success:
            return False

        bmesh.update_edit_mesh( self.mesh.data, loop_triangles=False, destructive=False,)

        return True

    # CREATE FACE
    def _create_face(self, first_edge_index, second_edge_index):

        if first_edge_index is None:
            return False

        if second_edge_index is None:
            return False

        if first_edge_index == second_edge_index:
            return False

        # Push undo state BEFORE modifying topology.
        bpy.ops.ed.undo_push( message="Before Fill Face")

        face = _fill_create_face( self, first_edge_index, second_edge_index,)

        if face is None:
            # The mesh wasn't changed.
            #
            # The explicit undo boundary is harmless here and is preferable
            # to trying to manipulate Blender's undo stack manually.
            return False

        self.created_faces += 1

        return True

    # CLEANUP
    def _restore_selection_before_tool(self, context):

        if self.selection_before is None:
            return

        bm = bmesh.from_edit_mesh( self.mesh.data)

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        _fill_clear_selection(bm)

        for index in self.selection_before["verts"]:

            if 0 <= index < len(bm.verts):

                vert = bm.verts[index]

                if vert.is_valid:
                    vert.select = True

        for index in self.selection_before["edges"]:

            if 0 <= index < len(bm.edges):

                edge = bm.edges[index]

                if edge.is_valid:
                    edge.select = True

        for index in self.selection_before["faces"]:

            if 0 <= index < len(bm.faces):

                face = bm.faces[index]

                if face.is_valid:
                    face.select = True

        bmesh.update_edit_mesh( self.mesh.data, loop_triangles=False, destructive=False,)

    def _cleanup(self, context, restore_selection=False):

        if getattr(self, "draw_handler", None) is not None:

            try:
                bpy.types.SpaceView3D.draw_handler_remove( self.draw_handler, "WINDOW",)
            except Exception:
                pass

            self.draw_handler = None

        if restore_selection and self.created_faces == 0:
            try:
                self._restore_selection_before_tool( context)
            except Exception:
                pass

        try:
            context.scene.tool_settings.mesh_select_mode = ( self.previous_select_mode)
        except Exception:
            pass

        try:
            context.window.cursor_set("DEFAULT")
        except Exception:
            pass

        if self.area is not None:
            self.area.tag_redraw()

    # MODAL
    def modal(self, context, event):

        # EXIT
        if event.type == "ESC":

            self._cleanup( context, restore_selection=True,)
            _retopo_switch_to_tweak(context)

            return {"CANCELLED"}

        if event.type == "RIGHTMOUSE":

            self._cleanup( context, restore_selection=True,)

            return {"CANCELLED"}

        # VIEWPORT NAVIGATION
        if event.type == "MIDDLEMOUSE":
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE" and event.alt:
            return {"PASS_THROUGH"}

        # MOUSE MOVE
        if event.type in { "MOUSEMOVE", "INBETWEEN_MOUSEMOVE", }:

            self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))

            self._update_hover(context)

            return {"RUNNING_MODAL"}

        # LEFT CLICK
        if ( event.type == "LEFTMOUSE" and event.value == "PRESS"):

            if self.hover_edge is None:
                return {"RUNNING_MODAL"}

            clicked_edge = self.hover_edge

            # FIRST EDGE
            if self.first_edge is None:

                success = self._select_first_edge( clicked_edge)

                if success:
                    self.first_edge = clicked_edge
                    self.hover_edge = None

                    if self.area is not None:
                        self.area.tag_redraw()

                return {"RUNNING_MODAL"}

            # SAME EDGE
            if self.first_edge == clicked_edge:
                return {"RUNNING_MODAL"}

            # SECOND EDGE
            success = self._create_face( self.first_edge, clicked_edge,)

            if success:

                # Face creation succeeded.
                #
                # Reset for another fill.
                self.first_edge = None
                self.hover_edge = None

                if self.area is not None:
                    self.area.tag_redraw()

            else:

                self.report( {"WARNING"}, "Unable to create face between these edges",)

            return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}

    # CANCEL
    def cancel(self, context):

        self._cleanup( context, restore_selection=True,)


# EXTRUDE EDGE TOOL
EXTRUDE_EDGE_PICK_RADIUS = 10.0
EXTRUDE_EDGE_HIGHLIGHT_COLOR = ( 1.0, 0.55, 0.05, 1.0,)
EXTRUDE_EDGE_HIGHLIGHT_WIDTH = 3.0

# SCREEN SPACE PICKING
def _extrude_point_segment_distance_squared(point, a, b):
    delta = b - a

    length_squared = delta.length_squared

    if length_squared <= 1e-12:
        return (point - a).length_squared

    t = (point - a).dot(delta) / length_squared
    t = max(0.0, min(1.0, t))

    closest = a + delta * t

    return (point - closest).length_squared


def _extrude_pick_edge_index(context, mesh, cursor):
    """
    Find the closest visible boundary edge under the cursor.

    Only an integer edge index is returned.
    """

    region = context.region
    space = context.space_data

    rv3d = (
        getattr(space, "region_3d", None)
        if space is not None
        else None
    )

    if region is None:
        return None

    if rv3d is None:
        return None

    bm = bmesh.from_edit_mesh(mesh.data)

    bm.edges.ensure_lookup_table()
    bm.edges.index_update()

    world_matrix = mesh.matrix_world

    radius_squared = ( EXTRUDE_EDGE_PICK_RADIUS * EXTRUDE_EDGE_PICK_RADIUS)

    best_edge_index = None
    best_distance_squared = radius_squared

    for edge in bm.edges:

        if not edge.is_valid:
            continue

        if edge.hide:
            continue

        # Retopo extrusion is intentionally restricted
        # to boundary edges.
        if not edge.is_boundary:
            continue

        v0 = edge.verts[0]
        v1 = edge.verts[1]

        if v0.hide or v1.hide:
            continue

        p0 = view3d_utils.location_3d_to_region_2d( region, rv3d, world_matrix @ v0.co,)
        p1 = view3d_utils.location_3d_to_region_2d( region, rv3d, world_matrix @ v1.co,)

        if p0 is None:
            continue

        if p1 is None:
            continue

        distance_squared = ( _extrude_point_segment_distance_squared( cursor, p0, p1,))

        if distance_squared < best_distance_squared:

            best_distance_squared = distance_squared
            best_edge_index = edge.index

    return best_edge_index


# EDGE HIGHLIGHT
def _draw_extrude_edge(operator):
    edge_index = operator.hover_edge

    if edge_index is None:
        return

    if operator.region is None:
        return

    if operator.rv3d is None:
        return

    bm = bmesh.from_edit_mesh( operator.mesh.data)

    bm.edges.ensure_lookup_table()

    if edge_index < 0:
        return

    if edge_index >= len(bm.edges):
        return

    edge = bm.edges[edge_index]

    if not edge.is_valid:
        return

    world_matrix = operator.mesh.matrix_world

    p0 = view3d_utils.location_3d_to_region_2d( operator.region, operator.rv3d, world_matrix @ edge.verts[0].co,)
    p1 = view3d_utils.location_3d_to_region_2d( operator.region, operator.rv3d, world_matrix @ edge.verts[1].co,)

    if p0 is None:
        return

    if p1 is None:
        return

    positions = [ (p0.x, p0.y), (p1.x, p1.y), ]

    shader = gpu.shader.from_builtin( "UNIFORM_COLOR")

    batch = batch_for_shader( shader, "LINES", { "pos": positions, },)

    gpu.state.blend_set("ALPHA")

    try:
        gpu.state.line_width_set( EXTRUDE_EDGE_HIGHLIGHT_WIDTH)
    except Exception:
        pass

    shader.bind()

    shader.uniform_float( "color", EXTRUDE_EDGE_HIGHLIGHT_COLOR,)

    batch.draw(shader)

    try:
        gpu.state.line_width_set(1.0)
    except Exception:
        pass

    gpu.state.blend_set("NONE")


# EXTRUDE OPERATOR
class AllPie_OT_ExtrudeEdge(Operator):

    bl_idname = "cop.extrude_edge"
    bl_label = "Extrude Edge"
    bl_description = "Hover a boundary edge and drag to extrude it"
    # The outer operator stays alive while the user performs multiple extrusions.
    # The native Blender extrusion operator owns its individual undo step.
    bl_options = { "REGISTER", }

    # POLL
    @classmethod
    def poll(cls, context):

        return ( context.area is not None
            and context.area.type == "VIEW_3D"
            and is_retopo_edit_context(context)
        )

    # INVOKE
    def invoke(self, context, event):

        mesh = get_retopo_mesh(context)

        if mesh is None:

            self.report( {"WARNING"}, "Specify the mesh for retopology",)

            return {"CANCELLED"}

        if mesh.mode != "EDIT":

            self.report(
                {"WARNING"},
                "Retopology mesh must be in Edit Mode",
            )

            return {"CANCELLED"}

        self.mesh = mesh

        self.area = context.area
        self.region = context.region
        self.rv3d = context.space_data.region_3d

        self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))

        self.hover_edge = None

        self.extrude_active = False
        self.cancel_transform = False
        self.exit_to_tweak = False

        self.previous_select_mode = tuple( context.scene.tool_settings.mesh_select_mode)

        # Extrusion works from edge selection.
        bpy.ops.mesh.select_mode( type="EDGE")

        # Draw hover edge.
        self.draw_handler = (
            bpy.types.SpaceView3D.draw_handler_add(
                _draw_extrude_edge,
                (self,),
                "WINDOW",
                "POST_PIXEL",
            )
        )

        try:
            context.window.cursor_set( "PAINT_BRUSH")
        except Exception:
            pass

        context.window_manager.modal_handler_add( self)

        self._update_hover(context)

        if self.area is not None:
            self.area.tag_redraw()

        return {"RUNNING_MODAL"}

    # HOVER UPDATE
    def _update_hover(self, context):

        # Don't run our custom hover picker while
        # native extrusion is controlling the mouse.

        if self.extrude_active:
            return

        self.hover_edge = ( _extrude_pick_edge_index( context, self.mesh, self.cursor,))

        if self.area is not None:
            self.area.tag_redraw()

    # SELECT EDGE
    def _select_edge(self, edge_index):

        if edge_index is None:
            return False

        bm = bmesh.from_edit_mesh( self.mesh.data)

        bm.edges.ensure_lookup_table()

        if edge_index < 0:
            return False

        if edge_index >= len(bm.edges):
            return False

        edge = bm.edges[edge_index]

        if not edge.is_valid:
            return False

        if not edge.is_boundary:
            return False

        # Clear selection.
        for vert in bm.verts:

            if vert.is_valid:
                vert.select = False

        for selected_edge in bm.edges:

            if selected_edge.is_valid:
                selected_edge.select = False

        for face in bm.faces:

            if face.is_valid:
                face.select = False

        # Select the source edge.
        edge.select = True

        edge.verts[0].select = True
        edge.verts[1].select = True

        bmesh.update_edit_mesh( self.mesh.data, loop_triangles=False, destructive=False,)

        return True

    # START NATIVE EXTRUDE
    def _begin_extrude(self, context):

        edge_index = self.hover_edge

        if edge_index is None:
            return False

        # Make sure the selected edge is still valid.
        bm = bmesh.from_edit_mesh( self.mesh.data)

        bm.edges.ensure_lookup_table()

        if edge_index < 0:
            return False

        if edge_index >= len(bm.edges):
            return False

        edge = bm.edges[edge_index]

        if not edge.is_valid:
            return False

        if not edge.is_boundary:
            return False

        if not self._select_edge(edge_index):
            return False

        self.cancel_transform = False
        self.exit_to_tweak = False

        try:

            with context.temp_override(
                window=context.window,
                screen=context.screen,
                area=self.area,
                region=self.region,
                space_data=context.space_data,
                active_object=self.mesh,
                object=self.mesh,
            ):

                result = ( bpy.ops.mesh.extrude_edges_move( "INVOKE_DEFAULT"))

        except RuntimeError as error:

            self.report( {"WARNING"}, f"Extrude failed: {error}",)

            return False

        if "CANCELLED" in result:

            return False

        # Native operator is now responsible for the extrusion + translation gesture.
        self.extrude_active = True

        self.hover_edge = None

        if self.area is not None:
            self.area.tag_redraw()

        return True

    # DETECT NATIVE EXTRUDE / TRANSFORM
    def _is_extrude_running(self, context):

        try:

            for operator in context.window.modal_operators:

                if operator.bl_idname in {
                    "MESH_OT_EXTRUDE_EDGES_MOVE",
                    "TRANSFORM_OT_TRANSLATE",
                }:
                    return True

        except Exception:
            pass

        return False

    # FINISH EXTRUSION
    def _finish_extrude(self, context):

        # A cancelled native transform should not
        # be treated as a completed extrusion.
        if self.cancel_transform:

            self.extrude_active = False
            self.cancel_transform = False
            self.hover_edge = None

            if self.area is not None:
                self.area.tag_redraw()

            return

        # Native Blender extrusion has finished.
        # The newly extruded edge should already be selected

        self.extrude_active = False

        self.cancel_transform = False
        self.hover_edge = None

        # Refresh BMesh state.
        try:

            bm = bmesh.from_edit_mesh( self.mesh.data)

            bm.normal_update()

            bmesh.update_edit_mesh( self.mesh.data, loop_triangles=True, destructive=True,)

        except Exception:
            pass

        if self.area is not None:
            self.area.tag_redraw()

    # CLEANUP
    def _cleanup(self, context):

        if getattr( self, "draw_handler", None,) is not None:

            try:

                bpy.types.SpaceView3D.draw_handler_remove( self.draw_handler, "WINDOW",)

            except Exception:
                pass

            self.draw_handler = None

        # Restore previous mesh selection mode.
        try:

            context.scene.tool_settings.mesh_select_mode = ( self.previous_select_mode)

        except Exception:
            pass

        # Restore cursor.
        try:
            context.window.cursor_set( "DEFAULT")

        except Exception:
            pass

        if self.area is not None:
            self.area.tag_redraw()

    # MODAL
    def modal(self, context, event):

        # NATIVE EXTRUSION IS ACTIVE
        if self.extrude_active:

            # ESC cancels the native extrusion and exits Extrude.
            if event.type == "ESC":
                self.cancel_transform = True
                self.exit_to_tweak = True

            # RMB cancels the native extrusion but keeps Extrude active.
            elif event.type == "RIGHTMOUSE":
                self.cancel_transform = True

            if self._is_extrude_running( context):

                return {"PASS_THROUGH"}

            should_exit = self.exit_to_tweak

            # Native extrusion has ended.
            self._finish_extrude(context)

            if should_exit:
                self._cleanup(context)
                self.exit_to_tweak = False
                _retopo_switch_to_tweak(context)
                return {"CANCELLED"}

            return {"RUNNING_MODAL"}

        # EXIT TOOL
        if event.type == "ESC":

            self._cleanup(context)
            _retopo_switch_to_tweak(context)

            return {"CANCELLED"}

        if event.type == "RIGHTMOUSE":

            self._cleanup(context)

            return {"CANCELLED"}

        # VIEWPORT NAVIGATION
        if event.type == "MIDDLEMOUSE":

            return {"PASS_THROUGH"}

        if ( event.type == "LEFTMOUSE" and event.alt):

            return {"PASS_THROUGH"}

        # MOUSE MOVE
        if event.type in { "MOUSEMOVE", "INBETWEEN_MOUSEMOVE", }:

            self.cursor = Vector(( event.mouse_region_x, event.mouse_region_y,))

            self._update_hover(context)

            return {"RUNNING_MODAL"}

        # LEFT CLICK
        if ( event.type == "LEFTMOUSE" and event.value == "PRESS"):

            if self.hover_edge is None:
                return {"RUNNING_MODAL"}

            # Start extrusion.
            self._begin_extrude( context)

            return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}

    # CANCEL
    def cancel(self, context):

        self._cleanup(context)


classes = (
    RetopoGuidePoint,
    RetopoGuideSplineState,
    RetopoSettings,
    AllPie_OT_InitRetopo,
    AllPie_OT_AddStrips,
    AllPie_OT_RelaxTopology,
    AllPie_OT_StitchTopology,
    AllPie_OT_FillFace,
    AllPie_OT_ExtrudeEdge,
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
