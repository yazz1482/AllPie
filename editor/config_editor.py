"""Blender-native JSON import/export UI for AllPie configurations.

Imports are staged and previewed before they replace the active configuration.
All actual parsing, migration, validation, saving and cache compilation remain
in the config/runtime layers.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, Mapping

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..config.loader import load_config
from ..core import runtime as ConfigRuntime

CONFIG_EDITOR_API_VERSION = 3
_PENDING_IMPORTS: Dict[str, Any] = {}


def _default_config_directory() -> Path:
    configured = (
        ConfigRuntime.USER_CONFIG_PATH
        or ConfigRuntime.ACTIVE_CONFIG_PATH
        or ConfigRuntime.DEFAULT_CONFIG_PATH
    )
    return Path(configured).expanduser().parent


def _json_filepath(filename: str) -> str:
    return str(_default_config_directory() / filename)


def _configuration_counts(config: Mapping[str, Any]) -> Dict[str, int]:
    menus = config.get("Menus", {})
    operators = config.get("Operators", {})
    third_party = config.get("ThirdParty", {})

    menu_count = len(menus)
    operator_count = len(operators)
    third_party_menu_count = 0
    third_party_operator_count = 0
    normal_slots = 0
    spaced_slots = 0

    for menu in menus.values():
        normal_slots += sum(value is not None for value in menu.get("slots", {}).values())
        spaced_slots += sum(value is not None for value in menu.get("spaced_slots", {}).values())

    for addon in third_party.values():
        addon_menus = addon.get("Menus", {})
        addon_operators = addon.get("Operators", {})
        third_party_menu_count += len(addon_menus)
        third_party_operator_count += len(addon_operators)
        for menu in addon_menus.values():
            normal_slots += sum(value is not None for value in menu.get("slots", {}).values())
            spaced_slots += sum(value is not None for value in menu.get("spaced_slots", {}).values())

    return {
        "menus": menu_count + third_party_menu_count,
        "operators": operator_count + third_party_operator_count,
        "normal_slots": normal_slots,
        "spaced_slots": spaced_slots,
        "third_party": len(third_party),
    }


def _invalidate_editor_state(context: Any) -> None:
    """Refresh all transient editor views after a configuration replacement."""
    from .. import Preferences

    prefs = Preferences.get_preferences()
    if prefs is not None:
        prefs.config_dirty = False
        prefs.config_save_error = ""
        prefs.editor_dirty = False
        prefs.editor_active_menu_id = ""
        prefs.editor_menu_id = ""
        prefs.editor_config_generation = -1
        prefs.editor_config_signature = ""
        prefs.operator_search_catalog_generation = -1
        prefs.operator_search_last_added = ""
        try:
            prefs.keybinds.clear()
        except (AttributeError, TypeError):
            pass

    from .. import RadialMenu

    RadialMenu.rebuild_keymaps()

    area = getattr(context, "area", None)
    if area is not None:
        area.tag_redraw()


class ALLPIE_OT_export_configuration(Operator):
    """Save the current AllPie configuration as a portable JSON file."""

    bl_idname = "allpie.export_configuration"
    bl_label = "Export JSON"
    bl_description = "Export menus, actions, keybindings and preferences to a JSON file"
    bl_options = {"INTERNAL"}

    filepath: StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = _json_filepath("allpie_config_export.json")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if not self.filepath:
            self.report({"ERROR"}, "Choose a destination JSON file")
            return {"CANCELLED"}

        destination = Path(bpy.path.abspath(self.filepath)).expanduser()
        if destination.suffix.casefold() != ".json":
            destination = destination.with_suffix(".json")

        try:
            from .. import Preferences
            from . import menu_editor

            prefs = Preferences.get_preferences()
            pending_menu_draft = bool(prefs is not None and prefs.editor_dirty)
            config_snapshot = (
                menu_editor._build_menu_draft_config(prefs)
                if pending_menu_draft else None
            )
            saved = ConfigRuntime.export_configuration(
                destination,
                prefs,
                backup=True,
                config_snapshot=config_snapshot,
            )

            # If the user deliberately exported over the active config file,
            # the draft was committed there and the transient editor must be
            # refreshed. Normal exports leave the draft visible and unapplied.
            if (
                pending_menu_draft
                and ConfigRuntime.ACTIVE_CONFIG_PATH is not None
                and saved.resolve() == ConfigRuntime.ACTIVE_CONFIG_PATH.resolve()
            ):
                _invalidate_editor_state(context)
        except Exception as error:
            self.report({"ERROR"}, f"Could not export AllPie configuration: {error}")
            return {"CANCELLED"}

        detail = " (including the unapplied menu draft)" if pending_menu_draft else ""
        self.report({"INFO"}, f"Exported AllPie configuration{detail} to {saved.name}")
        return {"FINISHED"}


class ALLPIE_OT_import_configuration(Operator):
    """Validate and preview a JSON file before importing it into AllPie."""

    bl_idname = "allpie.import_configuration"
    bl_label = "Import JSON"
    bl_description = "Load and validate an AllPie JSON configuration before applying it"
    bl_options = {"INTERNAL"}

    filepath: StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    preview_token: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        self.preview_token = ""
        if not self.filepath:
            self.filepath = _json_filepath("allpie_config.json")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        # First execute: file selector returned a path. Load and validate it,
        # then show a confirmation dialog. Second execute: user confirmed.
        if not self.preview_token:
            if not self.filepath:
                self.report({"ERROR"}, "Choose a JSON configuration file")
                return {"CANCELLED"}

            source = Path(bpy.path.abspath(self.filepath)).expanduser()
            try:
                result = load_config(
                    source,
                    valid_event_types=ConfigRuntime.get_blender_event_identifiers(),
                )
            except Exception as error:
                self.report({"ERROR"}, f"Could not load AllPie configuration: {error}")
                return {"CANCELLED"}

            # Only one import confirmation can be active at once. Discard an
            # abandoned preview before staging the next selected file.
            _PENDING_IMPORTS.clear()
            token = uuid.uuid4().hex
            _PENDING_IMPORTS[token] = result
            self.preview_token = token
            return context.window_manager.invoke_props_dialog(self, width=560)

        result = _PENDING_IMPORTS.pop(self.preview_token, None)
        self.preview_token = ""
        if result is None:
            self.report({"ERROR"}, "The import preview expired. Please select the file again.")
            return {"CANCELLED"}

        try:
            ConfigRuntime.commit_imported_configuration(result, backup=True)
        except Exception as error:
            self.report({"ERROR"}, f"Import was not applied: {error}")
            return {"CANCELLED"}

        refresh_warning = ""
        try:
            from .. import Preferences

            prefs = Preferences.get_preferences()
            ConfigRuntime.apply_config_preferences(prefs)
            _invalidate_editor_state(context)
        except Exception as error:
            refresh_warning = str(error)

        counts = _configuration_counts(result.config)
        message = (
            f"Imported {counts['menus']} menus and {counts['operators']} actions"
        )
        if result.migrated:
            message += " (migrated to current schema)"
        if result.warnings:
            message += f" with {len(result.warnings)} warning(s)"
        if refresh_warning:
            self.report({"WARNING"}, f"Configuration imported, but UI refresh had an issue: {refresh_warning}")
        self.report({"INFO"}, message)
        return {"FINISHED"}

    def draw(self, context):
        result = _PENDING_IMPORTS.get(self.preview_token)
        if result is None:
            self.layout.label(text="Import preview is unavailable.", icon="ERROR")
            return

        counts = _configuration_counts(result.config)
        layout = self.layout
        layout.label(text=Path(self.filepath).name, icon="FILE")
        layout.label(text="This will replace your current AllPie configuration.", icon="INFO")
        try:
            from .. import Preferences
            prefs = Preferences.get_preferences()
            if prefs is not None and getattr(prefs, "editor_dirty", False):
                layout.label(
                    text="Unapplied menu edits will be discarded by this import.",
                    icon="ERROR",
                )
        except Exception:
            pass
        box = layout.box()
        box.label(text=f"Menus: {counts['menus']}")
        box.label(text=f"Operator presets: {counts['operators']}")
        box.label(text=f"Assigned slots: {counts['normal_slots']} normal, {counts['spaced_slots']} spaced")
        box.label(text=f"Third-party namespaces: {counts['third_party']}")

        if result.migrated:
            layout.label(text="This file will be migrated to the current schema before import.", icon="FILE_REFRESH")
        if result.warnings:
            warning_box = layout.box()
            warning_box.label(text=f"Validation warnings: {len(result.warnings)}", icon="ERROR")
            for issue in result.warnings[:5]:
                warning_box.label(text=str(issue)[:150])
            if len(result.warnings) > 5:
                warning_box.label(text=f"And {len(result.warnings) - 5} more warning(s)…")
        current_user_config = ConfigRuntime.USER_CONFIG_PATH
        if current_user_config is not None and Path(current_user_config).exists():
            layout.label(text="Your existing user configuration will be backed up before replacement.", icon="INFO")
        else:
            layout.label(text="No existing user file was found; this import will create one.", icon="INFO")

    def cancel(self, context):
        if self.preview_token:
            _PENDING_IMPORTS.pop(self.preview_token, None)
            self.preview_token = ""


class ALLPIE_OT_restore_bundled_defaults(Operator):
    """Replace the user configuration with the bundled AllPie defaults."""

    bl_idname = "allpie.restore_bundled_defaults"
    bl_label = "Restore Bundled Defaults"
    bl_description = "Replace your current configuration with the defaults shipped with AllPie"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Restore the bundled AllPie configuration?", icon="INFO")
        try:
            from .. import Preferences
            prefs = Preferences.get_preferences()
            if prefs is not None and getattr(prefs, "editor_dirty", False):
                layout.label(
                    text="Unapplied menu edits will be discarded.",
                    icon="ERROR",
                )
        except Exception:
            pass

    def execute(self, context):
        try:
            result = load_config(
                ConfigRuntime.DEFAULT_CONFIG_PATH,
                valid_event_types=ConfigRuntime.get_blender_event_identifiers(),
            )
            ConfigRuntime.commit_imported_configuration(result, backup=True)
            from .. import Preferences

            ConfigRuntime.apply_config_preferences(Preferences.get_preferences())
            _invalidate_editor_state(context)
        except Exception as error:
            self.report({"ERROR"}, f"Could not restore bundled defaults: {error}")
            return {"CANCELLED"}
        self.report({"INFO"}, "Restored bundled AllPie defaults")
        return {"FINISHED"}


CLASSES = (
    ALLPIE_OT_export_configuration,
    ALLPIE_OT_import_configuration,
    ALLPIE_OT_restore_bundled_defaults,
)


def clear_pending_imports() -> None:
    _PENDING_IMPORTS.clear()


def draw_configuration_editor(layout: Any, prefs: Any, context: Any) -> None:
    """Draw the JSON configuration status and import/export controls."""
    box = layout.box()
    box.label(text="Configuration File", icon="FILE")

    if ConfigRuntime.CONFIG_RECOVERY_REQUIRED:
        recovery = layout.box()
        recovery.alert = True
        recovery.label(text="User configuration could not be loaded", icon="ERROR")
        recovery.label(text="Bundled defaults are active in memory. Your original JSON file has not been changed.")
        recovery.label(text=str(ConfigRuntime.CONFIG_RECOVERY_ERROR)[:220])
        recovery.label(text="Import a valid JSON file or choose Restore Bundled Defaults to replace the damaged file.")

    user_path = ConfigRuntime.USER_CONFIG_PATH or ConfigRuntime.ACTIVE_CONFIG_PATH
    source_path = ConfigRuntime.CONFIG_SOURCE_PATH
    if user_path is not None:
        box.label(text=f"User configuration: {Path(user_path)}")
    else:
        box.label(text="User configuration path is not initialized", icon="ERROR")

    if ConfigRuntime.LOADED_USER_CONFIG:
        box.label(text="Startup source: User configuration", icon="CHECKMARK")
    else:
        box.label(text="Startup source: Bundled defaults", icon="INFO")
    if source_path is not None and source_path != user_path:
        box.label(text=f"Loaded from: {Path(source_path).name}")

    row = box.row(align=True)
    row.scale_y = 1.4
    row.operator("allpie.export_configuration", text="Export Config", icon="EXPORT")
    row.operator("allpie.import_configuration", text="Import Config", icon="IMPORT")
    if getattr(prefs, "editor_dirty", False):
        layout.label(
            text="Export Config includes the current unapplied menu draft. Import Config and Restore Defaults replace it.",
            icon="INFO",
        )
    else:
        layout.label(
            text="Full configuration files contain all menus, shortcuts, action presets and preferences.",
            icon="INFO",
        )

    active_warnings = getattr(ConfigRuntime, "ACTIVE_VALIDATION_WARNINGS", ())
    if active_warnings:
        diagnostics = layout.box()
        diagnostics.alert = True
        diagnostics.label(text=f"Configuration warnings: {len(active_warnings)}", icon="ERROR")
        for issue in active_warnings[:8]:
            diagnostics.label(text=str(issue)[:180], icon="INFO")
        if len(active_warnings) > 8:
            diagnostics.label(text=f"And {len(active_warnings) - 8} more warning(s)…")

    if ConfigRuntime.INITIALIZED and ConfigRuntime.ACTIVE_CONFIG is not None:
        counts = _configuration_counts(ConfigRuntime.ACTIVE_CONFIG)
        summary = layout.box()
        summary.label(text="Active Configuration", icon="CHECKMARK")
        grid = summary.grid_flow(columns=2, even_columns=True, even_rows=True, align=True)
        grid.label(text=f"Menus: {counts['menus']}")
        grid.label(text=f"Actions: {counts['operators']}")
        grid.label(text=f"Normal slots: {counts['normal_slots']}")
        grid.label(text=f"Spaced slots: {counts['spaced_slots']}")
        summary.label(text=f"Third-party namespaces: {counts['third_party']}")

    # Operator RNA validation remains available without retaining a separate
    # Operators preferences page. The unified search owns preset editing and
    # deletion; Configuration is the appropriate home for diagnostics.
    from . import operator_editor
    operator_editor.draw_operator_validation(layout, prefs)

    layout.separator()
    layout.operator("allpie.restore_bundled_defaults", text="Restore Bundled Defaults", icon="LOOP_BACK")
    layout.label(text="Import replaces the active configuration and saves it to your user config folder.", icon="INFO")
