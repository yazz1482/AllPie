"""Read and migrate AllPie JSON configuration files.

Loading is an explicit startup/import operation. The radial menu runtime must
never call these functions while opening or executing a pie menu.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from ..core.brush_assets import BRUSH_ASSET_OPERATOR_ID, normalize_operator_properties, operator_properties_identity
from ..core.schema import COMMON_KEYMAP, SCHEMA_VERSION, make_default_config
from ..core.validation import ValidationIssue, validate_config


class ConfigLoadError(ValueError):
    """Raised when a configuration cannot be read, migrated, or validated."""


@dataclass(frozen=True)
class ConfigLoadResult:
    config: Dict[str, Any]
    path: Optional[Path]
    warnings: tuple[ValidationIssue, ...] = ()
    migrated: bool = False


def _reject_duplicate_keys(pairs: List[tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigLoadError(f"Duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    raise ConfigLoadError(f"Invalid non-finite JSON number: {value}")


# Register one migration function per source version when a future schema
# version is introduced. A migration receives a new dict and must return the
# next schema version's dict.
def _migrate_v1_to_v2(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove the duplicated Essential Sculpt brush preference mirror.

    Brush choices are now ordinary operator-preset assignments stored in the
    SCULPT.ESSENTIALS_BRUSH menu slots. The legacy Preferences.brushes arrays
    duplicated those assignments and are no longer part of schema v2.
    Existing menu slots and operator asset identifiers are left untouched.
    """
    preferences = config.get("Preferences")
    if isinstance(preferences, dict):
        preferences.pop("brushes", None)
    config["schema_version"] = 2
    return config


_COMMON_BUILTIN_MENU_GROUPS = {
    "OBJECT.SHADING": (
        "OBJECT.SHADING",
        "EDIT.SHADING",
        "SCULPT.SHADING",
        "TEXTUREPAINT.SHADING",
        "VERTEXPAINT.SHADING",
        "WEIGHTPAINT.SHADING",
    ),
    "OBJECT.VIEW": (
        "OBJECT.VIEW",
        "EDIT.VIEW",
        "SCULPT.VIEW",
        "TEXTUREPAINT.VIEW",
        "VERTEXPAINT.VIEW",
        "WEIGHTPAINT.VIEW",
    ),
    "OBJECT.MODE": (
        "OBJECT.MODE",
        "EDIT.MODE",
        "SCULPT.MODE",
        "TEXTUREPAINT.MODE",
        "VERTEXPAINT.MODE",
        "WEIGHTPAINT.MODE",
    ),
}


def _migrate_v2_to_v3(config: Dict[str, Any]) -> Dict[str, Any]:
    """Consolidate the stock cross-mode Shading, View and Mode menus.

    Earlier configurations stored six identical copies of each of these
    menus, one per built-in keymap context. They are now represented by one
    menu with the reserved Common scope, which the runtime registers in all
    six contexts.

    Only a complete set of six records that match in every field except
    ``keymap`` is collapsed. If a user customized one mode's copy differently,
    all six records are preserved rather than silently discarding that work.
    The Object Mode ID is retained as the stable ID for each consolidated menu.
    """
    menus = config.get("Menus")
    if isinstance(menus, dict):
        for canonical_id, group_ids in _COMMON_BUILTIN_MENU_GROUPS.items():
            if not all(menu_id in menus and isinstance(menus[menu_id], dict) for menu_id in group_ids):
                continue

            records = [menus[menu_id] for menu_id in group_ids]
            comparable_records = []
            for record in records:
                comparable = deepcopy(record)
                comparable.pop("keymap", None)
                comparable_records.append(comparable)

            reference = comparable_records[0]
            if not all(record == reference for record in comparable_records[1:]):
                continue

            common_record = deepcopy(menus[canonical_id])
            common_record["keymap"] = COMMON_KEYMAP
            menus[canonical_id] = common_record

            for duplicate_id in group_ids:
                if duplicate_id != canonical_id:
                    menus.pop(duplicate_id, None)

    config["schema_version"] = 3
    return config


def _migrate_v3_to_v4(config: Dict[str, Any]) -> Dict[str, Any]:
    """Mark the built-in Essentials Brushes menu as a brush-only menu.

    The menu already consists of brush asset activation presets, with the
    existing Asset Shelf popover retained as an assigned action. This migration
    changes only the menu-type flag; it does not alter slots, operator presets,
    shortcuts, enabled state, or any user customizations.

    Only apply the flag when the menu is still assigned to one of AllPie's
    supported paint contexts. A user who reassigned this stable menu ID to an
    unrelated keymap keeps that assignment without making the configuration
    invalid.
    """
    menus = config.get("Menus")
    if isinstance(menus, dict):
        menu = menus.get("SCULPT.ESSENTIALS_BRUSH")
        if isinstance(menu, dict):
            keymap = str(menu.get("keymap", "")).strip().casefold()
            supported_contexts = {
                "sculpt",
                "image paint",
                "vertex paint",
                "weight paint",
            }
            if keymap in supported_contexts:
                menu["is_brush_menu"] = True

    config["schema_version"] = 4
    return config


def _migrate_v4_to_v5(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize brush asset references and remove confirmed 1.5.5 duplicates.

    AllPie 1.5.5 could store an ``asset_library_identifier`` for non-CUSTOM
    brush libraries. Blender only uses that identifier for CUSTOM libraries,
    so it is not part of an Essentials/Local asset's identity. This migration
    normalizes those references and merges records with the same asset
    reference, invocation mode, and visible search label.

    Slot references are redirected before duplicate presets are removed.
    Distinct custom library identifiers, different brush assets, and entries
    with different visible labels are left separate.
    """
    operators = config.get("Operators")
    if not isinstance(operators, dict):
        config["schema_version"] = 5
        return config

    groups: Dict[tuple[Any, ...], list[tuple[str, Dict[str, Any]]]] = {}
    for action_id, action in operators.items():
        if not isinstance(action, dict) or action.get("operator_id") != BRUSH_ASSET_OPERATOR_ID:
            continue

        raw_properties = action.get("properties", {})
        properties = normalize_operator_properties(BRUSH_ASSET_OPERATOR_ID, raw_properties)
        action["properties"] = properties

        visible_label = str(action.get("search_name") or action.get("name") or action_id).strip().casefold()
        # JSON serialization gives nested property dictionaries a stable,
        # hashable identity without dropping any meaningful operator values.
        identity = operator_properties_identity(BRUSH_ASSET_OPERATOR_ID, properties)
        properties_key = json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        key = (bool(action.get("invoke", False)), properties_key, visible_label)
        groups.setdefault(key, []).append((str(action_id), action))

    # Prefer an existing menu-referenced preset over one created by the
    # redundant asset-assignment path. If all records are user-created, keep the earliest
    # generated ID so repeated assignments converge on one stable record.
    generated_id_pattern = re.compile(r"^BRUSH_ASSET_ACTIVATE(?:_\d+)?$", re.IGNORECASE)
    essential_menu_references = set()
    menus = config.get("Menus", {})
    essential_menu = menus.get("SCULPT.ESSENTIALS_BRUSH", {}) if isinstance(menus, dict) else {}
    if isinstance(essential_menu, dict):
        for field in ("slots", "spaced_slots"):
            slot_map = essential_menu.get(field, {})
            if isinstance(slot_map, dict):
                essential_menu_references.update(
                    value for value in slot_map.values() if isinstance(value, str)
                )

    replacement_ids: Dict[str, str] = {}
    for records in groups.values():
        # Identical canonical brush references are safe to consolidate even
        # when neither preset needed a metadata-field migration. This also
        # repairs duplicates created solely by Windows-vs-POSIX path separators.
        if len(records) < 2:
            continue

        def canonical_priority(record):
            action_id, action = record
            return (
                0 if action_id in essential_menu_references else 1,
                0 if action.get("user_defined") is not True else 1,
                1 if generated_id_pattern.fullmatch(action_id) else 0,
                action_id,
            )

        canonical_id, canonical_action = min(records, key=canonical_priority)
        canonical_contexts = canonical_action.setdefault("contexts", [])
        if not isinstance(canonical_contexts, list):
            canonical_contexts = []
            canonical_action["contexts"] = canonical_contexts
        known_contexts = {str(value).casefold() for value in canonical_contexts if isinstance(value, str)}

        for duplicate_id, duplicate_action in records:
            if duplicate_id == canonical_id:
                continue
            for context_name in duplicate_action.get("contexts", []):
                if not isinstance(context_name, str) or not context_name.strip():
                    continue
                if context_name.casefold() not in known_contexts:
                    canonical_contexts.append(context_name)
                    known_contexts.add(context_name.casefold())
            replacement_ids[duplicate_id] = canonical_id

    if replacement_ids:
        def rewrite_menu_slots(menu_collection):
            if not isinstance(menu_collection, dict):
                return
            for menu in menu_collection.values():
                if not isinstance(menu, dict):
                    continue
                for field in ("slots", "spaced_slots"):
                    slot_map = menu.get(field, {})
                    if not isinstance(slot_map, dict):
                        continue
                    for slot_number, action_id in list(slot_map.items()):
                        if action_id in replacement_ids:
                            slot_map[slot_number] = replacement_ids[action_id]

        rewrite_menu_slots(config.get("Menus", {}))
        third_party = config.get("ThirdParty", {})
        if isinstance(third_party, dict):
            for addon in third_party.values():
                if isinstance(addon, dict):
                    rewrite_menu_slots(addon.get("Menus", {}))

        for duplicate_id in replacement_ids:
            operators.pop(duplicate_id, None)

    config["schema_version"] = 5
    return config


def _migrate_v5_to_v6(config: Dict[str, Any]) -> Dict[str, Any]:
    """Re-run brush-reference normalization for configurations saved by 1.5.6.

    The first deduplication migration only removed empty non-CUSTOM library
    identifiers. Blender may expose a non-empty identifier for Essentials or
    Local assets too, even though the Asset Shelf API says it is ignored for
    those library types. Schema v6 canonicalizes those records and removes
    confirmed duplicate brush presets from already-migrated user configs.
    """
    _migrate_v4_to_v5(config)
    config["schema_version"] = 6
    return config


def _migrate_v6_to_v7(config: Dict[str, Any]) -> Dict[str, Any]:
    """Canonicalize brush asset path separators and merge duplicate presets."""
    _migrate_v4_to_v5(config)
    config["schema_version"] = 7
    return config


def _migrate_v7_to_v8(config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge built-in brush presets whose asset identifiers differ only by case.

    Blender's Asset Shelf can return title-cased brush names (for example
    ``Brush/Grab``), while the bundled AllPie brush presets use uppercase
    asset names (``Brush/GRAB``). These paths identify the same built-in asset.
    Schema v8 compares non-CUSTOM asset identifiers case-insensitively,
    redirects menu slots to the existing canonical presets, and preserves the
    original path spelling for Blender activation. Custom libraries remain
    case-sensitive and are never merged by this rule.
    """
    _migrate_v4_to_v5(config)
    config["schema_version"] = 8
    return config


def _migrate_v8_to_v9(config: Dict[str, Any]) -> Dict[str, Any]:
    """Enable the Paint Brushes Brush Menu and consolidate duplicate shelves.

    Brush Menus support brush asset activation and Asset Shelf popover actions.
    The migration marks the built-in Paint Brushes menu when it still targets a
    supported paint context. It also merges duplicate global Asset Shelf popup
    presets with the same operator, invocation mode and properties, redirects
    their menu references and preserves combined context/user-defined metadata.
    """
    menus = config.get("Menus")
    if isinstance(menus, dict):
        menu = menus.get("SCULPT.PAINT_BRUSH")
        if isinstance(menu, dict):
            keymap = str(menu.get("keymap", "")).strip().casefold()
            supported_contexts = {
                "sculpt",
                "image paint",
                "vertex paint",
                "weight paint",
            }
            if keymap in supported_contexts:
                menu["is_brush_menu"] = True

    operators = config.get("Operators")
    if isinstance(operators, dict):
        shelf_groups: Dict[tuple[Any, ...], list[tuple[str, Dict[str, Any]]]] = {}
        for action_id, action in operators.items():
            if not isinstance(action, dict):
                continue
            if action.get("operator_id") != "wm.call_asset_shelf_popover":
                continue
            properties = action.get("properties", {})
            if not isinstance(properties, dict):
                continue
            try:
                properties_key = json.dumps(
                    properties,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            except (TypeError, ValueError):
                continue
            identity = (bool(action.get("invoke", False)), properties_key)
            shelf_groups.setdefault(identity, []).append((str(action_id), action))

        replacement_ids: Dict[str, str] = {}
        for records in shelf_groups.values():
            if len(records) < 2:
                continue
            canonical_id = next(
                (action_id for action_id, _action in records if action_id == "ASSET_SHELF"),
                records[0][0],
            )
            canonical_action = operators[canonical_id]
            contexts = canonical_action.setdefault("contexts", [])
            if not isinstance(contexts, list):
                contexts = []
                canonical_action["contexts"] = contexts
            known_contexts = {
                value.casefold() for value in contexts if isinstance(value, str)
            }
            for action_id, action in records:
                if action_id == canonical_id:
                    continue
                replacement_ids[action_id] = canonical_id
                action_contexts = action.get("contexts", [])
                if isinstance(action_contexts, list):
                    for context_name in action_contexts:
                        if (
                            isinstance(context_name, str)
                            and context_name.casefold() not in known_contexts
                        ):
                            contexts.append(context_name)
                            known_contexts.add(context_name.casefold())
                if action.get("user_defined") is True:
                    canonical_action["user_defined"] = True

        if replacement_ids:
            def rewrite_slots(menu_collection: Any, local_operators: Any = None) -> None:
                if not isinstance(menu_collection, dict):
                    return
                local_operators = local_operators if isinstance(local_operators, dict) else {}
                for menu_record in menu_collection.values():
                    if not isinstance(menu_record, dict):
                        continue
                    for field in ("slots", "spaced_slots"):
                        slot_map = menu_record.get(field, {})
                        if not isinstance(slot_map, dict):
                            continue
                        for slot_number, reference in list(slot_map.items()):
                            if (
                                isinstance(reference, str)
                                and reference in replacement_ids
                                and reference not in local_operators
                            ):
                                slot_map[slot_number] = replacement_ids[reference]

            rewrite_slots(config.get("Menus", {}))
            third_party = config.get("ThirdParty", {})
            if isinstance(third_party, dict):
                for addon in third_party.values():
                    if isinstance(addon, dict):
                        rewrite_slots(addon.get("Menus", {}), addon.get("Operators", {}))

            for duplicate_id in replacement_ids:
                operators.pop(duplicate_id, None)

    config["schema_version"] = 9
    return config


MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
    4: _migrate_v4_to_v5,
    5: _migrate_v5_to_v6,
    6: _migrate_v6_to_v7,
    7: _migrate_v7_to_v8,
    8: _migrate_v8_to_v9,
}


def migrate_config(config: Mapping[str, Any]) -> tuple[Dict[str, Any], bool]:
    migrated_config = deepcopy(dict(config))
    version = migrated_config.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ConfigLoadError("Configuration field 'schema_version' must be an integer")
    if version > SCHEMA_VERSION:
        raise ConfigLoadError(
            f"Configuration schema version {version} is newer than the supported version {SCHEMA_VERSION}; "
            "the file was not modified"
        )
    if version < 1:
        raise ConfigLoadError(f"Unsupported legacy schema version: {version}")

    changed = False
    while version < SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ConfigLoadError(
                f"No migration is registered from schema version {version} to {version + 1}"
            )
        migrated_config = migration(migrated_config)
        next_version = migrated_config.get("schema_version")
        if next_version != version + 1:
            raise ConfigLoadError(
                f"Migration from version {version} must return schema_version {version + 1}"
            )
        version = next_version
        changed = True
    return migrated_config, changed


def load_config_data(
    data: Any,
    *,
    path: Optional[Path] = None,
    valid_event_types: Optional[Iterable[str]] = None,
) -> ConfigLoadResult:
    """Migrate, validate and normalize an already decoded configuration."""
    if not isinstance(data, dict):
        raise ConfigLoadError("Configuration root must be a JSON object")

    try:
        migrated_data, migrated = migrate_config(data)
    except ConfigLoadError:
        raise
    except Exception as error:  # Defensive boundary around user-provided files.
        raise ConfigLoadError(f"Configuration migration failed: {error}") from error

    report = validate_config(migrated_data, valid_event_types=valid_event_types)
    if not report.valid or report.config is None:
        details = "\n".join(str(issue) for issue in report.errors)
        raise ConfigLoadError(f"Configuration validation failed:\n{details}")

    return ConfigLoadResult(
        config=report.config,
        path=Path(path) if path is not None else None,
        warnings=tuple(report.warnings),
        migrated=migrated,
    )


def load_config(
    path: Any,
    *,
    valid_event_types: Optional[Iterable[str]] = None,
) -> ConfigLoadResult:
    """Read a UTF-8 JSON file once, then migrate and validate it."""
    config_path = Path(path).expanduser()
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            raw_data = json.load(
                config_file,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonstandard_constant,
            )
    except ConfigLoadError:
        raise
    except json.JSONDecodeError as error:
        raise ConfigLoadError(
            f"Invalid JSON in '{config_path}' at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except (OSError, UnicodeError) as error:
        raise ConfigLoadError(f"Could not read configuration '{config_path}': {error}") from error

    return load_config_data(
        raw_data,
        path=config_path,
        valid_event_types=valid_event_types,
    )


def load_default_config(
    *,
    valid_event_types: Optional[Iterable[str]] = None,
) -> ConfigLoadResult:
    """Return the built-in defaults without touching the filesystem."""
    return load_config_data(
        make_default_config(),
        valid_event_types=valid_event_types,
    )
