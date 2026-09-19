import bpy

from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import ( FloatProperty, FloatVectorProperty, StringProperty, IntProperty, BoolProperty, CollectionProperty,)

from . import EditModePies
from . import SculptModePies
from . import ObjectModePies


# KEYBIND DATA
class AllPieKeybind(PropertyGroup):

    pref_id: StringProperty()
    menu_id: StringProperty()

    key: StringProperty()
    value: StringProperty()

    enabled: BoolProperty( default=True, update=lambda self, context: update_enabled(self, context),)

    shift: BoolProperty(default=False)
    ctrl: BoolProperty(default=False)
    alt: BoolProperty(default=False)


# KEYBIND DEFINITIONS
def get_keybind_definitions():

    definitions = []

    for index, (key, menu_id, modifiers) in enumerate(
        EditModePies.MESH_HOTKEYS
    ):
        definitions.append((
            f"MESH_{index}",
            "Mesh",
            key,
            "PRESS",
            menu_id,
            modifiers,
        ))

    for index, (key, menu_id, modifiers) in enumerate(
        SculptModePies.SCULPT_HOTKEYS
    ):
        definitions.append((
            f"SCULPT_{index}",
            "Sculpt",
            key,
            "PRESS",
            menu_id,
            modifiers,
        ))
    for index, (key, menu_id, modifiers) in enumerate(
        ObjectModePies.OBJECT_HOTKEYS
    ):
        definitions.append((
            f"OBJECT_{index}",
            "Object Mode",
            key,
            "PRESS",
            menu_id,
            modifiers,
        ))

    return definitions


# GET PREFERENCES
def get_preferences():

    addon = bpy.context.preferences.addons.get(__package__)

    if addon is None:
        return None

    return addon.preferences


# FIND STORED KEYBIND
def get_keybind_store(prefs, pref_id):

    for keybind in prefs.keybinds:

        if keybind.pref_id == pref_id:
            return keybind

    return None


# INITIALIZE KEYBINDS
def initialize_keybinds(prefs):

    for (
        pref_id,
        keymap_name,
        default_key,
        default_value,
        menu_id,
        modifiers,
    ) in get_keybind_definitions():

        keybind = get_keybind_store(
            prefs,
            pref_id
        )

        if keybind is None:

            keybind = prefs.keybinds.add()

            keybind.pref_id = pref_id
            keybind.menu_id = menu_id

            keybind.key = default_key
            keybind.value = default_value

            keybind.shift = modifiers.get("shift", False)
            keybind.ctrl = modifiers.get("ctrl", False)
            keybind.alt = modifiers.get("alt", False)

        else:

            keybind.menu_id = menu_id
            keybind.value = "PRESS"


# FIND LIVE KEYMAP ITEM
def find_addon_kmi(kc, pref_id):

    for km in kc.keymaps:

        for kmi in km.keymap_items:

            if kmi.idname != "view3d.modal_radial_menu":
                continue

            if getattr(kmi.properties, "pref_id", None) == pref_id:
                return km, kmi

    return None, None


# SYNC LIVE KEYMAP TO PREFERENCES
def sync_kmi_to_preferences(prefs, kmi, pref_id):

    keybind = get_keybind_store( prefs, pref_id)

    if keybind is None:
        return

    keybind.key = kmi.type
    keybind.value = "PRESS"

    keybind.shift = kmi.shift
    keybind.ctrl = kmi.ctrl
    keybind.alt = kmi.alt
    kmi.value = "PRESS"

    # kmi.properties.hotkey = kmi.type


# SYNC ALL LIVE KEYMAPS
def sync_all_keymaps_to_preferences():

    kc = bpy.context.window_manager.keyconfigs.addon

    if kc is None:
        return

    prefs = get_preferences()

    if prefs is None:
        return

    initialize_keybinds(prefs)

    for (
        pref_id,
        keymap_name,
        default_key,
        default_value,
        menu_id,
        modifiers,
    ) in get_keybind_definitions():

        km, kmi = find_addon_kmi(
            kc,
            pref_id
        )

        if kmi is not None:

            sync_kmi_to_preferences( prefs, kmi, pref_id)


# UPDATE ENABLE STATE
def update_enabled(self, context):

    if context is None:
        return

    prefs = get_preferences()

    if prefs is None:
        return

    kc = context.window_manager.keyconfigs.addon

    if kc is None:
        return

    # Save any key edits made through Blender's native key widget
    # before changing the enabled state.
    sync_all_keymaps_to_preferences()

    # sync_all_keymaps_to_preferences() does not touch enabled,
    # so the new checkbox state remains intact.

    from . import RadialMenu

    RadialMenu.update_keymap( self.pref_id)


# MENU LABEL
def get_menu_label(menu_id):

    if "." in menu_id:
        name = menu_id.split(".", 1)[1]
    else:
        name = menu_id

    name = name.replace("_", " ")

    return name.title()


# DRAW KEYBIND
def draw_keybind(
    layout,
    kc,
    prefs,
    pref_id,
    keymap_name,
    menu_id,
):

    keybind = get_keybind_store(
        prefs,
        pref_id
    )

    if keybind is None:
        return

    km, kmi = find_addon_kmi(
        kc,
        pref_id
    )

    row = layout.row(align=True)
    row.separator(factor=4)
    row.prop( keybind, "enabled", text="")
    row.label( text=get_menu_label(menu_id))

    if kmi is None:

        row.label( text=keybind.key)

        return

    # Keep persistent settings synchronized with Blender's
    # native key event widget.
    sync_kmi_to_preferences( prefs, kmi, pref_id)

    row.prop( kmi, "type", text="", event=True)
    row.prop( kmi, "ctrl_ui", text="Ctrl", toggle=True)
    row.prop( kmi, "shift_ui", text="Shift", toggle=True)
    row.prop( kmi, "alt_ui", text="Alt", toggle=True)


# ADDON PREFERENCES
class AllPiePreferences(AddonPreferences):

    bl_idname = __package__

    keybinds: CollectionProperty( type=AllPieKeybind)

    hold_time: FloatProperty(default=0.125, min = 0.010,max=0.500, step=1)
    deadzone: IntProperty(default=25, min= 15,max=50, step=1)

    slot_color: FloatVectorProperty( name="Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.02, 0.02, 0.02, 0.8), min=0.0, max=1.0,)
    active_slot_color: FloatVectorProperty( name="Active Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.25, 0.25, 0.25, 0.90), min=0.0, max=1.0,)
    #Spaced Slot Color
    spaced_slot_color: FloatVectorProperty( name="Spaced Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.02, 0.02, 0.02, 0.8), min=0.0, max=1.0,)
    spaced_active_slot_color: FloatVectorProperty( name="Spaced Active Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.25, 0.25, 0.25, 0.90), min=0.0, max=1.0,)

    font_color: FloatVectorProperty( name="Font Color", subtype="COLOR_GAMMA", size=4, default=(0.90, 0.90, 0.90, 1.0), min=0.0, max=1.0,)
    active_font_color: FloatVectorProperty( name="Active Font Color", subtype="COLOR_GAMMA", size=4, default=(0.40, 1.00, 0.66, 1.0), min=0.0, max=1.0,)
    #Spaced Font Color
    spaced_font_color: FloatVectorProperty( name="Spaced Font Color", subtype="COLOR_GAMMA", size=4, default=(0.90, 0.90, 0.90, 1.0), min=0.0, max=1.0,)
    spaced_active_font_color: FloatVectorProperty( name="Spaced Active Font Color", subtype="COLOR_GAMMA", size=4, default=(0.64, 0.52, 1.00, 1.0), min=0.0, max=1.0,)

    outline_color: FloatVectorProperty( name="Outline Color", subtype="COLOR_GAMMA", size=4, default=(0.18, 1.00, 0.51, 0.50), min=0.0, max=1.0,)
    spaced_outline_color: FloatVectorProperty( name="Spaced Outline Color", subtype="COLOR_GAMMA", size=4, default=(0.45, 0.35, 0.75, 0.50), min=0.0, max=1.0,)
    
    mark_color: FloatVectorProperty( name="Mark Color", subtype="COLOR_GAMMA", size=4, default=(0.18, 1.00, 0.52, 1.0), min=0.0, max=1.0,)

    def draw(self, context):

        kc = context.window_manager.keyconfigs.addon

        initialize_keybinds(self)

        # Save any changes made through Blender's key widget.
        if kc is not None:
            sync_all_keymaps_to_preferences()

        layout = self.layout
        header, body = layout.panel( "AllPie_Radial_Menu_Settings", default_closed=False,)
        header.label( text="Radial Menu Settings")

        if body:
            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Key Hold Time")
            row.prop(self, "hold_time", text="")
            row = layout.row(align=True)

            row.separator(factor=4)
            row.label(text="Pie Menu Deadzone")
            row.prop(self, "deadzone", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Mark Color")
            row.prop(self, "mark_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Slot Color")
            row.prop(self, "slot_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Active Slot Color")
            row.prop(self, "active_slot_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Font Color")
            row.prop(self, "font_color", text="")
            
            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Active Font Color")
            row.prop(self, "active_font_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Outline Color")
            row.prop(self, "outline_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Spaced Slot Color")
            row.prop(self, "spaced_slot_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Spaced Active Slot Color")
            row.prop(self, "spaced_active_slot_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Spaced Font Color")
            row.prop(self, "spaced_font_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Spaced Active Font Color")
            row.prop(self, "spaced_active_font_color", text="")

            row = layout.row(align=True)
            row.separator(factor=4)
            row.label(text="Spaced Outline Color")
            row.prop(self, "spaced_outline_color", text="")


        # EDIT MODE
        header, body = layout.panel( "AllPie_Edit_Mode", default_closed=False,)
        header.label( text="Edit Mode")

        if body:

            for (
                pref_id,
                keymap_name,
                default_key,
                default_value,
                menu_id,
                modifiers,
            ) in get_keybind_definitions():

                if keymap_name != "Mesh":
                    continue

                draw_keybind(
                    body,
                    kc,
                    self,
                    pref_id,
                    keymap_name,
                    menu_id,
                )

        # SCULPT MODE
        header, body = layout.panel( "AllPie_Sculpt_Mode", default_closed=False,)
        header.label( text="Sculpt Mode")

        if body:

            for (
                pref_id,
                keymap_name,
                default_key,
                default_value,
                menu_id,
                modifiers,
            ) in get_keybind_definitions():

                if keymap_name != "Sculpt":
                    continue

                draw_keybind(
                    body,
                    kc,
                    self,
                    pref_id,
                    keymap_name,
                    menu_id,
                )
        # OBJECT MODE
        header, body = layout.panel( "AllPie_Objectt_Mode", default_closed=False,)
        header.label( text="Object Mode")

        if body:

            for (
                pref_id,
                keymap_name,
                default_key,
                default_value,
                menu_id,
                modifiers,
            ) in get_keybind_definitions():

                if keymap_name != "Object Mode":
                    continue

                draw_keybind(
                    body,
                    kc,
                    self,
                    pref_id,
                    keymap_name,
                    menu_id,
                )


classes = (
    AllPieKeybind,
    AllPiePreferences,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    prefs = get_preferences()

    if prefs is not None:
        initialize_keybinds(prefs)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
