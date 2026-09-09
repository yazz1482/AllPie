import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy.props import FloatProperty
from bpy.props import BoolProperty
from bpy.props import IntProperty
from bpy.props import EnumProperty

class AllPie_OT_Symmetry(Operator):
    bl_idname = "cop.symmetry"
    bl_label = "Symmetry Pie"

    action: EnumProperty(
        name="Action",
        items=[
            ("Toggle_X", "Toggle_X", ""),
            ("Toggle_Y", "Toggle_Y", ""),
            ("Toggle_Z", "Toggle_Z", ""),
            ("Flip_X", "Flip_X", ""),
            ("Flip_Y", "Flip_Y", ""),
            ("Flip_Z", "Flip_Z", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and context.object.type == 'MESH'
            and context.mode == 'SCULPT'
        )

    def execute(self, context):

        currentmirrorx = context.object.data.use_mirror_x
        currentmirrory = context.object.data.use_mirror_y
        currentmirrorz = context.object.data.use_mirror_z
        symmetrydirection = context.scene.tool_settings.sculpt.symmetrize_direction

        if self.action == "Toggle_X":
            if currentmirrorx == True:
                context.object.data.use_mirror_x = False
            else:
                context.object.data.use_mirror_x = True

        elif self.action == "Toggle_Y":
            if currentmirrory == True:
                context.object.data.use_mirror_y = False
            else:
                context.object.data.use_mirror_y = True
   
        elif self.action == "Toggle_Z":
            if currentmirrorz == True:
                context.object.data.use_mirror_z = False
            else:
                context.object.data.use_mirror_z = True

        elif self.action == "Flip_X":
            if symmetrydirection == "NEGATIVE_X":
                context.scene.tool_settings.sculpt.symmetrize_direction = "POSITIVE_X"
            else:
                context.scene.tool_settings.sculpt.symmetrize_direction = "NEGATIVE_X"

        elif self.action == "Flip_Y":
            if symmetrydirection == "NEGATIVE_Y":
                context.scene.tool_settings.sculpt.symmetrize_direction = "POSITIVE_Y"
            else:
                context.scene.tool_settings.sculpt.symmetrize_direction = "NEGATIVE_Y"

        elif self.action == "Flip_Z":
            if symmetrydirection == "NEGATIVE_Z":
                context.scene.tool_settings.sculpt.symmetrize_direction = "POSITIVE_Z"
            else:
                context.scene.tool_settings.sculpt.symmetrize_direction = "NEGATIVE_Z"

        return {"FINISHED"}


class AllPie_OT_Remesh(Operator):
    bl_idname = "cop.cremesh"
    bl_label = "Remesh Operator"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    action: EnumProperty(
        name="Action",
        items=[
            ("IncreaseVoxelSize10", "IncreaseVoxelSize10", ""),
            ("IncreaseVoxelSize25", "IncreaseVoxelSize25", ""),
            ("DecreaseVoxelSize25", "DecreaseVoxelSize25", ""),
            ("DecreaseVoxelSize10", "DecreaseVoxelSize10", ""),
        ],
    )

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        if obj.type != 'MESH':
            self.report({"WARNING"}, "Active object must be a mesh")
            return {"CANCELLED"}

        CurrentVoxelSize = round(obj.data.remesh_voxel_size, 3)

        if self.action == "DecreaseVoxelSize10":
            DecreasedVoxelSize = round(CurrentVoxelSize * 0.9, 3)
            bpy.context.object.data.remesh_voxel_size = DecreasedVoxelSize

        elif self.action == "DecreaseVoxelSize25":
            DecreasedVoxelSize = round(CurrentVoxelSize * 0.75, 3)
            bpy.context.object.data.remesh_voxel_size = DecreasedVoxelSize

        elif self.action == "IncreaseVoxelSize10":
            IncreasedVoxelSize = round(CurrentVoxelSize * 1.1, 3)
            bpy.context.object.data.remesh_voxel_size = IncreasedVoxelSize

        elif self.action == "IncreaseVoxelSize25":
            IncreasedVoxelSize = round(CurrentVoxelSize * 1.25, 3)
            bpy.context.object.data.remesh_voxel_size = IncreasedVoxelSize

        return {"FINISHED"}


class AllPie_OT_Shading(Operator):
    bl_idname = "cop.cshading"
    bl_label = "Shading Operator"

    SetShading: EnumProperty(
        name="SetShading",
        items=[
            ("SOLID", "SOLID", ""),
            ("WIREFRAME", "WIREFRAME", ""),
            ("RENDERED", "RENDERED", ""),
            ("MATERIAL", "MATERIAL", ""),
        ],
    )
    SetShadingLight: EnumProperty(
        name="SetShadingLight",
        items=[
            ("MATCAP", "MATCAP", ""),
            ("STUDIO", "STUDIO", ""),
            ("FLAT", "FLAT", ""),
        ],
    )

    def execute(self, context):

        bpy.context.space_data.shading.type = self.SetShading
        bpy.context.space_data.shading.light = self.SetShadingLight
        return {"FINISHED"}

class AllPie_OT_MultiRes(Operator):
    bl_idname = "cop.cmultirespie"
    bl_label = "MultiRes Pie"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    action: EnumProperty(
        name="Action",
        items=[
            ("MultiresSubdivide", "MultiresSubdivide", ""),
            ("IncreaseSculptLevel", "IncreaseSculptLevel", ""),
            ("DecreaseSculptLevel", "DecreaseSculptLevel", ""),
            ("SculptLevelToViewport", "SculptLevelToViewport", ""),
            ("SculptLevelToRender", "SculptLevelToRender", ""),
            ("DeleteHigher", "DeleteHigher", ""),
            ("ConformToBase", "ApplyToBase", ""),
            ("MaxSculptLevel", "MaxSculptLevel", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        obj = context.object

        return (
            obj is not None
            and obj.type == 'MESH'
            and "Multires" in obj.modifiers
        )

    def execute(self, context):
        obj = context.object

        # Safety checks
        if obj is None:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        if obj.type != 'MESH':
            self.report({"WARNING"}, "Active object must be a mesh")
            return {"CANCELLED"}

        multires = obj.modifiers.get("Multires")

        if multires is None:
            self.report({"WARNING"}, "Active object has no Multires modifier")
            return {"CANCELLED"}

        current_sculpt_level = multires.sculpt_levels

        if self.action == "MultiresSubdivide":
            bpy.ops.object.multires_subdivide(
                modifier="Multires",
                mode="CATMULL_CLARK",
            )

        elif self.action == "IncreaseSculptLevel":
            if current_sculpt_level < multires.total_levels:
                multires.sculpt_levels = current_sculpt_level + 1

        elif self.action == "DecreaseSculptLevel":
            if current_sculpt_level > 0:
                multires.sculpt_levels = current_sculpt_level - 1

        elif self.action == "SculptLevelToViewport":
            multires.levels = current_sculpt_level

        elif self.action == "SculptLevelToRender":
            multires.render_levels = current_sculpt_level

        elif self.action == "DeleteHigher":
            bpy.ops.object.multires_higher_levels_delete(
                modifier="Multires"
            )

        elif self.action == "ConformToBase":
            bpy.ops.object.multires_base_apply(
                modifier="Multires",
                apply_heuristic=False,
            )

        elif self.action == "MaxSculptLevel":
            multires.sculpt_levels = multires.total_levels

        return {"FINISHED"}



class AllPie_OT_ColorSelectorPopup(Operator):
    bl_idname = "cop.color_selector_popup"
    bl_label = "Brush Color"

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        layout = self.layout

        brush = bpy.context.scene.tool_settings.sculpt.unified_paint_settings
        # layout.template_color_picker(brush, "color", value_slider=True)
        layout.prop( brush, "color", text="")
        layout.operator("paint.brush_colors_flip", text="Swap Colors")
        layout.operator("palette.new", text="Add Palete")
        paint = context.tool_settings.sculpt
        layout.template_ID(
            paint,
            "palette",
            new="palette.new",
        )
        layout.template_palette(paint, "palette")

    def execute(self, context):
        return {"FINISHED"}


class AllPie_OT_CustomQuadriFlow(Operator):
    """Quadriflow remesher with some custom settings"""

    bl_label = "QuadRiflow Remesh Custom"
    bl_idname = "cop.customquadriflow"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    UseMeshSymmetry: BoolProperty(default=False)
    PreserveAttributes: BoolProperty(default=False)
    SmoothenNormals: BoolProperty(default=False)
    EnableProject: BoolProperty(default=False)
    TargetFaceCount: IntProperty(name="Faces", default=2000)

    def draw(self, context):
        layout = self.layout
        layout.label(text="QuadRiflow Settings")
        layout.prop(self, "TargetFaceCount", text="Face Count")
        layout.prop(self, "UseMeshSymmetry", text="Use Mesh Symmetry")
        layout.prop(self, "PreserveAttributes", text="Preserve Attributes")
        layout.prop(self, "SmoothenNormals", text="Smoothen Normals")
        layout.prop(self, "EnableProject", text="Enable Project")

    def execute(self, context):

        obj = context.object
        if obj is None:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        if obj.type != 'MESH':
            self.report({"WARNING"}, "Active object must be a mesh")
            return {"CANCELLED"}

        TargetFaceCount = self.TargetFaceCount
        UseMeshSymmetry = self.UseMeshSymmetry
        PreserveAttributes = self.PreserveAttributes
        SmoothenNormals = self.SmoothenNormals
        EnableProject = self.EnableProject
        obj = bpy.context.object
        if obj:
            name = obj.name
            # Copy Mesh
            bpy.ops.sculpt.sculptmode_toggle()
            bpy.ops.object.duplicate_move()
            bpy.data.objects[name].hide_set(True)

            if "Retopo" not in bpy.context.object.name:
                # Rename Mesh
                bpy.context.object.name = name + "Retopo"
            else:
                name = name
            # Remesh
            bpy.ops.object.quadriflow_remesh(
                use_mesh_symmetry=UseMeshSymmetry,
                use_preserve_sharp=True,
                use_preserve_boundary=True,
                preserve_attributes=PreserveAttributes,
                smooth_normals=SmoothenNormals,
                mode="FACES",
                target_faces=TargetFaceCount,
            )
            # Add Weld Modifier
            bpy.ops.object.modifier_add(type="WELD")
            if EnableProject:
                # ShrinkWrap Project
                bpy.ops.object.modifier_add(type="SHRINKWRAP")
                bpy.context.object.modifiers[
                    "Shrinkwrap"
                ].wrap_method = "TARGET_PROJECT"
                bpy.context.object.modifiers["Shrinkwrap"].target = bpy.data.objects[
                    name
                ]
                bpy.ops.object.modifier_apply(modifier="Weld")
                bpy.ops.object.modifier_apply(modifier="Shrinkwrap")
            else:
                bpy.ops.object.modifier_apply(modifier="Weld")
            bpy.ops.sculpt.sculptmode_toggle()

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


ESSENTIALS_BRUSH_ITEMS = [
    ("BLOB", "Blob", "Blob brush"),
    ("CLAY", "Clay", "Clay brush"),
    ("CLAY STRIPS", "Clay Strips", "Clay Strips brush"),
    ("CLAY THUMB", "Clay Thumb", "Clay Thumb brush"),
    ("CREASE POLISH", "Crease Polish", "Crease Polish brush"),
    ("CREASE SHARP", "Crease Sharp", "Crease Sharp brush"),
    ("DRAW", "Draw", "Draw brush"),
    ("DRAW SHARP", "Draw Sharp", "Draw Sharp brush"),
    ("INFLATE DEFLATE", "Inflate/Deflate", "Inflate/Deflate brush"),
    ("LAYER", "Layer", "Layer brush"),
    ("FILL DEEPEN", "Fill/Deepen", "Fill/Deepen brush"),
    ("FLATTEN CONTRAST", "Flatten/Contrast", "Flatten/Contrast brush"),
    ("PLATEAU", "Plateau", "Plateau brush"),
    ("SCRAPE MULTIPLANE", "Scrape Multiplane", "Scrape Multiplane brush"),
    ("SCRAPE FILL", "Scrape/Fill", "Scrape/Fill brush"),
    ("SMOOTH", "Smooth", "Smooth brush"),
    ("TRIM", "Trim", "Trim brush"),
    ("BOUNDARY", "Boundary", "Boundary brush"),
    ("ELASTIC GRAB", "Elastic Grab", "Elastic Grab brush"),
    ("ELASTIC SNAKE HOOK", "Elastic Snake Hook", "Elastic Snake Hook brush"),
    ("GRAB", "Grab", "Grab brush"),
    ("GRAB 2D", "Grab 2D", "Grab 2D brush"),
    ("GRAB SILHOUETTE", "Grab Silhouette", "Grab Silhouette brush"),
    ("NUDGE", "Nudge", "Nudge brush"),
    ("PINCH MAGNIFY", "Pinch/Magnify", "Pinch/Magnify brush"),
    ("POSE", "Pose", "Pose brush"),
    ("PULL", "Pull", "Pull brush"),
    ("RELAX PINCH", "Relax Pinch", "Relax Pinch brush"),
    ("RELAX SLIDE", "Relax Slide", "Relax Slide brush"),
    ("SNAKE HOOK", "Snake Hook", "Snake Hook brush"),
    ("THUMB", "Thumb", "Thumb brush"),
    ("TWIST", "Twist", "Twist brush"),
    ("DENSITY", "Density", "Density brush"),
    ( "ERASE MULTIRES DISPLACEMENT",
        "Erase Multires Displacement",
        "Erase Multires Displacement brush",
    ),
    ("FACE SET PAINT", "Face Set Paint", "Face Set Paint brush"),
    ("MASK", "Mask", "Mask brush"),
    (
        "SMEAR MULTIRES DISPLACEMENT",
        "Smear Multires Displacement",
        "Smear Multires Displacement brush",
    ),
    ("AIRBRUSH", "Airbrush", "Airbrush"),
    ("BLEND HARD", "Blend Hard", "Blend Hard brush"),
    ("BLEND SOFT", "Blend Soft", "Blend Soft brush"),
    ("BLEND SQUARE", "Blend Square", "Blend Square brush"),
    ("PAINT BLEND", "Paint Blend", "Paint Blend brush"),
    ("PAINT HARD", "Paint Hard", "Paint Hard brush"),
    ("PAINT HARD PRESSURE", "Paint Hard Pressure", "Paint Hard Pressure brush"),
    ("PAINT SOFT", "Paint Soft", "Paint Soft brush"),
    ("PAINT SOFT PRESSURE", "Paint Soft Pressure", "Paint Soft Pressure brush"),
    ("PAINT SQUARE", "Paint Square", "Paint Square brush"),
    ("SHARPEN", "Sharpen", "Sharpen brush"),
    ("SMEAR", "Smear", "Smear brush"),
    ("BEND BOUNDARY CLOTH", "Bend Boundary Cloth", "Bend Boundary Cloth brush"),
    ("BEND TWIST CLOTH", "Bend/Twist Cloth", "Bend/Twist Cloth brush"),
    ("DRAG CLOTH", "Drag Cloth", "Drag Cloth brush"),
    ("EXPAND CONTRACT CLOTH", "Expand/Contract Cloth", "Expand/Contract Cloth brush"),
    ("GRAB CLOTH", "Grab Cloth", "Grab Cloth brush"),
    ("GRAB PLANAR CLOTH", "Grab Planar Cloth", "Grab Planar Cloth brush"),
    ("GRAB RANDOM CLOTH", "Grab Random Cloth", "Grab Random Cloth brush"),
    ("INFLATE CLOTH", "Inflate Cloth", "Inflate Cloth brush"),
    ("PINCH FOLDS CLOTH", "Pinch Folds Cloth", "Pinch Folds Cloth brush"),
    ("PINCH POINT CLOTH", "Pinch Point Cloth", "Pinch Point Cloth brush"),
    ("PUSH CLOTH", "Push Cloth", "Push Cloth brush"),
    ("STRETCH MOVE CLOTH", "Stretch/Move Cloth", "Stretch/Move Cloth brush"),
    ("TWIST BOUNDARY CLOTH", "Twist Boundary Cloth", "Twist Boundary Cloth brush"),
]


class AllPie_OT_Search_SculptBrushes(Operator):
    bl_idname = "cop.searchsculptbrushes"
    bl_label = "Search Sculpt Brushes"
    bl_property = "SearchBrush"

    PrefProperty: StringProperty(default="")
    SearchBrush: EnumProperty(
        name="SearchBrush",
        items=ESSENTIALS_BRUSH_ITEMS,
    )

    def invoke(self, context, event):

        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        temp_item = self.SearchBrush
        temp_prop = self.PrefProperty
        setattr(prefs, temp_prop, temp_item)

        return {"FINISHED"}


class AllPie_OT_ToggleAutoMasking(Operator):
    bl_idname = "cop.toggle_auto_masking"
    bl_label = "ToggleAutoMasking Operator"

    ToggleAutoMaskingTopology: BoolProperty(default=False)
    ToggleAutoMaskingCavity: BoolProperty(default=False)
    ToggleAutoMaskingCavityInverted: BoolProperty(default=False)
    ToggleStabalizeStrokeOnActiveBrush: BoolProperty(default=False)

    def execute(self, context):

        if self.ToggleAutoMaskingTopology == True:
            currentautomasking = (
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_topology
            )
            if currentautomasking == True:
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_topology = False
            else:
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_topology = True
            self.ToggleAutoMaskingTopology = False

        elif self.ToggleAutoMaskingCavity == True:
            currentautomasking = (
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_cavity
            )
            if currentautomasking == True:
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_cavity = False
            else:
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_cavity = True
            self.ToggleAutoMaskingCavity = False

        elif self.ToggleAutoMaskingCavityInverted == True:
            currentautomasking = (
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_cavity_inverted
            )
            if currentautomasking == True:
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_cavity_inverted = False
            else:
                bpy.context.scene.tool_settings.sculpt.mesh_automasking_settings.use_automasking_cavity_inverted = True
            self.ToggleAutoMaskingCavityInverted = False

        elif self.ToggleStabalizeStrokeOnActiveBrush == True:
            brush = bpy.context.scene.tool_settings.sculpt.brush.use_smooth_stroke
            if brush == True:
                bpy.context.scene.tool_settings.sculpt.brush.use_smooth_stroke = False
            else:
                bpy.context.scene.tool_settings.sculpt.brush.use_smooth_stroke = True
            self.ToggleStabalizeStrokeOnActiveBrush = False

        return {"FINISHED"}


# Edit Mode Operators


class AllPie_OT_ToggleAutoMerge(Operator):
    bl_idname = "cop.toggle_auto_merge"
    bl_label = "Toggle Auto Merge"

    def execute(self, context):
        ts = context.scene.tool_settings
        ts.use_mesh_automerge = not ts.use_mesh_automerge
        return {"FINISHED"}

class AllPie_OT_OriginSet(Operator):
    bl_idname = "cop.originset"
    bl_label = "Set Origin"

    GeoToOrigin: BoolProperty(default=False)
    OriginToGeo: BoolProperty(default=False)
    OriginToCursor: BoolProperty(default=False)
    OriginToSelected: BoolProperty(default=False)

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        if obj.type != 'MESH':
            self.report({"WARNING"}, "Active object must be a mesh")
            return {"CANCELLED"}

        if context.mode != 'EDIT_MESH':
            self.report({"WARNING"}, "Origin tools require Edit Mode")
            return {"CANCELLED"}

        if self.GeoToOrigin == True:
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
            bpy.ops.object.editmode_toggle()
            self.GeoToOrigin = False

        elif self.OriginToGeo == True:
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
            bpy.ops.object.editmode_toggle()
            self.OriginToGeo = False

        elif self.OriginToCursor == True:
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            bpy.ops.object.editmode_toggle()
            self.OriginToCursor = False

        elif self.OriginToSelected == True:
            bpy.ops.view3d.snap_cursor_to_selected()
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            bpy.ops.view3d.snap_cursor_to_center()
            bpy.ops.object.editmode_toggle()
            self.OriginToSelected = False

        return {"FINISHED"}

classes = (
    AllPie_OT_Symmetry,
    AllPie_OT_Remesh,
    AllPie_OT_Shading,
    AllPie_OT_MultiRes,
    AllPie_OT_ColorSelectorPopup,
    AllPie_OT_CustomQuadriFlow,
    AllPie_OT_Search_SculptBrushes,
    AllPie_OT_ToggleAutoMasking,
    AllPie_OT_ToggleAutoMerge,
    AllPie_OT_OriginSet,
)

addon_keymaps = []


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
