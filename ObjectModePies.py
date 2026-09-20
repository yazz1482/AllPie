from . import  CommonMenus

ADD_MENU = [
    {
        "slot": 7,
        "label": "Add Plane",
        "operator": "mesh.primitive_plane_add",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Add Cube",
        "operator": "mesh.primitive_cube_add",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Search Add Menu",
        "operator": "wm.search_single_menu",
        "invoke": True,
        "props": {
            "menu_idname": "VIEW3D_MT_add"
        },
    },
    {
        "slot": 0,
        "label": "Add Menu",
        "operator": "wm.call_menu",
        "invoke": True,
        "props": {
            "name": "VIEW3D_MT_add"
        },
    },
    {
        "slot": 1,
        "label": "Add Cylinder",
        "operator": "mesh.primitive_cylinder_add",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Add UVSphere",
        "operator": "mesh.primitive_uv_sphere_add",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Add Cone",
        "operator": "mesh.primitive_cone_add",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Add Grid",
        "operator": "mesh.primitive_grid_add",
        "invoke": True,
    },
]


APPLY_TRANSFORMS_MENU = [
    {
        "slot": 2,
        "label": "Rotation",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": False,
            "rotation": True,
            "scale": False,
        },
    },
    {
        "slot": 4,
        "label": "All Transforms",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": True,
            "rotation": True,
            "scale": True,
        },
    },
    {
        "slot": 5,
        "label": "Rotation & Scale",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": False,
            "rotation": True,
            "scale": True,
        },
    },
    {
        "slot": 7,
        "label": "Location & Scale",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": True,
            "rotation": False,
            "scale": True,
        },
    },
    {
        "slot": 6,
        "label": "Location & Rotation",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": True,
            "rotation": True,
            "scale": False,
        },
    },
    {
        "slot": 0,
        "label": "  Apply Transforms Menu",
        "operator": "wm.call_menu",
        "invoke": True,
        "props": {
            "name": "VIEW3D_MT_object_apply"
        },
    },
    {
        "slot": 1,
        "label": "Location",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": True,
            "rotation": False,
            "scale": False,
        },
    },
    {
        "slot": 3,
        "label": "Scale",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": False,
            "rotation": False,
            "scale": True,
        },
    },
]


MODIFIER_MENU = [
    {
        "slot": 1,
        "label": "SubDivision",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "SUBSURF",
        },
    },
    {
        "slot": 2,
        "label": "Mirror",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "MIRROR",
        },
    },
    {
        "slot": 4,
        "label": "Modifier Search",
        "operator": "wm.search_single_menu",
        "invoke": True,
        "props": {
            "menu_idname": "OBJECT_MT_modifier_add",
        },
    },
    {
        "slot": 7,
        "label": "Multires",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "MULTIRES",
        },
    },
    {
        "slot": 3,
        "label": "Solidify",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "SOLIDIFY",
        },
    },
    {
        "slot": 5,
        "label": "Displace",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "DISPLACE",
        },
    },
    {
        "slot": 6,
        "label": "Shrinkwrap",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "SHRINKWRAP",
        },
    },
    {
        "slot": 0,
        "label": "Array",
        "operator": "object.modifier_add_node_group",
        "invoke": True,
        "props": {
            "asset_library_type": "ESSENTIALS",
            "asset_library_identifier": "",
            "relative_asset_identifier": (
                "nodes/geometry_nodes_essentials.blend/"
                "NodeTree/Array"
            ),
        },
    },
]


SELECTION_MENU = [
    {
        "slot": 5,
        "label": "Deselect All",
        "operator": "object.select_all",
        "invoke": True,
        "props": {
            "action": "DESELECT",
        },
    },
    {
        "slot": 3,
        "label": "Select All",
        "operator": "object.select_all",
        "invoke": True,
        "props": {
            "action": "SELECT",
        },
    },
    {
        "slot": 4,
        "label": "Invert Selection",
        "operator": "object.select_all",
        "invoke": True,
        "props": {
            "action": "INVERT",
        },
    },
    {
        "slot": 2,
        "label": "Rename Object",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "TOPBAR_PT_name",
        },
    },
    {
        "slot": 6,
        "label": "Move To Collection",
        "operator": "wm.call_menu",
        "invoke": True,
        "props": {
            "name": "OBJECT_MT_move_to_collection",
        },
    },
    {
        "slot": 0,
        "label": "Unhide All",
        "operator": "object.hide_view_clear",
        "invoke": True,
        "props": {
            "select": False,
        },
    },
    {
        "slot": 1,
        "label": "Solo Object",
        "operator": "object.hide_view_set",
        "invoke": True,
        "props": {
            "unselected": True,
        },
    },
    {
        "slot": 7,
        "label": "Hide Selected",
        "operator": "object.hide_view_set",
        "invoke": True,
        "props": {
            "unselected": False,
        },
    },
]

TOOL_SELECT_MENU = [
    {
        "slot": 5,
        "label": "Cursor Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.cursor",
        },
    },
    {
        "slot": 3,
        "label": "Lasso Select",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.select_lasso",
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
        "slot": 4,
        "label": "Tweak Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.select",
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
    {
        "slot": 2,
        "label": "Add Cube Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.primitive_cube_add",
        },
    },
    {
        "slot": 6,
        "label": "Add Cylinder Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.primitive_cylinder_add",
        },
    },
]



MENUS = {
    "OBJECT.ADD": ADD_MENU,
    "OBJECT.APPLY_TRANSFORMS": APPLY_TRANSFORMS_MENU,
    "OBJECT.MODIFIER": MODIFIER_MENU,
    "OBJECT.SELECTION": SELECTION_MENU,
    "OBJECT.TOOL_SELECT": TOOL_SELECT_MENU,

    # Common Menus
    "OBJECT.SHADING": CommonMenus.SHADING_MENU,
    "OBJECT.VIEW": CommonMenus.VIEW_MENU,
    "OBJECT.MODE": CommonMenus.MODE_MENU,
}

MENU_NAMES = {
    "OBJECT.ADD": "Add Object",
    "OBJECT.APPLY_TRANSFORMS": "Apply Transforms",
    "OBJECT.MODIFIER": "Add Modifier",
    "OBJECT.SELECTION": "Selection & Hide",
    "OBJECT.TOOL_SELECT": "Tool Select",

    "OBJECT.SHADING": "Shading",
    "OBJECT.VIEW": "View",
    "OBJECT.MODE": "Mode",
}

SPACE_MENUS = {}


OBJECT_HOTKEYS = [
    ("TAB", "OBJECT.MODE", {"ctrl":True}),
    ("Q", "OBJECT.MODIFIER", {"shift":True}),
    ("Q", "OBJECT.VIEW", {"ctrl":True}),
    ("W", "OBJECT.TOOL_SELECT", {}),
    ("A", "OBJECT.SELECTION", {}),
    ("A", "OBJECT.ADD", {"shift": True}),
    ("A", "OBJECT.APPLY_TRANSFORMS", {"ctrl": True}),
    ("Z", "OBJECT.SHADING", {}),
]
