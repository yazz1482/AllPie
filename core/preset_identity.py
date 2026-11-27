"""Stable identity helpers shared by configuration and editor code."""

from __future__ import annotations

import hashlib
from typing import Iterable

# Blender EnumProperty item numbers are stored as signed C integers. Keep the
# persistent values positive and leave zero for the empty slot enum item.
MAX_ENUM_VALUE = 2_147_483_647


def unique_enum_value(preset_id: str, used_values: Iterable[int] = ()) -> int:
    """Derive a deterministic, positive Blender enum number for one preset.

    The value is persisted in the operator record. Hash collisions are
    resolved against the current configuration with linear probing; once
    stored, the assigned number is never recomputed when another preset is
    inserted or the visible list is reordered.
    """
    identity = str(preset_id or "").strip()
    if not identity:
        raise ValueError("A permanent preset ID is required to derive an enum value")

    used = {
        int(value)
        for value in used_values
        if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_ENUM_VALUE
    }
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    candidate = (int.from_bytes(digest[:8], "big") % MAX_ENUM_VALUE) + 1
    first_candidate = candidate
    while candidate in used:
        candidate = 1 if candidate >= MAX_ENUM_VALUE else candidate + 1
        if candidate == first_candidate:
            raise RuntimeError("All available Blender EnumProperty values have been exhausted")
    return candidate
