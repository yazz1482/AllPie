import bpy
import importlib
from pathlib import Path

from . import Preferences
from . import CurveTools
from . import CustomOperators
from . import retopologytools
from . import RadialMenu
from .core import runtime as ConfigRuntime

# These modules contain Blender classes and are refreshed once before
# registration. Preferences is reloaded after its editor dependencies in
# _refresh_configuration_modules(), so it is deliberately not repeated here.
submodules = (
    CustomOperators,
    retopologytools,
    RadialMenu,
    CurveTools,
)


def _user_config_path():
    """Return AllPie's per-user JSON path, outside the installed addon ZIP."""
    config_directory = bpy.utils.user_resource(
        "CONFIG",
        path="AllPie",
        create=True,
    )
    if not config_directory:
        raise RuntimeError("Blender did not provide a user configuration directory for AllPie")
    return Path(config_directory) / "allpie_config.json"

def _refresh_configuration_modules():
    """Refresh nested configuration modules before validating bundled JSON.

    Blender can keep extension submodules cached when an installed ZIP is
    replaced in-place. The configuration may contain newer optional metadata
    than those cached validators understand, so refresh the dependency chain
    before the first load, not afterward in AddonPreferences.
    """
    from .core import brush_assets as BrushAssets
    from .core import schema as ConfigSchema
    from .core import validation as ConfigValidation
    from .core import registry as ConfigRegistry
    from .core import adapter as ConfigAdapter
    from .core import operator_validation as OperatorValidation
    from .config import loader as ConfigLoader
    from .config import saver as ConfigSaver
    from .editor import (
        menu_data, menu_exchange, menu_editor, operator_data, operator_editor,
        operator_properties, operator_setup, config_editor,
    )

    if getattr(ConfigRuntime, "RUNTIME_API_VERSION", 0) < 18:
        # BrushAssets must reload before ConfigLoader and operator_data because
        # both import brush-reference normalization and identity helpers directly.
        importlib.reload(BrushAssets)
        importlib.reload(ConfigSchema)
        importlib.reload(ConfigValidation)
        importlib.reload(ConfigRegistry)
        importlib.reload(ConfigAdapter)
        importlib.reload(OperatorValidation)
        importlib.reload(ConfigLoader)
        importlib.reload(ConfigSaver)
        importlib.reload(ConfigRuntime)

    if getattr(OperatorValidation, "OPERATOR_VALIDATION_API_VERSION", 0) < 3:
        importlib.reload(OperatorValidation)
    if getattr(menu_data, "ACTION_CONTEXT_CATALOG_API_VERSION", 0) < 7:
        importlib.reload(menu_data)
    if getattr(menu_exchange, "MENU_PACKAGE_API_VERSION", 0) < 3:
        importlib.reload(menu_exchange)
    if getattr(menu_editor, "MENU_EDITOR_API_VERSION", 0) < 18:
        importlib.reload(menu_editor)
    if getattr(operator_data, "OPERATOR_DATA_API_VERSION", 0) < 9:
        importlib.reload(operator_data)
    operator_properties_outdated = getattr(operator_properties, "OPERATOR_PROPERTIES_API_VERSION", 0) < 2
    operator_setup_outdated = getattr(operator_setup, "OPERATOR_SETUP_API_VERSION", 0) < 5
    if operator_properties_outdated or operator_setup_outdated:
        # Dynamic PropertyGroups are stored in bpy.app.driver_namespace so they
        # can survive Python module reloads. Clear their old schemas before
        # loading the new required-property rules.
        try:
            operator_setup.unregister_dynamic_property_groups()
        except Exception as error:
            print(f"[AllPie] Could not clear old operator setup groups: {error}")
    if operator_properties_outdated:
        importlib.reload(operator_properties)
    if operator_setup_outdated:
        importlib.reload(operator_setup)
    if getattr(operator_editor, "OPERATOR_EDITOR_API_VERSION", 0) < 9:
        importlib.reload(operator_editor)
    # config_editor imports load_config by name. Reload it after ConfigLoader
    # and ConfigRuntime so its ConfigLoadResult objects belong to the same
    # module generation used by commit_imported_configuration(). This also
    # prevents Blender's in-place extension upgrade cache from mixing classes.
    importlib.reload(config_editor)

    # Refresh AddonPreferences property declarations after the dependency
    # modules and editor API have been updated.
    importlib.reload(Preferences)


def register():
    # Refresh schema support before reading JSON that may contain newer action
    # metadata. This is still a single configuration read during startup.
    _refresh_configuration_modules()
    user_config = _user_config_path()
    ConfigRuntime.initialize(
        force=True,
        path=user_config,
        fallback_path=ConfigRuntime.DEFAULT_CONFIG_PATH,
    )

    for mod in submodules:
        importlib.reload(mod)
    Preferences.register()
    CustomOperators.register()
    retopologytools.register()
    RadialMenu.register()
    CurveTools.register()

def unregister():
    # Unregister in reverse registration order so keymaps and classes are
    # removed before the preference classes and runtime cache disappear.
    CurveTools.unregister()
    RadialMenu.unregister()
    retopologytools.unregister()
    CustomOperators.unregister()
    Preferences.unregister()
    ConfigRuntime.clear()


if __name__ == "__main__":
    register()

