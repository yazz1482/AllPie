"""Blender-native registered-operator browser for AllPie.

The catalog is scanned from Blender RNA and cached for the session. A compact
search popup displays operators in a UIList; each result button uses Blender's
dynamic Operator.description() callback so hovering a result explains what it
does. Selecting a result creates/reuses an AllPie preset and optionally assigns
it directly to a menu slot.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
import time
from typing import Any, Dict, List, Mapping

import bpy
from bpy.types import Menu, Operator, PropertyGroup, UIList
from bpy.props import BoolProperty, IntProperty, StringProperty

from ..core import runtime as ConfigRuntime
from . import menu_data, operator_data

OPERATOR_EDITOR_API_VERSION = 42

_OPERATOR_INFO: Dict[str, Dict[str, str]] = {}
_OPERATOR_CATALOG_GENERATION = 0
_SEARCH_MATCH_CACHE_KEY = None
_SEARCH_MATCH_CACHE: List[int] = []
_BUILTIN_ACTION_IDS = None
_OPERATOR_SCAN_ITERATOR = None
_OPERATOR_SCAN_RUNNING = False
_OPERATOR_SCAN_COMPLETE = False
_OPERATOR_SCAN_ERROR = ""
_SEARCH_ITEM_KEYS: set[tuple[str, str]] = set()
_LAST_CATALOG_REDRAW_TIME = 0.0
_LIVE_OPERATOR_RESULT_LIMIT = 200
_LIVE_OPERATOR_RESULTS_TRUNCATED = False
SEARCH_CONTEXT_ITEMS = tuple(
    item for item in menu_data.KEYMAP_ENUM_ITEMS if item[0] not in {"CUSTOM", "COMMON"}
)
SEARCH_CONTEXT_FILTER_ITEMS = tuple(
    (identifier, label, description, 1 << index)
    for index, (identifier, label, description) in enumerate(SEARCH_CONTEXT_ITEMS + (
        ("OTHER", "Other Contexts", "Presets tagged for custom or other keymap contexts"),
        ("UNASSIGNED", "Unassigned", "Presets without any context tags or menu usage"),
    ))
)


def _preferences_from_context(context: Any) -> Any:
    from .. import Preferences
    addon = context.preferences.addons.get(Preferences.__package__)
    return addon.preferences if addon is not None else None


def _humanize_operator_id(operator_id: str) -> str:
    return re.sub(r"[_]+", " ", operator_id.rsplit(".", 1)[-1]).strip().title()


def _operator_record(operator_id: str, rna: Any, module_hint: str = "") -> Dict[str, str] | None:
    operator_id = str(operator_id or "").strip().lower()
    if "." not in operator_id:
        return None
    module_name = operator_id.partition(".")[0]
    if not module_name or module_name.startswith("_") or module_name.casefold() == "allpie":
        return None
    try:
        label = str(getattr(rna, "name", "") or "").strip()
        description = str(getattr(rna, "description", "") or "").strip()
    except Exception:
        label = ""
        description = ""
    if not label:
        label = _humanize_operator_id(operator_id)
    if not description:
        description = f"No description is registered for {label}."
    return {
        "operator_id": operator_id,
        "name": label,
        "description": description,
        "module": module_name or module_hint,
        "display_name": label,
    }


def _iter_registered_operator_rna():
    """Yield registered operator RNA in small, lazily evaluated steps.

    Discovery deliberately yields one operator at a time. The search popup can
    appear immediately, while Blender's RNA catalog is filled by short timer
    batches instead of blocking the click handler with a full bpy.ops/bpy.types
    scan.
    """
    try:
        module_names = dir(bpy.ops)
    except Exception:
        module_names = ()

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
            try:
                operator = getattr(operator_module, operator_name)
                rna = operator.get_rna_type()
            except Exception:
                continue
            yield operator_id, rna, module_name

    # Supplement bpy.ops with registered Operator RNA classes. Some enabled
    # extensions register classes that do not appear in bpy.ops.dir snapshots.
    try:
        type_names = (name for name in dir(bpy.types) if "_OT_" in name)
    except Exception:
        type_names = ()
    for type_name in type_names:
        try:
            operator_class = getattr(bpy.types, type_name)
            rna = getattr(operator_class, "bl_rna", None)
            if rna is None:
                continue
            operator_id = str(getattr(operator_class, "bl_idname", "") or "").strip()
            if "." not in operator_id:
                operator_id = _operator_id_from_button_rna(
                    getattr(rna, "identifier", type_name)
                )
            yield operator_id, rna, ""
        except Exception:
            continue


def _finalize_operator_display_names() -> None:
    """Add module qualifiers only where different operators share a label."""
    label_counts = Counter(item["name"].casefold() for item in _OPERATOR_INFO.values())
    for item in _OPERATOR_INFO.values():
        item["display_name"] = (
            f"{item['name']} ({item['module']})"
            if label_counts[item["name"].casefold()] > 1
            else item["name"]
        )


def _scan_registered_operators() -> List[Dict[str, str]]:
    """Synchronously enumerate all registered operators for explicit tooling."""
    discovered: Dict[str, Dict[str, str]] = {}
    for operator_id, rna, module_hint in _iter_registered_operator_rna():
        record = _operator_record(operator_id, rna, module_hint)
        if record is not None:
            discovered[record["operator_id"]] = record
    records = list(discovered.values())
    records.sort(key=lambda item: (item["name"].casefold(), item["operator_id"].casefold()))
    counts = Counter(item["name"].casefold() for item in records)
    for item in records:
        item["display_name"] = (
            f"{item['name']} ({item['module']})"
            if counts[item["name"].casefold()] > 1
            else item["name"]
        )
    return records


def _redraw_preferences_areas() -> None:
    try:
        wm = bpy.context.window_manager
        for window in wm.windows:
            screen = getattr(window, "screen", None)
            if screen is None:
                continue
            for area in screen.areas:
                if area.type == "PREFERENCES":
                    area.tag_redraw()
    except (AttributeError, ReferenceError, RuntimeError):
        pass


def _operator_search_text_matches(record: Mapping[str, Any], needle: str) -> bool:
    """Return whether a live Blender operator matches the current query."""
    if not needle:
        return False
    haystack = " ".join((
        str(record.get("display_name") or ""),
        str(record.get("name") or ""),
        str(record.get("operator_id") or ""),
        str(record.get("description") or ""),
        str(record.get("module") or ""),
    )).casefold()
    return needle in haystack


def _operator_search_rank(record: Mapping[str, Any], needle: str) -> tuple:
    """Prioritize exact/leading name and ID matches ahead of description hits."""
    label = str(record.get("display_name") or record.get("name") or "").casefold()
    original_label = str(record.get("name") or "").casefold()
    operator_id = str(record.get("operator_id") or "").casefold()
    if operator_id == needle:
        rank = 0
    elif label.startswith(needle) or original_label.startswith(needle):
        rank = 1
    elif operator_id.startswith(needle):
        rank = 2
    elif needle in label or needle in original_label:
        rank = 3
    elif needle in operator_id:
        rank = 4
    else:
        rank = 5
    return rank, label, operator_id


def _remove_live_operator_search_items(prefs: Any) -> None:
    """Remove materialized raw operator results, keeping preset rows intact."""
    collection = prefs.operator_search_items
    for index in range(len(collection) - 1, -1, -1):
        if collection[index].source_kind == "BLENDER":
            collection.remove(index)


def _append_live_operator_search_item(collection: Any, record: Mapping[str, Any]) -> None:
    operator_id = str(record.get("operator_id", ""))
    _write_search_item(collection.add(), {
        "source_kind": "BLENDER",
        "action_id": "",
        "operator_id": operator_id,
        "name": str(record.get("display_name") or record.get("name") or operator_id),
        "search_alias": str(record.get("name") or ""),
        "description": str(record.get("description", "")),
        "module": str(record.get("module") or operator_id.partition(".")[0]),
        "contexts": [],
        "categories": [],
    })


def _refresh_live_operator_search_items(prefs: Any) -> None:
    """Materialize only live operators matching the current search query.

    Preset rows remain available when the query is empty. Raw Blender operators
    are kept in the in-memory RNA catalog and copied into Blender's UI collection
    only when the user enters a query. This prevents every slot click from
    creating thousands of RNA collection items before the popup can appear.
    """
    global _SEARCH_ITEM_KEYS, _SEARCH_MATCH_CACHE_KEY, _SEARCH_MATCH_CACHE
    global _LIVE_OPERATOR_RESULTS_TRUNCATED

    _remove_live_operator_search_items(prefs)
    collection = prefs.operator_search_items
    _SEARCH_ITEM_KEYS = {
        ("PRESET", str(item.action_id))
        for item in collection
        if item.source_kind == "PRESET" and item.action_id
    }

    needle = str(getattr(prefs, "operator_search_query", "") or "").casefold().strip()
    _LIVE_OPERATOR_RESULTS_TRUNCATED = False
    if needle:
        matches = []
        for record in _OPERATOR_INFO.values():
            operator_id = str(record.get("operator_id", ""))
            if not operator_id:
                continue
            if _operator_search_text_matches(record, needle):
                matches.append(record)
        matches.sort(key=lambda record: _operator_search_rank(record, needle))
        _LIVE_OPERATOR_RESULTS_TRUNCATED = len(matches) > _LIVE_OPERATOR_RESULT_LIMIT
        for record in matches[:_LIVE_OPERATOR_RESULT_LIMIT]:
            operator_id = str(record.get("operator_id", ""))
            _append_live_operator_search_item(collection, record)
            _SEARCH_ITEM_KEYS.add(("BLENDER", operator_id))

    prefs.operator_search_catalog_generation = _OPERATOR_CATALOG_GENERATION
    prefs.operator_search_catalog_loading = _OPERATOR_SCAN_RUNNING
    prefs.operator_search_catalog_error = _OPERATOR_SCAN_ERROR
    _SEARCH_MATCH_CACHE_KEY = None
    _SEARCH_MATCH_CACHE = []
    if prefs.operator_search_active_index >= len(collection):
        prefs.operator_search_active_index = 0


def _append_operator_search_batch(records: List[Dict[str, str]]) -> None:
    """Append only matching live operators while an incremental scan is active."""
    global _SEARCH_MATCH_CACHE_KEY, _SEARCH_MATCH_CACHE, _LAST_CATALOG_REDRAW_TIME
    global _LIVE_OPERATOR_RESULTS_TRUNCATED
    try:
        prefs = _preferences_from_context(bpy.context)
    except Exception:
        prefs = None
    if prefs is None:
        return

    # Keep generation/status current even when the user has not typed a query.
    prefs.operator_search_catalog_generation = _OPERATOR_CATALOG_GENERATION
    prefs.operator_search_catalog_loading = _OPERATOR_SCAN_RUNNING
    prefs.operator_search_catalog_error = _OPERATOR_SCAN_ERROR

    needle = str(getattr(prefs, "operator_search_query", "") or "").casefold().strip()
    if not needle:
        return

    collection = prefs.operator_search_items
    visible_live_count = sum(1 for item in collection if item.source_kind == "BLENDER")
    added = False
    for record in records:
        operator_id = str(record.get("operator_id", ""))
        if not operator_id:
            continue
        if not _operator_search_text_matches(record, needle):
            continue
        key = ("BLENDER", operator_id)
        if key in _SEARCH_ITEM_KEYS:
            continue
        if visible_live_count >= _LIVE_OPERATOR_RESULT_LIMIT:
            _LIVE_OPERATOR_RESULTS_TRUNCATED = True
            continue
        _SEARCH_ITEM_KEYS.add(key)
        _append_live_operator_search_item(collection, record)
        visible_live_count += 1
        added = True

    if added:
        _SEARCH_MATCH_CACHE_KEY = None
        _SEARCH_MATCH_CACHE = []
        now = time.monotonic()
        if now - _LAST_CATALOG_REDRAW_TIME >= 0.15:
            _LAST_CATALOG_REDRAW_TIME = now
            _redraw_preferences_areas()


def _operator_catalog_scan_tick():
    """Process a small slice of the Blender operator catalog per UI tick."""
    global _OPERATOR_SCAN_RUNNING, _OPERATOR_SCAN_COMPLETE, _OPERATOR_SCAN_ITERATOR
    global _OPERATOR_SCAN_ERROR, _OPERATOR_CATALOG_GENERATION

    iterator = _OPERATOR_SCAN_ITERATOR
    if iterator is None:
        _OPERATOR_SCAN_RUNNING = False
        _OPERATOR_SCAN_COMPLETE = True
        return None

    started = time.perf_counter()
    processed = 0
    batch: List[Dict[str, str]] = []
    finished = False
    try:
        while processed < 32 and (time.perf_counter() - started) < 0.004:
            try:
                operator_id, rna, module_hint = next(iterator)
            except StopIteration:
                finished = True
                break
            processed += 1
            record = _operator_record(operator_id, rna, module_hint)
            if record is None or record["operator_id"] in _OPERATOR_INFO:
                continue
            _OPERATOR_INFO[record["operator_id"]] = record
            batch.append(record)
    except Exception as error:
        _OPERATOR_SCAN_ERROR = str(error)
        finished = True

    if batch:
        _OPERATOR_CATALOG_GENERATION += 1
        _append_operator_search_batch(batch)

    if finished:
        _OPERATOR_SCAN_RUNNING = False
        _OPERATOR_SCAN_COMPLETE = True
        _OPERATOR_SCAN_ITERATOR = None
        _finalize_operator_display_names()
        _OPERATOR_CATALOG_GENERATION += 1
        _refresh_visible_operator_item_names()
        try:
            prefs = _preferences_from_context(bpy.context)
        except Exception:
            prefs = None
        if prefs is not None:
            prefs.operator_search_catalog_generation = _OPERATOR_CATALOG_GENERATION
            prefs.operator_search_catalog_loading = False
            prefs.operator_search_catalog_error = _OPERATOR_SCAN_ERROR
            _refresh_live_operator_search_items(prefs)
            matches = _matching_search_indices(prefs)
            prefs.operator_search_active_index = matches[0] if matches else 0
        _redraw_preferences_areas()
        return None

    return 0.05


def _refresh_visible_operator_item_names() -> None:
    """Apply final duplicate-label qualifiers to Blender rows already visible."""
    try:
        prefs = _preferences_from_context(bpy.context)
    except Exception:
        prefs = None
    if prefs is None:
        return
    for item in prefs.operator_search_items:
        if item.source_kind != "BLENDER":
            continue
        record = _OPERATOR_INFO.get(item.operator_id)
        if record is not None:
            item.name = str(record.get("display_name") or record.get("name") or item.operator_id)


def _schedule_operator_catalog_scan(*, reset: bool = False) -> int:
    """Start non-blocking catalog discovery and return the currently cached count."""
    global _OPERATOR_SCAN_ITERATOR, _OPERATOR_SCAN_RUNNING, _OPERATOR_SCAN_COMPLETE
    global _OPERATOR_SCAN_ERROR, _OPERATOR_CATALOG_GENERATION

    if reset:
        cancel_operator_catalog_scan()
        _OPERATOR_INFO.clear()
        _OPERATOR_SCAN_COMPLETE = False
        _OPERATOR_SCAN_ERROR = ""
        _OPERATOR_CATALOG_GENERATION += 1
    if _OPERATOR_SCAN_COMPLETE:
        return len(_OPERATOR_INFO)
    if not _OPERATOR_SCAN_RUNNING:
        _OPERATOR_SCAN_ITERATOR = iter(_iter_registered_operator_rna())
        _OPERATOR_SCAN_RUNNING = True
        _OPERATOR_SCAN_ERROR = ""
        try:
            if not bpy.app.timers.is_registered(_operator_catalog_scan_tick):
                bpy.app.timers.register(_operator_catalog_scan_tick, first_interval=0.05)
        except Exception as error:
            _OPERATOR_SCAN_RUNNING = False
            _OPERATOR_SCAN_ITERATOR = None
            _OPERATOR_SCAN_ERROR = str(error)
    try:
        prefs = _preferences_from_context(bpy.context)
    except Exception:
        prefs = None
    if prefs is not None:
        prefs.operator_search_catalog_loading = _OPERATOR_SCAN_RUNNING
        prefs.operator_search_catalog_error = _OPERATOR_SCAN_ERROR
    return len(_OPERATOR_INFO)


def cancel_operator_catalog_scan() -> None:
    """Stop a pending catalog timer before the addon module is reloaded/unregistered."""
    global _OPERATOR_SCAN_ITERATOR, _OPERATOR_SCAN_RUNNING
    try:
        if bpy.app.timers.is_registered(_operator_catalog_scan_tick):
            bpy.app.timers.unregister(_operator_catalog_scan_tick)
    except Exception:
        pass
    _OPERATOR_SCAN_ITERATOR = None
    _OPERATOR_SCAN_RUNNING = False


def _refresh_operator_catalog() -> int:
    """Synchronously refresh the catalog for rare direct-RNA fallback paths."""
    global _OPERATOR_INFO, _OPERATOR_CATALOG_GENERATION, _OPERATOR_SCAN_COMPLETE, _OPERATOR_SCAN_ERROR
    records = _scan_registered_operators()
    _OPERATOR_INFO = {record["operator_id"]: record for record in records}
    _OPERATOR_SCAN_COMPLETE = True
    _OPERATOR_SCAN_ERROR = ""
    _OPERATOR_CATALOG_GENERATION += 1
    return len(records)


def _ensure_operator_catalog() -> int:
    if not _OPERATOR_SCAN_COMPLETE:
        return _schedule_operator_catalog_scan()
    return len(_OPERATOR_INFO)


def _operator_search_config_fingerprint(records: List[Mapping[str, Any]]) -> str:
    """Hash only the fields that affect the unified picker rows and filters."""
    payload = [
        (
            str(record.get("action_id", "")),
            str(record.get("name", "")),
            str(record.get("search_name", "")),
            str(record.get("description", "")),
            str(record.get("operator_id", "")),
            tuple(str(value) for value in record.get("contexts", ())),
            tuple(str(value) for value in record.get("categories", ())),
            str(record.get("owner_addon", "")),
            bool(record.get("unassigned", False)),
        )
        for record in records
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2s(encoded, digest_size=12).hexdigest()


def _write_search_item(item: Any, record: Mapping[str, Any]) -> None:
    item.operator_id = record["operator_id"]
    item.name = record["name"]
    item.search_alias = record.get("search_alias", "")
    item.description = record["description"]
    item.module = record["module"]
    item.source_kind = record["source_kind"]
    item.action_id = record["action_id"]
    item.contexts_json = json.dumps(record.get("contexts", ()), separators=(",", ":"))
    item.categories_json = json.dumps(record.get("categories", ()), separators=(",", ":"))
    item.context_summary = ", ".join(record.get("contexts", ())) or ("All contexts" if record["source_kind"] == "PRESET" else "Blender operator")
    item.can_edit = bool(record.get("can_edit", False))
    item.can_delete = bool(record.get("can_delete", False))


def _populate_search_items(
    prefs: Any,
    *,
    config_override: Mapping[str, Any] | None = None,
    force: bool = False,
) -> None:
    """Populate the small saved-preset list without materializing raw RNA ops.

    The full Blender operator catalog stays as plain Python metadata. Matching
    live operators are materialized only when the user types a query; this
    keeps opening a slot picker independent of the total number of registered
    Blender/add-on operators.
    """
    config = (
        dict(config_override)
        if config_override is not None
        else (ConfigRuntime.ACTIVE_CONFIG or ConfigRuntime.get_config_copy())
    )
    preset_records = operator_data.iter_operator_records(config)
    fingerprint = _operator_search_config_fingerprint(preset_records)
    config_fingerprint = str(getattr(prefs, "operator_search_config_fingerprint", ""))
    collection = prefs.operator_search_items

    if force or fingerprint != config_fingerprint:
        collection.clear()
        try:
            bundled_ids = _get_bundled_action_ids()
        except RuntimeError:
            # Search remains available when the bundled defaults cannot be
            # inspected, but destructive preset controls must fail closed.
            bundled_ids = None
        for preset in preset_records:
            operator_id = str(preset.get("operator_id", ""))
            if not operator_id:
                continue
            action_id = str(preset.get("action_id", ""))
            owner_addon = str(preset.get("owner_addon", "") or "")
            can_delete = False
            if action_id and not owner_addon and bundled_ids is not None:
                action = config.get("Operators", {}).get(str(preset.get("legacy_id", "")), {})
                can_delete = operator_data.is_user_defined_action(
                    action_id,
                    action if isinstance(action, Mapping) else {},
                    bundled_ids,
                )
            item = collection.add()
            _write_search_item(item, {
                "source_kind": "PRESET",
                "action_id": action_id,
                "operator_id": operator_id,
                "name": str(preset.get("name") or preset.get("action_id", "")),
                "search_alias": str(preset.get("search_name") or preset.get("name") or ""),
                "description": str(preset.get("description", "")),
                "module": operator_id.partition(".")[0],
                "contexts": list(preset.get("contexts", ())),
                "categories": list(preset.get("categories", ())),
                "can_edit": not bool(owner_addon),
                "can_delete": can_delete,
            })
        prefs.operator_search_config_fingerprint = fingerprint

    global _SEARCH_ITEM_KEYS, _SEARCH_MATCH_CACHE_KEY, _SEARCH_MATCH_CACHE
    _SEARCH_ITEM_KEYS = {
        ("PRESET", str(item.action_id))
        for item in collection
        if item.source_kind == "PRESET" and item.action_id
    }
    # The query is cleared when a picker opens. Do not carry raw Blender rows
    # from the previous picker session into this one.
    _remove_live_operator_search_items(prefs)
    prefs.operator_search_catalog_generation = _OPERATOR_CATALOG_GENERATION
    prefs.operator_search_config_generation = int(getattr(getattr(ConfigRuntime, "REGISTRY", None), "generation", -1))
    prefs.operator_search_catalog_loading = _OPERATOR_SCAN_RUNNING
    prefs.operator_search_catalog_error = _OPERATOR_SCAN_ERROR
    _SEARCH_MATCH_CACHE_KEY = None
    _SEARCH_MATCH_CACHE = []


def _selected_context_filter_identifiers(prefs: Any) -> set[str]:
    value = getattr(prefs, "operator_search_context_filters", set())
    try:
        return {str(item) for item in value}
    except TypeError:
        return set()


def _record_matches_context_filters(item: Any, selected: set[str]) -> bool:
    """Match saved presets against selected context tags.

    Context filters are optional discovery aids, not execution restrictions.
    They narrow saved AllPie presets only. Live Blender operators remain visible
    because they do not have AllPie context metadata until captured or saved.
    Multiple selected filters use OR semantics.
    """
    if not selected:
        return True
    if str(getattr(item, "source_kind", "")) != "PRESET":
        return True
    try:
        contexts = json.loads(getattr(item, "contexts_json", "[]") or "[]")
    except Exception:
        contexts = []
    try:
        categories = json.loads(getattr(item, "categories_json", "[]") or "[]")
    except Exception:
        categories = []

    folded_contexts = {str(value).strip().casefold() for value in contexts if str(value).strip()}
    folded_categories = {str(value).strip().upper() for value in categories if str(value).strip()}
    for identifier in selected:
        if identifier == "UNASSIGNED":
            if not folded_contexts:
                return True
        elif identifier == "OTHER":
            if "OTHER" in folded_categories:
                return True
        else:
            context_name = menu_data.keymap_value(identifier).casefold()
            if context_name and context_name in folded_contexts:
                return True
    return False


def _operator_record_from_live_rna(operator_id: str) -> Dict[str, str] | None:
    """Build minimal catalog metadata for a currently registered RNA operator.

    The searchable catalog intentionally excludes some generic search
    operators. Operators captured from a specific Blender button must still be
    saveable, because the user explicitly selected that button and its RNA
    definition is available independently of catalog enumeration.
    """
    try:
        from . import operator_setup
        rna = operator_setup._operator_rna(operator_id)
    except Exception:
        return None

    module_name = operator_id.partition(".")[0]
    name = str(getattr(rna, "name", "") or _humanize_operator_id(operator_id)).strip()
    description = str(getattr(rna, "description", "") or "").strip()
    return {
        "operator_id": operator_id,
        "name": name,
        "description": description,
        "module": module_name,
        "display_name": name,
    }


def _resolve_operator_record(operator_id: str) -> Dict[str, str] | None:
    """Resolve metadata from the browser cache or the live Blender RNA registry."""
    record = _OPERATOR_INFO.get(operator_id)
    if record is not None:
        return record

    # Prefer direct RNA lookup. It also handles registered operators which are
    # intentionally excluded from the searchable catalog, without forcing an
    # expensive full scan every time a user captures one of those buttons.
    record = _operator_record_from_live_rna(operator_id)
    if record is not None:
        return record

    # Keep the historical refresh fallback for operators from add-ons enabled
    # after the initial catalog scan. If Blender can no longer resolve the
    # operator's RNA, the refresh will not make a stale button reference valid.
    _refresh_operator_catalog()
    return _OPERATOR_INFO.get(operator_id)


def _add_operator_to_allpie(
    context: Any,
    *,
    operator_id: str,
    target_menu_id: str = "",
    slot_number: int = 1,
    spaced: bool = False,
    context_name: str = "",
    properties: Mapping[str, Any] | None = None,
    property_defaults: Mapping[str, Any] | None = None,
    invoke: bool = True,
    name_override: str = "",
    search_name: str = "",
    additional_context_names: Any = (),
) -> bool:
    """Create/reuse a configured action preset, optionally assigning it to a menu slot."""
    prefs = _preferences_from_context(context)
    draft_mode = bool(prefs is not None and getattr(prefs, "editor_dirty", False))
    if draft_mode:
        if not target_menu_id or prefs.editor_active_menu_id != target_menu_id:
            raise RuntimeError(
                "Apply or discard the current menu draft before adding an operator outside this menu"
            )
        from . import menu_editor
        config = menu_editor.get_menu_operation_config(prefs, target_menu_id)
    else:
        config = ConfigRuntime.get_config_copy()
    record = _resolve_operator_record(operator_id)
    if record is None:
        raise RuntimeError("The selected Blender operator is no longer available. Refresh the catalog.")

    merged_context_names = list(menu_data.keymap_contexts(context_name))
    for value in additional_context_names or ():
        name = str(value or "").strip()
        if name and name.casefold() not in {item.casefold() for item in merged_context_names}:
            merged_context_names.append(name)

    action_id, created = operator_data.create_or_reuse_blender_operator(
        config,
        operator_id=operator_id,
        name=name_override or record["name"],
        description=record["description"],
        context_name=context_name,
        context_names=merged_context_names,
        properties=properties or {},
        invoke=invoke,
        search_name=search_name or record["name"],
        property_defaults=property_defaults,
    )

    if target_menu_id:
        if prefs is None:
            raise RuntimeError("AllPie preferences are unavailable")
        if not 1 <= int(slot_number) <= 8:
            raise ValueError("Menu slot number must be between 1 and 8")
        menu_container, local_menu_id = menu_data.get_menu_container(config, target_menu_id)
        menu = menu_container[local_menu_id]
        if spaced and not menu_data.spaced_slots_enabled(menu):
            raise RuntimeError("Spaced Slots are disabled for the target menu")
        slot_field = "spaced_slots" if spaced else "slots"
        menu.setdefault(slot_field, {})[str(slot_number)] = action_id

    # Ensure the preset was actually persisted before publishing any UI state.
    # This guards against a stale generated ID or an unexpected normalization
    # difference between the draft and the active registry.
    try:
        operator_data.get_operator(config, action_id)
    except KeyError as error:
        raise RuntimeError(f"Operator preset '{action_id}' was not created in the configuration") from error

    if draft_mode:
        from . import menu_editor
        menu_editor.store_menu_operation_draft(
            prefs,
            config,
            slot_assignment=(int(slot_number), bool(spaced), action_id),
        )
    else:
        ConfigRuntime.replace_and_save_configuration(config)

    if prefs is not None:
        context_status = f"in {context_name}" if context_name else "for all menu contexts"
        prefs.operator_search_last_added = f"{name_override or record['name']} {'added' if created else 'reused'} {context_status}"
        prefs.operator_search_config_generation = -1
        prefs.operator_search_config_fingerprint = ""
        if not draft_mode:
            if target_menu_id:
                from . import menu_editor
                prefs.editor_active_menu_id = target_menu_id
                try:
                    prefs.editor_category = menu_data.category_for_menu(config, target_menu_id)
                except Exception:
                    pass
                prefs.editor_config_generation = -1
                menu_editor._ensure_editor_state(prefs)
    return created



# Blender exposes the operator associated with a right-clicked UI button via
# Context.button_operator. Keep the context-menu integration here so it uses
# the same catalog and persistence path as the existing operator editor.
_BUTTON_CONTEXT_MENU_STATE_KEY = "_allpie_button_context_menu_callback"


def _operator_id_from_button_rna(identifier: str) -> str:
    """Convert an RNA operator type ID (MESH_OT_foo) to bpy.ops ID form."""
    identifier = str(identifier or "").strip()
    module_name, separator, operator_name = identifier.partition("_OT_")
    if not separator or not module_name or not operator_name:
        return ""
    return f"{module_name.lower()}.{operator_name.lower()}"


_BRUSH_ASSET_OPERATOR_ID = "brush.asset_activate"
_BRUSH_PAINT_SETTINGS_BY_MODE = {
    # Blender mesh sculpt and paint modes.
    "SCULPT": "sculpt",
    "PAINT_TEXTURE": "image_paint",
    "PAINT_VERTEX": "vertex_paint",
    "PAINT_WEIGHT": "weight_paint",
    # Curves and Grease Pencil paint modes available in Blender 5.x.
    "SCULPT_CURVES": "curves_sculpt",
    "PAINT_GPENCIL": "gpencil_paint",
    "PAINT_GREASE_PENCIL": "gpencil_paint",
    "SCULPT_GPENCIL": "gpencil_sculpt_paint",
    "SCULPT_GREASE_PENCIL": "gpencil_sculpt_paint",
    "VERTEX_GPENCIL": "gpencil_vertex_paint",
    "VERTEX_GREASE_PENCIL": "gpencil_vertex_paint",
    "WEIGHT_GPENCIL": "gpencil_weight_paint",
    "WEIGHT_GREASE_PENCIL": "gpencil_weight_paint",
}


def _capture_active_brush_asset(context: Any) -> Dict[str, Any] | None:
    """Read the asset reference for the brush activated by the Asset Shelf.

    Blender's built-in brush Asset Shelves activate the clicked asset before
    drawing their context menu (ACTIVATE_FOR_CONTEXT_MENU). The
    brush.asset_activate button itself can therefore expose default/empty RNA
    properties even though the selected brush is available from the active
    mode's Paint.brush_asset_reference.
    """
    mode = str(getattr(context, "mode", "") or "").upper()
    area = getattr(context, "area", None)
    if str(getattr(area, "type", "") or "").upper() == "IMAGE_EDITOR":
        space = getattr(context, "space_data", None)
        if space is None:
            try:
                space = area.spaces.active
            except Exception:
                space = None
        if str(getattr(space, "mode", "") or "").upper() == "PAINT":
            mode = "PAINT_TEXTURE"

    paint_settings_name = _BRUSH_PAINT_SETTINGS_BY_MODE.get(mode)
    if not paint_settings_name:
        return None

    scene = getattr(context, "scene", None)
    tool_settings = getattr(scene, "tool_settings", None) if scene is not None else None
    if tool_settings is None:
        tool_settings = getattr(context, "tool_settings", None)
    if tool_settings is None:
        try:
            tool_settings = bpy.context.scene.tool_settings
        except (AttributeError, ReferenceError, TypeError):
            tool_settings = None
    if tool_settings is None:
        return None

    paint_settings = getattr(tool_settings, paint_settings_name, None)
    if paint_settings is None:
        return None

    brush = getattr(paint_settings, "brush", None)
    asset_reference = getattr(paint_settings, "brush_asset_reference", None)
    if brush is None or asset_reference is None:
        return None

    try:
        library_type = str(asset_reference.asset_library_type or "").strip().upper()
        library_identifier = str(asset_reference.asset_library_identifier or "").strip()
        relative_identifier = str(asset_reference.relative_asset_identifier or "").strip()
        brush_name = str(brush.name or "").strip()
    except (AttributeError, ReferenceError, TypeError, ValueError):
        return None

    if library_type not in {"LOCAL", "ESSENTIALS", "ONLINE_ESSENTIALS", "CUSTOM"}:
        return None
    if not relative_identifier:
        return None
    if library_type == "CUSTOM" and not library_identifier:
        return None

    relative_identifier = relative_identifier.replace("\\", "/")
    if not brush_name:
        brush_name = relative_identifier.rsplit("/", 1)[-1] or "Brush Asset"

    return {
        "name": brush_name,
        "properties": {
            "asset_library_type": library_type,
            "asset_library_identifier": library_identifier,
            "relative_asset_identifier": relative_identifier,
        },
    }


def _capture_button_operator(context: Any) -> Dict[str, Any] | None:
    """Capture an operator button's serializable, non-default RNA properties."""
    button_operator = getattr(context, "button_operator", None)
    if button_operator is None:
        return None

    button_rna = getattr(button_operator, "bl_rna", None)
    operator_id = _operator_id_from_button_rna(
        getattr(button_rna, "identifier", "")
    )
    if not operator_id or operator_id.startswith("allpie."):
        return None

    from . import operator_setup, operator_properties

    rna = operator_setup._operator_rna(operator_id)
    schema = operator_properties.build_property_specs(operator_id, rna.properties)
    captured = {}
    unsupported = [
        str(item.get("name") or item.get("identifier") or "Unknown property")
        for item in schema.get("unsupported", ())
    ]
    for spec in schema.get("properties", ()):
        identifier = str(spec.get("identifier", ""))
        if not identifier:
            continue
        try:
            value = operator_properties.json_safe_value(
                getattr(button_operator, identifier)
            )
        except Exception:
            # The setup dialog will report RNA fields that cannot be represented
            # by AllPie's JSON-backed property controls.
            unsupported_name = str(spec.get("name") or identifier)
            if unsupported_name not in unsupported:
                unsupported.append(unsupported_name)
            continue

        # AllPie stores only values that differ from Blender's defaults. This
        # avoids generating duplicate presets merely because a UI button
        # materializes every RNA property with its default value.
        if value != spec.get("default"):
            captured[identifier] = value

    unsupported = list(dict.fromkeys(unsupported))

    operator_name = str(getattr(rna, "name", "") or operator_id)
    if operator_id == _BRUSH_ASSET_OPERATOR_ID:
        # Asset Shelf activation stores its asset reference in the active Paint
        # settings. The button operator may still contain empty defaults, so
        # overwrite those with the selected brush's authoritative reference.
        brush_capture = _capture_active_brush_asset(context)
        if brush_capture is not None:
            captured.update(brush_capture["properties"])
            operator_name = brush_capture["name"]

        # Never create a brush preset with an empty asset path. Such a preset
        # would later fail with "No asset found at path \"\"" at execution.
        relative_identifier = str(captured.get("relative_asset_identifier", "") or "").strip()
        if not relative_identifier:
            return None
        library_type = str(captured.get("asset_library_type", "LOCAL") or "LOCAL").upper()
        library_identifier = str(captured.get("asset_library_identifier", "") or "").strip()
        if library_type == "CUSTOM" and not library_identifier:
            return None

    return {
        "operator_id": operator_id,
        "properties": captured,
        "unsupported": unsupported,
        "name": operator_name,
    }


def _context_name_from_button(context: Any) -> str:
    """Infer the AllPie catalog context from the area under the right-click."""
    area = getattr(context, "area", None)
    area_type = str(getattr(area, "type", "") or "")

    if area_type == "VIEW_3D":
        mode_names = {
            "OBJECT": "Object Mode",
            "EDIT_MESH": "Mesh",
            "SCULPT": "Sculpt",
            "PAINT_TEXTURE": "Image Paint",
            "PAINT_VERTEX": "Vertex Paint",
            "PAINT_WEIGHT": "Weight Paint",
        }
        mode_name = mode_names.get(str(getattr(context, "mode", "") or ""))
        if mode_name:
            return mode_name

    elif area_type == "IMAGE_EDITOR":
        space = getattr(context, "space_data", None)
        if space is None:
            try:
                space = area.spaces.active
            except Exception:
                space = None
        # Blender 5.x exposes the UV/Image Editor mode as SpaceImageEditor.mode.
        # ui_mode is a separate VIEW/PAINT/MASK setting and therefore cannot be
        # used to identify UV editing reliably.
        editor_mode = str(getattr(space, "mode", "") or "").upper()
        show_uv = bool(getattr(space, "show_uvedit", False))
        ui_type = str(getattr(area, "ui_type", "") or "").upper()
        if editor_mode == "UV" or show_uv or ui_type in {"UV", "UV_EDITOR"}:
            return "UV Editor"
        if editor_mode in {"PAINT", "MASK"}:
            return "Image"
        return "Image"

    elif area_type == "NODE_EDITOR":
        return "Node Editor"

    # Operator buttons in Properties, Outliner and other panels still belong
    # to the active object mode. Use the mode only after editor-specific
    # contexts have been handled above.
    mode_names = {
        "OBJECT": "Object Mode",
        "EDIT_MESH": "Mesh",
        "SCULPT": "Sculpt",
        "PAINT_TEXTURE": "Image Paint",
        "PAINT_VERTEX": "Vertex Paint",
        "PAINT_WEIGHT": "Weight Paint",
    }
    mode_name = mode_names.get(str(getattr(context, "mode", "") or ""))
    if mode_name:
        return mode_name

    # Unknown/less common editors do not receive a guessed tag. An untagged
    # preset remains available in every menu and can still be found unfiltered.
    return ""


def _button_operator_id(button_operator: Any) -> str:
    button_rna = getattr(button_operator, "bl_rna", None)
    return _operator_id_from_button_rna(getattr(button_rna, "identifier", ""))


def _allpie_slot_target_from_button(context: Any) -> Dict[str, Any] | None:
    """Recognize an AllPie menu-slot button in Preferences for its RMB menu."""
    button_operator = getattr(context, "button_operator", None)
    if button_operator is None:
        return None
    operator_id = _button_operator_id(button_operator)
    if operator_id not in {
        "allpie.search_blender_operator",
        "allpie.setup_blender_operator",
        "allpie.menu_editor_pick_action",
    }:
        return None
    try:
        menu_id = str(getattr(button_operator, "target_menu_id", "") or "")
        slot_number = int(getattr(button_operator, "slot_number", 0) or 0)
        spaced = bool(getattr(button_operator, "spaced", False))
        button_action_id = str(getattr(button_operator, "assigned_action_id", "") or "")
    except (AttributeError, TypeError, ValueError, ReferenceError):
        return None
    if not menu_id or not 1 <= slot_number <= 8:
        return None

    prefs = _preferences_from_context(context)
    try:
        if prefs is not None and getattr(prefs, "editor_dirty", False):
            from . import menu_editor
            config = menu_editor.get_menu_operation_config(prefs, menu_id)
        else:
            config = ConfigRuntime.get_config_copy()
        menu = menu_data.get_menu(config, menu_id)
    except Exception:
        return None

    slot_field = "spaced_slots" if spaced else "slots"
    configured_action_id = str(menu.get(slot_field, {}).get(str(slot_number), "") or "")
    action_id = button_action_id or configured_action_id
    has_action = bool(action_id or configured_action_id)
    can_configure = False
    if action_id:
        try:
            _container, _legacy_id, owner_addon = operator_data.get_action_container(config, action_id)
            can_configure = owner_addon is None
        except Exception:
            can_configure = False

    return {
        "menu_id": menu_id,
        "slot_number": slot_number,
        "spaced": spaced,
        "has_action": has_action,
        "action_id": action_id,
        "can_configure": can_configure,
    }


def draw_button_context_menu(self: Any, context: Any) -> None:
    """Add AllPie's capture/assignment entries to Blender's shared RMB menu."""
    layout = self.layout

    # Slot buttons stay visually simple. Their right-click menu exposes the
    # less-frequent Configure and Clear actions without a permanent gear.
    slot_target = _allpie_slot_target_from_button(context)
    if slot_target:
        layout.separator()
        if slot_target["has_action"] and slot_target["can_configure"]:
            configure = layout.operator(
                "allpie.setup_blender_operator",
                text="Configure AllPie Action",
                icon="PREFERENCES",
            )
            configure.action_id = slot_target["action_id"]
            configure.operator_id = ""
            configure.create_new_action = False
            configure.source_action_id = ""
            configure.prefill_from_action = False
            configure.source_contexts_json = "[]"
            configure.expose_preset_name = False
            configure.target_menu_id = slot_target["menu_id"]
            configure.slot_number = slot_target["slot_number"]
            configure.spaced = slot_target["spaced"]
            configure.context_name = ""
            configure.capture_button_properties = False
            configure.button_properties_json = "{}"
            configure.button_unsupported_properties_json = "[]"

        if slot_target["has_action"]:
            clear = layout.operator(
                "allpie.menu_editor_clear_slot",
                text="Clear AllPie Slot",
                icon="X",
            )
            clear.target_menu_id = slot_target["menu_id"]
            clear.slot_number = slot_target["slot_number"]
            clear.spaced = slot_target["spaced"]

        return

    try:
        captured = _capture_button_operator(context)
    except Exception:
        # Context menus are drawn for many button types. An unsupported or
        # temporarily unavailable RNA operator must not break Blender's menu.
        return
    if not captured:
        button_operator_id = _button_operator_id(getattr(context, "button_operator", None))
        if button_operator_id == _BRUSH_ASSET_OPERATOR_ID:
            layout.separator()
            unavailable = layout.row()
            unavailable.enabled = False
            unavailable.label(
                text="Could not read the selected brush asset reference",
                icon="ERROR",
            )
        return

    context_name = _context_name_from_button(context)
    layout.separator()

    add_to_menu = layout.operator(
        "allpie.add_operator_to_menu",
        text="Add to AllPie Menu",
        icon="MENU_PANEL",
    )
    add_to_menu.operator_id = captured["operator_id"]
    add_to_menu.operator_label = str(captured.get("name", "") or "")[:64]
    add_to_menu.context_name = context_name
    add_to_menu.button_properties_json = json.dumps(
        captured.get("properties", {}), sort_keys=True, separators=(",", ":")
    )
    add_to_menu.button_unsupported_properties_json = json.dumps(
        captured.get("unsupported", []), separators=(",", ":")
    )


def _defer_allpie_operator(context: Any, operator_name: str, properties: Mapping[str, Any]) -> None:
    """Invoke an AllPie popup/dialog after the current popup handler has closed.

    Nested WindowManager popups otherwise stack above one another. Deferring to
    Blender's next UI cycle lets the current operator return FINISHED first,
    preserving the originating editor context while avoiding orphaned parent
    popups after the user continues the assignment workflow.
    """
    window = getattr(context, "window", None)
    area = getattr(context, "area", None)
    region = getattr(context, "region", None)
    operator_properties = dict(properties)

    def invoke_after_popup_closes():
        try:
            operator = getattr(bpy.ops.allpie, operator_name)
        except Exception as error:
            print(f"[AllPie] Could not find deferred operator '{operator_name}': {error}")
            return None

        # Preserve the exact originating window/area/region when those RNA
        # references are still alive. If Blender invalidated a child context
        # while closing the popup, progressively fall back to a wider override.
        overrides = []
        if window is not None and area is not None and region is not None:
            overrides.append({"window": window, "area": area, "region": region})
        if window is not None and area is not None:
            overrides.append({"window": window, "area": area})
        if window is not None:
            overrides.append({"window": window})
        overrides.append({})

        last_error = None
        for override in overrides:
            try:
                if override:
                    with bpy.context.temp_override(**override):
                        result = operator("INVOKE_DEFAULT", **operator_properties)
                else:
                    result = operator("INVOKE_DEFAULT", **operator_properties)
                # Blender operators commonly report a poll/context failure as
                # {'CANCELLED'} instead of raising an exception. Treat that as
                # a failed override and try the next, less restrictive context.
                if isinstance(result, set) and "CANCELLED" in result and not (result & {"FINISHED", "RUNNING_MODAL"}):
                    last_error = RuntimeError(
                        f"deferred operator '{operator_name}' returned CANCELLED"
                    )
                    continue
                return None
            except (ReferenceError, RuntimeError, TypeError, AttributeError) as error:
                last_error = error

        print(
            f"[AllPie] Could not continue the deferred operator assignment "
            f"'{operator_name}': {last_error}"
        )
        return None

    try:
        bpy.app.timers.register(invoke_after_popup_closes, first_interval=0.0)
    except Exception as error:
        raise RuntimeError(f"Could not schedule the next AllPie assignment step: {error}") from error


class ALLPIE_OT_add_operator_to_menu(Operator):
    """Choose an AllPie menu, then select a destination in its radial layout."""

    bl_idname = "allpie.add_operator_to_menu"
    bl_label = "Add Operator to AllPie Menu"
    bl_description = "Choose a menu in this Blender context, then assign by clicking a radial direction"
    bl_options = {"INTERNAL"}

    operator_id: StringProperty(options={"HIDDEN"})
    operator_label: StringProperty(options={"HIDDEN"})
    context_name: StringProperty(options={"HIDDEN"})
    button_properties_json: StringProperty(options={"HIDDEN"})
    button_unsupported_properties_json: StringProperty(options={"HIDDEN"})
    available_menus_json: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before assigning an operator")
            return {"CANCELLED"}
        try:
            config = ConfigRuntime.get_config_copy()
            records = menu_data.iter_enabled_menus_for_context(config, self.context_name)
            self.available_menus_json = json.dumps(
                [
                    {
                        "menu_id": item["menu_id"],
                        "name": item["name"],
                        "keymap": item["keymap"],
                        "owner_addon": item.get("owner_addon", ""),
                    }
                    for item in records
                ],
                separators=(",", ":"),
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not find AllPie menus for this context: {error}")
            return {"CANCELLED"}
        return context.window_manager.invoke_popup(self, width=380)

    def draw(self, context):
        layout = self.layout
        title = self.context_name or "Current Blender Context"
        layout.label(text=f"Menus registered in {title}", icon="MENU_PANEL")
        try:
            records = json.loads(self.available_menus_json or "[]")
        except Exception:
            records = []
        if not records:
            layout.label(text="No enabled AllPie menus are registered in this context.", icon="INFO")
            layout.label(text="Create or enable a menu in Preferences → Menus.")
            return

        for record in records:
            row = layout.row(align=True)
            choose = row.operator(
                "allpie.choose_operator_menu",
                text=str(record.get("name", record.get("menu_id", "Menu"))),
                icon="MENU_PANEL",
            )
            choose.menu_id = str(record.get("menu_id", ""))
            choose.operator_id = self.operator_id
            choose.operator_label = self.operator_label
            choose.context_name = str(record.get("keymap", ""))
            choose.button_properties_json = self.button_properties_json
            choose.button_unsupported_properties_json = self.button_unsupported_properties_json
            owner = str(record.get("owner_addon", "") or "")
            if owner:
                row.label(text=owner, icon="PLUGIN")

        if not self.context_name:
            layout.separator()
            layout.label(text="Blender's current editor context could not be identified; all enabled menus are shown.", icon="INFO")

    def execute(self, context):
        return {"CANCELLED"}


class ALLPIE_OT_choose_operator_menu(Operator):
    """Open the selected AllPie menu in radial assignment mode."""

    bl_idname = "allpie.choose_operator_menu"
    bl_label = "Choose AllPie Menu"
    bl_options = {"INTERNAL"}

    menu_id: StringProperty(options={"HIDDEN"})
    operator_id: StringProperty(options={"HIDDEN"})
    operator_label: StringProperty(options={"HIDDEN"})
    context_name: StringProperty(options={"HIDDEN"})
    button_properties_json: StringProperty(options={"HIDDEN"})
    button_unsupported_properties_json: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        try:
            _defer_allpie_operator(
                context,
                "begin_radial_assignment",
                {
                    "menu_id": self.menu_id,
                    "operator_id": self.operator_id,
                    "operator_label": self.operator_label,
                    "context_name": self.context_name,
                    "button_properties_json": self.button_properties_json,
                    "button_unsupported_properties_json": self.button_unsupported_properties_json,
                },
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not start radial assignment mode: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class ALLPIE_OT_begin_radial_assignment(Operator):
    """Open the selected menu's real radial layout in assignment mode."""

    bl_idname = "allpie.begin_radial_assignment"
    bl_label = "Assign Operator to Radial Menu"
    bl_options = {"INTERNAL"}

    menu_id: StringProperty(options={"HIDDEN"})
    operator_id: StringProperty(options={"HIDDEN"})
    operator_label: StringProperty(options={"HIDDEN"})
    context_name: StringProperty(options={"HIDDEN"})
    button_properties_json: StringProperty(options={"HIDDEN"})
    button_unsupported_properties_json: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before assigning an operator")
            return {"CANCELLED"}

        try:
            config = ConfigRuntime.get_config_copy()
            menu = menu_data.get_menu(config, self.menu_id)
            if not menu.get("enabled", True):
                raise ValueError("The selected AllPie menu is disabled")
        except Exception as error:
            self.report({"ERROR"}, f"Could not prepare radial assignment: {error}")
            return {"CANCELLED"}

        # The captured button may live in a sidebar or Properties editor. Draw
        # the radial overlay in the invoking supported editor's WINDOW region;
        # prefer the current area, then a 3D View, then another supported editor.
        window = getattr(context, "window", None)
        screen = getattr(window, "screen", None) or getattr(context, "screen", None)
        if window is None or screen is None:
            self.report({"ERROR"}, "Could not find the Blender window for radial assignment")
            return {"CANCELLED"}

        supported = {"VIEW_3D", "IMAGE_EDITOR", "NODE_EDITOR"}
        candidates = []
        current_area = getattr(context, "area", None)
        if current_area is not None and getattr(current_area, "type", None) in supported:
            candidates.append(current_area)
        remaining = [
            area for area in getattr(screen, "areas", ())
            if area is not current_area and getattr(area, "type", None) in supported
        ]
        remaining.sort(key=lambda area: (0 if area.type == "VIEW_3D" else 1, area.x, area.y))
        candidates.extend(remaining)

        target_area = None
        target_region = None
        for area in candidates:
            region = next(
                (item for item in getattr(area, "regions", ()) if getattr(item, "type", None) == "WINDOW"),
                None,
            )
            if region is not None:
                target_area = area
                target_region = region
                break

        if target_area is None or target_region is None:
            self.report({"ERROR"}, "Radial assignment requires a 3D View, Image Editor or Node Editor")
            return {"CANCELLED"}

        try:
            with context.temp_override(
                window=window,
                area=target_area,
                region=target_region,
            ):
                result = bpy.ops.view3d.modal_radial_assignment(
                    "INVOKE_DEFAULT",
                    menu_id=self.menu_id,
                    assignment_operator_id=self.operator_id,
                    assignment_operator_label=self.operator_label,
                    assignment_context_name=self.context_name,
                    assignment_button_properties_json=self.button_properties_json or "{}",
                    assignment_button_unsupported_properties_json=(
                        self.button_unsupported_properties_json or "[]"
                    ),
                )
            if isinstance(result, set) and "CANCELLED" in result:
                self.report({"ERROR"}, "Blender could not open the radial assignment interface")
                return {"CANCELLED"}
        except Exception as error:
            self.report({"ERROR"}, f"Could not open radial assignment interface: {type(error).__name__}: {error}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def execute(self, context):
        return {"CANCELLED"}


class ALLPIE_OT_choose_operator_menu_slots(Operator):
    """Show Main and Spaced Slots for a chosen menu."""

    bl_idname = "allpie.choose_operator_menu_slots"
    bl_label = "Choose AllPie Slot"
    bl_options = {"INTERNAL"}

    menu_id: StringProperty(options={"HIDDEN"})
    operator_id: StringProperty(options={"HIDDEN"})
    operator_label: StringProperty(options={"HIDDEN"})
    context_name: StringProperty(options={"HIDDEN"})
    button_properties_json: StringProperty(options={"HIDDEN"})
    button_unsupported_properties_json: StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before assigning an operator")
            return {"CANCELLED"}
        try:
            config = ConfigRuntime.get_config_copy()
            menu = menu_data.get_menu(config, self.menu_id)
            if not menu.get("enabled", True):
                self.report({"ERROR"}, "The selected AllPie menu is disabled")
                return {"CANCELLED"}
        except Exception as error:
            self.report({"ERROR"}, f"The selected AllPie menu is no longer available: {error}")
            return {"CANCELLED"}
        return context.window_manager.invoke_popup(self, width=430)

    def _slot_label(self, config, menu, slot_number: int, spaced: bool) -> str:
        slot_field = "spaced_slots" if spaced else "slots"
        reference = menu.get(slot_field, {}).get(str(slot_number), "")
        if not reference:
            return "(Empty)"
        try:
            action = operator_data.get_operator(config, reference)
            return str(action.get("name") or reference)
        except Exception:
            return str(reference)

    def _draw_slots(self, layout, config, menu, spaced: bool) -> None:
        columns = layout.row(align=True)
        left = columns.column(align=True)
        right = columns.column(align=True)
        for index, slot_number in enumerate(range(1, 9)):
            column = left if index < 4 else right
            label = self._slot_label(config, menu, slot_number, spaced)
            button = column.operator(
                "allpie.assign_captured_operator_slot",
                text=f"Slot {slot_number}: {label}",
                icon="DOT" if label == "(Empty)" else "FILE_TICK",
                emboss=True,
            )
            button.menu_id = self.menu_id
            button.slot_number = slot_number
            button.spaced = spaced
            button.operator_id = self.operator_id
            button.operator_label = self.operator_label
            button.context_name = self.context_name
            button.button_properties_json = self.button_properties_json
            button.button_unsupported_properties_json = self.button_unsupported_properties_json

    def draw(self, context):
        layout = self.layout
        try:
            config = ConfigRuntime.get_config_copy()
            menu = menu_data.get_menu(config, self.menu_id)
        except Exception:
            layout.label(text="The selected menu is no longer available.", icon="ERROR")
            return

        layout.label(text=f"{menu.get('name', self.menu_id)} — Choose Slot", icon="MENU_PANEL")
        layout.label(text=f"Main Slots · {menu.get('keymap', 'Unknown Context')}", icon="GRID")
        self._draw_slots(layout, config, menu, False)
        layout.separator()

        spaced_enabled = menu_data.spaced_slots_enabled(menu)
        spaced_box = layout.box()
        spaced_box.enabled = spaced_enabled
        spaced_box.label(
            text="Spaced Slots" if spaced_enabled else "Spaced Slots (disabled)",
            icon="GRID" if spaced_enabled else "RADIOBUT_OFF",
        )
        if spaced_enabled:
            self._draw_slots(spaced_box, config, menu, True)
        else:
            disabled_row = spaced_box.row()
            disabled_row.enabled = False
            disabled_row.label(text="Enable Spaced Slots in the menu's Preferences to use these slots.", icon="INFO")

    def execute(self, context):
        return {"CANCELLED"}


class ALLPIE_OT_assign_captured_operator_slot(Operator):
    """Confirm replacement if needed, then open the operator setup dialog."""

    bl_idname = "allpie.assign_captured_operator_slot"
    bl_label = "Assign Captured Operator"
    bl_options = {"INTERNAL"}

    menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    operator_id: StringProperty(options={"HIDDEN"})
    operator_label: StringProperty(options={"HIDDEN"})
    context_name: StringProperty(options={"HIDDEN"})
    button_properties_json: StringProperty(options={"HIDDEN"})
    button_unsupported_properties_json: StringProperty(options={"HIDDEN"})
    existing_action_name: StringProperty(options={"HIDDEN"})
    deferred_step: BoolProperty(default=False, options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before assigning an operator")
            return {"CANCELLED"}

        # First invocation originates inside Choose Slot. Finish that popup
        # before opening the replace confirmation or Configure dialog.
        if not self.deferred_step:
            try:
                config = ConfigRuntime.get_config_copy()
                menu = menu_data.get_menu(config, self.menu_id)
                if not menu.get("enabled", True):
                    raise ValueError("The selected AllPie menu is disabled")
                slot_field = "spaced_slots" if self.spaced else "slots"
                if self.spaced and not menu_data.spaced_slots_enabled(menu):
                    raise ValueError("Spaced Slots are disabled for this menu")
                if not 1 <= int(self.slot_number) <= 8:
                    raise ValueError("Menu slot number must be between 1 and 8")
            except Exception as error:
                self.report({"ERROR"}, f"Could not inspect the selected slot: {error}")
                return {"CANCELLED"}

            try:
                _defer_allpie_operator(
                    context,
                    "assign_captured_operator_slot",
                    {
                        "menu_id": self.menu_id,
                        "slot_number": self.slot_number,
                        "spaced": self.spaced,
                        "operator_id": self.operator_id,
                        "operator_label": self.operator_label,
                        "context_name": self.context_name,
                        "button_properties_json": self.button_properties_json,
                        "button_unsupported_properties_json": self.button_unsupported_properties_json,
                        "deferred_step": True,
                    },
                )
            except Exception as error:
                self.report({"ERROR"}, f"Could not schedule the slot assignment: {error}")
                return {"CANCELLED"}
            return {"FINISHED"}

        # The deferred invocation now runs after Choose Slot has closed. It can
        # safely ask for replacement or continue directly to operator setup.
        try:
            config = ConfigRuntime.get_config_copy()
            menu = menu_data.get_menu(config, self.menu_id)
            if not menu.get("enabled", True):
                raise ValueError("The selected AllPie menu is disabled")
            slot_field = "spaced_slots" if self.spaced else "slots"
            if self.spaced and not menu_data.spaced_slots_enabled(menu):
                raise ValueError("Spaced Slots are disabled for this menu")
            existing_reference = str(menu.get(slot_field, {}).get(str(self.slot_number), "") or "")
            if existing_reference:
                try:
                    old_action = operator_data.get_operator(config, existing_reference)
                    self.existing_action_name = str(old_action.get("name") or existing_reference)
                except Exception:
                    self.existing_action_name = existing_reference
                return context.window_manager.invoke_confirm(self, event)
        except Exception as error:
            self.report({"ERROR"}, f"Could not inspect the selected slot: {error}")
            return {"CANCELLED"}
        return self.execute(context)

    def draw(self, context):
        self.layout.label(text=f"Slot {self.slot_number} currently contains '{self.existing_action_name}'.", icon="ERROR")
        self.layout.label(text="Replace it with the new operator after configuration?", icon="QUESTION")
        self.layout.label(text="Cancel leaves the current slot and operator library unchanged.", icon="INFO")

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before assigning an operator")
            return {"CANCELLED"}
        try:
            _defer_allpie_operator(
                context,
                "setup_blender_operator",
                {
                    "operator_id": self.operator_id,
                    "action_id": "",
                    "preset_name": self.operator_label[:64],
                    "create_new_action": True,
                    "source_action_id": "",
                    "prefill_from_action": False,
                    "expose_preset_name": True,
                    "source_contexts_json": "[]",
                    "target_menu_id": self.menu_id,
                    "slot_number": self.slot_number,
                    "spaced": self.spaced,
                    "context_name": self.context_name,
                    "capture_button_properties": True,
                    "button_properties_json": self.button_properties_json or "{}",
                    "button_unsupported_properties_json": self.button_unsupported_properties_json or "[]",
                    "invoke_operator": True,
                    "invalid_saved_values": "[]",
                    "replace_invalid_saved_values": False,
                    "unknown_saved_properties": "[]",
                    "remove_unknown_saved_properties": False,
                },
            )
        except Exception as error:
            self.report({"ERROR"}, f"Could not schedule Configure Operator Preset: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


def register_button_context_menu() -> None:
    """Register AllPie's entry without replacing Blender or other addon entries.

    Keep the callback reference in Blender's driver namespace so an in-place
    module reload can remove the previous function object before appending the
    refreshed one. This prevents duplicate entries after extension updates.
    """
    menu_type = getattr(bpy.types, "UI_MT_button_context_menu", None)
    if menu_type is None:
        print("[AllPie] Blender button context menu hook is unavailable")
        return

    namespace = bpy.app.driver_namespace
    previous_callback = namespace.get(_BUTTON_CONTEXT_MENU_STATE_KEY)
    if previous_callback is not None:
        try:
            menu_type.remove(previous_callback)
        except (RuntimeError, ValueError, TypeError):
            pass

    try:
        menu_type.append(draw_button_context_menu)
        namespace[_BUTTON_CONTEXT_MENU_STATE_KEY] = draw_button_context_menu
    except Exception as error:
        namespace.pop(_BUTTON_CONTEXT_MENU_STATE_KEY, None)
        print(f"[AllPie] Could not register button context menu entry: {error}")


def unregister_button_context_menu() -> None:
    """Remove only AllPie's callback from Blender's shared button context menu."""
    menu_type = getattr(bpy.types, "UI_MT_button_context_menu", None)
    namespace = getattr(bpy.app, "driver_namespace", {})
    callback = namespace.pop(_BUTTON_CONTEXT_MENU_STATE_KEY, None)
    if callback is None:
        callback = draw_button_context_menu
    if menu_type is not None:
        try:
            menu_type.remove(callback)
        except (RuntimeError, ValueError, TypeError):
            pass


def _matching_search_indices(prefs: Any) -> List[int]:
    """Return searchable result indices for query text and optional context filters."""
    global _SEARCH_MATCH_CACHE_KEY, _SEARCH_MATCH_CACHE
    needle = str(getattr(prefs, "operator_search_query", "") or "").casefold().strip()
    generation = int(getattr(prefs, "operator_search_catalog_generation", -1))
    config_generation = int(getattr(prefs, "operator_search_config_generation", -1))
    filters = tuple(sorted(_selected_context_filter_identifiers(prefs)))
    cache_key = (generation, config_generation, needle, len(prefs.operator_search_items), filters)
    if cache_key == _SEARCH_MATCH_CACHE_KEY:
        return _SEARCH_MATCH_CACHE

    matches: List[int] = []
    for index, item in enumerate(prefs.operator_search_items):
        if filters and not _record_matches_context_filters(item, set(filters)):
            continue
        haystack = f"{item.name} {getattr(item, 'search_alias', '')} {item.operator_id} {item.description} {item.module} {item.context_summary}".casefold()
        if not needle or needle in haystack:
            matches.append(index)
    _SEARCH_MATCH_CACHE_KEY = cache_key
    _SEARCH_MATCH_CACHE = matches
    return _SEARCH_MATCH_CACHE


def update_operator_search_query(self: Any, context: Any) -> None:
    """Refresh matching live operators and keep selection on the first result."""
    _refresh_live_operator_search_items(self)
    matches = _matching_search_indices(self)
    self.operator_search_active_index = matches[0] if matches else 0


def _get_bundled_action_ids() -> frozenset[str]:
    """Read and validate the shipped preset IDs, failing closed on any error.

    A missing or malformed bundled catalogue must never be interpreted as an
    empty protection set: doing so would make shipped presets look user-owned
    and expose them to deletion. Failed reads are deliberately not cached, so
    a later retry can recover after the underlying problem is corrected.
    """
    global _BUILTIN_ACTION_IDS
    if _BUILTIN_ACTION_IDS is not None:
        return _BUILTIN_ACTION_IDS
    try:
        _BUILTIN_ACTION_IDS = operator_data.load_bundled_action_ids(ConfigRuntime.DEFAULT_CONFIG_PATH)
    except Exception as error:
        raise RuntimeError(
            "Cannot verify bundled AllPie presets. Preset deletion and cleanup are disabled "
            f"until the bundled configuration can be read: {error}"
        ) from error
    return _BUILTIN_ACTION_IDS


class AllPieOperatorSearchItem(PropertyGroup):
    operator_id: StringProperty()
    name: StringProperty()
    search_alias: StringProperty()
    description: StringProperty()
    module: StringProperty()
    source_kind: StringProperty()
    action_id: StringProperty()
    contexts_json: StringProperty(default="[]")
    categories_json: StringProperty(default="[]")
    context_summary: StringProperty()
    can_edit: BoolProperty(default=False)
    can_delete: BoolProperty(default=False)


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
        prefs = data
        row = layout.row(align=True)
        setup = row.operator(
            "allpie.setup_blender_operator",
            text=item.name,
            icon="CHECKMARK" if item.source_kind == "PRESET" else "BLENDER",
            emboss=True,
        )
        setup.operator_id = item.operator_id
        setup.action_id = ""
        setup.source_action_id = item.action_id
        setup.prefill_from_action = item.source_kind == "PRESET"
        setup.source_contexts_json = item.contexts_json
        setup.create_new_action = True
        setup.expose_preset_name = True
        # Live rows may include a module qualifier to distinguish duplicate
        # Blender labels. Start the editable preset name with Blender's actual
        # label; saved presets keep their canonical AllPie name.
        setup.preset_name = (
            item.search_alias or item.name
            if item.source_kind == "BLENDER"
            else item.name
        )
        setup.target_menu_id = prefs.operator_search_target_menu_id
        setup.slot_number = prefs.operator_search_target_slot
        setup.spaced = prefs.operator_search_target_spaced
        setup.context_name = prefs.operator_search_context_name
        setup.capture_button_properties = False
        setup.button_properties_json = "{}"
        setup.button_unsupported_properties_json = "[]"

        # Saved local presets can be edited in-place from the same picker.
        # This replaces the old standalone Preset Manager's Edit Properties
        # action without introducing a second management interface.
        if item.source_kind == "PRESET" and item.can_edit:
            edit = row.operator(
                "allpie.setup_blender_operator",
                text="",
                icon="PREFERENCES",
                emboss=True,
            )
            edit.action_id = item.action_id
            edit.operator_id = ""
            edit.create_new_action = False
            edit.source_action_id = ""
            edit.prefill_from_action = False
            edit.source_contexts_json = "[]"
            edit.expose_preset_name = True
            edit.preset_name = item.name
            edit.target_menu_id = prefs.operator_search_target_menu_id
            edit.slot_number = prefs.operator_search_target_slot
            edit.spaced = prefs.operator_search_target_spaced
            edit.context_name = prefs.operator_search_context_name
            edit.capture_button_properties = False
            edit.button_properties_json = "{}"
            edit.button_unsupported_properties_json = "[]"

        if item.source_kind == "PRESET" and item.can_delete:
            delete_column = row.column()
            delete_column.enabled = not bool(getattr(prefs, "editor_dirty", False))
            delete = delete_column.operator(
                "allpie.delete_user_action",
                text="",
                icon="TRASH",
                emboss=False,
            )
            delete.action_id = item.action_id
        row.label(text=item.context_summary or item.module, icon="TAG" if item.source_kind == "PRESET" else "PLUGIN")


class AllPieOperatorValidationItem(PropertyGroup):
    severity: StringProperty()
    location: StringProperty()
    message: StringProperty()


class ALLPIE_OT_delete_user_action(Operator):
    """Delete a user-created preset and clear all slots that reference it."""

    bl_idname = "allpie.delete_user_action"
    bl_label = "Delete Operator Preset"
    bl_description = "Delete this custom operator preset and clear any menu slots that use it"
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
            prefs.operator_search_config_fingerprint = ""
            prefs.operator_search_config_generation = -1
            prefs.operator_search_catalog_generation = -1
            prefs.editor_config_generation = -1
            if prefs.editor_active_menu_id:
                from . import menu_editor
                menu_editor._ensure_editor_state(prefs)
        self.report({"INFO"}, f"Deleted '{removed.get('name', self.action_id)}' and cleared {len(usages)} slot(s)")
        return {"FINISHED"}


class ALLPIE_OT_cleanup_unused_operator_presets(Operator):
    """Remove only user-created AllPie presets that no menu slot references."""

    bl_idname = "allpie.cleanup_unused_operator_presets"
    bl_label = "Clean Unused Presets"
    bl_description = (
        "Delete custom AllPie operator presets that are not assigned to any Main or Spaced slot; "
        "bundled and third-party presets are never removed"
    )
    bl_options = {"INTERNAL"}

    preview_count: IntProperty(default=0, min=0, options={"HIDDEN"})
    preview_names_json: StringProperty(default="[]", options={"HIDDEN"})
    candidate_ids_json: StringProperty(default="[]", options={"HIDDEN"})

    @staticmethod
    def _find_unused(
        config: Mapping[str, Any],
        bundled_ids: frozenset[str] | None = None,
    ) -> List[Dict[str, Any]]:
        """Return unused locally managed presets, excluding bundled and addon-owned actions."""
        if bundled_ids is None:
            bundled_ids = _get_bundled_action_ids()
        records = operator_data.iter_user_action_records(config, bundled_ids)
        return [record for record in records if int(record.get("usage_count", 0)) == 0]

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before cleaning presets")
            return {"CANCELLED"}

        try:
            bundled_ids = _get_bundled_action_ids()
            config = ConfigRuntime.get_config_copy()
            unused = self._find_unused(config, bundled_ids)
        except Exception as error:
            self.report({"ERROR"}, f"Could not inspect operator presets: {error}")
            return {"CANCELLED"}

        if not unused:
            self.report({"INFO"}, "No unused custom operator presets found")
            return {"CANCELLED"}

        self.preview_count = len(unused)
        self.candidate_ids_json = json.dumps(
            [str(record["action_id"]) for record in unused],
            ensure_ascii=False,
        )
        self.preview_names_json = json.dumps(
            [str(record.get("name") or record.get("operator_id") or record["action_id"]) for record in unused],
            ensure_ascii=False,
        )
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text=f"Delete {self.preview_count} unused custom preset(s)?",
            icon="TRASH",
        )
        layout.label(text="Only presets with zero Main and Spaced slot references will be removed.", icon="INFO")
        try:
            names = json.loads(self.preview_names_json or "[]")
        except (TypeError, ValueError):
            names = []
        if names:
            box = layout.box()
            for name in names[:8]:
                box.label(text=str(name)[:100], icon="DOT")
            if len(names) > 8:
                box.label(text=f"And {len(names) - 8} more preset(s)…")
        layout.label(text="Bundled AllPie and third-party presets are not affected.")

    def execute(self, context):
        prefs = _preferences_from_context(context)
        if prefs is not None and prefs.editor_dirty:
            self.report({"WARNING"}, "Apply or discard the current menu changes before cleaning presets")
            return {"CANCELLED"}

        try:
            bundled_ids = _get_bundled_action_ids()
            candidate_ids = json.loads(self.candidate_ids_json or "[]")
            if (
                not isinstance(candidate_ids, list)
                or not candidate_ids
                or len(candidate_ids) > 10000
                or any(not isinstance(value, str) or not value.strip() for value in candidate_ids)
            ):
                raise ValueError("The cleanup preview is invalid or expired; reopen Clean Unused Presets")

            config = ConfigRuntime.get_config_copy()
            # Recheck only the exact candidates shown in the confirmation
            # dialog. Newly-unused records wait for the next cleanup, while
            # candidates assigned during the dialog are preserved.
            removed = operator_data.remove_unused_user_presets(
                config,
                candidate_ids,
                bundled_ids,
            )
            if not removed:
                self.report({"INFO"}, "None of the previewed presets remain eligible for cleanup")
                return {"CANCELLED"}

            ConfigRuntime.replace_and_save_configuration(config)
        except Exception as error:
            self.report({"ERROR"}, f"Could not clean unused presets: {error}")
            return {"CANCELLED"}

        if prefs is not None:
            prefs.operator_search_config_fingerprint = ""
            prefs.operator_search_config_generation = -1
            prefs.operator_search_catalog_generation = -1
            prefs.editor_config_generation = -1
            if prefs.editor_active_menu_id:
                from . import menu_editor
                menu_editor._ensure_editor_state(prefs)

        self.report({"INFO"}, f"Removed {len(removed)} unused custom preset(s)")
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
    context_name: StringProperty(default="", options={"HIDDEN"})

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
                context_name=self.context_name.strip(),
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
            destination = f"in {self.context_name}" if self.context_name.strip() else "for all menu contexts"
            self.report({"INFO"}, f"{action} '{label}' to AllPie presets {destination}")
        return {"FINISHED"}


class ALLPIE_MT_operator_search_context_filters(Menu):
    bl_label = "Filter by Context"

    def draw(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None:
            return
        selected = _selected_context_filter_identifiers(prefs)
        layout = self.layout
        for identifier, label, _description, _flag in SEARCH_CONTEXT_FILTER_ITEMS:
            toggle = layout.operator(
                "allpie.toggle_operator_search_context_filter",
                text=label,
                icon="CHECKBOX_HLT" if identifier in selected else "CHECKBOX_DEHLT",
            )
            toggle.context_identifier = identifier
        layout.separator()
        clear = layout.operator("allpie.toggle_operator_search_context_filter", text="Clear Filters", icon="X")
        clear.clear_all = True


class ALLPIE_OT_toggle_operator_search_context_filter(Operator):
    bl_idname = "allpie.toggle_operator_search_context_filter"
    bl_label = "Toggle Operator Search Context Filter"
    bl_options = {"INTERNAL"}

    context_identifier: StringProperty(options={"HIDDEN"})
    clear_all: BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        global _SEARCH_MATCH_CACHE_KEY
        prefs = _preferences_from_context(context)
        if prefs is None:
            return {"CANCELLED"}
        selected = _selected_context_filter_identifiers(prefs)
        if self.clear_all:
            selected.clear()
        elif self.context_identifier:
            if self.context_identifier in selected:
                selected.remove(self.context_identifier)
            else:
                selected.add(self.context_identifier)
        prefs.operator_search_context_filters = selected
        _SEARCH_MATCH_CACHE_KEY = None
        matches = _matching_search_indices(prefs)
        prefs.operator_search_active_index = matches[0] if matches else 0
        return {"FINISHED"}


class ALLPIE_OT_search_blender_operator(Operator):
    """Open a unified search for saved AllPie presets and registered Blender operators."""

    bl_idname = "allpie.search_blender_operator"
    bl_label = "Search Operators"
    bl_description = "Choose or replace this slot action. Right-click for configuration and clearing options."
    bl_options = {"INTERNAL"}

    target_menu_id: StringProperty(options={"HIDDEN"})
    slot_number: IntProperty(min=1, max=8, default=1, options={"HIDDEN"})
    spaced: BoolProperty(default=False, options={"HIDDEN"})
    context_name: StringProperty(default="", options={"HIDDEN"})
    assigned_action_id: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        prefs = _preferences_from_context(context)
        draft_config = None
        if prefs is not None and prefs.editor_dirty:
            if not self.target_menu_id or prefs.editor_active_menu_id != self.target_menu_id:
                self.report({"WARNING"}, "Apply or discard the current menu draft before editing another menu or the Operator Library")
                return {"CANCELLED"}
            try:
                from . import menu_editor
                draft_config = menu_editor.get_menu_operation_config(prefs, self.target_menu_id)
            except Exception as error:
                self.report({"ERROR"}, f"Could not read the current menu draft: {error}")
                return {"CANCELLED"}

        if self.target_menu_id:
            if prefs is None:
                self.report({"ERROR"}, "AllPie preferences are unavailable")
                return {"CANCELLED"}
            try:
                config = draft_config if draft_config is not None else ConfigRuntime.get_config_copy()
                menu = menu_data.get_menu(config, self.target_menu_id)
            except (RuntimeError, KeyError) as error:
                self.report({"ERROR"}, f"Could not read the target menu: {error}")
                return {"CANCELLED"}
            self.context_name = str(menu.get("keymap", "Object Mode"))
        else:
            self.context_name = ""

        if prefs is None:
            self.report({"ERROR"}, "AllPie preferences are unavailable")
            return {"CANCELLED"}
        count = _ensure_operator_catalog()
        if not count and not ConfigRuntime.INITIALIZED:
            self.report({"WARNING"}, "No registered Blender operators or AllPie presets were found")
            return {"CANCELLED"}

        prefs.operator_search_query = ""
        # Filters refine this particular search session. Clear them on each
        # open so an old context selection cannot silently hide presets when
        # the user moves to a different menu or editor.
        prefs.operator_search_context_filters = set()
        _populate_search_items(
            prefs,
            config_override=draft_config,
        )
        _refresh_live_operator_search_items(prefs)
        prefs.operator_search_target_menu_id = self.target_menu_id
        prefs.operator_search_target_slot = self.slot_number
        prefs.operator_search_target_spaced = self.spaced
        prefs.operator_search_context_name = self.context_name
        matches = _matching_search_indices(prefs)
        prefs.operator_search_active_index = matches[0] if matches else 0
        return context.window_manager.invoke_popup(self, width=680)

    def draw(self, context):
        prefs = _preferences_from_context(context)
        if prefs is None:
            self.layout.label(text="AllPie preferences are unavailable", icon="ERROR")
            return
        layout = self.layout
        if prefs.operator_search_target_menu_id:
            layout.label(
                text=f"Choose Action for Slot {prefs.operator_search_target_slot} · {prefs.operator_search_context_name}",
                icon="ADD",
            )
        else:
            layout.label(text="Operator Library", icon="VIEWZOOM")

        search_row = layout.row(align=True)
        search_row.prop(
            prefs,
            "operator_search_query",
            text="",
            icon="VIEWZOOM",
            placeholder="Search by name or operator ID...",
        )
        search_row.menu(
            "ALLPIE_MT_operator_search_context_filters",
            text="",
            icon="ADD",
        )
        search_row.operator(
            "allpie.refresh_operator_catalog",
            text="",
            icon="FILE_REFRESH",
        )

        selected_filters = _selected_context_filter_identifiers(prefs)
        if selected_filters:
            filter_row = layout.row(align=True)
            filter_row.label(text="Filters:", icon="FILTER")
            labels = {identifier: label for identifier, label, _description, _flag in SEARCH_CONTEXT_FILTER_ITEMS}
            for identifier in sorted(selected_filters):
                remove = filter_row.operator(
                    "allpie.toggle_operator_search_context_filter",
                    text=labels.get(identifier, identifier),
                    icon="X",
                )
                remove.context_identifier = identifier
            filter_row.operator(
                "allpie.toggle_operator_search_context_filter",
                text="",
                icon="TRASH",
            ).clear_all = True

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
        if not matches:
            if not str(getattr(prefs, "operator_search_query", "") or "").strip():
                layout.label(text="Type to search registered Blender operators, or choose a saved preset.", icon="INFO")
            else:
                layout.label(text="No operators match this search.", icon="INFO")
        elif prefs.operator_search_target_menu_id:
            layout.label(text="Choose a preset or Blender operator. Configure it, then confirm to assign it to this slot.", icon="INFO")
        else:
            layout.label(text="Choose a saved preset or Blender operator, then configure and save it in the library.", icon="INFO")
        if selected_filters:
            layout.label(
                text="Context filters only narrow saved presets. Registered Blender operators remain searchable.",
                icon="INFO",
            )
        if _LIVE_OPERATOR_RESULTS_TRUNCATED:
            layout.label(text=f"Showing the first {_LIVE_OPERATOR_RESULT_LIMIT} Blender matches. Refine your search.", icon="INFO")
        if getattr(prefs, "operator_search_catalog_loading", False):
            layout.label(
                text="Discovering Blender operators. Results will appear as they are found.",
                icon="TIME",
            )
        elif getattr(prefs, "operator_search_catalog_error", ""):
            layout.label(
                text=f"Operator catalog scan issue: {prefs.operator_search_catalog_error}"[:160],
                icon="ERROR",
            )

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
    bl_label = "Refresh Operator Catalog"
    bl_description = "Rescan Blender and currently enabled add-on operators"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        from . import operator_setup
        from ..core import operator_validation
        operator_setup.refresh_special_search_catalogs()
        operator_setup.unregister_dynamic_property_groups()
        operator_validation.clear_operator_rna_cache()
        prefs = _preferences_from_context(context)
        count = _schedule_operator_catalog_scan(reset=True)
        if prefs is not None:
            prefs.operator_search_catalog_generation = -1
            prefs.operator_search_config_fingerprint = ""
            try:
                _populate_search_items(prefs, force=True)
            except Exception as error:
                self.report({"ERROR"}, f"Could not prepare operator search: {error}")
                return {"CANCELLED"}
        self.report({"INFO"}, f"Refreshing Blender operator catalog; {count} cached operator(s) available while new results load")
        return {"FINISHED"}


def draw_operator_validation(layout: Any, prefs: Any) -> None:
    """Draw RNA preset diagnostics in Configuration, not a separate tab."""
    panel_header, panel_body = layout.panel("AllPie_Operator_Preset_Diagnostics", default_closed=True)
    panel_header.label(text="Preset Diagnostics", icon="CHECKMARK")
    if panel_body is not None:
        validation_box = panel_body.box()
        validation_header = validation_box.row(align=True)
        validation_header.label(text="Validate saved presets")
        validation_header.operator("allpie.validate_operator_presets", text="Validate", icon="CHECKMARK")
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
            validation_box.label(text="Check saved presets against Blender's currently registered operators and RNA properties.", icon="INFO")


from . import operator_setup


CLASSES = (
    AllPieOperatorSearchItem,
    AllPieOperatorValidationItem,
    ALLPIE_UL_operator_search_results,
    ALLPIE_MT_operator_search_context_filters,
    ALLPIE_OT_toggle_operator_search_context_filter,
    ALLPIE_OT_delete_user_action,
    ALLPIE_OT_cleanup_unused_operator_presets,
    ALLPIE_OT_add_operator_to_menu,
    ALLPIE_OT_choose_operator_menu,
    ALLPIE_OT_begin_radial_assignment,
    ALLPIE_OT_choose_operator_menu_slots,
    ALLPIE_OT_assign_captured_operator_slot,
    ALLPIE_OT_select_blender_operator,
    ALLPIE_OT_search_blender_operator,
    ALLPIE_OT_refresh_operator_catalog,
    ALLPIE_OT_validate_operator_presets,
    *operator_setup.CLASSES,
)
