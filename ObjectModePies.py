import bpy
from bpy.types import Menu

class AllPie_MT_ObjectModeAdd(Menu):
    bl_idname = "ALLPIE_MT_ObjectModeAdd"
    bl_label = "Add Primitives Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()

        #Left
        pie.operator("mesh.primitive_plane_add", text="Add Plane", icon="MESH_PLANE")
        #Right
        pie.operator("mesh.primitive_cube_add", text="Add Cube", icon="MESH_CUBE")
        #Bottom
        pie.operator("wm.search_single_menu", text="Search Add Menu", icon="VIEWZOOM").menu_idname = "VIEW3D_MT_add"
        #Top
        pie.operator("wm.call_menu", text="Add Menu", icon="ADD").name = "VIEW3D_MT_add"
        #Top Left
        pie.operator("mesh.primitive_cone_add", text="Add Cone", icon="MESH_CONE")
        #Top Right
        pie.operator("mesh.primitive_cylinder_add", text="Add Cylinder", icon="MESH_CYLINDER")
        #Bottom Left
        pie.operator("mesh.primitive_ico_sphere_add", text="Add Ico Sphere", icon="MESH_ICOSPHERE")
        #Bottom Right
        pie.operator("mesh.primitive_uv_sphere_add", text="Add UV Sphere", icon="MESH_UVSPHERE")

class AllPie_MT_ObjectModeApplyTransforms(Menu):
    bl_idname = "ALLPIE_MT_ObjectModeApplyTransforms"
    bl_label = "Apply Transforms"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()

        #Left
        transform_apply = pie.operator("object.transform_apply", text="Rotation & Scale", icon="REC")
        transform_apply.location = False
        transform_apply.rotation = True
        transform_apply.scale = True
        #Right
        transform_apply = pie.operator("object.transform_apply", text="All Transforms", icon="REC")
        transform_apply.location = True
        transform_apply.rotation = True
        transform_apply.scale = True
        #Bottom
        transform_apply = pie.operator("object.transform_apply", text="Rotation & Scale", icon="REC")
        transform_apply.location = False
        transform_apply.rotation = True
        transform_apply.scale = True
        #Top
        pie.operator("wm.call_menu", text="Apply Transforms Menu", icon="COLLAPSEMENU").name = "VIEW3D_MT_object_apply"
        #Top Left
        pie.separator()
        #Top Right
        pie.separator()
        #Bottom Left
        transform_apply = pie.operator("object.transform_apply", text="Location", icon="REC")
        transform_apply.location = True
        transform_apply.rotation = False
        transform_apply.scale = False
        #Bottom Right
        transform_apply = pie.operator("object.transform_apply", text="Scale", icon="REC")
        transform_apply.location = False
        transform_apply.rotation = False
        transform_apply.scale = True

class AllPie_MT_ObjectModeModifierPie(Menu):
    bl_idname = "ALLPIE_MT_ObjectModeModifierPie"
    bl_label = "Modifier Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # # Left
        pie.operator(
            "object.modifier_add", icon="MOD_SUBSURF", text="SubDivision"
        ).type = "SUBSURF"
        # # Right
        pie.operator(
            "object.modifier_add", icon="MOD_MIRROR", text="Mirror"
        ).type = "MIRROR"
        # Bottom
        pie.operator(
            "object.modifier_add", icon="MOD_DISPLACE", text="Displacement"
        ).type = "DISPLACE"
        # Top
        pie.operator(
            "wm.search_single_menu", icon="VIEWZOOM", text="Modifier Search"
        ).menu_idname = "OBJECT_MT_modifier_add"
        # Top Left
        pie.operator(
            "object.modifier_add", icon="MOD_MULTIRES", text="Multires"
        ).type = "MULTIRES"
        # Top Right
        pie.operator(
            "object.modifier_add", icon="MOD_SOLIDIFY", text="Solidify"
        ).type = "SOLIDIFY"
        # Bottom Left
        pie.operator(
            "object.modifier_add", icon="MOD_SHRINKWRAP", text="ShrinkWrap"
        ).type = "SHRINKWRAP"
        # Bottom Right
        slot6 = pie.operator(
            "object.modifier_add_node_group", icon="MOD_ARRAY", text="Array"
        )
        slot6.asset_library_type = "ESSENTIALS"
        slot6.asset_library_identifier = ""
        slot6.relative_asset_identifier = (
            "nodes/geometry_nodes_essentials.blend/NodeTree/Array"
        )

class AllPie_MT_ObjectModeSelectionPie(Menu):
    bl_idname = "ALLPIE_MT_ObjectModeSelectionPie"
    bl_label = "ObjectMode Selection Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "object.select_all", icon="CHECKBOX_DEHLT", text="Deselect All"
        ).action = "DESELECT"
        # Right
        pie.operator(
            "object.select_all", icon="CHECKBOX_HLT", text="Select All"
        ).action = "SELECT"
        # Bottom
        pie.operator(
            "object.select_all", icon="CLIPUV_HLT", text="Invert Selection"
        ).action = "INVERT"
        # Top
        pie.operator( "wm.call_menu", icon="REC", text="Right Click Menu"
        ).name = "VIEW3D_MT_object_context_menu"
        # # Top Left
        pie.operator( "wm.call_panel", icon="REC", text="Rename Object"
        ).name = "TOPBAR_PT_name"
        # # Top Right
        pie.operator( "wm.call_menu", icon="OUTLINER_COLLECTION", text="Move To Collection"
        ).name = "OBJECT_MT_move_to_collection"

        # Bottom Left
        pie.operator( "object.hide_view_clear", icon="REC", text="Unhide All"
        ).select=False
        # Bottom Right
        pie.operator( "object.hide_view_set", icon="REC", text="Solo Object"
        ).unselected = True


classes = (
    AllPie_MT_ObjectModeAdd,
    AllPie_MT_ObjectModeApplyTransforms,
    AllPie_MT_ObjectModeModifierPie,
    AllPie_MT_ObjectModeSelectionPie
        )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
if  __name__ == "__main__":
    register()
