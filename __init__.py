import bpy
import importlib
from . import AddonPrefs
from . import SculptPies
from . import EditModePies
from . import COperators

submodules = (
AddonPrefs,
SculptPies,
EditModePies,
COperators,
)

def register():
    for mod in submodules:
        if mod.__name__ in locals() or mod.__name__ in __import__('sys').modules:
            importlib.reload(mod)    
    AddonPrefs.register()
    COperators.register()
    SculptPies.register()
    EditModePies.register()

def unregister():

    AddonPrefs.unregister()
    COperators.unregister()
    SculptPies.unregister()
    EditModePies.unregister()


if __name__ == "__main__":
    register()

