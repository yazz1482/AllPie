import bpy
from bpy.types import Menu
from . import AddonPreferences

class AllPie_MT_ObjectModeAdd(Menu):
    bl_idname = "ALLPIE_MT_ObjectModeAdd"
    bl_label = "Add Primitives/Add Menu Pie"

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
        transform_apply.scale = False
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

classes = (
    AllPie_MT_ObjectModeAdd,
    AllPie_MT_ObjectModeApplyTransforms,
        )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
if  __name__ == "__main__":
    register()
