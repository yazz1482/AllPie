"""Read and migrate AllPie JSON configuration files.

Loading is an explicit startup/import operation. The radial menu runtime must
never call these functions while opening or executing a pie menu.
"""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from ..core.brush_assets import BRUSH_ASSET_OPERATOR_ID, normalize_operator_properties, operator_properties_identity
from ..core.schema import COMMON_KEYMAP, SCHEMA_VERSION, make_default_config
from ..core.preset_identity import MAX_ENUM_VALUE, unique_enum_value
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
    """Advance the legacy configuration after brush assignments were consolidated.

    The old per-menu Brush Menu flag is no longer used. Brush actions are
    ordinary reusable operator presets and can be assigned to any menu.
    """
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
    """Consolidate duplicate Asset Shelf popup presets.

    Brush activation and Asset Shelf popover actions are ordinary operator
    presets; they are no longer restricted to menus carrying a special tag.
    """
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


def _migrate_v9_to_v10(config: Dict[str, Any]) -> Dict[str, Any]:
    """Add a dedicated Image Editor Mode menu without changing Common menus.

    The Image Paint keymap is also active in the Image Editor's Paint mode.
    The Image Editor therefore needs its own mode-switching menu (View, Paint,
    Mask) rather than inheriting the 3D View Common Mode menu. Existing user
    menus and shortcuts are preserved; the new menu inherits the current Mode
    shortcut when available.
    """
    menus = config.get("Menus")
    operators = config.get("Operators")
    if not isinstance(menus, dict) or not isinstance(operators, dict):
        config["schema_version"] = 10
        return config

    if "IMAGE.MODE" not in menus:
        operator_specs = (
            ("IMAGE_EDITOR_MODE_VIEW", "View Mode", "VIEW"),
            ("IMAGE_EDITOR_MODE_PAINT", "Paint Mode", "PAINT"),
            ("IMAGE_EDITOR_MODE_MASK", "Mask Mode", "MASK"),
        )
        action_ids: Dict[str, str] = {}
        for action_id, label, mode in operator_specs:
            action = {
                "name": label,
                "operator_id": "allpie.image_editor_set_mode",
                "invoke": False,
                "properties": {"mode": mode},
                "search_name": f"Image Editor {label}",
                "description": f"Switch the Image Editor to {label.replace(' Mode', '')} mode.",
                "contexts": ["Image"],
            }

            # Reuse an equivalent existing action if the user already created one.
            existing_id = next((
                candidate_id
                for candidate_id, candidate in operators.items()
                if isinstance(candidate, dict)
                and candidate.get("operator_id") == action["operator_id"]
                and bool(candidate.get("invoke", False)) == action["invoke"]
                and candidate.get("properties", {}) == action["properties"]
            ), None)
            if existing_id is not None:
                action_ids[mode] = existing_id
                continue

            unique_id = action_id
            suffix = 2
            while unique_id in operators:
                unique_id = f"{action_id}_{suffix}"
                suffix += 1
            operators[unique_id] = action
            action_ids[mode] = unique_id

        source_mode = menus.get("OBJECT.MODE", {})
        source_mode = source_mode if isinstance(source_mode, dict) else {}
        key = str(source_mode.get("key") or "TAB")
        modifiers = deepcopy(source_mode.get("keymodifiers", ["CTRL"]))
        if not isinstance(modifiers, list):
            modifiers = ["CTRL"]

        # Avoid introducing a shortcut collision with an enabled Image Editor
        # menu that the user had already configured before this built-in was added.
        image_menus = [menus]
        third_party = config.get("ThirdParty", {})
        if isinstance(third_party, dict):
            image_menus.extend(
                addon.get("Menus", {})
                for addon in third_party.values()
                if isinstance(addon, dict) and isinstance(addon.get("Menus", {}), dict)
            )

        for menu_group in image_menus:
            for existing in menu_group.values():
                if not isinstance(existing, dict) or not existing.get("enabled", True):
                    continue
                if str(existing.get("keymap", "")).strip().casefold() != "image":
                    continue
                existing_modifiers = existing.get("keymodifiers", [])
                if not isinstance(existing_modifiers, list):
                    existing_modifiers = []
                if (
                    str(existing.get("key", "")).upper() == key.upper()
                    and {str(value).upper() for value in existing_modifiers}
                    == {str(value).upper() for value in modifiers}
                ):
                    key = "NONE"
                    break
            if key == "NONE":
                break

        menus["IMAGE.MODE"] = {
            "name": "Mode",
            "key": key,
            "keymodifiers": modifiers,
            "keymap": "Image",
            # The Image Editor mode menu is independent of whether the user
            # enabled or disabled the 3D View's Common Mode menu.
            "enabled": True,
            "slots": {
                "1": action_ids["VIEW"],
                "3": action_ids["PAINT"],
                "5": action_ids["MASK"],
            },
            "spaced_slots": {},
        }

    config["schema_version"] = 10
    return config


def _migrate_v10_to_v11(config: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy migration retained for configurations created by 1.6.9."""
    config["schema_version"] = 11
    return config


def _migrate_v11_to_v12(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove deprecated per-slot display names.

    Slot labels are now derived exclusively from the referenced shared
    operator preset. Drop the old menu-local overrides from both global and
    third-party menus so every use of a preset always displays its one name.
    """
    menus = config.get("Menus", {})
    if isinstance(menus, dict):
        for menu in menus.values():
            if isinstance(menu, dict):
                menu.pop("slot_labels", None)
                menu.pop("spaced_slot_labels", None)

    third_party = config.get("ThirdParty", {})
    if isinstance(third_party, dict):
        for addon in third_party.values():
            if not isinstance(addon, dict):
                continue
            menus = addon.get("Menus", {})
            if isinstance(menus, dict):
                for menu in menus.values():
                    if isinstance(menu, dict):
                        menu.pop("slot_labels", None)
                        menu.pop("spaced_slot_labels", None)

    config["schema_version"] = 12
    return config


def _migrate_v12_to_v13(config: Dict[str, Any]) -> Dict[str, Any]:
    """Assign permanent preset UUIDs and rewrite every menu slot to use them.

    Operator dictionary keys are retained as legacy/local lookup keys for
    compatibility with bundled data and third-party contributors. ``preset_id``
    is the permanent identity, and all menu slot references are canonicalized
    to that identity. It never depends on a preset's name or sort position.
    """
    used_ids = set()
    global_aliases: Dict[str, str] = {}
    addon_aliases: Dict[str, Dict[str, str]] = {}
    preset_ids: Dict[str, str] = {}

    def deterministic_id(owner: str, legacy_id: str, salt: int = 0) -> str:
        """Return a reproducible UUID for a preset that predates stable IDs.

        Using the storage key and owner namespace keeps migration repeatable
        across the bundled defaults and a user's copy of those defaults. It
        also lets the operator manager continue distinguishing bundled presets
        from user-created presets after upgrading an older configuration.
        Newly-created presets still use random UUIDs in operator_data.
        """
        identity = f"AllPie:operator-preset:{owner}:{legacy_id}"
        if salt:
            identity = f"{identity}:{salt}"
        return "op_" + uuid.uuid5(uuid.NAMESPACE_URL, identity).hex

    def assign_collection(actions: Any, namespace: str = "global") -> None:
        if not isinstance(actions, dict):
            return
        for legacy_id, action in actions.items():
            if not isinstance(action, dict):
                continue
            candidate = str(action.get("preset_id", "") or "").strip()
            if not re.fullmatch(r"op_[0-9a-f]{32}", candidate) or candidate in used_ids:
                salt = 0
                candidate = deterministic_id(namespace, str(legacy_id), salt)
                while candidate in used_ids:
                    salt += 1
                    candidate = deterministic_id(namespace, str(legacy_id), salt)
            used_ids.add(candidate)
            action["preset_id"] = candidate
            preset_ids[candidate] = candidate
            if namespace != "global":
                addon_aliases.setdefault(namespace, {})[str(legacy_id)] = candidate
            else:
                global_aliases[str(legacy_id)] = candidate

    assign_collection(config.get("Operators", {}), "global")
    third_party = config.get("ThirdParty", {})
    if isinstance(third_party, dict):
        for addon_id, addon in third_party.items():
            if isinstance(addon, dict):
                assign_collection(addon.get("Operators", {}), str(addon_id))

    def canonicalize_slot_map(slot_map: Any, owner_addon: str = "") -> None:
        if not isinstance(slot_map, dict):
            return
        for slot_number, reference in list(slot_map.items()):
            if not isinstance(reference, str) or not reference:
                continue
            if reference in preset_ids:
                continue
            resolved = None
            if ":" in reference:
                addon_id, local_id = reference.split(":", 1)
                resolved = addon_aliases.get(addon_id, {}).get(local_id)
            elif owner_addon:
                resolved = addon_aliases.get(owner_addon, {}).get(reference)
                if resolved is None:
                    resolved = global_aliases.get(reference)
            else:
                resolved = global_aliases.get(reference)
            if resolved is not None:
                slot_map[slot_number] = resolved

    def canonicalize_menus(menus: Any, owner_addon: str = "") -> None:
        if not isinstance(menus, dict):
            return
        for menu in menus.values():
            if not isinstance(menu, dict):
                continue
            canonicalize_slot_map(menu.get("slots", {}), owner_addon)
            canonicalize_slot_map(menu.get("spaced_slots", {}), owner_addon)

    canonicalize_menus(config.get("Menus", {}))
    if isinstance(third_party, dict):
        for addon_id, addon in third_party.items():
            if isinstance(addon, dict):
                canonicalize_menus(addon.get("Menus", {}), str(addon_id))

    config["schema_version"] = 13
    return config


def _migrate_v13_to_v14(config: Dict[str, Any]) -> Dict[str, Any]:
    """Persist stable Blender EnumProperty numbers for every operator preset.

    Blender stores an EnumProperty's numeric item value, not just its string
    identifier. Supplying an explicit, persistent number prevents item sorting
    or insertion from changing the action referenced by an existing slot.
    """
    entries = []
    global_actions = config.get("Operators", {})
    if isinstance(global_actions, dict):
        for legacy_id, action in global_actions.items():
            if isinstance(action, dict):
                entries.append((str(action.get("preset_id", "")), "global", str(legacy_id), action))

    third_party = config.get("ThirdParty", {})
    if isinstance(third_party, dict):
        for addon_id, addon in third_party.items():
            if not isinstance(addon, dict):
                continue
            actions = addon.get("Operators", {})
            if not isinstance(actions, dict):
                continue
            for legacy_id, action in actions.items():
                if isinstance(action, dict):
                    entries.append((str(action.get("preset_id", "")), str(addon_id), str(legacy_id), action))

    # A deterministic order makes legacy migration reproducible. Existing
    # valid unique enum numbers are preserved; missing or colliding numbers
    # are derived from the already-permanent preset ID.
    entries.sort(key=lambda item: (item[0], item[1], item[2]))
    used_values = set()
    for preset_id, _owner, legacy_id, action in entries:
        value = action.get("enum_value")
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 1 <= value <= MAX_ENUM_VALUE
            and value not in used_values
        ):
            enum_value = value
        else:
            enum_value = unique_enum_value(preset_id or legacy_id, used_values)
        action["enum_value"] = enum_value
        used_values.add(enum_value)

    config["schema_version"] = 14
    return config


def _migrate_v14_to_v15(config: Dict[str, Any]) -> Dict[str, Any]:
    """Persist whether each menu's Spaced Slots feature is enabled.

    Schema v14 validation always materialized an empty ``spaced_slots`` map,
    even when the feature had been disabled. That erased the previous enabled
    state for empty grids. Recover the only reliable signal: menus with at
    least one assigned spaced action were operationally enabled; empty grids
    become disabled. Existing assignments and preset identities are untouched.
    """
    def migrate_menus(menus: Any) -> None:
        if not isinstance(menus, dict):
            return
        for menu in menus.values():
            if not isinstance(menu, dict):
                continue
            existing = menu.get("spaced_slots_enabled")
            if isinstance(existing, bool):
                enabled = existing
            else:
                spaced_slots = menu.get("spaced_slots", {})
                enabled = (
                    isinstance(spaced_slots, dict)
                    and any(reference is not None for reference in spaced_slots.values())
                )
            menu["spaced_slots_enabled"] = enabled

    migrate_menus(config.get("Menus", {}))
    third_party = config.get("ThirdParty", {})
    if isinstance(third_party, dict):
        for addon in third_party.values():
            if isinstance(addon, dict):
                migrate_menus(addon.get("Menus", {}))

    config["schema_version"] = 15
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
    9: _migrate_v9_to_v10,
    10: _migrate_v10_to_v11,
    11: _migrate_v11_to_v12,
    12: _migrate_v12_to_v13,
    13: _migrate_v13_to_v14,
    14: _migrate_v14_to_v15,
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
