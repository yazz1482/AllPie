import bpy
from bpy.types import Menu
from . import CustomOperators
from . import AddonPreferences

EssentialsLibraryPath = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"

#Essential Brushes Menu
class C_MT_EssentialsBrushPie(Menu):
    bl_label = "Essential Brushes"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        bpy.utils.manual_language_code
        prefs = context.preferences.addons[__package__].preferences

        # Middle Left
        slot1 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_1",
            text=prefs.EssentialPieBrush_Slot1,
        )  # Grab Brush
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot1
        )

        # Middle Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_2",
            text=prefs.EssentialPieBrush_Slot2,
        )  # Clay Strips
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot2
        )

        # Bottom
        slot3 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_7",
            text=prefs.EssentialPieBrush_Slot7,
        )  # Scrape Fill
        slot3.asset_library_type = "ESSENTIALS"
        slot3.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot7
        )

        # Top
        if prefs.EnableEssentialsNestedPieMenu == True:
            pie.operator(
                "wm.call_menu_pie", text="Nested Menu", icon="EVENT_NDOF_BUTTON_8"
            ).name = "C_MT_EssentialsNestedBrushPie"  # NestPie
        else:
            pie.operator(
                "wm.call_asset_shelf_popover", icon="EVENT_NDOF_BUTTON_8"
            ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf

        # Top Left
        slot4 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_3",
            text=prefs.EssentialPieBrush_Slot3,
        )  # Pinch
        slot4.asset_library_type = "ESSENTIALS"
        slot4.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot3
        )

        # Top Rightt
        slot5 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_4",
            text=prefs.EssentialPieBrush_Slot4,
        )  # Draw Sharp
        slot5.asset_library_type = "ESSENTIALS"
        slot5.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot4
        )

        # Bottom Left
        slot6 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_5",
            text=prefs.EssentialPieBrush_Slot5,
        )  # Inflate
        slot6.asset_library_type = "ESSENTIALS"
        slot6.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot5
        )

        # Bottom Right
        slot7 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_6",
            text=prefs.EssentialPieBrush_Slot6,
        )  # Draw
        slot7.asset_library_type = "ESSENTIALS"
        slot7.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrush_Slot6
        )


#Essential Brushes Nested Menu
class C_MT_EssentialsNestedBrushPie(Menu):
    bl_label = "Essential Brushes Nested"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        bpy.utils.manual_language_code
        prefs = context.preferences.addons[__package__].preferences

        # Middle Left
        slot1 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_1",
            text=prefs.EssentialPieBrushNested_Slot1,
        )  # Grab Brush
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot1
        )

        # Middle Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_2",
            text=prefs.EssentialPieBrushNested_Slot2,
        )  # Clay Strips
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot2
        )

        # Bottom
        slot3 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_7",
            text=prefs.EssentialPieBrushNested_Slot7,
        )  # Scrape Fill
        slot3.asset_library_type = "ESSENTIALS"
        slot3.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot7
        )

        # Top
        pie.operator(
            "wm.call_asset_shelf_popover", icon="EVENT_NDOF_BUTTON_8"
        ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf

        # Top Left
        slot4 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_3",
            text=prefs.EssentialPieBrushNested_Slot3,
        )  # Pinch
        slot4.asset_library_type = "ESSENTIALS"
        slot4.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot3
        )

        # Top Rightt
        slot5 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_4",
            text=prefs.EssentialPieBrushNested_Slot4,
        )  # Draw Sharp
        slot5.asset_library_type = "ESSENTIALS"
        slot5.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot4
        )

        # Bottom Left
        slot6 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_5",
            text=prefs.EssentialPieBrushNested_Slot5,
        )  # Inflate
        slot6.asset_library_type = "ESSENTIALS"
        slot6.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot5
        )

        # Bottom Right
        slot7 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_6",
            text=prefs.EssentialPieBrushNested_Slot6,
        )  # Draw
        slot7.asset_library_type = "ESSENTIALS"
        slot7.relative_asset_identifier = (
            EssentialsLibraryPath + prefs.EssentialPieBrushNested_Slot6
        )

#Symmetry Menu
class C_MT_SymmetryPie(Menu):
    bl_label = "Symmetry Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        if bpy.context.mode == "SCULPT":
            # Left
            pie.operator(
                "cop.symdirection", text="-X to +X", icon="MOD_MIRROR"
            ).direction = "NEGATIVE_X"
            # Right
            pie.operator(
                "cop.symdirection", text="+X to -X", icon="MOD_MIRROR"
            ).direction = "POSITIVE_X"
            # bottom
            pie.operator("sculpt.symmetrize", text="Symmetrize", icon="MOD_MIRROR")
            # top
            pie.operator(
                "wm.call_panel", text="Symmetry Menu", icon="MOD_MIRROR"
            ).name = "VIEW3D_PT_sculpt_symmetry_for_topbar"
            # Top Left
            pie.operator(
                "cop.symdirection", text="-Y to +Y", icon="MOD_MIRROR"
            ).direction = "NEGATIVE_Y"
            # Top Right
            pie.operator(
                "cop.symdirection", text="+Y to -Y", icon="MOD_MIRROR"
            ).direction = "POSITIVE_Y"
            # Bottom Left
            pie.operator(
                "cop.symdirection", text="-Z to +Z", icon="MOD_MIRROR"
            ).direction = "NEGATIVE_Z"
            # Bottom Right
            pie.operator(
                "cop.symdirection", text="+Z to -Z", icon="MOD_MIRROR"
            ).direction = "POSITIVE_Z"

#Remesh Menu
class C_MT_RemeshPie(Menu):
    bl_label = "Remesh Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        if bpy.context.mode == "SCULPT":
            # Left
            pie.operator(
                "cop.cremesh", text="Voxel Size +25%", icon="MESH_GRID"
            ).IncreaseVoxelSize25 = True
            # Right
            pie.operator(
                "cop.cremesh", text="Voxel Size -25%", icon="MESH_GRID"
            ).DecreaseVoxelSize25 = True
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
            ).IncreaseVoxelSize10 = True
            # Bottom Right
            pie.operator(
                "cop.cremesh", text="Voxel Size -10%", icon="MESH_GRID"
            ).DecreaseVoxelSize10 = True

#Shading Menu
class C_MT_ShadingPie(Menu):
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

#Multires Menu
class C_MT_MultiResPie(Menu):
    bl_label = "Multies Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        pie.operator(
            "cop.cmultirespie", text="- Sculpt Level", icon="MOD_MULTIRES"
        ).DecreaseSculptLevel = True
        # Right
        pie.operator(
            "cop.cmultirespie", text="+ Sculpt Level", icon="MOD_MULTIRES"
        ).IncreaseSculptLevel = True
        # bottom
        pie.operator(
            "cop.cmultirespie", text="Subdivide", icon="MOD_MULTIRES"
        ).MultiresSubdivide = True
        # top
        pie.operator(
            "cop.cmultirespie", text="Delete Higher", icon="MOD_MULTIRES"
        ).DeleteHigher = True
        # Top Left
        pie.operator(
            "cop.cmultirespie", text="Set Render Level", icon="MOD_MULTIRES"
        ).SculptLevelToRender = True
        # Top Right
        pie.operator(
            "cop.cmultirespie", text="Set Viewport Level", icon="MOD_MULTIRES"
        ).SculptLevelToViewport = True
        # Bottom Left
        pie.operator(
            "cop.cmultirespie", text="Apply To Base", icon="MOD_MULTIRES"
        ).ApplyToBase = True
        # Bottom Right
        pie.operator(
            "cop.cmultirespie", text="MaxSculpt Level", icon="MOD_MULTIRES"
        ).MaxSculptLevel = True

#Sculpt Paint Menu
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


class C_MT_SculptPaintPie(Menu):
    bl_label = "Painting Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        slot1 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_1", text=PaintBrushes["b6"]
        )
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b6"]
        # Right
        slot2 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_2", text=PaintBrushes["b8"]
        )
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b8"]
        # Top
        pie.operator(
            "cop.color_selector_popup", icon="EVENT_NDOF_BUTTON_7", text="Color Picker"
        )
        # Bottom
        pie.operator(
            "wm.call_asset_shelf_popover", icon="EVENT_NDOF_BUTTON_8"
        ).name = "VIEW3D_AST_brush_sculpt"
        # Top Left
        slot3 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_3", text=PaintBrushes["b7"]
        )
        slot3.asset_library_type = "ESSENTIALS"
        slot3.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b7"]
        # Top Right
        slot4 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_4", text=PaintBrushes["b9"]
        )
        slot4.asset_library_type = "ESSENTIALS"
        slot4.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b9"]
        # Bottom Left
        slot5 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_5", text=PaintBrushes["b4"]
        )
        slot5.asset_library_type = "ESSENTIALS"
        slot5.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b4"]
        # Bottom Right
        slot6 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_6", text=PaintBrushes["b10"]
        )
        slot6.asset_library_type = "ESSENTIALS"
        slot6.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b10"]

#Utility Brushes Menu
class C_MT_UtilBrushPie(Menu):
    bl_label = "Utility Brushes Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        slot1 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_1", text="FaceSet Brush"
        )
        slot1.asset_library_type = "ESSENTIALS"
        slot1.relative_asset_identifier = EssentialsLibraryPath + "Face Set Paint"
        # Right
        slot2 = pie.operator(
            "brush.asset_activate", icon="EVENT_NDOF_BUTTON_2", text="Mask Brush"
        )
        slot2.asset_library_type = "ESSENTIALS"
        slot2.relative_asset_identifier = EssentialsLibraryPath + "Mask"
        # Bottom
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_7", text="Lasso Trim"
        ).name = "builtin.lasso_trim"
        # Top
        pie.operator(
            "wm.call_menu_pie", icon="EVENT_NDOF_BUTTON_8", text="Nested Menu"
        ).name = "C_MT_UtilBrushNestedPie"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_3", text="FaceSet Lasso"
        ).name = "builtin.lasso_face_set"
        # Top Right
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_4", text="Mask Lasso"
        ).name = "builtin.lasso_mask"
        # Bottom Left
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_5", text="FaceSet Polyline"
        ).name = "builtin.polyline_face_set"
        # Bottom Right
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_6", text="Mask Polyline"
        ).name = "builtin.polyline_mask"


#Utility Brushes Nested Menu
class C_MT_UtilBrushNestedPie(Menu):
    bl_label = "UtilBrush NestedPie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "sculpt.face_sets_create",
            icon="EVENT_NDOF_BUTTON_1",
            text="FaceSet From Mask",
        ).mode = "MASKED"
        # Right
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_2", text="Mesh Filter"
        ).name = "builtin.mesh_filter"
        # Bottom
        pie.operator(
            "sculpt.paint_mask_extract", icon="EVENT_NDOF_BUTTON_8", text="Mask Extract"
        )
        # Top
        pie.operator(
            "sculpt.face_set_extract",
            icon="EVENT_NDOF_BUTTON_7",
            text="FaceSet Extract",
        )
        # Top Left
        pie.operator(
            "sculpt.face_sets_create",
            icon="EVENT_NDOF_BUTTON_3",
            text="FaceSet From EditMode",
        ).mode = "SELECTION"
        # Top Right
        pie.operator(
            "sculpt.paint_mask_slice", icon="EVENT_NDOF_BUTTON_4", text="Mask Slice"
        ).new_object = False
        # Bottom Left
        pie.operator(
            "sculpt.face_sets_create",
            icon="EVENT_NDOF_BUTTON_5",
            text="FaceSet From Visible",
        ).mode = "VISIBLE"
        # Bottom Right
        pie.operator(
            "sculpt.paint_mask_slice",
            icon="EVENT_NDOF_BUTTON_6",
            text="Mask Slice New Obj",
        )

#Transform Menu
class C_MT_SculptTransformPie(Menu):
    bl_label = "SculptTransform Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_1", text="Move"
        ).name = "builtin.move"
        # Right
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_2", text="transform"
        ).name = "builtin.transform"
        # Bottom
        pie.operator(
            "sculpt.set_pivot_position", icon="EVENT_NDOF_BUTTON_7", text="Set Pivot"
        ).mode = "SURFACE"
        # Top
        pie.operator(
            "sculpt.set_pivot_position", icon="EVENT_NDOF_BUTTON_8", text="Reset Pivot"
        ).mode = "ORIGIN"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_3", text="Scale"
        ).name = "builtin.scale"
        # Top Right
        pie.operator(
            "sculpt.mesh_filter", icon="EVENT_NDOF_BUTTON_4", text="MeshFilter Scale"
        ).type = "SCALE"
        #Bottom Left
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_5", text="Rotate"
        ).name = "builtin.rotate"
        #Bottom Right
        pie.operator(
            "sculpt.mesh_filter", icon="EVENT_NDOF_BUTTON_6", text="MeshFilter Inflate"
        ).type = "INFLATE"

#Brush Settings Pie
class C_MT_SculptBrushSettingsPie(Menu):
    bl_label = "SculptBrushSettings Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        scene = context.scene
        # Left
        pie.operator(
            "wm.call_panel", text="Brush Stroke Menu", icon="BRUSH_DATA"
        ).name = "VIEW3D_PT_tools_brush_stroke"
        # Right
        pie.operator(
            "cop.toggle_auto_masking", text="Toggle Stabalize Stroke", icon="MOD_MASK"
        ).ToggleStabalizeStrokeOnActiveBrush = True
        # bottom
        pie.operator(
            "cop.toggle_auto_masking", text="AutoMasking Topology", icon="MOD_MASK"
        ).ToggleAutoMaskingTopology = True
        # top
        pie.operator(
            "wm.call_panel", text="Brush Menu", icon="BRUSH_DATA"
        ).name = "VIEW3D_PT_tools_brush_settings_advanced"
        # Top Left
        pie.operator(
            "wm.call_panel", text="Brush Falloff Menu", icon="BRUSH_DATA"
        ).name = "VIEW3D_PT_tools_brush_falloff"
        # Top Right
        pie.operator(
            "wm.call_panel", text="Brush Texture Menu", icon="BRUSH_DATA"
        ).name = "VIEW3D_PT_tools_brush_texture"
        # Bottom Left
        pie.operator(
            "cop.toggle_auto_masking",
            text="AutoMasking Cavity Inverted",
            icon="MOD_MASK",
        ).ToggleAutoMaskingCavityInverted = True
        # Bottom Right
        pie.operator(
            "cop.toggle_auto_masking", text="AutoMasking Cavity", icon="MOD_MASK"
        ).ToggleAutoMaskingCavity = True

#CustomBrushes Pie
class C_MT_CustomBrushPie(Menu):
    bl_label = "Custom Brushes Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        bpy.utils.manual_language_code
        prefs = context.preferences.addons[__package__].preferences

        # Middle Left
        slot1 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_1",
            text=prefs.CustomPieBrush_Slot1,
        )

        slot1.asset_library_type = "CUSTOM"
        slot1.asset_library_identifier = prefs.CustomLib_Slot1
        slot1.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot1}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot1}"

        # Middle Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_2",
            text=prefs.CustomPieBrush_Slot2,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot2
        slot2.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot2}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot2}"

        # Bottom
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_7",
            text=prefs.CustomPieBrush_Slot7,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot7
        slot2.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot7}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot7}"

        # Top
        pie.operator(
            "wm.call_asset_shelf_popover", icon="EVENT_NDOF_BUTTON_8"
        ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf
        # Top Left
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_3",
            text=prefs.CustomPieBrush_Slot3,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot3
        slot2.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot3}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot3}"

        # Top Rightt
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_4",
            text=prefs.CustomPieBrush_Slot4,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot4
        slot2.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot4}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot4}"

        # Bottom Left
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_5",
            text=prefs.CustomPieBrush_Slot5,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot5
        slot2.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot5}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot5}"

        # Bottom Right
        slot2 = pie.operator(
            "brush.asset_activate",
            icon="EVENT_NDOF_BUTTON_6",
            text=prefs.CustomPieBrush_Slot6,
        )

        slot2.asset_library_type = "CUSTOM"
        slot2.asset_library_identifier = prefs.CustomLib_Slot6
        slot2.relative_asset_identifier = f"Saved\\Brushes\\{prefs.CustomPieBrush_Slot6}.asset.blend\\Brush\\{prefs.CustomPieBrush_Slot6}"

#Visibility Menu
class C_MT_SculptVisibilityPie(Menu):
    bl_label = "Sculpt Visibility Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "paint.visibility_invert",
            icon="EVENT_NDOF_BUTTON_5",
            text="Invert Visibility",
        )
        # Right
        pie.operator(
            "sculpt.face_set_change_visibility",
            icon="EVENT_NDOF_BUTTON_6",
            text="Hide Faceset",
        ).mode = "HIDE_ACTIVE"
        # Bottom
        pie.operator(
            "paint.hide_show_all", icon="EVENT_NDOF_BUTTON_7", text="UnHide All"
        ).action = "SHOW"
        # Top
        pie.operator(
            "wm.call_panel", icon="EVENT_NDOF_BUTTON_8", text="Sculpt Mode Overlay"
        ).name = "VIEW3D_PT_overlay_sculpt"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_3", text="Hide Polyline"
        ).name = "builtin.polyline_hide"
        # Top Right
        pie.operator(
            "wm.tool_set_by_id", icon="EVENT_NDOF_BUTTON_4", text="Hide Lasso"
        ).name = "builtin.lasso_hide"
        # Bottom Left
        pie.operator(
            "paint.hide_show_masked",
            icon="EVENT_NDOF_BUTTON_5",
            text="Hide Masked",
        ).action = "HIDE"
        # Bottom Right
        pie.operator(
            "sculpt.face_set_change_visibility",
            icon="EVENT_NDOF_BUTTON_5",
            text="Solo Faceset",
        ).mode = "TOGGLE"


classes = (
    C_MT_EssentialsBrushPie,
    C_MT_EssentialsNestedBrushPie,
    C_MT_SymmetryPie,
    C_MT_RemeshPie,
    C_MT_ShadingPie,
    C_MT_MultiResPie,
    C_MT_SculptPaintPie,
    C_MT_UtilBrushPie,
    C_MT_UtilBrushNestedPie,
    C_MT_SculptTransformPie,
    C_MT_SculptBrushSettingsPie,
    C_MT_CustomBrushPie,
    C_MT_SculptVisibilityPie,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
