import bpy
import math
from bpy.types import Operator
from bpy.props import StringProperty
from bpy.props import FloatProperty
from bpy.props import BoolProperty
from bpy.props import IntProperty
from bpy.props import EnumProperty
from . import EditModePies


class AllPie_OT_Symmetry(Operator):
    bl_idname = "cop.symdirection"
    bl_label = "Symmetrize"

    direction: EnumProperty(
        name="Direction",
        items=[
            ("NEGATIVE_X", "-X to +X", ""),
            ("POSITIVE_X", "+X to -X", ""),
            ("NEGATIVE_Y", "-Y to +Y", ""),
            ("POSITIVE_Y", "+Y to -Y", ""),
            ("NEGATIVE_Z", "-Z to +Z", ""),
            ("POSITIVE_Z", "+Z to -Z", ""),
        ],
    )

    def execute(self, context):
        context.scene.tool_settings.sculpt.symmetrize_direction = self.direction
        return {"FINISHED"}


class AllPie_OT_Remesh(Operator):
    bl_idname = "cop.cremesh"
    bl_label = "Remesh Operator"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    ResetVoxelSize: BoolProperty(default=False)
    IncreaseVoxelSize25: BoolProperty(default=False)
    DecreaseVoxelSize25: BoolProperty(default=False)
    IncreaseVoxelSize10: BoolProperty(default=False)
    DecreaseVoxelSize10: BoolProperty(default=False)

    def execute(self, context):
        CurrentVoxelSize = round(bpy.context.object.data.remesh_voxel_size, 3)

        if self.DecreaseVoxelSize10 == True:
            DecreasedVoxelSize = round(CurrentVoxelSize * 0.9, 3)
            bpy.context.object.data.remesh_voxel_size = DecreasedVoxelSize
            self.DecreaseVoxelSize10 = False

        elif self.DecreaseVoxelSize25 == True:
            DecreasedVoxelSize = round(CurrentVoxelSize * 0.75, 3)
            bpy.context.object.data.remesh_voxel_size = DecreasedVoxelSize
            self.DecreaseVoxelSize25 = False

        elif self.IncreaseVoxelSize10 == True:
            IncreasedVoxelSize = round(CurrentVoxelSize * 1.1, 3)
            bpy.context.object.data.remesh_voxel_size = IncreasedVoxelSize
            self.IncreaseVoxelSize10 = False

        elif self.IncreaseVoxelSize25 == True:
            IncreasedVoxelSize = round(CurrentVoxelSize * 1.25, 3)
            bpy.context.object.data.remesh_voxel_size = IncreasedVoxelSize
            self.IncreaseVoxelSize25 = False

        else:
            bpy.context.object.data.remesh_voxel_size = CurrentVoxelSize

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

    MultiresSubdivide: BoolProperty(default=False)
    IncreaseSculptLevel: BoolProperty(default=False)
    DecreaseSculptLevel: BoolProperty(default=False)
    SculptLevelToViewport: BoolProperty(default=False)
    SculptLevelToRender: BoolProperty(default=False)
    DeleteHigher: BoolProperty(default=False)
    ApplyToBase: BoolProperty(default=False)
    MaxSculptLevel: BoolProperty(default=False)

    def execute(self, context):

        obj = bpy.context.object
        if "Multires" in obj.modifiers:
            if self.MultiresSubdivide == True:
                bpy.ops.object.multires_subdivide(
                    modifier="Multires", mode="CATMULL_CLARK"
                )
                self.MultiresSubdivide = False

            CurrentSculptLevel = bpy.context.object.modifiers["Multires"].sculpt_levels
            if self.IncreaseSculptLevel == True:
                bpy.context.object.modifiers["Multires"].sculpt_levels = (
                    CurrentSculptLevel + 1
                )
                self.IncreaseSculptLevel = False

            elif self.DecreaseSculptLevel == True:
                bpy.context.object.modifiers["Multires"].sculpt_levels = (
                    CurrentSculptLevel - 1
                )
                self.DecreaseSculptLevel = False

            elif self.SculptLevelToViewport == True:
                bpy.context.object.modifiers["Multires"].levels = CurrentSculptLevel
                self.SculptLevelToViewport = False

            elif self.SculptLevelToRender == True:
                bpy.context.object.modifiers[
                    "Multires"
                ].render_levels = CurrentSculptLevel
                self.SculptLevelToRender = False

            elif self.DeleteHigher == True:
                bpy.ops.object.multires_higher_levels_delete(modifier="Multires")
                self.DeleteHiger = False

            elif self.ApplyToBase == True:
                bpy.ops.object.multires_base_apply(modifier="Multires")

            elif self.MaxSculptLevel == True:
                bpy.context.object.modifiers["Multires"].sculpt_levels = 20

        return {"FINISHED"}


class AllPie_OT_ColorSelectorPopup(Operator):
    bl_idname = "cop.color_selector_popup"
    bl_label = "Brush Color"

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        layout = self.layout

        brush = bpy.context.scene.tool_settings.sculpt.unified_paint_settings
        layout.template_color_picker(brush, "color", value_slider=True)
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
    (
        "ERASE MULTIRES DISPLACEMENT",
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
                bpy.context.scene.tool_settings.sculpt.use_automasking_topology
            )
            if currentautomasking == True:
                bpy.context.scene.tool_settings.sculpt.use_automasking_topology = False
            else:
                bpy.context.scene.tool_settings.sculpt.use_automasking_topology = True
            self.ToggleAutoMaskingTopology = False

        elif self.ToggleAutoMaskingCavity == True:
            currentautomasking = (
                bpy.context.scene.tool_settings.sculpt.use_automasking_cavity
            )
            if currentautomasking == True:
                bpy.context.scene.tool_settings.sculpt.use_automasking_cavity = False
            else:
                bpy.context.scene.tool_settings.sculpt.use_automasking_cavity = True
            self.ToggleAutoMaskingCavity = False

        elif self.ToggleAutoMaskingCavityInverted == True:
            currentautomasking = (
                bpy.context.scene.tool_settings.sculpt.use_automasking_cavity_inverted
            )
            if currentautomasking == True:
                bpy.context.scene.tool_settings.sculpt.use_automasking_cavity_inverted = False
            else:
                bpy.context.scene.tool_settings.sculpt.use_automasking_cavity_inverted = True
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

class AllPie_OT_ToggleAutoMerge(bpy.types.Operator):
    bl_idname = "cop.toggle_auto_merge"
    bl_label = "Toggle Auto Merge"

    def execute(self, context):
        ts = context.scene.tool_settings
        ts.use_mesh_automerge = not ts.use_mesh_automerge
        return {"FINISHED"}

class AllPie_OT_EditModeContextPie(Operator):
    bl_idname = "cop.editmode_context_pie"
    bl_label = "Simple Gesture Pie (6-Way)"

    def execute(self, context):
        CurrentSelectionMode = tuple(context.tool_settings.mesh_select_mode)

        if CurrentSelectionMode == (True, False, False):
            bpy.ops.wm.call_menu_pie(name="ALLPIE_MT_EditModeVertexPie" )

        elif CurrentSelectionMode == (False, True, False):
            bpy.ops.wm.call_menu_pie(name="ALLPIE_MT_EditModeEdgePie" )

        elif CurrentSelectionMode == (False, False, True):
            bpy.ops.wm.call_menu_pie(name="ALLPIE_MT_EditModeFacePie" )

        elif CurrentSelectionMode == (True, True, False):
            bpy.ops.wm.call_menu_pie(name="ALLPIE_MT_EditModeEdgePie" )

        elif CurrentSelectionMode == (False, True, True):
            bpy.ops.wm.call_menu_pie(name="ALLPIE_MT_EditModeFacePie" )

        else: 
            bpy.ops.wm.call_menu_pie(name="ALLPIE_MT_EditModeEdgePie" )

        return{"FINISHED"}


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
    AllPie_OT_EditModeContextPie,
)

addon_keymaps = []

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name="Mesh", space_type="EMPTY")
            kmi = km.keymap_items.new(AllPie_OT_EditModeContextPie.bl_idname, type='Q', value='PRESS')
        if kc:
            km = kc.keymaps.new(name="Mesh", space_type="EMPTY")
            kmi = km.keymap_items.new("wm.call_menu", type='Q', value='PRESS', alt = True)
            kmi.properties.name = "SCREEN_MT_user_menu"
            addon_keymaps.append((km, kmi))


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)

        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
        addon_keymaps.clear()


if __name__ == "__main__":
    register()
