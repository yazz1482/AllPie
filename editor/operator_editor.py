"""Blender-native registered-operator browser for AllPie.

The catalog is scanned from Blender RNA and cached for the session. A compact
search popup displays operators in a UIList; each result button uses Blender's
dynamic Operator.description() callback so hovering a result explains what it
does. Selecting a result creates/reuses an AllPie preset and optionally assigns
it directly to a menu slot.
"""

from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any, Dict, List, Mapping

import bpy
from bpy.types import Operator, PropertyGroup, UIList
from bpy.props import BoolProperty, IntProperty, StringProperty

from ..core import runtime as ConfigRuntime
from . import menu_data, operator_data

OPERATOR_EDITOR_API_VERSION = 9

_OPERATOR_INFO: Dict[str, Dict[str, str]] = {}
_OPERATOR_CATALOG_GENERATION = 0
_SEARCH_MATCH_CACHE_KEY = None
_SEARCH_MATCH_CACHE: List[int] = []
_BUILTIN_ACTION_IDS = None
_USER_ACTION_MATCH_CACHE_KEY = None
_USER_ACTION_MATCH_CACHE: List[int] = []
SEARCH_CONTEXT_ITEMS = tuple(
    item for item in menu_data.KEYMAP_ENUM_ITEMS if item[0] not in {"CUSTOM", "COMMON"}
)


def _preferences_from_context(context: Any) -> Any:
    from .. import Preferences
    addon = context.preferences.addons.get(Preferences.__package__)
    return addon.preferences if addon is not None else None


def _humanize_operator_id(operator_id: str) -> str:
    return re.sub(r"[_]+", " ", operator_id.rsplit(".", 1)[-1]).strip().title()


def _scan_registered_operators() -> List[Dict[str, str]]:
    """Enumerate registered bpy.ops identifiers and their RNA labels/descriptions."""
    discovered: List[Dict[str, str]] = []
    try:
        module_names = dir(bpy.ops)
    except Exception:
        return discovered

    for module_name in module_names:
        if not module_name or module_name.startswith("_") or module_name.casefold() == "allpie":
            continue
        try:
            operator_module = getattr(bpy.ops, module_name)
            operator_names = dir(operator_module)
        except Exception:
            continue

        for operator_name in operator_names:
            if not operator_name or operator_name.startswith("_"):
                continue
            operator_id = f"{module_name}.{operator_name}"
            if operator_id in {"wm.search_operator", "wm.search_menu", "wm.search_single_menu"}:
                continue
            try:
                operator = getattr(operator_module, operator_name)
                rna = operator.get_rna_type()
                label = str(getattr(rna, "name", "") or "").strip()
                description = str(getattr(rna, "description", "") or "").strip()
            except Exception:
                continue

            if not label:
                label = _humanize_operator_id(operator_id)
            if not description:
                description = f"No description is registered for {label}."
            discovered.append({
                "operator_id": operator_id,
                "name": label,
                "description": description,
                "module": module_name,
            })

    discovered.sort(key=lambda item: (item["name"].casefold(), item["operator_id"].casefold()))
    label_counts = Counter(item["name"].casefold() for item in discovered)
    for item in discovered:
        item["display_name"] = (
            f"{item['name']} ({item['module']})"
            if label_counts[item["name"].casefold()] > 1
            else item["name"]
        )
    return discovered


def _refresh_operator_catalog() -> int:
    """Rescan Blender's registered operators; called explicitly or on first use."""
    global _OPERATOR_INFO, _OPERATOR_CATALOG_GENERATION
    records = _scan_registered_operators()
    _OPERATOR_INFO = {record["operator_id"]: record for record in records}
    _OPERATOR_CATALOG_GENERATION += 1
    return len(records)


def _ensure_operator_catalog() -> int:
    if _OPERATOR_INFO:
        return len(_OPERATOR_INFO)
    return _refresh_operator_catalog()


def _populate_search_items(prefs: Any) -> None:
    """Copy the cached operator catalog into transient preference rows once per catalog generation."""
    if getattr(prefs, "operator_search_catalog_generation", -1) == _OPERATOR_CATALOG_GENERATION:
        return
    collection = prefs.operator_search_items
    collection.clear()
    for record in _OPERATOR_INFO.values():
        item = collection.add()
        item.operator_id = record["operator_id"]
        item.name = record["display_name"]
        item.description = record["description"]
        item.module = record["module"]
    prefs.operator_search_query = ""
    prefs.operator_search_active_index = 0
    prefs.operator_search_catalog_generation = _OPERATOR_CATALOG_GENERATION


def _context_from_preferences(prefs: Any) -> str:
    identifier = str(getattr(prefs, "operator_search_context", "OBJECT_MODE"))
    return menu_data.keymap_value(identifier)


def _add_operator_to_allpie(
    context: Any,
    *,
    operator_id: str,
    target_menu_id: str = "",
    slot_number: int = 1,
    spaced: bool = False,
    context_name: str = "Object Mode",
    properties: Mapping[str, Any] | None = None,
    invoke: bool = True,
    name_override: str = "",
    search_name: str = "",
) -> bool:
    """Create/reuse a configured action preset, optionally assigning it to a menu slot."""
    prefs = _preferences_from_context(context)
    if prefs is not None and prefs.editor_dirty:
        raise RuntimeError("Apply or discard the current menu changes before adding a Blender operator")
    record = _OPERATOR_INFO.get(operator_id)
    if record is None:
        raise RuntimeError("The selected Blender operator is no longer available. Refresh the catalog.")

    config = ConfigRuntime.get_config_copy()
    action_id, created = operator_data.create_or_reuse_blender_operator(
        config,
        operator_id=operator_id,
        name=name_override or record["name"],
        description=record["description"],
        context_name=context_name,
        context_names=menu_data.keymap_contexts(context_name),
        properties=properties or {},
        invoke=invoke,
        search_name=search_name or name_override or record["name"],
    )

    if target_menu_id:
        if prefs is None or prefs.editor_active_menu_id != target_menu_id:
            raise RuntimeError("The target menu is no longer selected")
        menu_container, local_menu_id = menu_data.get_menu_container(config, target_menu_id)
        menu = menu_container[local_menu_id]
        slot_field = "spaced_slots" if spaced else "slots"
        menu.setdefault(slot_field, {})[str(slot_number)] = action_id

    # Ensure the preset was actually persisted before publishing any UI state.
    # This guards against a stale generated ID or an unexpected normalization
    # difference between the draft and the active registry.
    if action_id not in config.get("Operators", {}):
        raise RuntimeError(f"Operator preset '{action_id}' was not created in the configuration")

    ConfigRuntime.replace_and_save_configuration(config)
    if prefs is not None:
        prefs.operator_search_last_added = f"{record['name']} {'added' if created else 'reused'} in {context_name}"
        # The custom-action list is a cached UI snapshot. Invalidate and rebuild
        # it immediately so a newly-created preset can be edited/deleted without
        # selecting a stale row from the previous registry generation.
        prefs.user_action_registry_generation = -1
        _ensure_user_action_items(prefs)
        if target_menu_id:
            from . import menu_editor
            prefs.editor_config_generation = -1
            menu_editor._ensure_editor_state(prefs)
    return created


def _matching_search_indices(prefs: Any) -> List[int]:
    """Return cached result indices; rebuild only when query/catalog changes."""
    global _SEARCH_MATCH_CACHE_KEY, _SEARCH_MATCH_CACHE
    needle = str(getattr(prefs, "operator_search_query", "") or "").casefold().strip()
    generation = int(getattr(prefs, "operator_search_catalog_generation", -1))
    brush_only = bool(getattr(prefs, "operator_search_brush_only", False))
    cache_key = (generation, needle, len(prefs.operator_search_items), brush_only)
    if cache_key == _SEARCH_MATCH_CACHE_KEY:
        return _SEARCH_MATCH_CACHE

    matches: List[int] = []
    for index, item in enumerate(prefs.operator_search_items):
        if brush_only and item.operator_id not in menu_data.BRUSH_MENU_OPERATOR_IDS:
            continue
        haystack = f"{item.name} {item.operator_id} {item.description} {item.module}".casefold()
        if not needle or needle in haystack:
            matches.append(index)
    _SEARCH_MATCH_CACHE_KEY = cache_key
    _SEARCH_MATCH_CACHE = matches
    return _SEARCH_MATCH_CACHE


def update_operator_search_query(self: Any, context: Any) -> None:
    """Keep the active result on the first visible item as the query changes."""
    matches = _matching_search_indices(self)
    self.operator_search_active_index = matches[0] if matches else 0


def _get_bundled_action_ids() -> frozenset[str]:
    """Read the shipped preset IDs once to recognize custom actions from older builds."""
    global _BUILTIN_ACTION_IDS
    if _BUILTIN_ACTION_IDS is not None:
        return _BUILTIN_ACTION_IDS
    try:
        with ConfigRuntime.DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
            bundled = json.load(handle)
        _BUILTIN_ACTION_IDS = frozenset(bundled.get("Operators", {}).keys())
    except Exception:
        # Explicit user_defined metadata still makes newly-created actions
        # manageable if the bundled config cannot be read for some reason.
        _BUILTIN_ACTION_IDS = frozenset()
    return _BUILTIN_ACTION_IDS


def _ensure_user_action_items(prefs: Any) -> None:
    """Refresh the compact custom-action manager only when config changes."""
    if not ConfigRuntime.INITIALIZED:
        return
    generation = ConfigRuntime.REGISTRY.generation
    if getattr(prefs, "user_action_registry_generation", -1) == generation:
        return

    config = ConfigRuntime.get_config_copy()
    records = operator_data.iter_user_action_records(config, _get_bundled_action_ids())
    previous_id = ""
    try:
        if 0 <= prefs.user_action_active_index < len(prefs.user_action_items):
            previous_id = prefs.user_action_items[prefs.user_action_active_index].action_id
    except (AttributeError, IndexError, TypeError):
        pass

    prefs.user_action_loading = True
    try:
        prefs.user_action_items.clear()
        selected_index = 0
        for index, record in enumerate(records):
            item = prefs.user_action_items.add()
            item.action_id = record["action_id"]
            item.name = record["name"]
            item.operator_id = record["operator_id"]
            item.description = record["description"]
            item.usage_count = record["usage_count"]
            if record["action_id"] == previous_id:
                selected_index = index
        prefs.user_action_active_index = min(selected_index, max(0, len(records) - 1))
        prefs.user_action_registry_generation = generation
    finally:
        prefs.user_action_loading = False


def _matching_user_action_indices(prefs: Any) -> List[int]:
    """Filter the manageable-action list by name, preset ID, operator and description."""
    global _USER_ACTION_MATCH_CACHE_KEY, _USER_ACTION_MATCH_CACHE
    needle = str(getattr(prefs, "user_action_search", "") or "").casefold().strip()
    generation = int(getattr(prefs, "user_action_registry_generation", -1))
    cache_key = (generation, needle, len(prefs.user_action_items))
    if cache_key == _USER_ACTION_MATCH_CACHE_KEY:
        return _USER_ACTION_MATCH_CACHE

    matches: List[int] = []
    for index, item in enumerate(prefs.user_action_items):
        haystack = f"{item.name} {item.action_id} {item.operator_id} {item.description}".casefold()
        if not needle or needle in haystack:
            matches.append(index)
    _USER_ACTION_MATCH_CACHE_KEY = cache_key
    _USER_ACTION_MATCH_CACHE = matches
    return _USER_ACTION_MATCH_CACHE


def update_user_action_search(self: Any, context: Any) -> None:
    matches = _matching_user_action_indices(self)
    self.user_action_active_index = matches[0] if matches else 0


def _selected_user_action_id(prefs: Any) -> str:
    index = int(getattr(prefs, "user_action_active_index", -1))
    items = prefs.user_action_items
    if 0 <= index < len(items):
        return str(items[index].action_id)
    return ""


class AllPieOperatorSearchItem(PropertyGroup):
    operator_id: StringProperty()
    name: StringProperty()
    description: StringProperty()
    module: StringProperty()


class ALLPIE_UL_operator_search_results(UIList):
    """Searchable catalog; every row button has an operator-specific tooltip."""

    def filter_items(self, context, data, property_name):
        items = getattr(data, property_name)
        visible_indices = set(_matching_search_indices(data))
        flags = [
            self.bitflag_filter_item if index in visible_indices else 0
            for index, _item in enumerate(items)
        ]
        return flags, []

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.label(text=item.name, icon="DOT")
        row.label(text=item.module, icon="PLUGIN")


class AllPieUserActionItem(PropertyGroup):
    action_id: StringProperty()
    name: StringProperty()
    operator_id: StringProperty()
    description: StringProperty()
    usage_count: IntProperty(default=0, min=0)


class AllPieOperatorValidationItem(PropertyGroup):
    severity: StringProperty()
    location: StringProperty()
    message: StringProperty()


class ALLPIE_UL_user_actions(UIList):
    """Compact searchable list of presets added by the user."""

    def filter_items(self, context, data, property_name):
        items = getattr(data, property_name)
        visible = set(_matching_user_action_indices(data))
        flags = [
            self.bitflag_filter_item if index in visible else 0
            for index, _item in enumerate(items)
        ]
        return flags, []

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.label(text=item.name, icon="DOT")
        row.label(text=item.operator_id)
        usage = f"{item.usage_count} slot(s)" if item.usage_count else "Unused"
        row.label(text=usage, icon="CHECKMARK" if item.usage_count else "DOT")


class ALLPIE_OT_delete_user_action(Operator):
    """Delete a user-created preset and clear all slots that reference it."""

    bl_idname = "allpie.delete_user_action"
    bl_label = "Delete Added Action"
    bl_description = "Delete this custom action preset and clear any menu slots that use it"
    bl_options = {"INTERNAL"}

    action_id: StringProperty(options={"HIDDEN"})
    action_name: StringProperty(options={"HIDDEN"})
    usage_count: IntProperty(default=0, min=0, options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before deleting an action")
            return {"CANCELLED"}
        try:
            config = ConfigRuntime.get_config_copy()
            action = operator_data.get_operator(config, self.action_id)
            if not operator_data.is_user_defined_action(self.action_id, action, _get_bundled_action_ids()):
                self.report({"ERROR"}, "Bundled AllPie actions cannot be deleted")
                return {"CANCELLED"}
            self.action_name = str(action.get("name", self.action_id))
            self.usage_count = len(operator_data.get_operator_usages(config, self.action_id))
        except Exception as error:
            self.report({"ERROR"}, f"Could not inspect action: {error}")
            return {"CANCELLED"}
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Delete '{self.action_name}'?", icon="TRASH")
        if self.usage_count:
            layout.label(text=f"This will also clear {self.usage_count} assigned menu slot(s).", icon="INFO")
            layout.label(text="Other slots and menus will not be affected.")
        else:
            layout.label(text="This action is not currently assigned to a menu.")

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before deleting an action")
            return {"CANCELLED"}
        try:
            config = ConfigRuntime.get_config_copy()
            action = operator_data.get_operator(config, self.action_id)
            if not operator_data.is_user_defined_action(self.action_id, action, _get_bundled_action_ids()):
                raise ValueError("Bundled AllPie actions cannot be deleted")
            removed, usages = operator_data.remove_operator_and_unassign(config, self.action_id)
            ConfigRuntime.replace_and_save_configuration(config)
        except Exception as error:
            self.report({"ERROR"}, f"Could not delete action: {error}")
            return {"CANCELLED"}

        if prefs is not None:
            prefs.user_action_registry_generation = -1
            _ensure_user_action_items(prefs)
            prefs.editor_config_generation = -1
            if prefs.editor_active_menu_id:
                from . import menu_editor
                menu_editor._ensure_editor_state(prefs)
        self.report({"INFO"}, f"Deleted '{removed.get('name', self.action_id)}' and cleared {len(usages)} slot(s)")
        return {"FINISHED"}


class ALLPIE_OT_select_blender_operator(Operator):
    """Select a discovered Blender operator and create/reuse an AllPie preset."""

    bl_idname = "allpie.select_blender_operator"
    bl_label = "Add Blender Operator to AllPie"
    bl_description = "Add this Blender operator to the selected AllPie context"
    bl_options = {"INTERNAL"}

    operator_id: StringProperty(options={"HIDDEN"})
    description_text: StringProperty(options={"HIDDEN"})
    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, default=1, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    context_name: StringProperty(default="Object Mode", options={"HIDDEN"})

    @classmethod
    def description(cls, context, properties):
        """Use the selected Blender operator's RNA description for the button tooltip."""
        text = str(getattr(properties, "description_text", "") or "").strip()
        if text:
            return text
        operator_id = str(getattr(properties, "operator_id", "") or "")
        return f"Add {operator_id} to AllPie." if operator_id else "Add this Blender operator to AllPie."

    def execute(self, context):
        try:
            created = _add_operator_to_allpie(
                context,
                operator_id=self.operator_id,
                target_menu_id=self.target_menu_id,
                slot_number=self.slot_number,
                spaced=self.spaced,
                context_name=self.context_name or "Object Mode",
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not add Blender operator: {error}")
            return {"CANCELLED"}

        action = "Added" if created else "Reused"
        record = _OPERATOR_INFO.get(self.operator_id, {})
        label = record.get("name", self.operator_id)
        if self.target_menu_id:
            self.report({"INFO"}, f"{action} '{label}' in Slot {self.slot_number}")
        else:
            self.report({"INFO"}, f"{action} '{label}' to AllPie actions for {self.context_name}")
        return {"FINISHED"}


class ALLPIE_OT_search_blender_operator(Operator):
    """Open a searchable operator list with per-result hover descriptions."""

    bl_idname = "allpie.search_blender_operator"
    bl_label = "Search Blender Operators"
    bl_description = "Search Blender and installed addon operators; hover a result to read its description"
    bl_options = {"INTERNAL"}

    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, default=1, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    context_name: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before adding a Blender operator")
            return {"CANCELLED"}

        brush_only = False
        if self.target_menu_id:
            if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
                self.report({"ERROR"}, "The target menu is no longer selected")
                return {"CANCELLED"}
            try:
                config = ConfigRuntime.get_config_copy()
                menu = menu_data.get_menu(config, self.target_menu_id)
            except (RuntimeError, KeyError) as error:
                self.report({"ERROR"}, f"Could not read the target menu: {error}")
                return {"CANCELLED"}
            self.context_name = str(menu.get("keymap", "Object Mode"))
            brush_only = bool(menu.get("is_brush_menu", False))
        else:
            self.context_name = _context_from_preferences(prefs) if prefs is not None else "Object Mode"

        count = _ensure_operator_catalog()
        if not count:
            self.report({"WARNING"}, "No registered Blender operators were found")
            return {"CANCELLED"}
        if prefs is None:
            self.report({"ERROR"}, "AllPie preferences are unavailable")
            return {"CANCELLED"}

        _populate_search_items(prefs)
        prefs.operator_search_target_menu_id = self.target_menu_id
        prefs.operator_search_brush_only = brush_only
        matches = _matching_search_indices(prefs)
        prefs.operator_search_active_index = matches[0] if matches else 0
        prefs.operator_search_target_slot = self.slot_number
        prefs.operator_search_target_spaced = self.spaced
        prefs.operator_search_context_name = self.context_name
        return context.window_manager.invoke_popup(self, width=680)

    def draw(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None:
            self.layout.label(text="AllPie preferences are unavailable", icon="ERROR")
            return
        layout = self.layout
        layout.label(text=f"Add to {prefs.operator_search_context_name}", icon="ADD")
        layout.prop(
            prefs,
            "operator_search_query",
            text="",
            icon="VIEWZOOM",
            placeholder="Search names, operator IDs and descriptions",
        )
        layout.template_list(
            "ALLPIE_UL_operator_search_results",
            "allpie_operator_search_results",
            prefs,
            "operator_search_items",
            prefs,
            "operator_search_active_index",
            rows=12,
            maxrows=16,
            item_dyntip_propname="description",
        )
        matches = _matching_search_indices(prefs)
        index = prefs.operator_search_active_index
        if matches and index in matches:
            selected = prefs.operator_search_items[index]
            info = layout.box()
            info.label(text=selected.name, icon="INFO")
            info.label(text=selected.description or "No description is registered for this operator.")
            setup = layout.operator(
                "allpie.setup_blender_operator",
                text=f"Configure and Add {selected.name}",
                icon="ADD",
            )
            setup.operator_id = selected.operator_id
            # Blender may retain the last-used operator button properties.
            # Explicitly clear action_id so a new search result can never be
            # mistaken for an edit of a previously selected preset.
            setup.action_id = ""
            setup.create_new_action = True
            setup.invoke_operator = True
            setup.target_menu_id = prefs.operator_search_target_menu_id
            setup.slot_number = prefs.operator_search_target_slot
            setup.spaced = prefs.operator_search_target_spaced
            setup.context_name = prefs.operator_search_context_name
        else:
            layout.label(text="No operators match this search.", icon="INFO")
        layout.label(text="Hover a result for its description, select it, then configure its properties before adding.", icon="INFO")

    def execute(self, context):
        return {"FINISHED"}


class ALLPIE_OT_validate_operator_presets(Operator):
    """Check saved AllPie presets against Blender's currently registered RNA."""

    bl_idname = "allpie.validate_operator_presets"
    bl_label = "Validate Operator Presets"
    bl_description = "Check that saved operator presets and properties match this Blender installation"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None:
            self.report({"ERROR"}, "AllPie Preferences are unavailable")
            return {"CANCELLED"}
        from ..core.operator_validation import validate_configuration_operators

        try:
            config = ConfigRuntime.get_config_copy()
            issues = validate_configuration_operators(config)
            prefs.operator_validation_items.clear()
            for issue in issues:
                row = prefs.operator_validation_items.add()
                row.severity = issue.severity
                row.location = issue.path
                row.message = issue.message
            total_presets = len(config.get("Operators", {})) + sum(
                len(addon.get("Operators", {}))
                for addon in config.get("ThirdParty", {}).values()
                if isinstance(addon, Mapping) and addon.get("enabled", True)
            )
            prefs.operator_validation_summary = (
                f"{len(issues)} issue(s) found across {total_presets} enabled presets"
                if issues else f"All {total_presets} enabled presets passed RNA validation"
            )
            prefs.operator_validation_generation = ConfigRuntime.REGISTRY.generation
        except Exception as error:
            self.report({"ERROR"}, f"Could not validate operator presets: {error}")
            return {"CANCELLED"}

        if issues:
            error_count = sum(issue.severity == "error" for issue in issues)
            warning_count = len(issues) - error_count
            self.report({"WARNING"}, f"Found {error_count} error(s) and {warning_count} warning(s) in operator presets")
        else:
            self.report({"INFO"}, prefs.operator_validation_summary)
        return {"FINISHED"}


class ALLPIE_OT_refresh_operator_catalog(Operator):
    bl_idname = "allpie.refresh_operator_catalog"
    bl_label = "Refresh Blender Operator List"
    bl_description = "Rescan Blender and currently enabled addon operators"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        count = _refresh_operator_catalog()
        from . import operator_setup
        from ..core import operator_validation
        operator_setup.refresh_special_search_catalogs()
        operator_setup.unregister_dynamic_property_groups()
        operator_validation.clear_operator_rna_cache()
        prefs = _preferences_from_context(context)
        if prefs is not None:
            prefs.operator_search_catalog_generation = -1
        self.report({"INFO"}, f"Found {count} registered Blender and addon operators")
        return {"FINISHED"}


def draw_operator_editor(layout: Any, prefs: Any, context: Any) -> None:
    """Search Blender operators and manage only presets created by the user."""
    box = layout.box()
    box.label(text="Add Blender Operators", icon="VIEWZOOM")
    box.label(text="Search registered Blender and enabled-addon operators. Hover results for descriptions.")
    box.prop(prefs, "operator_search_context", text="Add to Context")
    row = box.row(align=True)
    row.scale_y = 1.5
    row.operator("allpie.search_blender_operator", text="Search Blender Operators", icon="VIEWZOOM")
    row.operator("allpie.refresh_operator_catalog", text="", icon="FILE_REFRESH")
    box.label(text="Some operators require a specific mode, selection or editor.", icon="INFO")
    preset_count = len(ConfigRuntime.REGISTRY.operators) if ConfigRuntime.INITIALIZED else 0
    box.separator()
    box.label(text=f"{preset_count} reusable AllPie action presets", icon="CHECKMARK")
    box.label(text="In Menus, use + beside a slot to search and assign an operator directly.", icon="INFO")
    if getattr(prefs, "operator_search_last_added", ""):
        box.separator()
        box.label(text=prefs.operator_search_last_added, icon="ADD")

    validation_box = layout.box()
    validation_header = validation_box.row(align=True)
    validation_header.label(text="Preset Validation", icon="CHECKMARK")
    validation_header.operator("allpie.validate_operator_presets", text="Validate Presets", icon="CHECKMARK")
    if prefs.operator_validation_generation == ConfigRuntime.REGISTRY.generation and prefs.operator_validation_summary:
        validation_box.label(text=prefs.operator_validation_summary)
        for issue in list(prefs.operator_validation_items)[:8]:
            icon = "ERROR" if issue.severity == "error" else "INFO"
            validation_box.label(text=f"{issue.location}: {issue.message}"[:180], icon=icon)
        if len(prefs.operator_validation_items) > 8:
            validation_box.label(text=f"And {len(prefs.operator_validation_items) - 8} more issue(s)…")
    elif prefs.operator_validation_summary:
        validation_box.label(text="Configuration changed; run validation again.", icon="INFO")
    else:
        validation_box.label(text="Check saved actions against Blender's registered operators and RNA properties.", icon="INFO")

    if ConfigRuntime.INITIALIZED:
        _ensure_user_action_items(prefs)
    actions_box = layout.box()
    actions_box.label(text=f"Your Added Actions ({len(prefs.user_action_items)})", icon="PREFERENCES")
    actions_box.label(text="Edit a saved action to correct its settings, or delete it when it is no longer needed.")
    actions_box.prop(prefs, "user_action_search", text="", icon="VIEWZOOM", placeholder="Search your added actions")
    actions_box.template_list(
        "ALLPIE_UL_user_actions",
        "allpie_user_actions",
        prefs,
        "user_action_items",
        prefs,
        "user_action_active_index",
        rows=5,
        maxrows=10,
        item_dyntip_propname="description",
    )
    selected_action_id = _selected_user_action_id(prefs)
    action_buttons = actions_box.row(align=True)
    action_buttons.enabled = bool(selected_action_id) and not prefs.editor_dirty
    edit = action_buttons.operator(
        "allpie.setup_blender_operator",
        text="Edit Settings",
        icon="PREFERENCES",
    )
    edit.action_id = selected_action_id
    edit.operator_id = ""
    edit.create_new_action = False
    delete = action_buttons.operator(
        "allpie.delete_user_action",
        text="Delete Action",
        icon="TRASH",
    )
    delete.action_id = selected_action_id
    if not prefs.user_action_items:
        actions_box.label(text="No user-added actions yet. Add one using Blender Operator Search.", icon="INFO")
    elif not selected_action_id:
        actions_box.label(text="Select an action to edit or delete it.", icon="INFO")
    if prefs.editor_dirty:
        actions_box.label(text="Apply or discard the menu draft before editing or deleting actions.", icon="INFO")


from . import operator_setup


CLASSES = (
    AllPieOperatorSearchItem,
    AllPieUserActionItem,
    AllPieOperatorValidationItem,
    ALLPIE_UL_operator_search_results,
    ALLPIE_UL_user_actions,
    ALLPIE_OT_delete_user_action,
    ALLPIE_OT_select_blender_operator,
    ALLPIE_OT_search_blender_operator,
    ALLPIE_OT_refresh_operator_catalog,
    ALLPIE_OT_validate_operator_presets,
    *operator_setup.CLASSES,
)
