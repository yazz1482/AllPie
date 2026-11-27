"""Blender-independent RNA operator-property normalization helpers.

The Blender UI layer converts these normalized specifications into dynamic
PropertyGroup fields. Keeping the normalization logic independent makes the
supported property model testable without starting Blender.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

OPERATOR_PROPERTIES_API_VERSION = 5

_BRUSH_ASSET_OPERATOR_ID = "brush.asset_activate"
_BRUSH_ASSET_REFERENCE_PROPERTIES = frozenset({
    "asset_library_type",
    "asset_library_identifier",
    "relative_asset_identifier",
})

SUPPORTED_SCALAR_TYPES = frozenset({"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"})


def _get(value: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(value, name)
    except Exception:
        return default


def _enum_items(prop: Any) -> list[dict[str, str]]:
    """Read static enum values, falling back to the context-resolved list."""
    items = None
    for attr in ("enum_items_static", "enum_items"):
        try:
            candidate = getattr(prop, attr)
            if candidate:
                items = candidate
                break
        except Exception:
            continue

    result: list[dict[str, str]] = []
    if items is None:
        return result
    try:
        for item in items:
            identifier = str(_get(item, "identifier", "") or "")
            if not identifier:
                continue
            result.append({
                "identifier": identifier,
                "name": str(_get(item, "name", "") or identifier),
                "description": str(_get(item, "description", "") or ""),
            })
    except Exception:
        return []
    return result


def _finite_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError, OverflowError):
        return fallback


def _default_for(prop: Any, prop_type: str, is_array: bool, array_length: int, enum_flag: bool) -> Any:
    if prop_type == "ENUM" and enum_flag:
        value = _get(prop, "default_flag", None)
        if value is None:
            value = _get(prop, "default", ())
        try:
            return sorted(str(item) for item in value)
        except TypeError:
            return []

    if is_array:
        value = _get(prop, "default_array", None)
        if value is None:
            value = _get(prop, "default", None)
        if value is None:
            value = [False if prop_type == "BOOLEAN" else 0 for _ in range(array_length)]
        try:
            values = list(value)
        except TypeError:
            values = []
        if len(values) < array_length:
            values.extend([0] * (array_length - len(values)))
        return values[:array_length]

    value = _get(prop, "default", None)
    if value is not None:
        return value
    if prop_type == "BOOLEAN":
        return False
    if prop_type == "INT":
        return 0
    if prop_type == "FLOAT":
        return 0.0
    if prop_type == "STRING":
        return ""
    return None


def build_property_specs(operator_id: str, rna_properties: Iterable[Any]) -> dict[str, Any]:
    """Create serializable specs for properties that AllPie can edit.

    Pointer and collection properties (and unknown RNA types) are reported as
    unsupported instead of being silently omitted. The `wm.call_panel.name`
    and `wm.call_menu*.name` fields are marked for clear manual identifier
    entry in the setup dialog; they deliberately do not use StringProperty's
    autocomplete callback because unmatched IDs must be committed verbatim.
    """
    specs: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []

    for prop in rna_properties:
        identifier = str(_get(prop, "identifier", "") or "")
        if not identifier or identifier == "rna_type":
            continue
        if bool(_get(prop, "is_readonly", False)):
            continue

        options = set(_get(prop, "options", ()) or ())
        # Blender deliberately marks the three asset-reference properties of
        # brush.asset_activate as HIDDEN | SKIP_SAVE. They are nevertheless
        # essential to a reusable brush preset. Keep them in AllPie's internal
        # dynamic PropertyGroup so captured asset references are recognized,
        # validated, and retained, but mark them as UI-hidden below. Other
        # hidden fields (notably use_toggle) remain excluded.
        is_brush_asset_reference = (
            operator_id == _BRUSH_ASSET_OPERATOR_ID
            and identifier in _BRUSH_ASSET_REFERENCE_PROPERTIES
        )
        is_hidden = bool(_get(prop, "is_hidden", False)) or "HIDDEN" in options
        if is_hidden and not is_brush_asset_reference:
            continue

        prop_type = str(_get(prop, "type", "") or "").upper()
        is_array = bool(_get(prop, "is_array", False))
        array_length = int(_get(prop, "array_length", 0) or 0) if is_array else 0
        enum_flag = prop_type == "ENUM" and bool(_get(prop, "is_enum_flag", False))

        supported = prop_type in SUPPORTED_SCALAR_TYPES
        if is_array and prop_type not in {"BOOLEAN", "INT", "FLOAT"}:
            supported = False
        if prop_type == "ENUM":
            enum_items = _enum_items(prop)
            if not enum_items:
                supported = False
        else:
            enum_items = []

        required = bool(_get(prop, "is_required", False))
        # These UI-dispatch operators accept arbitrary registered identifiers
        # as strings. Their RNA defaults are empty, but an empty value cannot
        # invoke a useful panel/menu action, so AllPie treats them as required.
        panel_name_search = operator_id == "wm.call_panel" and identifier == "name"
        menu_name_search = operator_id in {"wm.call_menu", "wm.call_menu_pie"} and identifier == "name"
        if panel_name_search or menu_name_search:
            required = True

        if not supported:
            unsupported.append({
                "identifier": identifier,
                "name": str(_get(prop, "name", identifier) or identifier),
                "description": str(_get(prop, "description", "") or ""),
                "type": prop_type,
                "required": required,
                "reason": "This RNA property type needs specialized handling.",
            })
            continue

        default = _default_for(prop, prop_type, is_array, array_length, enum_flag)
        if prop_type == "ENUM" and not enum_flag:
            valid_ids = {item["identifier"] for item in enum_items}
            if default not in valid_ids:
                default = enum_items[0]["identifier"] if enum_items else None

        spec = {
            "identifier": identifier,
            "name": str(_get(prop, "name", identifier) or identifier),
            "ui_hidden": bool(is_brush_asset_reference),
            "description": str(_get(prop, "description", "") or ""),
            "type": prop_type,
            "is_array": is_array,
            "array_length": array_length,
            "enum_flag": enum_flag,
            "enum_items": enum_items,
            "default": default,
            "required": required,
            "subtype": str(_get(prop, "subtype", "NONE") or "NONE"),
            "unit": str(_get(prop, "unit", "NONE") or "NONE"),
            "hard_min": _get(prop, "hard_min", None),
            "hard_max": _get(prop, "hard_max", None),
            "soft_min": _get(prop, "soft_min", None),
            "soft_max": _get(prop, "soft_max", None),
            "maxlen": int(_get(prop, "length_max", 0) or 0),
            "panel_name_search": panel_name_search,
            "menu_name_search": menu_name_search,
        }
        specs.append(spec)

    return {
        "operator_id": str(operator_id),
        "properties": specs,
        "unsupported": unsupported,
        "required_unsupported": [item for item in unsupported if item["required"]],
    }


def json_safe_value(value: Any) -> Any:
    """Convert Blender RNA values into JSON-compatible primitives."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Operator properties cannot contain NaN or infinity")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (set, frozenset)):
        return sorted(json_safe_value(item) for item in value)
    if isinstance(value, (tuple, list)):
        return [json_safe_value(item) for item in value]
    # Blender's IDPropertyArray / bpy_prop_array generally implements the
    # sequence protocol without inheriting from list or tuple.
    try:
        return [json_safe_value(item) for item in list(value)]
    except (TypeError, ValueError):
        raise TypeError(f"Unsupported operator property value: {type(value).__name__}")


def validate_required_values(specs: Iterable[Mapping[str, Any]], values: Mapping[str, Any]) -> list[str]:
    """Return required fields that remain unset in the proposed preset."""
    missing: list[str] = []
    for spec in specs:
        if not spec.get("required"):
            continue
        identifier = str(spec["identifier"])
        value = values.get(identifier)
        if value is None or value == "" or value == set() or value == []:
            missing.append(str(spec.get("name") or identifier))
    return missing


def default_values_from_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return JSON-safe RNA defaults for the properties exposed by a setup dialog."""
    defaults: dict[str, Any] = {}
    for spec in schema.get("properties", ()):
        identifier = str(spec.get("identifier", "")).strip()
        if identifier and "default" in spec:
            defaults[identifier] = json_safe_value(spec.get("default"))
    return defaults


def strip_default_properties(
    values: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove properties equal to Blender's current RNA defaults.

    Omitting a property and storing its current RNA default have the same
    effective operator behavior. Canonicalizing both forms prevents a newly
    configured default action from becoming a duplicate of an older preset
    whose properties were stored sparsely.
    """
    result: dict[str, Any] = {}
    normalized_defaults = {
        str(key): json_safe_value(value)
        for key, value in defaults.items()
    }
    for key, value in values.items():
        identifier = str(key)
        safe_value = json_safe_value(value)
        if identifier in normalized_defaults and safe_value == normalized_defaults[identifier]:
            continue
        result[identifier] = safe_value
    return result


def merge_configured_values(
    original: Mapping[str, Any],
    edited: Mapping[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Update supported fields, omit current defaults, and preserve unknown values.

    Known fields are rebuilt from the edited values so changing a property back
    to its Blender default removes the redundant stored key. Properties not
    exposed by this Blender RNA schema remain untouched for forward/backward
    compatibility unless the caller explicitly removes them.
    """
    normalized_defaults = {
        str(key): json_safe_value(value)
        for key, value in (defaults or {}).items()
    }
    result = {str(key): json_safe_value(value) for key, value in original.items()}
    for identifier in normalized_defaults:
        result.pop(identifier, None)
    result.update(strip_default_properties(edited, normalized_defaults))
    return result
