import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import (
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
    IntProperty,
    BoolProperty,
    CollectionProperty,
    EnumProperty,
)

from .core import runtime as ConfigRuntime
from .core.schema import DEFAULT_PREFERENCES
from .editor import menu_data, menu_editor, operator_editor, operator_setup, config_editor

_PREFERENCE_SAVE_INTERVAL = 0.65

# Immutable UI definition: General Preferences only draws existing RNA values.
# Keep file I/O, JSON validation, cache rebuilds and keymap work out of draw().
_GENERAL_SETTING_ROWS = (
    ("Key Hold Time", "hold_time"),
    ("Pie Menu Deadzone", "deadzone"),
    ("Mark Color", "mark_color"),
    ("Slot Color", "slot_color"),
    ("Active Slot Color", "active_slot_color"),
    ("Font Color", "font_color"),
    ("Active Font Color", "active_font_color"),
    ("Outline Color", "outline_color"),
    ("Spaced Slot Color", "spaced_slot_color"),
    ("Spaced Active Slot Color", "spaced_active_slot_color"),
    ("Spaced Font Color", "spaced_font_color"),
    ("Spaced Active Font Color", "spaced_active_font_color"),
    ("Spaced Outline Color", "spaced_outline_color"),
)


def _flush_config_save():
    """Debounced timer: serialize the current RNA values to user JSON."""
    prefs = get_preferences()
    if prefs is None or not ConfigRuntime.INITIALIZED:
        return None
    if getattr(prefs, "config_loading", False):
        return _PREFERENCE_SAVE_INTERVAL
    try:
        ConfigRuntime.sync_preferences_to_config(prefs, persist=True)
        prefs.config_dirty = False
        prefs.config_save_error = ""
    except Exception as error:
        prefs.config_dirty = True
        prefs.config_save_error = str(error)
        print(f"[AllPie] Could not persist preferences: {error}")
    return None


def schedule_config_save(self, context):
    """Debounce preference persistence while colors/sliders are being dragged."""
    if getattr(self, "config_loading", False):
        return
    try:
        self.config_dirty = True
        if bpy.app.timers.is_registered(_flush_config_save):
            bpy.app.timers.unregister(_flush_config_save)
        bpy.app.timers.register(
            _flush_config_save,
            first_interval=_PREFERENCE_SAVE_INTERVAL,
        )
    except (AttributeError, RuntimeError, ValueError) as error:
        # During shutdown or registration reload the timer API may not be
        # available. Keep the state dirty so the UI can report it.
        try:
            self.config_save_error = str(error)
        except Exception:
            pass


# Legacy keybind records are retained only so the first user-config creation
# can migrate shortcuts saved by pre-JSON AllPie versions. Runtime keymaps no
# longer read this collection; the JSON Menus section is now authoritative.
class AllPieKeybind(PropertyGroup):
    pref_id: StringProperty()
    menu_id: StringProperty()
    key: StringProperty()
    value: StringProperty()
    enabled: BoolProperty(default=True)
    shift: BoolProperty(default=False)
    ctrl: BoolProperty(default=False)
    alt: BoolProperty(default=False)


def get_keybind_definitions():
    return ConfigRuntime.get_keybind_definitions()


def get_preferences():
    addon = bpy.context.preferences.addons.get(__package__)
    if addon is None:
        return None
    return addon.preferences


# ADDON PREFERENCES
class AllPiePreferences(AddonPreferences):

    bl_idname = __package__

    # Deprecated Blender-stored keybind collection. Read once for migration only.
    keybinds: CollectionProperty(type=AllPieKeybind)

    # Configuration editor state (transient UI state; the JSON runtime remains
    # the source of truth for menus and action presets).
    editor_page: EnumProperty(
        name="Preferences Page",
        items=(
            ("GENERAL", "General", "Radial menu timing and appearance"),
            ("MENUS", "Menus", "Browse and edit AllPie radial menus"),
            # Retained as a hidden compatibility value for older saved
            # AddonPreferences. The Operators page is now integrated into the
            # Menus picker and preset controls, so this item is not drawn.
            ("OPERATORS", "Operators (retired)", "Legacy page; operator management is integrated into Menus"),
            ("CONFIGURATION", "Configuration", "Import, export and restore AllPie JSON configurations"),
        ),
        default="GENERAL",
    )
    # Menu browser state. These two properties are consumed by menu_editor.py;
    # keeping them on AddonPreferences avoids runtime AttributeError during draw.
    editor_category: EnumProperty(
        name="Category",
        description="Filter radial menus by their Blender keymap context",
        items=menu_data.MENU_CATEGORY_ITEMS,
        default="ALL",
        update=menu_editor.on_category_changed,
    )
    editor_menus: CollectionProperty(type=menu_editor.AllPieMenuListItem)
    active_menu_index: IntProperty(
        name="Active Menu Index",
        default=0,
        options={"HIDDEN"},
        update=menu_editor.on_active_menu_changed,
    )
    editor_slots: CollectionProperty(type=menu_editor.AllPieMenuSlotItem)
    editor_spaced_slots: CollectionProperty(type=menu_editor.AllPieMenuSlotItem)
    operator_search_context_filters: EnumProperty(
        name="Context Filters",
        description="Optional filters inside the slot operator search. Multiple selected contexts are combined with OR.",
        items=operator_editor.SEARCH_CONTEXT_FILTER_ITEMS,
        options={"ENUM_FLAG", "SKIP_SAVE"},
        default=set(),
    )
    operator_search_last_added: StringProperty(default="", options={"HIDDEN"})
    operator_search_items: CollectionProperty(type=operator_editor.AllPieOperatorSearchItem, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_query: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE", "TEXTEDIT_UPDATE"}, update=operator_editor.update_operator_search_query)
    operator_search_active_index: IntProperty(default=0, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_catalog_generation: IntProperty(default=-1, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_config_generation: IntProperty(default=-1, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_config_fingerprint: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    operator_search_catalog_loading: BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_catalog_error: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    operator_search_target_menu_id: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    operator_search_target_slot: IntProperty(default=1, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_target_spaced: BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})
    operator_search_context_name: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    operator_validation_items: CollectionProperty(type=operator_editor.AllPieOperatorValidationItem, options={"HIDDEN", "SKIP_SAVE"})
    operator_validation_summary: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    operator_validation_generation: IntProperty(default=-1, options={"HIDDEN", "SKIP_SAVE"})
    editor_config_generation: IntProperty(default=-1, options={"HIDDEN"})
    editor_config_signature: StringProperty(options={"HIDDEN"})
    editor_active_menu_id: StringProperty(options={"HIDDEN"})
    # Full detached configuration snapshot for one unapplied menu edit session.
    # SKIP_SAVE keeps unfinished drafts out of Blender's persistent preferences.
    editor_draft_config_json: StringProperty(
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    editor_dirty: BoolProperty(default=False, options={"HIDDEN"})
    editor_menu_id: StringProperty(options={"HIDDEN"})
    editor_menu_name: StringProperty(name="Menu Name", default="", update=menu_editor.mark_editor_dirty)
    editor_menu_key: StringProperty(name="Key", default="A", update=menu_editor.mark_editor_dirty)
    editor_menu_mode: EnumProperty(
        name="Context",
        description="Blender mode or editor context in which this radial menu is available",
        items=menu_editor.menu_data.KEYMAP_ENUM_ITEMS,
        default="OBJECT_MODE",
        update=menu_editor.mark_editor_dirty,
    )
    editor_menu_enabled: BoolProperty(name="Enabled", default=True, update=menu_editor.mark_editor_dirty)
    editor_menu_shift: BoolProperty(name="Shift", default=False, update=menu_editor.mark_editor_dirty)
    editor_menu_ctrl: BoolProperty(name="Ctrl", default=False, update=menu_editor.mark_editor_dirty)
    editor_menu_alt: BoolProperty(name="Alt", default=False, update=menu_editor.mark_editor_dirty)
    editor_menu_oskey: BoolProperty(name="OSKey", default=False, update=menu_editor.mark_editor_dirty)
    editor_menu_hyper: BoolProperty(name="Hyper", default=False, update=menu_editor.mark_editor_dirty)
    editor_spaced_enabled: BoolProperty(name="Enable Spaced Slots", default=False, update=menu_editor.mark_editor_dirty)
    editor_loading: BoolProperty(default=False, options={"HIDDEN"})
    editor_custom_keymap: StringProperty(name="Custom Keymap", default="", update=menu_editor.mark_editor_dirty)
    config_loading: BoolProperty(default=False, options={"HIDDEN"})
    config_dirty: BoolProperty(default=False, options={"HIDDEN"})
    config_save_error: StringProperty(default="", options={"HIDDEN"})

    hold_time: FloatProperty(default=DEFAULT_PREFERENCES["radial"]["hold_time"], min=0.010, max=0.500, step=1, update=schedule_config_save)
    deadzone: IntProperty(default=DEFAULT_PREFERENCES["radial"]["deadzone"], min=15, max=50, step=1, update=schedule_config_save)

    slot_color: FloatVectorProperty( name="Slot Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["slot_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    active_slot_color: FloatVectorProperty( name="Active Slot Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["active_slot_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    #Spaced Slot Color
    spaced_slot_color: FloatVectorProperty( name="Spaced Slot Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["spaced_slot_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    spaced_active_slot_color: FloatVectorProperty( name="Spaced Active Slot Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["spaced_active_slot_color"]), min=0.0, max=1.0, update=schedule_config_save,)

    font_color: FloatVectorProperty( name="Font Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["font_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    active_font_color: FloatVectorProperty( name="Active Font Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["active_font_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    #Spaced Font Color
    spaced_font_color: FloatVectorProperty( name="Spaced Font Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["spaced_font_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    spaced_active_font_color: FloatVectorProperty( name="Spaced Active Font Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["spaced_active_font_color"]), min=0.0, max=1.0, update=schedule_config_save,)

    outline_color: FloatVectorProperty( name="Outline Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["outline_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    spaced_outline_color: FloatVectorProperty( name="Spaced Outline Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["spaced_outline_color"]), min=0.0, max=1.0, update=schedule_config_save,)
    
    mark_color: FloatVectorProperty( name="Mark Color", subtype="COLOR_GAMMA", size=4, default=tuple(DEFAULT_PREFERENCES["colors"]["mark_color"]), min=0.0, max=1.0, update=schedule_config_save,)

    # Deprecated hidden properties retained only to migrate custom brush slots
    # from pre-JSON AllPie preferences on the first creation of user config.
    # They are intentionally not drawn or synchronized after migration.
    EssentialBrush_Slot1: StringProperty(default="DRAW", options={"HIDDEN"})
    EssentialBrush_Slot2: StringProperty(default="DRAW SHARP", options={"HIDDEN"})
    EssentialBrush_Slot3: StringProperty(default="CLAY STRIPS", options={"HIDDEN"})
    EssentialBrush_Slot4: StringProperty(default="MASK", options={"HIDDEN"})
    EssentialBrush_Slot5: StringProperty(default="SCRAPE/FILL", options={"HIDDEN"})
    EssentialBrush_Slot6: StringProperty(default="INFLATE/DEFLATE", options={"HIDDEN"})
    EssentialBrush_Slot7: StringProperty(default="GRAB", options={"HIDDEN"})
    EssentialBrush_Slot8: StringProperty(default="PINCH/MAGNIFY", options={"HIDDEN"})

    EssentialSpaceBrush_Slot1: StringProperty(default="CREASE SHARP", options={"HIDDEN"})
    EssentialSpaceBrush_Slot2: StringProperty(default="CLAY", options={"HIDDEN"})
    EssentialSpaceBrush_Slot3: StringProperty(default="FACE SET PAINT", options={"HIDDEN"})
    EssentialSpaceBrush_Slot4: StringProperty(default="TRIM", options={"HIDDEN"})
    EssentialSpaceBrush_Slot5: StringProperty(default="ERASE MULTIRES DISPLACEMENT", options={"HIDDEN"})
    EssentialSpaceBrush_Slot6: StringProperty(default="SNAKE HOOK", options={"HIDDEN"})
    EssentialSpaceBrush_Slot7: StringProperty(default="RELAX SLIDE", options={"HIDDEN"})

    def draw(self, context):
        layout = self.layout

        # Redirect preferences saved on the retired Operators page to Menus.
        # Keep the enum identifier registered above for backwards compatibility,
        # but never expose it in the visible navigation.
        if self.editor_page == "OPERATORS":
            self.editor_page = "MENUS"

        navigation = layout.row(align=True)
        navigation.prop_enum(self, "editor_page", "GENERAL", text="General")
        navigation.prop_enum(self, "editor_page", "MENUS", text="Menus")
        navigation.prop_enum(self, "editor_page", "CONFIGURATION", text="Configuration")
        if ConfigRuntime.CONFIG_RECOVERY_REQUIRED:
            recovery_box = layout.box()
            recovery_box.alert = True
            recovery_box.label(text="AllPie loaded bundled defaults because your user configuration is invalid.", icon="ERROR")
            recovery_box.label(text="Your original JSON file is preserved. Open Configuration to import a valid file or restore bundled defaults.")
            recovery_box.label(text=str(ConfigRuntime.CONFIG_RECOVERY_ERROR)[:180])
        if self.config_save_error:
            error_box = layout.box()
            error_box.alert = True
            error_box.label(text=f"Configuration save failed: {self.config_save_error}", icon="ERROR")
        elif self.config_dirty:
            layout.label(text="Saving AllPie configuration…", icon="TIME")

        if self.editor_page == "MENUS":
            menu_editor.draw_menu_editor(layout, self, context)
            return
        if self.editor_page == "CONFIGURATION":
            config_editor.draw_configuration_editor(layout, self, context)
            return

        self.draw_general(context)

    def draw_general(self, context):
        """Draw only the lightweight General RNA controls.

        This method intentionally performs no configuration copies, JSON
        serialization, operator scans, keymap synchronization or cache work.
        Blender's normal property widgets own the update callbacks.
        """
        layout = self.layout
        header, body = layout.panel(
            "AllPie_Radial_Menu_Settings",
            default_closed=False,
        )
        header.label(text="Radial Menu Settings")
        if body is None:
            return

        for label, property_name in _GENERAL_SETTING_ROWS:
            row = body.row(align=True)
            row.separator(factor=2)
            row.prop(self, property_name, text=label)



classes = (
    AllPieKeybind,
    *menu_editor.CLASSES,
    *operator_editor.CLASSES,
    *config_editor.CLASSES,
    AllPiePreferences,
)


def _unregister_legacy_brush_menu_operator():
    """Remove the retired active-brush assignment operator from old sessions."""
    legacy_class = getattr(bpy.types, "ALLPIE_OT_menu_assign_active_brush", None)
    if legacy_class is not None and legacy_class not in classes:
        try:
            bpy.utils.unregister_class(legacy_class)
        except (RuntimeError, ValueError, TypeError):
            pass


def register():
    _unregister_legacy_brush_menu_operator()
    for cls in classes:
        bpy.utils.register_class(cls)

    operator_editor.register_button_context_menu()

    prefs = get_preferences()
    if prefs is None:
        # The bundled defaults still become persistent even when Blender does
        # not expose the AddonPreferences instance during this registration.
        if ConfigRuntime.ACTIVE_CONFIG_PATH is not None:
            ConfigRuntime.replace_and_save_configuration(ConfigRuntime.get_config_copy())
        return

    prefs.editor_dirty = False
    prefs.editor_draft_config_json = ""
    prefs.editor_config_generation = -1
    prefs.editor_config_signature = ""
    # The unified operator result rows gained in-place Edit/Delete controls.
    # Rebuild any result collection left in Blender's saved preferences so
    # every row receives the new can_edit/can_delete metadata.
    prefs.operator_search_config_fingerprint = ""
    prefs.operator_search_config_generation = -1
    prefs.operator_search_catalog_generation = -1
    if prefs.editor_page == "OPERATORS":
        prefs.editor_page = "MENUS"

    # On first user-config creation, preserve settings stored by older builds
    # (including the old keybind CollectionProperty). Once JSON exists, it is
    # the only persistent configuration source and is pushed into RNA instead.
    if ConfigRuntime.CONFIG_RECOVERY_REQUIRED:
        # Do not migrate old RNA values into the in-memory defaults: doing so
        # would attempt to persist over the damaged user file during startup.
        ConfigRuntime.apply_config_preferences(prefs)
    elif not ConfigRuntime.LOADED_USER_CONFIG:
        ConfigRuntime.migrate_legacy_preferences(prefs)
        ConfigRuntime.apply_config_preferences(prefs)
    else:
        try:
            prefs.keybinds.clear()
        except (AttributeError, TypeError):
            pass
        ConfigRuntime.apply_config_preferences(prefs)
    prefs.config_dirty = False
    prefs.config_save_error = ""


def unregister():
    operator_editor.cancel_operator_catalog_scan()
    operator_editor.unregister_button_context_menu()
    menu_editor.clear_shortcut_capture_items()
    config_editor.clear_pending_imports()
    try:
        timer_pending = bpy.app.timers.is_registered(_flush_config_save)
        if timer_pending:
            bpy.app.timers.unregister(_flush_config_save)
        prefs = get_preferences()
        if prefs is not None and getattr(prefs, "config_dirty", False):
            _flush_config_save()
    except (AttributeError, RuntimeError, ValueError) as error:
        print(f"[AllPie] Could not flush pending preferences during unregister: {error}")

    try:
        operator_setup.unregister_dynamic_property_groups()
    except Exception as error:
        print(f"[AllPie] Could not clean dynamic operator property groups: {error}")

    _unregister_legacy_brush_menu_operator()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
