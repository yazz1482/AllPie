"""Runtime validation for Blender operator presets.

This module bridges the JSON-safe AllPie action model and Blender's RNA
operator definitions. It is deliberately kept outside the radial modal
implementation so operator checks can be reused by setup dialogs, diagnostics
and the slot executor.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

OPERATOR_VALIDATION_API_VERSION = 3

_OPERATOR_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_OPERATOR_RNA_CACHE: dict[str, tuple[Any, Any]] = {}

_REQUIRED_NAME_OPERATORS = {
    "wm.call_panel",
    "wm.call_menu",
    "wm.call_menu_pie",
}


@dataclass(frozen=True)
class OperatorValidationIssue:
    severity: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.upper()}: {self.path}: {self.message}"


@dataclass
class OperatorValidationResult:
    operator_id: str
    registered: bool = False
    operator: Any = None
    rna: Any = None
    errors: list[OperatorValidationIssue] = field(default_factory=list)
    warnings: list[OperatorValidationIssue] = field(default_factory=list)
    poll_ok: Optional[bool] = None
    execution_properties: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return self.registered and not self.errors and self.poll_ok is not False


def _bpy_module(bpy_module=None):
    if bpy_module is not None:
        return bpy_module
    try:
        import bpy
    except ImportError:
        return None
    return bpy


def _property_map(rna: Any) -> dict[str, Any]:
    properties = getattr(rna, "properties", ())
    result = {}
    try:
        iterator = list(properties)
    except TypeError:
        try:
            iterator = list(properties.values())
        except Exception:
            iterator = []
    for prop in iterator:
        identifier = str(getattr(prop, "identifier", "") or "")
        if identifier and identifier != "rna_type":
            result[identifier] = prop
    return result


def _static_enum_identifiers(prop: Any) -> Optional[frozenset[str]]:
    """Return static enum IDs, or None for context-dependent/dynamic enums."""
    try:
        items = getattr(prop, "enum_items_static")
    except Exception:
        items = None
    if items is None:
        return None
    try:
        identifiers = frozenset(
            str(getattr(item, "identifier", "") or "")
            for item in items
            if getattr(item, "identifier", "")
        )
    except Exception:
        return None
    return identifiers or None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _issue(result: OperatorValidationResult, severity: str, path: str, message: str) -> None:
    issue = OperatorValidationIssue(severity, path, message)
    (result.errors if severity == "error" else result.warnings).append(issue)


def _validate_scalar(
    result: OperatorValidationResult,
    operator_id: str,
    identifier: str,
    prop: Any,
    value: Any,
) -> None:
    prop_type = str(getattr(prop, "type", "") or "").upper()
    is_array = bool(getattr(prop, "is_array", False))
    path = f"{operator_id}.{identifier}"

    if is_array:
        if not isinstance(value, (list, tuple)):
            _issue(result, "error", path, "must be an array")
            return
        expected_length = int(getattr(prop, "array_length", 0) or 0)
        if expected_length and len(value) != expected_length:
            _issue(result, "error", path, f"must contain exactly {expected_length} values")
            return
        values = list(value)
    else:
        values = [value]

    if prop_type == "BOOLEAN":
        valid = all(isinstance(item, bool) for item in values)
    elif prop_type == "INT":
        valid = all(isinstance(item, int) and not isinstance(item, bool) for item in values)
    elif prop_type == "FLOAT":
        valid = all(_is_number(item) for item in values)
    elif prop_type == "STRING":
        valid = isinstance(value, str) and not is_array
    elif prop_type == "ENUM":
        enum_flag = bool(getattr(prop, "is_enum_flag", False))
        if enum_flag:
            valid = isinstance(value, (list, tuple, set, frozenset)) and all(isinstance(item, str) for item in value)
        else:
            valid = isinstance(value, str) and not is_array
        if not valid:
            _issue(result, "error", path, "has the wrong value type for this enum")
            return
        allowed = _static_enum_identifiers(prop)
        if allowed is not None:
            selected = set(value) if enum_flag else {value}
            invalid = selected - allowed
            if invalid:
                _issue(result, "error", path, f"contains unknown enum value(s): {', '.join(sorted(invalid))}")
        # Dynamic enum choices have no stable global item list. Their values
        # are deferred to the operator's own context-sensitive validation.
        return
    else:
        _issue(
            result,
            "error",
            path,
            f"RNA type '{prop_type or 'UNKNOWN'}' cannot be represented safely by an AllPie JSON preset",
        )
        return

    if not valid:
        _issue(result, "error", path, f"value does not match Blender RNA type {prop_type}")
        return

    if prop_type in {"INT", "FLOAT"}:
        lower = getattr(prop, "hard_min", None)
        upper = getattr(prop, "hard_max", None)
        for item in values:
            if lower is not None and _is_number(lower) and item < lower:
                _issue(result, "error", path, f"value {item} is below Blender's minimum {lower}")
                break
            if upper is not None and _is_number(upper) and item > upper:
                _issue(result, "error", path, f"value {item} exceeds Blender's maximum {upper}")
                break
    elif prop_type == "STRING":
        max_length = int(getattr(prop, "length_max", 0) or 0)
        if max_length and len(value) > max_length:
            _issue(result, "error", path, f"text exceeds Blender's maximum length of {max_length}")


def validate_operator_preset(
    operator_id: str,
    properties: Any,
    *,
    bpy_module=None,
    check_poll: bool = False,
) -> OperatorValidationResult:
    """Validate one configured action against the currently registered RNA.

    Missing operators are warnings because third-party addons may be disabled.
    Invalid configured properties are errors because Blender will reject the
    operator call. Context-sensitive enum membership and poll status are only
    checked when Blender can resolve them in the current execution context.
    """
    result = OperatorValidationResult(operator_id=str(operator_id or ""))
    if not isinstance(operator_id, str) or not _OPERATOR_ID_RE.fullmatch(operator_id):
        _issue(result, "error", str(operator_id or "<empty>"), "invalid Blender operator identifier")
        return result
    if not isinstance(properties, Mapping):
        _issue(result, "error", operator_id, "operator properties must be a JSON object")
        return result

    cache_eligible = bpy_module is None
    bpy = _bpy_module(bpy_module)
    if bpy is None:
        _issue(result, "warning", operator_id, "Blender RNA is unavailable; operator registration could not be checked")
        return result

    cached = _OPERATOR_RNA_CACHE.get(operator_id) if cache_eligible else None
    if cached is None:
        module_name, operator_name = operator_id.split(".", 1)
        try:
            operator = getattr(getattr(bpy.ops, module_name), operator_name)
            rna = operator.get_rna_type()
        except Exception as error:
            _issue(result, "warning", operator_id, f"operator is not currently registered: {error}")
            return result
        if cache_eligible:
            _OPERATOR_RNA_CACHE[operator_id] = (operator, rna)
    else:
        operator, rna = cached

    result.registered = True
    result.operator = operator
    result.rna = rna
    rna_properties = _property_map(rna)

    for identifier in properties:
        if identifier not in rna_properties:
            _issue(
                result,
                "error",
                f"{operator_id}.{identifier}",
                "property is not defined by this Blender operator (possibly from another Blender version)",
            )

    execution_properties: dict[str, Any] = {}
    for identifier, prop in rna_properties.items():
        if identifier not in properties:
            # Hidden/read-only fields are intentionally excluded from the setup
            # editor and are normally managed internally by Blender. Visible
            # required fields must be supplied by an AllPie preset.
            if not bool(getattr(prop, "is_hidden", False)) and not bool(getattr(prop, "is_readonly", False)):
                required = bool(getattr(prop, "is_required", False))
                if operator_id in _REQUIRED_NAME_OPERATORS and identifier == "name":
                    required = True
                if required:
                    prop_type = str(getattr(prop, "type", "") or "").upper()
                    is_array = bool(getattr(prop, "is_array", False))
                    supported = prop_type in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"}
                    if is_array and prop_type not in {"BOOLEAN", "INT", "FLOAT"}:
                        supported = False
                    if not supported:
                        _issue(
                            result,
                            "error",
                            f"{operator_id}.{identifier}",
                            f"required RNA type '{prop_type or 'UNKNOWN'}' is not supported by the AllPie preset editor",
                        )
                    else:
                        _issue(result, "error", f"{operator_id}.{identifier}", "required operator property is missing")
            continue

        path = f"{operator_id}.{identifier}"
        # RNA's HIDDEN flag controls whether Blender exposes a property in its
        # own UI; it does not mean the property is invalid for bpy.ops calls.
        # AllPie presets are allowed to retain and pass hidden-but-writable
        # fields (many built-in operators rely on them). Only genuinely
        # read-only properties cannot be supplied by an action preset.
        if bool(getattr(prop, "is_readonly", False)):
            _issue(result, "error", path, "property is read-only and cannot be passed to a Blender operator")
            continue

        required = bool(getattr(prop, "is_required", False))
        if operator_id in _REQUIRED_NAME_OPERATORS and identifier == "name":
            required = True
        value = properties[identifier]
        if required:
            is_empty = value is None
            if isinstance(value, str):
                is_empty = not value.strip()
            elif isinstance(value, (list, tuple, set, frozenset, dict)):
                is_empty = len(value) == 0
            if is_empty:
                _issue(result, "error", path, "required operator property cannot be empty")
                continue

        _validate_scalar(result, operator_id, identifier, prop, value)

        # JSON stores enum flags and arrays as arrays. Convert them to the
        # Python value shapes expected by Blender's operator call API.
        prop_type = str(getattr(prop, "type", "") or "").upper()
        if prop_type == "ENUM" and bool(getattr(prop, "is_enum_flag", False)):
            execution_properties[identifier] = set(value) if isinstance(value, (list, tuple, set, frozenset)) else value
        elif bool(getattr(prop, "is_array", False)) and isinstance(value, list):
            execution_properties[identifier] = tuple(value)
        else:
            execution_properties[identifier] = value

    result.execution_properties = execution_properties

    if check_poll:
        try:
            result.poll_ok = bool(operator.poll())
            if not result.poll_ok:
                _issue(result, "warning", operator_id, "operator is not available in the current Blender context (check mode, selection and active editor)")
        except Exception as error:
            result.poll_ok = None
            _issue(result, "warning", operator_id, f"could not evaluate operator context availability: {error}")

    return result


def validate_configuration_operators(config: Mapping[str, Any], *, bpy_module=None) -> list[OperatorValidationIssue]:
    """Validate availability and configured properties for every action preset."""
    issues: list[OperatorValidationIssue] = []
    operator_collections = [("Operators", config.get("Operators", {}))]
    for addon_id, addon in config.get("ThirdParty", {}).items():
        if not isinstance(addon, Mapping) or not addon.get("enabled", True):
            continue
        operator_collections.append((f"ThirdParty.{addon_id}.Operators", addon.get("Operators", {})))

    for collection_path, collection in operator_collections:
        if not isinstance(collection, Mapping):
            continue
        for action_id, action in collection.items():
            if not isinstance(action, Mapping):
                continue
            operator_id = str(action.get("operator_id", ""))
            result = validate_operator_preset(
                operator_id,
                action.get("properties", {}),
                bpy_module=bpy_module,
                check_poll=False,
            )
            action_path = f"{collection_path}.{action_id}"
            for issue in result.errors:
                property_path = issue.path[len(operator_id) + 1:] if issue.path.startswith(operator_id + ".") else ""
                message = f"{property_path}: {issue.message}" if property_path else issue.message
                issues.append(OperatorValidationIssue(issue.severity, action_path, message))
            for issue in result.warnings:
                property_path = issue.path[len(operator_id) + 1:] if issue.path.startswith(operator_id + ".") else ""
                message = f"{property_path}: {issue.message}" if property_path else issue.message
                issues.append(OperatorValidationIssue(issue.severity, action_path, message))
    return issues


def clear_operator_rna_cache() -> None:
    """Invalidate cached RNA wrappers after operator/addon catalog refreshes."""
    _OPERATOR_RNA_CACHE.clear()
