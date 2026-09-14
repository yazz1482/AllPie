SELECTION_MENU = [
    {
        "slot": 5,
        "label": "Vert Select",
        "operator": "mesh.select_mode",
        "props": {
            "type": "VERT",
        },
    },
    {
        "slot": 0,
        "label": "Edge Select",
        "operator": "mesh.select_mode",
        "props": {
            "type": "EDGE",
        },
    },
    {
        "slot": 1,
        "label": "Face Select",
        "operator": "mesh.select_mode",
        "props": {
            "type": "FACE",
        },
    },
    {
        "slot": 2,
        "label": "Select All",
        "operator": "mesh.select_all",
        "invoke": True,
        "props": {
            "action": "SELECT",
        },
    },
    {
        "slot": 3,
        "label": "Invert\n Selection",
        "operator": "mesh.select_all",
        "invoke": True,
        "props": {
            "action": "INVERT",
        },
    },
    {
        "slot": 4,
        "label": "Deselect All",
        "operator": "mesh.select_all",
        "invoke": True,
        "props": {
            "action": "DESELECT",
        },
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
        "label": "Face Dissolve",
        "operator": "mesh.dissolve_faces",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Edge Dissolve",
        "operator": "mesh.dissolve_edges",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Vertices Dissolve",
        "operator": "mesh.dissolve_verts",
        "invoke": True,
    },
    {
        "slot": 5,
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
        "label": "Separate\nSelection",
        "operator": "mesh.separate",
        "invoke": True,
        "props": {
            "type": "SELECTED",
        },
    },
    {
        "slot": 1,
        "label": "Merge By\nDistance",
        "operator": "mesh.remove_doubles",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "At Center",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "CENTER",
        },
    },
    {
        "slot": 4,
        "label": "At First",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "FIRST",
        },
    },
    {
        "slot": 5,
        "label": "At Cursor",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "CURSOR",
        },
    },
    {
        "slot": 2,
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
        "slot": 0,
        "label": "Rip Vertices",
        "operator": "mesh.rip_move",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Knife Tool",
        "operator": "mesh.knife_tool",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Extrude\nVertices",
        "operator": "mesh.extrude_vertices_move",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Merge At\nCenter",
        "operator": "mesh.merge",
        "invoke": True,
        "props": {
            "type": "CENTER",
        },
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
        "slot": 1,
        "label": "Loop Cut",
        "operator": "mesh.loopcut_slide",
        "invoke": True,
    },
    {
        "slot": 2,
        "label": "Edge Bevel",
        "operator": "mesh.bevel",
        "invoke": True,
        "props": {
            "affect": "EDGES",
        },
    },
    {
        "slot": 3,
        "label": "Extrude\nEdges",
        "operator": "mesh.extrude_edges_move",
        "invoke": True,
    },
    {
        "slot": 0,
        "label": "Grid Fill",
        "operator": "mesh.fill_grid",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Bridge\nEdgeLoops",
        "operator": "mesh.bridge_edge_loops",
        "invoke": True,
    },
    {
        "slot": 4,
        "label": "Fill",
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
        "slot": 5,
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
        "slot": 4,
        "label": "Clear Seam",
        "operator": "mesh.mark_seam",
        "invoke": True,
        "props": {
            "clear": True,
        },
    },
    {
        "slot": 0,
        "label": "Edge Bevel\nWeight",
        "operator": "transform.edge_bevelweight",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Edge Crease",
        "operator": "transform.edge_crease",
        "invoke": True,
    },
]

FACE_MENU = [
    {
        "slot": 0,
        "label": "Poke",
        "operator": "mesh.poke",
    },
    {
        "slot": 4,
        "label": "Extrude\nIndividual",
        "operator": "mesh.extrude_faces_move",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "Extrude\nFaces",
        "operator": "mesh.extrude_region_move",
        "invoke": True,
    },
    {
        "slot": 1,
        "label": "Inset",
        "operator": "mesh.inset",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Flip Normals",
        "operator": "mesh.flip_normals",
    },
    {
        "slot": 2,
        "label": "Extrude\nAlong Normals",
        "operator": "mesh.extrude_region_shrink_fatten",
        "invoke": True,
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

UV_MENU = [
    {
        "slot": 0,
        "label": "Follow\nActive Quads",
        "operator": "uv.follow_active_quads",
        "invoke": True,
    },
    {
        "slot": 5,
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
        "slot": 4,
        "label": "Clear Seam",
        "operator": "mesh.mark_seam",
        "invoke": True,
        "props": {
            "clear": True,
        },
    },
    {
        "slot": 1,
        "label": "Unwrap\nConformal",
        "operator": "uv.unwrap",
        "invoke": True,
        "props": {
            "method": "CONFORMAL",
        },
    },
    {
        "slot": 3,
        "label": "Unwrap\nMinimum\nStretch",
        "operator": "uv.unwrap",
        "invoke": True,
        "props": {
            "method": "MINIMUM_STRETCH",
        },
    },
]

ORIGIN_MENU = [
    {
        "slot": 0,
        "label": "Origin To\nGeometry",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "OriginToGeo": True,
        },
    },
    {
        "slot": 4,
        "label": "Cursor To\nOrigin",
        "operator": "view3d.snap_cursor_to_center",
        "invoke": True,
    },
    {
        "slot": 5,
        "label": "Selected To\nCursor",
        "operator": "view3d.snap_selected_to_cursor",
        "invoke": True,
        "props": {
            "use_offset": True,
        },
    },
    {
        "slot": 3,
        "label": "Origin To\nSelected",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "OriginToSelected": True,
        },
    },
    {
        "slot": 2,
        "label": "Cursor To\nSelected",
        "invoke": True,
        "operator": "view3d.snap_cursor_to_selected",
    },
    {
        "slot": 1,
        "label": "Origin To\nCursor",
        "operator": "cop.originset",
        "invoke": True,
        "props": {
            "OriginToCursor": True,
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
    "EDIT.SELECTION": SELECTION_MENU,
    "EDIT.DELETE": DELETE_MENU,
    "EDIT.MERGE": MERGE_MENU,
    "EDIT.VERTEX": VERTEX_MENU,
    "EDIT.EDGE": EDGE_MENU,
    "EDIT.FACE": FACE_MENU,
    "EDIT.TOOL_SELECT": TOOL_SELECT_MENU,
    "EDIT.UV": UV_MENU,
    "EDIT.ORIGIN": ORIGIN_MENU,
    "EDIT.SHADING": SHADING_MENU,
}

SPACE_MENUS = {
    "EDIT.EDGE": EDGE_SPACE_MENU,
    "EDIT.VERTEX": MERGE_MENU,
    "EDIT.FACE": UV_MENU
}


MESH_HOTKEYS = [
    ("ONE", "EDIT.VERTEX", {}),
    ("TWO", "EDIT.EDGE", {}),
    ("THREE", "EDIT.FACE", {}),
    ("W", "EDIT.TOOL_SELECT", {"alt": True}),
    ("A", "EDIT.SELECTION", {}),
    ("X", "EDIT.DELETE", {}),
    ("X", "EDIT.ORIGIN", {"alt": True}),
    ("M", "EDIT.MERGE", {}),
    ("U", "EDIT.UV", {}),
    ("Z", "EDIT.SHADING", {}),
]
