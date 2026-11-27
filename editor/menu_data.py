"""Blender-independent operations used by the AllPie menu editor."""

from __future__ import annotations

ACTION_CONTEXT_CATALOG_API_VERSION = 16

from copy import deepcopy
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.schema import COMMON_KEYMAP, keymap_contexts


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
    ("UV_EDITOR", "UV Editor", "Menus registered in Blender's UV Editor"),
    ("IMAGE_EDITOR", "Image Editor", "Menus registered in Blender's Image Editor"),
    ("NODE_EDITOR", "Node Editor", "Menus registered in Shader, Geometry Nodes, Compositor and Texture Node editors"),
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
    "UV_EDITOR": "UV Editor",
    "IMAGE_EDITOR": "Image",
    "NODE_EDITOR": "Node Editor",
}

# Stable RNA identifiers are separate from Blender's displayed keymap names
# and stored Blender keymap names. The legacy mode identifiers are preserved;
# editor contexts use their own identifiers and exact Blender keymap names.
KEYMAP_ENUM_ITEMS = (
    ("COMMON", "Common (All Modes)", "Register this menu in Object Mode, Mesh, Sculpt, Image Paint, Vertex Paint and Weight Paint"),
    ("OBJECT_MODE", "Object Mode", "Register this menu in Object Mode"),
    ("MESH", "Mesh", "Register this menu in Mesh Edit Mode"),
    ("SCULPT", "Sculpt", "Register this menu in Sculpt Mode"),
    ("IMAGE_PAINT", "Texture Paint", "Register this menu in Texture Paint mode"),
    ("VERTEX_PAINT", "Vertex Paint", "Register this menu in Vertex Paint mode"),
    ("WEIGHT_PAINT", "Weight Paint", "Register this menu in Weight Paint mode"),
    ("UV_EDITOR", "UV Editor", "Register this menu in the UV Editor"),
    ("IMAGE_EDITOR", "Image Editor", "Register this menu in the Image Editor"),
    ("NODE_EDITOR", "Node Editor", "Register this menu in Shader, Geometry Nodes, Compositor and Texture Nodes"),
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
    "UV_EDITOR": "UV Editor",
    "IMAGE_EDITOR": "Image",
    "NODE_EDITOR": "Node Editor",
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


KEYMAP_TO_CATEGORY = {
    keymap.casefold(): category
    for category, keymap in CATEGORY_TO_KEYMAP.items()
}
CATEGORY_LABELS = {
    identifier: label
    for identifier, label, _description in MENU_CATEGORY_ITEMS
}


def spaced_slots_enabled(menu: Mapping[str, Any]) -> bool:
    """Return the explicit Spaced Slots state, with a legacy-data fallback."""
    enabled = menu.get("spaced_slots_enabled")
    if isinstance(enabled, bool):
        return enabled
    slots = menu.get("spaced_slots", {})
    return (
        isinstance(slots, Mapping)
        and any(reference is not None for reference in slots.values())
    )


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
            "keymodifiers": tuple(menu.get("keymodifiers", ())),
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
                "keymodifiers": tuple(menu.get("keymodifiers", ())),
                "keymap": menu.get("keymap", ""),
                "enabled": bool(menu.get("enabled", True) and addon.get("enabled", True)),
                "owner_addon": addon_name,
            })

    records.sort(key=lambda item: (item["owner_addon"].casefold(), item["name"].casefold(), item["menu_id"]))
    return records


def iter_enabled_menus_for_context(
    config: Mapping[str, Any],
    context_name: str = "",
) -> List[Dict[str, Any]]:
    """Return shortcut-enabled menus registered in one Blender context.

    ``Common`` menus are expanded through :func:`keymap_contexts`, so they
    appear in each supported built-in mode. When the current editor/mode
    cannot be identified, all enabled menus with a real shortcut are returned
    rather than silently hiding valid destinations.
    """
    target_context = str(context_name or "").strip().casefold()
    records = []
    for record in iter_menu_records(config):
        if not record.get("enabled", False):
            continue
        key = str(record.get("key", "") or "").strip().upper()
        if not key or key == "NONE":
            continue
        registered_contexts = keymap_contexts(str(record.get("keymap", "")))
        if target_context and target_context not in {value.casefold() for value in registered_contexts}:
            continue
        item = dict(record)
        item["registered_contexts"] = list(registered_contexts)
        records.append(item)
    return records


def iter_action_records(
    config: Mapping[str, Any],
    keymap: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """Return presets keyed by permanent UUID, optionally scoped to a context."""
    records: Dict[str, Tuple[str, str, str]] = {}
    for _legacy_id, action in config.get("Operators", {}).items():
        preset_id = str(action.get("preset_id", ""))
        if preset_id:
            records[preset_id] = (
                preset_id,
                action.get("name", preset_id),
                action.get("operator_id", ""),
            )

    third_party = config.get("ThirdParty", {})
    for addon in third_party.values():
        for _legacy_id, action in addon.get("Operators", {}).items():
            preset_id = str(action.get("preset_id", ""))
            if preset_id:
                records[preset_id] = (
                    preset_id,
                    action.get("name", preset_id),
                    action.get("operator_id", ""),
                )

    if keymap is not None:
        target_keymaps = {name.casefold() for name in keymap_contexts(keymap)}
        allowed_references = set()

        # Explicit tags make a reusable preset discoverable even before it is
        # assigned. Slot references are already canonical permanent IDs.
        for _legacy_id, action in config.get("Operators", {}).items():
            preset_id = str(action.get("preset_id", ""))
            contexts = action.get("contexts", ()) if isinstance(action, Mapping) else ()
            if preset_id and isinstance(contexts, (list, tuple)) and any(
                isinstance(context_name, str)
                and context_name.strip().casefold() in target_keymaps
                for context_name in contexts
            ):
                allowed_references.add(preset_id)

        for addon in third_party.values():
            for _legacy_id, action in addon.get("Operators", {}).items():
                preset_id = str(action.get("preset_id", ""))
                contexts = action.get("contexts", ()) if isinstance(action, Mapping) else ()
                if preset_id and isinstance(contexts, (list, tuple)) and any(
                    isinstance(context_name, str)
                    and context_name.strip().casefold() in target_keymaps
                    for context_name in contexts
                ):
                    allowed_references.add(preset_id)

        def collect_menu_references(menu: Mapping[str, Any]) -> None:
            menu_contexts = {name.casefold() for name in keymap_contexts(menu.get("keymap", ""))}
            if not menu_contexts.intersection(target_keymaps):
                return
            for slot_field in ("slots", "spaced_slots"):
                for reference in menu.get(slot_field, {}).values():
                    if isinstance(reference, str) and reference in records:
                        allowed_references.add(reference)

        for menu in config.get("Menus", {}).values():
            collect_menu_references(menu)
        for addon in third_party.values():
            for menu in addon.get("Menus", {}).values():
                collect_menu_references(menu)

        records = {
            preset_id: record
            for preset_id, record in records.items()
            if preset_id in allowed_references
        }

    result = list(records.values())
    result.sort(key=lambda item: (item[1].casefold(), item[0]))
    return result


def get_action_metadata(config: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return preset metadata keyed by permanent ID; name is canonical display text."""
    metadata: Dict[str, Dict[str, Any]] = {}
    for _legacy_id, action in config.get("Operators", {}).items():
        preset_id = str(action.get("preset_id", ""))
        if not preset_id:
            continue
        metadata[preset_id] = {
            "name": str(action.get("name") or preset_id),
            "search_name": str(action.get("search_name") or action.get("name") or preset_id),
            "description": str(action.get("description") or ""),
            "operator_id": str(action.get("operator_id") or ""),
            "enum_value": int(action.get("enum_value", 0)),
        }

    for addon in config.get("ThirdParty", {}).values():
        for _legacy_id, action in addon.get("Operators", {}).items():
            preset_id = str(action.get("preset_id", ""))
            if not preset_id:
                continue
            metadata[preset_id] = {
                "name": str(action.get("name") or preset_id),
                "search_name": str(action.get("search_name") or action.get("name") or preset_id),
                "description": str(action.get("description") or ""),
                "operator_id": str(action.get("operator_id") or ""),
                "enum_value": int(action.get("enum_value", 0)),
            }
    return metadata


def _make_unique_id(container: Mapping[str, Any], base_id: str) -> str:
    candidate = base_id
    suffix = 1
    while candidate in container:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    return candidate


def generate_menu_id(config: Mapping[str, Any], name: str) -> str:
    """Generate a valid, unique stable ID from a user-facing menu name.

    IDs are generated only when a menu is created. Renaming an existing menu
    never changes its ID or breaks references to that menu.
    """
    raw_name = unicodedata.normalize("NFKD", str(name or ""))
    ascii_name = raw_name.encode("ascii", "ignore").decode("ascii")
    token = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_").upper()
    if not token:
        token = "MENU"
    if not token[0].isalpha():
        token = f"MENU_{token}"

    menus = config.get("Menus", {})
    base_id = f"CUSTOM.{token}"
    candidate = base_id
    suffix = 2
    while candidate in menus:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    return candidate


def add_menu(
    config: Dict[str, Any],
    *,
    name: str,
    menu_id: Optional[str] = None,
    key: str = "A",
    keymap: str = "Object Mode",
) -> str:
    """Add a disabled blank built-in menu and return its stable ID.

    Callers normally omit ``menu_id`` so the ID is generated from the menu
    name. The optional argument remains for import/compatibility callers that
    need to preserve an already established ID.
    """
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Menu name cannot be empty")
    menu_id = str(menu_id or "").strip() or generate_menu_id(config, clean_name)
    if menu_id in config["Menus"]:
        raise ValueError(f"Menu ID '{menu_id}' already exists")
    config["Menus"][menu_id] = {
        "name": clean_name,
        "key": key,
        "keymodifiers": [],
        "keymap": keymap,
        "enabled": False,
        "slots": {},
        "spaced_slots": {},
        "spaced_slots_enabled": False,
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
    duplicate.pop("is_brush_menu", None)
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
    menu.pop("is_brush_menu", None)
    menu["spaced_slots_enabled"] = bool(spaced_enabled)

    normal = {
        str(slot): action_id
        for slot, action_id in slots.items()
        if action_id not in (None, "", "__EMPTY__")
    }
    menu["slots"] = normal

    # Legacy per-slot label maps are no longer part of the menu model.
    menu.pop("slot_labels", None)
    menu.pop("spaced_slot_labels", None)

    if spaced_enabled:
        menu["spaced_slots"] = {
            str(slot): action_id
            for slot, action_id in spaced_slots.items()
            if action_id not in (None, "", "__EMPTY__")
        }
    else:
        menu.pop("spaced_slots", None)
