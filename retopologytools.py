from dataclasses import dataclass, field

import bpy
import bmesh
from mathutils import Vector
from bpy.props import (CollectionProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty,)
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

classes = (
    RetopoGuidePoint,
    RetopoGuideSplineState,
    RetopoSettings,
    AllPie_OT_InitRetopo,
    AllPie_OT_AddSurface,
    AllPie_OT_SculptRelaxSlide,
    AllPie_OT_ToggleAutoMerge,
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
