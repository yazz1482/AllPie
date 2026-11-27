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
from . import menu_data, operator_data, operator_properties

OPERATOR_SETUP_API_VERSION = 25
_DRIVER_STATE_KEY = "_allpie_operator_setup_dynamic_groups_v2"
_LEGACY_DRIVER_STATE_KEY = "_allpie_operator_setup_dynamic_groups_v1"
_PANEL_SEARCH_CACHE = None
_MENU_SEARCH_CACHE = None
_PANEL_ID_PICKER_ITEMS = None
_MENU_ID_PICKER_ITEMS = None


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
    """Yield Python subclasses recursively as a secondary discovery source."""
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


def _ui_type_identifier(cls) -> str:
    """Return the registered RNA identifier for a Panel/Menu class."""
    try:
        identifier = str(getattr(cls, "bl_idname", "") or "").strip()
        if identifier:
            return identifier
        class_rna = getattr(cls, "bl_rna", None)
        return str(getattr(class_rna, "identifier", "") or "").strip()
    except Exception:
        return ""


def _registered_python_subclass(base_type, cls, *, from_bpy_types: bool = False):
    """Resolve a candidate to its registered Python RNA class.

    Blender exposes registered extension types through ``bpy.types`` using
    their RNA identifier. Walking ``__subclasses__`` alone is incomplete for
    some registered UI types, while walking it without validation also picks
    up Python classes that have never been registered. Use both sources and
    verify each candidate against the base type's RNA subclass registry.
    """
    try:
        identifiers = []
        bl_idname = _ui_type_identifier(cls)
        if bl_idname:
            identifiers.append(bl_idname)
        class_rna = getattr(cls, "bl_rna", None)
        rna_identifier = str(getattr(class_rna, "identifier", "") or "").strip()
        if rna_identifier and rna_identifier not in identifiers:
            identifiers.append(rna_identifier)
    except Exception:
        return None
    if not identifiers:
        return None

    try:
        lookup = getattr(base_type, "bl_rna_get_subclass_py", None)
    except Exception:
        lookup = None
    if callable(lookup):
        for identifier in identifiers:
            try:
                registered = lookup(identifier, None)
            except TypeError:
                try:
                    registered = lookup(identifier)
                except Exception:
                    registered = None
            except Exception:
                registered = None
            if registered is not None:
                try:
                    if issubclass(registered, base_type):
                        return registered
                except TypeError:
                    pass
        # bpy.types is Blender's public registered-type namespace. Trust a
        # class found there if an RNA build exposes it under a nonstandard
        # lookup identifier. Subclass-only candidates still require a match.
        return cls if from_bpy_types else None

    # Compatibility fallback for Blender builds without the Python lookup.
    # Classes obtained from bpy.types are registered by definition; for the
    # subclass fallback, require a distinct class-level RNA definition.
    if from_bpy_types:
        return cls
    try:
        class_rna = cls.__dict__.get("bl_rna")
        base_rna = getattr(base_type, "bl_rna", None)
        if class_rna is not None and class_rna is not base_rna:
            return cls
    except Exception:
        pass
    return None


def _iter_registered_ui_types(base_type):
    """Yield registered Panel/Menu Python classes from all available sources."""
    found = {}
    bpy_types = getattr(bpy, "types", None)

    # Primary source: Blender's public registered-type namespace. Add-on
    # classes are exposed here under their bl_idname, not necessarily their
    # original Python class name.
    if bpy_types is not None:
        for attribute_name in dir(bpy_types):
            try:
                cls = getattr(bpy_types, attribute_name)
                if not isinstance(cls, type) or cls is base_type:
                    continue
                if not issubclass(cls, base_type):
                    continue
            except Exception:
                continue
            registered = _registered_python_subclass(
                base_type, cls, from_bpy_types=True
            )
            if registered is None:
                continue
            identifier = _ui_type_identifier(registered)
            if identifier:
                found[identifier] = registered

    # Secondary source: recursive subclass discovery catches registered
    # classes that are not exposed as ordinary attributes on bpy.types in
    # some Blender versions/add-on registration patterns. RNA lookup filters
    # out unregistered Python subclasses.
    for cls in _walk_subclasses(base_type):
        try:
            registered = _registered_python_subclass(base_type, cls)
        except Exception:
            continue
        if registered is None:
            continue
        identifier = _ui_type_identifier(registered)
        if identifier:
            found[identifier] = registered

    return tuple(found.values())


def _search_registered_types(base_type, edit_text: str):
    needle = str(edit_text or "").casefold().strip()
    results = []
    for cls in _iter_registered_ui_types(base_type):
        identifier = _ui_type_identifier(cls)
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
    global _PANEL_ID_PICKER_ITEMS, _MENU_ID_PICKER_ITEMS
    _PANEL_SEARCH_CACHE = None
    _MENU_SEARCH_CACHE = None
    _PANEL_ID_PICKER_ITEMS = None
    _MENU_ID_PICKER_ITEMS = None


def _panel_id_picker_items(_self, _context):
    """Keep a stable enum-item list for Blender's searchable ID picker."""
    global _PANEL_SEARCH_CACHE, _PANEL_ID_PICKER_ITEMS
    if _PANEL_SEARCH_CACHE is None:
        _PANEL_SEARCH_CACHE = _search_registered_types(bpy.types.Panel, "")
    if _PANEL_ID_PICKER_ITEMS is None:
        _PANEL_ID_PICKER_ITEMS = [
            (identifier, f"{label} ({identifier})", f"Copy {identifier} to the clipboard")
            for identifier, label in _PANEL_SEARCH_CACHE
        ]
    return _PANEL_ID_PICKER_ITEMS


def _menu_id_picker_items(_self, _context):
    """Keep a stable enum-item list for Blender's searchable ID picker."""
    global _MENU_SEARCH_CACHE, _MENU_ID_PICKER_ITEMS
    if _MENU_SEARCH_CACHE is None:
        _MENU_SEARCH_CACHE = _search_registered_types(bpy.types.Menu, "")
    if _MENU_ID_PICKER_ITEMS is None:
        _MENU_ID_PICKER_ITEMS = [
            (identifier, f"{label} ({identifier})", f"Copy {identifier} to the clipboard")
            for identifier, label in _MENU_SEARCH_CACHE
        ]
    return _MENU_ID_PICKER_ITEMS


class ALLPIE_OT_copy_panel_id(Operator):
    """Search registered Blender panels and copy the selected panel ID."""

    bl_idname = "allpie.copy_panel_id"
    bl_label = "Copy Panel ID"
    bl_description = "Search registered Blender panels and copy the selected bl_idname"
    bl_property = "panel_id"

    panel_id: EnumProperty(name="Panel", items=_panel_id_picker_items)

    def invoke(self, context, event):
        refresh_special_search_catalogs()
        items = _panel_id_picker_items(self, context)
        if not items:
            self.report({"WARNING"}, "No registered Blender panels were found")
            return {"CANCELLED"}
        self.panel_id = items[0][0]
        # invoke_search_popup() is a fire-and-forget WindowManager API in
        # Blender: it returns None. The operator invoke callback must return
        # a valid operator status set itself.
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        identifier = str(self.panel_id or "").strip()
        if not identifier:
            self.report({"WARNING"}, "No panel ID was selected")
            return {"CANCELLED"}
        try:
            context.window_manager.clipboard = identifier
        except Exception as error:
            self.report({"ERROR"}, f"Could not copy panel ID: {error}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Copied panel ID: {identifier}")
        return {"FINISHED"}


class ALLPIE_OT_copy_menu_id(Operator):
    """Search registered Blender menus and copy the selected menu ID."""

    bl_idname = "allpie.copy_menu_id"
    bl_label = "Copy Menu ID"
    bl_description = "Search registered Blender menus and copy the selected bl_idname"
    bl_property = "menu_id"

    menu_id: EnumProperty(name="Menu", items=_menu_id_picker_items)

    def invoke(self, context, event):
        refresh_special_search_catalogs()
        items = _menu_id_picker_items(self, context)
        if not items:
            self.report({"WARNING"}, "No registered Blender menus were found")
            return {"CANCELLED"}
        self.menu_id = items[0][0]
        # See the panel picker above: invoke_search_popup() does not return
        # an operator status set. Keep the popup running explicitly.
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        identifier = str(self.menu_id or "").strip()
        if not identifier:
            self.report({"WARNING"}, "No menu ID was selected")
            return {"CANCELLED"}
        try:
            context.window_manager.clipboard = identifier
        except Exception as error:
            self.report({"ERROR"}, f"Could not copy menu ID: {error}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Copied menu ID: {identifier}")
        return {"FINISHED"}


class ALLPIE_OT_browse_panel_id(Operator):
    """Choose a registered Panel ID and write it into an operator setup field."""

    bl_idname = "allpie.browse_panel_id"
    bl_label = "Browse Panel IDs"
    bl_description = "Choose a registered Blender panel and fill its bl_idname into this field"
    bl_property = "panel_id"

    panel_id: EnumProperty(name="Panel", items=_panel_id_picker_items)
    target_group_attr: StringProperty(options={"HIDDEN"})
    target_property: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        refresh_special_search_catalogs()
        items = _panel_id_picker_items(self, context)
        if not items:
            self.report({"WARNING"}, "No registered Blender panels were found")
            return {"CANCELLED"}
        self.panel_id = items[0][0]
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        identifier = str(self.panel_id or "").strip()
        if not identifier:
            self.report({"WARNING"}, "No panel ID was selected")
            return {"CANCELLED"}
        try:
            group = getattr(context.window_manager, self.target_group_attr)
            if not self.target_property or not hasattr(group, self.target_property):
                raise AttributeError(f"Operator setup field '{self.target_property}' is no longer available")
            setattr(group, self.target_property, identifier)
        except Exception as error:
            self.report({"ERROR"}, f"Could not set the Panel ID field: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class ALLPIE_OT_browse_menu_id(Operator):
    """Choose a registered Menu ID and write it into an operator setup field."""

    bl_idname = "allpie.browse_menu_id"
    bl_label = "Browse Menu IDs"
    bl_description = "Choose a registered Blender menu and fill its bl_idname into this field"
    bl_property = "menu_id"

    menu_id: EnumProperty(name="Menu", items=_menu_id_picker_items)
    target_group_attr: StringProperty(options={"HIDDEN"})
    target_property: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        refresh_special_search_catalogs()
        items = _menu_id_picker_items(self, context)
        if not items:
            self.report({"WARNING"}, "No registered Blender menus were found")
            return {"CANCELLED"}
        self.menu_id = items[0][0]
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        identifier = str(self.menu_id or "").strip()
        if not identifier:
            self.report({"WARNING"}, "No menu ID was selected")
            return {"CANCELLED"}
        try:
            group = getattr(context.window_manager, self.target_group_attr)
            if not self.target_property or not hasattr(group, self.target_property):
                raise AttributeError(f"Operator setup field '{self.target_property}' is no longer available")
            setattr(group, self.target_property, identifier)
        except Exception as error:
            self.report({"ERROR"}, f"Could not set the Menu ID field: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


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
    group_attr: str = "",
) -> None:
    properties = schema.get("properties", ())
    if not properties:
        layout.label(text="This operator has no supported configurable properties.", icon="INFO")
    for spec in properties:
        if spec.get("ui_hidden"):
            continue
        identifier = spec["identifier"]
        is_panel_id = operator_id == "wm.call_panel" and identifier == "name"
        is_menu_id = operator_id in {"wm.call_menu", "wm.call_menu_pie"} and identifier == "name"
        is_tool_target_space = operator_id == "wm.tool_set_by_id" and identifier == "space_type"
        row = layout.row()
        label = (
            "Panel ID" if is_panel_id else
            "Menu ID" if is_menu_id else
            "Target Editor" if is_tool_target_space else
            spec.get("name", identifier)
        )
        row.prop(group, identifier, text=label)
        if is_panel_id:
            browse = row.operator(
                "allpie.browse_panel_id",
                text="",
                icon="VIEWZOOM",
                emboss=True,
            )
            browse.target_group_attr = group_attr
            browse.target_property = identifier
        elif is_menu_id:
            browse = row.operator(
                "allpie.browse_menu_id",
                text="",
                icon="VIEWZOOM",
                emboss=True,
            )
            browse.target_group_attr = group_attr
            browse.target_property = identifier
        if is_tool_target_space:
            layout.label(
                text="Controls where Blender activates the tool; it does not control which AllPie menu context lists this preset.",
                icon="INFO",
            )
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
    bl_label = "Configure Operator Preset"
    bl_description = "Configure a reusable AllPie operator preset"
    bl_options = {"INTERNAL"}

    operator_id: StringProperty(options={"HIDDEN"})
    action_id: StringProperty(options={"HIDDEN"})
    preset_name: StringProperty(
        name="Preset Name",
        description="Name shown in AllPie's operator list. Give different operator settings distinct names.",
        default="",
        maxlen=64,
    )
    # Explicitly distinguish a fresh search result from editing a saved preset.
    # Blender can retain the previous button/operator properties between calls.
    create_new_action: BoolProperty(default=False, options={"HIDDEN"})
    source_action_id: StringProperty(default="", options={"HIDDEN"})
    prefill_from_action: BoolProperty(default=False, options={"HIDDEN"})
    expose_preset_name: BoolProperty(default=False, options={"HIDDEN"})
    source_contexts_json: StringProperty(default="[]", options={"HIDDEN"})
    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, default=1, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    context_name: StringProperty(default="", options={"HIDDEN"})
    capture_button_properties: BoolProperty(default=False, options={"HIDDEN"})
    button_properties_json: StringProperty(default="{}", options={"HIDDEN"})
    button_unsupported_properties_json: StringProperty(default="[]", options={"HIDDEN"})
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
        draft_mode = bool(prefs is not None and getattr(prefs, "editor_dirty", False))
        if draft_mode and (
            not self.target_menu_id
            or prefs.editor_active_menu_id != self.target_menu_id
        ):
            self.report({"WARNING"}, "Apply or discard the current menu draft before configuring an operator outside this menu")
            return {"CANCELLED"}

        target_menu = None
        if self.target_menu_id:
            if prefs is None:
                self.report({"ERROR"}, "AllPie preferences are unavailable")
                return {"CANCELLED"}
            try:
                config = (
                    menu_editor.get_menu_operation_config(prefs, self.target_menu_id)
                    if draft_mode
                    else ConfigRuntime.get_config_copy()
                )
                target_menu = menu_editor.menu_data.get_menu(config, self.target_menu_id)
                if self.spaced and not menu_data.spaced_slots_enabled(target_menu):
                    raise ValueError("Spaced Slots are disabled for the target menu")
            except (RuntimeError, KeyError, ValueError) as error:
                self.report({"ERROR"}, f"Could not read the target menu: {error}")
                return {"CANCELLED"}

        initial_values = {}
        if self.capture_button_properties:
            try:
                initial_values = json.loads(self.button_properties_json or "{}")
                if not isinstance(initial_values, dict):
                    raise ValueError("Captured button properties are not a JSON object")
            except Exception as error:
                self.report({"ERROR"}, f"Could not read the clicked button's properties: {error}")
                return {"CANCELLED"}
        else:
            # Search/editor buttons must not inherit a property snapshot from a
            # previous right-click capture. Keep the row's preset name only when
            # the unified picker explicitly exposes it.
            initial_values = {}
            if not self.expose_preset_name:
                self.preset_name = ""
            self.button_unsupported_properties_json = "[]"
        self.invalid_saved_values = "[]"
        self.unknown_saved_properties = "[]"
        self.replace_invalid_saved_values = False
        self.remove_unknown_saved_properties = False

        if self.prefill_from_action:
            if not self.source_action_id:
                self.report({"ERROR"}, "The selected AllPie preset reference is empty")
                return {"CANCELLED"}
            try:
                source_config = _operator_setup_config(prefs, self.target_menu_id)
                source_action = operator_data.get_operator(source_config, self.source_action_id)
            except (RuntimeError, KeyError) as error:
                self.report({"ERROR"}, f"Could not load the selected AllPie preset: {error}")
                return {"CANCELLED"}
            self.operator_id = str(source_action.get("operator_id", self.operator_id))
            initial_values = dict(source_action.get("properties", {}))
            self.invoke_operator = bool(source_action.get("invoke", True))
            if not self.preset_name.strip():
                self.preset_name = str(source_action.get("name") or "")
            # Contexts are passed separately from the operator's Blender RNA
            # properties and merged with the target menu context on save.
            try:
                source_contexts = json.loads(self.source_contexts_json or "[]")
                if not isinstance(source_contexts, list):
                    source_contexts = []
            except Exception:
                source_contexts = []
            explicit_contexts = source_action.get("contexts", [])
            for value in explicit_contexts:
                if isinstance(value, str) and value.strip() and value.casefold() not in {str(x).casefold() for x in source_contexts}:
                    source_contexts.append(value.strip())
            self.source_contexts_json = json.dumps(source_contexts, separators=(",", ":"))

        if self.action_id and not self.create_new_action:
            try:
                config = _operator_setup_config(prefs, self.target_menu_id)
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
                    self.report({"ERROR"}, "Third-party presets are managed by their owning add-on and cannot be edited here. Duplicate the preset to customize it.")
                    return {"CANCELLED"}
                self.operator_id = str(action.get("operator_id", ""))
                initial_values = action.get("properties", {})
                self.invoke_operator = bool(action.get("invoke", True))
                self.preset_name = str(action.get("name") or self.action_id)[:64]
        if not self.action_id and self.target_menu_id:
            try:
                menu_config = _operator_setup_config(prefs, self.target_menu_id)
                menu = menu_editor.menu_data.get_menu(menu_config, self.target_menu_id)
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
            if not self.action_id and not self.preset_name.strip():
                # Use Blender's original RNA label as an editable suggestion.
                # Preset names are explicit library data, never synthesized
                # from arbitrary operator properties.
                rna = _operator_rna(self.operator_id)
                self.preset_name = str(
                    getattr(rna, "name", "") or self.operator_id
                ).strip()[:64]
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
        # The preset name is shared by every menu slot that references this
        # action. Keep it visible for both new presets and existing-preset
        # edits (including the slot gear), so there is only one naming system.
        name_box = layout.box()
        name_box.label(text="Operator Preset Name", icon="FONT_DATA")
        name_box.prop(self, "preset_name", text="Name")
        if self.action_id and not self.create_new_action:
            name_box.label(
                text="Renaming this preset updates every menu slot that uses it.",
                icon="INFO",
            )
        else:
            name_box.label(
                text="Blender's operator name is suggested; you can change it.",
                icon="INFO",
            )
        if self.capture_button_properties:
            context_box = layout.box()
            captured_context = str(self.context_name or "Unspecified").strip()
            if captured_context and captured_context.casefold() != "unspecified":
                context_box.label(text=f"Preset Context Tag: {captured_context}", icon="KEYINGSET")
                context_box.label(text="This tag is optional discovery metadata; it does not restrict where the preset can be assigned.", icon="INFO")
            else:
                context_box.label(text="No context tag was captured. This preset is available in every menu context.", icon="INFO")
            layout.label(text="Initial values were captured from the right-clicked Blender button.", icon="CHECKMARK")
            layout.label(text="Confirm Invoke Operator below; Blender's original button invocation mode is not exposed here.", icon="INFO")
            try:
                uncaptured = json.loads(self.button_unsupported_properties_json or "[]")
            except Exception:
                uncaptured = []
            if uncaptured:
                warning = layout.box()
                warning.alert = True
                warning.label(text="These advanced properties cannot be copied by AllPie:", icon="INFO")
                warning.label(text=", ".join(str(value) for value in uncaptured[:6]))
                if len(uncaptured) > 6:
                    warning.label(text=f"And {len(uncaptured) - 6} more…")
                warning.label(text="They will keep Blender defaults in the saved preset.")
        layout.separator()
        _draw_property_group(layout, group, entry["schema"], self.operator_id, entry["pointer_attr"])
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
        elif self.prefill_from_action:
            layout.label(
                text="Starts from the selected preset settings. A matching preset is reused; otherwise a separate preset is created.",
                icon="INFO",
            )
            if self.target_menu_id:
                layout.label(text=f"Will assign to Slot {self.slot_number}.", icon="INFO")
        elif self.target_menu_id:
            layout.label(text=f"Will create or reuse a preset and assign it to Slot {self.slot_number}.", icon="INFO")
        else:
            if self.context_name.strip():
                layout.label(text=f"Will create a preset tagged for {self.context_name}.", icon="INFO")
            else:
                layout.label(text="Will create an untagged preset available in every menu context.", icon="INFO")

    def execute(self, context):
        try:
            if not self.preset_name.strip():
                self.report({"ERROR"}, "Enter a name for this AllPie operator preset")
                return {"CANCELLED"}
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
            property_defaults = operator_properties.default_values_from_schema(entry["schema"])
            stored_values = operator_properties.strip_default_properties(
                edited_values,
                property_defaults,
            )
            from ..core.operator_validation import validate_operator_preset
            validation = validate_operator_preset(self.operator_id, edited_values, check_poll=False)
            if validation.errors:
                details = "; ".join(
                    f"{issue.path}: {issue.message}" for issue in validation.errors[:3]
                )
                self.report({"ERROR"}, f"Operator properties are invalid: {details}")
                return {"CANCELLED"}
            if self.action_id and not self.create_new_action:
                prefs = _preferences_from_context(context)
                draft_mode = bool(
                    prefs is not None
                    and getattr(prefs, "editor_dirty", False)
                    and self.target_menu_id
                    and prefs.editor_active_menu_id == self.target_menu_id
                )
                if prefs is not None and prefs.editor_dirty and not draft_mode:
                    self.report({"WARNING"}, "Apply or discard the current menu draft before editing a library preset")
                    return {"CANCELLED"}
                if draft_mode:
                    from . import menu_editor
                    config = menu_editor.get_menu_operation_config(prefs, self.target_menu_id)
                else:
                    config = ConfigRuntime.get_config_copy()
                action = operator_data.get_operator(config, self.action_id)
                previous_properties = dict(action.get("properties", {}))
                updated_properties = operator_properties.merge_configured_values(
                    previous_properties,
                    edited_values,
                    defaults=property_defaults,
                )
                if unknown_values and self.remove_unknown_saved_properties:
                    for property_name in unknown_values:
                        updated_properties.pop(property_name, None)

                preset_name = self.preset_name.strip()
                if not preset_name:
                    self.report({"ERROR"}, "Enter a name for this AllPie operator preset")
                    return {"CANCELLED"}
                action["name"] = preset_name
                # Keep search_name as an optional alias. It is searchable but
                # never used as the canonical visible preset name.
                action["properties"] = updated_properties
                action["invoke"] = bool(self.invoke_operator)
                if draft_mode:
                    menu_editor.store_menu_operation_draft(prefs, config)
                else:
                    ConfigRuntime.replace_and_save_configuration(config)
                    if prefs is not None:
                        _refresh_menu_editor(prefs)
                self.report({"INFO"}, f"Updated operator preset '{self.action_id}'")
                return {"FINISHED"}

            from . import operator_editor
            rna = _operator_rna(self.operator_id)
            preset_name = self.preset_name.strip()
            try:
                additional_context_names = json.loads(self.source_contexts_json or "[]")
                if not isinstance(additional_context_names, list):
                    additional_context_names = []
            except Exception:
                additional_context_names = []
            # Right-click capture stores the AllPie context inferred from the
            # editor where the button was clicked. Menu-slot additions inherit
            # the target menu context. Library additions stay untagged/global.
            selected_context_name = self.context_name.strip()
            created = operator_editor._add_operator_to_allpie(
                context,
                operator_id=self.operator_id,
                target_menu_id=self.target_menu_id,
                slot_number=self.slot_number,
                spaced=self.spaced,
                context_name=selected_context_name,
                properties=stored_values,
                property_defaults=property_defaults,
                invoke=bool(self.invoke_operator),
                name_override=preset_name,
                # Use Blender's registered operator label as an optional
                # search alias; the user-edited preset name remains canonical.
                search_name="",
                additional_context_names=additional_context_names,
            )
            state = "Added" if created else "Reused"
            self.report({"INFO"}, f"{state} '{self.operator_id}'")
        except Exception as error:
            self.report({"ERROR"}, f"Could not save operator preset: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}




def _preferences_from_context(context: Any) -> Any:
    from .. import Preferences
    addon = context.preferences.addons.get(Preferences.__package__)
    return addon.preferences if addon is not None else None


def _operator_setup_config(prefs: Any, target_menu_id: str) -> Dict[str, Any]:
    """Read the active menu draft when operator setup belongs to that draft."""
    if prefs is not None and getattr(prefs, "editor_dirty", False):
        if not target_menu_id or prefs.editor_active_menu_id != target_menu_id:
            raise RuntimeError(
                "Apply or discard the current menu draft before configuring an operator outside this menu"
            )
        from . import menu_editor
        return menu_editor.get_menu_operation_config(prefs, target_menu_id)
    return ConfigRuntime.get_config_copy()


def _refresh_menu_editor(prefs: Any) -> None:
    from . import menu_editor

    prefs.editor_config_generation = -1
    if prefs.editor_active_menu_id:
        menu_editor._ensure_editor_state(prefs)


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
    ALLPIE_OT_copy_panel_id,
    ALLPIE_OT_copy_menu_id,
    ALLPIE_OT_browse_panel_id,
    ALLPIE_OT_browse_menu_id,
    ALLPIE_OT_setup_blender_operator,
)
