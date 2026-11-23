"""Runtime configuration state for AllPie.

Configuration JSON is loaded and compiled during addon registration (or an
explicit configuration reload). The radial menu only reads the in-memory
legacy views and never accesses the filesystem or parses JSON.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from ..config.loader import ConfigLoadResult, load_config
from .adapter import build_legacy_views
from .registry import MenuRegistry, build_registry
from .schema import CompiledConfig, keymap_contexts
from .validation import ValidationIssue, validate_config

RUNTIME_API_VERSION = 18

ADDON_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ADDON_ROOT / "config" / "allpie_config.json"
ESSENTIALS_ASSET_PATH = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"

REGISTRY = MenuRegistry()
ACTIVE_CONFIG: Optional[Dict[str, Any]] = None
ACTIVE_CONFIG_PATH: Optional[Path] = None  # Persistent user-config destination.
CONFIG_SOURCE_PATH: Optional[Path] = None
LOADED_USER_CONFIG = False
USER_CONFIG_PATH: Optional[Path] = None
CONFIG_RECOVERY_REQUIRED = False
CONFIG_RECOVERY_ERROR = ""
ACTIVE_VALIDATION_WARNINGS: Tuple[ValidationIssue, ...] = ()
INITIALIZED = False

# These dictionaries are imported by RadialMenu.py. They are updated in place
# so references remain valid across configuration rebuilds.
MENUS: Dict[str, list] = {}
SPACE_MENUS: Dict[str, list] = {}
MENU_NAMES: Dict[str, str] = {}


def _replace_mapping(target: dict, source: Mapping[str, Any]) -> None:
    target.clear()
    target.update(source)


def get_blender_event_identifiers() -> Optional[frozenset[str]]:
    """Return Blender's registered Event.type enum identifiers.

    The pure JSON validator remains usable outside Blender by accepting no
    runtime identifier set. Inside Blender, this reads the same RNA enum used
    by KeyMapItems.new(type=...).
    """
    try:
        import bpy
    except ImportError:
        return None

    try:
        event_type = bpy.types.Event.bl_rna.properties["type"]
        enum_items = event_type.enum_items
        identifiers = frozenset(str(identifier) for identifier in enum_items.keys())
        if not identifiers:
            raise RuntimeError("Blender returned an empty Event.type enum")
        return identifiers
    except Exception as error:
        raise RuntimeError(
            f"Could not read Blender's Event.type enum for key validation: {error}"
        ) from error


def _prepare_config(config: Mapping[str, Any]):
    """Validate and compile a new config without publishing it."""
    config_copy = deepcopy(dict(config))
    report = validate_config(
        config_copy,
        valid_event_types=get_blender_event_identifiers(),
    )
    if not report.valid or report.config is None:
        details = "\n".join(str(issue) for issue in report.errors)
        raise ValueError(f"Cannot activate invalid AllPie configuration:\n{details}")
    normalized = report.config
    compiled = build_registry(normalized)
    menus, spaced_menus, names = build_legacy_views(compiled)
    return normalized, compiled, menus, spaced_menus, names, tuple(report.warnings)


def _publish_prepared(prepared, path: Optional[Path] = None) -> CompiledConfig:
    """Publish a previously prepared config after all dependent steps succeed."""
    global ACTIVE_CONFIG, ACTIVE_CONFIG_PATH, ACTIVE_VALIDATION_WARNINGS, INITIALIZED
    normalized, compiled, menus, spaced_menus, names, warnings = prepared
    REGISTRY.activate(compiled)
    ACTIVE_CONFIG = normalized
    ACTIVE_VALIDATION_WARNINGS = tuple(warnings)
    if path is not None:
        ACTIVE_CONFIG_PATH = Path(path)
    _replace_mapping(MENUS, menus)
    _replace_mapping(SPACE_MENUS, spaced_menus)
    _replace_mapping(MENU_NAMES, names)
    INITIALIZED = True
    return compiled


def _commit_config(config: Mapping[str, Any], path: Optional[Path] = None) -> CompiledConfig:
    """Build a new registry and compatibility views before publishing them."""
    return _publish_prepared(_prepare_config(config), path)


def initialize(
    *,
    force: bool = False,
    path: Optional[Path] = None,
    fallback_path: Optional[Path] = None,
) -> ConfigLoadResult:
    """Load the user config, recovering to bundled defaults if it is invalid.

    A corrupt existing user file is never modified during startup. Bundled
    defaults are activated in memory, and persistence is blocked until the
    user explicitly imports a valid config or restores bundled defaults.
    """
    global ACTIVE_CONFIG_PATH, CONFIG_SOURCE_PATH, LOADED_USER_CONFIG, USER_CONFIG_PATH
    global CONFIG_RECOVERY_REQUIRED, CONFIG_RECOVERY_ERROR

    requested_path = Path(path).expanduser() if path is not None else None
    if INITIALIZED and not force:
        if requested_path is None or requested_path == ACTIVE_CONFIG_PATH:
            return ConfigLoadResult(
                config=deepcopy(ACTIVE_CONFIG or {}),
                path=CONFIG_SOURCE_PATH or ACTIVE_CONFIG_PATH,
                warnings=(),
                migrated=False,
            )

    valid_event_types = get_blender_event_identifiers()
    CONFIG_RECOVERY_REQUIRED = False
    CONFIG_RECOVERY_ERROR = ""

    if requested_path is not None and fallback_path is not None:
        fallback = Path(fallback_path).expanduser()
        USER_CONFIG_PATH = requested_path
        if requested_path.exists():
            try:
                result = load_config(requested_path, valid_event_types=valid_event_types)
                source_path = requested_path
                loaded_user_config = True
                if result.migrated:
                    # Persist only a successfully validated migration.
                    try:
                        from ..config.saver import save_config
                        save_config(result.config, requested_path, backup=True)
                    except Exception as error:
                        print(f"[AllPie] Configuration migrated in memory but could not be saved: {error}")
            except Exception as user_error:
                # A malformed or incompatible user file must not prevent the
                # addon from registering. Preserve it byte-for-byte and load
                # bundled defaults in memory. Do not set ACTIVE_CONFIG_PATH,
                # so normal preference/menu autosaves cannot overwrite it.
                try:
                    result = load_config(fallback, valid_event_types=valid_event_types)
                except Exception as fallback_error:
                    raise RuntimeError(
                        "AllPie could not load the user configuration and the bundled defaults "
                        f"also failed. User config error: {user_error}. Bundled config error: {fallback_error}"
                    ) from fallback_error
                source_path = fallback
                loaded_user_config = False
                CONFIG_RECOVERY_REQUIRED = True
                CONFIG_RECOVERY_ERROR = str(user_error)
                recovery_warning = ValidationIssue(
                    "warning",
                    str(requested_path),
                    "user configuration could not be loaded; bundled defaults are active in memory and the original file has been preserved",
                )
                result = ConfigLoadResult(
                    config=result.config,
                    path=result.path,
                    warnings=tuple(result.warnings) + (recovery_warning,),
                    migrated=False,
                )
        else:
            result = load_config(fallback, valid_event_types=valid_event_types)
            source_path = fallback
            loaded_user_config = False

        if CONFIG_RECOVERY_REQUIRED:
            _commit_config(result.config, None)
            ACTIVE_CONFIG_PATH = None
        else:
            _commit_config(result.config, requested_path)
        CONFIG_SOURCE_PATH = source_path
        LOADED_USER_CONFIG = loaded_user_config
        return ConfigLoadResult(
            config=deepcopy(ACTIVE_CONFIG or {}),
            path=source_path,
            warnings=result.warnings,
            migrated=result.migrated,
        )

    config_path = requested_path if requested_path is not None else DEFAULT_CONFIG_PATH
    result = load_config(config_path, valid_event_types=valid_event_types)
    _commit_config(result.config, None)
    ACTIVE_CONFIG_PATH = None
    CONFIG_SOURCE_PATH = config_path
    USER_CONFIG_PATH = None
    LOADED_USER_CONFIG = False
    return result


def reload_configuration(path: Optional[Path] = None) -> ConfigLoadResult:
    """Explicitly reload user configuration with bundled-default recovery."""
    target = Path(path).expanduser() if path is not None else (
        USER_CONFIG_PATH or ACTIVE_CONFIG_PATH or DEFAULT_CONFIG_PATH
    )
    if USER_CONFIG_PATH is not None and target == USER_CONFIG_PATH:
        return initialize(force=True, path=target, fallback_path=DEFAULT_CONFIG_PATH)
    return initialize(force=True, path=target)


def replace_configuration(config: Mapping[str, Any]) -> CompiledConfig:
    """Apply a decoded configuration to the active session without saving it."""
    return _commit_config(config)


def replace_and_save_configuration(
    config: Mapping[str, Any],
    path: Optional[Path] = None,
    *,
    backup: bool = True,
) -> CompiledConfig:
    """Validate, compile, persist and then publish a new configuration.

    The active registry is not replaced unless both compilation and the atomic
    file save succeed. This keeps the session and user config in sync.
    """
    global CONFIG_SOURCE_PATH, LOADED_USER_CONFIG, USER_CONFIG_PATH
    global CONFIG_RECOVERY_REQUIRED, CONFIG_RECOVERY_ERROR

    recovery_target = USER_CONFIG_PATH
    destination = Path(path).expanduser() if path is not None else ACTIVE_CONFIG_PATH
    if destination is None:
        if CONFIG_RECOVERY_REQUIRED:
            raise RuntimeError(
                "AllPie is using bundled defaults because the user configuration is invalid. "
                "Your original file is preserved. Use Import JSON or Restore Bundled Defaults "
                "on the Configuration page before saving further changes."
            )
        raise RuntimeError("No persistent AllPie configuration path has been configured")
    if CONFIG_RECOVERY_REQUIRED:
        if recovery_target is None or destination.resolve() != Path(recovery_target).expanduser().resolve():
            raise RuntimeError(
                "Recovery mode only allows an explicit import or restore to the original user "
                "configuration path. The damaged file must remain preserved until then."
            )

    if CONFIG_RECOVERY_REQUIRED:
        # The original malformed user file is the recovery source; always keep
        # a byte-for-byte backup before an explicit replacement.
        backup = True

    prepared = _prepare_config(config)
    normalized = prepared[0]
    from ..config.saver import save_config
    save_config(normalized, destination, backup=backup)
    USER_CONFIG_PATH = destination
    CONFIG_SOURCE_PATH = destination
    LOADED_USER_CONFIG = True
    if CONFIG_RECOVERY_REQUIRED and recovery_target is not None and destination.resolve() == Path(recovery_target).expanduser().resolve():
        CONFIG_RECOVERY_REQUIRED = False
        CONFIG_RECOVERY_ERROR = ""
    return _publish_prepared(prepared, destination)


def save_active_configuration(*, backup: bool = True) -> Path:
    """Persist the current active config to its user configuration path."""
    if ACTIVE_CONFIG is None:
        raise RuntimeError("AllPie configuration has not been initialized")
    if ACTIVE_CONFIG_PATH is None:
        if CONFIG_RECOVERY_REQUIRED:
            raise RuntimeError(
                "AllPie is using bundled defaults because the user configuration is invalid. "
                "Your original file is preserved. Use Import JSON or Restore Bundled Defaults "
                "before saving further changes."
            )
        raise RuntimeError("No persistent AllPie configuration path has been configured")
    from ..config.saver import save_config
    saved = save_config(ACTIVE_CONFIG, ACTIVE_CONFIG_PATH, backup=backup)
    global CONFIG_SOURCE_PATH, LOADED_USER_CONFIG, USER_CONFIG_PATH
    CONFIG_SOURCE_PATH = saved
    USER_CONFIG_PATH = saved
    LOADED_USER_CONFIG = True
    return saved


def get_config_copy() -> Dict[str, Any]:
    if ACTIVE_CONFIG is None:
        raise RuntimeError("AllPie configuration has not been initialized")
    return deepcopy(ACTIVE_CONFIG)


def get_keybind_definitions() -> list[tuple]:
    """Return keybind definitions sourced from the loaded menu configuration.

    The tuple keeps the existing Preferences/RadialMenu call shape and appends
    the configured default enabled state as its seventh item.
    """
    if ACTIVE_CONFIG is None:
        return []

    definitions = []
    for menu_id, menu in ACTIVE_CONFIG["Menus"].items():
        for keymap_name in keymap_contexts(menu.get("keymap", "")):
            definitions.append(_make_keybind_definition(menu_id, menu, keymap_name=keymap_name))

    for addon_id, addon in ACTIVE_CONFIG["ThirdParty"].items():
        for menu_id, menu in addon["Menus"].items():
            qualified_menu_id = f"{addon_id}:{menu_id}"
            for keymap_name in keymap_contexts(menu.get("keymap", "")):
                definitions.append(
                    _make_keybind_definition(
                        qualified_menu_id,
                        menu,
                        owner_enabled=addon.get("enabled", True),
                        keymap_name=keymap_name,
                    )
                )

    return definitions


def _make_keybind_definition(
    menu_id: str,
    menu: Mapping[str, Any],
    *,
    owner_enabled: bool = True,
    keymap_name: Optional[str] = None,
) -> tuple:
    modifiers = {
        name.lower(): name.upper() in menu.get("keymodifiers", [])
        for name in ("shift", "ctrl", "alt", "oskey", "hyper")
    }
    return (
        menu_id,
        keymap_name or menu["keymap"],
        menu["key"],
        "PRESS",
        menu_id,
        modifiers,
        bool(menu.get("enabled", True) and owner_enabled),
    )


def get_menu_name(menu_id: str) -> str:
    menu = REGISTRY.get_menu(menu_id)
    return menu.name if menu is not None else ""


def _update_brushes_in_config(
    config: Dict[str, Any],
    normal_brushes: Sequence[str],
    spaced_brushes: Sequence[str],
) -> bool:
    if len(normal_brushes) != 8 or len(spaced_brushes) != 7:
        raise ValueError("Essential brushes require 8 normal and 7 spaced names")

    menu_data = config["Menus"].get("SCULPT.ESSENTIALS_BRUSH")
    if menu_data is None:
        return False

    changed = False
    assignments = (
        (menu_data.get("slots", {}), normal_brushes, 1),
        # The spaced brush preference fields map to visible radial slots 2–8;
        # visible slot 1 (JSON slot 1 / legacy index 0) is the Asset Shelf.
        (menu_data.get("spaced_slots", {}), spaced_brushes, 2),
    )

    for slot_map, brush_names, start_slot in assignments:
        for offset, brush_name in enumerate(brush_names):
            action_id = slot_map.get(str(start_slot + offset))
            if action_id is None:
                continue
            action = config["Operators"].get(action_id)
            if action is None:
                continue
            relative_asset = ESSENTIALS_ASSET_PATH + brush_name
            properties = action.setdefault("properties", {})
            if action.get("name") != brush_name:
                action["name"] = brush_name
                changed = True
            # Picker-only metadata follows the currently assigned Essentials
            # brush while the legacy radial label remains the original name.
            # Keep the picker-facing label concise so natural searches such as
            # "draw brush" match exactly. The menu context already tells the
            # user these are Sculpt actions; repeating "Sculpt" in every label
            # makes useful multi-word searches less predictable.
            search_name = f"{brush_name.replace('/', ' / ').title()} Brush"
            description = (
                f"Activate the {brush_name} brush preset from Blender's Essentials "
                "sculpt brush library."
            )
            if action.get("search_name") != search_name:
                action["search_name"] = search_name
                changed = True
            if action.get("description") != description:
                action["description"] = description
                changed = True
            if properties.get("relative_asset_identifier") != relative_asset:
                properties["relative_asset_identifier"] = relative_asset
                changed = True
    return changed


def _copy_preferences_to_config(config: Dict[str, Any], preferences: Any) -> bool:
    """Copy persisted Blender AddonPreferences values into JSON data."""
    if preferences is None:
        return False

    config_preferences = config["Preferences"]
    before = deepcopy(config_preferences)
    config_preferences["radial"]["hold_time"] = float(preferences.hold_time)
    config_preferences["radial"]["deadzone"] = int(preferences.deadzone)

    color_fields = (
        "slot_color",
        "active_slot_color",
        "spaced_slot_color",
        "spaced_active_slot_color",
        "font_color",
        "active_font_color",
        "spaced_font_color",
        "spaced_active_font_color",
        "outline_color",
        "spaced_outline_color",
        "mark_color",
    )
    for field_name in color_fields:
        config_preferences["colors"][field_name] = [
            float(value) for value in getattr(preferences, field_name)
        ]

    return config_preferences != before


def sync_preferences_to_config(preferences: Any, *, persist: bool = False) -> bool:
    """Synchronize UI properties into JSON, optionally saving atomically.

    Menu shortcuts are deliberately not read from a separate Preferences
    collection: their only source of truth is the menu configuration itself.
    """
    if ACTIVE_CONFIG is None or preferences is None:
        return False

    updated = get_config_copy()
    changed = _copy_preferences_to_config(updated, preferences)
    if not changed:
        if persist:
            save_active_configuration()
        return False

    if persist:
        replace_and_save_configuration(updated)
    else:
        _commit_config(updated)
    return True


def apply_config_preferences(preferences: Any) -> None:
    """Populate Blender RNA preference controls from the active JSON config."""
    if ACTIVE_CONFIG is None or preferences is None:
        return

    config_preferences = ACTIVE_CONFIG["Preferences"]
    preferences.config_loading = True
    try:
        preferences.hold_time = float(config_preferences["radial"]["hold_time"])
        preferences.deadzone = int(config_preferences["radial"]["deadzone"])
        for field_name, color in config_preferences["colors"].items():
            if hasattr(preferences, field_name):
                setattr(preferences, field_name, tuple(color))
    finally:
        preferences.config_loading = False


def migrate_legacy_preferences(preferences: Any) -> bool:
    """Migrate old Blender-stored preference values once into first-run JSON.

    Deprecated Blender-stored keybind and brush values are read only here.
    After successful persistence, the legacy keybind collection is cleared;
    future menu shortcuts and brush assignments come directly from JSON menus.
    """
    if ACTIVE_CONFIG is None or preferences is None:
        return False

    updated = get_config_copy()
    _copy_preferences_to_config(updated, preferences)

    # Preserve user-customized brush assignments from pre-JSON addon
    # preferences exactly once. These hidden RNA fields are retained only as
    # an upgrade bridge; the new Menus editor owns brush assignments.
    legacy_normal = [
        getattr(preferences, f"EssentialBrush_Slot{slot}", None)
        for slot in range(1, 9)
    ]
    legacy_spaced = [
        getattr(preferences, f"EssentialSpaceBrush_Slot{slot}", None)
        for slot in range(1, 8)
    ]
    if all(isinstance(name, str) and name for name in legacy_normal + legacy_spaced):
        _update_brushes_in_config(updated, legacy_normal, legacy_spaced)

    valid_event_types = get_blender_event_identifiers()
    for legacy in getattr(preferences, "keybinds", ()):
        legacy_key = str(getattr(legacy, "key", "") or "")
        if legacy_key == "NONE" or (valid_event_types is not None and legacy_key not in valid_event_types):
            # A pre-JSON preference may contain an obsolete or malformed event
            # identifier. Ignore that one legacy shortcut rather than allowing
            # it to abort first-run migration or register an invalid keymap.
            print(f"[AllPie] Ignored legacy shortcut with invalid Blender event type: {legacy_key!r}")
            continue
        menu_id = str(getattr(legacy, "menu_id", "") or getattr(legacy, "pref_id", ""))
        if not menu_id:
            continue
        menu_data = updated["Menus"].get(menu_id)
        if menu_data is None and ":" in menu_id:
            addon_id, local_id = menu_id.split(":", 1)
            menu_data = updated["ThirdParty"].get(addon_id, {}).get("Menus", {}).get(local_id)
        if menu_data is None:
            # Legacy records sometimes carried only the pref_id; accept it if
            # the id matches a stable current menu identifier.
            pref_id = str(getattr(legacy, "pref_id", ""))
            menu_data = updated["Menus"].get(pref_id)
            menu_id = pref_id
        if menu_data is None:
            continue
        menu_data["key"] = legacy_key
        menu_data["keymodifiers"] = [
            name for name, enabled in (
                ("SHIFT", bool(getattr(legacy, "shift", False))),
                ("CTRL", bool(getattr(legacy, "ctrl", False))),
                ("ALT", bool(getattr(legacy, "alt", False))),
                ("OSKEY", bool(getattr(legacy, "oskey", False))),
                ("HYPER", bool(getattr(legacy, "hyper", False))),
            ) if enabled
        ]
        menu_data["enabled"] = bool(getattr(legacy, "enabled", menu_data.get("enabled", True)))

    replace_and_save_configuration(updated)
    try:
        preferences.keybinds.clear()
    except (AttributeError, TypeError):
        pass
    return True


def export_configuration(
    path: Path,
    preferences: Any = None,
    *,
    backup: bool = False,
    config_snapshot: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Export a complete configuration snapshot to a selected JSON file.

    ``config_snapshot`` is used by the Preferences UI when the Menus editor has
    an unapplied draft. In that case the detached draft is exported without
    silently applying it to the live session or overwriting the user's active
    configuration. General radial preferences are still copied from their
    live RNA controls into the exported snapshot.
    """
    if ACTIVE_CONFIG is None:
        raise RuntimeError("AllPie configuration has not been initialized")

    if config_snapshot is not None:
        snapshot = deepcopy(dict(config_snapshot))
        _copy_preferences_to_config(snapshot, preferences)
        report = validate_config(
            snapshot,
            valid_event_types=get_blender_event_identifiers(),
        )
        if not report.valid or report.config is None:
            details = "\n".join(str(issue) for issue in report.errors)
            raise ValueError(f"Cannot export invalid AllPie configuration:\n{details}")
        snapshot = report.config
    elif preferences is not None:
        if CONFIG_RECOVERY_REQUIRED:
            # Export remains available during recovery, but must not write the
            # active bundled fallback over the damaged user file. Snapshot live
            # RNA settings into a detached copy and export only to the chosen
            # destination.
            snapshot = get_config_copy()
            _copy_preferences_to_config(snapshot, preferences)
        else:
            # Flush current RNA values into the live runtime and user file
            # before making the portable export snapshot.
            sync_preferences_to_config(preferences, persist=True)
            snapshot = get_config_copy()
    else:
        snapshot = get_config_copy()

    destination = Path(path).expanduser()
    if CONFIG_RECOVERY_REQUIRED and USER_CONFIG_PATH is not None:
        if destination.resolve() == Path(USER_CONFIG_PATH).expanduser().resolve():
            raise RuntimeError(
                "Cannot export over the damaged user configuration while AllPie is in recovery mode. "
                "Choose a different export path; the original file must remain preserved."
            )
    if ACTIVE_CONFIG_PATH is not None and destination.resolve() == ACTIVE_CONFIG_PATH.resolve():
        if config_snapshot is None:
            return destination
        # The caller explicitly chose the live config path. Persist and publish
        # the supplied draft there instead of pretending it was already saved.
        replace_and_save_configuration(snapshot, destination, backup=backup)
        return destination

    from ..config.saver import save_config
    return save_config(snapshot, destination, backup=backup)


def commit_imported_configuration(
    load_result: ConfigLoadResult,
    *,
    destination: Optional[Path] = None,
    backup: bool = True,
) -> CompiledConfig:
    """Persist and activate a previously loaded, validated JSON config.

    The loader performs parsing, duplicate-key detection, migration and schema
    validation before this function is called. The runtime then compiles the
    normalized data, writes the user's configuration atomically, and only
    publishes the new registry after the file save succeeds.
    """
    if not isinstance(load_result, ConfigLoadResult):
        raise TypeError("load_result must be returned by config.loader.load_config")

    target = Path(destination).expanduser() if destination is not None else (
        USER_CONFIG_PATH or ACTIVE_CONFIG_PATH
    )
    if target is None:
        raise RuntimeError("No persistent AllPie configuration path has been configured")

    return replace_and_save_configuration(load_result.config, target, backup=backup)


def import_configuration(
    source: Path,
    *,
    destination: Optional[Path] = None,
    backup: bool = True,
) -> ConfigLoadResult:
    """Load, validate, migrate, persist and activate an external JSON file."""
    result = load_config(
        source,
        valid_event_types=get_blender_event_identifiers(),
    )
    commit_imported_configuration(result, destination=destination, backup=backup)
    return result


def clear() -> None:
    """Release the compiled cache when the addon is unregistered."""
    global ACTIVE_CONFIG, ACTIVE_CONFIG_PATH, CONFIG_SOURCE_PATH
    global INITIALIZED, LOADED_USER_CONFIG, USER_CONFIG_PATH
    global CONFIG_RECOVERY_REQUIRED, CONFIG_RECOVERY_ERROR
    REGISTRY.clear()
    ACTIVE_CONFIG = None
    ACTIVE_CONFIG_PATH = None
    CONFIG_SOURCE_PATH = None
    USER_CONFIG_PATH = None
    LOADED_USER_CONFIG = False
    CONFIG_RECOVERY_REQUIRED = False
    CONFIG_RECOVERY_ERROR = ""
    INITIALIZED = False
    MENUS.clear()
    SPACE_MENUS.clear()
    MENU_NAMES.clear()
