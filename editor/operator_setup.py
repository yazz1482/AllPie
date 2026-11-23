"""RNA-driven operator setup dialogs for AllPie.

A Blender operator's RNA definition is converted into a temporary PropertyGroup
so users can configure operator arguments without hand-writing JSON. The
resulting JSON-compatible values are stored in the reusable AllPie preset.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)

from ..core import runtime as ConfigRuntime
from . import operator_data, operator_properties

OPERATOR_SETUP_API_VERSION = 5
_DRIVER_STATE_KEY = "_allpie_operator_setup_dynamic_groups_v2"
_LEGACY_DRIVER_STATE_KEY = "_allpie_operator_setup_dynamic_groups_v1"
_PANEL_SEARCH_CACHE = None
_MENU_SEARCH_CACHE = None


def _driver_state() -> dict:
    namespace = bpy.app.driver_namespace

    # Remove dynamic PropertyGroups created by the previous autocomplete-based
    # implementation. The new manual-ID StringProperty schema must be rebuilt;
    # otherwise Blender could keep the old search callback attached after an
    # in-place extension update.
    legacy_state = namespace.pop(_LEGACY_DRIVER_STATE_KEY, None)
    if isinstance(legacy_state, dict):
        for operator_id, entry in tuple(legacy_state.get("groups", {}).items()):
            try:
                _remove_dynamic_group(operator_id, entry)
            except Exception:
                pass

    state = namespace.get(_DRIVER_STATE_KEY)
    if not isinstance(state, dict):
        state = {"groups": {}}
        namespace[_DRIVER_STATE_KEY] = state
    state.setdefault("groups", {})
    return state


def _operator_rna(operator_id: str):
    if not operator_id or "." not in operator_id:
        raise ValueError(f"Invalid Blender operator identifier: {operator_id!r}")
    module_name, operator_name = operator_id.split(".", 1)
    try:
        operator = getattr(getattr(bpy.ops, module_name), operator_name)
        return operator.get_rna_type()
    except Exception as error:
        raise RuntimeError(f"Blender operator '{operator_id}' is not currently registered") from error


def _walk_subclasses(base_type):
    """Yield subclasses recursively; Blender panels/menus are nested by addon."""
    seen = set()
    stack = list(getattr(base_type, "__subclasses__", lambda: [])())
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        yield cls
        try:
            stack.extend(cls.__subclasses__())
        except Exception:
            pass


def _search_registered_types(base_type, edit_text: str):
    needle = str(edit_text or "").casefold().strip()
    results = []
    for cls in _walk_subclasses(base_type):
        identifier = str(getattr(cls, "bl_idname", "") or "").strip()
        label = str(getattr(cls, "bl_label", "") or identifier).strip()
        if not identifier:
            continue
        if needle and needle not in identifier.casefold() and needle not in label.casefold():
            continue
        results.append((identifier, label or identifier))
    results.sort(key=lambda item: (item[1].casefold(), item[0].casefold()))
    return results


def _panel_name_search(_self, _context, edit_text):
    """Provide the live panel-id search used by bpy.ops.wm.call_panel."""
    global _PANEL_SEARCH_CACHE
    if _PANEL_SEARCH_CACHE is None:
        _PANEL_SEARCH_CACHE = _search_registered_types(bpy.types.Panel, "")
    needle = str(edit_text or "").casefold().strip()
    if not needle:
        return _PANEL_SEARCH_CACHE
    return [item for item in _PANEL_SEARCH_CACHE if needle in item[0].casefold() or needle in item[1].casefold()]


def _menu_name_search(_self, _context, edit_text):
    """Provide a live menu-id search for wm.call_menu and wm.call_pie_menu."""
    global _MENU_SEARCH_CACHE
    if _MENU_SEARCH_CACHE is None:
        _MENU_SEARCH_CACHE = _search_registered_types(bpy.types.Menu, "")
    needle = str(edit_text or "").casefold().strip()
    if not needle:
        return _MENU_SEARCH_CACHE
    return [item for item in _MENU_SEARCH_CACHE if needle in item[0].casefold() or needle in item[1].casefold()]


def refresh_special_search_catalogs() -> None:
    global _PANEL_SEARCH_CACHE, _MENU_SEARCH_CACHE
    _PANEL_SEARCH_CACHE = None
    _MENU_SEARCH_CACHE = None


def _numeric_kwargs(spec: Mapping[str, Any], *, integer: bool = False) -> dict:
    kwargs = {}
    for source, target in (("hard_min", "min"), ("hard_max", "max"), ("soft_min", "soft_min"), ("soft_max", "soft_max")):
        value = spec.get(source)
        if value is None:
            continue
        try:
            kwargs[target] = int(value) if integer else float(value)
        except (TypeError, ValueError, OverflowError):
            pass
    return kwargs


def _safe_subtype(spec: Mapping[str, Any], *, vector: bool = False) -> str:
    subtype = str(spec.get("subtype", "NONE") or "NONE")
    allowed = {
        "NONE", "PIXEL", "UNSIGNED", "PERCENTAGE", "FACTOR", "ANGLE", "TIME",
        "DISTANCE", "DISTANCE_CAMERA", "POWER", "TEMPERATURE", "WAVELENGTH",
        "COLOR_TEMPERATURE", "FREQUENCY", "CAMERA", "LENGTH", "AREA", "VOLUME",
        "MASS", "VELOCITY", "ACCELERATION", "UNIT", "ROTATION", "XYZ",
        "XYZ_LENGTH", "XYZ_DISTANCE", "COLOR", "COLOR_GAMMA", "TRANSLATION",
        "DIRECTION", "EULER", "QUATERNION", "AXISANGLE",
    }
    return subtype if subtype in allowed else "NONE"


def _make_property_definition(spec: Mapping[str, Any], operator_id: str):
    identifier = str(spec["identifier"])
    label = str(spec.get("name") or identifier)
    description = str(spec.get("description") or "")
    kind = str(spec["type"])
    is_array = bool(spec.get("is_array"))
    common = {"name": label, "description": description}

    if kind == "BOOLEAN":
        if is_array:
            return BoolVectorProperty(
                **common,
                size=max(1, int(spec.get("array_length", 1))),
                default=tuple(bool(value) for value in spec.get("default", ())),
            )
        return BoolProperty(**common, default=bool(spec.get("default", False)))

    if kind == "INT":
        numeric = _numeric_kwargs(spec, integer=True)
        if is_array:
            return IntVectorProperty(
                **common,
                **numeric,
                size=max(1, int(spec.get("array_length", 1))),
                default=tuple(int(value) for value in spec.get("default", ())),
                subtype=_safe_subtype(spec, vector=True),
            )
        return IntProperty(
            **common,
            **numeric,
            default=int(spec.get("default", 0)),
            subtype=_safe_subtype(spec),
        )

    if kind == "FLOAT":
        numeric = _numeric_kwargs(spec)
        unit = str(spec.get("unit", "NONE") or "NONE")
        if unit in {"NONE", "LENGTH", "AREA", "VOLUME", "ROTATION", "TIME", "VELOCITY", "ACCELERATION", "MASS", "CAMERA", "POWER", "TEMPERATURE", "WAVELENGTH", "COLOR_TEMPERATURE", "FREQUENCY"}:
            numeric["unit"] = unit
        if is_array:
            return FloatVectorProperty(
                **common,
                **numeric,
                size=max(1, int(spec.get("array_length", 1))),
                default=tuple(float(value) for value in spec.get("default", ())),
                subtype=_safe_subtype(spec, vector=True),
            )
        return FloatProperty(
            **common,
            **numeric,
            default=float(spec.get("default", 0.0)),
            subtype=_safe_subtype(spec),
        )

    if kind == "STRING":
        kwargs = dict(common)
        maxlen = int(spec.get("maxlen", 0) or 0)
        if maxlen > 0:
            kwargs["maxlen"] = maxlen

        # Do not attach Blender's StringProperty search callback to these ID
        # fields. In Blender's search widget, pressing Enter with a value that
        # has no matching result can commit the previously highlighted result
        # instead of the text the user typed. Panel/menu IDs must remain freely
        # editable, including identifiers from addons that aren't discoverable
        # through Python subclass enumeration.
        if spec.get("panel_name_search"):
            kwargs["description"] = (
                f"{description} Enter the panel bl_idname directly; manual identifiers "
                "are accepted even when they are not in the registered panel list."
            ).strip()
        elif operator_id in {"wm.call_menu", "wm.call_menu_pie"} and identifier == "name":
            kwargs["description"] = (
                f"{description} Enter the menu bl_idname directly; manual identifiers "
                "are accepted even when they are not in the registered menu list."
            ).strip()
        return StringProperty(**kwargs, default=str(spec.get("default", "") or ""))

    if kind == "ENUM":
        items = tuple(
            (str(item["identifier"]), str(item["name"]), str(item.get("description", "")))
            for item in spec.get("enum_items", ())
        )
        if not items:
            raise ValueError(f"Enum property '{identifier}' has no static RNA items")
        options = {"ENUM_FLAG"} if spec.get("enum_flag") else set()
        default = spec.get("default")
        if spec.get("enum_flag"):
            default = set(default or ())
        return EnumProperty(
            **common,
            items=items,
            default=default,
            options=options,
        )

    raise TypeError(f"Unsupported RNA property type '{kind}' for {identifier}")


def _schema_signature(specs: Mapping[str, Any]) -> str:
    return json.dumps(specs, sort_keys=True, separators=(",", ":"), default=str)


def _remove_dynamic_group(operator_id: str, entry: Mapping[str, Any]) -> None:
    attr = entry.get("pointer_attr", "")
    cls = entry.get("class")
    if attr and hasattr(bpy.types.WindowManager, attr):
        try:
            delattr(bpy.types.WindowManager, attr)
        except Exception:
            pass
    if cls is not None:
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


def _ensure_dynamic_group(operator_id: str) -> dict:
    """Return a cached dynamic RNA group, creating it only once per operator."""
    state = _driver_state()
    groups = state["groups"]
    cached = groups.get(operator_id)
    if cached and hasattr(bpy.types.WindowManager, cached.get("pointer_attr", "")):
        return cached
    if cached:
        _remove_dynamic_group(operator_id, cached)
        groups.pop(operator_id, None)

    rna = _operator_rna(operator_id)
    schema = operator_properties.build_property_specs(operator_id, rna.properties)

    digest = hashlib.sha1(operator_id.encode("utf-8")).hexdigest()[:12]
    class_name = f"ALLPIE_PG_OperatorSetup_{digest}"
    pointer_attr = f"allpie_operator_setup_{digest}"

    # Clean up a stale definition left behind by an in-place extension reload.
    old_class = getattr(bpy.types, class_name, None)
    if old_class is not None or hasattr(bpy.types.WindowManager, pointer_attr):
        stale_entry = {"class": old_class, "pointer_attr": pointer_attr}
        _remove_dynamic_group(operator_id, stale_entry)

    annotations = {}
    property_specs = schema["properties"]
    for spec in property_specs:
        identifier = spec["identifier"]
        try:
            annotations[identifier] = _make_property_definition(spec, operator_id)
        except Exception as error:
            schema["unsupported"].append({
                "identifier": identifier,
                "name": spec.get("name", identifier),
                "description": spec.get("description", ""),
                "type": spec.get("type", ""),
                "required": bool(spec.get("required")),
                "reason": f"Could not create a Blender UI control: {error}",
            })
    schema["properties"] = [spec for spec in property_specs if spec["identifier"] in annotations]
    schema["required_unsupported"] = [item for item in schema["unsupported"] if item.get("required")]

    dynamic_class = type(
        class_name,
        (PropertyGroup,),
        {
            "__annotations__": annotations,
            "__module__": __name__,
        },
    )
    bpy.utils.register_class(dynamic_class)
    try:
        setattr(bpy.types.WindowManager, pointer_attr, PointerProperty(type=dynamic_class))
    except Exception:
        try:
            bpy.utils.unregister_class(dynamic_class)
        except Exception:
            pass
        raise

    entry = {
        "class": dynamic_class,
        "pointer_attr": pointer_attr,
        "schema": schema,
    }
    groups[operator_id] = entry
    return entry


def _get_setup_group(context: Any, operator_id: str):
    entry = _ensure_dynamic_group(operator_id)
    return getattr(context.window_manager, entry["pointer_attr"]), entry


def _normalize_initial_value(spec: Mapping[str, Any], value: Any) -> Any:
    if spec.get("enum_flag"):
        if isinstance(value, str):
            return {value}
        return set(value or ())
    if spec.get("is_array"):
        return tuple(value or ())
    return value


def _populate_group(group: Any, schema: Mapping[str, Any], values: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    """Reset and populate the temporary RNA group without hiding stale values.

    A dynamic PropertyGroup is reused between dialogs. Resetting every field
    first prevents the previous operator's values from leaking into a new
    preset. Values that no longer fit the current RNA definition are returned
    to the caller so the dialog can require an explicit user decision.
    """
    supplied = values or {}
    issues: list[dict[str, str]] = []
    for spec in schema.get("properties", ()):
        identifier = spec["identifier"]
        default_value = spec.get("default")
        try:
            if default_value is not None:
                setattr(group, identifier, _normalize_initial_value(spec, default_value))
        except Exception as error:
            issues.append({
                "identifier": identifier,
                "name": str(spec.get("name") or identifier),
                "message": f"Could not initialize the current Blender default: {error}",
            })
            continue

        if identifier not in supplied:
            continue
        value = supplied[identifier]
        try:
            setattr(group, identifier, _normalize_initial_value(spec, value))
        except Exception as error:
            issues.append({
                "identifier": identifier,
                "name": str(spec.get("name") or identifier),
                "message": f"Saved value {value!r} is no longer valid: {error}",
            })
    return issues


def _collect_group_values(group: Any, schema: Mapping[str, Any]) -> dict:
    values = {}
    for spec in schema.get("properties", ()):
        identifier = spec["identifier"]
        try:
            values[identifier] = operator_properties.json_safe_value(getattr(group, identifier))
        except Exception as error:
            raise ValueError(f"Could not read operator property '{spec.get('name', identifier)}': {error}") from error
    missing = operator_properties.validate_required_values(schema.get("properties", ()), values)
    if missing:
        raise ValueError("Set the required operator properties: " + ", ".join(missing))
    required_unsupported = schema.get("required_unsupported", ())
    if required_unsupported:
        names = ", ".join(item.get("name", item.get("identifier", "property")) for item in required_unsupported)
        raise ValueError("This operator has required properties AllPie cannot configure yet: " + names)
    return values


def _draw_property_group(
    layout: Any,
    group: Any,
    schema: Mapping[str, Any],
    operator_id: str = "",
) -> None:
    properties = schema.get("properties", ())
    if not properties:
        layout.label(text="This operator has no supported configurable properties.", icon="INFO")
    for spec in properties:
        identifier = spec["identifier"]
        is_panel_id = operator_id == "wm.call_panel" and identifier == "name"
        is_menu_id = operator_id in {"wm.call_menu", "wm.call_menu_pie"} and identifier == "name"
        row = layout.row()
        label = "Panel ID" if is_panel_id else "Menu ID" if is_menu_id else spec.get("name", identifier)
        row.prop(group, identifier, text=label)
        if is_panel_id:
            layout.label(
                text="Enter the exact panel bl_idname manually (for example, VIEW3D_PT_overlay).",
                icon="INFO",
            )
            layout.label(text="Manual IDs are accepted even when they do not appear in the registered list.")
        elif is_menu_id:
            layout.label(text="Enter the exact menu bl_idname manually; it does not need to appear in a search list.", icon="INFO")

    unsupported = schema.get("unsupported", ())
    if unsupported:
        box = layout.box()
        box.label(text=f"{len(unsupported)} advanced RNA propert(ies) are not exposed", icon="INFO")
        box.label(text="These values keep their Blender defaults for new presets.")
        for item in unsupported[:6]:
            box.label(text=f"{item.get('name', item.get('identifier', 'Property'))}: {item.get('reason', 'Unsupported')}")
        if len(unsupported) > 6:
            box.label(text=f"And {len(unsupported) - 6} more...")


class ALLPIE_OT_setup_blender_operator(Operator):
    """Configure RNA properties, then create or update an AllPie action preset."""

    bl_idname = "allpie.setup_blender_operator"
    bl_label = "Configure Blender Operator"
    bl_description = "Configure this Blender operator's properties before adding it to AllPie"
    bl_options = {"INTERNAL"}

    operator_id: StringProperty(options={"HIDDEN"})
    action_id: StringProperty(options={"HIDDEN"})
    # Explicitly distinguish a fresh search result from editing a saved preset.
    # Blender can retain the previous button/operator properties between calls.
    create_new_action: BoolProperty(default=False, options={"HIDDEN"})
    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, default=1, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    context_name: StringProperty(default="Object Mode", options={"HIDDEN"})
    invoke_operator: BoolProperty(name="Invoke Operator", description="Use Blender's invoke context instead of direct execution", default=True)
    invalid_saved_values: StringProperty(options={"HIDDEN"})
    replace_invalid_saved_values: BoolProperty(
        name="Replace invalid saved values with current Blender defaults",
        description="Explicitly discard saved property values that no longer match this Blender operator",
        default=False,
    )
    unknown_saved_properties: StringProperty(options={"HIDDEN"})
    remove_unknown_saved_properties: BoolProperty(
        name="Remove properties not recognized by this Blender version",
        description="Remove obsolete property keys from this preset when saving",
        default=False,
    )

    def invoke(self, context, event):
        from . import menu_editor
        prefs = _preferences_from_context(context)
        if self.create_new_action:
            # Do not allow Blender's last-used action_id to redirect a new
            # operator search result into the edit-existing-preset path.
            self.action_id = ""
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard menu changes before configuring an operator")
            return {"CANCELLED"}

        initial_values = {}
        self.invalid_saved_values = "[]"
        self.unknown_saved_properties = "[]"
        self.replace_invalid_saved_values = False
        self.remove_unknown_saved_properties = False
        if self.action_id and not self.create_new_action:
            try:
                config = ConfigRuntime.get_config_copy()
                action = operator_data.get_operator(config, self.action_id)
            except (RuntimeError, KeyError) as error:
                # Blender can retain the last-used values for an operator button.
                # A newly-added operator search result explicitly supplies
                # operator_id but has no preset yet. If a stale action_id leaks
                # into that button, recover as a new-preset flow instead of
                # trying to edit a preset that does not exist.
                if self.operator_id:
                    self.report(
                        {"WARNING"},
                        f"A stale preset reference was ignored; creating a new preset for {self.operator_id}.",
                    )
                    self.action_id = ""
                    initial_values = {}
                else:
                    self.report({"ERROR"}, f"Could not read the selected action: {error}")
                    return {"CANCELLED"}
            else:
                if ":" in self.action_id:
                    self.report({"ERROR"}, "Third-party presets are read-only. Duplicate them before editing.")
                    return {"CANCELLED"}
                self.operator_id = str(action.get("operator_id", ""))
                initial_values = action.get("properties", {})
                self.invoke_operator = bool(action.get("invoke", True))
                if self.target_menu_id and prefs is not None and prefs.editor_active_menu_id != self.target_menu_id:
                    self.report({"ERROR"}, "The target menu is no longer selected")
                    return {"CANCELLED"}
        if not self.action_id and self.target_menu_id:
            if prefs is None or prefs.editor_active_menu_id != self.target_menu_id:
                self.report({"ERROR"}, "The target menu is no longer selected")
                return {"CANCELLED"}
            try:
                menu = menu_editor.menu_data.get_menu(ConfigRuntime.get_config_copy(), self.target_menu_id)
            except (RuntimeError, KeyError) as error:
                self.report({"ERROR"}, f"Could not read the target menu: {error}")
                return {"CANCELLED"}
            self.context_name = str(menu.get("keymap", self.context_name))
        if not self.operator_id:
            self.report({"ERROR"}, "No Blender operator was selected")
            return {"CANCELLED"}

        try:
            group, entry = _get_setup_group(context, self.operator_id)
            population_issues = _populate_group(group, entry["schema"], initial_values)
            self.invalid_saved_values = json.dumps(population_issues)
            supported_names = {spec["identifier"] for spec in entry["schema"].get("properties", ())}
            unknown_names = sorted(set(initial_values) - supported_names)
            self.unknown_saved_properties = json.dumps(unknown_names)
        except Exception as error:
            self.report({"ERROR"}, f"Could not inspect operator properties: {error}")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        layout = self.layout
        try:
            group, entry = _get_setup_group(context, self.operator_id)
        except Exception as error:
            layout.label(text=f"Could not load operator properties: {error}", icon="ERROR")
            return

        rna = _operator_rna(self.operator_id)
        layout.label(text=str(getattr(rna, "name", "") or self.operator_id), icon="PREFERENCES")
        description = str(getattr(rna, "description", "") or "").strip()
        if description:
            layout.label(text=description)
        layout.separator()
        _draw_property_group(layout, group, entry["schema"], self.operator_id)
        layout.separator()
        layout.prop(self, "invoke_operator")
        try:
            invalid_values = json.loads(self.invalid_saved_values or "[]")
        except Exception:
            invalid_values = []
        if invalid_values:
            warning = layout.box()
            warning.alert = True
            warning.label(text="Some saved values no longer match this Blender operator:", icon="ERROR")
            for issue in invalid_values[:5]:
                warning.label(text=f"{issue.get('name', issue.get('identifier', 'Property'))}: {issue.get('message', 'Invalid saved value')}")
            if len(invalid_values) > 5:
                warning.label(text=f"And {len(invalid_values) - 5} more…")
            warning.prop(self, "replace_invalid_saved_values")
        try:
            unknown_values = json.loads(self.unknown_saved_properties or "[]")
        except Exception:
            unknown_values = []
        if unknown_values:
            warning = layout.box()
            warning.label(text="Saved properties not exposed by this Blender version:", icon="INFO")
            warning.label(text=", ".join(unknown_values[:6]))
            warning.prop(self, "remove_unknown_saved_properties")
        if self.action_id and not self.create_new_action:
            layout.label(text="Editing a shared preset updates every menu slot that uses it.", icon="INFO")
        elif self.target_menu_id:
            layout.label(text=f"Will assign to Slot {self.slot_number}.", icon="INFO")
        else:
            layout.label(text=f"Will create an action preset for {self.context_name}.", icon="INFO")

    def execute(self, context):
        try:
            try:
                invalid_values = json.loads(self.invalid_saved_values or "[]")
                unknown_values = json.loads(self.unknown_saved_properties or "[]")
            except Exception:
                invalid_values = []
                unknown_values = []
            if invalid_values and not self.replace_invalid_saved_values:
                self.report({"ERROR"}, "Review invalid saved values and explicitly choose whether to replace them with Blender defaults")
                return {"CANCELLED"}
            if unknown_values and not self.remove_unknown_saved_properties:
                self.report({"ERROR"}, "This preset contains properties unknown to the current Blender version. Choose whether to remove them before saving")
                return {"CANCELLED"}

            group, entry = _get_setup_group(context, self.operator_id)
            edited_values = _collect_group_values(group, entry["schema"])
            from ..core.operator_validation import validate_operator_preset
            validation = validate_operator_preset(self.operator_id, edited_values, check_poll=False)
            if validation.errors:
                details = "; ".join(
                    f"{issue.path}: {issue.message}" for issue in validation.errors[:3]
                )
                self.report({"ERROR"}, f"Operator properties are invalid: {details}")
                return {"CANCELLED"}
            if self.action_id and not self.create_new_action:
                config = ConfigRuntime.get_config_copy()
                action = operator_data.get_operator(config, self.action_id)
                previous_properties = dict(action.get("properties", {}))
                updated_properties = operator_properties.merge_configured_values(
                    previous_properties, edited_values
                )
                if unknown_values and self.remove_unknown_saved_properties:
                    for property_name in unknown_values:
                        updated_properties.pop(property_name, None)

                # Keep generated labels in sync with parameterized operator
                # presets (e.g. changing Add Subdivision Modifier to Add Mirror
                # Modifier). Preserve labels that the user has customized.
                rna = _operator_rna(self.operator_id)
                previous_generated_name = _configured_preset_name(
                    self.operator_id, rna, previous_properties, entry["schema"]
                )
                updated_generated_name = _configured_preset_name(
                    self.operator_id, rna, updated_properties, entry["schema"]
                )
                if str(action.get("name", "")) == previous_generated_name:
                    action["name"] = updated_generated_name
                if str(action.get("search_name", action.get("name", ""))) == previous_generated_name:
                    action["search_name"] = updated_generated_name

                action["properties"] = updated_properties
                action["invoke"] = bool(self.invoke_operator)
                ConfigRuntime.replace_and_save_configuration(config)
                prefs = _preferences_from_context(context)
                if prefs is not None:
                    prefs.editor_config_generation = -1
                    if prefs.editor_active_menu_id:
                        from . import menu_editor
                        menu_editor._ensure_editor_state(prefs)
                self.report({"INFO"}, f"Updated operator preset '{self.action_id}'")
                return {"FINISHED"}

            from . import operator_editor
            rna = _operator_rna(self.operator_id)
            preset_name = _configured_preset_name(self.operator_id, rna, edited_values, entry["schema"])
            created = operator_editor._add_operator_to_allpie(
                context,
                operator_id=self.operator_id,
                target_menu_id=self.target_menu_id,
                slot_number=self.slot_number,
                spaced=self.spaced,
                context_name=self.context_name or "Object Mode",
                properties=edited_values,
                invoke=bool(self.invoke_operator),
                name_override=preset_name,
                search_name=preset_name,
            )
            state = "Added" if created else "Reused"
            self.report({"INFO"}, f"{state} '{self.operator_id}'")
        except Exception as error:
            self.report({"ERROR"}, f"Could not save operator preset: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}




def _configured_preset_name(operator_id: str, rna: Any, values: Mapping[str, Any], schema: Mapping[str, Any]) -> str:
    """Create a useful slot label for common parameterized Blender operators."""
    base_name = str(getattr(rna, "name", "") or operator_id).strip()
    specs = {spec["identifier"]: spec for spec in schema.get("properties", ())}

    if operator_id == "object.modifier_add" and values.get("type"):
        modifier_type = str(values["type"])
        type_spec = specs.get("type", {})
        type_label = next(
            (item["name"] for item in type_spec.get("enum_items", ()) if item["identifier"] == modifier_type),
            modifier_type.replace("_", " ").title(),
        )
        return f"Add {type_label} Modifier"

    if operator_id == "wm.call_panel" and values.get("name"):
        panel_id = str(values["name"])
        panel_items = _PANEL_SEARCH_CACHE
        if panel_items is None:
            panel_items = _panel_name_search(None, None, "")
        panel_label = next((label for identifier, label in panel_items if identifier == panel_id), panel_id)
        return f"Call Panel: {panel_label}"

    if operator_id in {"wm.call_menu", "wm.call_menu_pie"} and values.get("name"):
        menu_id = str(values["name"])
        menu_items = _MENU_SEARCH_CACHE
        if menu_items is None:
            menu_items = _menu_name_search(None, None, "")
        menu_label = next((label for identifier, label in menu_items if identifier == menu_id), menu_id)
        return f"Call Menu: {menu_label}"

    return base_name


def _preferences_from_context(context: Any) -> Any:
    from .. import Preferences
    addon = context.preferences.addons.get(Preferences.__package__)
    return addon.preferences if addon is not None else None


def unregister_dynamic_property_groups() -> None:
    """Remove temporary RNA groups before AllPie unregisters its static classes."""
    try:
        state = _driver_state()
    except Exception:
        return
    for operator_id, entry in tuple(state.get("groups", {}).items()):
        _remove_dynamic_group(operator_id, entry)
    state["groups"].clear()


CLASSES = (
    ALLPIE_OT_setup_blender_operator,
)
