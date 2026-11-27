"""Structural and reference validation for AllPie JSON configurations."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .brush_assets import operator_properties_match
from .preset_identity import MAX_ENUM_VALUE
from .schema import (
    DEFAULT_PREFERENCES,
    SCHEMA_VERSION,
    SLOT_IDS,
    SUPPORTED_MODIFIERS,
    keymap_contexts,
)

_MENU_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*)*$")
_OPERATOR_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*)*$")
_ADDON_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]*$")
_BLENDER_OPERATOR_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_PRESET_ID_RE = re.compile(r"^op_[0-9a-f]{32}$")

_TOP_LEVEL_KEYS = {"schema_version", "Menus", "Operators", "ThirdParty", "Preferences"}
_MENU_KEYS = {
    # is_brush_menu remains accepted as a legacy key and is dropped during
    # normalization so older user configurations continue to load cleanly.
    "name", "key", "keymodifiers", "keymap", "enabled", "is_brush_menu",
    "slots", "spaced_slots", "spaced_slots_enabled",
}
_OPERATOR_KEYS = {"preset_id", "enum_value", "name", "operator_id", "invoke", "properties", "search_name", "description", "contexts", "user_defined"}
_THIRD_PARTY_KEYS = {"name", "enabled", "Operators", "Menus"}
_PREFERENCE_KEYS = {"radial", "colors"}
_RADIAL_PREFERENCE_KEYS = {"hold_time", "deadzone"}
_COLOR_PREFERENCE_KEYS = set(DEFAULT_PREFERENCES["colors"])

RADIAL_RESERVED_MENU_SHORTCUTS = frozenset({"SPACE", "ESC"})
_RADIAL_RESERVED_SHORTCUT_MESSAGES = {
    "SPACE": "Space is reserved for switching to the Spaced Menu",
    "ESC": "Esc is reserved for cancelling the radial menu",
}


def reserved_menu_shortcut_message(key: Any) -> Optional[str]:
    """Return why a key cannot be used to open an AllPie radial menu."""
    if not isinstance(key, str):
        return None
    normalized = key.upper()
    if normalized not in RADIAL_RESERVED_MENU_SHORTCUTS:
        return None
    return _RADIAL_RESERVED_SHORTCUT_MESSAGES.get(normalized)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    path: str
    message: str

    def __str__(self) -> str:
        location = self.path or "$"
        return f"{self.severity.upper()}: {location}: {self.message}"


@dataclass
class ValidationReport:
    """Result of validating and normalizing one configuration."""

    config: Optional[Dict[str, Any]] = None
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            details = "\n".join(str(issue) for issue in self.errors)
            raise ValueError(f"AllPie configuration is invalid:\n{details}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _check_unknown_keys(
    value: Mapping[str, Any],
    allowed: Iterable[str],
    path: str,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
    *,
    strict: bool,
) -> None:
    allowed_set = set(allowed)
    for key in value:
        if key not in allowed_set:
            issue = ValidationIssue(
                "error" if strict else "warning",
                f"{path}.{key}" if path else key,
                "unknown field",
            )
            (errors if strict else warnings).append(issue)


def _merge_defaults(value: Any, defaults: Mapping[str, Any]) -> Dict[str, Any]:
    result = deepcopy(dict(value)) if isinstance(value, dict) else {}
    for key, default in defaults.items():
        if key not in result:
            result[key] = deepcopy(default)
        elif isinstance(default, dict):
            result[key] = _merge_defaults(result[key], default)
    return result


def _validate_preferences(
    raw: Any,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
    strict_unknown_fields: bool,
) -> Dict[str, Any]:
    path = "Preferences"
    if not isinstance(raw, dict):
        errors.append(ValidationIssue("error", path, "must be an object"))
        raw = {}

    # Schema-v1 files may still arrive through direct validation APIs. Their
    # duplicated brush settings are ignored safely; the actual brush mapping is
    # already represented by operator presets assigned in the Sculpt menu.
    raw = deepcopy(raw)
    if isinstance(raw, dict) and "brushes" in raw:
        raw.pop("brushes", None)
        warnings.append(ValidationIssue(
            "warning",
            f"{path}.brushes",
            "deprecated preference field ignored; edit Sculpt brush assignments in the Menus tab",
        ))

    _check_unknown_keys(raw, _PREFERENCE_KEYS, path, errors, warnings, strict=strict_unknown_fields)
    prefs = _merge_defaults(raw, DEFAULT_PREFERENCES)

    radial = prefs.get("radial")
    if not isinstance(radial, dict):
        errors.append(ValidationIssue("error", f"{path}.radial", "must be an object"))
        radial = {}
        prefs["radial"] = radial
    _check_unknown_keys(radial, _RADIAL_PREFERENCE_KEYS, f"{path}.radial", errors, warnings, strict=strict_unknown_fields)

    hold_time = radial.get("hold_time")
    if not _is_number(hold_time) or not 0.010 <= float(hold_time) <= 0.500:
        errors.append(ValidationIssue("error", f"{path}.radial.hold_time", "must be a finite number from 0.010 to 0.500"))
    else:
        radial["hold_time"] = float(hold_time)

    deadzone = radial.get("deadzone")
    if isinstance(deadzone, bool) or not isinstance(deadzone, int) or not 15 <= deadzone <= 50:
        errors.append(ValidationIssue("error", f"{path}.radial.deadzone", "must be an integer from 15 to 50"))

    colors = prefs.get("colors")
    if not isinstance(colors, dict):
        errors.append(ValidationIssue("error", f"{path}.colors", "must be an object"))
        colors = {}
        prefs["colors"] = colors
    _check_unknown_keys(colors, _COLOR_PREFERENCE_KEYS, f"{path}.colors", errors, warnings, strict=strict_unknown_fields)
    for color_name in _COLOR_PREFERENCE_KEYS:
        color = colors.get(color_name)
        color_path = f"{path}.colors.{color_name}"
        if not isinstance(color, list) or len(color) != 4:
            errors.append(ValidationIssue("error", color_path, "must be an RGBA array containing exactly four numbers"))
            continue
        if any(not _is_number(component) or not 0.0 <= float(component) <= 1.0 for component in color):
            errors.append(ValidationIssue("error", color_path, "each component must be a finite number from 0.0 to 1.0"))
        else:
            colors[color_name] = [float(component) for component in color]


    return prefs


def _validate_action(
    identifier: str,
    raw: Any,
    path: str,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
    strict_unknown_fields: bool,
) -> Optional[Dict[str, Any]]:
    if not isinstance(identifier, str) or not _OPERATOR_ID_RE.fullmatch(identifier):
        errors.append(ValidationIssue("error", path, "action ID must use uppercase letters, digits, underscores and optional dot-separated groups"))
    if not isinstance(raw, dict):
        errors.append(ValidationIssue("error", path, "must be an object"))
        return None

    _check_unknown_keys(raw, _OPERATOR_KEYS, path, errors, warnings, strict=strict_unknown_fields)
    normalized = deepcopy(raw)
    for required in ("preset_id", "enum_value", "name", "operator_id"):
        if required not in raw:
            errors.append(ValidationIssue("error", f"{path}.{required}", "is required"))

    preset_id = raw.get("preset_id")
    if not isinstance(preset_id, str) or not _PRESET_ID_RE.fullmatch(preset_id):
        errors.append(ValidationIssue("error", f"{path}.preset_id", "must be a permanent AllPie ID in the form op_ followed by 32 lowercase hexadecimal characters"))
    else:
        normalized["preset_id"] = preset_id

    enum_value = raw.get("enum_value")
    if (
        isinstance(enum_value, bool)
        or not isinstance(enum_value, int)
        or not 1 <= enum_value <= MAX_ENUM_VALUE
    ):
        errors.append(ValidationIssue("error", f"{path}.enum_value", f"must be a unique positive integer from 1 to {MAX_ENUM_VALUE}"))
    else:
        normalized["enum_value"] = enum_value

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(ValidationIssue("error", f"{path}.name", "must be a non-empty string"))

    operator_id = raw.get("operator_id")
    if not isinstance(operator_id, str) or not _BLENDER_OPERATOR_RE.fullmatch(operator_id):
        errors.append(ValidationIssue("error", f"{path}.operator_id", "must be a Blender operator identifier such as mesh.primitive_cube_add"))

    invoke = raw.get("invoke", False)
    if not isinstance(invoke, bool):
        errors.append(ValidationIssue("error", f"{path}.invoke", "must be a boolean"))
    normalized["invoke"] = invoke

    properties = raw.get("properties", {})
    if not isinstance(properties, dict):
        errors.append(ValidationIssue("error", f"{path}.properties", "must be an object"))
    elif not _is_json_value(properties):
        errors.append(ValidationIssue("error", f"{path}.properties", "contains a value that cannot be represented safely in JSON"))
    normalized["properties"] = deepcopy(properties)

    search_name = raw.get("search_name", name if isinstance(name, str) else identifier)
    if not isinstance(search_name, str) or not search_name.strip():
        errors.append(ValidationIssue("error", f"{path}.search_name", "must be a non-empty string when provided"))
        search_name = name if isinstance(name, str) and name.strip() else identifier
    normalized["search_name"] = search_name.strip()

    description = raw.get("description", "")
    if not isinstance(description, str):
        errors.append(ValidationIssue("error", f"{path}.description", "must be a string when provided"))
        description = ""
    normalized["description"] = description.strip()

    # Optional context tags make catalogue actions searchable in a context
    # even before they have been assigned to a menu slot. This is used for the
    # full Sculpt Essentials brush catalog; ordinary actions remain discoverable
    # through their menu assignments.
    contexts = raw.get("contexts", [])
    if not isinstance(contexts, list):
        errors.append(ValidationIssue("error", f"{path}.contexts", "must be an array of Blender keymap context names"))
        contexts = []
    else:
        normalized_contexts = []
        seen_contexts = set()
        for index, context_name in enumerate(contexts):
            context_path = f"{path}.contexts[{index}]"
            if not isinstance(context_name, str) or not context_name.strip():
                errors.append(ValidationIssue("error", context_path, "must be a non-empty keymap context name"))
                continue
            context_name = context_name.strip()
            folded = context_name.casefold()
            if folded in seen_contexts:
                errors.append(ValidationIssue("error", context_path, "context is duplicated"))
                continue
            seen_contexts.add(folded)
            normalized_contexts.append(context_name)
        contexts = normalized_contexts
    normalized["contexts"] = contexts

    # User-created presets are explicitly marked so the Operators preferences
    # can offer edit/delete controls without exposing bundled defaults. Older
    # user presets without this marker are detected against the bundled config.
    if "user_defined" in raw:
        user_defined = raw.get("user_defined")
        if not isinstance(user_defined, bool):
            errors.append(ValidationIssue("error", f"{path}.user_defined", "must be a boolean when provided"))
        else:
            normalized["user_defined"] = user_defined

    return normalized


def _validate_slots(raw: Any, path: str, errors: List[ValidationIssue]) -> Dict[str, Optional[str]]:
    if not isinstance(raw, dict):
        errors.append(ValidationIssue("error", path, "must be an object mapping slot numbers 1–8 to action IDs"))
        return {}

    slots: Dict[str, Optional[str]] = {}
    for slot, action_ref in raw.items():
        slot_path = f"{path}.{slot}"
        if slot not in SLOT_IDS:
            errors.append(ValidationIssue("error", slot_path, "slot must be a string from '1' through '8'"))
            continue
        if action_ref is None:
            slots[slot] = None
        elif isinstance(action_ref, str) and action_ref.strip():
            slots[slot] = action_ref.strip()
        else:
            errors.append(ValidationIssue("error", slot_path, "must be null or a non-empty action ID"))
    return slots


def _validate_menu(
    identifier: str,
    raw: Any,
    path: str,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
    strict_unknown_fields: bool,
    valid_event_types: Optional[Iterable[str]] = None,
) -> Optional[Dict[str, Any]]:
    if not isinstance(identifier, str) or not _MENU_ID_RE.fullmatch(identifier):
        errors.append(ValidationIssue("error", path, "menu ID must use uppercase letters, digits, underscores and optional dot-separated groups"))
    if not isinstance(raw, dict):
        errors.append(ValidationIssue("error", path, "must be an object"))
        return None

    _check_unknown_keys(raw, _MENU_KEYS, path, errors, warnings, strict=strict_unknown_fields)
    normalized = deepcopy(raw)
    # ``is_brush_menu`` was a legacy UI mode. Brush assets now use ordinary
    # captured operator presets and may be assigned to any menu, so accept the
    # old field for compatibility but remove it from normalized configs.
    normalized.pop("is_brush_menu", None)
    for required in ("name", "key", "keymap", "slots"):
        if required not in raw:
            errors.append(ValidationIssue("error", f"{path}.{required}", "is required"))

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(ValidationIssue("error", f"{path}.name", "must be a non-empty string"))

    key = raw.get("key")
    if not isinstance(key, str) or not key.strip() or any(character.isspace() for character in key):
        errors.append(ValidationIssue("error", f"{path}.key", "must be a non-empty Blender event identifier without whitespace"))
    elif key != "NONE":
        reserved_message = reserved_menu_shortcut_message(key)
        if reserved_message:
            errors.append(ValidationIssue("error", f"{path}.key", reserved_message + " and cannot open a menu"))
        elif valid_event_types is not None and key not in valid_event_types:
            errors.append(ValidationIssue(
                "error",
                f"{path}.key",
                f"'{key}' is not a recognized Blender event identifier",
            ))

    keymap = raw.get("keymap")
    if not isinstance(keymap, str) or not keymap.strip():
        errors.append(ValidationIssue("error", f"{path}.keymap", "must be a non-empty Blender keymap name"))

    modifiers = raw.get("keymodifiers", [])
    if not isinstance(modifiers, list):
        errors.append(ValidationIssue("error", f"{path}.keymodifiers", "must be an array of modifier names"))
        modifiers = []
    else:
        seen = set()
        for index, modifier in enumerate(modifiers):
            modifier_path = f"{path}.keymodifiers[{index}]"
            if not isinstance(modifier, str) or modifier not in SUPPORTED_MODIFIERS:
                errors.append(ValidationIssue("error", modifier_path, f"must be one of {', '.join(sorted(SUPPORTED_MODIFIERS))}"))
            elif modifier in seen:
                errors.append(ValidationIssue("error", modifier_path, "modifier is duplicated"))
            seen.add(modifier)
    normalized["keymodifiers"] = modifiers

    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append(ValidationIssue("error", f"{path}.enabled", "must be a boolean"))
    normalized["enabled"] = enabled

    if "slots" in raw:
        normalized["slots"] = _validate_slots(raw["slots"], f"{path}.slots", errors)
    else:
        normalized["slots"] = {}

    raw_spaced_slots = raw.get("spaced_slots", {})
    if "spaced_slots" in raw:
        normalized["spaced_slots"] = _validate_slots(raw_spaced_slots, f"{path}.spaced_slots", errors)
    else:
        normalized["spaced_slots"] = {}

    # The enabled state must be independent of slot occupancy. An enabled
    # Spaced Slots grid can legitimately be empty while the user configures it.
    inferred_spaced_enabled = (
        isinstance(raw_spaced_slots, dict)
        and any(reference is not None for reference in raw_spaced_slots.values())
    )
    spaced_enabled = raw.get("spaced_slots_enabled", inferred_spaced_enabled)
    if not isinstance(spaced_enabled, bool):
        errors.append(ValidationIssue(
            "error",
            f"{path}.spaced_slots_enabled",
            "must be a boolean",
        ))
        spaced_enabled = False
    normalized["spaced_slots_enabled"] = spaced_enabled

    return normalized


def _resolve_action_reference(
    reference: str,
    owner_addon: Optional[str],
    global_operators: Mapping[str, Any],
    third_party: Mapping[str, Any],
    preset_index: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """Resolve legacy aliases or permanent preset IDs to a canonical ID."""
    if preset_index and reference in preset_index:
        return reference
    if ":" in reference:
        addon_id, action_id = reference.split(":", 1)
        addon = third_party.get(addon_id)
        action = addon.get("Operators", {}).get(action_id) if isinstance(addon, Mapping) else None
        return action.get("preset_id") if isinstance(action, Mapping) else None
    if owner_addon:
        own_addon = third_party.get(owner_addon, {})
        own_action = own_addon.get("Operators", {}).get(reference) if isinstance(own_addon, Mapping) else None
        if isinstance(own_action, Mapping):
            return own_action.get("preset_id")
    action = global_operators.get(reference)
    return action.get("preset_id") if isinstance(action, Mapping) else None


def validate_config(
    config: Any,
    *,
    strict_unknown_fields: bool = True,
    valid_event_types: Optional[Iterable[str]] = None,
) -> ValidationReport:
    """Validate and normalize a v2 config without mutating the caller's data.

    Missing optional sections and optional fields receive defaults. Required
    menu/action fields remain errors. Reference checks run after all operator
    collections have been normalized.
    """
    report = ValidationReport()
    errors = report.errors
    warnings = report.warnings
    if valid_event_types is not None:
        valid_event_types = frozenset(str(item) for item in valid_event_types)

    if not isinstance(config, Mapping):
        errors.append(ValidationIssue("error", "$", "configuration root must be an object"))
        return report

    config_data = dict(config)
    _check_unknown_keys(config_data, _TOP_LEVEL_KEYS, "$", errors, warnings, strict=strict_unknown_fields)
    normalized = deepcopy(config_data)

    version = config.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        errors.append(ValidationIssue("error", "schema_version", "must be an integer"))
    elif version != SCHEMA_VERSION:
        errors.append(ValidationIssue("error", "schema_version", f"unsupported schema version {version}; expected {SCHEMA_VERSION}"))

    for section in ("Menus", "Operators", "ThirdParty"):
        if section not in normalized:
            normalized[section] = {}
        elif not isinstance(normalized[section], dict):
            errors.append(ValidationIssue("error", section, "must be an object"))
            normalized[section] = {}

    global_operators: Dict[str, Any] = {}
    for action_id, action_data in normalized["Operators"].items():
        action = _validate_action(
            action_id,
            action_data,
            f"Operators.{action_id}",
            errors,
            warnings,
            strict_unknown_fields,
        )
        if action is not None:
            global_operators[action_id] = action
    normalized["Operators"] = global_operators

    third_party: Dict[str, Any] = {}
    for addon_id, addon_data in normalized["ThirdParty"].items():
        addon_path = f"ThirdParty.{addon_id}"
        if not isinstance(addon_id, str) or not _ADDON_ID_RE.fullmatch(addon_id):
            errors.append(ValidationIssue("error", addon_path, "addon ID must be a lowercase namespace using letters, digits, underscores, dots or hyphens"))
        if not isinstance(addon_data, dict):
            errors.append(ValidationIssue("error", addon_path, "must be an object"))
            continue

        _check_unknown_keys(addon_data, _THIRD_PARTY_KEYS, addon_path, errors, warnings, strict=strict_unknown_fields)
        name = addon_data.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(ValidationIssue("error", f"{addon_path}.name", "must be a non-empty string"))
        addon_enabled = addon_data.get("enabled", True)
        if not isinstance(addon_enabled, bool):
            errors.append(ValidationIssue("error", f"{addon_path}.enabled", "must be a boolean"))
            addon_enabled = True

        addon_operators_raw = addon_data.get("Operators", {})
        addon_menus_raw = addon_data.get("Menus", {})
        if not isinstance(addon_operators_raw, dict):
            errors.append(ValidationIssue("error", f"{addon_path}.Operators", "must be an object"))
            addon_operators_raw = {}
        if not isinstance(addon_menus_raw, dict):
            errors.append(ValidationIssue("error", f"{addon_path}.Menus", "must be an object"))
            addon_menus_raw = {}

        addon_operators: Dict[str, Any] = {}
        for action_id, action_data in addon_operators_raw.items():
            action = _validate_action(
                action_id,
                action_data,
                f"{addon_path}.Operators.{action_id}",
                errors,
                warnings,
                strict_unknown_fields,
            )
            if action is not None:
                addon_operators[action_id] = action

        addon_menus: Dict[str, Any] = {}
        for menu_id, menu_data in addon_menus_raw.items():
            menu = _validate_menu(
                menu_id,
                menu_data,
                f"{addon_path}.Menus.{menu_id}",
                errors,
                warnings,
                strict_unknown_fields,
                valid_event_types,
            )
            if menu is not None:
                addon_menus[menu_id] = menu

        third_party[addon_id] = {
            "name": name,
            "enabled": addon_enabled,
            "Operators": addon_operators,
            "Menus": addon_menus,
        }
    normalized["ThirdParty"] = third_party

    # Preset IDs are the canonical identity across the global and third-party
    # libraries. Reject collisions before any menu references are resolved.
    preset_index: Dict[str, Dict[str, Any]] = {}
    enum_value_index: Dict[int, str] = {}
    for collection_path, action_collection in (
        [("Operators", global_operators)]
        + [
            (f"ThirdParty.{addon_id}.Operators", addon.get("Operators", {}))
            for addon_id, addon in third_party.items()
        ]
    ):
        for action_id, action in action_collection.items():
            preset_id = str(action.get("preset_id", ""))
            if not preset_id:
                continue
            previous = preset_index.get(preset_id)
            if previous is not None:
                errors.append(ValidationIssue(
                    "error",
                    f"{collection_path}.{action_id}.preset_id",
                    f"duplicates permanent preset ID '{preset_id}'",
                ))
            else:
                preset_index[preset_id] = action
            enum_value = action.get("enum_value")
            if isinstance(enum_value, int) and not isinstance(enum_value, bool):
                previous_enum_path = enum_value_index.get(enum_value)
                if previous_enum_path is not None:
                    errors.append(ValidationIssue(
                        "error",
                        f"{collection_path}.{action_id}.enum_value",
                        f"duplicates persistent Blender enum value {enum_value} from {previous_enum_path}",
                    ))
                else:
                    enum_value_index[enum_value] = f"{collection_path}.{action_id}"

    menus: Dict[str, Any] = {}
    for menu_id, menu_data in normalized["Menus"].items():
        menu = _validate_menu(
            menu_id,
            menu_data,
            f"Menus.{menu_id}",
            errors,
            warnings,
            strict_unknown_fields,
            valid_event_types,
        )
        if menu is not None:
            menus[menu_id] = menu
    normalized["Menus"] = menus

    # Resolve all slot references after the global and third-party registries
    # have been collected. A local third-party menu first checks its own addon.
    all_menus: List[Tuple[str, Dict[str, Any], Optional[str]]] = []
    all_menus.extend((f"Menus.{menu_id}", menu, None) for menu_id, menu in menus.items())
    for addon_id, addon in third_party.items():
        all_menus.extend(
            (f"ThirdParty.{addon_id}.Menus.{menu_id}", menu, addon_id)
            for menu_id, menu in addon["Menus"].items()
        )

    keybinds: Dict[Tuple[str, str, Tuple[str, ...]], str] = {}
    reported_keybind_conflicts: set[Tuple[str, str]] = set()
    inferred_action_contexts: Dict[str, set[str]] = {}

    def _action_for_reference(reference: str, owner_addon: Optional[str]):
        canonical_id = _resolve_action_reference(
            reference, owner_addon, global_operators, third_party, preset_index
        )
        return canonical_id, preset_index.get(canonical_id) if canonical_id else None

    for menu_path, menu, owner_addon in all_menus:
        menu_contexts = keymap_contexts(menu.get("keymap", ""))
        for slot_collection in ("slots", "spaced_slots"):
            slot_map = menu.get(slot_collection, {})
            for slot, action_ref in list(slot_map.items()):
                if action_ref is None:
                    continue
                canonical_id, action = _action_for_reference(action_ref, owner_addon)
                if action is None or canonical_id is None:
                    errors.append(ValidationIssue(
                        "error",
                        f"{menu_path}.{slot_collection}.{slot}",
                        f"references unknown action '{action_ref}'",
                    ))
                    continue
                # Normalize legacy action-key references to permanent IDs.
                # This makes every runtime/menu-editor slot reference stable.
                slot_map[slot] = canonical_id
                if menu_contexts:
                    inferred_action_contexts.setdefault(canonical_id, set()).update(menu_contexts)

        owner_enabled = owner_addon is None or third_party.get(owner_addon, {}).get("enabled", True)
        if menu.get("enabled", True) and owner_enabled:
            key = menu.get("key", "")
            modifiers = tuple(sorted(menu.get("keymodifiers", [])))
            for context_name in menu_contexts:
                signature = (context_name, key, modifiers)
                previous = keybinds.get(signature)
                if previous:
                    # Avoid six copies of an identical warning when a Common
                    # shortcut collides with another menu in every mode.
                    conflict_pair = (menu_path, previous)
                    if conflict_pair not in reported_keybind_conflicts:
                        warnings.append(ValidationIssue(
                            "warning",
                            menu_path,
                            f"keybinding conflicts with {previous} ({key} in {context_name})",
                        ))
                        reported_keybind_conflicts.add(conflict_pair)
                else:
                    keybinds[signature] = menu_path

    # Duplicate action labels are confusing in the scoped menu picker. Warn
    # only when two different presets can appear in the same keymap context;
    # identical labels in unrelated contexts are valid and remain independent.
    action_label_owners: Dict[Tuple[str, str], Tuple[str, Mapping[str, Any]]] = {}
    action_collections = [("Operators", global_operators)]
    for addon_id, addon in third_party.items():
        if addon.get("enabled", True):
            action_collections.append((f"ThirdParty.{addon_id}.Operators", addon.get("Operators", {})))
    for collection_path, action_collection in action_collections:
        for action_id, action in action_collection.items():
            label = str(action.get("name") or action_id).strip()
            if not label:
                continue
            contexts = set(str(item).strip() for item in action.get("contexts", []) if str(item).strip())
            local_reference = str(action.get("preset_id", ""))
            contexts.update(inferred_action_contexts.get(local_reference, set()))
            action_path = f"{collection_path}.{action_id}"
            for context_name in contexts:
                signature = (context_name.casefold(), label.casefold())
                previous = action_label_owners.get(signature)
                if previous and previous[0] != action_path:
                    previous_path, previous_action = previous
                    # Exact aliases with identical operator/property behavior
                    # are redundant presets, but not an ambiguous picker result.
                    previous_operator_id = str(previous_action.get("operator_id", ""))
                    same_action = (
                        previous_operator_id == action.get("operator_id")
                        and operator_properties_match(
                            previous_operator_id,
                            previous_action.get("properties", {}),
                            action.get("properties", {}),
                        )
                        and bool(previous_action.get("invoke", False)) == bool(action.get("invoke", False))
                    )
                    if not same_action:
                        warnings.append(ValidationIssue(
                            "warning",
                            f"{action_path}.name",
                            f"preset name '{label}' duplicates {previous_path} in the '{context_name}' context",
                        ))
                else:
                    action_label_owners[signature] = (action_path, action)

    preferences_raw = normalized.get("Preferences", {})
    normalized["Preferences"] = _validate_preferences(
        preferences_raw,
        errors,
        warnings,
        strict_unknown_fields,
    )

    report.config = normalized if not errors else None
    return report
