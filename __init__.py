import bpy
import importlib
from . import Preferences
from . import ObjectModePies
from . import SculptModePies
from . import EditModePies
from . import CustomOperators
from . import RadialMenu

submodules = (
Preferences,
CustomOperators,
SculptModePies,
EditModePies,
ObjectModePies,
RadialMenu,

)

def register():
    for mod in submodules:
        if mod.__name__ in locals() or mod.__name__ in __import__('sys').modules:
            importlib.reload(mod)    
    Preferences.register()
    CustomOperators.register()
    ObjectModePies.register()
    RadialMenu.register()

def unregister():

    Preferences.unregister()
    CustomOperators.unregister()
    ObjectModePies.unregister()
    RadialMenu.unregister()


if __name__ == "__main__":
    register()

