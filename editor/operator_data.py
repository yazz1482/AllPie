"""Blender-independent operations for the AllPie operator preset editor.

Operator presets are reusable action definitions. This module deliberately
contains no Blender imports so CRUD, context classification and usage tracking
can be tested without starting Blender.
"""

from __future__ import annotations

from copy import deepcopy
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.schema import keymap_contexts
from ..core.preset_identity import MAX_ENUM_VALUE, unique_enum_value
from ..core.validation import validate_config
from ..core.brush_assets import normalize_operator_properties, operator_properties_match
from .operator_properties import strip_default_properties

OPERATOR_DATA_API_VERSION = 22

_CONTEXT_CATEGORY = {
    "object mode": "OBJECT",
    "mesh": "MESH",
    "sculpt": "SCULPT",
    "image paint": "IMAGE_PAINT",
    "vertex paint": "VERTEX_PAINT",
    "weight paint": "WEIGHT_PAINT",
    "uv editor": "UV_EDITOR",
    "image": "IMAGE_EDITOR",
    "node editor": "NODE_EDITOR",
}

CATEGORY_ITEMS = (
    ("ALL", "All", "All AllPie and third-party operator presets"),
    ("OBJECT", "Object", "Presets used or catalogued in Object Mode"),
    ("MESH", "Mesh", "Presets used or catalogued in Mesh Edit Mode"),
    ("SCULPT", "Sculpt", "Presets used or catalogued in Sculpt Mode"),
    ("IMAGE_PAINT", "Texture Paint", "Presets used or catalogued in Texture Paint"),
    ("VERTEX_PAINT", "Vertex Paint", "Presets used or catalogued in Vertex Paint"),
    ("WEIGHT_PAINT", "Weight Paint", "Presets used or catalogued in Weight Paint"),
    ("UV_EDITOR", "UV Editor", "Presets used or catalogued in the UV Editor"),
    ("IMAGE_EDITOR", "Image Editor", "Presets used or catalogued in the Image Editor"),
    ("NODE_EDITOR", "Node Editor", "Presets used or catalogued in node editors"),
    ("OTHER", "Other Contexts", "Presets associated with custom Blender keymap contexts"),
    ("UNASSIGNED", "Unassigned", "Presets that are not used by a menu and have no context tags"),
    ("THIRD_PARTY", "Third Party", "Presets owned by external addons"),
)


def load_bundled_action_ids(path: Any) -> frozenset[str]:
    """Load a complete, validated bundled preset-ID protection catalogue.

    This intentionally fails closed. A missing, empty, malformed or partially
    identified bundled catalogue must never be treated as an empty set, since
    that would make shipped presets appear user-owned to destructive actions.
    """
    source = Path(path).expanduser()
    try:
        with source.open("r", encoding="utf-8") as handle:
            bundled = json.load(handle)
        if not isinstance(bundled, dict):
            raise ValueError("configuration root is not an object")
        report = validate_config(bundled)
        if not report.valid or report.config is None:
            details = "; ".join(str(issue) for issue in report.errors[:5])
            raise ValueError(f"bundled configuration failed schema validation: {details}")
        actions = report.config.get("Operators")
        if not isinstance(actions, dict) or not actions:
            raise ValueError("bundled operator preset collection is missing or empty")

        preset_ids = []
        for legacy_id, action in actions.items():
            if not isinstance(action, dict):
                raise ValueError(f"preset '{legacy_id}' is not an object")
            preset_id = str(action.get("preset_id", "") or "").strip()
            if not preset_id:
                raise ValueError(f"preset '{legacy_id}' has no permanent ID")
            preset_ids.append(preset_id)
        if len(set(preset_ids)) != len(preset_ids):
            raise ValueError("bundled operator preset IDs are not unique")
        return frozenset(preset_ids)
    except Exception as error:
        raise RuntimeError(
            f"Could not verify bundled AllPie preset protection from '{source}': {error}"
        ) from error


def split_action_id(action_id: str) -> Tuple[Optional[str], str]:
    if ":" in str(action_id):
        addon_id, local_id = str(action_id).split(":", 1)
        return addon_id, local_id
    return None, str(action_id)


def _iter_action_containers(config: Mapping[str, Any]):
    """Yield (mapping, legacy key, owning addon) for every preset record."""
    global_actions = config.get("Operators", {})
    if isinstance(global_actions, Mapping):
        for local_id, action in global_actions.items():
            if isinstance(action, Mapping):
                yield global_actions, str(local_id), None, action

    third_party = config.get("ThirdParty", {})
    if isinstance(third_party, Mapping):
        for addon_id, addon in third_party.items():
            if not isinstance(addon, Mapping):
                continue
            actions = addon.get("Operators", {})
            if not isinstance(actions, Mapping):
                continue
            for local_id, action in actions.items():
                if isinstance(action, Mapping):
                    yield actions, str(local_id), str(addon_id), action


def _find_action_by_preset_id(config: Mapping[str, Any], preset_id: str):
    for container, local_id, owner_addon, action in _iter_action_containers(config):
        if str(action.get("preset_id", "")) == str(preset_id):
            return container, local_id, owner_addon, action
    return None


def _new_preset_id(config: Mapping[str, Any]) -> str:
    existing = {
        str(action.get("preset_id", ""))
        for _container, _local_id, _owner, action in _iter_action_containers(config)
    }
    while True:
        candidate = "op_" + uuid.uuid4().hex
        if candidate not in existing:
            return candidate


def _new_enum_value(config: Mapping[str, Any], preset_id: str) -> int:
    used_values = {
        action.get("enum_value")
        for _container, _local_id, _owner, action in _iter_action_containers(config)
        if isinstance(action.get("enum_value"), int)
        and not isinstance(action.get("enum_value"), bool)
        and 1 <= action.get("enum_value") <= MAX_ENUM_VALUE
    }
    return unique_enum_value(preset_id, used_values)


def get_action_container(config: Dict[str, Any], action_id: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """Resolve a permanent preset ID or a legacy dictionary alias to its record."""
    action_id = str(action_id)
    found = _find_action_by_preset_id(config, action_id)
    if found is not None:
        container, local_id, owner_addon, _action = found
        return container, local_id, owner_addon

    addon_id, local_id = split_action_id(action_id)
    if addon_id is not None:
        addon = config.get("ThirdParty", {}).get(addon_id)
        if isinstance(addon, Mapping):
            container = addon.get("Operators", {})
            if isinstance(container, dict) and local_id in container:
                return container, local_id, addon_id
        raise KeyError(f"Operator preset '{action_id}' does not exist")

    container = config.get("Operators", {})
    if isinstance(container, dict) and action_id in container:
        return container, action_id, None
    raise KeyError(f"Operator preset '{action_id}' does not exist")


def get_operator(config: Mapping[str, Any], action_id: str) -> Dict[str, Any]:
    container, local_id, _owner_addon = get_action_container(dict(config), str(action_id))
    try:
        return container[local_id]
    except KeyError as error:
        raise KeyError(f"Operator preset '{action_id}' does not exist") from error


def _resolve_reference(reference: str, owner_addon: Optional[str], config: Mapping[str, Any]) -> Optional[str]:
    """Resolve a stable ID or supported legacy alias to a permanent preset ID."""
    reference = str(reference or "")
    if not reference:
        return None
    if _find_action_by_preset_id(config, reference) is not None:
        return reference
    if ":" in reference:
        addon_id, local_id = split_action_id(reference)
        addon = config.get("ThirdParty", {}).get(addon_id, {})
        action = addon.get("Operators", {}).get(local_id) if isinstance(addon, Mapping) else None
        return str(action.get("preset_id")) if isinstance(action, Mapping) and action.get("preset_id") else None
    if owner_addon:
        own_addon = config.get("ThirdParty", {}).get(owner_addon, {})
        own_action = own_addon.get("Operators", {}).get(reference) if isinstance(own_addon, Mapping) else None
        if isinstance(own_action, Mapping) and own_action.get("preset_id"):
            return str(own_action["preset_id"])
    action = config.get("Operators", {}).get(reference)
    if isinstance(action, Mapping) and action.get("preset_id"):
        return str(action["preset_id"])
    return None


def _build_preset_reference_indexes(config: Mapping[str, Any]):
    """Build constant-time maps for permanent IDs and legacy preset aliases."""
    by_preset_id: Dict[str, Dict[str, Any]] = {}
    global_aliases: Dict[str, str] = {}
    third_party_aliases: Dict[Tuple[str, str], str] = {}

    global_actions = config.get("Operators", {})
    if isinstance(global_actions, Mapping):
        for legacy_id, action in global_actions.items():
            if not isinstance(action, Mapping):
                continue
            preset_id = str(action.get("preset_id", ""))
            if not preset_id:
                continue
            by_preset_id[preset_id] = dict(action)
            global_aliases[str(legacy_id)] = preset_id

    third_party = config.get("ThirdParty", {})
    if isinstance(third_party, Mapping):
        for addon_id, addon in third_party.items():
            if not isinstance(addon, Mapping):
                continue
            actions = addon.get("Operators", {})
            if not isinstance(actions, Mapping):
                continue
            for legacy_id, action in actions.items():
                if not isinstance(action, Mapping):
                    continue
                preset_id = str(action.get("preset_id", ""))
                if not preset_id:
                    continue
                by_preset_id[preset_id] = dict(action)
                third_party_aliases[(str(addon_id), str(legacy_id))] = preset_id

    return by_preset_id, global_aliases, third_party_aliases


def _resolve_reference_index(
    reference: str,
    owner_addon: Optional[str],
    by_preset_id: Mapping[str, Any],
    global_aliases: Mapping[str, str],
    third_party_aliases: Mapping[Tuple[str, str], str],
) -> Optional[str]:
    """Resolve menu references in O(1), preserving legacy owner-first lookup."""
    reference = str(reference or "")
    if not reference:
        return None
    if reference in by_preset_id:
        return reference
    if ":" in reference:
        addon_id, local_id = split_action_id(reference)
        return third_party_aliases.get((str(addon_id), str(local_id)))
    if owner_addon:
        local_match = third_party_aliases.get((str(owner_addon), reference))
        if local_match:
            return local_match
    return global_aliases.get(reference)


def _collect_menu_usage_contexts(config: Mapping[str, Any]):
    """Collect preset usages and inferred contexts in one pass over all menus."""
    by_preset_id, global_aliases, third_party_aliases = _build_preset_reference_indexes(config)
    contexts_by_preset: Dict[str, List[str]] = {}
    usages_by_preset: Dict[str, List[Dict[str, Any]]] = {}

    def visit_menu(menu_id: str, menu: Mapping[str, Any], owner_addon: Optional[str]) -> None:
        keymap = str(menu.get("keymap", ""))
        menu_contexts = keymap_contexts(keymap.strip())
        menu_name = str(menu.get("name", menu_id))
        for field, slot_type in (("slots", "Main"), ("spaced_slots", "Spaced")):
            slot_map = menu.get(field, {})
            if not isinstance(slot_map, Mapping):
                continue
            for slot_number, reference in slot_map.items():
                if not isinstance(reference, str):
                    continue
                preset_id = _resolve_reference_index(
                    reference,
                    owner_addon,
                    by_preset_id,
                    global_aliases,
                    third_party_aliases,
                )
                if not preset_id:
                    continue

                if menu_contexts:
                    target_contexts = contexts_by_preset.setdefault(preset_id, [])
                    existing = {value.casefold() for value in target_contexts}
                    for context_name in menu_contexts:
                        if context_name.casefold() not in existing:
                            target_contexts.append(context_name)
                            existing.add(context_name.casefold())

                usages_by_preset.setdefault(preset_id, []).append({
                    "menu_id": menu_id,
                    "menu_name": menu_name,
                    "keymap": keymap,
                    "slot_number": str(slot_number),
                    "slot_type": slot_type,
                    "owner_addon": owner_addon or "",
                })

    for menu_id, menu in config.get("Menus", {}).items():
        if isinstance(menu, Mapping):
            visit_menu(str(menu_id), menu, None)
    for addon_id, addon in config.get("ThirdParty", {}).items():
        if not isinstance(addon, Mapping):
            continue
        for local_id, menu in addon.get("Menus", {}).items():
            if isinstance(menu, Mapping):
                visit_menu(f"{addon_id}:{local_id}", menu, str(addon_id))

    for usages in usages_by_preset.values():
        usages.sort(key=lambda item: (
            item["menu_name"].casefold(),
            item["slot_type"],
            int(item["slot_number"]),
        ))
    return by_preset_id, contexts_by_preset, usages_by_preset


def get_operator_usages(config: Mapping[str, Any], action_id: str) -> List[Dict[str, Any]]:
    """Return every normal/spaced slot referencing one preset in O(P + S)."""
    by_preset_id, _contexts, usages = _collect_menu_usage_contexts(config)
    target_id = str(action_id or "")
    if target_id not in by_preset_id:
        by_id, global_aliases, third_party_aliases = _build_preset_reference_indexes(config)
        if ":" in target_id:
            target_id = _resolve_reference_index(target_id, None, by_id, global_aliases, third_party_aliases) or target_id
        else:
            target_id = global_aliases.get(target_id, target_id)
    return list(usages.get(target_id, ()))


def _all_menu_contexts(config: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Map permanent preset IDs to distinct contexts inferred from menu usage."""
    _by_preset_id, contexts, _usages = _collect_menu_usage_contexts(config)
    return contexts


def iter_operator_records(config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return UI-ready presets keyed by permanent ID with inferred contexts.

    Menu references are indexed once, then each preset is materialized from
    those maps. The old implementation re-scanned every menu and every preset
    for each action, which made the slot search scale approximately O(P² × S).
    This implementation is O(P + S), where P is presets and S is occupied slots.
    """
    by_preset_id, menu_contexts, usages_by_preset = _collect_menu_usage_contexts(config)
    records: List[Dict[str, Any]] = []

    def add_record(legacy_id: str, action: Mapping[str, Any], owner_addon: Optional[str], addon_name: str = "") -> None:
        preset_id = str(action.get("preset_id", ""))
        if not preset_id:
            return
        contexts: List[str] = []
        seen_contexts = set()
        for value in list(action.get("contexts", ())) + menu_contexts.get(preset_id, []):
            if not isinstance(value, str) or not value.strip():
                continue
            normalized = value.strip()
            folded = normalized.casefold()
            if folded not in seen_contexts:
                contexts.append(normalized)
                seen_contexts.add(folded)
        contexts.sort(key=str.casefold)
        categories = {
            _CONTEXT_CATEGORY.get(context.casefold(), "OTHER")
            for context in contexts
        }
        usages = usages_by_preset.get(preset_id, [])
        records.append({
            "action_id": preset_id,
            "preset_id": preset_id,
            "legacy_id": legacy_id,
            "local_id": legacy_id,
            "name": str(action.get("name", legacy_id)),
            "search_name": str(action.get("search_name") or action.get("name") or legacy_id),
            "description": str(action.get("description", "")),
            "operator_id": str(action.get("operator_id", "")),
            "invoke": bool(action.get("invoke", False)),
            "properties": deepcopy(action.get("properties", {})),
            "explicit_contexts": list(action.get("contexts", [])),
            "contexts": contexts,
            "categories": sorted(categories),
            "owner_addon": owner_addon or "",
            "addon_name": addon_name or ("AllPie" if owner_addon is None else owner_addon),
            "usages": usages,
            "usage_count": len(usages),
            "unassigned": not contexts and not usages,
        })

    for legacy_id, action in config.get("Operators", {}).items():
        add_record(str(legacy_id), action, None)
    for addon_id, addon in config.get("ThirdParty", {}).items():
        if not isinstance(addon, Mapping):
            continue
        addon_name = str(addon.get("name", addon_id))
        for legacy_id, action in addon.get("Operators", {}).items():
            add_record(str(legacy_id), action, str(addon_id), addon_name)

    records.sort(key=lambda record: (record["name"].casefold(), record["action_id"]))
    return records


def filter_operator_records(records: Iterable[Mapping[str, Any]], category: str) -> List[Dict[str, Any]]:
    category = str(category or "ALL").upper()
    if category == "ALL":
        return [dict(record) for record in records]
    if category == "THIRD_PARTY":
        return [dict(record) for record in records if record.get("owner_addon")]
    if category == "UNASSIGNED":
        return [dict(record) for record in records if record.get("unassigned")]
    return [dict(record) for record in records if category in record.get("categories", ())]


def build_operator_picker_records(
    config: Mapping[str, Any],
    blender_operators: Iterable[Mapping[str, Any]],
    *,
    preset_records: Iterable[Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Build the unified slot-picker catalog from saved presets and live RNA ops.

    ``preset_records`` lets the caller reuse the already-computed, efficiently
    indexed library records for cache fingerprinting and UI population.
    """
    presets = list(preset_records) if preset_records is not None else iter_operator_records(config)
    records: List[Dict[str, Any]] = []
    for preset in presets:
        operator_id = str(preset.get("operator_id", ""))
        if not operator_id:
            continue
        records.append({
            "source_kind": "PRESET",
            "action_id": str(preset.get("action_id", "")),
            "operator_id": operator_id,
            "name": str(preset.get("name") or preset.get("action_id", "")),
            "search_alias": str(preset.get("search_name") or preset.get("name") or ""),
            "description": str(preset.get("description", "")),
            "module": operator_id.partition(".")[0],
            "contexts": list(preset.get("contexts", ())),
            "categories": list(preset.get("categories", ())),
            "unassigned": bool(preset.get("unassigned", False)),
            "invoke": bool(preset.get("invoke", True)),
        })

    for operator in blender_operators:
        operator_id = str(operator.get("operator_id", ""))
        if not operator_id:
            continue
        records.append({
            "source_kind": "BLENDER",
            "action_id": "",
            "operator_id": operator_id,
            "name": str(operator.get("display_name") or operator.get("name") or operator_id),
            "description": str(operator.get("description", "")),
            "module": str(operator.get("module") or operator_id.partition(".")[0]),
            "contexts": [],
            "categories": [],
            "unassigned": True,
            "invoke": True,
        })

    records.sort(key=lambda item: (
        str(item["name"]).casefold(),
        item["source_kind"],
        item["action_id"],
        item["operator_id"],
    ))
    return records


def _make_unique_id(container: Mapping[str, Any], base_id: str) -> str:
    candidate = base_id
    suffix = 1
    while candidate in container:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    return candidate


def _remap_menu_references_for_duplicate(
    config: Dict[str, Any],
    duplicate_preset_id: str,
    canonical_preset_id: str,
    by_preset_id: Mapping[str, Any],
    global_aliases: Mapping[str, str],
    third_party_aliases: Mapping[Tuple[str, str], str],
) -> None:
    """Redirect every menu usage of an exact duplicate to its canonical preset."""
    def visit_menu(menu: Mapping[str, Any], owner_addon: Optional[str]) -> None:
        for field in ("slots", "spaced_slots"):
            slot_map = menu.get(field, {})
            if not isinstance(slot_map, dict):
                continue
            for slot_number, reference in tuple(slot_map.items()):
                if not isinstance(reference, str):
                    continue
                resolved = _resolve_reference_index(
                    reference,
                    owner_addon,
                    by_preset_id,
                    global_aliases,
                    third_party_aliases,
                )
                if resolved == duplicate_preset_id:
                    slot_map[slot_number] = canonical_preset_id

    for menu in config.get("Menus", {}).values():
        if isinstance(menu, Mapping):
            visit_menu(menu, None)
    for addon_id, addon in config.get("ThirdParty", {}).items():
        if not isinstance(addon, Mapping):
            continue
        for menu in addon.get("Menus", {}).values():
            if isinstance(menu, Mapping):
                visit_menu(menu, str(addon_id))


def create_or_reuse_blender_operator(
    config: Dict[str, Any],
    *,
    operator_id: str,
    name: str,
    description: str,
    context_name: str,
    properties: Mapping[str, Any] | None = None,
    context_names: Iterable[str] | None = None,
    invoke: bool = True,
    search_name: str | None = None,
    property_defaults: Mapping[str, Any] | None = None,
) -> Tuple[str, bool]:
    """Create/reuse a configured preset and collapse exact same-name aliases.

    Properties are canonicalized against current Blender RNA defaults before
    matching, so an older sparse preset and a newly captured dialog containing
    explicit defaults resolve to one reusable action.
    """
    operator_id = str(operator_id).strip()
    name = str(name).strip() or operator_id
    description = str(description).strip()
    search_name = str(search_name or name).strip() or name
    context_name = str(context_name).strip()
    target_contexts = tuple(dict.fromkeys(
        str(value).strip() for value in (context_names if context_names is not None else (context_name,))
        if str(value).strip()
    ))
    target_contexts_folded = {value.casefold() for value in target_contexts}
    property_defaults = {
        str(key): value for key, value in (property_defaults or {}).items()
    }
    properties = strip_default_properties(properties or {}, property_defaults)
    properties = normalize_operator_properties(operator_id, properties)
    invoke = bool(invoke)
    operators = config.setdefault("Operators", {})

    matches = []
    for order, (legacy_id, action) in enumerate(tuple(operators.items())):
        if not isinstance(action, Mapping):
            continue
        if str(action.get("operator_id", "")) != operator_id:
            continue
        if bool(action.get("invoke", False)) != invoke:
            continue
        if str(action.get("name", "")) != name:
            continue

        raw_action_properties = normalize_operator_properties(operator_id, action.get("properties", {}))
        canonical_action_properties = strip_default_properties(raw_action_properties, property_defaults)
        if not operator_properties_match(operator_id, canonical_action_properties, properties):
            continue
        preset_id = str(action.get("preset_id", ""))
        if not preset_id:
            continue
        contexts = action.get("contexts", [])
        context_match = any(str(value).casefold() in target_contexts_folded for value in contexts) if target_contexts_folded else False
        is_user_defined = bool(action.get("user_defined", False))
        matches.append((
            1 if is_user_defined else 0,
            0 if context_match else 1,
            order,
            str(legacy_id),
            preset_id,
            action,
            canonical_action_properties,
        ))

    if matches:
        matches.sort(key=lambda item: (item[0], item[1], item[2], item[4]))
        _user_rank, _context_rank, _order, canonical_legacy_id, preset_id, action, canonical_properties = matches[0]
        # Persist the sparse form only on presets that are actually being
        # reused. Unrelated named variants are left byte-for-byte untouched.
        action["properties"] = deepcopy(canonical_properties)
        contexts = action.setdefault("contexts", [])
        existing_contexts = {str(value).casefold() for value in contexts}
        for target_context in target_contexts:
            if target_context.casefold() not in existing_contexts:
                contexts.append(target_context)
                existing_contexts.add(target_context.casefold())

        # Previous builds could create a second same-name preset because a raw
        # Blender operator dialog stored its default values explicitly. Merge
        # only exact effective aliases; preserve differently configured variants.
        by_preset_id, global_aliases, third_party_aliases = _build_preset_reference_indexes(config)
        for duplicate in matches[1:]:
            duplicate_legacy_id, duplicate_preset_id, duplicate_action, duplicate_properties = (
                duplicate[3], duplicate[4], duplicate[5], duplicate[6]
            )
            if duplicate_preset_id == preset_id:
                continue
            if duplicate_action is not action:
                duplicate_contexts = duplicate_action.get("contexts", [])
                canonical_contexts = action.setdefault("contexts", [])
                known = {str(value).casefold() for value in canonical_contexts}
                for value in duplicate_contexts:
                    if str(value).casefold() not in known:
                        canonical_contexts.append(value)
                        known.add(str(value).casefold())
                _remap_menu_references_for_duplicate(
                    config,
                    duplicate_preset_id,
                    preset_id,
                    by_preset_id,
                    global_aliases,
                    third_party_aliases,
                )
                operators.pop(duplicate_legacy_id, None)

        return preset_id, False

    base_id = re.sub(r"[^A-Za-z0-9]+", "_", operator_id).strip("_").upper()
    base_id = base_id or "BLENDER_OPERATOR"
    legacy_id = _make_unique_id(operators, base_id)
    preset_id = add_operator(
        config,
        action_id=legacy_id,
        name=name,
        search_name=search_name,
        description=description,
        operator_id=operator_id,
        invoke=invoke,
        properties=properties,
        contexts=target_contexts,
    )
    return preset_id, True


def add_operator(
    config: Dict[str, Any],
    *,
    action_id: str,
    name: str,
    search_name: str,
    description: str,
    operator_id: str,
    invoke: bool,
    properties: Mapping[str, Any],
    contexts: Iterable[str] = (),
    preset_id: str | None = None,
) -> str:
    """Create one preset and return its permanent unique ID."""
    action_id = str(action_id).strip()
    if not action_id:
        raise ValueError("Operator preset storage key cannot be empty")
    operators = config.setdefault("Operators", {})
    if action_id in operators:
        raise ValueError(f"Operator preset storage key '{action_id}' already exists")
    preset_id = str(preset_id or _new_preset_id(config)).strip()
    if _find_action_by_preset_id(config, preset_id) is not None:
        raise ValueError(f"Permanent operator preset ID '{preset_id}' already exists")
    enum_value = _new_enum_value(config, preset_id)
    operators[action_id] = {
        "preset_id": preset_id,
        "enum_value": enum_value,
        "name": str(name).strip() or action_id,
        "search_name": str(search_name).strip() or str(name).strip() or action_id,
        "description": str(description).strip(),
        "operator_id": str(operator_id).strip(),
        "invoke": bool(invoke),
        "properties": deepcopy(dict(properties)),
        "contexts": list(dict.fromkeys(str(value).strip() for value in contexts if str(value).strip())),
        "user_defined": True,
    }
    return preset_id


def duplicate_operator(config: Dict[str, Any], action_id: str) -> str:
    """Copy any preset into the AllPie namespace, assigning a fresh stable ID."""
    source = get_operator(config, action_id)
    _container, legacy_id, _owner = get_action_container(config, action_id)
    new_legacy_id = _make_unique_id(config.setdefault("Operators", {}), f"{legacy_id}_COPY")
    duplicate = deepcopy(source)
    duplicate["preset_id"] = _new_preset_id(config)
    duplicate["enum_value"] = _new_enum_value(config, duplicate["preset_id"])
    duplicate["name"] = f"{source.get('name', legacy_id)} Copy"
    duplicate["search_name"] = f"{source.get('search_name') or source.get('name', legacy_id)} Copy"

    effective_contexts = list(source.get("contexts", ()))
    for context_name in _all_menu_contexts(config).get(str(source.get("preset_id", "")), ()):
        if context_name.casefold() not in {value.casefold() for value in effective_contexts}:
            effective_contexts.append(context_name)
    duplicate["contexts"] = effective_contexts
    duplicate["user_defined"] = True

    config["Operators"][new_legacy_id] = duplicate
    return duplicate["preset_id"]


def update_operator(
    config: Dict[str, Any],
    action_id: str,
    *,
    name: str,
    search_name: str,
    description: str,
    operator_id: str,
    invoke: bool,
    properties: Mapping[str, Any],
    contexts: Iterable[str] = (),
) -> None:
    container, local_id, owner_addon = get_action_container(config, action_id)
    if owner_addon is not None:
        raise ValueError("Third-party operator presets are managed by their owning addon; duplicate them to customize")
    action = container[local_id]
    action.update({
        "name": str(name).strip(),
        "search_name": str(search_name).strip(),
        "description": str(description).strip(),
        "operator_id": str(operator_id).strip(),
        "invoke": bool(invoke),
        "properties": deepcopy(dict(properties)),
        "contexts": list(dict.fromkeys(str(value).strip() for value in contexts if str(value).strip())),
    })


def remove_operator(config: Dict[str, Any], action_id: str) -> Dict[str, Any]:
    """Remove an unused AllPie preset; refuse to break any menu slot."""
    container, local_id, owner_addon = get_action_container(config, action_id)
    if owner_addon is not None:
        raise ValueError("Third-party operator presets are managed by their owning addon")
    preset_id = str(container[local_id].get("preset_id", action_id))
    usages = get_operator_usages(config, preset_id)
    if usages:
        names = sorted({usage["menu_name"] for usage in usages})
        raise ValueError(
            f"Cannot delete '{container[local_id].get('name', local_id)}': used by {len(usages)} slot(s) in {len(names)} menu(s): "
            + ", ".join(names[:5])
        )
    try:
        return container.pop(local_id)
    except KeyError as error:
        raise KeyError(f"Operator preset '{action_id}' does not exist") from error


def is_user_defined_action(
    action_id: str,
    action: Mapping[str, Any],
    bundled_action_ids: Iterable[str] = (),
) -> bool:
    """Return True for locally managed presets, keyed by permanent ID.

    An empty protection catalogue is treated as unknown, not as proof that all
    presets are user-owned. This keeps callers safe even if they accidentally
    omit the bundled catalogue.
    """
    preset_id = str(action.get("preset_id", action_id) or action_id)
    bundled_ids = set(bundled_action_ids)
    if not bundled_ids:
        return False
    # Bundled ownership always wins over stale or malformed user_defined
    # metadata. A shipped preset must never become deletable by carrying a
    # contradictory flag in a user-edited configuration.
    if preset_id in bundled_ids:
        return False
    return bool(action.get("user_defined") is True or preset_id)


def iter_user_action_records(
    config: Mapping[str, Any],
    bundled_action_ids: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Return user-added AllPie presets with usage summaries for the manager UI."""
    bundled_ids = set(bundled_action_ids)
    # Build the menu reference index once. Calling get_operator_usages() from
    # inside this loop rebuilt the same index for every preset, making cleanup
    # scale as O(P × (P + S)) instead of O(P + S).
    _by_preset_id, menu_contexts, usages_by_preset = _collect_menu_usage_contexts(config)
    records: List[Dict[str, Any]] = []
    for legacy_id, action in config.get("Operators", {}).items():
        preset_id = str(action.get("preset_id", ""))
        if not is_user_defined_action(preset_id, action, bundled_ids):
            continue
        usages = list(usages_by_preset.get(preset_id, ()))
        contexts = list(action.get("contexts", ()))
        for value in menu_contexts.get(preset_id, ()):
            if value.casefold() not in {str(item).casefold() for item in contexts}:
                contexts.append(value)
        records.append({
            "action_id": preset_id,
            "preset_id": preset_id,
            "legacy_id": str(legacy_id),
            "name": str(action.get("name", legacy_id)),
            "search_name": str(action.get("search_name") or action.get("name") or legacy_id),
            "description": str(action.get("description", "")),
            "operator_id": str(action.get("operator_id", "")),
            "contexts": sorted((str(value) for value in contexts if str(value).strip()), key=str.casefold),
            "usage_count": len(usages),
            "usages": usages,
        })
    records.sort(key=lambda record: (record["name"].casefold(), record["action_id"]))
    return records


def remove_unused_user_presets(
    config: Dict[str, Any],
    candidate_preset_ids: Iterable[str],
    bundled_action_ids: Iterable[str],
) -> List[Dict[str, Any]]:
    """Remove only snapshot candidates that are still local, custom and unused.

    ``candidate_preset_ids`` is the immutable set shown in the cleanup preview.
    Usage is indexed once from the fresh configuration passed to this function,
    so presets assigned while the confirmation dialog was open are preserved.
    Newly-unused presets are not considered until the next cleanup operation.
    """
    bundled_ids = frozenset(str(value) for value in bundled_action_ids if str(value))
    if not bundled_ids:
        raise ValueError("Bundled preset protection is unavailable; no presets were removed")

    operators = config.get("Operators")
    if not isinstance(operators, dict):
        raise ValueError("The local operator preset collection is unavailable")

    _by_preset_id, _contexts_by_preset, usages_by_preset = _collect_menu_usage_contexts(config)
    local_actions_by_preset = {
        str(action.get("preset_id", "")): (str(local_id), action)
        for local_id, action in operators.items()
        if isinstance(action, Mapping) and str(action.get("preset_id", ""))
    }
    removed: List[Dict[str, Any]] = []
    seen_ids = set()

    for raw_preset_id in candidate_preset_ids:
        preset_id = str(raw_preset_id or "").strip()
        if not preset_id or preset_id in seen_ids:
            continue
        seen_ids.add(preset_id)

        local_record = local_actions_by_preset.get(preset_id)
        if local_record is None:
            # The candidate was removed or replaced after the preview opened.
            continue
        local_id, action = local_record

        actual_preset_id = str(action.get("preset_id", "") or "").strip()
        if not actual_preset_id or actual_preset_id in bundled_ids:
            continue
        if not is_user_defined_action(actual_preset_id, action, bundled_ids):
            continue
        if usages_by_preset.get(actual_preset_id):
            continue

        removed_action = operators.pop(local_id)
        removed.append({
            "action_id": actual_preset_id,
            "legacy_id": str(local_id),
            "name": str(removed_action.get("name") or local_id),
            "operator_id": str(removed_action.get("operator_id", "")),
        })

    return removed


def remove_operator_and_unassign(
    config: Dict[str, Any],
    action_id: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Delete a user preset and clear every main/spaced slot using its UUID."""
    container, local_id, owner_addon = get_action_container(config, action_id)
    if owner_addon is not None:
        raise ValueError("Third-party operator presets are managed by their owning addon")
    if local_id not in container:
        raise KeyError(f"Operator preset '{action_id}' does not exist")

    preset_id = str(container[local_id].get("preset_id", action_id))
    usages = get_operator_usages(config, preset_id)
    for menu in config.get("Menus", {}).values():
        for field in ("slots", "spaced_slots"):
            slots = menu.get(field, {})
            if not isinstance(slots, dict):
                continue
            for slot_number, reference in tuple(slots.items()):
                if isinstance(reference, str) and _resolve_reference(reference, None, config) == preset_id:
                    slots[slot_number] = None

    for addon_id, addon in config.get("ThirdParty", {}).items():
        for menu in addon.get("Menus", {}).values():
            for field in ("slots", "spaced_slots"):
                slots = menu.get(field, {})
                if not isinstance(slots, dict):
                    continue
                for slot_number, reference in tuple(slots.items()):
                    if isinstance(reference, str) and _resolve_reference(reference, addon_id, config) == preset_id:
                        slots[slot_number] = None

    removed = container.pop(local_id)
    return removed, usages
