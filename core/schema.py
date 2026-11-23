"""AllPie configuration schema and runtime data structures.

This module deliberately has no Blender dependency. JSON is the persistent
representation; the dataclasses below are the compiled, in-memory form used
by the runtime menu system.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

SCHEMA_VERSION = 9
SLOT_COUNT = 8
SLOT_IDS = tuple(str(index) for index in range(1, SLOT_COUNT + 1))

# These are the contexts currently used by AllPie's existing keymaps. Custom
# Blender keymap names remain permitted by validation.
BUILTIN_KEYMAPS = (
    "Object Mode",
    "Mesh",
    "Sculpt",
    "Image Paint",
    "Vertex Paint",
    "Weight Paint",
)

# Reserved menu keymap value. A menu assigned to this scope is registered in
# every built-in AllPie context above, while remaining one JSON menu record.
COMMON_KEYMAP = "Common"

# Contexts that support Brush Menus with brush assets and Asset Shelf actions.
BRUSH_MENU_KEYMAPS = ("Sculpt", "Image Paint", "Vertex Paint", "Weight Paint")


def keymap_contexts(keymap: str) -> Tuple[str, ...]:
    """Expand a menu scope into the actual Blender keymap contexts it targets.

    Ordinary and custom keymap names remain single-context assignments. The
    reserved Common scope maps only to AllPie's six supported built-in modes.
    """
    value = str(keymap or "").strip()
    if value.casefold() == COMMON_KEYMAP.casefold():
        return BUILTIN_KEYMAPS
    return (value,) if value else ()

SUPPORTED_MODIFIERS = frozenset({"SHIFT", "CTRL", "ALT", "OSKEY", "HYPER"})

# Defaults are based on the actual AllPiePreferences definitions in the
# current addon, rather than the fallback constants in RadialMenu.py.
DEFAULT_PREFERENCES: Dict[str, Any] = {
    "radial": {
        "hold_time": 0.125,
        "deadzone": 25,
    },
    "colors": {
        "slot_color": [0.02, 0.02, 0.02, 1.0],
        "active_slot_color": [0.14, 0.14, 0.14, 1.0],
        "spaced_slot_color": [0.02, 0.02, 0.02, 1.0],
        "spaced_active_slot_color": [0.14, 0.14, 0.14, 1.0],
        "font_color": [1.0, 1.0, 1.0, 1.0],
        "active_font_color": [0.45, 0.75, 0.97, 1.0],
        "spaced_font_color": [1.0, 1.0, 1.0, 1.0],
        "spaced_active_font_color": [0.82, 0.55, 0.33, 1.0],
        "outline_color": [0.18, 0.42, 0.70, 1.0],
        "spaced_outline_color": [0.82, 0.55, 0.33, 1.0],
        "mark_color": [1.0, 1.0, 1.0, 1.0],
    },
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "Menus": {},
    "Operators": {},
    "ThirdParty": {},
    "Preferences": DEFAULT_PREFERENCES,
}


def make_default_config() -> Dict[str, Any]:
    """Return a fresh, independently mutable configuration using the current schema."""
    return deepcopy(DEFAULT_CONFIG)


@dataclass(frozen=True)
class OperatorPreset:
    """A reusable, fully specified action preset."""

    identifier: str
    name: str
    operator_id: str
    invoke: bool
    properties: Mapping[str, Any]
    search_name: str = ""
    description: str = ""
    addon_id: Optional[str] = None

    @property
    def execution_context(self) -> str:
        """Match the existing RadialMenu.execute_slot behavior."""
        return "INVOKE_DEFAULT" if self.invoke else "EXEC_DEFAULT"


@dataclass(frozen=True)
class CompiledMenu:
    """A menu with its eight slots resolved to reusable action objects."""

    identifier: str
    name: str
    key: str
    keymodifiers: Tuple[str, ...]
    keymap: str
    enabled: bool
    slots: Tuple[Optional[OperatorPreset], ...]
    slot_order: Tuple[int, ...]
    spaced_slots: Optional[Tuple[Optional[OperatorPreset], ...]]
    spaced_slot_order: Optional[Tuple[int, ...]]
    addon_id: Optional[str] = None


@dataclass(frozen=True)
class CompiledConfig:
    """Immutable top-level view of a compiled configuration."""

    schema_version: int
    menus: Mapping[str, CompiledMenu]
    operators: Mapping[str, OperatorPreset]
    preferences: Mapping[str, Any]
