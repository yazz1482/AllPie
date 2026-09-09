import bpy
from bpy.types import Menu
from . import CustomOperators
from . import AddonPreferences

EssentialsLibraryPath = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"


# Essential Brushes Menu
class AllPie_MT_EssentialsBrushPie(Menu):
    bl_idname = "ALLPIE_MT_EssentialsBrushPie"
    bl_label = "Essential Brushes"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        prefs = context.preferences.addons[__package__].preferences

        # Middle Left
        slot1 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot1,
        )
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot1
        )

        # Middle Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot2,
        )
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot2
        )

        # Bottom
        slot3 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot7,
        )
        slot3.asset_library_type = "ESSENTIALS"
        slot3.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot7
        )

        # Top
        if prefs.EnableEssentialsNestedPieMenu == True:
            pie.operator(
                "wm.call_menu_pie", text="Nested Menu", icon="REC"
            ).name = "ALLPIE_MT_EssentialsNestedBrushPie"  # NestPie
        else:
            pie.operator(
                "wm.call_asset_shelf_popover", icon="ASSET_MANAGER", text="Asset Shelf"
            ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf

        # Top Left
        slot4 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot3,
        )
        slot4.asset_library_type = "ESSENTIALS"
        slot4.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot3
        )

        # Top Rightt
        slot5 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot4,
        )
        slot5.asset_library_type = "ESSENTIALS"
        slot5.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot4
        )

        # Bottom Left
        slot6 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot5,
        )
        slot6.asset_library_type = "ESSENTIALS"
        slot6.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot5
        )

        # Bottom Right
        slot7 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrush_Slot6,
        )
        slot7.asset_library_type = "ESSENTIALS"
        slot7.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot6
        )


# Essential Brushes Nested Menu
class AllPie_MT_EssentialsNestedBrushPie(Menu):
    bl_idname = "ALLPIE_MT_EssentialsNestedBrushPie"
    bl_label = "Essential Brushes Nested"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        prefs = context.preferences.addons[__package__].preferences

        # Middle Left
        slot1 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot1,
        )
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot1
        )

        # Middle Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot2,
        )
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot2
        )

        # Bottom
        slot3 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot7,
        )
        slot3.asset_library_type = "ESSENTIALS"
        slot3.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot7
        )

        # Top
        pie.operator(
            "wm.call_asset_shelf_popover", icon="ASSET_MANAGER", text="Asset Shelf"
        ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf

        # Top Left
        slot4 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot3,
        )
        slot4.asset_library_type = "ESSENTIALS"
        slot4.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot3
        )

        # Top Rightt
        slot5 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot4,
        )
        slot5.asset_library_type = "ESSENTIALS"
        slot5.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot4
        )

        # Bottom Left
        slot6 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot5,
        )
        slot6.asset_library_type = "ESSENTIALS"
        slot6.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot5
        )

        # Bottom Right
        slot7 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.EssentialPieBrushNested_Slot6,
        )
        slot7.asset_library_type = "ESSENTIALS"
        slot7.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot6
        )


# Symmetry Menu
class AllPie_MT_SymmetryPie(Menu):
    bl_idname = "ALLPIE_MT_SymmetryPie"
    bl_label = "Symmetry Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        if bpy.context.mode == "SCULPT":
            # Left
            pie.operator( "cop.symmetry", text="Flip Y Symmetry", icon="MOD_MIRROR").action = "Flip_Y"
            # Right
            pie.operator( "cop.symmetry", text="Y Symmetry", icon="MOD_MIRROR").action = "Toggle_Y"
            # bottom
            pie.operator("sculpt.symmetrize", text="Symmetrize", icon="MOD_MIRROR")
            # top
            pie.operator(
                "wm.call_panel", text="Symmetry Menu", icon="MOD_MIRROR"
            ).name = "VIEW3D_PT_sculpt_symmetry_for_topbar"
            # Top Left
            pie.operator( "cop.symmetry", text="Flip X Symmetry", icon="MOD_MIRROR").action = "Flip_X"
            # Top Right
            pie.operator( "cop.symmetry", text="X Symmetry", icon="MOD_MIRROR").action = "Toggle_X"
            # Bottom Left
            pie.operator( "cop.symmetry", text="Flip Z Symmetry", icon="MOD_MIRROR").action = "Flip_Z"
            # Bottom Right
            pie.operator( "cop.symmetry", text="Z Symmetry", icon="MOD_MIRROR").action = "Toggle_Z"


# Remesh Menu
class AllPie_MT_RemeshPie(Menu):
    bl_idname = "ALLPIE_MT_RemeshPie"
    bl_label = "Remesh Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        if bpy.context.mode == "SCULPT":
            # Left
            pie.operator(
                "cop.cremesh", text="Voxel Size +25%", icon="MESH_GRID"
            ).action  = "IncreaseVoxelSize25"
            # Right
            pie.operator(
                "cop.cremesh", text="Voxel Size -25%", icon="MESH_GRID"
            ).action = "DecreaseVoxelSize25"
            # bottom
            pie.operator("object.voxel_remesh", text="Remesh", icon="MESH_GRID")
            # top
            pie.operator(
                "wm.call_panel", text="Remesh Menu", icon="MESH_GRID"
            ).name = "VIEW3D_PT_sculpt_voxel_remesh"
            pie.operator(
                "cop.customquadriflow", text="QuadriFlow Remesh", icon="MESH_GRID"
            )
            # Top Right
            pie.operator(
                "object.voxel_size_edit", text="Set Voxel Size", icon="MESH_GRID"
            )
            # Bottom Left
            pie.operator(
                "cop.cremesh", text="Voxel Size +10%", icon="MESH_GRID"
            ).action = "IncreaseVoxelSize10"
            # Bottom Right
            pie.operator(
                "cop.cremesh", text="Voxel Size -10%", icon="MESH_GRID"
            ).action = "DecreaseVoxelSize10"


# Shading Menu
class AllPie_MT_ShadingPie(Menu):
    bl_idname = "ALLPIE_MT_ShadingPie"
    bl_label = "Shading Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        pie.operator(
            "cop.cshading", text="Material Preview", icon="MATERIAL"
        ).SetShading = "MATERIAL"
        # Right
        pie.operator(
            "cop.cshading", text="Solid ", icon="SHADING_SOLID"
        ).SetShading = "SOLID"
        # bottom
        pie.operator(
            "cop.cshading", text="Matcap ", icon="MATSPHERE"
        ).SetShadingLight = "MATCAP"
        # top
        pie.operator(
            "wm.call_panel", text="Shading Menu", icon="SHADING_SOLID"
        ).name = "VIEW3D_PT_shading"
        # Top Left
        pie.operator(
            "cop.cshading", text="WireFrame ", icon="SHADING_WIRE"
        ).SetShading = "WIREFRAME"
        # Top Right
        pie.operator(
            "cop.cshading", text="Rendered ", icon="SHADING_RENDERED"
        ).SetShading = "RENDERED"
        # Bottom Left
        pie.operator(
            "cop.cshading", text="Studio ", icon="MATSPHERE"
        ).SetShadingLight = "STUDIO"
        # Bottom Right
        pie.operator(
            "cop.cshading", text="Flat ", icon="MATSPHERE"
        ).SetShadingLight = "FLAT"


# Multires Menu
class AllPie_MT_MultiResPie(Menu):
    bl_idname = "ALLPIE_MT_MultiResPie"
    bl_label = "Multires Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        pie.operator(
            "cop.cmultirespie", text="- Sculpt Level", icon="MOD_MULTIRES"
        ).action = "DecreaseSculptLevel"
        # Right
        pie.operator(
            "cop.cmultirespie", text="+ Sculpt Level", icon="MOD_MULTIRES"
        ).action = "IncreaseSculptLevel"
        # bottom
        pie.operator(
            "cop.cmultirespie", text="Subdivide", icon="MOD_MULTIRES"
        ).action = "MultiresSubdivide"
        # top
        pie.operator(
            "cop.cmultirespie", text="Delete Higher", icon="MOD_MULTIRES"
        ).action = "DeleteHigher"
        # Top Left
        pie.operator( "cop.cmultirespie", text="Set Render Level", icon="MOD_MULTIRES").action = "SculptLevelToRender"
        # Top Right
        pie.operator( "cop.cmultirespie", text="Set Viewport Level", icon="MOD_MULTIRES").action = "SculptLevelToViewport"
        # Bottom Left
        pie.operator( "cop.cmultirespie", text="Apply To Base", icon="MOD_MULTIRES").action = "ConformToBase"
        # Bottom Right
        pie.operator(
            "cop.cmultirespie", text="MaxSculpt Level", icon="MOD_MULTIRES"
        ).action = "MaxSculptLevel"


# Sculpt Paint Menu
PaintBrushes = {
    "b1": "Airbrush",
    "b2": "Blend Hard",
    "b3": "Blend Soft",
    "b4": "Blend Square",
    "b5": "Paint Blend",
    "b6": "Paint Hard",
    "b7": "Paint Hard Pressure",
    "b8": "Paint Soft",
    "b9": "Paint Soft Pressure",
    "b10": "Paint Square",
    "b11": "Sharpen",
    "b12": "Smear",
}


class AllPie_MT_SculptPaintPie(Menu):
    bl_idname = "ALLPIE_MT_SculptPaintPie"
    bl_label = "Painting Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        slot1 = pie.operator(
            "brush.asset_activate", icon="REC", text=PaintBrushes["b6"]
        )
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b6"]
        # Right
        slot2 = pie.operator(
            "brush.asset_activate", icon="REC", text=PaintBrushes["b8"]
        )
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b8"]
        # Bottom
        pie.operator("cop.color_selector_popup", icon="COLOR", text="Color Picker")
        # Top
        pie.operator(
            "wm.call_asset_shelf_popover", icon="ASSET_MANAGER", text="Asset Shelf"
        ).name = "VIEW3D_AST_brush_sculpt"
        # Top Left
        slot3 = pie.operator(
            "brush.asset_activate", icon="REC", text=PaintBrushes["b7"]
        )
        slot3.asset_library_type = "ESSENTIALS"
        slot3.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b7"]
        # Top Right
        slot4 = pie.operator(
            "brush.asset_activate", icon="REC", text=PaintBrushes["b9"]
        )
        slot4.asset_library_type = "ESSENTIALS"
        slot4.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b9"]
        # Bottom Left
        slot5 = pie.operator(
            "brush.asset_activate", icon="REC", text=PaintBrushes["b4"]
        )
        slot5.asset_library_type = "ESSENTIALS"
        slot5.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b4"]
        # Bottom Right
        slot6 = pie.operator(
            "brush.asset_activate", icon="REC", text=PaintBrushes["b10"]
        )
        slot6.asset_library_type = "ESSENTIALS"
        slot6.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b10"]


# Utility Brushes Menu
class AllPie_MT_UtilBrushPie(Menu):
    bl_idname = "ALLPIE_MT_UtilBrushPie"
    bl_label = "Utility Brushes Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        slot1 = pie.operator(
            "brush.asset_activate", icon="REC", text="FaceSet Brush"
        )
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = EssentialsLibraryPath + "Face Set Paint"
        # Right
        slot2 = pie.operator(
            "brush.asset_activate", icon="REC", text="Mask Brush"
        )
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = EssentialsLibraryPath + "Mask"
        # Bottom
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="Lasso Trim"
        ).name = "builtin.lasso_trim"
        # Top
        pie.operator(
            "wm.call_menu_pie", icon="REC", text="Nested Menu"
        ).name = "ALLPIE_MT_UtilBrushNestedPie"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="FaceSet Lasso"
        ).name = "builtin.lasso_face_set"
        # Top Right
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="Mask Lasso"
        ).name = "builtin.lasso_mask"
        # Bottom Left
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="FaceSet Polyline"
        ).name = "builtin.polyline_face_set"
        # Bottom Right
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="Mask Polyline"
        ).name = "builtin.polyline_mask"


# Utility Brushes Nested Menu
class AllPie_MT_UtilBrushNestedPie(Menu):
    bl_idname = "ALLPIE_MT_UtilBrushNestedPie"
    bl_label = "UtilBrush NestedPie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "sculpt.face_sets_create",
            icon="REC",
            text="FaceSet From Mask",
        ).mode = "MASKED"
        # Right
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="Mesh Filter"
        ).name = "builtin.mesh_filter"
        # Bottom
        pie.operator(
            "sculpt.paint_mask_extract", icon="REC", text="Mask Extract"
        )
        # Top
        pie.operator(
            "sculpt.face_set_extract",
            icon="REC",
            text="FaceSet Extract",
        )
        # Top Left
        pie.operator(
            "sculpt.face_sets_create",
            icon="REC",
            text="FaceSet From EditMode",
        ).mode = "SELECTION"
        # Top Right
        pie.operator(
            "sculpt.paint_mask_slice", icon="REC", text="Mask Slice"
        ).new_object = False
        # Bottom Left
        pie.operator(
            "sculpt.face_sets_create",
            icon="REC",
            text="FaceSet From Visible",
        ).mode = "VISIBLE"
        # Bottom Right
        pie.operator(
            "sculpt.paint_mask_slice",
            icon="REC",
            text="Mask Slice New Obj",
        )


# Transform Menu
class AllPie_MT_SculptTransformPie(Menu):
    bl_idname = "ALLPIE_MT_SculptTransformPie"
    bl_label = "SculptTransform Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "wm.tool_set_by_id", icon="TRANSFORM_ORIGINS", text="Move"
        ).name = "builtin.move"
        # Right
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="transform"
        ).name = "builtin.transform"
        # Bottom
        pie.operator(
            "sculpt.set_pivot_position", icon="REC", text="Set Pivot"
        ).mode = "SURFACE"
        # Top
        pie.operator(
            "sculpt.set_pivot_position", icon="REC", text="Reset Pivot"
        ).mode = "ORIGIN"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="FULLSCREEN_ENTER", text="Scale"
        ).name = "builtin.scale"
        # Top Right
        pie.operator(
            "sculpt.mesh_filter", icon="REC", text="MeshFilter Scale"
        ).type = "SCALE"
        # Bottom Left
        pie.operator(
            "wm.tool_set_by_id", icon="GESTURE_ROTATE", text="Rotate"
        ).name = "builtin.rotate"
        # Bottom Right
        pie.operator(
            "sculpt.mesh_filter", icon="REC", text="MeshFilter Inflate"
        ).type = "INFLATE"


# Brush Settings Pie
class AllPie_MT_SculptBrushSettingsPie(Menu):
    bl_idname = "ALLPIE_MT_SculptBrushSettingsPie"
    bl_label = "SculptBrushSettings Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        scene = context.scene
        # Left
        pie.operator(
            "wm.call_panel", text="Brush Stroke Menu", icon="REC"
        ).name = "VIEW3D_PT_tools_brush_stroke"
        # Right
        pie.operator(
            "cop.toggle_auto_masking",
            text="Toggle Stabalize Stroke",
            icon="REC",
        ).ToggleStabalizeStrokeOnActiveBrush = True
        # bottom
        pie.operator(
            "cop.toggle_auto_masking", text="AutoMasking Topology", icon="REC"
        ).ToggleAutoMaskingTopology = True
        # top
        pie.operator(
            "wm.call_panel", text="Brush Menu", icon="REC"
        ).name = "VIEW3D_PT_tools_brush_settings_advanced"
        # Top Left
        pie.operator(
            "wm.call_panel", text="Brush Falloff Menu", icon="REC"
        ).name = "VIEW3D_PT_tools_brush_falloff"
        # Top Right
        pie.operator(
            "wm.call_panel", text="Brush Texture Menu", icon="REC"
        ).name = "VIEW3D_PT_tools_brush_texture"
        # Bottom Left
        pie.operator(
            "cop.toggle_auto_masking",
            text="AutoMasking Cavity Inverted",
            icon="REC",
        ).ToggleAutoMaskingCavityInverted = True
        # Bottom Right
        pie.operator(
            "cop.toggle_auto_masking", text="AutoMasking Cavity", icon="REC"
        ).ToggleAutoMaskingCavity = True


# CustomBrushes Pie
class AllPie_MT_CustomBrushPie(Menu):
    bl_idname = "ALLPIE_MT_CustomBrushPie"
    bl_label = "Custom Brushes Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        prefs = context.preferences.addons[__package__].preferences

        # Middle Left
        slot1 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot1,
        )

        slot1.asset_library_type = "CUSTOM"
        slot1.asset_library_identifier = prefs.CustomLib_Slot1
        slot1.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot1}.asset.blend/Brush/{prefs.CustomPieBrush_Slot1}"

        # Middle Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot2,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot2
        slot2.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot2}.asset.blend/Brush/{prefs.CustomPieBrush_Slot2}"

        # Bottom
        slot3 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot7,
        )

        slot3.asset_library_type = "CUSTOM"
        slot3.asset_library_identifier = prefs.CustomLib_Slot7
        slot3.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot7}.asset.blend/Brush/{prefs.CustomPieBrush_Slot7}"

        # Top
        pie.operator(
            "wm.call_asset_shelf_popover", icon="ASSET_MANAGER", text="Asset Shelf"
        ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf
        # Top Left
        slot4 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot3,
        )

        slot4.asset_library_type = "CUSTOM"
        slot4.asset_library_identifier = prefs.CustomLib_Slot3
        slot4.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot3}.asset.blend/Brush/{prefs.CustomPieBrush_Slot3}"

        # Top Rightt
        slot5 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot4,
        )

        slot5.asset_library_type = "CUSTOM"
        slot5.asset_library_identifier = prefs.CustomLib_Slot4
        slot5.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot4}.asset.blend/Brush/{prefs.CustomPieBrush_Slot4}"

        # Bottom Left
        slot6 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot5,
        )

        slot6.asset_library_type = "CUSTOM"
        slot6.asset_library_identifier = prefs.CustomLib_Slot5
        slot6.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot5}.asset.blend/Brush/{prefs.CustomPieBrush_Slot5}"

        # Bottom Right
        slot7 = pie.operator(
            "brush.asset_activate",
            icon="REC",
            text=prefs.CustomPieBrush_Slot6,
        )

        slot7.asset_library_type = "CUSTOM"
        slot7.asset_library_identifier = prefs.CustomLib_Slot6
        slot7.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot6}.asset.blend/Brush/{prefs.CustomPieBrush_Slot6}"


# Visibility Menu
class AllPie_MT_SculptVisibilityPie(Menu):
    bl_idname = "ALLPIE_MT_SculptVisibilityPie"
    bl_label = "Sculpt Visibility Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "paint.visibility_invert",
            icon="REC",
            text="Invert Visibility",
        )
        # Right
        pie.operator(
            "sculpt.face_set_change_visibility",
            icon="REC",
            text="Hide Faceset",
        ).mode = "HIDE_ACTIVE"
        # Bottom
        pie.operator(
            "paint.hide_show_all", icon="REC", text="UnHide All"
        ).action = "SHOW"
        # Top
        pie.operator(
            "wm.call_panel", icon="SCULPTMODE_HLT", text="Sculpt Mode Overlay"
        ).name = "VIEW3D_PT_overlay_sculpt"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="Hide Polyline"
        ).name = "builtin.polyline_hide"
        # Top Right
        pie.operator(
            "wm.tool_set_by_id", icon="REC", text="Hide Lasso"
        ).name = "builtin.lasso_hide"
        # Bottom Left
        pie.operator(
            "paint.hide_show_masked",
            icon="REC",
            text="Hide Masked",
        ).action = "HIDE"
        # Bottom Right
        pie.operator(
            "sculpt.face_set_change_visibility",
            icon="REC",
            text="Solo Faceset",
        ).mode = "TOGGLE"


classes = (
    AllPie_MT_EssentialsBrushPie,
    AllPie_MT_EssentialsNestedBrushPie,
    AllPie_MT_SymmetryPie,
    AllPie_MT_RemeshPie,
    AllPie_MT_ShadingPie,
    AllPie_MT_MultiResPie,
    AllPie_MT_SculptPaintPie,
    AllPie_MT_UtilBrushPie,
    AllPie_MT_UtilBrushNestedPie,
    AllPie_MT_SculptTransformPie,
    AllPie_MT_SculptBrushSettingsPie,
    AllPie_MT_CustomBrushPie,
    AllPie_MT_SculptVisibilityPie,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
