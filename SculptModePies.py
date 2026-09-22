from . import CommonMenus

ESSENTIALS_PATH = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"

ESSENTIALS_BRUSH_MENU = [
    {
        "slot": 1,
        "label": "DRAW SHARP",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "DRAW SHARP",
        },
    },
    {
        "slot": 5,
        "label": "INFLATE",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "INFLATE/DEFLATE",
        },
    },
    {
        "slot": 7,
        "label": "PINCH",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PINCH/MAGNIFY",
        },
    },
    {
        "slot": 6,
        "label": "GRAB",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "GRAB",
        },
    },
    {
        "slot": 4,
        "label": "SCRAPE",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "SCRAPE/FILL",
        },
    },
    {
        "slot": 2,
        "label": "CLAY STRIPS",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "CLAY STRIPS",
        },
    },
    {
        "slot": 0,
        "label": "DRAW",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "DRAW",
        },
    },
    {
        "slot": 3,
        "label": "MASK",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "MASK",
        },
    },
]


ESSENTIALS_BRUSH_SPACE_MENU = [
    {
        "slot": 6,
        "label": "SNAKE HOOK",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "SNAKE HOOK",
        },
    },
    {
        "slot": 0,
        "label": "ASSET SHELF",
        "operator": "wm.call_asset_shelf_popover",
        "invoke": True,
        "props": {
            "name": "VIEW3D_AST_brush_sculpt",
        },
    },
    {
        "slot": 5,
        "label": "ERASE MULTIRES DISPLACEMENT",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "ERASE MULTIRES DISPLACEMENT",
        },
    },
    {
        "slot": 7,
        "label": "RELAX SLIDE",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "RELAX SLIDE",
        },
    },
    {
        "slot": 3,
        "label": "FACE SET PAINT",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "FACE SET PAINT",
        },
    },
    {
        "slot": 4,
        "label": "TRIM",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "TRIM",
        },
    },
    {
        "slot": 2,
        "label": "CLAY",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "CLAY",
        },
    },
    {
        "slot": 1,
        "label": "CREASE SHARP",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "CREASE SHARP",
        },
    },
]

REMESH_MENU = [
    {
        "slot": 1,
        "label": "Set Voxel Size",
        "operator": "object.voxel_size_edit",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "Remesh Menu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_sculpt_voxel_remesh",
        },
    },
    {
        "slot": 7,
        "label": "Quadriflow Remesh",
        "operator": "cop.customquadriflow",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Increase VoxelSize 25%",
        "operator": "cop.cremesh",
        "invoke": True,
        "props": {
            "action": "IncreaseVoxelSize25",
        },
    },
    {
        "slot": 5,
        "label": "Increase VoxelSize 10%",
        "operator": "cop.cremesh",
        "invoke": True,
        "props": {
            "action": "IncreaseVoxelSize10",
        },
    },
    {
        "slot": 4,
        "label": "REMESH",
        "operator": "object.voxel_remesh",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Decrease VoxelSize 25%",
        "operator": "cop.cremesh",
        "invoke": True,
        "props": {
            "action": "DecreaseVoxelSize25",
        },
    },
    {
        "slot": 3,
        "label": "Decrease VoxelSize 10%",
        "operator": "cop.cremesh",
        "invoke": True,
        "props": {
            "action": "DecreaseVoxelSize10",
        },
    },
]


SYMMETRY_MENU = [
    {
        "slot": 0,
        "label": "Symmetry Menu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_sculpt_symmetry_for_topbar",
        },
    },
    {
        "slot": 4,
        "label": "Symmetrize ",
        "operator": "sculpt.symmetrize",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Z Symmetry ",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Toggle_Z",
        },
    },
    {
        "slot": 2,
        "label": "Y Symmetry ",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Toggle_Y",
        },
    },
    {
        "slot": 1,
        "label": "X Symmetry ",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Toggle_X",
        },
    },
    {
        "slot": 7,
        "label": "Flip X",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Flip_X",
        },
    },
    {
        "slot": 6,
        "label": "Flip Y",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Flip_Y",
        },
    },
    {
        "slot": 5,
        "label": "Flip Z",
        "operator": "cop.symmetry",
        "invoke": True,
        "props": {
            "action": "Flip_Z",
        },
    },
]

MULTIRES_MENU = [
    {
        "slot": 0,
        "label": "Delete Higher",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DeleteHigher",
        },
    },
    {
        "slot": 1,
        "label": "Apply To Base ",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DeleteHigher",
        },
    },
    {
        "slot": 2,
        "label": "Increase Sculpt Level ",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "IncreaseSculptLevel",
        },
    },
    {
        "slot": 3,
        "label": "Increase Veiwport Level ",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "IncreaseViewportLevel",
        },
    },
    {
        "slot": 4,
        "label": "Subdivide",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "MultiresSubdivide",
        },
    },
    {
        "slot": 6,
        "label": "Decrease Sculpt Level",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DecreaseSculptLevel",
        },
    },
    {
        "slot": 5,
        "label": "Decrease Viewport Level",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "DecreaseViewportLevel",
        },
    },
    {
        "slot": 7,
        "label": "Set Render Level",
        "operator": "cop.cmultirespie",
        "invoke": True,
        "props": {
            "action": "SculptLevelToRender",
        },
    },
]

TOOL_SELECT_MENU = [
    {
        "slot": 5,
        "label": "Reset Pivot",
        "operator": "sculpt.set_pivot_position",
        "props": {
            "mode": "ORIGIN",
        },
    },
    {
        "slot": 4,
        "label": "Color Picker",
        "operator": "cop.color_selector_popup",
        "invoke": True,
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
        "label": "Mask Lasso",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.lasso_mask",
        },
    },
    {
        "slot": 6,
        "label": "Mask Line",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.line_mask",
        },
    },
    {
        "slot": 3,
        "label": "Set Pivot",
        "operator": "sculpt.set_pivot_position",
        "invoke": True,
        "props": {
            "mode": "SURFACE",
        },
    },
    {
        "slot": 7,
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
        "slot": 2,
        "label": "Grow Visibility",
        "operator": "paint.visibility_filter",
        "invoke": True,
        "props": {
            "action": "GROW"
            },
    },
    {
        "slot": 6,
        "label": "Shrink Visibility",
        "operator": "paint.visibility_filter",
        "invoke": True,
        "props": {
            "action": "SHRINK"
            },
    },
    {
        "slot": 3,
        "label": "Hide Lasso",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.lasso_hide",
        },
    },
    {
        "slot": 5,
        "label": "Hide Masked",
        "operator": "paint.hide_show_masked",
        "invoke": True,
        "props": {
            "action": "HIDE",
        },
    },
    {
        "slot": 1,
        "label": "Solo Faceset",
        "operator": "sculpt.face_set_change_visibility",
        "invoke": True,
        "props": {
            "mode": "TOGGLE",
        },
    },
    {
        "slot": 4,
        "label": "Invert Visible",
        "operator": "paint.visibility_invert",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "Unhide All",
        "operator": "paint.hide_show_all",
        "invoke": True,
        "props": {
            "action": "SHOW",
        },
    },
    {
        "slot": 7,
        "label": "Hide Faceset",
        "operator": "sculpt.face_set_change_visibility",
        "invoke": True,
        "props": {
            "mode": "HIDE_ACTIVE",
        },
    },
]



PAINT_BRUSH_MENU = [

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
        "slot": 4,
        "label": "Airbrush",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "AIRBRUSH",
        },
    },
    {
        "slot": 3,
        "label": "Paint Square",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PAINT SQUARE",
        },
    },
    {
        "slot": 2,
        "label": "Paint Soft",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PAINT SOFT",
        },
    },
    {
        "slot": 6,
        "label": "Paint Hard",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PAINT HARD",
        },
    },
    {
        "slot": 5,
        "label": "Paint Blend",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PAINT BLEND",
        },
    },
    {
        "slot": 1,
        "label": "Paint Soft Pressure",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PAINT SOFT PRESSURE",
        },
    },
    {
        "slot": 7,
        "label": "Paint Hard Pressure",
        "operator": "brush.asset_activate",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "relative_asset_identifier": ESSENTIALS_PATH + "PAINT HARD PRESSURE",
        },
    },
]

BRUSH_SETTINGS_MENU = [
    {
        "slot": 0,
        "label": "Brush Stroke Menu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_tools_brush_stroke",
        },
    },
    {
        "slot": 1,
        "label": "Brush Setting Menu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_tools_brush_settings_advanced",
        },
    },
    {
        "slot": 7,
        "label": "Brush Texture Menu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_tools_brush_texture",
        },
    },
    {
        "slot": 2,
        "label": "AutoMasking Cavity",
        "operator": "cop.toggle_auto_masking",
        "invoke": True,
        "props": {
            "ToggleAutoMaskingCavity": True,
        },
    },
    {
        "slot": 6,
        "label": "AutoMasking Cavity Inverted",
        "operator": "cop.toggle_auto_masking",
        "invoke": True,
        "props": {
            "ToggleAutoMaskingCavityInverted": True,
        },
    },
    {
        "slot": 3,
        "label": "AutoMasking Faceset",
        "operator": "cop.toggle_auto_masking",
        "invoke": True,
        "props": {
            "ToggleAutoMaskingFaceSet": True,
        },
    },
    {
        "slot": 5,
        "label": "AutoMasking Topology",
        "operator": "cop.toggle_auto_masking",
        "invoke": True,
        "props": {
            "ToggleAutoMaskingTopology": True,
        },
    },
    {
        "slot": 4,
        "label": "Toggle Stabilize Stroke",
        "operator": "cop.toggle_auto_masking",
        "invoke": True,
        "props": {
            "ToggleStabalizeStrokeOnActiveBrush": True,
        },
    },
]


MASK_MENU = [
    {
        "slot": 6,
        "label": "Invert Mask",
        "operator": "paint.mask_flood_fill",
        "invoke": True,
        "props": {
            "mode": "INVERT",
            },
    },
    {
        "slot": 2,
        "label": "Clear Mask",
        "operator": "paint.mask_flood_fill",
        "invoke": True,
        "props": {
            "mode": "VALUE",
            "value": 0,
            },
    },
    {
        "slot": 4,
        "label": "Sharpen Mask",
        "operator": "sculpt.mask_filter",
        "invoke": True,
        "props": {
            "filter_type": "SHARPEN",
            },
    },
    {
        "slot": 0,
        "label": "Smooth Mask",
        "operator": "sculpt.mask_filter",
        "invoke": True,
        "props": {
            "filter_type": "SMOOTH",
            },
    },
    {
        "slot": 5,
        "label": "Decrease Contrast",
        "operator": "sculpt.mask_filter",
        "invoke": True,
        "props": {
            "filter_type": "CONTRAST_DECREASE",
            "auto_iteration_count": False,
            },
    },
    {
        "slot": 3,
        "label": "Increase Contrast",
        "operator": "sculpt.mask_filter",
        "invoke": True,
        "props": {
            "filter_type": "CONTRAST_INCREASE",
            "auto_iteration_count": False,
            },
    },
    {
        "slot": 1,
        "label": "Grow Mask",
        "operator": "sculpt.mask_filter",
        "invoke": True,
        "props": {
            "filter_type": "GROW",
            },
    },
    {
        "slot": 7,
        "label": "Shrink Mask",
        "operator": "sculpt.mask_filter",
        "invoke": True,
        "props": {
            "filter_type": "SHRINK",
            },
    },
]

MASK_SPACED_MENU = [
    {
        "slot": 5,
        "label": "Cavity Mask Inverted",
        "operator": "sculpt.mask_from_cavity",
        "invoke": True,
        "props": {
            "settings_source": "OPERATOR",
            "invert": True,
        },
    },
    {
        "slot": 3,
        "label": "Cavity Mask",
        "operator": "sculpt.mask_from_cavity",
        "invoke": True,
        "props": {
            "settings_source": "OPERATOR",
            "invert": False,
        },
    },
    {
        "slot": 0,
        "label": "Faceset From Mask",
        "operator": "sculpt.face_sets_create",
        "invoke": True,
        "props": {
            "mode": "MASKED",
        },
    },
    {
        "slot": 7,
        "label": "Mask From Edit Mode",
        "operator": "mesh.selection_to_mask",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Mask From Faceset",
        "operator": "cop.maskfrom_faceset",
    },
    {
        "slot": 1,
        "label": "Mask Extract",
        "operator": "sculpt.paint_mask_extract",
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
        "slot": 6,
        "label": "Mask Slice New Obj",
        "operator": "sculpt.paint_mask_slice",
        "invoke": True,
        "props": {
            "new_object": True,
        },
    },

]

MENUS = {
    "SCULPT.ESSENTIALS_BRUSH": ESSENTIALS_BRUSH_MENU,
    "SCULPT.PAINT_BRUSH": PAINT_BRUSH_MENU,
    "SCULPT.BRUSH_SETTINGS": BRUSH_SETTINGS_MENU,
    "SCULPT.REMESH": REMESH_MENU,
    "SCULPT.SYMMETRY": SYMMETRY_MENU,
    "SCULPT.MULTIRES": MULTIRES_MENU,
    "SCULPT.TOOL_SELECT": TOOL_SELECT_MENU,
    "SCULPT.VISIBILITY": VISIBILITY_MENU,
    "SCULPT.MASK": MASK_MENU,

    # Common Menus
    "SCULPT.SHADING": CommonMenus.SHADING_MENU,
    "SCULPT.VIEW": CommonMenus.VIEW_MENU,
    "SCULPT.MODE": CommonMenus.MODE_MENU,
}

SPACE_MENUS = {
    "SCULPT.ESSENTIALS_BRUSH": ESSENTIALS_BRUSH_SPACE_MENU,
    "SCULPT.MASK": MASK_SPACED_MENU,
}

MENU_NAMES = {
    "SCULPT.ESSENTIALS_BRUSH": "Essentials Brushes",
    "SCULPT.PAINT_BRUSH": "Paint Brushes",
    "SCULPT.REMESH": "Remesh",
    "SCULPT.SYMMETRY": "Symmetry",
    "SCULPT.MULTIRES": "Multires",
    "SCULPT.SHADING": "Shading",
    "SCULPT.TOOL_SELECT": "Tool Select",
    "SCULPT.VISIBILITY": "Visibility",
    "SCULPT.VIEW": "View",
    "SCULPT.MODE": "Mode",
    "SCULPT.BRUSH_SETTINGS": "Brush Settings",
    "SCULPT.MASK": "Mask Menu",
}

SCULPT_HOTKEYS = [
    ("TAB", "SCULPT.MODE", {"ctrl": True}),
    ("ONE", "SCULPT.ESSENTIALS_BRUSH", {}),
    ("TWO", "SCULPT.PAINT_BRUSH", {}),
    ("Q", "SCULPT.VIEW", {"ctrl": True}),
    ("W", "SCULPT.TOOL_SELECT", {}),
    ("E", "SCULPT.VISIBILITY", {}),
    ("R", "SCULPT.REMESH", {}),
    ("A", "SCULPT.MASK", {}),
    ("S", "SCULPT.SYMMETRY", {}),
    ("D", "SCULPT.MULTIRES", {}),
    ("Z", "SCULPT.SHADING", {}),
    ("X", "SCULPT.BRUSH_SETTINGS", {}),
]
