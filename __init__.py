import bpy
import importlib
from . import AddonPreferences
from . import SculptPies
from . import EditModePies
from . import CustomOperators
from . import SettingsPanel

submodules = (
AddonPreferences,
CustomOperators,
SculptPies,
SettingsPanel
# EditModePies,
)

def register():
    for mod in submodules:
        if mod.__name__ in locals() or mod.__name__ in __import__('sys').modules:
            importlib.reload(mod)    
    AddonPreferences.register()
    CustomOperators.register()
    SculptPies.register()
    SettingsPanel.register()
    # EditModePies.register()

def unregister():

    AddonPreferences.unregister()
    CustomOperators.unregister()
    SculptPies.unregister()
    SettingsPanel.unregister()
    # EditModePies.unregister()


if __name__ == "__main__":
    register()

