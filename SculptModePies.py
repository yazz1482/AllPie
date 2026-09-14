#
# # Sculpt Paint Menu
# PaintBrushes = {
#     "b1": "Airbrush",
#     "b2": "Blend Hard",
#     "b3": "Blend Soft",
#     "b4": "Blend Square",
#     "b5": "Paint Blend",
#     "b6": "Paint Hard",
#     "b7": "Paint Hard Pressure",
#     "b8": "Paint Soft",
#     "b9": "Paint Soft Pressure",
#     "b10": "Paint Square",
#     "b11": "Sharpen",
#     "b12": "Smear",
# }
#
#
# class AllPie_MT_SculptPaintPie(Menu):
#     bl_idname = "ALLPIE_MT_SculptPaintPie"
#     bl_label = "Painting Pie"
#
#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()
#
#         # Left
#         slot1 = pie.operator(
#             "brush.asset_activate", icon="REC", text=PaintBrushes["b6"]
#         )
#         slot1.asset_library_type = "ESSENTIALS"
#         slot1.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b6"]
#         # Right
#         slot2 = pie.operator(
#             "brush.asset_activate", icon="REC", text=PaintBrushes["b8"]
#         )
#         slot2.asset_library_type = "ESSENTIALS"
#         slot2.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b8"]
#         # Bottom
#         pie.operator("cop.color_selector_popup", icon="COLOR", text="Color Picker")
#         # Top
#         pie.operator(
#             "wm.call_asset_shelf_popover", icon="ASSET_MANAGER", text="Asset Shelf"
#         ).name = "VIEW3D_AST_brush_sculpt"
#         # Top Left
#         slot3 = pie.operator(
#             "brush.asset_activate", icon="REC", text=PaintBrushes["b7"]
#         )
#         slot3.asset_library_type = "ESSENTIALS"
#         slot3.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b7"]
#         # Top Right
#         slot4 = pie.operator(
#             "brush.asset_activate", icon="REC", text=PaintBrushes["b9"]
#         )
#         slot4.asset_library_type = "ESSENTIALS"
#         slot4.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b9"]
#         # Bottom Left
#         slot5 = pie.operator(
#             "brush.asset_activate", icon="REC", text=PaintBrushes["b4"]
#         )
#         slot5.asset_library_type = "ESSENTIALS"
#         slot5.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b4"]
#         # Bottom Right
#         slot6 = pie.operator(
#             "brush.asset_activate", icon="REC", text=PaintBrushes["b10"]
#         )
#         slot6.asset_library_type = "ESSENTIALS"
#         slot6.relative_asset_identifier = EssentialsLibraryPath + PaintBrushes["b10"]
#
#
# # Utility Brushes Menu
# class AllPie_MT_UtilBrushPie(Menu):
#     bl_idname = "ALLPIE_MT_UtilBrushPie"
#     bl_label = "Utility Brushes Pie"
#
#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()
#         pie.operator( "wm.tool_set_by_id", icon="REC", text="Mask Lasso").name = "builtin.lasso_mask"
#         pie.operator( "wm.tool_set_by_id", icon="REC", text="Mask line").name = "builtin.line_mask"
#         pie.operator( "wm.tool_set_by_id", icon="REC", text="Trim Lasso").name = "builtin.lasso_trim"
#         pie.operator( "wm.tool_set_by_id", icon="REC", text="Trim line").name = "builtin.line_trim"
#         maskop = pie.operator( "paint.mask_flood_fill", icon="REC", text="ClearMask")
#         maskop.mode = 'VALUE'
#         maskop.value = 0
#         pie.operator( "paint.mask_flood_fill", icon="REC", text="InvertMask").mode='INVERT'

# # Utility nested  Brushes Menu
# class AllPie_MT_UtilBrushNestedPie(Menu):
#     bl_idname = "ALLPIE_MT_UtilBrushPie"
#     bl_label = "Utility Brushes Pie"

#         pie.operator( "sculpt.face_sets_create", icon="REC", text="FaceSet From Mask",).mode = "MASKED"
#         pie.operator("mesh.selection_to_mask", icon="REC", text="Mask From Edit Mode Selection")
#         pie.operator( "sculpt.paint_mask_slice", icon="REC", text="Mask Slice").new_object = False
#         pie.operator( "sculpt.paint_mask_slice", icon="REC", text="Mask Slice New Obj",)
#         pie.operator( "sculpt.face_set_extract", icon="REC", text="FaceSet Extract",)
#         pie.operator( "sculpt.paint_mask_extract", icon="REC", text="Mask Extract")
#
#
# # Transform Menu
# class AllPie_MT_SculptTransformPie(Menu):
#     bl_idname = "ALLPIE_MT_SculptTransformPie"
#     bl_label = "SculptTransform Pie"
#
#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()
#         # Left
#         pie.operator(
#             "wm.tool_set_by_id", icon="TRANSFORM_ORIGINS", text="Move"
#         ).name = "builtin.move"
#         # Right
#         pie.operator(
#             "sculpt.set_pivot_position", icon="REC", text="Set Pivot"
#         ).mode = "SURFACE"
#         # Top
#         pie.operator(
#             "sculpt.set_pivot_position", icon="REC", text="Reset Pivot"
#         ).mode = "ORIGIN"
#         # Top Left
#         pie.operator(
#             "wm.tool_set_by_id", icon="FULLSCREEN_ENTER", text="Scale"
#         ).name = "builtin.scale"
#         # Bottom Left
#         pie.operator(
#             "wm.tool_set_by_id", icon="GESTURE_ROTATE", text="Rotate"
#         ).name = "builtin.rotate"
#         # Bottom Right
#         pie.operator(
#             "sculpt.mesh_filter", icon="REC", text="MeshFilter Inflate"
#         ).type = "INFLATE"
#
#
# # Brush Settings Pie
# class AllPie_MT_SculptBrushSettingsPie(Menu):
#     bl_idname = "ALLPIE_MT_SculptBrushSettingsPie"
#     bl_label = "SculptBrushSettings Pie"
#
#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()
#         scene = context.scene
#         # Left
#         pie.operator(
#             "wm.call_panel", text="Brush Stroke Menu", icon="REC"
#         ).name = "VIEW3D_PT_tools_brush_stroke"
#         # Right
#         pie.operator(
#             "cop.toggle_auto_masking",
#             text="Toggle Stabalize Stroke",
#             icon="REC",
#         ).ToggleStabalizeStrokeOnActiveBrush = True
#         # bottom
#         pie.operator(
#             "cop.toggle_auto_masking", text="AutoMasking Topology", icon="REC"
#         ).ToggleAutoMaskingTopology = True
#         # top
#         pie.operator(
#             "wm.call_panel", text="Brush Menu", icon="REC"
#         ).name = "VIEW3D_PT_tools_brush_settings_advanced"
#         # Top Left
#         pie.operator(
#             "wm.call_panel", text="Brush Falloff Menu", icon="REC"
#         ).name = "VIEW3D_PT_tools_brush_falloff"
#         # Top Right
#         pie.operator(
#             "wm.call_panel", text="Brush Texture Menu", icon="REC"
#         ).name = "VIEW3D_PT_tools_brush_texture"
#         # Bottom Left
#         pie.operator(
#             "cop.toggle_auto_masking",
#             text="AutoMasking Cavity Inverted",
#             icon="REC",
#         ).ToggleAutoMaskingCavityInverted = True
#         # Bottom Right
#         pie.operator(
#             "cop.toggle_auto_masking", text="AutoMasking Cavity", icon="REC"
#         ).ToggleAutoMaskingCavity = True
#
#
# # CustomBrushes Pie
# class AllPie_MT_CustomBrushPie(Menu):
#     bl_idname = "ALLPIE_MT_CustomBrushPie"
#     bl_label = "Custom Brushes Pie"
#
#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()
#
#         prefs = context.preferences.addons[__package__].preferences
#
#         # Middle Left
#         slot1 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot1,
#         )
#
#         slot1.asset_library_type = "CUSTOM"
#         slot1.asset_library_identifier = prefs.CustomLib_Slot1
#         slot1.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot1}.asset.blend/Brush/{prefs.CustomPieBrush_Slot1}"
#
#         # Middle Right
#         slot2 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot2,
#         )
#
#         slot2.asset_library_type = "CUSTOM"
#         slot2.asset_library_identifier = prefs.CustomLib_Slot2
#         slot2.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot2}.asset.blend/Brush/{prefs.CustomPieBrush_Slot2}"
#
#         # Bottom
#         slot3 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot7,
#         )
#
#         slot3.asset_library_type = "CUSTOM"
#         slot3.asset_library_identifier = prefs.CustomLib_Slot7
#         slot3.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot7}.asset.blend/Brush/{prefs.CustomPieBrush_Slot7}"
#
#         # Top
#         pie.operator(
#             "wm.call_asset_shelf_popover", icon="ASSET_MANAGER", text="Asset Shelf"
#         ).name = "VIEW3D_AST_brush_sculpt"  # AssetShelf
#         # Top Left
#         slot4 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot3,
#         )
#
#         slot4.asset_library_type = "CUSTOM"
#         slot4.asset_library_identifier = prefs.CustomLib_Slot3
#         slot4.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot3}.asset.blend/Brush/{prefs.CustomPieBrush_Slot3}"
#
#         # Top Rightt
#         slot5 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot4,
#         )
#
#         slot5.asset_library_type = "CUSTOM"
#         slot5.asset_library_identifier = prefs.CustomLib_Slot4
#         slot5.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot4}.asset.blend/Brush/{prefs.CustomPieBrush_Slot4}"
#
#         # Bottom Left
#         slot6 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot5,
#         )
#
#         slot6.asset_library_type = "CUSTOM"
#         slot6.asset_library_identifier = prefs.CustomLib_Slot5
#         slot6.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot5}.asset.blend/Brush/{prefs.CustomPieBrush_Slot5}"
#
#         # Bottom Right
#         slot7 = pie.operator(
#             "brush.asset_activate",
#             icon="REC",
#             text=prefs.CustomPieBrush_Slot6,
#         )
#
#         slot7.asset_library_type = "CUSTOM"
#         slot7.asset_library_identifier = prefs.CustomLib_Slot6
#         slot7.relative_asset_identifier = f"Saved/Brushes/{prefs.CustomPieBrush_Slot6}.asset.blend/Brush/{prefs.CustomPieBrush_Slot6}"
#
#
# # Visibility Menu
# class AllPie_MT_SculptVisibilityPie(Menu):
#     bl_idname = "ALLPIE_MT_SculptVisibilityPie"
#     bl_label = "Sculpt Visibility Pie"
#
#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()
#         # Left
#         pie.operator(
#             "paint.visibility_invert",
#             icon="REC",
#             text="Invert Visibility",
#         )
#         # Right
#         pie.operator(
#             "sculpt.face_set_change_visibility",
#             icon="REC",
#             text="Hide Faceset",
#         ).mode = "HIDE_ACTIVE"
#         # Bottom
#         pie.operator(
#             "paint.hide_show_all", icon="REC", text="UnHide All"
#         ).action = "SHOW"
#         # Top
#         pie.operator(
#             "wm.call_panel", icon="SCULPTMODE_HLT", text="Sculpt Mode Overlay"
#         ).name = "VIEW3D_PT_overlay_sculpt"
#         # Top Left
#         pie.operator(
#             "wm.tool_set_by_id", icon="REC", text="Hide Polyline"
#         ).name = "builtin.polyline_hide"
#         # Top Right
#         pie.operator(
#             "wm.tool_set_by_id", icon="REC", text="Hide Lasso"
#         ).name = "builtin.lasso_hide"
#         # Bottom Left
#         pie.operator(
#             "paint.hide_show_masked",
#             icon="REC",
#             text="Hide Masked",
#         ).action = "HIDE"
#         # Bottom Right
#         pie.operator(
#             "sculpt.face_set_change_visibility",
#             icon="REC",
#             text="Solo Faceset",
#         ).mode = "TOGGLE"
#
#
# classes = (
#     AllPie_MT_EssentialsBrushPie,
#     AllPie_MT_EssentialsNestedBrushPie,
#     AllPie_MT_SymmetryPie,
#     AllPie_MT_RemeshPie,
#     AllPie_MT_ShadingPie,
#     AllPie_MT_MultiResPie,
#     AllPie_MT_SculptPaintPie,
#     AllPie_MT_UtilBrushPie,
#     AllPie_MT_UtilBrushNestedPie,
#     AllPie_MT_SculptTransformPie,
#     AllPie_MT_SculptBrushSettingsPie,
#     AllPie_MT_CustomBrushPie,
#     AllPie_MT_SculptVisibilityPie,
# )
#
#
# def register():
#
#     for cls in classes:
#         bpy.utils.register_class(cls)
#
#
# def unregister():
#
#     for cls in classes:
#         bpy.utils.unregister_class(cls)
#
#
# if __name__ == "__main__":
#     register()

essentialspath = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"

Grab = essentialspath + "GRAB"
Clay = essentialspath + "CLAY STRIPS"
Drawsharp = essentialspath + "DRAW SHARP"
Draw = essentialspath + "DRAW"
Scrape = essentialspath + "SCRAPE/FILL"
Inflate = essentialspath + "INFLATE/DEFLATE"
Mask = essentialspath + "MASK"
Faceset = essentialspath + "FACE SET PAINT"
Trim = essentialspath + "TRIM"
Creasesharp = essentialspath + "CREASE SHARP"
Snakehook = essentialspath + "SNAKE HOOK"


ESSENTIALSBRUSH_MENU = [
    {
        "slot": 1,
        "label": "DRAW\nSHARP",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Drawsharp,
        },
    },
    {
        "slot": 0,
        "label": "INFLATE",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Inflate,
        },
    },
    {
        "slot": 5,
        "label": "DRAW",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Draw,
        },
    },
    {
        "slot": 4,
        "label": "GRAB",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Grab,
        },
    },
    {
        "slot": 3,
        "label": "SCRAPE",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Scrape,
        },
    },
    {
        "slot": 2,
        "label": "CLAY\nSTRIPS",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Clay,
        },
    },
]

ESSENTIALS_BRUSH_SPACE_MENU = [
    {
        "slot": 1,
        "label": "CREASE\nSHARP",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Creasesharp,
        },
    },
    {
        "slot": 0,
        "label": "ASSET\nSHELF",
        "operator": "wm.call_asset_shelf_popover",
        "invoke": True,
        "props": {
            "name": "VIEW3D_AST_brush_sculpt",
        },
    },
    {
        "slot": 5,
        "label": "SNAKE\nHOOK",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Snakehook,
        },
    },
    {
        "slot": 4,
        "label": "FACESET",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Faceset,
        },
    },
    {
        "slot": 3,
        "label": "TRIM",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Trim,
        },
    },
    {
        "slot": 2,
        "label": "MASK",
        "operator": "brush.asset_activate",
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Mask,
        },
    },
]

REMESH_MENU = [
    {
        "slot": 1,
        "label": "SET VOXEL\nSIZE",
        "operator": "object.voxel_size_edit",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "REMESH\nMenu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_sculpt_voxel_remesh",
        },
    },
    {
        "slot": 5,
        "label": "QUADRIFLOW\nREMESH",
        "operator": "cop.customquadriflow",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "+ VOXEL\n SIZE",
        "operator": "cop.cremesh",
        "props": {
            "action": "IncreaseVoxelSize25",
        },
    },
    {
        "slot": 3,
        "label": "REMESH",
        "operator": "object.voxel_remesh",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "- VOXEL\n SIZE",
        "operator": "cop.cremesh",
        "props": {
            "action": "DecreaseVoxelSize25",
        },
    },
]

UTIL_BRUSH_MENU = [
    {
        "slot": 1,
        "label": "Mask Lasso",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.lasso_mask",
        },
    },
    {
        "slot": 2,
        "label": "Mask Line",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.line_mask",
        },
    },
    {
        "slot": 4,
        "label": "Trim Lasso",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.lasso_trim",
        },
    },
    {
        "slot": 5,
        "label": "Trim Line",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.line_trim",
        },
    },
    {
        "slot": 0,
        "label": "Clear Mask",
        "operator": "paint.mask_flood_fill",
        "invoke": True,
        "props": {
            "mode": "VALUE",
            "value": 0,
        },
    },
    {
        "slot": 3,
        "label": "Invert Mask",
        "operator": "paint.mask_flood_fill",
        "invoke": True,
        "props": {
            "mode": "INVERT",
        },
    },
]

UTIL_BRUSH_SPACE_MENU = [
    {
        "slot": 3,
        "label": "FaceSet From \nMask",
        "operator": "sculpt.face_sets_create",
        "invoke": True,
        "props": {
            "mode": "MASKED",
        },
    },
    {
        "slot": 0,
        "label": "Mask From \nEdit Mode",
        "operator": "mesh.selection_to_mask",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Mask Slice",
        "operator": "sculpt.paint_mask_slice",
        "invoke": True,
        "props": {
            "new_object": False,
        },
    },
    {
        "slot": 4,
        "label": "Mask Slice \nNew Obj",
        "operator": "sculpt.paint_mask_slice",
        "invoke": True,
        "props": {
            "new_object": True,
        },
    },
    {
        "slot": 5,
        "label": "FaceSet \nExtract",
        "operator": "sculpt.face_set_extract",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Mask \nExtract",
        "operator": "sculpt.paint_mask_extract",
        "invoke": True,
    },
]

SYMMETRY_MENU = [
    {
        "slot": 0,
        "label": "Symmetry \nMenu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_sculpt_symmetry_for_topbar",
        },
    },
    {
        "slot": 1,
        "label": "Symmetrize ",
        "operator": "sculpt.symmetrize",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Z Symmetry ",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Toggle_Z",
        },
    },
    {
        "slot": 3,
        "label": "Y Symmetry ",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Toggle_Y",
        },
    },
    {
        "slot": 4,
        "label": "X Symmetry ",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Toggle_X",
        },
    },
    {
        "slot": 5,
        "label": "Flip \n Direction",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Flip",
        },
    },
]

MULTIRES_MENU = [
    {
        "slot": 0,
        "label": "Delete \nHigher",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DeleteHigher",
        },
    },
    {
        "slot": 1,
        "label": "Apply To\n Base ",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DeleteHigher",
        },
    },
    {
        "slot": 2,
        "label": "+ Sculpt \nLevel ",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "IncreaseSculptLevel",
        },
    },
    {
        "slot": 3,
        "label": "Subdivide",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "MultiresSubdivide",
        },
    },
    {
        "slot": 4,
        "label": "- Sculpt \nLevel",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DecreaseSculptLevel",
        },
    },
    {
        "slot": 5,
        "label": "Set Viewport\nLevel",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "SculptLevelToViewport",
        },
    },
]

SHADING_MENU = [
    {
        "slot": 0,
        "label": "Shading\nMenu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_shading",
        },
    },
    {
        "slot": 1,
        "label": "Wireframe",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetShading": "WIREFRAME",
        },
    },
    {
        "slot": 2,
        "label": "Solid",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetShading": "SOLID",
        },
    },
    {
        "slot": 3,
        "label": "Switch\nLighting",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SwitchLighting": True,
        },
    },
    {
        "slot": 4,
        "label": "Material",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetShading": "MATERIAL",
        },
    },
    {
        "slot": 5,
        "label": "Rendered",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetShading": "RENDERED",
        },
    },
]

MENUS = {
    "SCULPT.ESSENTIALS_BRUSH": ESSENTIALSBRUSH_MENU,
    "SCULPT.REMESH": REMESH_MENU,
    "SCULPT.UTIL_BRUSH": UTIL_BRUSH_MENU,
    "SCULPT.SYMMETRY": SYMMETRY_MENU,
    "SCULPT.MULTIRES": MULTIRES_MENU,
    "SCULPT.SHADING": SHADING_MENU,
}

SPACE_MENUS = {
    "SCULPT.ESSENTIALS_BRUSH": ESSENTIALS_BRUSH_SPACE_MENU,
    "SCULPT.UTIL_BRUSH": UTIL_BRUSH_SPACE_MENU,
}

SCULPT_HOTKEYS = [
    ("W", "SCULPT.ESSENTIALS_BRUSH", {}),
    ("E", "SCULPT.UTIL_BRUSH", {}),
    ("R", "SCULPT.REMESH", {}),
    ("S", "SCULPT.SYMMETRY", {}),
    ("D", "SCULPT.MULTIRES", {}),
    ("Z", "SCULPT.SHADING", {}),
]
