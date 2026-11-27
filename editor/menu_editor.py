"""Blender-native menu browser and editor for AllPie.

The editor works on a detached JSON-style configuration copy. Applying changes
validates and compiles a replacement registry, then refreshes keymaps. The
radial modal interaction and drawing implementation are not modified here.
"""

from __future__ import annotations

from itertools import count
from typing import Any, Dict, Iterable, List, Optional, Tuple

import bpy
import json
import re
from pathlib import Path
from bpy.types import Operator, PropertyGroup, UIList
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)

from ..core import runtime as ConfigRuntime
from ..core.validation import reserved_menu_shortcut_message, validate_config
from . import menu_data, menu_exchange, operator_data

MENU_EDITOR_API_VERSION = 36

_EMPTY_ACTION = "__EMPTY__"
_ALL_ACTION_ENUM_ITEMS: Tuple[Tuple[Any, ...], ...] = (
    (_EMPTY_ACTION, "(Empty)", "Leave this radial slot empty", 0),
)
_ACTION_ENUM_ITEMS: Tuple[Tuple[Any, ...], ...] = (
    (_EMPTY_ACTION, "(Empty)", "Leave this radial slot empty", 0),
)
_ACTION_ALLOWED_TOKENS = {_EMPTY_ACTION}
_ACTION_REFERENCE_TO_TOKEN: Dict[str, str] = {}
_ACTION_TOKEN_TO_REFERENCE: Dict[str, str] = {}
_ACTION_TOKEN_TO_LABEL: Dict[str, str] = {}
_SHORTCUT_CAPTURE_KEYMAP_NAME = "AllPie Shortcut Capture (Internal)"
_SHORTCUT_CAPTURE_ITEMS: Dict[str, Tuple[Any, Any]] = {}
_SHORTCUT_CAPTURE_COUNTER = count(1)


def _capture_keymap(context: Any) -> Any:
    """Return AllPie's private keymap used only as a Blender event-field proxy."""
    keyconfigs = context.window_manager.keyconfigs
    keyconfig = keyconfigs.addon
    if keyconfig is None:
        raise RuntimeError("Blender's add-on key configuration is unavailable")

    keymap = keyconfig.keymaps.get(_SHORTCUT_CAPTURE_KEYMAP_NAME)
    if keymap is None:
        keymap = keyconfig.keymaps.new(
            name=_SHORTCUT_CAPTURE_KEYMAP_NAME,
            space_type="EMPTY",
        )
    elif not _SHORTCUT_CAPTURE_ITEMS:
        # Clean up proxy items left behind by an interrupted script reload.
        for item in list(keymap.keymap_items):
            keymap.keymap_items.remove(item)
    return keymap


def _remove_shortcut_capture_item(token: str) -> None:
    record = _SHORTCUT_CAPTURE_ITEMS.pop(token, None)
    if record is None:
        return

    keymap, item = record
    try:
        keymap.keymap_items.remove(item)
    except (ReferenceError, RuntimeError, ValueError):
        pass

    try:
        if len(keymap.keymap_items) == 0:
            keyconfig = bpy.context.window_manager.keyconfigs.addon
            if keyconfig is not None:
                keyconfig.keymaps.remove(keymap)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass


def clear_shortcut_capture_items() -> None:
    """Remove temporary shortcut proxies, including stale reload leftovers."""
    for token in tuple(_SHORTCUT_CAPTURE_ITEMS):
        _remove_shortcut_capture_item(token)

    # The module may have been reloaded while a capture dialog was open, which
    # resets the Python token map but leaves the add-on KeyMap alive in Blender.
    try:
        keyconfig = bpy.context.window_manager.keyconfigs.addon
        keymap = keyconfig.keymaps.get(_SHORTCUT_CAPTURE_KEYMAP_NAME) if keyconfig else None
        if keymap is not None:
            for item in tuple(keymap.keymap_items):
                keymap.keymap_items.remove(item)
            keyconfig.keymaps.remove(keymap)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pass


def _create_shortcut_capture_item(
    context: Any,
    key: str,
    modifiers: Iterable[str],
) -> str:
    """Create an inactive KeyMapItem for Blender's native full-event widget."""
    modifier_set = set(modifiers)
    keymap = _capture_keymap(context)
    kwargs = {
        "shift": "SHIFT" in modifier_set,
        "ctrl": "CTRL" in modifier_set,
        "alt": "ALT" in modifier_set,
        "oskey": "OSKEY" in modifier_set,
        "hyper": "HYPER" in modifier_set,
    }
    item = keymap.keymap_items.new(
        "wm.call_menu",
        key or "A",
        "PRESS",
        **kwargs,
    )
    # The proxy exists solely for the Preferences UI. It must never activate.
    item.active = False
    token = str(next(_SHORTCUT_CAPTURE_COUNTER))
    _SHORTCUT_CAPTURE_ITEMS[token] = (keymap, item)
    return token


def _shortcut_modifier_values(item: Any) -> Dict[str, bool]:
    """Read the UI-facing modifier states from a KeyMapItem proxy."""
    result: Dict[str, bool] = {}
    for name in ("shift", "ctrl", "alt", "oskey", "hyper"):
        ui_name = f"{name}_ui"
        value = getattr(item, ui_name, None)
        if value is None:
            value = getattr(item, name, False)
        result[name.upper()] = bool(value)
    return result


def _format_shortcut(key: str, modifiers: Iterable[str]) -> str:
    """Format a compact, readable shortcut label for the editor button."""
    labels = {
        "NONE": "Unassigned",
        "LEFTMOUSE": "LMB",
        "RIGHTMOUSE": "RMB",
        "MIDDLEMOUSE": "MMB",
        "BUTTON4MOUSE": "Mouse 4",
        "BUTTON5MOUSE": "Mouse 5",
        "RET": "Enter",
        "NUMPAD_ENTER": "Numpad Enter",
        "SPACE": "Space",
        "ESC": "Esc",
        "TAB": "Tab",
        "BACK_SPACE": "Backspace",
        "DEL": "Delete",
        "LEFT_ARROW": "Left",
        "RIGHT_ARROW": "Right",
        "UP_ARROW": "Up",
        "DOWN_ARROW": "Down",
    }
    ordered = ("CTRL", "SHIFT", "ALT", "OSKEY", "HYPER")
    modifier_set = set(modifiers)
    parts = [name.title() for name in ordered if name in modifier_set]
    parts.append(labels.get(key, key.replace("_", " ").title()))
    return " + ".join(parts)


def action_enum_items(_self: Any, _context: Any) -> Tuple[Tuple[Any, ...], ...]:
    """Return actions scoped to the keymap context of the active menu picker."""
    return _ACTION_ENUM_ITEMS


def all_action_enum_items(_self: Any, _context: Any) -> Tuple[Tuple[Any, ...], ...]:
    """Return all presets for persistent slot-value storage in RNA."""
    return _ALL_ACTION_ENUM_ITEMS



def _operator_rna_description(operator_id: str) -> str:
    """Use a third-party or Blender operator's own RNA description as fallback."""
    if not operator_id or "." not in operator_id:
        return ""
    module_name, operator_name = operator_id.split(".", 1)
    try:
        operator = getattr(getattr(bpy.ops, module_name), operator_name)
        rna = operator.get_rna_type()
        return str(getattr(rna, "description", "") or "").strip()
    except Exception:
        return ""

def _refresh_action_enum_items(
    config: Dict[str, Any],
    keymap: str | None = None,
) -> None:
    """Refresh stable action tokens and the current menu's scoped search list.

    Tokens and label/reference maps are built from the complete registry so
    existing assignments remain readable and serializable even while a user
    changes a menu's keymap in an unapplied draft. Only the search popup's enum
    list is filtered to actions used by menus in ``keymap``.
    """
    global _ALL_ACTION_ENUM_ITEMS, _ACTION_ENUM_ITEMS
    global _ACTION_REFERENCE_TO_TOKEN, _ACTION_TOKEN_TO_REFERENCE, _ACTION_TOKEN_TO_LABEL
    global _ACTION_ALLOWED_TOKENS

    action_metadata = menu_data.get_action_metadata(config)
    all_records = sorted(
        menu_data.iter_action_records(config),
        key=lambda record: (
            action_metadata.get(record[0], {}).get("name", record[1]).casefold(),
            record[0],
        ),
    )
    all_items: List[Tuple[Any, ...]] = [
        (_EMPTY_ACTION, "(Empty)", "Leave this radial slot empty", 0)
    ]
    reference_to_token: Dict[str, str] = {}
    token_to_reference: Dict[str, str] = {}
    token_to_label: Dict[str, str] = {}
    token_items: Dict[str, Tuple[Any, ...]] = {}

    for identifier, name, operator_id in all_records:
        # The enum identifier is the preset's permanent UUID. Never derive it
        # from sort order: inserting or renaming another preset cannot change
        # the identity held by an existing Main or Spaced slot.
        token = identifier
        reference_to_token[identifier] = token
        token_to_reference[token] = identifier
        metadata = action_metadata.get(identifier, {})
        label = metadata.get("name") or name or identifier
        if isinstance(label, str) and label.isupper():
            label = label.title()
        description = metadata.get("description") or _operator_rna_description(operator_id)
        if not description:
            description = "This preset runs the associated Blender operator with the properties shown in its preset definition."
        # Blender displays this enum description as the hover tooltip in the
        # search popup. Keep it focused on what the action does; internal IDs
        # and Blender operator identifiers stay out of the user-facing text.
        tooltip = description
        enum_value = int(metadata.get("enum_value", 0))
        if enum_value <= 0:
            raise RuntimeError(f"Preset '{identifier}' has no stable Blender enum value")
        token_item = (token, label, tooltip, enum_value)
        all_items.append(token_item)
        token_items[identifier] = token_item
        token_to_label[token] = label

    if keymap is None:
        scoped_records = all_records
    else:
        scoped_records = menu_data.iter_action_records(config, keymap=keymap)

    scoped_references = {identifier for identifier, _name, _operator_id in scoped_records}

    scoped_items = [
        (_EMPTY_ACTION, "(Empty)", "Leave this radial slot empty", 0)
    ]
    for identifier, _name, _operator_id in all_records:
        if identifier in scoped_references:
            scoped_items.append(token_items[identifier])

    # Keep generated strings alive globally; Blender's dynamic EnumProperty
    # callbacks require their item strings to remain referenced.
    _ALL_ACTION_ENUM_ITEMS = tuple(all_items)
    _ACTION_ENUM_ITEMS = tuple(scoped_items)
    _ACTION_REFERENCE_TO_TOKEN = reference_to_token
    _ACTION_TOKEN_TO_REFERENCE = token_to_reference
    _ACTION_TOKEN_TO_LABEL = token_to_label
    _ACTION_ALLOWED_TOKENS = {
        _EMPTY_ACTION,
        *(reference_to_token[identifier] for identifier in scoped_references if identifier in reference_to_token),
    }


def _preferences_from_context(context: Any) -> Any:
    from .. import Preferences

    addon = context.preferences.addons.get(Preferences.__package__)
    return addon.preferences if addon is not None else None


def _serialize_editor_config(config: Dict[str, Any]) -> str:
    """Serialize a detached editor draft without changing the active runtime."""
    return json.dumps(config, ensure_ascii=False, separators=(",", ":"))


def _mark_menu_draft_dirty(prefs: Any) -> None:
    """Start a detached full-config draft on the first edit, then mark it dirty.

    Menu properties and slot collections are transient RNA controls. Operator
    assignment/configuration must be able to update the same detached config
    while those controls remain unapplied. Keeping the base configuration in a
    hidden SKIP_SAVE string lets Apply commit all changes together and Discard
    throw them away without leaving orphan presets behind.
    """
    if prefs is None or getattr(prefs, "editor_loading", False):
        return

    draft_json = str(getattr(prefs, "editor_draft_config_json", "") or "")
    if not draft_json:
        prefs.editor_draft_config_json = _serialize_editor_config(
            ConfigRuntime.get_config_copy()
        )
    else:
        # Detect stale/corrupt transient state before any editor operation
        # mutates it. A malformed draft must never silently overwrite the live
        # configuration with a fresh copy.
        try:
            draft = json.loads(draft_json)
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"The pending menu draft is invalid: {error}") from error
        if not isinstance(draft, dict):
            raise RuntimeError("The pending menu draft is not a configuration object")
    prefs.editor_dirty = True


def get_menu_operation_config(prefs: Any, target_menu_id: str) -> Dict[str, Any]:
    """Return the menu's current draft when editing it, otherwise live config.

    Operators invoked from a slot can work while the menu editor is dirty only
    when they target the menu whose draft is currently open. This avoids
    silently editing a different menu or writing around an unapplied draft.
    """
    if prefs is not None and getattr(prefs, "editor_dirty", False):
        if not target_menu_id or prefs.editor_active_menu_id != target_menu_id:
            raise RuntimeError(
                "Apply or discard the current menu draft before editing another menu"
            )
        return _build_menu_draft_config(prefs)
    return ConfigRuntime.get_config_copy()


def store_menu_operation_draft(
    prefs: Any,
    config: Dict[str, Any],
    *,
    slot_assignment: Optional[Tuple[int, bool, str]] = None,
) -> None:
    """Store an operator/preset edit inside the pending menu draft.

    slot_assignment is (slot_number, spaced, action_id). It synchronizes the
    visible RNA slot row so the next Apply does not overwrite the assignment
    with stale collection values.
    """
    if prefs is None or not getattr(prefs, "editor_active_menu_id", ""):
        raise RuntimeError("No active menu draft is available")

    # Resolve every UI-side dependency before publishing the new draft JSON.
    # If the slot cannot be synchronized, the previous draft remains intact.
    pending_slot = None
    pending_token = ""
    _refresh_action_enum_items(config, None)
    if slot_assignment is not None:
        slot_number, spaced, action_id = slot_assignment
        pending_token = _ACTION_REFERENCE_TO_TOKEN.get(str(action_id or ""))
        if not pending_token:
            raise RuntimeError(f"Could not resolve the newly assigned preset '{action_id}'")
        collection = prefs.editor_spaced_slots if spaced else prefs.editor_slots
        pending_slot = next((item for item in collection if item.slot_number == slot_number), None)
        if pending_slot is None:
            raise RuntimeError(f"Draft Slot {slot_number} is unavailable")

    pending_json = _serialize_editor_config(config)
    if pending_slot is not None:
        previous_action_id = pending_slot.action_id
        prefs.editor_loading = True
        try:
            pending_slot.action_id = pending_token
        except Exception:
            # Keep the transient slot and saved draft coherent if an RNA enum
            # assignment unexpectedly fails.
            try:
                pending_slot.action_id = previous_action_id
            except Exception:
                pass
            raise
        finally:
            prefs.editor_loading = False

    prefs.editor_draft_config_json = pending_json
    prefs.editor_dirty = True
    # A newly-created preset exists only in this draft, so force the unified
    # operator picker to rebuild against the draft on its next open.
    try:
        prefs.operator_search_config_generation = -1
        prefs.operator_search_config_fingerprint = ""
    except (AttributeError, TypeError):
        pass


def mark_editor_dirty(self: Any, context: Any) -> None:
    """Mark the current draft dirty when a preference editor field changes."""
    if getattr(self, "editor_loading", False):
        return
    try:
        _mark_menu_draft_dirty(self)
    except (AttributeError, TypeError):
        prefs = _preferences_from_context(context) if context is not None else None
        if prefs is not None and not getattr(prefs, "editor_loading", False):
            _mark_menu_draft_dirty(prefs)


def mark_slot_dirty(self: Any, context: Any) -> None:
    """Start/mark the owning AddonPreferences draft after a slot edit."""
    prefs = _preferences_from_context(context) if context is not None else None
    if prefs is not None and not getattr(prefs, "editor_loading", False):
        _mark_menu_draft_dirty(prefs)


def _fill_slot_collection(
    collection: Any,
    slot_config: Dict[str, Any],
) -> None:
    collection.clear()
    for slot_number in range(1, 9):
        item = collection.add()
        item.slot_number = slot_number
        action_id = slot_config.get(str(slot_number))
        item.action_id = _ACTION_REFERENCE_TO_TOKEN.get(action_id, _EMPTY_ACTION) if action_id else _EMPTY_ACTION


def load_selected_menu(prefs: Any) -> None:
    """Copy the currently selected config menu into transient RNA editor fields."""
    if getattr(prefs, "editor_loading", False):
        return
    index = prefs.active_menu_index
    if index < 0 or index >= len(prefs.editor_menus):
        prefs.editor_loading = True
        try:
            prefs.editor_active_menu_id = ""
            prefs.editor_menu_name = ""
            prefs.editor_menu_id = ""
            prefs.editor_menu_key = "A"
            prefs.editor_menu_mode = "OBJECT_MODE"
            prefs.editor_custom_keymap = ""
            prefs.editor_menu_enabled = False
            prefs.editor_menu_shift = False
            prefs.editor_menu_ctrl = False
            prefs.editor_menu_alt = False
            prefs.editor_menu_oskey = False
            prefs.editor_menu_hyper = False
            _fill_slot_collection(prefs.editor_slots, {})
            _fill_slot_collection(prefs.editor_spaced_slots, {})
            prefs.editor_spaced_enabled = False
            prefs.editor_config_generation = ConfigRuntime.REGISTRY.generation
            prefs.editor_draft_config_json = ""
            prefs.editor_dirty = False
        finally:
            prefs.editor_loading = False
        return

    menu_id = prefs.editor_menus[index].menu_id
    try:
        config = ConfigRuntime.get_config_copy()
        menu = menu_data.get_menu(config, menu_id)
    except (RuntimeError, KeyError):
        return

    # The compact slot enum remains unfiltered. Context filters live in the
    # unified search popup opened by clicking a slot button.
    _refresh_action_enum_items(config, None)
    prefs.editor_loading = True
    try:
        prefs.editor_active_menu_id = menu_id
        prefs.editor_menu_id = menu_id
        prefs.editor_menu_name = menu.get("name", menu_id)
        prefs.editor_menu_key = menu.get("key", "A")
        prefs.editor_menu_mode = menu_data.keymap_identifier(menu.get("keymap", "Object Mode"))
        prefs.editor_custom_keymap = (
            menu.get("keymap", "") if prefs.editor_menu_mode == "CUSTOM" else ""
        )

        modifiers = set(menu.get("keymodifiers", ()))
        prefs.editor_menu_shift = "SHIFT" in modifiers
        prefs.editor_menu_ctrl = "CTRL" in modifiers
        prefs.editor_menu_alt = "ALT" in modifiers
        prefs.editor_menu_oskey = "OSKEY" in modifiers
        prefs.editor_menu_hyper = "HYPER" in modifiers

        prefs.editor_menu_enabled = bool(menu.get("enabled", True))

        _fill_slot_collection(prefs.editor_slots, menu.get("slots", {}))
        spaced = menu.get("spaced_slots", {})
        prefs.editor_spaced_enabled = menu_data.spaced_slots_enabled(menu)
        _fill_slot_collection(prefs.editor_spaced_slots, spaced)
        prefs.editor_config_generation = ConfigRuntime.REGISTRY.generation
        prefs.editor_draft_config_json = ""
        prefs.editor_dirty = False
    finally:
        prefs.editor_loading = False


def _ensure_editor_state(prefs: Any) -> None:
    """Refresh transient editor rows only when the runtime cache changes.

    This function is called from AddonPreferences.draw(), so its fast path must
    be O(1) and must not deepcopy or serialize the full JSON configuration.
    Registry.generation is incremented whenever the active configuration is
    replaced, while category changes explicitly invalidate the editor state.
    """
    if not ConfigRuntime.INITIALIZED:
        return

    # Do not touch the active config while a draft is open. It is intentionally
    # kept stable until the user applies or discards the draft.
    if prefs.editor_dirty:
        return

    generation = ConfigRuntime.REGISTRY.generation
    if prefs.editor_config_generation == generation:
        return

    # This is now an infrequent operation: startup, category changes, or a
    # successful configuration replacement—not every UI redraw.
    config = ConfigRuntime.get_config_copy()
    previous_id = prefs.editor_active_menu_id
    records = menu_data.filter_menu_records(
        menu_data.iter_menu_records(config), prefs.editor_category
    )
    prefs.editor_loading = True
    try:
        prefs.editor_menus.clear()
        selected_index = 0
        for index, record in enumerate(records):
            item = prefs.editor_menus.add()
            item.menu_id = record["menu_id"]
            item.name = record["name"]
            item.key = record["key"]
            item.shortcut = (
                "—"
                if record["key"] in {"", "NONE"}
                else _format_shortcut(record["key"], record.get("keymodifiers", ()))
            )
            item.keymap = record["keymap"]
            item.owner_addon = record["owner_addon"]
            item.enabled = record["enabled"]
            if record["menu_id"] == previous_id:
                selected_index = index

        prefs.active_menu_index = min(selected_index, max(0, len(records) - 1))
        prefs.editor_config_generation = generation
        # Retained as a hidden compatibility field for preferences saved by
        # earlier builds. It is no longer computed during drawing.
        prefs.editor_config_signature = ""
    finally:
        prefs.editor_loading = False

    load_selected_menu(prefs)


def on_active_menu_changed(self: Any, context: Any) -> None:
    if not getattr(self, "editor_loading", False) and not getattr(self, "editor_dirty", False):
        load_selected_menu(self)


def on_category_changed(self: Any, context: Any) -> None:
    """Rebuild the visible menu list when the browser category changes."""
    if getattr(self, "editor_loading", False) or getattr(self, "editor_dirty", False):
        return
    self.editor_config_generation = -1
    _ensure_editor_state(self)


class AllPieMenuListItem(PropertyGroup):
    menu_id: StringProperty()
    name: StringProperty()
    key: StringProperty()
    shortcut: StringProperty()
    keymap: StringProperty()
    owner_addon: StringProperty()
    enabled: BoolProperty(default=True)
    export_selected: BoolProperty(
        name="Include in Export",
        description="Include this menu in the next JSON export",
        default=False,
        options={"SKIP_SAVE"},
    )


class AllPieMenuSlotItem(PropertyGroup):
    slot_number: IntProperty(min=1, max=8)
    # Keep all tokens valid in stored editor slots. The picker operator uses
    # the separately scoped action_enum_items callback for search results.
    action_id: EnumProperty(name="Action", items=all_action_enum_items, update=mark_slot_dirty)


class ALLPIE_UL_menu_list(UIList):
    """Searchable menu list showing menu name, key and context."""

    def draw_filter(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="", icon="VIEWZOOM")

    def filter_items(self, context, data, property_name):
        items = getattr(data, property_name)
        flags = []
        needle = self.filter_name.casefold().strip()
        for item in items:
            searchable = f"{item.name} {item.menu_id} {item.shortcut} {item.keymap} {item.owner_addon}".casefold()
            flags.append(self.bitflag_filter_item if not needle or needle in searchable else 0)
        return flags, []

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {"GRID", "GRID_FLOW"}:
            layout.alignment = "CENTER"
            layout.label(text=item.name, icon="MENU_PANEL" if item.enabled else "RADIOBUT_OFF")
            return

        row = layout.row(align=True)
        row.prop(item, "export_selected", text="")
        row.label(text="", icon="CHECKMARK" if item.enabled else "DOT")
        row.label(text=item.name or item.menu_id)
        row.label(text=item.shortcut)
        row.label(text=menu_data.keymap_label(item.keymap) or item.owner_addon)


def _slot_values(collection: Any) -> Dict[int, str]:
    return {
        item.slot_number: _ACTION_TOKEN_TO_REFERENCE.get(item.action_id, _EMPTY_ACTION)
        for item in collection
    }


def _selected_keymap(prefs: Any) -> str:
    return menu_data.keymap_value(
        prefs.editor_menu_mode,
        getattr(prefs, "editor_custom_keymap", ""),
    )


def _rebuild_keymaps() -> None:
    from .. import RadialMenu

    RadialMenu.rebuild_keymaps()


class ALLPIE_OT_menu_pick_action(Operator):
    """Open Blender's searchable action selector for one menu slot."""

    bl_idname = "allpie.menu_editor_pick_action"
    bl_label = "Choose Menu Action"
    bl_description = "Search AllPie action presets and assign one to this slot"
    bl_options = {"INTERNAL"}
    bl_property = "action_id"

    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    action_id: EnumProperty(name="Action", items=action_enum_items)

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
            self.report({"ERROR"}, "The target menu is no longer selected")
            return {"CANCELLED"}

        config = ConfigRuntime.get_config_copy()
        # Rebuild the searchable enum immediately before opening the popup so
        # newly added or removed presets are reflected without reopening prefs.
        current_reference = None
        collection = prefs.editor_spaced_slots if self.spaced else prefs.editor_slots
        for slot in collection:
            if slot.slot_number == self.slot_number:
                current_reference = _ACTION_TOKEN_TO_REFERENCE.get(slot.action_id)
                break
        _refresh_action_enum_items(config, None)
        current_token = _ACTION_REFERENCE_TO_TOKEN.get(current_reference, _EMPTY_ACTION)
        self.action_id = current_token if current_token in _ACTION_ALLOWED_TOKENS else _EMPTY_ACTION
        # Blender expects the operator invoke callback itself to return an
        # operator status set. invoke_search_popup() opens the search UI, but
        # its Python return value is not the status to return from invoke().
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
            self.report({"ERROR"}, "The target menu is no longer selected")
            return {"CANCELLED"}

        collection = prefs.editor_spaced_slots if self.spaced else prefs.editor_slots
        slot = next((item for item in collection if item.slot_number == self.slot_number), None)
        if slot is None:
            self.report({"ERROR"}, "The target slot no longer exists")
            return {"CANCELLED"}

        if self.action_id not in _ACTION_ALLOWED_TOKENS:
            self.report({"ERROR"}, "That action is not available in this menu's keymap context")
            return {"CANCELLED"}

        slot.action_id = self.action_id or _EMPTY_ACTION
        _mark_menu_draft_dirty(prefs)
        return {"FINISHED"}


class ALLPIE_OT_menu_clear_slot(Operator):
    """Clear one slot assignment without deleting its reusable action preset."""

    bl_idname = "allpie.menu_editor_clear_slot"
    bl_label = "Clear Menu Slot"
    bl_description = "Remove this action from the slot. The reusable preset remains available for other menus."
    bl_options = {"INTERNAL"}

    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
            self.report({"ERROR"}, "The target menu is no longer selected")
            return {"CANCELLED"}

        collection = prefs.editor_spaced_slots if self.spaced else prefs.editor_slots
        slot = next((item for item in collection if item.slot_number == self.slot_number), None)
        if slot is None:
            self.report({"ERROR"}, "The target slot no longer exists")
            return {"CANCELLED"}
        if slot.action_id == _EMPTY_ACTION:
            return {"CANCELLED"}

        slot.action_id = _EMPTY_ACTION
        _mark_menu_draft_dirty(prefs)
        self.report({"INFO"}, f"Cleared Slot {self.slot_number}")
        return {"FINISHED"}




class ALLPIE_OT_menu_clear_shortcut(Operator):
    """Remove the selected menu's shortcut without deleting the menu."""

    bl_idname = "allpie.menu_editor_clear_shortcut"
    bl_label = "Clear Shortcut"
    bl_description = "Remove this menu's key assignment"
    bl_options = {"INTERNAL"}

    target_menu_id: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
            self.report({"ERROR"}, "The target menu is no longer selected")
            return {"CANCELLED"}

        prefs.editor_loading = True
        try:
            prefs.editor_menu_key = "NONE"
            prefs.editor_menu_shift = False
            prefs.editor_menu_ctrl = False
            prefs.editor_menu_alt = False
            prefs.editor_menu_oskey = False
            prefs.editor_menu_hyper = False
        finally:
            prefs.editor_loading = False
        _mark_menu_draft_dirty(prefs)
        self.report({"INFO"}, "Shortcut cleared. Apply to save the change.")
        return {"FINISHED"}



class ALLPIE_OT_menu_assign_shortcut(Operator):
    """Assign a menu shortcut using Blender's native keymap event widget."""

    bl_idname = "allpie.menu_editor_assign_shortcut"
    bl_label = "Assign Shortcut"
    bl_description = "Capture a keyboard or mouse shortcut; Space and Esc are reserved for radial controls"
    bl_options = {"INTERNAL"}

    target_menu_id: StringProperty(options={"HIDDEN"})
    capture_token: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
            self.report({"ERROR"}, "The target menu is no longer selected")
            return {"CANCELLED"}

        modifiers = (
            name for name, enabled in (
                ("SHIFT", prefs.editor_menu_shift),
                ("CTRL", prefs.editor_menu_ctrl),
                ("ALT", prefs.editor_menu_alt),
                ("OSKEY", prefs.editor_menu_oskey),
                ("HYPER", prefs.editor_menu_hyper),
            ) if enabled
        )
        try:
            self.capture_token = _create_shortcut_capture_item(
                context,
                prefs.editor_menu_key,
                modifiers,
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not open shortcut capture: {error}")
            return {"CANCELLED"}

        result = context.window_manager.invoke_props_dialog(self, width=360)
        if "RUNNING_MODAL" not in result:
            _remove_shortcut_capture_item(self.capture_token)
        return result

    def draw(self, context):
        layout = self.layout
        record = _SHORTCUT_CAPTURE_ITEMS.get(self.capture_token)
        if record is None:
            layout.label(text="Shortcut capture is no longer available", icon="ERROR")
            return

        _keymap, item = record
        layout.label(text="Click the field, then press the desired key or mouse button.")
        row = layout.row(align=True)
        row.prop(item, "type", text="Shortcut", full_event=True)
        layout.label(text="Modifier keys are captured automatically.", icon="INFO")
        layout.label(text="Space and Esc are reserved for radial controls and cannot be assigned.", icon="INFO")

    def execute(self, context):
        record = _SHORTCUT_CAPTURE_ITEMS.get(self.capture_token)
        prefs = _preferences_from_context(context)
        if record is None:
            self.report({"ERROR"}, "Shortcut capture expired. Please try again.")
            return {"CANCELLED"}
        if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
            _remove_shortcut_capture_item(self.capture_token)
            self.report({"ERROR"}, "The target menu is no longer selected")
            return {"CANCELLED"}

        _keymap, item = record
        if not item.type or item.type == "NONE":
            _remove_shortcut_capture_item(self.capture_token)
            self.report({"WARNING"}, "Choose a valid key or mouse event")
            return {"CANCELLED"}

        reserved_message = reserved_menu_shortcut_message(item.type)
        if reserved_message:
            _remove_shortcut_capture_item(self.capture_token)
            self.report({"ERROR"}, reserved_message + ". Choose another menu shortcut.")
            return {"CANCELLED"}

        modifiers = _shortcut_modifier_values(item)
        prefs.editor_loading = True
        try:
            prefs.editor_menu_key = item.type
            prefs.editor_menu_shift = modifiers["SHIFT"]
            prefs.editor_menu_ctrl = modifiers["CTRL"]
            prefs.editor_menu_alt = modifiers["ALT"]
            prefs.editor_menu_oskey = modifiers["OSKEY"]
            prefs.editor_menu_hyper = modifiers["HYPER"]
        finally:
            prefs.editor_loading = False
        _mark_menu_draft_dirty(prefs)
        _remove_shortcut_capture_item(self.capture_token)
        self.report({"INFO"}, "Shortcut updated. Apply to save the change.")
        return {"FINISHED"}

    def cancel(self, context):
        _remove_shortcut_capture_item(self.capture_token)


def _build_menu_draft_config(prefs: Any) -> Dict[str, Any]:
    """Build the complete detached config containing the currently edited menu.

    When the draft contains new/edited operator presets, start from the stored
    draft rather than the active runtime. This preserves those pending operator
    changes while the menu's RNA controls are merged into the selected menu.
    """
    if prefs is None or not prefs.editor_active_menu_id:
        raise ValueError("No menu is selected")
    draft_json = str(getattr(prefs, "editor_draft_config_json", "") or "")
    if getattr(prefs, "editor_dirty", False) and draft_json:
        try:
            config = json.loads(draft_json)
        except (TypeError, ValueError) as error:
            raise ValueError(f"The pending menu draft could not be read: {error}") from error
        if not isinstance(config, dict):
            raise ValueError("The pending menu draft is not a configuration object")
    else:
        config = ConfigRuntime.get_config_copy()
    menu_data.update_menu(
        config,
        prefs.editor_active_menu_id,
        name=prefs.editor_menu_name,
        key=prefs.editor_menu_key,
        keymap=_selected_keymap(prefs),
        modifiers=(
            name for name, enabled in (
                ("SHIFT", prefs.editor_menu_shift),
                ("CTRL", prefs.editor_menu_ctrl),
                ("ALT", prefs.editor_menu_alt),
                ("OSKEY", prefs.editor_menu_oskey),
                ("HYPER", prefs.editor_menu_hyper),
            ) if enabled
        ),
        enabled=prefs.editor_menu_enabled,
        slots=_slot_values(prefs.editor_slots),
        spaced_enabled=prefs.editor_spaced_enabled,
        spaced_slots=_slot_values(prefs.editor_spaced_slots),
    )
    return config


class ALLPIE_OT_menu_apply(Operator):
    bl_idname = "allpie.menu_editor_apply"
    bl_label = "Apply Menu Changes"
    bl_description = "Validate and apply this menu to the active AllPie runtime"
    bl_options = {"INTERNAL"}

    validation_warning_text: StringProperty(options={"HIDDEN"})
    warnings_presented: BoolProperty(default=False, options={"HIDDEN"})

    def invoke(self, context, event):
        # A previously used operator button can retain hidden RNA values.
        # Reset this confirmation marker for every invocation so warnings are
        # never treated as reviewed merely because the operator ran before.
        self.warnings_presented = False
        self.validation_warning_text = ""
        prefs = _preferences_from_context(context)
        try:
            config = _build_menu_draft_config(prefs)
            report = validate_config(
                config,
                valid_event_types=ConfigRuntime.get_blender_event_identifiers(),
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not validate menu changes: {error}")
            return {"CANCELLED"}

        if not report.valid:
            details = "; ".join(
                f"{issue.path}: {issue.message}" for issue in report.errors[:3]
            )
            self.report({"ERROR"}, f"Menu changes are invalid: {details}")
            return {"CANCELLED"}

        self.validation_warning_text = "\n".join(str(issue) for issue in report.warnings)
        self.warnings_presented = bool(report.warnings)
        if report.warnings:
            return context.window_manager.invoke_props_dialog(self, width=620)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.label(text="AllPie found configuration warnings:", icon="ERROR")
        warning_box = layout.box()
        for line in self.validation_warning_text.splitlines()[:8]:
            warning_box.label(text=line[:180], icon="INFO")
        lines = self.validation_warning_text.splitlines()
        if len(lines) > 8:
            warning_box.label(text=f"And {len(lines) - 8} more warning(s)…")
        layout.label(text="Apply these changes anyway? You can edit conflicting shortcuts later.", icon="QUESTION")

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None or not prefs.editor_active_menu_id:
            self.report({"ERROR"}, "No menu is selected")
            return {"CANCELLED"}

        menu_id = prefs.editor_active_menu_id
        try:
            config = _build_menu_draft_config(prefs)
            report = validate_config(
                config,
                valid_event_types=ConfigRuntime.get_blender_event_identifiers(),
            )
            if not report.valid:
                details = "; ".join(
                    f"{issue.path}: {issue.message}" for issue in report.errors[:3]
                )
                self.report({"ERROR"}, f"Menu changes are invalid: {details}")
                return {"CANCELLED"}
            if report.warnings and not self.warnings_presented:
                self.report({"WARNING"}, "Configuration warnings must be reviewed before applying these changes")
                return {"CANCELLED"}
            ConfigRuntime.replace_and_save_configuration(config)
            _rebuild_keymaps()
        except Exception as error:
            self.report({"ERROR"}, f"Could not apply menu: {error}")
            return {"CANCELLED"}

        prefs.editor_dirty = False
        prefs.editor_draft_config_json = ""
        prefs.editor_config_generation = -1
        # A keymap edit can move a menu into a different browser category.
        # Follow it automatically so the edited menu remains selected.
        prefs.editor_category = menu_data.category_for_menu(config, menu_id)
        _ensure_editor_state(prefs)
        self.report({"INFO"}, f"Applied '{prefs.editor_menu_name}'")
        return {"FINISHED"}


class ALLPIE_OT_menu_add(Operator):
    bl_idname = "allpie.menu_editor_add"
    bl_label = "Add Menu"
    bl_description = "Create a new empty AllPie menu"

    name: StringProperty(name="Name", default="Custom Menu")
    key: StringProperty(name="Key", default="A", options={"HIDDEN"})
    keymap: EnumProperty(
        name="Context",
        description="Blender mode or editor context in which this radial menu is available",
        items=menu_data.KEYMAP_ENUM_ITEMS,
        default="OBJECT_MODE",
    )
    custom_keymap: StringProperty(name="Custom Keymap", default="")

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None:
            if prefs.editor_category == "OTHER":
                self.keymap = "CUSTOM"
                self.custom_keymap = ""
            else:
                default_keymap = menu_data.CATEGORY_TO_KEYMAP.get(
                    prefs.editor_category, "Object Mode"
                )
                self.keymap = menu_data.keymap_identifier(default_keymap)
                self.custom_keymap = ""
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        try:
            preview_config = ConfigRuntime.get_config_copy()
            generated_id = menu_data.generate_menu_id(preview_config, self.name)
        except Exception:
            generated_id = "CUSTOM.MENU"
        preview = layout.row()
        preview.enabled = False
        preview.label(text=f"Generated ID: {generated_id}", icon="INFO")
        preview.label(text="ID remains stable after creation")
        layout.prop(self, "keymap")
        if self.keymap == "CUSTOM":
            layout.prop(self, "custom_keymap")
        layout.label(text="The new menu starts disabled with a default A shortcut and eight empty slots.", icon="INFO")
        layout.label(text="You can assign its shortcut in the menu editor after creation.")

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu draft first")
            return {"CANCELLED"}
        try:
            config = ConfigRuntime.get_config_copy()
            if not self.name.strip():
                raise ValueError("Menu name cannot be empty")
            menu_id = menu_data.add_menu(
                config,
                name=self.name,
                key=self.key,
                keymap=menu_data.keymap_value(self.keymap, self.custom_keymap),
            )
            ConfigRuntime.replace_and_save_configuration(config)
            _rebuild_keymaps()
        except Exception as error:
            self.report({"ERROR"}, f"Could not create menu: {error}")
            return {"CANCELLED"}

        prefs = _preferences_from_context(context)
        if prefs is not None:
            prefs.editor_active_menu_id = menu_id
            prefs.editor_dirty = False
            prefs.editor_draft_config_json = ""
            prefs.editor_config_generation = -1
            prefs.editor_category = menu_data.category_for_menu(config, menu_id)
            _ensure_editor_state(prefs)
        self.report({"INFO"}, f"Created menu '{menu_id}'")
        return {"FINISHED"}


class ALLPIE_OT_menu_duplicate(Operator):
    bl_idname = "allpie.menu_editor_duplicate"
    bl_label = "Duplicate Menu"
    bl_description = "Duplicate the selected menu; the copy starts disabled"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        prefs = _preferences_from_context(context)
        return prefs is not None and bool(prefs.editor_active_menu_id)

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu draft first")
            return {"CANCELLED"}
        try:
            config = ConfigRuntime.get_config_copy()
            new_id = menu_data.duplicate_menu(config, prefs.editor_active_menu_id)
            ConfigRuntime.replace_and_save_configuration(config)
            _rebuild_keymaps()
        except Exception as error:
            self.report({"ERROR"}, f"Could not duplicate menu: {error}")
            return {"CANCELLED"}

        prefs.editor_active_menu_id = new_id
        prefs.editor_dirty = False
        prefs.editor_draft_config_json = ""
        prefs.editor_config_generation = -1
        _ensure_editor_state(prefs)
        self.report({"INFO"}, f"Duplicated menu as '{new_id}'")
        return {"FINISHED"}


class ALLPIE_OT_menu_remove(Operator):
    bl_idname = "allpie.menu_editor_remove"
    bl_label = "Remove Menu"
    bl_description = "Remove the selected menu from the active configuration"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        prefs = _preferences_from_context(context)
        return prefs is not None and bool(prefs.editor_active_menu_id)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu draft first")
            return {"CANCELLED"}
        menu_id = prefs.editor_active_menu_id
        try:
            config = ConfigRuntime.get_config_copy()
            menu_data.remove_menu(config, menu_id)
            ConfigRuntime.replace_and_save_configuration(config)

            _rebuild_keymaps()
        except Exception as error:
            self.report({"ERROR"}, f"Could not remove menu: {error}")
            return {"CANCELLED"}

        prefs.editor_active_menu_id = ""
        prefs.editor_dirty = False
        prefs.editor_draft_config_json = ""
        prefs.editor_config_generation = -1
        _ensure_editor_state(prefs)
        self.report({"INFO"}, f"Removed menu '{menu_id}'")
        return {"FINISHED"}


class ALLPIE_OT_menu_discard(Operator):
    bl_idname = "allpie.menu_editor_discard"
    bl_label = "Discard Draft"
    bl_description = "Discard unapplied edits and load the currently selected menu"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is not None:
            selected_id = (
                prefs.editor_menus[prefs.active_menu_index].menu_id
                if 0 <= prefs.active_menu_index < len(prefs.editor_menus)
                else prefs.editor_active_menu_id
            )
            prefs.editor_active_menu_id = selected_id
            prefs.editor_dirty = False
            prefs.editor_draft_config_json = ""
            prefs.editor_config_generation = -1
            _ensure_editor_state(prefs)
        return {"FINISHED"}


class ALLPIE_OT_menu_export_json(Operator):
    """Export checked menu definitions and their referenced operator presets."""

    bl_idname = "allpie.menu_editor_export_json"
    bl_label = "Export Menu JSON"
    bl_description = "Export checked menus, or the active menu when none are checked, with their referenced presets"
    bl_options = {"INTERNAL"}

    target_menu_ids: StringProperty(options={"HIDDEN"})
    filepath: StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        prefs = _preferences_from_context(context)
        return (
            prefs is not None
            and (bool(prefs.editor_active_menu_id) or any(item.export_selected for item in prefs.editor_menus))
            and not prefs.editor_dirty
        )

    def invoke(self, context, event):
        if not self.target_menu_ids:
            prefs = _preferences_from_context(context)
            if prefs is not None:
                selected_ids = [item.menu_id for item in prefs.editor_menus if item.export_selected]
                if not selected_ids and prefs.editor_active_menu_id:
                    selected_ids = [prefs.editor_active_menu_id]
                self.target_menu_ids = json.dumps(selected_ids)
        if not self.filepath:
            try:
                target_ids = json.loads(self.target_menu_ids or "[]")
                config = ConfigRuntime.get_config_copy()
                if len(target_ids) == 1:
                    menu = menu_data.get_menu(config, target_ids[0])
                    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", str(menu.get("name", target_ids[0]))).strip("_")
                    filename = f"{stem or 'allpie_menu'}.json"
                else:
                    filename = "allpie_menus.json"
                configured = ConfigRuntime.USER_CONFIG_PATH or ConfigRuntime.ACTIVE_CONFIG_PATH or ConfigRuntime.DEFAULT_CONFIG_PATH
                self.filepath = str(Path(configured).expanduser().parent / filename)
            except Exception:
                self.filepath = "allpie_menus.json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard menu changes before exporting")
            return {"CANCELLED"}
        try:
            target_menu_ids = json.loads(self.target_menu_ids or "[]")
        except (TypeError, ValueError):
            target_menu_ids = []
        if not isinstance(target_menu_ids, list) or not target_menu_ids:
            target_menu_ids = [prefs.editor_active_menu_id] if prefs.editor_active_menu_id else []
        target_menu_ids = [menu_id for menu_id in target_menu_ids if isinstance(menu_id, str) and menu_id]
        if not target_menu_ids:
            self.report({"ERROR"}, "Select at least one menu to export")
            return {"CANCELLED"}
        if not self.filepath:
            self.report({"ERROR"}, "Choose a destination JSON file")
            return {"CANCELLED"}

        destination = Path(bpy.path.abspath(self.filepath)).expanduser()
        if destination.suffix.casefold() != ".json":
            destination = destination.with_suffix(".json")
        try:
            config = ConfigRuntime.get_config_copy()
            package = menu_exchange.build_menu_package(config, target_menu_ids)
            menu_exchange.write_menu_package(destination, package)
            self.report(
                {"INFO"},
                f"Exported {len(package['Menus'])} menu(s) with {len(package['Operators'])} operator preset(s)",
            )
            for item in prefs.editor_menus:
                if item.menu_id in target_menu_ids:
                    item.export_selected = False
        except Exception as error:
            self.report({"ERROR"}, f"Could not export menu JSON: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class ALLPIE_OT_menu_import_json(Operator):
    """Import menu definitions additively from an AllPie menu JSON file."""

    bl_idname = "allpie.menu_editor_import_json"
    bl_label = "Import Menu JSON"
    bl_description = "Add menus and their referenced operator presets from an AllPie JSON file"
    bl_options = {"INTERNAL"}

    filepath: StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        prefs = _preferences_from_context(context)
        return prefs is not None and not prefs.editor_dirty

    def invoke(self, context, event):
        if not self.filepath:
            configured = ConfigRuntime.USER_CONFIG_PATH or ConfigRuntime.ACTIVE_CONFIG_PATH or ConfigRuntime.DEFAULT_CONFIG_PATH
            self.filepath = str(Path(configured).expanduser().parent / "allpie_menu.json")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None or prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard menu changes before importing")
            return {"CANCELLED"}
        if not self.filepath:
            self.report({"ERROR"}, "Choose an AllPie menu JSON file")
            return {"CANCELLED"}

        source = Path(bpy.path.abspath(self.filepath)).expanduser()
        try:
            package = menu_exchange.load_menu_package(source)
            current = ConfigRuntime.get_config_copy()
            merged, counts = menu_exchange.merge_menu_package(
                current,
                package,
                valid_event_types=ConfigRuntime.get_blender_event_identifiers(),
            )
            destination = ConfigRuntime.USER_CONFIG_PATH or ConfigRuntime.ACTIVE_CONFIG_PATH
            ConfigRuntime.replace_and_save_configuration(
                merged,
                path=destination,
                backup=True,
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not import menu JSON: {error}")
            return {"CANCELLED"}

        refresh_warning = ""
        try:
            _rebuild_keymaps()
            imported_menu_id = counts["menu_ids"][0] if counts["menu_ids"] else ""
            prefs.editor_loading = True
            try:
                prefs.editor_category = "ALL"
                prefs.editor_active_menu_id = imported_menu_id
                prefs.editor_dirty = False
                prefs.editor_draft_config_json = ""
                prefs.editor_config_generation = -1
            finally:
                prefs.editor_loading = False
            _ensure_editor_state(prefs)
        except Exception as error:
            refresh_warning = str(error)

        message = (
            f"Imported {len(counts['menu_ids'])} menu(s); "
            f"added {counts['actions_added']} and reused {counts['actions_reused']} operator preset(s)"
        )
        self.report({"WARNING"} if (counts["warnings"] or refresh_warning) else {"INFO"}, message)
        if counts["warnings"]:
            self.report({"WARNING"}, f"Imported menus created {len(counts['warnings'])} new configuration warning(s), possibly including shortcut conflicts")
        if refresh_warning:
            self.report({"WARNING"}, f"Menus imported, but the editor refresh had an issue: {refresh_warning}")
        return {"FINISHED"}


class ALLPIE_OT_menu_refresh(Operator):
    bl_idname = "allpie.menu_editor_refresh"
    bl_label = "Refresh Menu List"
    bl_description = "Reload the menu browser from the active configuration"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is not None:
            selected_id = (
                prefs.editor_menus[prefs.active_menu_index].menu_id
                if 0 <= prefs.active_menu_index < len(prefs.editor_menus)
                else prefs.editor_active_menu_id
            )
            prefs.editor_active_menu_id = selected_id
            prefs.editor_dirty = False
            prefs.editor_draft_config_json = ""
            prefs.editor_config_generation = -1
            _ensure_editor_state(prefs)
        return {"FINISHED"}


def _configurable_slot_action_ids(prefs: Any) -> set[str]:
    """Return AllPie's locally editable preset IDs used by the visible slots.

    Use the active config by reference during ordinary drawing. When the menu
    has unapplied edits, build one detached draft so newly assigned presets are
    also recognized without repeatedly parsing the draft for every slot.
    """
    try:
        config = (
            _build_menu_draft_config(prefs)
            if getattr(prefs, "editor_dirty", False)
            else ConfigRuntime.ACTIVE_CONFIG
        )
        if not isinstance(config, dict):
            return set()

        tokens = {
            str(slot.action_id or "")
            for collection in (prefs.editor_slots, prefs.editor_spaced_slots)
            for slot in collection
        }
        action_ids = {
            _ACTION_TOKEN_TO_REFERENCE.get(token, "")
            for token in tokens
            if token and token != _EMPTY_ACTION
        }

        configurable: set[str] = set()
        for action_id in action_ids:
            if not action_id:
                continue
            try:
                _container, _local_id, owner_addon = operator_data.get_action_container(
                    config, action_id
                )
            except (KeyError, TypeError, ValueError):
                continue
            if owner_addon is None:
                configurable.add(action_id)
        return configurable
    except Exception:
        # A temporary draft/configuration issue should not break Preferences
        # drawing. The search and clear controls remain available regardless.
        return set()


def _draw_slot_button(
    layout: Any,
    prefs: Any,
    slot: Any,
    menu_id: str,
    spaced: bool,
    configurable_action_ids: set[str],
) -> None:
    """Draw the numbered slot picker with compact configure and clear icons."""
    token = slot.action_id or _EMPTY_ACTION
    action_id = _ACTION_TOKEN_TO_REFERENCE.get(token, "")
    action_label = _ACTION_TOKEN_TO_LABEL.get(token, "Empty") if action_id else "Empty"
    label = f"{slot.slot_number}. {action_label}"

    # Reserve most of the row for the action label and keep the two utility
    # icons compact and consistently aligned at the right edge.
    slot_split = layout.split(factor=0.84, align=True)
    picker = slot_split.operator(
        "allpie.search_blender_operator",
        text=label,
        emboss=True,
    )
    picker.target_menu_id = menu_id
    picker.slot_number = slot.slot_number
    picker.spaced = spaced
    picker.context_name = _selected_keymap(prefs)
    picker.assigned_action_id = action_id

    controls = slot_split.row(align=True)

    gear_column = controls.column(align=True)
    gear_column.enabled = bool(action_id and action_id in configurable_action_ids)
    configure = gear_column.operator(
        "allpie.setup_blender_operator",
        text="",
        icon="PREFERENCES",
    )
    configure.action_id = action_id
    configure.operator_id = ""
    configure.create_new_action = False
    configure.source_action_id = ""
    configure.prefill_from_action = False
    configure.source_contexts_json = "[]"
    configure.expose_preset_name = False
    configure.target_menu_id = menu_id
    configure.slot_number = slot.slot_number
    configure.spaced = spaced
    configure.context_name = ""
    configure.capture_button_properties = False
    configure.button_properties_json = "{}"
    configure.button_unsupported_properties_json = "[]"

    clear_column = controls.column(align=True)
    clear_column.enabled = bool(action_id)
    clear = clear_column.operator(
        "allpie.menu_editor_clear_slot",
        text="",
        icon="X",
    )
    clear.target_menu_id = menu_id
    clear.slot_number = slot.slot_number
    clear.spaced = spaced


def _draw_slot_list(
    layout: Any,
    prefs: Any,
    collection: Any,
    menu_id: str,
    spaced: bool,
    configurable_action_ids: set[str],
) -> None:
    """Draw eight vertically stacked numbered buttons for one slot set."""
    slots_by_number = {slot.slot_number: slot for slot in collection}
    slot_list = layout.column(align=False)

    for slot_number in range(1, 9):
        slot = slots_by_number.get(slot_number)
        if slot is None:
            continue
        button_row = slot_list.row(align=True)
        _draw_slot_button(
            button_row,
            prefs,
            slot,
            menu_id,
            spaced,
            configurable_action_ids,
        )


def draw_menu_editor(layout: Any, prefs: Any, context: Any) -> None:
    """Draw the first-stage Menus editor inside AddonPreferences."""
    _ensure_editor_state(prefs)

    header = layout.row(align=True)
    header.label(text="Menu Configuration", icon="MENU_PANEL")
    header.operator("allpie.menu_editor_refresh", text="", icon="FILE_REFRESH")

    active_warnings = getattr(ConfigRuntime, "ACTIVE_VALIDATION_WARNINGS", ())
    if active_warnings:
        warning_box = layout.box()
        warning_box.alert = True
        warning_box.label(text=f"Configuration warnings: {len(active_warnings)}", icon="ERROR")
        for issue in active_warnings[:4]:
            warning_box.label(text=str(issue)[:180], icon="INFO")
        if len(active_warnings) > 4:
            warning_box.label(text=f"And {len(active_warnings) - 4} more warning(s)…")

    split = layout.split(factor=0.34)
    browser = split.column(align=True)
    editor = split.column(align=True)

    category_row = browser.row(align=True)
    category_row.enabled = not prefs.editor_dirty
    category_row.prop(prefs, "editor_category", text="Category")
    category_title = menu_data.category_label(prefs.editor_category)
    if prefs.editor_category == "COMMON":
        browser.label(text=f"{category_title}  ({len(prefs.editor_menus)})")
    else:
        browser.label(text=f"{category_title} Menus  ({len(prefs.editor_menus)})")
    browser.template_list(
        "ALLPIE_UL_menu_list",
        "allpie_menus",
        prefs,
        "editor_menus",
        prefs,
        "active_menu_index",
        rows=12,
        maxrows=18,
    )
    buttons = browser.row(align=True)
    # Third-party menus are contributed by their owning addons; the generic
    # Add Menu action creates a built-in menu and therefore is not available
    # while browsing that category. Duplicate and Remove remain available.
    add_column = buttons.column()
    add_column.enabled = prefs.editor_category != "THIRD_PARTY"
    add_column.operator("allpie.menu_editor_add", text="", icon="ADD")
    buttons.operator("allpie.menu_editor_duplicate", text="", icon="DUPLICATE")
    buttons.operator("allpie.menu_editor_remove", text="", icon="REMOVE")

    cleanup = browser.row(align=True)
    cleanup.enabled = not prefs.editor_dirty
    cleanup.operator(
        "allpie.cleanup_unused_operator_presets",
        text="Clean Unused Presets",
        icon="TRASH",
    )

    exchange = browser.row(align=True)
    exchange.enabled = not prefs.editor_dirty
    exchange.operator("allpie.menu_editor_import_json", text="Import Menu", icon="IMPORT")
    export_column = exchange.column()
    export_column.enabled = bool(prefs.editor_active_menu_id) or any(
        item.export_selected for item in prefs.editor_menus
    )
    export_menu = export_column.operator(
        "allpie.menu_editor_export_json", text="Export Menu", icon="EXPORT"
    )
    selected_menu_ids = [item.menu_id for item in prefs.editor_menus if item.export_selected]
    if not selected_menu_ids and prefs.editor_active_menu_id:
        selected_menu_ids = [prefs.editor_active_menu_id]
    export_menu.target_menu_ids = json.dumps(selected_menu_ids)
    browser.label(
        text="Menu packages are additive; use Configuration for a full backup and restore.",
        icon="INFO",
    )

    if not prefs.editor_active_menu_id:
        editor.label(text="Select a menu to edit", icon="INFO")
        editor.label(text="Use + to create a new menu.")
        return

    editor_header = editor.row(align=True)
    editor_header.label(text=prefs.editor_menu_name or prefs.editor_active_menu_id, icon="MENU_PANEL")
    if prefs.editor_dirty:
        warning = editor.box()
        warning.alert = True
        warning.label(text="Unapplied changes. Apply or discard before switching menus.", icon="ERROR")

    identity = editor.box()
    identity.enabled = False
    identity.prop(prefs, "editor_menu_id", text="Menu ID")

    details = editor.box()
    details.label(text="Menu Settings")

    # Keep the two most frequently edited menu properties together. The
    # category/list already communicates the menu context, so repeating it in
    # every menu's settings only consumes vertical space.
    name_shortcut_row = details.row(align=True)
    name_shortcut_row.prop(prefs, "editor_menu_name", text="Name")
    shortcut = name_shortcut_row.operator(
        "allpie.menu_editor_assign_shortcut",
        text=_format_shortcut(
            prefs.editor_menu_key,
            [
                name for name, enabled in (
                    ("SHIFT", prefs.editor_menu_shift),
                    ("CTRL", prefs.editor_menu_ctrl),
                    ("ALT", prefs.editor_menu_alt),
                    ("OSKEY", prefs.editor_menu_oskey),
                    ("HYPER", prefs.editor_menu_hyper),
                ) if enabled
            ],
        ),
        icon="KEYINGSET",
    )
    shortcut.target_menu_id = prefs.editor_active_menu_id
    clear_shortcut = name_shortcut_row.operator(
        "allpie.menu_editor_clear_shortcut",
        text="",
        icon="X",
    )
    clear_shortcut.target_menu_id = prefs.editor_active_menu_id

    row = details.row(align=True)
    row.prop(prefs, "editor_menu_enabled", text="Enabled")
    # Keep both slot sets side by side, but list their eight actions vertically.
    # Each action button has compact gear and clear icons at its right edge.
    configurable_action_ids = _configurable_slot_action_ids(prefs)
    slot_panels = editor.split(factor=0.5, align=False)

    normal_panel = slot_panels.column(align=False)
    normal_header = normal_panel.row(align=True)
    normal_header.alignment = "CENTER"
    normal_header.label(text="Normal Slots")
    _draw_slot_list(
        normal_panel,
        prefs,
        prefs.editor_slots,
        prefs.editor_active_menu_id,
        False,
        configurable_action_ids,
    )

    spaced_panel = slot_panels.column(align=False)
    spaced_header = spaced_panel.row(align=True)
    spaced_header.alignment = "CENTER"
    spaced_header.label(text="Spaced Slots")
    spaced_header.prop(prefs, "editor_spaced_enabled", text="")
    spaced_controls = spaced_panel.column(align=False)
    spaced_controls.enabled = bool(prefs.editor_spaced_enabled)
    _draw_slot_list(
        spaced_controls,
        prefs,
        prefs.editor_spaced_slots,
        prefs.editor_active_menu_id,
        True,
        configurable_action_ids,
    )

    note = editor.row()
    note.label(text="Apply saves changes to your AllPie user configuration.", icon="INFO")

    # Keep commit controls at the bottom of the editing surface, close to the
    # slots they apply to, rather than in the menu title/header row.
    actions = editor.row(align=True)
    actions.alignment = "RIGHT"
    actions.operator("allpie.menu_editor_apply", text="Apply", icon="CHECKMARK")
    if prefs.editor_dirty:
        actions.operator("allpie.menu_editor_discard", text="Discard", icon="LOOP_BACK")


CLASSES = (
    AllPieMenuListItem,
    ALLPIE_OT_menu_pick_action,
    ALLPIE_OT_menu_clear_slot,
    ALLPIE_OT_menu_clear_shortcut,
    ALLPIE_OT_menu_assign_shortcut,
    AllPieMenuSlotItem,
    ALLPIE_UL_menu_list,
    ALLPIE_OT_menu_apply,
    ALLPIE_OT_menu_add,
    ALLPIE_OT_menu_duplicate,
    ALLPIE_OT_menu_remove,
    ALLPIE_OT_menu_discard,
    ALLPIE_OT_menu_export_json,
    ALLPIE_OT_menu_import_json,
    ALLPIE_OT_menu_refresh,
)
