"""Blender-independent operations used by the AllPie menu editor."""

from __future__ import annotations

ACTION_CONTEXT_CATALOG_API_VERSION = 6
BRUSH_ASSET_OPERATOR_ID = "brush.asset_activate"
ASSET_SHELF_OPERATOR_ID = "wm.call_asset_shelf_popover"
BRUSH_MENU_OPERATOR_IDS = frozenset({
    BRUSH_ASSET_OPERATOR_ID,
    ASSET_SHELF_OPERATOR_ID,
})

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.schema import BRUSH_MENU_KEYMAPS, COMMON_KEYMAP, keymap_contexts


# Menu browser categories are derived from each menu's Blender keymap context.
# This keeps the JSON schema simple: keymap remains the source of truth and no
# duplicate category field needs to be maintained in configuration files.
MENU_CATEGORY_ITEMS = (
    ("ALL", "All", "Show menus from every category"),
    ("COMMON", "Common Menus", "Menus registered in all six built-in AllPie mode contexts"),
    ("OBJECT", "Object", "Menus registered in Object Mode"),
    ("MESH", "Mesh", "Menus registered in Mesh Edit Mode"),
    ("SCULPT", "Sculpt", "Menus registered in Sculpt Mode"),
    ("IMAGE_PAINT", "Texture Paint", "Menus registered in Image Paint mode"),
    ("VERTEX_PAINT", "Vertex Paint", "Menus registered in Vertex Paint mode"),
    ("WEIGHT_PAINT", "Weight Paint", "Menus registered in Weight Paint mode"),
    ("THIRD_PARTY", "Third Party", "Menus contributed by external addons"),
    ("OTHER", "Other", "Menus using another Blender keymap context"),
)

CATEGORY_TO_KEYMAP = {
    "COMMON": COMMON_KEYMAP,
    "OBJECT": "Object Mode",
    "MESH": "Mesh",
    "SCULPT": "Sculpt",
    "IMAGE_PAINT": "Image Paint",
    "VERTEX_PAINT": "Vertex Paint",
    "WEIGHT_PAINT": "Weight Paint",
}

# Stable RNA identifiers are separate from Blender's displayed keymap names.
# These are the six contexts used by AllPie's built-in menus and browser.
KEYMAP_ENUM_ITEMS = (
    ("COMMON", "Common (All Modes)", "Register this menu in Object Mode, Mesh, Sculpt, Image Paint, Vertex Paint and Weight Paint"),
    ("OBJECT_MODE", "Object Mode", "Register this menu in Object Mode"),
    ("MESH", "Mesh", "Register this menu in Mesh Edit Mode"),
    ("SCULPT", "Sculpt", "Register this menu in Sculpt Mode"),
    ("IMAGE_PAINT", "Texture Paint", "Register this menu in Texture Paint mode"),
    ("VERTEX_PAINT", "Vertex Paint", "Register this menu in Vertex Paint mode"),
    ("WEIGHT_PAINT", "Weight Paint", "Register this menu in Weight Paint mode"),
    ("CUSTOM", "Custom Keymap…", "Preserve a custom Blender keymap context name"),
)

KEYMAP_IDENTIFIER_TO_VALUE = {
    "COMMON": COMMON_KEYMAP,
    "OBJECT_MODE": "Object Mode",
    "MESH": "Mesh",
    "SCULPT": "Sculpt",
    "IMAGE_PAINT": "Image Paint",
    "VERTEX_PAINT": "Vertex Paint",
    "WEIGHT_PAINT": "Weight Paint",
}

KEYMAP_VALUE_TO_IDENTIFIER = {
    value.casefold(): identifier
    for identifier, value in KEYMAP_IDENTIFIER_TO_VALUE.items()
}


def keymap_identifier(keymap: str) -> str:
    """Convert a stored menu scope without discarding custom contexts."""
    return KEYMAP_VALUE_TO_IDENTIFIER.get(
        str(keymap or "").strip().casefold(), "CUSTOM"
    )


def keymap_value(identifier: str, custom_value: str = "") -> str:
    """Resolve the selected keymap enum, preserving a custom keymap name."""
    identifier = str(identifier or "OBJECT_MODE")
    if identifier == "CUSTOM":
        return str(custom_value or "").strip()
    return KEYMAP_IDENTIFIER_TO_VALUE.get(identifier, "Object Mode")


def supports_brush_menu(keymap: str) -> bool:
    """Return whether a menu context supports Brush Menu actions."""
    value = str(keymap or "").strip()
    supported_names = {name.casefold() for name in BRUSH_MENU_KEYMAPS}
    supported_ids = {
        "SCULPT",
        "IMAGE_PAINT",
        "VERTEX_PAINT",
        "WEIGHT_PAINT",
    }
    return value.casefold() in supported_names or value.upper() in supported_ids


KEYMAP_TO_CATEGORY = {
    keymap.casefold(): category
    for category, keymap in CATEGORY_TO_KEYMAP.items()
}
CATEGORY_LABELS = {
    identifier: label
    for identifier, label, _description in MENU_CATEGORY_ITEMS
}


def split_menu_id(menu_id: str) -> Tuple[Optional[str], str]:
    """Split a runtime menu ID into (addon_id, local_id)."""
    if ":" in menu_id:
        addon_id, local_id = menu_id.split(":", 1)
        return addon_id, local_id
    return None, menu_id


def get_menu_container(config: Dict[str, Any], menu_id: str) -> Tuple[Dict[str, Any], str]:
    """Return the menu mapping and local key for a global or third-party ID."""
    addon_id, local_id = split_menu_id(menu_id)
    if addon_id is None:
        return config["Menus"], local_id
    addon = config["ThirdParty"].get(addon_id)
    if addon is None:
        raise KeyError(f"Third-party addon '{addon_id}' does not exist")
    return addon["Menus"], local_id


def get_menu(config: Dict[str, Any], menu_id: str) -> Dict[str, Any]:
    container, local_id = get_menu_container(config, menu_id)
    try:
        return container[local_id]
    except KeyError as error:
        raise KeyError(f"Menu '{menu_id}' does not exist") from error


def category_for_record(record: Mapping[str, Any]) -> str:
    """Return the primary browser category for one normalized menu record."""
    keymap = str(record.get("keymap", "")).strip().casefold()
    if keymap == COMMON_KEYMAP.casefold():
        return "COMMON"
    if record.get("owner_addon"):
        return "THIRD_PARTY"
    return KEYMAP_TO_CATEGORY.get(keymap, "OTHER")


def filter_menu_records(
    records: Iterable[Mapping[str, Any]],
    category: str,
) -> List[Dict[str, Any]]:
    """Filter menu records by keymap-derived browser category."""
    category = str(category or "ALL").upper()
    records = list(records)
    if category == "ALL":
        return [dict(record) for record in records]
    if category == "THIRD_PARTY":
        # Third-party ownership remains independently filterable, even when a
        # contributed menu also uses the Common registration scope.
        return [dict(record) for record in records if record.get("owner_addon")]
    return [
        dict(record)
        for record in records
        if category_for_record(record) == category
    ]


def category_for_menu(config: Mapping[str, Any], menu_id: str) -> str:
    """Find the browser category of a menu by its stable ID."""
    for record in iter_menu_records(config):
        if record["menu_id"] == menu_id:
            return category_for_record(record)
    raise KeyError(f"Menu '{menu_id}' does not exist")


def category_label(category: str) -> str:
    """Return the display label for a browser category identifier."""
    return CATEGORY_LABELS.get(str(category).upper(), "All")


def keymap_label(keymap: str) -> str:
    """Return a compact list label for a stored menu registration scope."""
    if str(keymap or "").strip().casefold() == COMMON_KEYMAP.casefold():
        return "Common"
    return str(keymap or "")


def iter_menu_records(config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return sorted UI records for built-in and third-party menus."""
    records: List[Dict[str, Any]] = []
    for menu_id, menu in config.get("Menus", {}).items():
        records.append({
            "menu_id": menu_id,
            "name": menu.get("name", menu_id),
            "key": menu.get("key", ""),
            "keymap": menu.get("keymap", ""),
            "enabled": bool(menu.get("enabled", True)),
            "owner_addon": "",
        })

    for addon_id, addon in config.get("ThirdParty", {}).items():
        addon_name = addon.get("name", addon_id)
        for local_id, menu in addon.get("Menus", {}).items():
            records.append({
                "menu_id": f"{addon_id}:{local_id}",
                "name": menu.get("name", local_id),
                "key": menu.get("key", ""),
                "keymap": menu.get("keymap", ""),
                "enabled": bool(menu.get("enabled", True) and addon.get("enabled", True)),
                "owner_addon": addon_name,
            })

    records.sort(key=lambda item: (item["owner_addon"].casefold(), item["name"].casefold(), item["menu_id"]))
    return records


def iter_action_records(
    config: Mapping[str, Any],
    keymap: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """Return reusable action records, optionally limited to one keymap context.

    With no ``keymap``, all presets are returned. When a keymap is supplied,
    presets are scoped to menus registered in that context. The Common scope
    uses the union of all six supported built-in contexts. The scope is inferred
    from normal and spaced slot
    assignments, so the JSON schema does not need duplicated category tags on
    every operator preset.

    A preset referenced by menus in multiple contexts is intentionally
    available in each of those contexts. Both regular and spaced slots count.
    Third-party references are resolved using the same local-namespace
    precedence as the runtime registry.
    """
    records: Dict[str, Tuple[str, str, str]] = {}
    for action_id, action in config.get("Operators", {}).items():
        records[action_id] = (
            action_id,
            action.get("name", action_id),
            action.get("operator_id", ""),
        )

    third_party = config.get("ThirdParty", {})
    for addon_id, addon in third_party.items():
        for action_id, action in addon.get("Operators", {}).items():
            qualified_id = f"{addon_id}:{action_id}"
            records[qualified_id] = (
                qualified_id,
                action.get("name", action_id),
                action.get("operator_id", ""),
            )

    if keymap is not None:
        target_keymaps = {name.casefold() for name in keymap_contexts(keymap)}
        allowed_references = set()

        # Explicit action contexts form a discoverable catalog in addition to
        # actions already assigned to slots. A Common menu sees the union of
        # the six supported mode catalogs, because one menu can be opened in
        # any of those contexts.
        def collect_context_catalog(actions: Mapping[str, Any], namespace: Optional[str]) -> None:
            for action_id, action in actions.items():
                contexts = action.get("contexts", ()) if isinstance(action, Mapping) else ()
                if isinstance(contexts, (list, tuple)) and any(
                    isinstance(context_name, str)
                    and context_name.strip().casefold() in target_keymaps
                    for context_name in contexts
                ):
                    allowed_references.add(f"{namespace}:{action_id}" if namespace else action_id)

        collect_context_catalog(config.get("Operators", {}), None)
        for catalog_addon_id, catalog_addon in third_party.items():
            collect_context_catalog(catalog_addon.get("Operators", {}), catalog_addon_id)

        def collect_menu_references(menu: Mapping[str, Any], owner_addon: Optional[str]) -> None:
            menu_contexts = {name.casefold() for name in keymap_contexts(menu.get("keymap", ""))}
            if not menu_contexts.intersection(target_keymaps):
                return

            for slot_field in ("slots", "spaced_slots"):
                for reference in menu.get(slot_field, {}).values():
                    if not isinstance(reference, str) or not reference:
                        continue

                    if ":" in reference:
                        resolved_reference = reference
                    elif owner_addon and f"{owner_addon}:{reference}" in records:
                        resolved_reference = f"{owner_addon}:{reference}"
                    else:
                        resolved_reference = reference

                    if resolved_reference in records:
                        allowed_references.add(resolved_reference)

        for menu in config.get("Menus", {}).values():
            collect_menu_references(menu, None)

        for addon_id, addon in third_party.items():
            for menu in addon.get("Menus", {}).values():
                collect_menu_references(menu, addon_id)

        records = {
            identifier: record
            for identifier, record in records.items()
            if identifier in allowed_references
        }

    result = list(records.values())
    result.sort(key=lambda item: (item[1].casefold(), item[0]))
    return result



def get_action_metadata(config: Mapping[str, Any]) -> Dict[str, Dict[str, str]]:
    """Return picker-facing names and descriptions for global/third-party presets."""
    metadata: Dict[str, Dict[str, str]] = {}
    for action_id, action in config.get("Operators", {}).items():
        metadata[action_id] = {
            "search_name": str(action.get("search_name") or action.get("name") or action_id),
            "description": str(action.get("description") or ""),
            "operator_id": str(action.get("operator_id") or ""),
        }

    for addon_id, addon in config.get("ThirdParty", {}).items():
        for action_id, action in addon.get("Operators", {}).items():
            qualified_id = f"{addon_id}:{action_id}"
            metadata[qualified_id] = {
                "search_name": str(action.get("search_name") or action.get("name") or action_id),
                "description": str(action.get("description") or ""),
                "operator_id": str(action.get("operator_id") or ""),
            }
    return metadata

def _make_unique_id(container: Mapping[str, Any], base_id: str) -> str:
    candidate = base_id
    suffix = 1
    while candidate in container:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    return candidate


def add_menu(
    config: Dict[str, Any],
    *,
    menu_id: str,
    name: str,
    key: str = "A",
    keymap: str = "Object Mode",
    is_brush_menu: bool = False,
) -> str:
    """Add a disabled blank built-in menu and return its stable ID."""
    menu_id = menu_id.strip()
    if not menu_id:
        raise ValueError("Menu ID cannot be empty")
    if menu_id in config["Menus"]:
        raise ValueError(f"Menu ID '{menu_id}' already exists")
    config["Menus"][menu_id] = {
        "name": name.strip() or menu_id,
        "key": key,
        "keymodifiers": [],
        "keymap": keymap,
        "enabled": False,
        "is_brush_menu": bool(is_brush_menu and supports_brush_menu(keymap)),
        "slots": {},
        "spaced_slots": {},
    }
    return menu_id


def duplicate_menu(config: Dict[str, Any], menu_id: str) -> str:
    """Duplicate a menu in its current namespace, disabled to avoid key conflicts."""
    container, local_id = get_menu_container(config, menu_id)
    source = get_menu(config, menu_id)
    new_local_id = _make_unique_id(container, f"{local_id}_COPY")
    duplicate = deepcopy(source)
    duplicate["name"] = f"{source.get('name', local_id)} Copy"
    duplicate["enabled"] = False
    container[new_local_id] = duplicate
    addon_id, _ = split_menu_id(menu_id)
    return f"{addon_id}:{new_local_id}" if addon_id else new_local_id


def remove_menu(config: Dict[str, Any], menu_id: str) -> Dict[str, Any]:
    """Remove a menu and return the removed definition."""
    container, local_id = get_menu_container(config, menu_id)
    try:
        return container.pop(local_id)
    except KeyError as error:
        raise KeyError(f"Menu '{menu_id}' does not exist") from error


def update_menu(
    config: Dict[str, Any],
    menu_id: str,
    *,
    name: str,
    key: str,
    keymap: str,
    modifiers: Iterable[str],
    enabled: bool,
    slots: Mapping[int, Optional[str]],
    spaced_enabled: bool,
    spaced_slots: Mapping[int, Optional[str]],
    is_brush_menu: bool = False,
) -> None:
    """Write editor values into a mutable v1 config without touching operators."""
    menu = get_menu(config, menu_id)
    menu["name"] = name.strip()
    menu["key"] = key
    menu["keymap"] = keymap.strip()
    enabled_modifiers = set(modifiers)
    menu["keymodifiers"] = [
        name for name in ("SHIFT", "CTRL", "ALT", "OSKEY", "HYPER")
        if name in enabled_modifiers
    ]
    menu["enabled"] = bool(enabled)
    menu["is_brush_menu"] = bool(is_brush_menu and supports_brush_menu(keymap))

    normal = {
        str(slot): action_id
        for slot, action_id in slots.items()
        if action_id not in (None, "", "__EMPTY__")
    }
    menu["slots"] = normal

    if spaced_enabled:
        menu["spaced_slots"] = {
            str(slot): action_id
            for slot, action_id in spaced_slots.items()
            if action_id not in (None, "", "__EMPTY__")
        }
    else:
        menu.pop("spaced_slots", None)
