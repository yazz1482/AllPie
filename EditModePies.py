import bpy
from bpy.types import Operator
from bpy.types import Menu
from . import CustomOperators
from . import AddonPreferences


class C_MT_EditModeSelectionPie(Menu):
    bl_label = "EditMode Selection Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "mesh.select_all", icon="CHECKBOX_DEHLT", text="Deselect All"
        ).action = "DESELECT"
        # Right
        pie.operator(
            "mesh.select_all", icon="CHECKBOX_HLT", text="Select All"
        ).action = "SELECT"
        # Bottom
        pie.operator(
            "mesh.select_all", icon="CLIPUV_HLT", text="Invert Selection"
        ).action = "INVERT"
        # Top
        pie.operator(
            "mesh.select_mode", icon="EDGESEL", text="Edge Select"
        ).type = "EDGE"
        # Top Left
        pie.operator(
            "mesh.select_mode", icon="VERTEXSEL", text="Vert Select"
        ).type = "VERT"
        # Top Right
        pie.operator(
            "mesh.select_mode", icon="FACESEL", text="Face Select"
        ).type = "FACE"
        # Bottom Left
        pie.operator("mesh.edges_select_sharp", icon="CUBE", text="Select Sharp")
        # Bottom Right
        pie.operator(
            "mesh.loop_to_region", icon="RIGID_BODY", text="Select Loop Inner Region"
        ).select_bigger = True


class C_MT_EditModeDeletionPie(Menu):
    bl_label = "EditMode Deletion Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Left
        pie.operator(
            "mesh.delete", icon="MOD_EDGESPLIT", text="Only Edge & Faces"
        ).type = "EDGE_FACE"
        # Right
        pie.operator(
            "mesh.delete", icon="FACE_MAPS", text="Only Faces"
        ).type = "ONLY_FACE"
        # Bottom
        pie.operator("mesh.dissolve_edges", icon="EDGESEL", text="Edge Dissolve")
        # Top
        pie.operator("mesh.delete", icon="EDGESEL", text="Edge Delete").type = "EDGE"
        # Top Left
        pie.operator(
            "mesh.delete", icon="VERTEXSEL", text="Vertices Delete"
        ).type = "VERT"
        # Top Right
        pie.operator("mesh.delete", icon="FACESEL", text="Face Delete").type = "FACE"
        # Bottom Left
        pie.operator("mesh.dissolve_verts", icon="VERTEXSEL", text="Vert Dissolve")
        # Bottom Right
        pie.operator("mesh.dissolve_faces", icon="FACESEL", text="Face Dissolve")


class C_MT_EditModeMergePie(Menu):
    bl_label = "EditMode Selection Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="Merge At Cursor"
        ).type = "CURSOR"
        # Right
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="Merge Collapse"
        ).type = "COLLAPSE"
        # Bottom
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="Merge At Center"
        ).type = "CENTER"
        # Top
        pie.operator(
            "cop.toggle_auto_merge", icon="AUTOMERGE_ON", text="Toggle Auto Merge"
        )
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="AUTOMERGE_OFF", text="Vertex Slide Tool"
        ).name = "builtin.vertex_slide"
        # Top Right
        pie.operator(
            "mesh.remove_doubles", icon="AUTOMERGE_OFF", text="Merge By Disatance"
        )
        # Bottom Left
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="Merge At First"
        ).type = "FIRST"
        # Bottom Right
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="Merge At Last"
        ).type = "LAST"


class C_MT_EditModeModelPie(Menu):
    bl_label = "EditMode Model Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.loopcut_slide", icon="SPLIT_VERTICAL", text="Loop Cut")
        # Right
        pie.operator("mesh.bevel", icon="MOD_BEVEL", text="Bevel")
        # Bottom
        pie.operator_context = "INVOKE_REGION_WIN"
        pie.operator("screen.redo_last", icon="RECOVER_LAST", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu_pie", icon="EDGESEL", text="Edge Pie"
        ).name = "C_MT_EditModeEdgePie"
        # Top Left
        pie.operator(
            "wm.call_menu_pie", icon="VERTEXSEL", text="Vertex Pie"
        ).name = "C_MT_EditModeVertexPie"
        # Top Right
        pie.operator(
            "wm.call_menu_pie", icon="FACESEL", text="Face Pie"
        ).name = "C_MT_EditModeFacePie"
        # Bottom Left
        pie.operator(
            "mesh.knife_tool", icon="SCULPTMODE_HLT", text="Knife Tool"
        )
        # Bottom Right
        pie.operator(
            "wm.call_menu_pie", icon="AUTOMERGE_OFF", text="Merge Pie"
        ).name = "C_MT_EditModeMergePie"


class C_MT_EditModeVertexPie(Menu):
    bl_label = "EditMode Vertex Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.loopcut_slide", icon="VERTEXSEL", text="Loop Cut")
        # Right
        pie.operator(
            "mesh.bevel", icon="VERTEXSEL", text="Vertex Bevel"
        ).affect = "VERTICES"
        # Bottom
        pie.operator(
            "mesh.dupli_extrude_cursor", icon="VERTEXSEL", text="Extrude To Cursor"
        )
        # Top
        pie.operator(
            "wm.call_menu", icon="VERTEXSEL", text="Vertex Menu"
        ).name = "VIEW3D_MT_edit_mesh_vertices"
        # Top Left
        pie.operator("transform.vert_crease", icon="VERTEXSEL", text="Crease Vertices")
        # Top Right
        pie.operator(
            "mesh.extrude_vertices_move", icon="VERTEXSEL", text="Extrude Vertices"
        )
        # Bottom Left
        pie.operator("mesh.rip_move", icon="VERTEXSEL", text="Rip Vertices")
        # Bottom Right
        pie.operator("mesh.vert_connect_path", icon="VERTEXSEL", text="Join Vertices")


class C_MT_EditModeEdgePie(Menu):
    bl_label = "EditMode Edge Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.loopcut_slide", icon="EDGESEL", text="Loop Cut")
        # Right
        pie.operator("mesh.bevel", icon="EDGESEL", text="Edge Bevel").affect = "EDGES"
        # Bottom
        pie.operator("mesh.extrude_edges_move", icon="EDGESEL", text="Extrude Edges")
        # Top
        pie.operator(
            "wm.call_menu", icon="EDGESEL", text="Edges Menu"
        ).name = "VIEW3D_MT_edit_mesh_edges"
        # Top Left
        pie.operator("transform.edge_crease", icon="EDGESEL", text="Crease Edges")
        # Top Right
        pie.operator("mesh.bridge_edge_loops", icon="EDGESEL", text="Bridge EdgeLoops")
        # Bottom Left
        pie.operator("mesh.mark_sharp", icon="EDGESEL", text="Clear Sharp").clear = True
        # Bottom Right
        pie.operator("mesh.mark_sharp", icon="EDGESEL", text="Mark Sharp")


class C_MT_EditModeFacePie(Menu):
    bl_label = "EditMode Face Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.fill_grid", icon="FACESEL", text="Grid Fill")
        # Right
        pie.operator("mesh.inset", icon="FACESEL", text="Inset")
        # Bottom
        pie.operator("mesh.extrude_region_move", icon="FACESEL", text="Extrude")
        # Top
        pie.operator(
            "wm.call_menu", icon="FACESEL", text="Faces Menu"
        ).name = "VIEW3D_MT_edit_mesh_faces"
        # Top Left
        pie.operator("mesh.faces_shade_flat", icon="FACESEL", text="Shade Flat")
        # Top Right
        pie.operator("mesh.faces_shade_smooth", icon="FACESEL", text="Shade Smooth")
        # Bottom Left
        pie.operator(
            "mesh.extrude_faces_move", icon="FACESEL", text="Extrude Innvididual Faces"
        )
        # Bottom Right
        pie.operator(
            "mesh.extrude_region_shrink_fatten",
            icon="FACESEL",
            text="Extrude Along Normals",
        )


class C_MT_EditModeToolSelectPie(Menu):
    bl_label = "EditMode ToolSelect Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator(
            "wm.tool_set_by_id", icon="TRANSFORM_ORIGINS", text="Move Tool"
        ).name = "builtin.move"
        # Right
        pie.operator(
            "wm.tool_set_by_id", icon="CENTER_ONLY", text="Vertex Slide Tool"
        ).name = "builtin.vertex_slide"
        # Bottom
        pie.operator(
            "wm.tool_set_by_id", icon="ACTION_TWEAK", text="Tweak Tool"
        ).name = "builtin.select"
        # Top
        pie.operator(
            "wm.tool_set_by_id", icon="CURSOR", text="Cursor Tool"
        ).name = "builtin.cursor"
        # Top Left
        pie.operator(
            "wm.tool_set_by_id", icon="FULLSCREEN_ENTER", text="Scale Tool"
        ).name = "builtin.scale"
        # Top Right
        pie.operator(
            "wm.tool_set_by_id", icon="MOD_DASH", text="Lasso Select"
        ).name = "builtin.select_lasso"
        # Bottom Left
        pie.operator(
            "wm.tool_set_by_id", icon="GESTURE_ROTATE", text="Rotate Tool"
        ).name = "builtin.rotate"
        # Bottom Right
        pie.operator(
            "wm.tool_set_by_id", icon="MESH_CIRCLE", text="Circle Select"
        ).name = "builtin.select_circle"


classes = (
    C_MT_EditModeSelectionPie,
    C_MT_EditModeDeletionPie,
    C_MT_EditModeMergePie,
    C_MT_EditModeModelPie,
    C_MT_EditModeVertexPie,
    C_MT_EditModeEdgePie,
    C_MT_EditModeFacePie,
    C_MT_EditModeToolSelectPie,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
