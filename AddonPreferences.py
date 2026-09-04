import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import ( StringProperty, FloatProperty, BoolProperty, EnumProperty, CollectionProperty,)

addon_keymaps = []

piekeymapitems = [
    # Sculpt Mode Keybinds
    # ("Preference Name", "Keymap name", "Key", "Key Value",
    #  "PieMenu Class Name", Shift KeyModifier, Ctrl KeyModifier, Alt KeyModifier)
    ("EnableEssentialsPie", "Sculpt", "W", "PRESS", "ALLPIE_MT_EssentialsBrushPie", False, False, False),
    ("EnableUtilBrushPie", "Sculpt", "E", "PRESS", "ALLPIE_MT_UtilBrushPie", False, False, False),
    ("EnableRemeshPie", "Sculpt", "R", "PRESS", "ALLPIE_MT_RemeshPie", False, False, False),
    ("EnableSculptTransformPie", "Sculpt", "T", "PRESS", "AllPie_MT_SculptTransformPie", False, False, False),
    ("EnableSymmetryPie", "Sculpt", "S", "PRESS", "ALLPIE_MT_SymmetryPie", False, False, False),
    ("EnableMultiResPie", "Sculpt", "D", "PRESS", "ALLPIE_MT_MultiResPie", False, False, False),
    ("EnableShadingPie", "Sculpt", "Z", "PRESS", "ALLPIE_MT_ShadingPie", False, False, False),
    ("EnableSculptBrushSettingsPie", "Sculpt", "X", "PRESS", "ALLPIE_MT_SculptBrushSettingsPie", False, False, False),
    ("EnableSculptPaintPie", "Sculpt", "C", "PRESS", "ALLPIE_MT_SculptPaintPie", False, False, False),
    ("EnableSculptVisibilityPie", "Sculpt", "V", "PRESS", "ALLPIE_MT_SculptVisibilityPie", False, False, False),
    ("EnableCustomBrushPie", "Sculpt", "W", "PRESS", "ALLPIE_MT_CustomBrushPie", True, False, False),

    # Edit Mode Keybinds
    ("EnableEditModeSelectionPie", "Mesh", "A", "PRESS", "ALLPIE_MT_EditModeSelectionPie", False, False, False),
    ("EnableEditModeShadingPie", "Mesh", "Z", "PRESS", "ALLPIE_MT_ShadingPie", False, False, False),
    ("EnableEditModeDeletionPie", "Mesh", "X", "PRESS", "ALLPIE_MT_EditModeDeletionPie", False, False, False),
    ("EnableEditModeMergePie", "Mesh", "M", "PRESS", "ALLPIE_MT_EditModeMergePie", False, False, False),
    ("EnableEditModeModelPie", "Mesh", "W", "PRESS", "ALLPIE_MT_EditModeModelPie", False, False, False),
    ("EnableEditModeVertexPie", "Mesh", "ONE", "PRESS", "ALLPIE_MT_EditModeVertexPie", False, False, False),
    ("EnableEditModeEdgePie", "Mesh", "TWO", "PRESS", "ALLPIE_MT_EditModeEdgePie", False, False, False),
    ("EnableEditModeFacePie", "Mesh", "THREE", "PRESS", "ALLPIE_MT_EditModeFacePie", False, False, False),
    ("EnableEditModeToolSelectPie", "Mesh", "T", "PRESS", "ALLPIE_MT_EditModeToolSelectPie", False, False, False),
    ("EnableEditModeUVPie", "Mesh", "U", "PRESS", "ALLPIE_MT_EditModeUVPie", False, False, False),

    # Object Mode Keybinds
    ("EnableObjectModeAddPie", "Object Mode", "A", "PRESS", "ALLPIE_MT_ObjectModeAdd", True, False, False),
]


class AllPieKeybind(PropertyGroup):
    """Persistent copy of a pie keybind.

    The actual KeyMapItem is still used by the UI so Blender's native
    key-capture widget remains available. These properties are the values
    we restore when the add-on registers its keymaps again.
    """

    menu_name: StringProperty()
    key: StringProperty()
    value: StringProperty()
    shift: BoolProperty()
    ctrl: BoolProperty()
    alt: BoolProperty()


def get_asset_libs(self, context):
    items = []
    for library in context.preferences.filepaths.asset_libraries:
        items.append((library.name, library.name, ""))
    return items


def get_keybind_store(prefs, menu_name):
    for keybind in prefs.keybinds:
        if keybind.menu_name == menu_name:
            return keybind
    return None


def initialize_keybinds(prefs):
    """Create persistent keybind entries for any pie that does not have one yet."""
    for (
        pref_name,
        km_name,
        default_key,
        default_value,
        menu_name,
        default_shift,
        default_ctrl,
        default_alt,
    ) in piekeymapitems:

        keybind = get_keybind_store(prefs, menu_name)

        if keybind is None:
            keybind = prefs.keybinds.add()
            keybind.menu_name = menu_name
            keybind.key = default_key
            keybind.value = default_value
            keybind.shift = default_shift
            keybind.ctrl = default_ctrl
            keybind.alt = default_alt


def find_addon_kmi(kc, km_name, menu_name):
    """Find a wm.call_menu_pie keymap item by keymap and pie menu name."""
    km = kc.keymaps.get(km_name)

    if km is None:
        return None

    for kmi in km.keymap_items:
        if (
            kmi.idname == "wm.call_menu_pie"
            and kmi.properties.name == menu_name
        ):
            return kmi

    return None


def sync_kmi_to_preferences(prefs, kmi):
    """Copy the live Blender keymap item into persistent add-on preferences."""
    menu_name = kmi.properties.name
    keybind = get_keybind_store(prefs, menu_name)

    if keybind is None:
        return

    keybind.key = kmi.type
    keybind.value = kmi.value
    keybind.shift = kmi.shift
    keybind.ctrl = kmi.ctrl
    keybind.alt = kmi.alt


def sync_all_keymaps_to_preferences():
    """Save all currently visible addon keymap edits into AddonPreferences."""
    kc = bpy.context.window_manager.keyconfigs.addon
    prefs = bpy.context.preferences.addons[__package__].preferences

    if kc is None:
        return

    initialize_keybinds(prefs)

    for (
        pref_name,
        km_name,
        default_key,
        default_value,
        menu_name,
        default_shift,
        default_ctrl,
        default_alt,
    ) in piekeymapitems:
        kmi = find_addon_kmi(kc, km_name, menu_name)

        if kmi is not None:
            sync_kmi_to_preferences(prefs, kmi)


def ApKeymapResgister():
    kc = bpy.context.window_manager.keyconfigs.addon
    prefs = bpy.context.preferences.addons[__package__].preferences

    if not kc:
        return

    initialize_keybinds(prefs)

    for (
        pref_name,
        km_name,
        default_key,
        default_value,
        menu_name,
        default_shift,
        default_ctrl,
        default_alt,
    ) in piekeymapitems:

        # Don't register if the preference is disabled.
        if not getattr(prefs, pref_name):
            continue

        keybind = get_keybind_store(prefs, menu_name)

        # This should only be possible if initialization failed.
        if keybind is None:
            continue

        km = kc.keymaps.get(km_name)

        if km is None:
            km = kc.keymaps.new(
                name=km_name,
                space_type="EMPTY",
            )

        kmi = find_addon_kmi(kc, km_name, menu_name)

        if kmi is None:
            kmi = km.keymap_items.new(
                "wm.call_menu_pie",
                type=keybind.key,
                value=keybind.value,
                ctrl=keybind.ctrl,
                shift=keybind.shift,
                alt=keybind.alt,
            )
            kmi.properties.name = menu_name
            addon_keymaps.append((km, kmi))
        else:
            # If Blender already has our addon KMI, restore the persistent values.
            kmi.type = keybind.key
            kmi.value = keybind.value
            kmi.ctrl = keybind.ctrl
            kmi.shift = keybind.shift
            kmi.alt = keybind.alt
            kmi.properties.name = menu_name


def ApKeymapUnResgister():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except ReferenceError:
            pass

    addon_keymaps.clear()


def update_pie_keymaps(self, context):
    # IMPORTANT:
    # Save any keybind edits before rebuilding the enabled/disabled keymaps.
    sync_all_keymaps_to_preferences()

    ApKeymapUnResgister()
    ApKeymapResgister()


def draw_pie_keybind(body, kc, prefs, km_name, menu_name):
    """Draw one pie keybind using Blender's native KeyMapItem event widget."""
    kmi = find_addon_kmi(kc, km_name, menu_name)

    if kmi is None:
        return

    # Persist the current value so it survives Blender restart.
    sync_kmi_to_preferences(prefs, kmi)

    row = body.row()
    row.separator(factor=4)
    row.label(text="Key:")
    row.prop(kmi, "type", text="", event=True)
    row.prop(kmi, "value")

    row = body.row()
    row.separator(factor=4)
    row.label(text="Key Modifiers:")
    row.separator(factor=8)
    row.prop(kmi, "ctrl_ui", toggle=True)
    row.prop(kmi, "shift_ui", toggle=True)
    row.prop(kmi, "alt_ui", toggle=True)


class AllpieCustomAddonPref(AddonPreferences):
    bl_idname = __package__

    # Persistent keybind data.
    keybinds: CollectionProperty(type=AllPieKeybind)

    # Sculpt Mode Properties

    # Bool Properties
    EnableEssentialsPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEssentialsNestedPieMenu: BoolProperty(default=True)
    EnableSymmetryPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableRemeshPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableShadingPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableMultiResPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableSculptPaintPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableSculptBrushSettingsPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableSculptTransformPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableUtilBrushPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableSculptVisibilityPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableCustomBrushPie: BoolProperty(default=True, update=update_pie_keymaps)

    # Enum Properties
    # Custom Brushes Pie Menu Properties
    CustomLib_Slot1: EnumProperty(items=get_asset_libs)
    CustomLib_Slot2: EnumProperty(items=get_asset_libs)
    CustomLib_Slot3: EnumProperty(items=get_asset_libs)
    CustomLib_Slot4: EnumProperty(items=get_asset_libs)
    CustomLib_Slot5: EnumProperty(items=get_asset_libs)
    CustomLib_Slot6: EnumProperty(items=get_asset_libs)
    CustomLib_Slot7: EnumProperty(items=get_asset_libs)

    # String Properties
    # Essential Brushes Pie Menu Properties
    EssentialPieBrush_Slot1: StringProperty(default="GRAB")
    EssentialPieBrush_Slot2: StringProperty(default="CLAY STRIPS")
    EssentialPieBrush_Slot3: StringProperty(default="PINCH/MAGNIFY")
    EssentialPieBrush_Slot4: StringProperty(default="DRAW SHARP")
    EssentialPieBrush_Slot5: StringProperty(default="INFLATE/DEFLATE")
    EssentialPieBrush_Slot6: StringProperty(default="DRAW")
    EssentialPieBrush_Slot7: StringProperty(default="SCRAPE/FILL")
    EssentialPieBrushNested_Slot1: StringProperty(default="TRIM")
    EssentialPieBrushNested_Slot2: StringProperty(default="CREASE SHARP")
    EssentialPieBrushNested_Slot3: StringProperty(default="SNAKE HOOK")
    EssentialPieBrushNested_Slot4: StringProperty(default="CLAY")
    EssentialPieBrushNested_Slot5: StringProperty(default="ERASE MULTIRES DISPLACEMENT")
    EssentialPieBrushNested_Slot6: StringProperty(default="POSE")
    EssentialPieBrushNested_Slot7: StringProperty(default="MASK")

    # Custom Brushes Pie Menu Properties
    CustomPieBrush_Slot1: StringProperty(default="")
    CustomPieBrush_Slot2: StringProperty(default="")
    CustomPieBrush_Slot3: StringProperty(default="")
    CustomPieBrush_Slot4: StringProperty(default="")
    CustomPieBrush_Slot5: StringProperty(default="")
    CustomPieBrush_Slot6: StringProperty(default="")
    CustomPieBrush_Slot7: StringProperty(default="")

    # Edit Mode Properties

    # Bool Properties
    EnableEditModeSelectionPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeDeletionPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeShadingPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeMergePie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeModelPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeVertexPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeEdgePie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeFacePie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeContextPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeToolSelectPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeUVPie: BoolProperty(default=True, update=update_pie_keymaps)
    # Object Mode Properties

    # Bool Properties
    EnableObjectModeAddPie: BoolProperty(default=True, update=update_pie_keymaps)

    def draw(self, context):
        wm = context.window_manager
        kc = wm.keyconfigs.addon

        # Make sure new keybinds are added without overwriting old user settings.
        initialize_keybinds(self)

        layout = self.layout

        # Sculpt Mode Pie Menu Settings
        header, body = layout.panel(
            "Sculpt_Mode_Pie_Menu_Settings",
            default_closed=True,
        )
        header.label(text="Sculpt Mode Pie Menu Settings")

        if body:
            # Essential Brushes Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEssentialsPie",
                text="Enable Essential Brushes Pie Menu",
            )

            if self.EnableEssentialsPie:
                row = body.row()
                row.separator(factor=4)
                row.prop(
                    self,
                    "EnableEssentialsNestedPieMenu",
                    text="Enable Nested Menu",
                )

                if kc:
                    draw_pie_keybind(
                        body,
                        kc,
                        self,
                        "Sculpt",
                        "ALLPIE_MT_EssentialsBrushPie",
                    )

            # Utility Brushes Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableUtilBrushPie",
                text="Enable Utility Brushes Pie Menu",
            )

            if self.EnableUtilBrushPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_UtilBrushPie",
                )

            # Remesh Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableRemeshPie",
                text="Enable Remesh Pie Menu",
            )

            if self.EnableRemeshPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_RemeshPie",
                )

            # Sculpt Transform Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableSculptTransformPie",
                text="Enable Sculpt Transform Pie Menu",
            )

            if self.EnableSculptTransformPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_SculptTransformPie",
                )

            # Symmetry Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableSymmetryPie",
                text="Enable Sculpt Symmetry Pie Menu",
            )

            if self.EnableSymmetryPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_SymmetryPie",
                )

            # Multires Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableMultiResPie",
                text="Enable Multires Pie Menu",
            )

            if self.EnableMultiResPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_MultiResPie",
                )

            # Shading Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableShadingPie",
                text="Enable Shading Pie Menu",
            )

            if self.EnableShadingPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_ShadingPie",
                )

            # Sculpt Brush Settings Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableSculptBrushSettingsPie",
                text="Enable Sculpt Brush Settings Pie Menu",
            )

            if self.EnableSculptBrushSettingsPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_SculptBrushSettingsPie",
                )

            # Sculpt Paint Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableSculptPaintPie",
                text="Enable Sculpt Paint Pie Menu",
            )

            if self.EnableSculptPaintPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_SculptPaintPie",
                )

            # Sculpt Visibility Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableSculptVisibilityPie",
                text="Enable Sculpt Visibility Pie Menu",
            )

            if self.EnableSculptVisibilityPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_SculptVisibilityPie",
                )

            # Custom Brush Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableCustomBrushPie",
                text="Enable Custom Sculpt Brush Pie Menu",
            )

            if self.EnableCustomBrushPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Sculpt",
                    "ALLPIE_MT_CustomBrushPie",
                )

        # Edit Mode Pie Menu Settings
        header, body = layout.panel(
            "Edit_Mode_Pie_Menu_Settings",
            default_closed=True,
        )
        header.label(text="Edit Mode Pie Menu Settings")

        if body:
            # Edit Mode Model Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeModelPie",
                text="Enable Edit Mode Quick Model Pie Menu",
            )

            if self.EnableEditModeModelPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeModelPie",
                )

            # Edit Mode Tool Select Pie Menu
            # This uses the same EnableEditModeModelPie property as in the
            # original file because that is how your current settings are structured.
            if self.EnableEditModeToolSelectPie and kc:
                row = body.row()
                row.separator(factor=2)
                row.label(text="Tool Select Pie Menu")

                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeToolSelectPie",
                )

            # Edit Mode Vertex Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeVertexPie",
                text="Enable Edit Mode Vertex Pie Menu",
            )

            if self.EnableEditModeVertexPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeVertexPie",
                )

            # Edit Mode Edge Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeEdgePie",
                text="Enable Edit Mode Edge Pie Menu",
            )

            if self.EnableEditModeEdgePie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeEdgePie",
                )

            # Edit Mode Face Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeFacePie",
                text="Enable Edit Mode Face Pie Menu",
            )

            if self.EnableEditModeFacePie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeFacePie",
                )

            # Edit Mode Selection Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeSelectionPie",
                text="Enable Edit Mode Selection Pie Menu",
            )

            if self.EnableEditModeSelectionPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeSelectionPie",
                )

            # Edit Mode Deletion Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeDeletionPie",
                text="Enable Edit Mode Deletion Pie Menu",
            )

            if self.EnableEditModeDeletionPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeDeletionPie",
                )

            # Edit Mode Shading Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeShadingPie",
                text="Enable Edit Mode Shading Pie Menu",
            )

            if self.EnableEditModeShadingPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_ShadingPie",
                )

            # Edit Mode Merge Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeMergePie",
                text="Enable Edit Mode Merge Pie Menu",
            )

            if self.EnableEditModeMergePie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeMergePie",
                )
            # Edit Mode UV Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableEditModeMergePie",
                text="Enable Edit Mode Merge Pie Menu",
            )

            if self.EnableEditModeUVPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Mesh",
                    "ALLPIE_MT_EditModeUVPie",
                )

        # Object Mode Pie Menu Settings
        header, body = layout.panel(
            "Object_Mode_Pie_Menu_Settings",
            default_closed=True,
        )
        header.label(text="Object Mode Pie Menu Settings")

        if body:
            # Object Mode Add Pie Menu
            row = body.row()
            row.separator(factor=2)
            row.prop(
                self,
                "EnableObjectModeAddPie",
                text="Enable Object Mode Add Pie Menu",
            )

            if self.EnableObjectModeAddPie and kc:
                draw_pie_keybind(
                    body,
                    kc,
                    self,
                    "Object Mode",
                    "ALLPIE_MT_ObjectModeAdd",
                )


classes = (
    AllPieKeybind,
    AllpieCustomAddonPref,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    prefs = bpy.context.preferences.addons[__package__].preferences
    initialize_keybinds(prefs)
    ApKeymapResgister()


def unregister():
    ApKeymapUnResgister()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
