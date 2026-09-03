import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty
from bpy.props import FloatProperty
from bpy.props import BoolProperty
from bpy.props import EnumProperty

addon_keymaps = []

piekeymapitems = [
        # Sculpt Mode Keybinds
        ("EnableEssentialsPie", "Sculpt", "W", "PRESS", "C_MT_EssentialsBrushPie"),
        ("EnableUtilBrushPie", "Sculpt", "E", "PRESS", "C_MT_UtilBrushPie"),
        ("EnableRemeshPie", "Sculpt", "R", "PRESS", "C_MT_RemeshPie"),
        ("EnableSculptTransformPie", "Sculpt", "T", "PRESS", "C_MT_SculptTransformPie"),
        ("EnableSymmetryPie", "Sculpt", "S", "PRESS", "C_MT_SymmetryPie"),
        ("EnableMultiResPie", "Sculpt", "D", "PRESS", "C_MT_MultiResPie"),
        ("EnableShadingPie", "Sculpt", "Z", "PRESS", "C_MT_ShadingPie"),
        ("EnableSculptBrushSettingsPie", "Sculpt", "X", "PRESS", "C_MT_SculptBrushSettingsPie"),
        ("EnableSculptPaintPie", "Sculpt", "C", "PRESS", "C_MT_SculptPaintPie"),
        ("EnableSculptVisibilityPie", "Sculpt", "V", "PRESS", "C_MT_SculptVisibilityPie"),
        ("EnableCustomBrushPie", "Sculpt", "B", "PRESS", "C_MT_CustomBrushPie"),

        # Edit Mode Keybinds
        ("EnableEditModeSelectionPie", "Mesh", "A", "PRESS", "C_MT_EditModeSelectionPie"),
        ("EnableEditModeShadingPie", "Mesh", "Z", "PRESS", "C_MT_ShadingPie"),
        ("EnableEditModeDeletionPie", "Mesh", "X", "PRESS", "C_MT_EditModeDeletetionPie"),
        ("EnableEditModeMergePie", "Mesh", "M", "PRESS", "C_MT_EditModeMergePie"),
        ("EnableEditModeModelPie", "Mesh", "W", "PRESS", "C_MT_EditModeModelPie"),
        ("EnableEditModeModelPie", "Mesh", "ONE", "PRESS", "C_MT_EditModeModelVertexPie"),
        ("EnableEditModeModelPie", "Mesh", "TWO", "PRESS", "C_MT_EditModeModelEdgePie"),
        ("EnableEditModeModelPie", "Mesh", "THREE", "PRESS", "C_MT_EditModeModelFacePie"),
        ("EnableEditModeModelPie", "Mesh", "T", "PRESS", "C_MT_EditModeToolSelectPie"),
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

    for pref_name, km_name, key, value, menu_name in piekeymapitems:

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

    def draw(self, context):

        wm = context.window_manager
        kc = wm.keyconfigs.addon

        layout = self.layout

        header, body = layout.panel("Sculpt_Mode_Pie_Menus", default_closed=True)
        header.label(text="Sculpt Mode Pie Menus")
        prefs = context.preferences.addons[__package__].preferences
        if body:
            # Essential Brushes Pie Menu Keybind
            body.prop(self, "EnableEssentialsPieMenu", text = "Enable Essential Brushes Pie Menu")
            if self.EnableEssentialsPie == True:
                row = body.row()
                row.separator(factor=2)
                row.prop(self, "EnableEssentialsNestedPieMenu", text="Enable Nested Menu")
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EssentialsBrushPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=4)
                                row.prop(kmi, "ctrl_ui", toggle=True)
                                row.prop(kmi, "shift_ui", toggle=True)
                                row.prop(kmi, "alt_ui", toggle=True)
                                break
            # Utility Brushes Pie Menu Keybind
            body.prop(self, "EnableUtilBrushPie", text = "Enable Utility Brushes Pie Menu")
            if self.EnableUtilBrushPie == True:
                row = body.row()
                row.separator(factor=2)
                if kc:
                    km = kc.keymaps.get("Sculpt")
                    if km:
                        for kmi in km.keymap_items:
                            if kmi.idname == "wm.call_menu_pie" and kmi.properties.name == "C_MT_EssentialsBrushPie":
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key:")
                                row.prop(kmi, "type",text="", event=True)
                                row.prop(kmi, "value")
                                row = body.row()
                                row.separator(factor=2)
                                row.label(text="Key Modifiers:")
                                row.separator(factor=4)
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
