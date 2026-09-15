#         # # Bottom Left
#         # pie.operator( "object.hide_view_clear", icon="REC", text="Unhide All"
#         # ).select=False
#         # # Bottom Right
#         # pie.operator( "object.hide_view_set", icon="REC", text="Solo Object"
#         # ).unselected = True
#

ADD_MENU = [
    {
        "slot": 5,
        "label": "Add Plane",
        "operator": "mesh.primitive_plane_add",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Add Cube",
        "operator": "mesh.primitive_cube_add",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Search \nAdd Menu",
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
        "slot": 4,
        "label": "Add Cylinder",
        "operator": "mesh.primitive_cylinder_add",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Add UVSphere",
        "operator": "mesh.primitive_uv_sphere_add",
        "invoke": True,
    },
]


APPLY_TRANSFORMS_MENU = [
    {
        "slot": 0,
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
        "slot": 3,
        "label": "All\nTransforms",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": True,
            "rotation": True,
            "scale": True,
        },
    },
    {
        "slot": 2,
        "label": "Rotation &\n Scale",
        "operator": "object.transform_apply",
        "invoke": True,
        "props": {
            "location": False,
            "rotation": True,
            "scale": True,
        },
    },
    {
        "slot": 4,
        "label": "  Apply\nTransforms\n Menu",
        "operator": "wm.call_menu",
        "invoke": True,
        "props": {
            "name": "VIEW3D_MT_object_apply"
        },
    },
    {
        "slot": 5,
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
        "slot": 1,
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
        "slot": 2,
        "label": "SubDivision",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "SUBSURF",
        },
    },
    {
        "slot": 3,
        "label": "Mirror",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "MIRROR",
        },
    },
    {
        "slot": 0,
        "label": "Modifier Search",
        "operator": "wm.search_single_menu",
        "invoke": True,
        "props": {
            "menu_idname": "OBJECT_MT_modifier_add",
        },
    },
    {
        "slot": 1,
        "label": "Multires",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "MULTIRES",
        },
    },
    {
        "slot": 4,
        "label": "Solidify",
        "operator": "object.modifier_add",
        "invoke": True,
        "props": {
            "type": "SOLIDIFY",
        },
    },
    {
        "slot": 5,
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
        "slot": 4,
        "label": "Deselect All",
        "operator": "object.select_all",
        "invoke": True,
        "props": {
            "action": "DESELECT",
        },
    },
    {
        "slot": 2,
        "label": "Select All",
        "operator": "object.select_all",
        "invoke": True,
        "props": {
            "action": "SELECT",
        },
    },
    {
        "slot": 3,
        "label": "Invert\nSelection",
        "operator": "object.select_all",
        "invoke": True,
        "props": {
            "action": "INVERT",
        },
    },
    {
        "slot": 0,
        "label": "Right Click\nMenu",
        "operator": "wm.call_menu",
        "invoke": True,
        "props": {
            "name": "VIEW3D_MT_object_context_menu",
        },
    },
    {
        "slot": 5,
        "label": "Rename\nObject",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "TOPBAR_PT_name",
        },
    },
    {
        "slot": 1,
        "label": "Move To\nCollection",
        "operator": "wm.call_menu",
        "invoke": True,
        "props": {
            "name": "OBJECT_MT_move_to_collection",
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
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SwitchLighting": True,
        },
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
        "label": "Cursor Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.cursor",
        },
    },
    {
        "slot": 2,
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
        "slot": 3,
        "label": "Tweak Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.select",
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

MODE_MENU = [
    {
        "slot": 0,
        "label": "Object Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "OBJECT",
        },
    },
    {
        "slot": 4,
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
        "slot": 3,
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

# TODO - BUG: AFTER CHANGING KEYBIND, IT BREAKS HOVER FUNCTIONALITY
MENUS = {
    "OBJECT.ADD": ADD_MENU,
    "OBJECT.APPLY_TRANSFORMS": APPLY_TRANSFORMS_MENU,
    "OBJECT.MODIFIER": MODIFIER_MENU,
    "OBJECT.SELECTION": SELECTION_MENU,
    "OBJECT.SHADING": SHADING_MENU,
    "OBJECT.TOOL_SELECT":TOOL_SELECT_MENU,
    "OBJECT.VIEW":VIEW_MENU,
    "OBJECT.MODE":MODE_MENU,
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
