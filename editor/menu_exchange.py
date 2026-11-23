"""Small JSON import/export helpers for portable AllPie menus.

A menu package contains existing AllPie menu/operator records, plus only the
operator presets referenced by the included menu slots. Third-party operator
references are flattened into the package's local Operators namespace so an
imported menu remains self-contained.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..core.brush_assets import BRUSH_ASSET_OPERATOR_ID, operator_properties_match
from ..core.schema import make_default_config
from ..core.validation import validate_config
from . import menu_data

MENU_PACKAGE_API_VERSION = 3
MENU_PACKAGE_FORMAT = "allpie_menus"
MENU_PACKAGE_VERSION = 1


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str):
    raise ValueError(f"non-standard JSON constant: {value}")


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
) -> Tuple[str, Mapping[str, Any], Optional[str]]:
    """Resolve a slot reference using the same precedence as AllPie's registry."""
    third_party = config.get("ThirdParty", {})

    if ":" in reference:
        addon_id, local_id = reference.split(":", 1)
        addon = third_party.get(addon_id, {})
        action = addon.get("Operators", {}).get(local_id)
        if isinstance(action, Mapping):
            return f"{addon_id}:{local_id}", action, addon_id
        raise ValueError(f"Menu references missing third-party operator preset '{reference}'")

    if owner_addon:
        own_addon = third_party.get(owner_addon, {})
        action = own_addon.get("Operators", {}).get(reference)
        if isinstance(action, Mapping):
            return f"{owner_addon}:{reference}", action, owner_addon

    action = config.get("Operators", {}).get(reference)
    if isinstance(action, Mapping):
        return reference, action, None

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

                resolved_id, action, action_owner = _resolve_action(config, reference, owner_addon)
                portable_id = portable_action_ids.get(resolved_id)
                if portable_id is None:
                    if action_owner is None:
                        base_id = resolved_id
                    else:
                        base_id = _safe_identifier(f"{action_owner}_{resolved_id.split(':', 1)[1]}")
                    portable_id = _unique_id(package_operators, base_id, "ACTION")
                    portable_action_ids[resolved_id] = portable_id
                    package_operators[portable_id] = deepcopy(dict(action))
                rewritten_slots[slot_number] = portable_id
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
    if package.get("format") != MENU_PACKAGE_FORMAT:
        raise ValueError("This JSON file is not an AllPie menu export")
    version = package.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != MENU_PACKAGE_VERSION:
        raise ValueError(f"Unsupported AllPie menu package version: {version!r}")
    if not isinstance(package.get("Menus"), dict) or not package["Menus"]:
        raise ValueError("Menu JSON must contain at least one menu in 'Menus'")
    if not isinstance(package.get("Operators", {}), dict):
        raise ValueError("Menu JSON field 'Operators' must be an object")

    allowed_fields = {"format", "version", "Menus", "Operators"}
    unknown_fields = sorted(set(package) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"Unknown menu JSON field(s): {', '.join(unknown_fields)}")

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
    if package.get("format") != MENU_PACKAGE_FORMAT:
        raise ValueError("This file is not an AllPie menu package")
    package_version = package.get("version")
    if isinstance(package_version, bool) or not isinstance(package_version, int) or package_version != MENU_PACKAGE_VERSION:
        raise ValueError(f"Unsupported AllPie menu package version: {package_version!r}")
    unknown_fields = sorted(set(package) - {"format", "version", "Menus", "Operators"})
    if unknown_fields:
        raise ValueError(f"Unknown menu package field(s): {', '.join(unknown_fields)}")

    raw_menus = package.get("Menus")
    raw_operators = package.get("Operators", {})
    if not isinstance(raw_menus, Mapping) or not raw_menus:
        raise ValueError("Menu package does not contain any menus")
    if not isinstance(raw_operators, Mapping):
        raise ValueError("Menu package 'Operators' must be an object")

    # Validate the portable records independently before merging them into the
    # user's data. This catches malformed IDs, fields, slots and references.
    package_config = make_default_config()
    package_config["Menus"] = deepcopy(dict(raw_menus))
    package_config["Operators"] = deepcopy(dict(raw_operators))
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

    action_id_map: Dict[str, str] = {}
    added_actions = 0
    reused_actions = 0
    for package_action_id, action in normalized_package["Operators"].items():
        operators = merged["Operators"]
        existing_action = operators.get(package_action_id)
        equivalent_id = None

        # Prefer the exact preset ID when it already represents the same
        # executable action, then search other presets for a semantic match.
        if (
            isinstance(existing_action, Mapping)
            and _actions_are_equivalent(existing_action, action)
        ):
            equivalent_id = package_action_id
        else:
            for candidate_id, candidate_action in operators.items():
                if _actions_are_equivalent(candidate_action, action):
                    equivalent_id = candidate_id
                    break

        if equivalent_id is not None:
            target_action_id = equivalent_id
            _merge_action_contexts(operators[target_action_id], action)
            reused_actions += 1
        else:
            target_action_id = _unique_id(
                operators, package_action_id, "IMPORTED"
            )
            operators[target_action_id] = deepcopy(action)
            added_actions += 1
        action_id_map[package_action_id] = target_action_id

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
