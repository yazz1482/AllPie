from . import CommonMenus

MENUS = {
    # Common Menus
    "VERTEXPAINT.SHADING": CommonMenus.SHADING_MENU,
    "VERTEXPAINT.VIEW": CommonMenus.VIEW_MENU,
    "VERTEXPAINT.MODE": CommonMenus.MODE_MENU,
}

MENU_NAMES = {
    "VERTEXPAINT.SHADING": "Shading",
    "VERTEXPAINT.VIEW": "View",
    "VERTEXPAINT.MODE": "Mode",
}

SPACE_MENUS = {}


VERTEXPAINT_HOTKEYS = [
    ("TAB", "VERTEXPAINT.MODE", {"ctrl":True}),
    ("Q", "VERTEXPAINT.VIEW", {"ctrl":True}),
    ("Z", "VERTEXPAINT.SHADING", {}),
]
