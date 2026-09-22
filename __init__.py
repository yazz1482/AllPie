import bpy
import importlib
from . import Preferences
from . import CustomOperators
from . import RadialMenu
from . import CommonMenus
from . import ObjectModePies
from . import SculptModePies
from . import EditModePies
from . import TexturePaintPies
from . import VertexPaintPies

submodules = (
Preferences,
CustomOperators,
RadialMenu,
CommonMenus,
ObjectModePies,
SculptModePies,
EditModePies,
TexturePaintPies,
VertexPaintPies,
)

def register():
    for mod in submodules:
        if mod.__name__ in locals() or mod.__name__ in __import__('sys').modules:
            importlib.reload(mod)    
    Preferences.register()
    CustomOperators.register()
    RadialMenu.register()

def unregister():

    Preferences.unregister()
    CustomOperators.unregister()
    RadialMenu.unregister()


if __name__ == "__main__":
    register()

