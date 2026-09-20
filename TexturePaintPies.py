from . import CommonMenus

MENUS = {
    # Common Menus
    "TEXTUREPAINT.SHADING": CommonMenus.SHADING_MENU,
    "TEXTUREPAINT.VIEW": CommonMenus.VIEW_MENU,
    "TEXTUREPAINT.MODE": CommonMenus.MODE_MENU,
}

MENU_NAMES = {
    "TEXTUREPAINT.SHADING": "Shading",
    "TEXTUREPAINT.VIEW": "View",
    "TEXTUREPAINT.MODE": "Mode",
}

SPACE_MENUS = {}


TEXTUREPAINT_HOTKEYS = [
    ("TAB", "TEXTUREPAINT.MODE", {"ctrl":True}),
    ("Q", "TEXTUREPAINT.VIEW", {"ctrl":True}),
    ("Z", "TEXTUREPAINT.SHADING", {}),
]
