MODE_MENU = [
    {
        "slot": 6,
        "label": "Object Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "OBJECT",
        },
    },
    {
        "slot": 0,
        "label": "Texture Paint Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "TEXTURE_PAINT",
        },
    },
    {
        "slot": 1,
        "label": "Edit Mode Vertex Select",
        "operator": "cop.editmode_switch",
        "invoke": True,
        "props": {
            "Action": "VERTEX",
        },
    },
    {
        "slot": 2,
        "label": "Edit Mode Edge Select",
        "operator": "cop.editmode_switch",
        "invoke": True,
        "props": {
            "Action": "EDGE",
        },
    },
    {
        "slot": 3,
        "label": "Edit Mode Face Select",
        "operator": "cop.editmode_switch",
        "invoke": True,
        "props": {
            "Action": "FACE",
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
        "slot": 7,
        "label": "Weight Paint Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "WEIGHT_PAINT",
        },
    },
    {
        "slot": 5,
        "label": "Vertex Paint Mode",
        "operator": "object.mode_set",
        "invoke": True,
        "props": {
            "mode": "VERTEX_PAINT",
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
        "slot": 4,
        "label": "Bottom",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "BOTTOM",
        },
    },
    {
        "slot": 6,
        "label": "Left",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "LEFT",
        },
    },
    {
        "slot": 7,
        "label": "Back",
        "operator": "view3d.view_axis",
        "invoke": True,
        "props": {
            "type": "BACK",
        },
    },
    {
        "slot": 5,
        "label": "View Camera",
        "operator": "view3d.view_camera",
        "invoke": True,
    },
    {
        "slot": 3,
        "label": "View Selected",
        "operator": "view3d.view_selected",
        "invoke": True,
    },
]

SHADING_MENU = [
    {
        "slot": 0,
        "label": "Shading Menu",
        "operator": "wm.call_panel",
        "invoke": True,
        "props": {
            "name": "VIEW3D_PT_shading",
        },
    },
    {
        "slot": 6,
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
        "slot": 5,
        "label": "Studio",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetLighting": "STUDIO",
        },
    },
    {
        "slot": 4,
        "label": "Matcap",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetLighting": "MATCAP",
        },
    },
    {
        "slot": 3,
        "label": "Flat",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetLighting": "FLAT",
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
        "slot": 7,
        "label": "Rendered",
        "operator": "cop.cshading",
        "invoke": True,
        "props": {
            "SetShading": "RENDERED",
        },
    },
]


SUBD_MENU = [
    {
        "slot": 2,
        "label": "Increase Subdivision",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "IncreaseSubDLevel",
        },
    },
    {
        "slot": 1,
        "label": "Increase Render Level ",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "IncreaseRenderLevel",
        },
    },
    {
        "slot": 6,
        "label": "Decrease Subdivision",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "DecreaseSubDLevel",
        },
    },
    {
        "slot": 7,
        "label": "Decrease Render Level",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "DecreaseRenderLevel",
        },
    },
    {
        "slot": 0,
        "label": "Show In Viewport",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "ShowInViewport",
        },
    },
    {
        "slot": 4,
        "label": "Show In EditMode",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "ShowInEdit",
        },
    },
    {
        "slot": 3,
        "label": "Show In Render",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "ShowInRender",
        },
    },
    {
        "slot": 5,
        "label": "Show Cage",
        "operator": "cop.csubd",
        "invoke": True,
        "props": {
            "action": "ShowInCage",
        },
    },
]
