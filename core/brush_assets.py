"""Canonical helpers for Blender brush-asset operator presets.

This module has no Blender dependency. It keeps brush asset references
consistent across preset creation, configuration migration and validation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

BRUSH_ASSET_OPERATOR_ID = "brush.asset_activate"


def normalize_operator_properties(
    operator_id: str,
    properties: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a canonical copy of an operator's JSON properties.

    Blender's Asset Shelf API defines ``asset_library_identifier`` as relevant
    only for CUSTOM libraries. Omit it for Essentials, Online Essentials and
    Local assets even when a Blender version exposes a non-empty value. This
    keeps the same built-in asset from becoming multiple presets.

    Custom-library identifiers are always preserved because they distinguish
    otherwise-identical assets. All other properties are preserved exactly.
    """
    normalized = deepcopy(dict(properties or {}))
    if str(operator_id).strip() != BRUSH_ASSET_OPERATOR_ID:
        return normalized

    library_type = str(normalized.get("asset_library_type", "")).strip().upper()
    if "asset_library_type" in normalized and isinstance(normalized.get("asset_library_type"), str):
        normalized["asset_library_type"] = library_type

    if "asset_library_identifier" in normalized:
        identifier = normalized.get("asset_library_identifier")
        if library_type != "CUSTOM":
            # Blender's Asset Shelf API documents this identifier as relevant
            # only for CUSTOM libraries. Blender versions/builds may expose a
            # non-empty display identifier for Essentials/Local libraries, but
            # it is not part of the asset's identity and must not create a
            # second preset for the same built-in asset.
            normalized.pop("asset_library_identifier", None)
        elif isinstance(identifier, str):
            # Keep even an empty CUSTOM identifier: treating it as equivalent
            # to another library would be unsafe. The assignment UI rejects
            # empty CUSTOM identifiers before a preset can be created.
            normalized["asset_library_identifier"] = identifier.strip()

    if "relative_asset_identifier" in normalized:
        relative_identifier = normalized.get("relative_asset_identifier")
        if isinstance(relative_identifier, str):
            # Blender may return AssetWeakReference paths with native Windows
            # separators while AllPie's bundled presets use forward slashes.
            # The identifier is a Blender asset-relative path, not an OS path;
            # use one canonical separator so the same Essentials asset matches.
            normalized["relative_asset_identifier"] = relative_identifier.strip().replace("\\", "/")

    return normalized


def operator_properties_identity(
    operator_id: str,
    properties: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a comparison-only identity for an operator preset.

    Blender may expose built-in asset names with different capitalization
    depending on whether the reference came from a prebuilt AllPie preset or
    the active Asset Shelf. For non-CUSTOM brush libraries, the relative asset
    identifier is therefore compared case-insensitively. The returned mapping
    is only for equality/grouping; never pass it to Blender to activate an
    asset because it may contain a case-folded identifier.

    CUSTOM libraries remain case-sensitive so distinct user-library paths
    are not accidentally merged.
    """
    identity = normalize_operator_properties(operator_id, properties)
    if str(operator_id).strip() == BRUSH_ASSET_OPERATOR_ID:
        library_type = str(identity.get("asset_library_type", "")).strip().upper()
        relative_identifier = identity.get("relative_asset_identifier")
        if library_type in {"LOCAL", "ESSENTIALS", "ONLINE_ESSENTIALS"} and isinstance(relative_identifier, str):
            identity["relative_asset_identifier"] = relative_identifier.casefold()
    return identity


def operator_properties_match(
    operator_id: str,
    left: Mapping[str, Any] | None,
    right: Mapping[str, Any] | None,
) -> bool:
    """Compare operator properties using AllPie's semantic asset identity."""
    return operator_properties_identity(operator_id, left) == operator_properties_identity(operator_id, right)
