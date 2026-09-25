from . import CommonMenus

SELECTION_MENU = [
    {
        "slot": 7,
        "label": "Hide Selected",
        "operator": "mesh.hide",
        "invoke": True,
        "props": {
            "unselected": False,
        },
    },
    {
        "slot": 0,
        "label": "UnHide All",
        "operator": "mesh.reveal",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Solo Selected",
        "operator": "mesh.hide",
        "invoke": True,
        "props": {
            "unselected": True,
        },
    },
    {
        "slot": 3,
        "label": "Select All",
        "operator": "mesh.select_all",
        "invoke": True,
        "props": {
            "action": "SELECT",
        },
    },
    {
        "slot": 4,
        "label": "Invert Selection",
        "operator": "mesh.select_all",
        "invoke": True,
        "props": {
            "action": "INVERT",
        },
    },
    {
        "slot": 5,
        "label": "Deselect All",
        "operator": "mesh.select_all",
        "invoke": True,
        "props": {
            "action": "DESELECT",
        },
    },
    {
        "slot": 6,
        "label": "Loop Inner Region",
        "operator": "mesh.loop_to_region",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Select Mirror",
        "operator": "mesh.select_mirror",
        "invoke": True,
        "props": {
            "extend": True,
            },
    },
]

SELECTION_SPACE_MENU = [
    {
        "slot": 7,
        "label": "Vert Select",
        "operator": "mesh.select_mode",
        "invoke": True,
        "props": {
            "type": "VERT",
        },
    },
    {
        "slot": 0,
        "label": "Edge Select",
        "operator": "mesh.select_mode",
        "invoke": True,
        "props": {
            "type": "EDGE",
        },
    },
    {
        "slot": 1,
        "label": "Face Select",
        "operator": "mesh.select_mode",
        "invoke": True,
        "props": {
            "type": "FACE",
        },
    },
    {
        "slot": 2,
        "label": "Select Non Manifold",
        "operator": "mesh.select_non_manifold",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Select Sharp Edges",
        "operator": "mesh.edges_select_sharp",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Checker Deselect",
        "operator": "mesh.select_nth",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Select Similar",
        "operator": "mesh.select_similar",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Select Linked",
        "operator": "mesh.select_linked_pick",
        "invoke": True,
    },
]

DELETE_MENU = [
    {
        "slot": 0,
        "label": "Edge Delete",
        "operator": "mesh.delete",
        "invoke": True,
        "props": {
            "type": "EDGE",
        },
    },
    {
        "slot": 1,
        "label": "Face Delete",
        "operator": "mesh.delete",
        "invoke": True,
        "props": {
            "type": "FACE",
        },
    },
    {
        "slot": 2,
        "label": "Only Face",
        "operator": "mesh.delete",
        "invoke": True,
        "props": {
            "type": "ONLY_FACE",
        },
    },
    {
        "slot": 3,
        "label": "Face Dissolve",
        "operator": "mesh.dissolve_faces",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Edge Dissolve",
        "operator": "mesh.dissolve_edges",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Vertices Dissolve",
        "operator": "mesh.dissolve_verts",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Edge & Face",
        "operator": "mesh.delete",
        "invoke": True,
        "props": {
            "type": "EDGE_FACE",
        },
    },
    {
        "slot": 7,
        "label": "Vertices Delete",
        "operator": "mesh.delete",
        "invoke": True,
        "props": {
            "type": "VERT",
        },
    },
]

MERGE_MENU = [
    {
        "slot": 0,
        "label": "Separate Selection",
        "operator": "mesh.separate",
        "invoke": True,
        "props": {
            "type": "SELECTED",
        },
    },
    {
        "slot": 1,
        "label": "Separate Loose Geometry",
        "operator": "mesh.separate",
        "invoke": True,
        "props": {
            "type": "LOOSE",
        },
    },
    {
        "slot": 7,
        "label": "Separate By Material",
        "operator": "mesh.separate",
        "invoke": True,
        "props": {
            "type": "MATERIAL",
        },
    },
    {
        "slot": 2,
        "label": "Merge By Distance",
        "operator": "mesh.remove_doubles",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "At Center",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "CENTER",
        },
    },
    {
        "slot": 5,
        "label": "At First",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "FIRST",
        },
    },
    {
        "slot": 6,
        "label": "At Cursor",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "CURSOR",
        },
    },
    {
        "slot": 3,
        "label": "At Last",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "LAST",
        },
    },
]

VERTEX_MENU = [
    {
        "slot": 7,
        "label": "Rip Vertices",
        "operator": "mesh.rip_move",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Vertex Slide",
        "operator": "transform.vert_slide",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "Extrude Vertices",
        "operator": "mesh.extrude_vertices_move",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Merge At Center",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "CENTER",
        },
    },
    {
        "slot": 3,
        "label": "Fill Face",
        "operator": "mesh.edge_face_add",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Knife Tool",
        "operator": "mesh.knife_tool",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Join Vertices",
        "invoke": True,
        "operator": "mesh.vert_connect_path",
    },
    {
        "slot": 2,
        "label": "Vertex Bevel",
        "operator": "mesh.bevel",
        "invoke": True,
        "props": {
            "affect": "VERTICES",
        },
    },
]

EDGE_MENU = [
    {
        "slot": 6,
        "label": "Loop Cut Slide",
        "operator": "mesh.loopcut_slide",
        "invoke": True,
    },

    {
        "slot": 5,
        "label": "Loop Cut",
        "operator": "mesh.loopcut",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Edge Bevel",
        "operator": "mesh.bevel",
        "invoke": True,
        "props": {
            "offset": 0.5,
            "affect": "EDGES",
            "segments": 1,
            "profile": 0.5,
        },

    },
    {
        "slot": 4,
        "label": "Flat Bevel",
        "operator": "mesh.bevel",
        "invoke": True,
        "props": {
            "offset": 0.5,
            "affect": "EDGES",
            "segments": 2,
            "profile": 1.0,
        },

    },
    {
        "slot": 0,
        "label": "Extrude Edges",
        "operator": "mesh.extrude_edges_move",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Edge Slide",
        "operator": "transform.edge_slide",
        "invoke": True,
    },
    {
        "slot": 7,
        "label": "Bridge EdgeLoops",
        "operator": "mesh.bridge_edge_loops",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Fill Face",
        "operator": "mesh.edge_face_add",
        "invoke": True,
    },
]


EDGE_SPACE_MENU = [
    {
        "slot": 1,
        "label": "Mark Sharp",
        "operator": "mesh.mark_sharp",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Mark Sharp",
        "operator": "mesh.set_sharpness_by_angle",
        "invoke": True,
        "props": {
            "extend": True,
            },
    },
    {
        "slot": 7,
        "label": "Clear Sharp",
        "operator": "mesh.mark_sharp",
        "invoke": True,
        "props": {
            "clear": True,
        },
    },
    {
        "slot": 2,
        "label": "Mark Seam",
        "operator": "mesh.mark_seam",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Clear Seam",
        "operator": "mesh.mark_seam",
        "invoke": True,
        "props": {
            "clear": True,
        },
    },
    {
        "slot": 3,
        "label": "Edge Bevel Weight",
        "operator": "transform.edge_bevelweight",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Clear Bevel Weight",
        "operator": "transform.edge_bevelweight",
        "props": {
            "value": -1,
        },
    },
    {
        "slot": 4,
        "label": "Edge Crease",
        "operator": "cop.ccrease",
        "invoke": True,
        "props": { "factor": 0.0, },
    },
    {
        "slot": 0,
        "label": "Clear Edge Crease",
        "operator": "transform.edge_crease",
        "props": {
            "value": -1,
        },
    },
]

FACE_MENU = [
    {
        "slot": 6,
        "label": "Poke",
        "operator": "mesh.poke",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "Extrude Faces",
        "operator": "mesh.extrude_region_move",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Inset",
        "operator": "mesh.inset",
        "invoke": True,
    },
    {
        "slot": 7,
        "label": "Shade Face Smooth",
        "operator": "mesh.faces_shade_smooth",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Shade Face Flat",
        "operator": "mesh.faces_shade_flat",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Fill Face",
        "operator": "mesh.edge_face_add",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Grid Fill",
        "operator": "mesh.fill_grid",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Extrude Along Normals",
        "operator": "mesh.extrude_region_shrink_fatten",
        "invoke": True,
    },
]

TOOL_SELECT_MENU = [
    {
        "slot": 6,
        "label": "Box Select Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.select_box",
        },
    },
    {
        "slot": 2,
        "label": "Lasso Select Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.select_lasso",
        },
    },
    {
        "slot": 3,
        "label": "Circle Select Tool",
        "operator": "wm.tool_set_by_id",
        "invoke": True,
        "props": {
            "name": "builtin.select_circle",
        },
    },
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
]

UV_MENU = [
    {
        "slot": 1,
        "label": "Follow Active Quads",
        "operator": "uv.follow_active_quads",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "UV Reset",
        "operator": "uv.reset",
        "invoke": True,
    },
    {
        "slot": 7,
        "label": "Smart Project",
        "operator": "uv.smart_project",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Mark Seam",
        "operator": "mesh.mark_seam",
        "invoke": True,
    },
    {
        "slot": 6,
        "label": "Clear Seam",
        "operator": "mesh.mark_seam",
        "invoke": True,
        "props": {
            "clear": True,
        },
    },
    {
        "slot": 3,
        "label": "Unwrap Conformal",
        "operator": "uv.unwrap",
        "invoke": True,
        "props": {
            "method": "CONFORMAL",
        },
    },
    {
        "slot": 4,
        "label": "Unwrap Minimum Stretch",
        "operator": "uv.unwrap",
        "invoke": True,
        "props": {
            "method": "MINIMUM_STRETCH",
        },
    },
    {
        "slot": 5,
        "label": "Unwrap Angle Based",
        "operator": "uv.unwrap",
        "invoke": True,
        "props": {
            "method": "ANGLE_BASED",
        },
    },
]

ORIGIN_MENU = [
    {
        "slot": 1,
        "label": "Origin To Geometry",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "OriginToGeo": True,
        },
    },
    {
        "slot": 7,
        "label": "Cursor To Origin",
        "operator": "view3d.snap_cursor_to_center",
        "invoke": True,
    },
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
        "slot": 0,
        "label": "Selected To Cursor",
        "operator": "view3d.snap_selected_to_cursor",
        "invoke": True,
        "props": {
            "use_offset": True,
        },
    },
    {
        "slot": 4,
        "label": "Geometry To Origin",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "GeoToOrigin": True,
        },
    },
    {
        "slot": 2,
        "label": "Origin To Selected",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "OriginToSelected": True,
        },
    },
    {
        "slot": 6,
        "label": "Cursor To Selected",
        "invoke": True,
        "operator": "view3d.snap_cursor_to_selected",
    },
    {
        "slot": 3,
        "label": "Origin To Cursor",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "OriginToCursor": True,
        },
    },
    {
        "slot": 3,
        "label": "Origin To Cursor",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "GeoToOrigin": True,
        },
    },
]

MENUS = {
    "EDIT.SELECTION": SELECTION_MENU,
    "EDIT.DELETE": DELETE_MENU,
    "EDIT.MERGE": MERGE_MENU,
    "EDIT.VERTEX": VERTEX_MENU,
    "EDIT.EDGE": EDGE_MENU,
    "EDIT.FACE": FACE_MENU,
    "EDIT.TOOL_SELECT": TOOL_SELECT_MENU,
    "EDIT.UV": UV_MENU,
    "EDIT.ORIGIN": ORIGIN_MENU,

    # Common Menus
    "EDIT.SHADING": CommonMenus.SHADING_MENU,
    "EDIT.VIEW": CommonMenus.VIEW_MENU,
    "EDIT.MODE": CommonMenus.MODE_MENU,
    "EDIT.SUBD": CommonMenus.SUBD_MENU,
}

MENU_NAMES = {
    "EDIT.SELECTION": "Selection & Hide",
    "EDIT.DELETE": "Deletion",
    "EDIT.MERGE": "Merge & Separate",
    "EDIT.VERTEX": "Vertex",
    "EDIT.EDGE": "Edge",
    "EDIT.FACE": "Face",
    "EDIT.TOOL_SELECT": "Tool Select",
    "EDIT.UV": "UV",
    "EDIT.ORIGIN": "Origin",
    "EDIT.SUBD": "Subdivision",

    "EDIT.SHADING": "Shading",
    "EDIT.VIEW": "View",
    "EDIT.MODE": "Mode",
}

SPACE_MENUS = {
    "EDIT.EDGE": EDGE_SPACE_MENU,
    "EDIT.VERTEX": MERGE_MENU,
    "EDIT.FACE": UV_MENU,
    "EDIT.SELECTION": SELECTION_SPACE_MENU,
}


MESH_HOTKEYS = [
    ("TAB", "EDIT.MODE", {"ctrl":True}),
    ("ONE", "EDIT.VERTEX", {}),
    ("TWO", "EDIT.EDGE", {}),
    ("THREE", "EDIT.FACE", {}),
    ("Q", "EDIT.VIEW", {"ctrl": True}),
    ("W", "EDIT.TOOL_SELECT", {}),
    ("A", "EDIT.SELECTION", {}),
    ("S", "EDIT.ORIGIN", {"shift": True}),
    ("D", "EDIT.SUBD", {}),
    ("X", "EDIT.DELETE", {}),
    ("M", "EDIT.MERGE", {}),
    ("U", "EDIT.UV", {}),
    ("Z", "EDIT.SHADING", {}),
]
