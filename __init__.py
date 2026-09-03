import bpy
import importlib
from . import AddonPreferences
from . import SculptModePies
from . import EditModePies
from . import CustomOperators
from . import SettingsPanel

submodules = (
AddonPreferences,
CustomOperators,
SculptModePies,
EditModePies,
SettingsPanel,
)

def register():
    for mod in submodules:
        if mod.__name__ in locals() or mod.__name__ in __import__('sys').modules:
            importlib.reload(mod)    
    AddonPreferences.register()
    CustomOperators.register()
    SculptModePies.register()
    SettingsPanel.register()
    EditModePies.register()

def unregister():

    AddonPreferences.unregister()
    CustomOperators.unregister()
    SculptModePies.unregister()
    SettingsPanel.unregister()
    EditModePies.unregister()


if __name__ == "__main__":
    register()

