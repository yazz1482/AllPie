from dataclasses import dataclass, field

import bpy
import bmesh
import gpu
from gpu_extras.presets import draw_circle_2d
from bpy_extras import view3d_utils
from mathutils import Vector
from bpy.props import (CollectionProperty,FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty,)
from bpy.types import ( Operator, PropertyGroup,)

# Retopology mesh helper
def get_retopo_mesh(context):
    mesh = context.scene.retopo.mesh
    if mesh is None or mesh.type != "MESH":
        return None
    return mesh

# Returns the active annotation data.
def get_active_annotation_data(context):
    """Return the active Scene annotation layer without relying on UI context."""
    annotation_data = getattr(context.scene, "annotation", None)
    if annotation_data is None:
        return None

    layers = annotation_data.layers
    if not layers:
        return None

    index = layers.active_index
    if index < 0 or index >= len(layers):
        return None

    return layers[index]

# Removes the active annotation data.
def clear_active_annotation_strokes(context):
    """Remove strokes from the active annotation frame without removing the layer."""
    annotation_data = getattr(context.scene, "annotation", None)
    layer = get_active_annotation_data(context)

    if annotation_data is None or layer is None:
        return False

    frame = layer.active_frame
    if frame is None:
        return False

    layer.frames.remove(frame)
    return True

@dataclass
class RetopoGuideSpline:
    points: list[Vector] = field(default_factory=list)


@dataclass
class RetopoGuide:
    source: str = "ANNOTATION"
    splines: list[RetopoGuideSpline] = field(default_factory=list)


class RetopoGuidePoint(PropertyGroup):
    co: FloatVectorProperty(size=3, subtype='XYZ')


class RetopoGuideSplineState(PropertyGroup):
    points: CollectionProperty(type=RetopoGuidePoint)


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
    guide = RetopoGuide(source=settings.guide_source or "ANNOTATION")
    for spline_state in settings.guide_splines:
        points = [Vector(point_state.co) for point_state in spline_state.points]
        if len(points) >= 2:
            guide.splines.append( RetopoGuideSpline(points=points))
    return guide if guide.splines else None


def get_annotation_strokes(context):
    """Return strokes from the active scene annotation layer/frame."""
    try:
        layer = get_active_annotation_data(context)
        if layer is None or layer.active_frame is None:
            return []
        return list(layer.active_frame.strokes)
    except (AttributeError, IndexError, TypeError, RuntimeError):
        return []

def capture_annotation_guide(context):
    """Capture annotation geometry into AllPie's runtime guide representation."""
    guide = RetopoGuide()

    for stroke in get_annotation_strokes(context):
        points = [ Vector((point.co.x, point.co.y, point.co.z)) for point in stroke.points ]

        if len(points) < 2:
            continue

        guide.splines.append(RetopoGuideSpline(points=points))

    return guide if guide.splines else None


def is_retopo_edit_context(context):
    """Return True when the registered retopo mesh is currently in Edit Mode."""
    mesh = get_retopo_mesh(context)
    return mesh is not None and mesh.type == 'MESH' and mesh.mode == 'EDIT'


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
    # For a retopo surface created from screen-space annotations, orient the
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

# Add surface operator
class AllPie_OT_AddSurface(Operator):
    bl_idname = "cop.add_surface"
    bl_label = "Add Surface"
    bl_description = "Generate a retopology surface from annotation guides"
    bl_options = {'REGISTER', 'UNDO'}

    across_count: IntProperty(
        name="Across",
        description="Number of rows between neighboring guide strokes",
        default=5,
        min=1,
        max=200,
    )
    along_count: IntProperty(
        name="Along",
        description="Number of segments along each guide stroke",
        default=8,
        min=1,
        max=200,
    )
    @classmethod
    def poll(cls, context):
        # Use the registered retopo mesh instead of popup context fields.
        mesh = get_retopo_mesh(context)
        return mesh is not None and mesh.type == 'MESH' and mesh.mode == 'EDIT'

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "across_count")
        layout.prop(self, "along_count")

    def execute(self, context):
        mesh = get_retopo_mesh(context)
        if mesh is None:
            self.report({'WARNING'}, "Specify the mesh for retopology")
            return {'CANCELLED'}

        if not is_retopo_edit_context(context):
            self.report({'WARNING'}, "Retopology must be initialized in Edit Mode")
            return {'CANCELLED'}

        retopo_settings = context.scene.retopo

        # A fresh annotation replaces the previous stored guide. If there is
        # no fresh annotation, keep the stored guide so the operator can still
        # be re-executed from Blender's redo panel.
        current_guide = capture_annotation_guide(context)
        if current_guide is not None:
            store_guide_state(retopo_settings, current_guide)

        guide = load_guide_state(retopo_settings)
        if guide is None:
            self.report({'WARNING'}, "Draw a retopology guide")
            return {'CANCELLED'}
        guide_analysis = analyze_guide(guide)

        if len(guide_analysis.splines) < 2:
            self.report({'WARNING'}, "At least two guide strokes are required")
            return {'CANCELLED'}

        settings = SurfaceGenerationSettings(
            across_count=self.across_count,
            along_count=self.along_count,
        )

        patch = generate_surface(guide_analysis, settings)
        if patch is None:
            self.report({'WARNING'}, "Unable to generate a surface from the guides")
            return {'CANCELLED'}

        if not commit_surface(context, mesh, patch):
            self.report({'WARNING'}, "Generated surface is empty")
            return {'CANCELLED'}

        clear_active_annotation_strokes(context)

        retopo_settings.across_count = self.across_count
        retopo_settings.along_count = self.along_count

        return {'FINISHED'}

    def invoke(self, context, event):
        mesh = get_retopo_mesh(context)
        if mesh is None:
            self.report({'WARNING'}, "Specify the mesh for retopology")
            return {'CANCELLED'}

        settings = context.scene.retopo
        self.across_count = settings.across_count
        self.along_count = settings.along_count

        return self.execute(context)


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
        context.scene.retopo.guide_splines.clear()

        tool_settings = context.scene.tool_settings

        # Viewport display
        obj.display_type = "SOLID"
        obj.show_wire = True
        obj.show_all_edges = True

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

        # Auto Merge
        tool_settings.use_mesh_automerge = True
        tool_settings.double_threshold = 0.01

        # Shrinkwrap: create/configure it, but never assign its target.
        shrinkwrap = next(
            (mod for mod in obj.modifiers if mod.type == "SHRINKWRAP"),
            None,
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

        # Leave the user ready to draw retopology guides.
        bpy.ops.wm.tool_set_by_id(name="builtin.annotate")
        tool_settings.annotation_stroke_placement_view3d = "SURFACE"

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
    guide_source: StringProperty(options={'HIDDEN'})
    guide_splines: CollectionProperty(type=RetopoGuideSplineState)
    mesh: PointerProperty(
        name="Retopo Mesh",
        type=bpy.types.Object,
        description="Mesh used for retopology",
    )


class AllPie_OT_SculptRelaxSlide(Operator):
    bl_idname = "cop.sculpt_relax_slide"
    bl_label = "Sculpt Relax Slide"
    bl_description = "Enter Sculpt Mode and activate the Relax Slide brush"

    @classmethod
    def poll(cls, context):
        mesh = get_retopo_mesh(context)
        return mesh is not None and mesh.type == "MESH"

    def execute(self, context):
        mesh = get_retopo_mesh(context)
        if mesh is None:
            self.report({"WARNING"}, "Specify the mesh for retopology")
            return {"CANCELLED"}

        if context.object is not mesh:
            if context.object is not None and context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            for obj in context.selected_objects:
                obj.select_set(False)
            mesh.select_set(True)
            context.view_layer.objects.active = mesh

        if mesh.mode != "SCULPT":
            if mesh.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.objects.active = mesh
            mesh.select_set(True)
            bpy.ops.object.mode_set(mode="SCULPT")

        result = bpy.ops.brush.asset_activate(
            asset_library_type="ESSENTIALS",
            asset_library_identifier="",
            relative_asset_identifier=(
                "brushes/essentials_brushes-mesh_sculpt.blend/Brush/Relax Slide"
            ),
        )

        if 'FINISHED' not in result:
            self.report({"WARNING"}, "Unable to activate the Relax Slide brush")
            return {"CANCELLED"}

        return {"FINISHED"}

class AllPie_OT_ToggleAutoMerge(Operator):
    bl_idname = "cop.toggle_auto_merge"
    bl_label = "Toggle Auto Merge"
    bl_description = "Toggle Blender's mesh auto merge setting for retopology"

    @classmethod
    def poll(cls, context):
        return is_retopo_edit_context(context)

    def execute(self, context):
        tool_settings = context.scene.tool_settings
        tool_settings.use_mesh_automerge = not tool_settings.use_mesh_automerge
        return {"FINISHED"}

# ============================================================
# Blender topology-relax algorithm, adapted for Edit Mode BMesh.
#
# Based on Blender's topology-relax step:
#   - corners (<= 2 neighbors) are not modified
#   - boundary vertices use boundary neighbors
#   - neighbor positions are averaged
#   - smoothed position is projected onto the vertex tangent plane
#   - result is scaled by brush factor
#   - Relax Slide alternate path performs 4 passes
#
# Intentionally omitted:
#   - automasking
#   - texture
#   - face sets
#   - symmetry
#   - PBVH
#   - sculpt masks
#   - SculptSession-specific machinery
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

        if not vert.is_valid:
            continue

        if factor <= 0.0:
            continue

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
            (
                positions[neighbor]
                for neighbor in neighbors
                if neighbor in positions
            ),
            Vector((0.0, 0.0, 0.0)),
        )

        valid_neighbor_count = sum(
            1
            for neighbor in neighbors
            if neighbor in positions
        )

        if valid_neighbor_count == 0:
            continue

        smooth_position /= valid_neighbor_count

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

    moved = 0

    for _ in range(4):
        moved += _relax_topology_pass( bm, factors,)

    return moved

def _draw_relax_brush(operator):
    if operator.cursor is None:
        return

    # Blender's radial brush-size control keeps the brush preview anchored
    # at the position where F was pressed while the mouse is dragged.
    if getattr(operator, "resize_active", False):
        center = operator.resize_center
    else:
        center = operator.cursor

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

    radius: FloatProperty(
        name="Radius",
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
        if getattr(self, "draw_handler", None) is not None:
            bpy.types.SpaceView3D.draw_handler_remove( self.draw_handler, "WINDOW",)
            self.draw_handler = None

        if getattr(self, "modal_cursor_active", False):
            try:
                context.window.cursor_modal_restore()
            except RuntimeError:
                pass
            self.modal_cursor_active = False

        if context.area:
            context.area.tag_redraw()

    def _start_view_navigation(self, context, event):
        """Start Blender's native View3D navigation operator."""
        try:
            if event.shift and event.ctrl:
                result = bpy.ops.view3d.dolly( "INVOKE_DEFAULT", use_cursor_init=True,)
            elif event.ctrl:
                result = bpy.ops.view3d.zoom( "INVOKE_DEFAULT", use_cursor_init=True,)
            elif event.shift:
                result = bpy.ops.view3d.move( "INVOKE_DEFAULT", use_cursor_init=True,)
            else:
                result = bpy.ops.view3d.rotate( "INVOKE_DEFAULT", use_cursor_init=True,)
        except RuntimeError:
            return False

        return "RUNNING_MODAL" in result

    # ------------------------------------------------------------------
    # Stroke
    # ------------------------------------------------------------------

    def invoke(self, context, event):
        mesh = get_retopo_mesh(context)

        if mesh is None:
            self.report(
                {"WARNING"},
                "Specify the mesh for retopology",
            )
            return {"CANCELLED"}

        self.mesh = mesh

        self.stroke_active = False
        self.stroke_changed = False
        self.modal_cursor_active = False

        # Blender-style F brush-size control state.
        self.resize_active = False
        self.resize_center = Vector(( event.mouse_region_x, event.mouse_region_y,))
        self.resize_start_mouse = self.resize_center.copy()
        self.resize_start_radius = self.radius

        self.last_mouse = Vector(( event.mouse_region_x, event.mouse_region_y,))

        self.cursor = self.last_mouse.copy()

        self.last_pressure = 1.0
        self.distance_since_dab = 0.0

        self.stroke_backup = {}

        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                _draw_relax_brush,
                (self,),
                "WINDOW",
                "POST_PIXEL",
                )

        context.window_manager.modal_handler_add(self)

        # Override the active tool's cursor for the lifetime of this modal
        # operator. The Annotation tool can otherwise restore its Pencil
        # cursor whenever the mouse moves.
        try:
            context.window.cursor_modal_set("PAINT_BRUSH")
            self.modal_cursor_active = True
        except RuntimeError:
            context.window.cursor_set("PAINT_BRUSH")

        context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    def _get_spacing_pixels(self):
        return max( 2.0, self.radius * self.spacing,)

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

    # ------------------------------------------------------------------
    # Dab
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Stroke begin/end
    # ------------------------------------------------------------------

    def _begin_stroke(self, context, event):
        self.stroke_active = True

        self.last_mouse = Vector(( event.mouse_region_x, event.mouse_region_y,))

        self.last_pressure = ( getattr(event, "pressure", 1.0) or 1.0)

        self.distance_since_dab = 0.0

        self.stroke_changed = False
        self._capture_stroke_backup()

        # First dab happens immediately.
        changed = self._apply_dab( context, self.last_mouse, self.last_pressure,)

        if changed:
            self.stroke_changed = True

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
        self.distance_since_dab = 0.0
        self.stroke_backup.clear()

    # ------------------------------------------------------------------
    # Stroke interpolation
    # ------------------------------------------------------------------

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

        spacing = self._get_spacing_pixels()

        remaining = segment_length
        travelled = 0.0
        current_position = start.copy()

        start_pressure = self.last_pressure

        while True:
            distance_to_dab = (
                spacing
                - self.distance_since_dab
            )

            if remaining + EPSILON < distance_to_dab:
                self.distance_since_dab += remaining
                break

            current_position += ( direction * distance_to_dab)

            remaining -= distance_to_dab
            travelled += distance_to_dab

            t = travelled / segment_length

            dab_pressure = ( start_pressure + (pressure - start_pressure) * t)

            changed = self._apply_dab( context, current_position, dab_pressure,)

            if changed:
                self.stroke_changed = True

            self.distance_since_dab = 0.0

        self.last_mouse = end
        self.last_pressure = pressure

    # ------------------------------------------------------------------
    # Brush size control (Blender F behavior)
    # ------------------------------------------------------------------

    def _begin_radius_resize(self, event):
        self.resize_active = True
        self.resize_center = Vector(( event.mouse_region_x, event.mouse_region_y,))
        self.resize_start_mouse = self.resize_center.copy()
        self.resize_start_radius = self.radius

    def _update_radius_resize(self, event):
        mouse_x = event.mouse_region_x
        start_x = self.resize_start_mouse.x

        # Blender's WM_OT_radial_control uses the horizontal mouse travel for
        # pixel brush size: moving right increases size and moving left
        # decreases it. The initial size is preserved at the starting point.
        delta_x = mouse_x - start_x

        self.radius = max( 5.0, min( 500.0, self.resize_start_radius + delta_x,),)

    def _cancel_radius_resize(self):
        self.radius = self.resize_start_radius
        self.resize_active = False

    def _confirm_radius_resize(self):
        self.resize_active = False

    # ------------------------------------------------------------------
    # Modal
    # ------------------------------------------------------------------

    def modal(self, context, event):

        # --------------------------------------------------------------
        # Blender-style F brush radius control.
        # --------------------------------------------------------------

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
                self._confirm_radius_resize()
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            if event.type in {"ESC", "RIGHTMOUSE"}:
                self._cancel_radius_resize()
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            return {"RUNNING_MODAL"}

        # --------------------------------------------------------------
        # Cancel current stroke / operator
        # --------------------------------------------------------------

        if event.type == "ESC":
            if self.stroke_active:
                self._cancel_stroke()

            self._remove_draw_handler(context)
            context.window.cursor_set("DEFAULT")
            context.area.tag_redraw()

            return {"CANCELLED"}

        if event.type == "RIGHTMOUSE":
            if self.stroke_active:
                self._cancel_stroke()
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            self._remove_draw_handler(context)

            context.window.cursor_set("DEFAULT")
            return {"CANCELLED"}

        # --------------------------------------------------------------
        # Viewport navigation
        #
        # Launch Blender's native navigation operator as a nested modal
        # operation. We deliberately do not keep a local navigation state:
        # the native operator owns the navigation gesture and returns control
        # to this brush modal when it finishes. This is important because
        # otherwise our brush would stop receiving MOUSEMOVE events after
        # an Alt+LMB / emulated-MMB navigation gesture.
        # --------------------------------------------------------------

        if event.type == "MIDDLEMOUSE" and event.value == "PRESS":
            self._start_view_navigation(context, event)
            return {"RUNNING_MODAL"}

        # Fallback for systems where Alt+LMB reaches this modal directly
        # instead of being converted to MIDDLEMOUSE by Emulate 3 Button Mouse.
        if ( event.type == "LEFTMOUSE" and event.alt and event.value == "PRESS"):
            self._start_view_navigation(context, event)
            return {"RUNNING_MODAL"}

        # --------------------------------------------------------------
        # Mouse movement
        # --------------------------------------------------------------

        if event.type in { "MOUSEMOVE", "INBETWEEN_MOUSEMOVE", }:

            mouse_position = Vector(( event.mouse_region_x, event.mouse_region_y,))

            self.cursor = mouse_position

            pressure = ( getattr(event, "pressure", 1.0) or self.last_pressure)

            if self.stroke_active:
                self._process_mouse_segment( context, mouse_position, max(0.0, min(1.0, pressure)),)
            else:
                self.last_mouse = mouse_position
                self.last_pressure = pressure

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # --------------------------------------------------------------
        # Stroke begin/end
        # --------------------------------------------------------------

        if event.type == "LEFTMOUSE":

            if event.value == "PRESS":
                self._begin_stroke( context, event,)

                return {"RUNNING_MODAL"}

            if event.value == "RELEASE":
                self._end_stroke()

                context.area.tag_redraw()

                return {"RUNNING_MODAL"}

        # --------------------------------------------------------------
        # Radius
        # --------------------------------------------------------------

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
    AllPie_OT_AddSurface,
    AllPie_OT_SculptRelaxSlide,
    AllPie_OT_ToggleAutoMerge,
    AllPie_OT_RelaxTopology,
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
