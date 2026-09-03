import bpy
from bpy.types import Panel
from . import CustomOperators
from . import AddonPreferences

class C_PT_AllPieSettingsPanel(Panel):
    bl_label = "AllPie Brush Settings"
    bl_idname = "C_PT_AllPieBrush_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AllPie"  # Tab name in the N-panel

    def draw(self, context):
        layout = self.layout

        header, body = layout.panel("Essentials_Brushes_Pie", default_closed=True)
        header.label(text="Essentials Sculpt Brushes Pie")
        prefs = context.preferences.addons[__package__].preferences
        if body:
            # Slot 1
            body.label(text="Brush Slot1 (Middle Left):", icon="EVENT_NDOF_BUTTON_1")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot1", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot1"
            body.separator()

            # Slot 2
            body.label(text="Brush Slot2 (Middle Right):", icon="EVENT_NDOF_BUTTON_2")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot2", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot2"
            body.separator()

            # Slot 3
            body.label(text="Brush Slot3 (Top Left):", icon="EVENT_NDOF_BUTTON_3")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot3", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot3"
            body.separator()

            # Slot 4
            body.label(text="Brush Slot4 (Top Right):", icon="EVENT_NDOF_BUTTON_4")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot4", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot4"
            body.separator()

            # Slot 5
            body.label(text="Brush Slot5 (Bottom Left):", icon="EVENT_NDOF_BUTTON_5")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot5", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot5"
            body.separator()

            # Slot 6
            body.label(text="Brush Slot6 (Bottom Right):", icon="EVENT_NDOF_BUTTON_6")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot6", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot6"
            body.separator()

            # Slot 7
            body.label(text="Brush Slot7 (Bottom):", icon="EVENT_NDOF_BUTTON_7")
            row = body.row()
            row.prop(prefs, "EssentialPieBrush_Slot7", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrush_Slot7"
            body.separator()

        header, body = layout.panel(
            "Essentials_Brushes_Nested_Pie", default_closed=True
        )
        header.label(text="Essentials Sculpt Brushes Nested Pie")
        prefs = context.preferences.addons[__package__].preferences
        if body:
            # Slot 1
            body.label(text="Brush Slot1 (Middle Left):", icon="EVENT_NDOF_BUTTON_1")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot1", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text=prefs.EssentialPieBrushNested_Slot1
            ).PrefProperty = "EssentialPieBrushNested_Slot1"
            body.separator()

            # Slot 2
            body.label(text="Brush Slot2 (Middle Right):", icon="EVENT_NDOF_BUTTON_2")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot2", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrushNested_Slot2"
            body.separator()

            # Slot 3
            body.label(text="Brush Slot3 (Top Left):", icon="EVENT_NDOF_BUTTON_3")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot3", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrushNested_Slot3"
            body.separator()

            # Slot 4
            body.label(text="Brush Slot4 (Top Right):", icon="EVENT_NDOF_BUTTON_4")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot4", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrushNested_Slot4"
            body.separator()

            # Slot 5
            body.label(text="Brush Slot5 (Bottom Left):", icon="EVENT_NDOF_BUTTON_5")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot5", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrushNested_Slot5"
            body.separator()

            # Slot 6
            body.label(text="Brush Slot6 (Bottom Right):", icon="EVENT_NDOF_BUTTON_6")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot6", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrushNested_Slot6"
            body.separator()

            # Slot 7
            body.label(text="Brush Slot7 (Bottom):", icon="EVENT_NDOF_BUTTON_7")
            row = body.row()
            row.prop(prefs, "EssentialPieBrushNested_Slot7", text="Name")
            brushslot1 = row.operator(
                "cop.searchsculptbrushes", text="Search Brush"
            ).PrefProperty = "EssentialPieBrushNested_Slot7"
            body.separator()

        header, body = layout.panel("Custom_Sculpt_Brushes_Pie", default_closed=True)
        header.label(text="Custom Sculpt Brushes  Pie")
        prefs = context.preferences.addons[__package__].preferences
        if body:
            # Slot 1
            body.label(text="Brush Slot1 (Middle Left):", icon="EVENT_NDOF_BUTTON_1")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot1", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot1", text="Name")
            body.separator()

            # Slot 2
            body.label(text="Brush Slot2 (Middle Right):", icon="EVENT_NDOF_BUTTON_2")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot2", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot2", text="Name")
            body.separator()

            # Slot 3
            body.label(text="Brush Slot3 (Top Left):", icon="EVENT_NDOF_BUTTON_3")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot3", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot3", text="Name")
            body.separator()

            # Slot 4
            body.label(text="Brush Slot4 (Top Right):", icon="EVENT_NDOF_BUTTON_4")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot4", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot4", text="Name")
            body.separator()

            # Slot 5
            body.label(text="Brush Slot5 (bottom Left):", icon="EVENT_NDOF_BUTTON_5")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot5", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot5", text="Name")
            body.separator()

            # Slot 6
            body.label(text="Brush Slot6 (bottom Right):", icon="EVENT_NDOF_BUTTON_6")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot6", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot6", text="Name")
            body.separator()

            # Slot 7
            body.label(text="Brush Slot7 (bottom):", icon="EVENT_NDOF_BUTTON_7")
            row = body.row()
            row.prop(prefs, "CustomLib_Slot7", text="Library Name")
            row = body.row()
            row.prop(prefs, "CustomPieBrush_Slot7", text="Name")
            body.separator()



classes = (
    C_PT_AllPieSettingsPanel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
