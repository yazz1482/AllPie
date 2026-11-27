"""Compile validated JSON into an efficient in-memory menu registry.

The radial menu's modal interaction should query this registry directly. No
JSON parsing, reference searching, or menu reconstruction is done at invoke
 time.
"""

from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

from .schema import CompiledConfig, CompiledMenu, OperatorPreset, SLOT_COUNT
from .validation import validate_config


class RegistryBuildError(ValueError):
    """Raised when a configuration cannot be compiled into a menu registry."""


def _make_action(identifier: str, raw: Mapping[str, Any], addon_id: Optional[str] = None) -> OperatorPreset:
    return OperatorPreset(
        identifier=str(raw.get("preset_id") or identifier),
        name=raw["name"],
        operator_id=raw["operator_id"],
        invoke=raw.get("invoke", False),
        properties=MappingProxyType(deepcopy(raw.get("properties", {}))),
        search_name=raw.get("search_name", raw["name"]),
        description=raw.get("description", ""),
        addon_id=addon_id,
    )


def _resolve_preset(
    reference: Optional[str],
    owner_addon: Optional[str],
    actions: Mapping[str, OperatorPreset],
) -> Optional[OperatorPreset]:
    if reference is None:
        return None
    # Validated menu slot references are always permanent preset IDs.
    return actions[reference]


def _compile_slots(
    slot_config: Mapping[str, Optional[str]],
    owner_addon: Optional[str],
    actions: Mapping[str, OperatorPreset],
) -> Tuple[Optional[OperatorPreset], ...]:
    """Compile sparse JSON slots ('1'–'8') to a fixed 8-item tuple."""
    result = [None] * SLOT_COUNT
    for slot_id, action_reference in slot_config.items():
        result[int(slot_id) - 1] = _resolve_preset(action_reference, owner_addon, actions)
    return tuple(result)


def build_registry(config: Mapping[str, Any]) -> CompiledConfig:
    """Validate and compile a JSON-style configuration.

    Action presets are created once. All menu slots that reference the same
    preset share the same OperatorPreset instance in the compiled cache.
    """
    report = validate_config(config)
    if not report.valid or report.config is None:
        details = "\n".join(str(issue) for issue in report.errors)
        raise RegistryBuildError(f"Cannot build AllPie registry:\n{details}")

    normalized = report.config
    actions: Dict[str, OperatorPreset] = {}

    for action_id, action_data in normalized["Operators"].items():
        preset_id = str(action_data["preset_id"])
        actions[preset_id] = _make_action(preset_id, action_data)

    for addon_id, addon_data in normalized["ThirdParty"].items():
        for action_id, action_data in addon_data["Operators"].items():
            preset_id = str(action_data["preset_id"])
            actions[preset_id] = _make_action(preset_id, action_data, addon_id)

    menus: Dict[str, CompiledMenu] = {}

    def add_menu(
        menu_id: str,
        menu_data: Mapping[str, Any],
        owner_addon: Optional[str] = None,
        owner_enabled: bool = True,
    ) -> None:
        spaced_data = menu_data.get("spaced_slots", {})
        # An enabled but currently empty Spaced Slots layout is still a real
        # destination: it must be available to the radial assignment workflow
        # and should render eight empty positions in normal radial use.
        has_spaced_slots = bool(menu_data.get("spaced_slots_enabled", False))
        spaced_slots = (
            _compile_slots(spaced_data, owner_addon, actions)
            if has_spaced_slots
            else None
        )
        runtime_id = f"{owner_addon}:{menu_id}" if owner_addon else menu_id
        menus[runtime_id] = CompiledMenu(
            identifier=runtime_id,
            name=menu_data["name"],
            key=menu_data["key"],
            keymodifiers=tuple(menu_data.get("keymodifiers", ())),
            keymap=menu_data["keymap"],
            enabled=bool(menu_data.get("enabled", True) and owner_enabled),
            slots=_compile_slots(menu_data.get("slots", {}), owner_addon, actions),
            slot_order=tuple(int(slot_id) - 1 for slot_id in menu_data.get("slots", {})),
            spaced_slots=spaced_slots,
            spaced_slot_order=(
                tuple(int(slot_id) - 1 for slot_id in spaced_data)
                if has_spaced_slots
                else None
            ),
            addon_id=owner_addon,
        )

    for menu_id, menu_data in normalized["Menus"].items():
        add_menu(menu_id, menu_data)

    for addon_id, addon_data in normalized["ThirdParty"].items():
        for menu_id, menu_data in addon_data["Menus"].items():
            add_menu(menu_id, menu_data, addon_id, addon_data.get("enabled", True))

    return CompiledConfig(
        schema_version=normalized["schema_version"],
        menus=MappingProxyType(menus),
        operators=MappingProxyType(actions),
        preferences=MappingProxyType(deepcopy(normalized["Preferences"])),
    )


class MenuRegistry:
    """Small swappable cache used by the radial-menu compatibility adapter."""

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self._compiled: Optional[CompiledConfig] = None
        self.generation = 0
        if config is not None:
            self.replace(config)

    @property
    def compiled(self) -> Optional[CompiledConfig]:
        return self._compiled

    @property
    def menus(self) -> Mapping[str, CompiledMenu]:
        return self._compiled.menus if self._compiled else MappingProxyType({})

    @property
    def operators(self) -> Mapping[str, OperatorPreset]:
        return self._compiled.operators if self._compiled else MappingProxyType({})

    @property
    def preferences(self) -> Mapping[str, Any]:
        return self._compiled.preferences if self._compiled else MappingProxyType({})

    def activate(self, compiled: CompiledConfig) -> CompiledConfig:
        """Publish an already-built cache after dependent views are ready."""
        self._compiled = compiled
        self.generation += 1
        return compiled

    def replace(self, config: Mapping[str, Any]) -> CompiledConfig:
        """Build fully off to the side, then atomically swap the active cache."""
        compiled = build_registry(config)
        return self.activate(compiled)

    def clear(self) -> None:
        """Release the active compiled configuration."""
        self._compiled = None
        self.generation += 1

    def get_menu(self, menu_id: str) -> Optional[CompiledMenu]:
        """O(1) lookup by stable menu ID."""
        return self.menus.get(menu_id)

    def get_slots(
        self,
        menu_id: str,
        *,
        spaced: bool = False,
    ) -> Optional[Tuple[Optional[OperatorPreset], ...]]:
        """Return a precompiled slot tuple; fall back to normal slots.

        The fallback matches the existing behavior when Space is held for a
        menu that has no spaced variant.
        """
        menu = self.get_menu(menu_id)
        if menu is None:
            return None
        if spaced and menu.spaced_slots is not None:
            return menu.spaced_slots
        return menu.slots
