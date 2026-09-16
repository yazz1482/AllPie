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

#         pie.operator( "wm.call_panel", icon="SCULPTMODE_HLT", text="Sculpt Mode Overlay"
#         ).name = "VIEW3D_PT_overlay_sculpt"


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
Pinch = essentialspath + "PINCH/MAGNIFY"
Pose = essentialspath + "POSE"


ESSENTIALS_BRUSH_MENU = [
    {
        "slot": 1,
        "label": "DRAW\nSHARP",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Drawsharp,
        },
    },
    {
        "slot": 0,
        "label": "INFLATE",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Inflate,
        },
    },
    {
        "slot": 5,
        "label": "DRAW",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Draw,
        },
    },
    {
        "slot": 4,
        "label": "GRAB",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Grab,
        },
    },
    {
        "slot": 3,
        "label": "SCRAPE",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Scrape,
        },
    },
    {
        "slot": 2,
        "label": "CLAY\nSTRIPS",
        "operator": "brush.asset_activate",
        "invoke": True,
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
        "invoke": True,
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
        "label": "POSE",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Pose,
        },
    },
    {
        "slot": 4,
        "label": "SNAKE\nHOOK",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Snakehook,
        },
    },
    {
        "slot": 3,
        "label": "TRIM",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Trim,
        },
    },
    {
        "slot": 2,
        "label": "PINCH",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Pinch,
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
        "invoke": True,
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
        "invoke": True,
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
        "label": "Mask Brush",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Mask,
        },
    },
    {
        "slot": 4,
        "label": "Faceset\nBrush",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": Faceset,
        },
    },
    {
        "slot": 5,
        "label": "Faceset From \n Mask",
        "operator": "sculpt.face_sets_create",
        "invoke": True,
        "props": {
            "mode": "MASKED",
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
        "slot": 0,
        "label": "Mask From \nEdit Mode",
        "operator": "sculpt.face_sets_create",
        "invoke": True,
        "props": {
            "mode": "SELECTION",
        },
    },
    {
        "slot": 3,
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
        "slot": 4,
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
        "operator": "cop.togglesihoutte",
        "invoke": True,
    },
    {
        "slot": 1,
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


TOOL_SELECT_MENU = [
    {
        "slot": 4,
        "label": "Reset Pivot",
        "operator": "sculpt.set_pivot_position",
        "props": {
            "mode": "ORIGIN",
        },
    },
    {
        "slot": 3,
        "label": "Transform",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.transform",
        },
    },
    {
        "slot": 0,
        "label": "Rotate Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.rotate",
        },
    },
    {
        "slot": 2,
        "label": "Set Pivot",
        "operator": "sculpt.set_pivot_position",
        "invoke": True,
        "props": {
            "mode": "SURFACE",
        },
    },
    {
        "slot": 5,
        "label": "Move Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.move",
        },
    },
    {
        "slot": 1,
        "label": "Scale Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.scale",
        },
    },
]

VISIBILITY_MENU = [
    {
        "slot": 5,
        "label": "Hide \n Lasso",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.lasso_hide",
        },
    },
    {
        "slot": 1,
        "label": "Hide \n Masked",
        "operator": "paint.hide_show_masked",
        "invoke": True,
        "props": {
            "action": "HIDE",
        },
    },
    {
        "slot": 3,
        "label": "Solo \n Faceset",
        "operator": "sculpt.face_set_change_visibility",
        "invoke": True,
        "props": {
            "mode": "TOGGLE",
        },
    },
    {
        "slot": 4,
        "label": "Invert \n Visible",
        "operator": "paint.visibility_invert",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "Show All",
        "operator": "paint.hide_show_all",
        "invoke": True,
        "props": {
            "action": "SHOW",
        },
    },
    {
        "slot": 2,
        "label": "Hide \n Faceset",
        "operator": "sculpt.face_set_change_visibility",
        "invoke": True,
        "props": {
            "mode": "HIDE_ACTIVE",
        },
    },
]

VIEW_MENU = [
    {
        "slot": 0,
        "label": "Top",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "TOP",
        },
    },
    {
        "slot": 1,
        "label": "Front",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "FRONT",
        },
    },
    {
        "slot": 2,
        "label": "Right",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "RIGHT",
        },
    },
    {
        "slot": 3,
        "label": "Bottom",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "BOTTOM",
        },
    },
    {
        "slot": 4,
        "label": "Left",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "LEFT",
        },
    },
    {
        "slot": 5,
        "label": "Back",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "BACK",
        },
    },
]

PaintSoft = essentialspath + "PAINT SOFT"
PaintHard = essentialspath + "PAINT HARD"
PaintSquare = essentialspath + "PAINT SQUARE"
PaintBlend = essentialspath + "PAINT BLEND"
PaintAirbrush = essentialspath + "AIRBRUSH"
PaintBlendHard = essentialspath + "BLEND HARD "
PaintBlendSoft = essentialspath + "BLEND SOFT"
PaintBlendSquare = essentialspath + "BLEND SQUARE"
PaintBlur = essentialspath + "BLUR"
PaintHardPressure = essentialspath + "PAINT HARD PRESSURE"
PaintSoftPressure = essentialspath + "PAINT SOFT PRESSURE"
PaintSharpen = essentialspath + "SHARPEN"
PaintSmear = essentialspath + "SMEAR"


PAINT_BRUSH_MENU = [
    {
        "slot": 0,
        "label": "Airbrush",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintAirbrush,
        },
    },
    {
        "slot": 3,
        "label": "ColorPicker",
        "operator": "cop.color_selector_popup",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Paint Square",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintSquare,
        },
    },
    {
        "slot": 2,
        "label": "Paint Soft",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintSoft,
        },
    },
    {
        "slot": 4,
        "label": "Paint Hard",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintHard,
        },
    },
    {
        "slot": 5,
        "label": "Paint Blend",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintBlend,
        },
    },
]

PAINT_BRUSH_SPACE_MENU = [
    {
        "slot": 0,
        "label": "AssetShelf",
        "operator": "wm.call_asset_shelf_popover",
        "invoke": True,
        "props": {
            "name": "VIEW3D_AST_brush_sculpt",
        },
    },
    {
        "slot": 3,
        "label": "Smear",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintSquare,
        },
    },
    {
        "slot": 1,
        "label": "Paint Blend \n Square",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintBlendSquare,
        },
    },
    {
        "slot": 2,
        "label": "Paint Soft \n Pressure",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintSoftPressure,
        },
    },
    {
        "slot": 4,
        "label": "Paint Hard\n Pressure",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintHardPressure,
        },
    },
    {
        "slot": 5,
        "label": "Blend Soft",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": PaintBlendSoft,
        },
    },
]

MODE_MENU = [
    {
        "slot": 3,
        "label": "Object Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "OBJECT",
        },
    },
    {
        "slot": 0,
        "label": "Texture Paint\n Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "TEXTURE_PAINT",
        },
    },
    {
        "slot": 2,
        "label": "Edit Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "EDIT",
        },
    },
    {
        "slot": 4,
        "label": "Sculpt Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "SCULPT",
        },
    },
    {
        "slot": 1,
        "label": "Weight Paint \n Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "WEIGHT_PAINT",
        },
    },
    {
        "slot": 5,
        "label": "Vertex Paint \n Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "VERTEX_PAINT",
        },
    },
]

BRUSH_SETTINGS_MENU = [
    {
        "slot": 0,
        "label": "Brush\nStroke\nMenu",
        "operator": "wm.call_panel",
        "props": {
            "name": "VIEW3D_PT_tools_brush_stroke",
        },
    },
    {
        "slot": 1,
        "label": "Brush\nSettings\nMenu",
        "operator": "wm.call_panel",
        "props": {
            "name": "VIEW3D_PT_tools_brush_settings_advanced",
        },
    },
    {
        "slot": 5,
        "label": "Brush\nTexture\nMenu",
        "operator": "wm.call_panel",
        "props": {
            "name": "VIEW3D_PT_tools_brush_texture",
        },
    },
    {
        "slot": 4,
        "label": "AutoMasking\nCavity",
        "operator": "cop.toggle_auto_masking",
        "props": {
            "ToggleAutoMaskingCavity": True,
        },
    },
    {
        "slot": 2,
        "label": "AutoMasking\nTopology",
        "operator": "cop.toggle_auto_masking",
        "props": {
            "ToggleAutoMaskingTopology": True,
        },
    },
    {
        "slot": 3,
        "label": "Toggle\nStabilize\nStroke",
        "operator": "cop.toggle_auto_masking",
        "props": {
            "ToggleStabalizeStrokeOnActiveBrush": True,
        },
    },
]

MENUS = {
    "SCULPT.ESSENTIALS_BRUSH": ESSENTIALS_BRUSH_MENU,
    "SCULPT.PAINT_BRUSH": PAINT_BRUSH_MENU,
    "SCULPT.REMESH": REMESH_MENU,
    "SCULPT.UTIL_BRUSH": UTIL_BRUSH_MENU,
    "SCULPT.SYMMETRY": SYMMETRY_MENU,
    "SCULPT.MULTIRES": MULTIRES_MENU,
    "SCULPT.SHADING": SHADING_MENU,
    "SCULPT.TOOL_SELECT": TOOL_SELECT_MENU,
    "SCULPT.VISIBILITY": VISIBILITY_MENU,
    "SCULPT.VIEW": VIEW_MENU,
    "SCULPT.MODE": MODE_MENU,
    "SCULPT.BRUSH_SETTINGS": BRUSH_SETTINGS_MENU,
}

SPACE_MENUS = {
    "SCULPT.ESSENTIALS_BRUSH": ESSENTIALS_BRUSH_SPACE_MENU,
    "SCULPT.UTIL_BRUSH": UTIL_BRUSH_SPACE_MENU,
    "SCULPT.PAINT_BRUSH": PAINT_BRUSH_SPACE_MENU,
}

SCULPT_HOTKEYS = [
    ("TAB", "SCULPT.MODE", {"ctrl": True}),
    ("ONE", "SCULPT.ESSENTIALS_BRUSH", {}),
    ("TWO", "SCULPT.PAINT_BRUSH", {}),
    ("Q", "SCULPT.VIEW", {"ctrl": True}),
    ("W", "SCULPT.TOOL_SELECT", {}),
    ("E", "SCULPT.UTIL_BRUSH", {}),
    ("R", "SCULPT.REMESH", {}),
    ("S", "SCULPT.SYMMETRY", {}),
    ("D", "SCULPT.MULTIRES", {}),
    ("Z", "SCULPT.SHADING", {}),
    ("V", "SCULPT.VISIBILITY", {}),
    ("X", "SCULPT.BRUSH_SETTINGS", {}),
]
