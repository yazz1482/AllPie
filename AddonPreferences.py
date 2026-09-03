import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty
from bpy.props import FloatProperty
from bpy.props import BoolProperty
from bpy.props import EnumProperty

addon_keymaps = []

piekeymapitems = [
    # Sculpt Mode Keybinds
    # ("Preference Name", "Keymap name", "Key", "Key Value", "PieMenu Class Name", Shift KeyModifier, Ctrl KeyModifier, Alt KeyModifier)
    ("EnableEssentialsPie", "Sculpt", "W", "PRESS", "C_MT_EssentialsBrushPie", False, False, False),
    ("EnableUtilBrushPie", "Sculpt", "E", "PRESS", "C_MT_UtilBrushPie", False, False, False),
    ("EnableRemeshPie", "Sculpt", "R", "PRESS", "C_MT_RemeshPie", False, False, False),
    ("EnableSculptTransformPie", "Sculpt", "T", "PRESS", "C_MT_SculptTransformPie", False, False, False),
    ("EnableSymmetryPie", "Sculpt", "S", "PRESS", "C_MT_SymmetryPie", False, False, False),
    ("EnableMultiResPie", "Sculpt", "D", "PRESS", "C_MT_MultiResPie", False, False, False),
    ("EnableShadingPie", "Sculpt", "Z", "PRESS", "C_MT_ShadingPie", False, False, False),
    ("EnableSculptBrushSettingsPie", "Sculpt", "X", "PRESS", "C_MT_SculptBrushSettingsPie", False, False, False),
    ("EnableSculptPaintPie", "Sculpt", "C", "PRESS", "C_MT_SculptPaintPie", False, False, False),
    ("EnableSculptVisibilityPie", "Sculpt", "V", "PRESS", "C_MT_SculptVisibilityPie", False, False, False),
    ("EnableCustomBrushPie", "Sculpt", "W", "PRESS", "C_MT_CustomBrushPie", True, False, False),

    # Edit Mode Keybinds
    ("EnableEditModeSelectionPie", "Mesh", "A", "PRESS", "C_MT_EditModeSelectionPie", False, False, False),
    ("EnableEditModeShadingPie", "Mesh", "Z", "PRESS", "C_MT_ShadingPie", False, False, False),
    ("EnableEditModeDeletionPie", "Mesh", "X", "PRESS", "C_MT_EditModeDeletionPie", False, False, False),
    ("EnableEditModeMergePie", "Mesh", "M", "PRESS", "C_MT_EditModeMergePie", False, False, False),
    ("EnableEditModeModelPie", "Mesh", "W", "PRESS", "C_MT_EditModeModelPie", False, False, False),
    ("EnableEditModeVertexPie", "Mesh", "ONE", "PRESS", "C_MT_EditModeVertexPie", False, False, False),
    ("EnableEditModeEdgePie", "Mesh", "TWO", "PRESS", "C_MT_EditModeEdgePie", False, False, False),
    ("EnableEditModeFacePie", "Mesh", "THREE", "PRESS", "C_MT_EditModeFacePie", False, False, False),
    ("EnableEditModeModelPie", "Mesh", "T", "PRESS", "C_MT_EditModeToolSelectPie", False, False, False),

    # Object Mode Keybinds
    ("EnableObjectModeAddPie", "Object Mode", "A", "PRESS", "C_MT_ObjectModeAdd", True, False, False),
]

def get_asset_libs(self, context):
    items = []
    for library in context.preferences.filepaths.asset_libraries:
        items.append(( library.name, library.name, ""))
    return items


def ApKeymapResgister():
    kc = bpy.context.window_manager.keyconfigs.addon
    prefs = bpy.context.preferences.addons[__package__].preferences
    if not kc:
        return

    for pref_name, km_name, key, value, menu_name, mod_shift, mod_ctrl, mod_alt in piekeymapitems:

        #Dont register if the prefernce is disabled
        if not getattr(prefs, pref_name):
            continue

        km = kc.keymaps.get(km_name)

        if not km:
            km = kc.keymaps.new(
                name = km_name,
                space_type="EMPTY"
            )

        already_exist = False
        for kmi in km.keymap_items:
            if ( kmi.idname == "wm.call_menu_pie" and kmi.properties.name == menu_name):
                already_exist = True
                break

        if already_exist:
            continue

        kmi = km.keymap_items.new(
                "wm.call_menu_pie",
                type=key,
                value=value,
                ctrl=mod_ctrl,
                shift=mod_shift,
                alt=mod_alt,
                )
        kmi.properties.name = menu_name
        addon_keymaps.append((km, kmi))

def ApKeymapUnResgister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()

def update_pie_keymaps(self, context):
    ApKeymapUnResgister()
    ApKeymapResgister()


class AllpieCustomAddonPref(AddonPreferences):
    bl_idname = __package__

    #Sculpt Mode Properties

    #Bool Properties
    # Sculpt Mode Addon Prefernce Properties
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

    #Enum Properties
    #Custom Brushes Pie Menu Properties
    CustomLib_Slot1: EnumProperty( items=get_asset_libs)
    CustomLib_Slot2: EnumProperty( items=get_asset_libs)
    CustomLib_Slot3: EnumProperty( items=get_asset_libs)
    CustomLib_Slot4: EnumProperty( items=get_asset_libs)
    CustomLib_Slot5: EnumProperty( items=get_asset_libs)
    CustomLib_Slot6: EnumProperty( items=get_asset_libs)
    CustomLib_Slot7: EnumProperty( items=get_asset_libs)

    # String Properties
    #Essential Brushes Pie Menu Properties
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

    #Custom Brushes Pie Menu Properties
    CustomPieBrush_Slot1: StringProperty(default="")
    CustomPieBrush_Slot2: StringProperty(default="")
    CustomPieBrush_Slot3: StringProperty(default="")
    CustomPieBrush_Slot4: StringProperty(default="")
    CustomPieBrush_Slot5: StringProperty(default="")
    CustomPieBrush_Slot6: StringProperty(default="")
    CustomPieBrush_Slot7: StringProperty(default="")

    #Edit Mode Properties

    # Bools Properties
    # Edit Mode Addon Prefernce Properties
    EnableEditModeSelectionPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeDeletionPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeShadingPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeMergePie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeModelPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeVertexPie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeEdgePie: BoolProperty(default=True, update=update_pie_keymaps)
    EnableEditModeFacePie: BoolProperty(default=True, update=update_pie_keymaps)


    #Object Mode Properties

    # Bools Properties
    # Object Mode Addon Prefernce Properties
    EnableObjectModeAddPie: BoolProperty(default=True, update=update_pie_keymaps)

    def draw(self, context):

        wm = context.window_manager
        kc = wm.keyconfigs.addon

        layout = self.layout

        # Sculpt Mode Pie Menu Settings
        header, body = layout.panel("Sculpt_Mode_Pie_Menu_Settings", default_closed=True)
        header.label(text="Sculpt Mode Pie Menu Settings")
        if body:
            # Essential Brushes Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEssentialsPie", text = "Enable Essential Brushes Pie Menu")
            if self.EnableEssentialsPie == True:
                row = body.row()
                row.separator(factor=4)
                row.prop(self, "EnableEssentialsNestedPieMenu", text="Enable Nested Menu")
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EssentialsBrushPie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Utility Brushes Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableUtilBrushPie", text = "Enable Utility Brushes Pie Menu")
            if self.EnableUtilBrushPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_UtilBrushPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Remesh Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableRemeshPie", text = "Enable Remesh Pie Menu")
            if self.EnableRemeshPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_RemeshPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Sculpt Transform Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableSculptTransformPie", text = "Enable Sculpt Transform Pie Menu")
            if self.EnableSculptTransformPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_SculptTransformPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Sculpt Symmetry Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableSymmetryPie", text = "Enable Sculpt Symmetry Pie Menu")
            if self.EnableSymmetryPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_SymmetryPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Multires Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableMultiResPie", text = "Enable Multires Pie Menu")
            if self.EnableMultiResPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_MultiResPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Shading Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableShadingPie", text = "Enable Shading Pie Menu")
            if self.EnableShadingPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_ShadingPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Sculpt Brush Settings Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableSculptBrushSettingsPie", text = "Enable Sculpt Brush Settings Pie Menu")
            if self.EnableSculptBrushSettingsPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_SculptBrushSettingsPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Sculpt Paint Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableSculptPaintPie", text = "Enable Sculpt Paint Pie Menu")
            if self.EnableSculptPaintPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_SculptPaintPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Sculpt Visibility Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableSculptVisibilityPie", text = "Enable Sculpt Visibility Pie Menu")
            if self.EnableSculptVisibilityPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_SculptVisibilityPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # Sculpt Visibility Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableCustomBrushPie", text = "Enable Custom Sculpt Brush Pie Menu")
            if self.EnableSculptVisibilityPie == True:
                row = body.row()
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_CustomBrushPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

        #Edit Mode Pie Menu Settings
        header, body = layout.panel("Edit_Mode_Pie_Menu_Settings", default_closed=True)
        header.label(text="Edit Mode Pie Menu Settings")
        if body:
            # EditMode Model Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeModelPie", text = "Enable Edit Mode Quick Model Pie Menu")
            if self.EnableEditModeModelPie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeModelPie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Vertex Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeVertexPie", text = "Enable Edit Mode Vertex Pie Menu")
            if self.EnableEditModeVertexPie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeVertexPie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Edge Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeEdgePie", text = "Enable Edit Mode Edge Pie Menu")
            if self.EnableEditModeEdgePie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeEdgePie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Face Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeFacePie", text = "Enable Edit Mode Face Pie Menu")
            if self.EnableEditModeFacePie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeFacePie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Selection Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeSelectionPie", text = "Enable Edit Mode Selection Pie Menu")
            if self.EnableEditModeSelectionPie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeSelectionPie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Deletion Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeDeletionPie", text = "Enable Edit Mode Deletion Pie Menu")
            if self.EnableEditModeDeletionPie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeDeletionPie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Shading Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeShadingPie", text = "Enable Edit Mode Shading Pie Menu")
            if self.EnableEditModeShadingPie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_ShadingPie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

            # EditMode Merge Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableEditModeMergePie", text = "Enable Edit Mode Shading Pie Menu")
            if self.EnableEditModeMergePie == True:
                if kc:
                    km = kc.keymaps.get("Mesh")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EditModeMergePie":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break

        #Object Mode Pie Menu Settings
        header, body = layout.panel("Object_Mode_Pie_Menu_Settings", default_closed=True)
        header.label(text="Object Mode Pie Menu Settings")
        if body:
            # ObjectMode Add Pie Menu Keybind
            row = body.row()
            row.separator(factor=2)
            row.prop(self, "EnableObjectModeAddPie", text = "Enable Object Mode Add Pie Menu")
            if self.EnableObjectModeAddPie == True:
                if kc:
                    km = kc.keymaps.get("Object Mode")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_ObjectModeAdd":
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=4)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=8)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break


def register():
    bpy.utils.register_class(AllpieCustomAddonPref)
    ApKeymapResgister()

def unregister():

    bpy.utils.unregister_class(AllpieCustomAddonPref)
    ApKeymapUnResgister()

if __name__ == "__main__":
    register()
