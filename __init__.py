import bpy
import importlib
from . import AddonPreferences
from . import ObjectModePies
from . import SculptModePies
from . import EditModePies
from . import CustomOperators
from . import SettingsPanel
from . import Modalop

submodules = (
AddonPreferences,
CustomOperators,
SculptModePies,
EditModePies,
SettingsPanel,
ObjectModePies,
Modalop,

)

def register():
    for mod in submodules:
        if mod.__name__ in locals() or mod.__name__ in __import__('sys').modules:
            importlib.reload(mod)    
    AddonPreferences.register()
    CustomOperators.register()
    ObjectModePies.register()
    SculptModePies.register()
    SettingsPanel.register()
    EditModePies.register()
    Modalop.register()

def unregister():

    AddonPreferences.unregister()
    CustomOperators.unregister()
    ObjectModePies.unregister()
    SculptModePies.unregister()
    SettingsPanel.unregister()
    EditModePies.unregister()
    Modalop.unregister()


if __name__ == "__main__":
    register()

