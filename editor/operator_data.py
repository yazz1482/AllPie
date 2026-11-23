"""Blender-independent operations for the AllPie operator preset editor.

Operator presets are reusable action definitions. This module deliberately
contains no Blender imports so CRUD, context classification and usage tracking
can be tested without starting Blender.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.schema import keymap_contexts
from ..core.brush_assets import normalize_operator_properties, operator_properties_match

OPERATOR_DATA_API_VERSION = 9

_CONTEXT_CATEGORY = {
    "object mode": "OBJECT",
    "mesh": "MESH",
    "sculpt": "SCULPT",
    "image paint": "IMAGE_PAINT",
    "vertex paint": "VERTEX_PAINT",
    "weight paint": "WEIGHT_PAINT",
}

CATEGORY_ITEMS = (
    ("ALL", "All", "All AllPie and third-party operator presets"),
    ("OBJECT", "Object", "Presets used or catalogued in Object Mode"),
    ("MESH", "Mesh", "Presets used or catalogued in Mesh Edit Mode"),
    ("SCULPT", "Sculpt", "Presets used or catalogued in Sculpt Mode"),
    ("IMAGE_PAINT", "Texture Paint", "Presets used or catalogued in Texture Paint"),
    ("VERTEX_PAINT", "Vertex Paint", "Presets used or catalogued in Vertex Paint"),
    ("WEIGHT_PAINT", "Weight Paint", "Presets used or catalogued in Weight Paint"),
    ("OTHER", "Other Contexts", "Presets associated with custom Blender keymap contexts"),
    ("UNASSIGNED", "Unassigned", "Presets that are not used by a menu and have no context tags"),
    ("THIRD_PARTY", "Third Party", "Presets owned by external addons"),
)


def split_action_id(action_id: str) -> Tuple[Optional[str], str]:
    if ":" in str(action_id):
        addon_id, local_id = str(action_id).split(":", 1)
        return addon_id, local_id
    return None, str(action_id)


def get_action_container(config: Dict[str, Any], action_id: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
    addon_id, local_id = split_action_id(action_id)
    if addon_id is None:
        return config["Operators"], local_id, None
    addon = config.get("ThirdParty", {}).get(addon_id)
    if not isinstance(addon, dict):
        raise KeyError(f"Third-party addon '{addon_id}' does not exist")
    return addon.setdefault("Operators", {}), local_id, addon_id


def get_operator(config: Mapping[str, Any], action_id: str) -> Dict[str, Any]:
    addon_id, local_id = split_action_id(action_id)
    if addon_id is None:
        container = config.get("Operators", {})
    else:
        addon = config.get("ThirdParty", {}).get(addon_id, {})
        container = addon.get("Operators", {}) if isinstance(addon, Mapping) else {}
    try:
        return container[local_id]
    except KeyError as error:
        raise KeyError(f"Operator preset '{action_id}' does not exist") from error


def _resolve_reference(reference: str, owner_addon: Optional[str], config: Mapping[str, Any]) -> Optional[str]:
    if ":" in reference:
        return reference
    if owner_addon:
        local_actions = config.get("ThirdParty", {}).get(owner_addon, {}).get("Operators", {})
        if reference in local_actions:
            return f"{owner_addon}:{reference}"
    if reference in config.get("Operators", {}):
        return reference
    return None


def get_operator_usages(config: Mapping[str, Any], action_id: str) -> List[Dict[str, Any]]:
    """Return every normal/spaced slot referencing one preset."""
    usages: List[Dict[str, Any]] = []

    def visit_menu(menu_id: str, menu: Mapping[str, Any], owner_addon: Optional[str]) -> None:
        for field, label in (("slots", "Main"), ("spaced_slots", "Spaced")):
            slot_map = menu.get(field, {})
            if not isinstance(slot_map, Mapping):
                continue
            for slot_number, reference in slot_map.items():
                if not isinstance(reference, str):
                    continue
                resolved = _resolve_reference(reference, owner_addon, config)
                if resolved != action_id:
                    continue
                usages.append({
                    "menu_id": menu_id,
                    "menu_name": str(menu.get("name", menu_id)),
                    "keymap": str(menu.get("keymap", "")),
                    "slot_number": str(slot_number),
                    "slot_type": label,
                    "owner_addon": owner_addon or "",
                })

    for menu_id, menu in config.get("Menus", {}).items():
        visit_menu(menu_id, menu, None)
    for addon_id, addon in config.get("ThirdParty", {}).items():
        for local_id, menu in addon.get("Menus", {}).items():
            visit_menu(f"{addon_id}:{local_id}", menu, addon_id)

    usages.sort(key=lambda item: (item["menu_name"].casefold(), item["slot_type"], int(item["slot_number"])))
    return usages


def _all_menu_contexts(config: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Map resolved action IDs to distinct menu keymap contexts."""
    contexts: Dict[str, List[str]] = {}

    def visit_menu(menu: Mapping[str, Any], owner_addon: Optional[str]) -> None:
        menu_contexts = keymap_contexts(str(menu.get("keymap", "")).strip())
        if not menu_contexts:
            return
        for field in ("slots", "spaced_slots"):
            slot_map = menu.get(field, {})
            if not isinstance(slot_map, Mapping):
                continue
            for reference in slot_map.values():
                if not isinstance(reference, str):
                    continue
                resolved = _resolve_reference(reference, owner_addon, config)
                if resolved is not None:
                    values = contexts.setdefault(resolved, [])
                    existing = {value.casefold() for value in values}
                    for keymap in menu_contexts:
                        if keymap.casefold() not in existing:
                            values.append(keymap)
                            existing.add(keymap.casefold())

    for menu in config.get("Menus", {}).values():
        visit_menu(menu, None)
    for addon_id, addon in config.get("ThirdParty", {}).items():
        for menu in addon.get("Menus", {}).values():
            visit_menu(menu, addon_id)
    return contexts


def iter_operator_records(config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return UI-ready operator records with inferred contexts and references."""
    menu_contexts = _all_menu_contexts(config)
    records: List[Dict[str, Any]] = []

    def add_record(action_id: str, action: Mapping[str, Any], owner_addon: Optional[str], addon_name: str = "") -> None:
        explicit = action.get("contexts", ())
        contexts: List[str] = []
        for value in list(explicit) + menu_contexts.get(action_id, []):
            if not isinstance(value, str) or not value.strip():
                continue
            if value.casefold() not in {item.casefold() for item in contexts}:
                contexts.append(value.strip())
        contexts.sort(key=str.casefold)
        categories = {
            _CONTEXT_CATEGORY.get(context.casefold(), "OTHER")
            for context in contexts
        }
        usages = get_operator_usages(config, action_id)
        local_id = split_action_id(action_id)[1]
        records.append({
            "action_id": action_id,
            "local_id": local_id,
            "name": str(action.get("name", local_id)),
            "search_name": str(action.get("search_name") or action.get("name") or local_id),
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

    for action_id, action in config.get("Operators", {}).items():
        add_record(action_id, action, None)
    for addon_id, addon in config.get("ThirdParty", {}).items():
        addon_name = str(addon.get("name", addon_id))
        for action_id, action in addon.get("Operators", {}).items():
            add_record(f"{addon_id}:{action_id}", action, addon_id, addon_name)

    records.sort(key=lambda record: (record["search_name"].casefold(), record["action_id"]))
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


def _make_unique_id(container: Mapping[str, Any], base_id: str) -> str:
    candidate = base_id
    suffix = 1
    while candidate in container:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    return candidate


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
) -> Tuple[str, bool]:
    """Create or reuse a preset matching an operator and its configured values.

    Two AllPie actions may use the same Blender operator with different RNA
    properties. They are only considered equivalent when both the invocation
    mode and complete JSON property mapping match.
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
    properties = normalize_operator_properties(operator_id, properties)
    invoke = bool(invoke)
    operators = config.setdefault("Operators", {})

    matches = []
    for action_id, action in operators.items():
        if str(action.get("operator_id", "")) != operator_id:
            continue
        if bool(action.get("invoke", False)) != invoke:
            continue
        action_properties = normalize_operator_properties(
            operator_id, action.get("properties", {})
        )
        if not operator_properties_match(operator_id, action_properties, properties):
            continue
        contexts = action.get("contexts", [])
        context_match = any(str(value).casefold() in target_contexts_folded for value in contexts) if target_contexts_folded else False
        label_match = (
            str(action.get("name", "")) == name
            or str(action.get("search_name", action.get("name", ""))) == name
        )
        score = (2 if context_match else 0) + (1 if label_match else 0)
        matches.append((score, action_id, action))

    if matches:
        _score, action_id, action = max(matches, key=lambda item: (item[0], item[1]))
        action_properties = normalize_operator_properties(
            operator_id, action.get("properties", {})
        )
        # Persist the canonical representation when an older preset used an
        # empty optional asset-library identifier. This keeps future equality
        # checks and exported JSON consistent.
        if action.get("properties", {}) != action_properties:
            action["properties"] = action_properties
        contexts = action.setdefault("contexts", [])
        existing_contexts = {str(value).casefold() for value in contexts}
        for target_context in target_contexts:
            if target_context.casefold() not in existing_contexts:
                contexts.append(target_context)
                existing_contexts.add(target_context.casefold())
        return action_id, False

    base_id = re.sub(r"[^A-Za-z0-9]+", "_", operator_id).strip("_").upper()
    base_id = base_id or "BLENDER_OPERATOR"
    action_id = _make_unique_id(operators, base_id)
    add_operator(
        config,
        action_id=action_id,
        name=name,
        search_name=search_name,
        description=description,
        operator_id=operator_id,
        invoke=invoke,
        properties=properties,
        contexts=target_contexts,
    )
    return action_id, True


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
) -> str:
    action_id = str(action_id).strip()
    if not action_id:
        raise ValueError("Operator preset ID cannot be empty")
    if action_id in config.setdefault("Operators", {}):
        raise ValueError(f"Operator preset '{action_id}' already exists")
    config["Operators"][action_id] = {
        "name": str(name).strip() or action_id,
        "search_name": str(search_name).strip() or str(name).strip() or action_id,
        "description": str(description).strip(),
        "operator_id": str(operator_id).strip(),
        "invoke": bool(invoke),
        "properties": deepcopy(dict(properties)),
        "contexts": list(dict.fromkeys(str(value).strip() for value in contexts if str(value).strip())),
        "user_defined": True,
    }
    return action_id


def duplicate_operator(config: Dict[str, Any], action_id: str) -> str:
    """Copy any preset into the AllPie namespace, without copying slot refs."""
    source = get_operator(config, action_id)
    local_id = split_action_id(action_id)[1]
    new_id = _make_unique_id(config.setdefault("Operators", {}), f"{local_id}_COPY")
    duplicate = deepcopy(source)
    duplicate["name"] = f"{source.get('name', local_id)} Copy"
    duplicate["search_name"] = f"{source.get('search_name') or source.get('name', local_id)} Copy"

    # A preset may inherit its search contexts from the menus that reference
    # it rather than storing explicit context tags. Preserve those effective
    # contexts when copying it into the AllPie namespace, while keeping the
    # duplicate independent from the source preset.
    effective_contexts = list(source.get("contexts", ()))
    for context_name in _all_menu_contexts(config).get(action_id, ()):
        if context_name.casefold() not in {value.casefold() for value in effective_contexts}:
            effective_contexts.append(context_name)
    duplicate["contexts"] = effective_contexts
    duplicate["user_defined"] = True

    config["Operators"][new_id] = duplicate
    return new_id


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
    usages = get_operator_usages(config, action_id)
    if usages:
        names = sorted({usage["menu_name"] for usage in usages})
        raise ValueError(
            f"Cannot delete '{action_id}': used by {len(usages)} slot(s) in {len(names)} menu(s): "
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
    """Return True for locally managed presets, including pre-marker custom entries.

    Older AllPie builds did not store provenance. Those presets are recognized
    by comparing their IDs with the bundled defaults shipped with the addon.
    Third-party presets are never considered user-managed here.
    """
    addon_id, _local_id = split_action_id(action_id)
    if addon_id is not None:
        return False
    if action.get("user_defined") is True:
        return True
    return action_id not in set(bundled_action_ids)


def iter_user_action_records(
    config: Mapping[str, Any],
    bundled_action_ids: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Return user-added AllPie presets with usage summaries for the manager UI."""
    bundled_ids = set(bundled_action_ids)
    records: List[Dict[str, Any]] = []
    for action_id, action in config.get("Operators", {}).items():
        if not is_user_defined_action(action_id, action, bundled_ids):
            continue
        usages = get_operator_usages(config, action_id)
        records.append({
            "action_id": action_id,
            "name": str(action.get("name", action_id)),
            "search_name": str(action.get("search_name") or action.get("name") or action_id),
            "description": str(action.get("description", "")),
            "operator_id": str(action.get("operator_id", "")),
            "usage_count": len(usages),
            "usages": usages,
        })
    records.sort(key=lambda record: (record["search_name"].casefold(), record["action_id"]))
    return records


def remove_operator_and_unassign(
    config: Dict[str, Any],
    action_id: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Delete a user preset and clear every main/spaced slot that references it.

    Returns the removed preset and the list of references cleared. Built-in
    callers should check ``is_user_defined_action`` before invoking this helper.
    Third-party-owned presets cannot be removed by AllPie users.
    """
    container, local_id, owner_addon = get_action_container(config, action_id)
    if owner_addon is not None:
        raise ValueError("Third-party operator presets are managed by their owning addon")
    if local_id not in container:
        raise KeyError(f"Operator preset '{action_id}' does not exist")

    usages = get_operator_usages(config, action_id)
    for menu in config.get("Menus", {}).values():
        for field in ("slots", "spaced_slots"):
            slots = menu.get(field, {})
            if not isinstance(slots, dict):
                continue
            for slot_number, reference in tuple(slots.items()):
                if isinstance(reference, str) and _resolve_reference(reference, None, config) == action_id:
                    slots[slot_number] = None

    for addon_id, addon in config.get("ThirdParty", {}).items():
        for menu in addon.get("Menus", {}).values():
            for field in ("slots", "spaced_slots"):
                slots = menu.get(field, {})
                if not isinstance(slots, dict):
                    continue
                for slot_number, reference in tuple(slots.items()):
                    if isinstance(reference, str) and _resolve_reference(reference, addon_id, config) == action_id:
                        slots[slot_number] = None

    removed = container.pop(local_id)
    return removed, usages

