import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import ( FloatProperty, FloatVectorProperty, StringProperty, IntProperty, BoolProperty, CollectionProperty,)

from . import EditModePies
from . import SculptModePies
from . import ObjectModePies
from . import TexturePaintPies
from . import VertexPaintPies
from . import WeightPaintPies

def update_essential_brushes(self, context):

    normal = (
        "EssentialBrush_Slot1",
        "EssentialBrush_Slot2",
        "EssentialBrush_Slot3",
        "EssentialBrush_Slot4",
        "EssentialBrush_Slot5",
        "EssentialBrush_Slot6",
        "EssentialBrush_Slot7",
        "EssentialBrush_Slot8"
    )

    spaced = (
        "EssentialSpaceBrush_Slot1",
        "EssentialSpaceBrush_Slot2",
        "EssentialSpaceBrush_Slot3",
        "EssentialSpaceBrush_Slot4",
        "EssentialSpaceBrush_Slot5",
        "EssentialSpaceBrush_Slot6",
        "EssentialSpaceBrush_Slot7",
    )

    for slot, prop in enumerate(normal):
        brush = getattr(self, prop)
        item = next(item for item in SculptModePies.ESSENTIALS_BRUSH_MENU if item["slot"] == slot)
        item["label"] = brush
        item["props"]["relative_asset_identifier"] = ( SculptModePies.ESSENTIALS_PATH + brush)

    for slot, prop in enumerate(spaced, start=1):
        brush = getattr(self, prop)
        item = next(item for item in SculptModePies.ESSENTIALS_BRUSH_SPACE_MENU if item["slot"] == slot)
        item["label"] = brush
        item["props"]["relative_asset_identifier"] = (
            SculptModePies.ESSENTIALS_PATH + brush
        )

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

    for index, (key, menu_id, modifiers) in enumerate(
        TexturePaintPies.TEXTUREPAINT_HOTKEYS
    ):
        definitions.append((
            f"TEXTUREPAINT_{index}",
            "Image Paint",
            key,
            "PRESS",
            menu_id,
            modifiers,
        ))

    for index, (key, menu_id, modifiers) in enumerate(
        VertexPaintPies.VERTEXPAINT_HOTKEYS
    ):
        definitions.append((
            f"VERTEXPAINT_{index}",
            "Vertex Paint",
            key,
            "PRESS",
            menu_id,
            modifiers,
        ))

    for index, (key, menu_id, modifiers) in enumerate(
        WeightPaintPies.WEIGHTPAINT_HOTKEYS
    ):
        definitions.append((
            f"WEIGHTPAINT_{index}",
            "Weight Paint",
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

    slot_color: FloatVectorProperty( name="Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.02, 0.02, 0.02, 1.0), min=0.0, max=1.0,)
    active_slot_color: FloatVectorProperty( name="Active Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.14, 0.14, 0.14, 1.00), min=0.0, max=1.0,)
    #Spaced Slot Color
    spaced_slot_color: FloatVectorProperty( name="Spaced Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.02, 0.02, 0.02, 1.0), min=0.0, max=1.0,)
    spaced_active_slot_color: FloatVectorProperty( name="Spaced Active Slot Color", subtype="COLOR_GAMMA", size=4, default=(0.14, 0.14, 0.14, 1.00), min=0.0, max=1.0,)

    font_color: FloatVectorProperty( name="Font Color", subtype="COLOR_GAMMA", size=4, default=(1.00, 1.00, 1.00, 1.0), min=0.0, max=1.0,)
    active_font_color: FloatVectorProperty( name="Active Font Color", subtype="COLOR_GAMMA", size=4, default=(0.45, 0.75, 0.97, 1.0), min=0.0, max=1.0,)
    #Spaced Font Color
    spaced_font_color: FloatVectorProperty( name="Spaced Font Color", subtype="COLOR_GAMMA", size=4, default=(1.00, 1.00, 1.00, 1.0), min=0.0, max=1.0,)
    spaced_active_font_color: FloatVectorProperty( name="Spaced Active Font Color", subtype="COLOR_GAMMA", size=4, default=(0.82, 0.55, 0.33, 1.0), min=0.0, max=1.0,)

    outline_color: FloatVectorProperty( name="Outline Color", subtype="COLOR_GAMMA", size=4, default=(0.18, 0.42, 0.70, 1.00), min=0.0, max=1.0,)
    spaced_outline_color: FloatVectorProperty( name="Spaced Outline Color", subtype="COLOR_GAMMA", size=4, default=(0.82, 0.55, 0.33, 1.00), min=0.0, max=1.0,)
    
    mark_color: FloatVectorProperty( name="Mark Color", subtype="COLOR_GAMMA", size=4, default=(1.00, 1.00, 1.00, 1.0), min=0.0, max=1.0,)

# Brush Properties
# ESSENTIAL BRUSHES
    EssentialBrush_Slot1: StringProperty(default="DRAW", update=update_essential_brushes)
    EssentialBrush_Slot2: StringProperty(default="DRAW SHARP", update=update_essential_brushes)
    EssentialBrush_Slot3: StringProperty(default="CLAY STRIPS", update=update_essential_brushes)
    EssentialBrush_Slot4: StringProperty(default="MASK", update=update_essential_brushes)
    EssentialBrush_Slot5: StringProperty(default="SCRAPE/FILL", update=update_essential_brushes)
    EssentialBrush_Slot6: StringProperty(default="INFLATE/DEFLATE", update=update_essential_brushes)
    EssentialBrush_Slot7: StringProperty(default="GRAB", update=update_essential_brushes)
    EssentialBrush_Slot8: StringProperty(default="PINCH/MAGNIFY", update=update_essential_brushes)

# SPACE ESSENTIAL BRUSHES
    EssentialSpaceBrush_Slot1: StringProperty(default="CREASE SHARP", update=update_essential_brushes)
    EssentialSpaceBrush_Slot2: StringProperty(default="CLAY", update=update_essential_brushes)
    EssentialSpaceBrush_Slot3: StringProperty(default="FACE SET PAINT", update=update_essential_brushes)
    EssentialSpaceBrush_Slot4: StringProperty(default="TRIM", update=update_essential_brushes)
    EssentialSpaceBrush_Slot5: StringProperty(default="ERASE MULTIRES DISPLACEMENT", update=update_essential_brushes)
    EssentialSpaceBrush_Slot6: StringProperty(default="SNAKE HOOK", update=update_essential_brushes)
    EssentialSpaceBrush_Slot7: StringProperty(default="RELAX SLIDE", update=update_essential_brushes)

    def draw(self, context):

        update_essential_brushes(self, context)

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

        # ESSENTIAL SCULPT BRUSHES
        header, body = layout.panel( "AllPie_Essential_Brushes", default_closed=True,)
        header.label( text="Essential Sculpt Brushes Menu Settings")

        if body:
            row = body.row(align=True)
            row.separator(factor=4)
            row.label(text="Essentials Brushes")

            for slot in range(1, 9):
                row = body.row(align=True)
                row.separator(factor=4)
                row.label(text=f"Slot {slot}", icon="BRUSH_DATA")
                row.prop(self, f"EssentialBrush_Slot{slot}", text="")
                row.operator("cop.searchsculptbrushes", text="Search").PrefProperty = f"EssentialBrush_Slot{slot}"

            body.separator()

            row = body.row(align=True)
            row.separator(factor=4)
            row.label(text="Essential Spaced Brushes")

            row = body.row(align=True)
            row.separator(factor=4)
            row.label(text="Slot 0", icon="ASSET_MANAGER")
            row.label(text="Asset Shelf")
            row.separator()

            for slot in range(1, 8):
                row = body.row(align=True)
                row.separator(factor=4)
                row.label(text=f"Slot {slot}", icon="BRUSH_DATA")
                row.prop(self, f"EssentialSpaceBrush_Slot{slot}", text="")
                row.operator("cop.searchsculptbrushes", text="Search").PrefProperty = f"EssentialSpaceBrush_Slot{slot}"


        # EDIT MODE
        header, body = layout.panel( "AllPie_Edit_Mode", default_closed=True,)
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
        header, body = layout.panel( "AllPie_Sculpt_Mode", default_closed=True,)
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
        header, body = layout.panel( "AllPie_Object_Mode", default_closed=True,)
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
        # Texture Paint MODE
        header, body = layout.panel( "AllPie_Texture_Paint_Mode", default_closed=True,)
        header.label( text="Texture Paint")

        if body:

            for (
                pref_id,
                keymap_name,
                default_key,
                default_value,
                menu_id,
                modifiers,
            ) in get_keybind_definitions():

                if keymap_name != "Image Paint":
                    continue

                draw_keybind(
                    body,
                    kc,
                    self,
                    pref_id,
                    keymap_name,
                    menu_id,
                )

        # Vertex Paint MODE
        header, body = layout.panel( "AllPie_Vertex_Paint_Mode", default_closed=True,)
        header.label( text="Vertex Paint")

        if body:

            for (
                pref_id,
                keymap_name,
                default_key,
                default_value,
                menu_id,
                modifiers,
            ) in get_keybind_definitions():

                if keymap_name != "Vertex Paint":
                    continue

                draw_keybind(
                    body,
                    kc,
                    self,
                    pref_id,
                    keymap_name,
                    menu_id,
                )

        # Weight Paint MODE
        header, body = layout.panel( "AllPie_Weight_Paint_Mode", default_closed=True,)
        header.label( text="Weight Paint")

        if body:

            for (
                pref_id,
                keymap_name,
                default_key,
                default_value,
                menu_id,
                modifiers,
            ) in get_keybind_definitions():

                if keymap_name != "Weight Paint":
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
        update_essential_brushes(prefs, None)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
