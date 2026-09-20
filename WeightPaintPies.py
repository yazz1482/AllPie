from . import CommonMenus

MENUS = {
    # Common Menus
    "WEIGHTPAINT.SHADING": CommonMenus.SHADING_MENU,
    "WEIGHTPAINT.VIEW": CommonMenus.VIEW_MENU,
    "WEIGHTPAINT.MODE": CommonMenus.MODE_MENU,
}

MENU_NAMES = {
    "WEIGHTPAINT.SHADING": "Shading",
    "WEIGHTPAINT.VIEW": "View",
    "WEIGHTPAINT.MODE": "Mode",
}

SPACE_MENUS = {}


WEIGHTPAINT_HOTKEYS = [
    ("TAB", "WEIGHTPAINT.MODE", {"ctrl":True}),
    ("Q", "WEIGHTPAINT.VIEW", {"ctrl":True}),
    ("Z", "WEIGHTPAINT.SHADING", {}),
]
