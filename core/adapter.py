"""Compatibility adapter between the compiled registry and legacy radial UI.

The current radial menu expects lists of dictionaries containing ``slot``,
``label``, ``operator``, ``invoke`` and ``props``. This module creates those
views once when the configuration cache is compiled. The radial modal code can
therefore continue using its existing data contract without reading JSON or
resolving action IDs while a menu is opening.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from .schema import CompiledConfig, OperatorPreset

LegacyMenu = List[dict]
LegacyMenuMap = Dict[str, LegacyMenu]
LegacyNameMap = Dict[str, str]


def _convert_slots(
    slots: Tuple[Optional[OperatorPreset], ...],
    order: Tuple[int, ...],
) -> LegacyMenu:
    """Convert a compiled eight-slot tuple to the radial engine's old list.

    Slot order is retained from the JSON object so the compatibility view
    preserves the legacy source-list ordering as well as each slot index.
    """
    result: LegacyMenu = []
    for index in order:
        action = slots[index]
        if action is None:
            continue
        result.append(
            {
                "slot": index,
                "label": action.name,
                "operator": action.operator_id,
                "invoke": action.invoke,
                "props": deepcopy(dict(action.properties)),
            }
        )
    return result


def build_legacy_views(compiled: CompiledConfig) -> tuple[LegacyMenuMap, LegacyMenuMap, LegacyNameMap]:
    """Build legacy radial-menu dictionaries from an already compiled cache.

    This function is called only when the active configuration is loaded or
    changed. The returned mappings are then kept alive for normal menu use.
    """
    menus: LegacyMenuMap = {}
    spaced_menus: LegacyMenuMap = {}
    menu_names: LegacyNameMap = {}

    for menu_id, menu in compiled.menus.items():
        menus[menu_id] = _convert_slots(menu.slots, menu.slot_order)
        menu_names[menu_id] = menu.name
        if menu.spaced_slots is not None and menu.spaced_slot_order is not None:
            spaced_menus[menu_id] = _convert_slots(menu.spaced_slots, menu.spaced_slot_order)

    return menus, spaced_menus, menu_names
