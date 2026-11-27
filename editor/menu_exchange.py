"""Small JSON import/export helpers for portable AllPie menus.

A menu package contains existing AllPie menu/operator records, plus only the
operator presets referenced by the included menu slots. Third-party operator
references are flattened into the package's local Operators namespace so an
imported menu remains self-contained.
"""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..core.brush_assets import BRUSH_ASSET_OPERATOR_ID, operator_properties_match
from ..core.schema import make_default_config, SCHEMA_VERSION
from ..core.preset_identity import MAX_ENUM_VALUE, unique_enum_value
from ..core.validation import validate_config
from ..config.loader import migrate_config
from . import menu_data

MENU_PACKAGE_API_VERSION = 9
MENU_PACKAGE_FORMAT = "allpie_menus"
# Version 3 introduced permanent preset IDs; version 4 also stores stable
# numeric EnumProperty values so slot selections remain stable in Blender RNA.
MENU_PACKAGE_VERSION = 4
LEGACY_MENU_PACKAGE_VERSION = 1
PREVIOUS_MENU_PACKAGE_VERSION = 2
STABLE_ID_MENU_PACKAGE_VERSION = 3
SUPPORTED_MENU_PACKAGE_VERSIONS = frozenset({1, 2, 3, 4})


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str):
    raise ValueError(f"non-standard JSON constant: {value}")


def _validate_package_header(package: Mapping[str, Any]) -> int:
    """Validate the versioned package envelope shared by load and merge.

    Keep version-1 imports for packages made by 1.6.8 and earlier, version-2
    imports for releases that included per-slot labels, and version-3 imports
    with permanent preset IDs. Version 4 adds persistent numeric enum values.
    Legacy slot-label fields are discarded before current schema validation.
    New exports use version 4.
    """
    if package.get("format") != MENU_PACKAGE_FORMAT:
        raise ValueError("This is not an AllPie menu package")

    version = package.get("version")
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version not in SUPPORTED_MENU_PACKAGE_VERSIONS
    ):
        supported = ", ".join(str(item) for item in sorted(SUPPORTED_MENU_PACKAGE_VERSIONS))
        raise ValueError(
            f"Unsupported AllPie menu package version: {version!r} (supported: {supported})"
        )

    allowed_fields = {"format", "version", "Menus", "Operators"}
    unknown_fields = sorted(set(package) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"Unknown menu package field(s): {', '.join(unknown_fields)}")

    return version


def _safe_identifier(value: str) -> str:
    """Convert a third-party namespace and local ID to a legal action ID."""
    identifier = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).upper()
    identifier = re.sub(r"_+", "_", identifier).strip("_")
    if not identifier or not identifier[0].isalpha():
        identifier = f"IMPORTED_{identifier}"
    return identifier


def _unique_id(container: Mapping[str, Any], base_id: str, suffix: str) -> str:
    candidate = base_id
    if candidate not in container:
        return candidate
    candidate = f"{base_id}_{suffix}"
    index = 1
    while candidate in container:
        candidate = f"{base_id}_{suffix}_{index}"
        index += 1
    return candidate


def _resolve_action(
    config: Mapping[str, Any],
    reference: str,
    owner_addon: Optional[str],
) -> Tuple[str, Mapping[str, Any], Optional[str], str]:
    """Resolve a stable slot UUID to (UUID, action, owner addon, legacy key)."""
    reference = str(reference or "")
    for legacy_id, action in config.get("Operators", {}).items():
        if isinstance(action, Mapping) and str(action.get("preset_id", "")) == reference:
            return reference, action, None, str(legacy_id)

    third_party = config.get("ThirdParty", {})
    for addon_id, addon in third_party.items():
        if not isinstance(addon, Mapping):
            continue
        for legacy_id, action in addon.get("Operators", {}).items():
            if isinstance(action, Mapping) and str(action.get("preset_id", "")) == reference:
                return reference, action, str(addon_id), str(legacy_id)

    # Accept legacy references as a defensive compatibility path for configs
    # that have not yet passed through schema migration.
    if ":" in reference:
        addon_id, local_id = reference.split(":", 1)
        addon = third_party.get(addon_id, {})
        action = addon.get("Operators", {}).get(local_id) if isinstance(addon, Mapping) else None
        if isinstance(action, Mapping):
            return str(action.get("preset_id", reference)), action, addon_id, local_id
    if owner_addon:
        own_addon = third_party.get(owner_addon, {})
        action = own_addon.get("Operators", {}).get(reference) if isinstance(own_addon, Mapping) else None
        if isinstance(action, Mapping):
            return str(action.get("preset_id", reference)), action, owner_addon, reference
    action = config.get("Operators", {}).get(reference)
    if isinstance(action, Mapping):
        return str(action.get("preset_id", reference)), action, None, reference
    raise ValueError(f"Menu references missing operator preset '{reference}'")


def build_menu_package(
    config: Mapping[str, Any],
    menu_ids: Iterable[str],
) -> Dict[str, Any]:
    """Build a portable package from one or more menu IDs and their presets."""
    selected_ids = list(dict.fromkeys(str(menu_id) for menu_id in menu_ids if str(menu_id)))
    if not selected_ids:
        raise ValueError("Select at least one menu to export")

    package_menus: Dict[str, Any] = {}
    package_operators: Dict[str, Any] = {}
    portable_action_ids: Dict[str, str] = {}
    for menu_id in selected_ids:
        menu = deepcopy(menu_data.get_menu(dict(config), menu_id))
        # Never export deprecated slot-local labels, even when this helper is
        # called with an older in-memory configuration.
        menu.pop("slot_labels", None)
        menu.pop("spaced_slot_labels", None)

        owner_addon, local_menu_id = menu_data.split_menu_id(menu_id)
        if local_menu_id in package_menus:
            local_menu_id = _unique_id(package_menus, local_menu_id, "MENU")

        for slot_field in ("slots", "spaced_slots"):
            slot_map = menu.get(slot_field, {})
            if not isinstance(slot_map, dict):
                raise ValueError(f"Menu '{menu_id}' has an invalid {slot_field} mapping")

            rewritten_slots = {}
            for slot_number, reference in slot_map.items():
                if reference in (None, ""):
                    rewritten_slots[slot_number] = reference
                    continue
                if not isinstance(reference, str):
                    raise ValueError(f"Menu '{menu_id}' has an invalid action reference in {slot_field}")

                resolved_id, action, action_owner, legacy_id = _resolve_action(config, reference, owner_addon)
                portable_id = portable_action_ids.get(resolved_id)
                if portable_id is None:
                    if action_owner is None:
                        base_id = legacy_id
                    else:
                        base_id = _safe_identifier(f"{action_owner}_{legacy_id}")
                    portable_id = _unique_id(package_operators, base_id, "ACTION")
                    portable_action_ids[resolved_id] = portable_id
                    package_operators[portable_id] = deepcopy(dict(action))
                # Slot references always remain the stable UUID; the package's
                # dictionary key is only a local compatibility/storage alias.
                rewritten_slots[slot_number] = resolved_id
            menu[slot_field] = rewritten_slots

        package_menus[local_menu_id] = menu

    return {
        "format": MENU_PACKAGE_FORMAT,
        "version": MENU_PACKAGE_VERSION,
        "Menus": package_menus,
        "Operators": package_operators,
    }


def write_menu_package(path: Any, package: Mapping[str, Any]) -> Path:
    """Write a menu package as readable UTF-8 JSON."""
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(package, file, ensure_ascii=False, indent=4)
        file.write("\n")
    return destination


def load_menu_package(path: Any) -> Dict[str, Any]:
    """Read a mini JSON package and reject duplicate keys/non-standard values."""
    source = Path(path).expanduser()
    try:
        with source.open("r", encoding="utf-8") as file:
            package = json.load(
                file,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonstandard_constant,
            )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"Could not read menu JSON '{source.name}': {error}") from error

    if not isinstance(package, dict):
        raise ValueError("Menu JSON root must be an object")
    _validate_package_header(package)
    if not isinstance(package.get("Menus"), dict) or not package["Menus"]:
        raise ValueError("Menu JSON must contain at least one menu in 'Menus'")
    if not isinstance(package.get("Operators", {}), dict):
        raise ValueError("Menu JSON field 'Operators' must be an object")

    return package


def _actions_are_equivalent(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> bool:
    """Compare the executable identity of two operator presets.

    Preset IDs, labels, descriptions and context tags are metadata. The
    operator, invocation mode and properties determine what the action does.
    Brush assets use AllPie's library-aware semantic path comparison.
    """
    if not isinstance(existing, Mapping) or not isinstance(incoming, Mapping):
        return False
    operator_id = str(incoming.get("operator_id", ""))
    if operator_id != str(existing.get("operator_id", "")):
        return False
    if bool(existing.get("invoke", False)) != bool(incoming.get("invoke", False)):
        return False

    existing_properties = existing.get("properties", {})
    incoming_properties = incoming.get("properties", {})
    if operator_id == BRUSH_ASSET_OPERATOR_ID:
        return operator_properties_match(
            operator_id, existing_properties, incoming_properties
        )
    return existing_properties == incoming_properties


def _merge_action_contexts(existing: Any, incoming: Mapping[str, Any]) -> None:
    """Preserve discoverability when an imported action reuses a preset."""
    if not isinstance(existing, dict):
        return
    existing_contexts = existing.setdefault("contexts", [])
    if not isinstance(existing_contexts, list):
        return
    known_contexts = {
        value.casefold()
        for value in existing_contexts
        if isinstance(value, str)
    }
    for context_name in incoming.get("contexts", ()):
        if not isinstance(context_name, str):
            continue
        folded = context_name.casefold()
        if folded not in known_contexts:
            existing_contexts.append(context_name)
            known_contexts.add(folded)


def merge_menu_package(
    config: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    valid_event_types: Optional[Iterable[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Validate and add package menus/presets without replacing user records.

    Existing semantically equivalent operator presets are reused even when
    their IDs or descriptive metadata differ. Conflicting operator and menu IDs
    receive deterministic ``_IMPORTED`` suffixes. Slot references are rewritten
    to the resulting canonical operator IDs.
    """
    if not isinstance(package, Mapping):
        raise ValueError("Menu package must be an object")
    _validate_package_header(package)

    raw_menus = package.get("Menus")
    raw_operators = package.get("Operators", {})
    if not isinstance(raw_menus, Mapping) or not raw_menus:
        raise ValueError("Menu package does not contain any menus")
    if not isinstance(raw_operators, Mapping):
        raise ValueError("Menu package 'Operators' must be an object")

    # Validate the portable records independently before merging them into the
    # user's data. This catches malformed IDs, fields, slots and references.
    package_config = make_default_config()
    package_menus = deepcopy(dict(raw_menus))
    for menu in package_menus.values():
        if isinstance(menu, dict):
            menu.pop("slot_labels", None)
            menu.pop("spaced_slot_labels", None)
    package_config["Menus"] = package_menus
    package_config["Operators"] = deepcopy(dict(raw_operators))
    package_version = int(package.get("version", 1))
    if package_version in {1, 2}:
        # Legacy packages store local action keys in slots and contain no
        # permanent preset IDs. Convert them through both identity migrations.
        package_config["schema_version"] = 12
        package_config, _migrated = migrate_config(package_config)
    elif package_version == 3:
        # Version 3 has stable UUID references but predates persistent enum
        # numbers. Migrate it without changing its menu/operator identities.
        package_config["schema_version"] = 13
        package_config, _migrated = migrate_config(package_config)
    else:
        package_config["schema_version"] = SCHEMA_VERSION
    package_report = validate_config(
        package_config,
        valid_event_types=valid_event_types,
    )
    if not package_report.valid or package_report.config is None:
        details = "\n".join(str(issue) for issue in package_report.errors)
        raise ValueError(f"Menu package validation failed:\n{details}")
    normalized_package = package_report.config

    merged = deepcopy(dict(config))
    merged.setdefault("Menus", {})
    merged.setdefault("Operators", {})
    merged.setdefault("ThirdParty", {})
    operators = merged["Operators"]

    action_id_map: Dict[str, str] = {}
    added_actions = 0
    reused_actions = 0
    existing_by_preset_id = {
        str(action.get("preset_id")): action
        for action in operators.values()
        if isinstance(action, Mapping) and action.get("preset_id")
    }
    # A preset UUID is global across AllPie and third-party namespaces. Only
    # AllPie-owned presets are eligible for equivalence reuse here, but every
    # existing UUID must be reserved to prevent collisions on import.
    used_preset_ids = set(existing_by_preset_id)
    used_enum_values = {
        action.get("enum_value")
        for action in operators.values()
        if isinstance(action, Mapping)
        and isinstance(action.get("enum_value"), int)
        and not isinstance(action.get("enum_value"), bool)
        and 1 <= action.get("enum_value") <= MAX_ENUM_VALUE
    }
    for addon in merged.get("ThirdParty", {}).values():
        for action in addon.get("Operators", {}).values():
            if isinstance(action, Mapping):
                if action.get("preset_id"):
                    used_preset_ids.add(str(action["preset_id"]))
                enum_value = action.get("enum_value")
                if isinstance(enum_value, int) and not isinstance(enum_value, bool) and 1 <= enum_value <= MAX_ENUM_VALUE:
                    used_enum_values.add(enum_value)
    for package_action_key, action in normalized_package["Operators"].items():
        package_preset_id = str(action.get("preset_id", ""))
        existing_action = existing_by_preset_id.get(package_preset_id)
        equivalent_action = None

        if isinstance(existing_action, Mapping) and _actions_are_equivalent(existing_action, action):
            equivalent_action = existing_action
        else:
            for candidate_action in operators.values():
                if _actions_are_equivalent(candidate_action, action):
                    equivalent_action = candidate_action
                    break

        if equivalent_action is not None:
            target_preset_id = str(equivalent_action.get("preset_id", ""))
            _merge_action_contexts(equivalent_action, action)
            reused_actions += 1
        else:
            target_legacy_key = _unique_id(operators, package_action_key, "IMPORTED")
            target_preset_id = package_preset_id
            if not target_preset_id or target_preset_id in used_preset_ids:
                target_preset_id = "op_" + uuid.uuid4().hex
                while target_preset_id in used_preset_ids:
                    target_preset_id = "op_" + uuid.uuid4().hex
            imported_action = deepcopy(dict(action))
            imported_action["preset_id"] = target_preset_id
            enum_value = imported_action.get("enum_value")
            if (
                isinstance(enum_value, bool)
                or not isinstance(enum_value, int)
                or not 1 <= enum_value <= MAX_ENUM_VALUE
                or enum_value in used_enum_values
            ):
                enum_value = unique_enum_value(target_preset_id, used_enum_values)
            imported_action["enum_value"] = enum_value
            operators[target_legacy_key] = imported_action
            existing_by_preset_id[target_preset_id] = imported_action
            used_preset_ids.add(target_preset_id)
            used_enum_values.add(enum_value)
            added_actions += 1
        action_id_map[package_preset_id] = target_preset_id

    imported_menu_ids = []
    remapped_menu_ids = {}
    for package_menu_id, raw_menu in normalized_package["Menus"].items():
        menu = deepcopy(raw_menu)
        if package_menu_id in merged["Menus"]:
            target_menu_id = _unique_id(
                merged["Menus"], package_menu_id, "IMPORTED"
            )
            menu_name = str(menu.get("name", package_menu_id)).strip()
            if not menu_name.casefold().endswith("(imported)"):
                menu["name"] = f"{menu_name} (Imported)"
        else:
            target_menu_id = package_menu_id

        for slot_field in ("slots", "spaced_slots"):
            rewritten_slots = {}
            for slot_number, reference in menu.get(slot_field, {}).items():
                if reference is None:
                    rewritten_slots[slot_number] = None
                    continue
                target_action_id = action_id_map.get(reference)
                if target_action_id is None:
                    raise ValueError(
                        f"Menu '{package_menu_id}' references missing package preset '{reference}'"
                    )
                rewritten_slots[slot_number] = target_action_id
            menu[slot_field] = rewritten_slots

        merged["Menus"][target_menu_id] = menu
        imported_menu_ids.append(target_menu_id)
        remapped_menu_ids[package_menu_id] = target_menu_id

    base_report = validate_config(
        config,
        valid_event_types=valid_event_types,
    )
    existing_warnings = (
        {str(issue) for issue in base_report.warnings}
        if base_report.valid else set()
    )
    final_report = validate_config(
        merged,
        valid_event_types=valid_event_types,
    )
    if not final_report.valid or final_report.config is None:
        details = "\n".join(str(issue) for issue in final_report.errors)
        raise ValueError(f"Imported menus would make the configuration invalid:\n{details}")

    result = {
        "menu_ids": imported_menu_ids,
        "menu_id_map": remapped_menu_ids,
        "actions_added": added_actions,
        "actions_reused": reused_actions,
        "warnings": [
            str(issue) for issue in final_report.warnings
            if str(issue) not in existing_warnings
        ],
    }
    return final_report.config, result
