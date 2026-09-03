import bpy
from bpy.types import Menu
from . import AddonPreferences

class C_MT_ObjectModeAdd(Menu):
    bl_label = "Add Primitives/Add Menu Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()

        #Left
        pie.operator("mesh.primitive_plane_add", text="Add Plane", icon="MESH_PLANE")
        #Right
        pie.operator("mesh.primitive_cube_add", text="Add Cube", icon="MESH_CUBE")
        #Bottom
        pie.operator("wm.search_single_menu", text="Search Add menu").menu_idname = "VIEW3D_MT_add"
        #Top
        pie.operator("wm.search_single_menu", text="Search Add menu").menu_idname = "VIEW3D_MT_add"
        #Top Left
        pie.operator("mesh.primitive_cone_add", text="Add Cone", icon="MESH_CONE")
        #Top Right
        pie.operator("mesh.primitive_cylinder_add", text="Add Cylinder", icon="MESH_CYLINDER")
        #Bottom Left
        pie.operator("mesh.primitive_ico_sphere_add", text="Add Ico Sphere", icon="MESH_ICOSPHERE")
        #Bottom Right
        pie.operator("mesh.primitive_uv_sphere_add", text="Add UV Sphere", icon="MESH_UVSPHERE")

classes = (
    C_MT_ObjectModeAdd,
        )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
if  __name__ == "__main__":
    register()
