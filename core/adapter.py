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

from .schema import CompiledConfig, OperatorPreset, SLOT_COUNT

LegacyMenu = List[dict]
LegacyMenuMap = Dict[str, LegacyMenu]
LegacyNameMap = Dict[str, str]


def _convert_slots(
    slots: Tuple[Optional[OperatorPreset], ...],
) -> LegacyMenu:
    """Convert all eight compiled positions into drawable radial entries.

    Empty positions are deliberately retained. The radial UI must still show
    the complete pie when a menu has only a few assigned actions—or no actions
    at all—so users can understand the available directions and assign into
    those positions. Empty entries are harmless at execution time because they
    carry no operator identifier.
    """
    result: LegacyMenu = []
    for index in range(SLOT_COUNT):
        action = slots[index] if index < len(slots) else None
        if action is None:
            result.append(
                {
                    "slot": index,
                    "label": "Empty",
                    "operator": "",
                    "invoke": False,
                    "props": {},
                    "empty": True,
                }
            )
            continue
        result.append(
            {
                "slot": index,
                "label": action.name,
                "operator": action.operator_id,
                "invoke": action.invoke,
                "props": deepcopy(dict(action.properties)),
                "empty": False,
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
        menus[menu_id] = _convert_slots(menu.slots)
        menu_names[menu_id] = menu.name
        if menu.spaced_slots is not None and menu.spaced_slot_order is not None:
            spaced_menus[menu_id] = _convert_slots(menu.spaced_slots)

    return menus, spaced_menus, menu_names
