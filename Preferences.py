import bpy

from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import ( StringProperty, BoolProperty, CollectionProperty,)

from . import EditModePies
from . import SculptModePies


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

    keybind = get_keybind_store(
        prefs,
        pref_id
    )

    if keybind is None:
        return

    keybind.key = kmi.type
    keybind.value = kmi.value

    keybind.shift = kmi.shift
    keybind.ctrl = kmi.ctrl
    keybind.alt = kmi.alt


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

            sync_kmi_to_preferences(
                prefs,
                kmi,
                pref_id
            )


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
    row.prop( keybind, "enabled", text="")
    row.label( text=get_menu_label(menu_id))

    if kmi is None:

        row.label( text=keybind.key)

        return

    # Keep persistent settings synchronized with Blender's
    # native key event widget.
    sync_kmi_to_preferences( prefs, kmi, pref_id)

    row.prop( kmi, "type", text="", event=True)
    row.prop( kmi, "value", text="")
    row.prop( kmi, "ctrl_ui", text="Ctrl", toggle=True)
    row.prop( kmi, "shift_ui", text="Shift", toggle=True)
    row.prop( kmi, "alt_ui", text="Alt", toggle=True)


# ADDON PREFERENCES
class AllPiePreferences(AddonPreferences):

    bl_idname = __package__

    keybinds: CollectionProperty(
        type=AllPieKeybind
    )

    def draw(self, context):

        kc = context.window_manager.keyconfigs.addon

        initialize_keybinds(self)

        # Save any changes made through Blender's key widget.
        if kc is not None:
            sync_all_keymaps_to_preferences()

        layout = self.layout

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
