import bpy
from bpy.types import Operator
from bpy.types import Menu
from . import CustomOperators
from . import AddonPreferences


class AllPie_MT_EditModeSelectionPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeSelectionPie"
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


class AllPie_MT_EditModeDeletionPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeDeletionPie"
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


class AllPie_MT_EditModeMergePie(Menu):
    bl_idname = "ALLPIE_MT_EditModeMergePie"
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


class AllPie_MT_EditModeModelPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeModelPie"
    bl_label = "EditMode Model Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # # Left
        pie.operator("mesh.separate", icon="MOD_EDGESPLIT", text="Separate Menu")
        # # Right
        pie.operator(
            "wm.call_menu_pie", icon="MODIFIER", text="Modifer Pie"
        ).name = "ALLPIE_MT_EditModeModifierPie"
        # Bottom
        pie.operator_context = "INVOKE_REGION_WIN"
        pie.operator("screen.redo_last", icon="RECOVER_LAST", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu_pie", icon="EDGESEL", text="Edge Pie"
        ).name = "ALLPIE_MT_EditModeEdgePie"
        # Top Left
        pie.operator(
            "wm.call_menu_pie", icon="VERTEXSEL", text="Vertex Pie"
        ).name = "ALLPIE_MT_EditModeVertexPie"
        # Top Right
        pie.operator(
            "wm.call_menu_pie", icon="FACESEL", text="Face Pie"
        ).name = "ALLPIE_MT_EditModeFacePie"
        # Bottom Left
        pie.operator(
            "wm.call_menu_pie", icon="UV", text="UV Unwrap Pie"
        ).name = "ALLPIE_MT_EditModeUVPie"
        # Bottom Right
        pie.operator(
            "wm.call_menu_pie", icon="AUTOMERGE_OFF", text="Merge Pie"
        ).name = "ALLPIE_MT_EditModeMergePie"


class AllPie_MT_EditModeVertexPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeVertexPie"
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
            "mesh.extrude_vertices_move", icon="VERTEXSEL", text="Extrude Vertices"
        )
        # Top
        pie.operator(
            "wm.call_menu", icon="VERTEXSEL", text="Vertex Menu"
        ).name = "VIEW3D_MT_edit_mesh_vertices"
        # Top Left
        pie.operator("transform.vert_crease", icon="VERTEXSEL", text="Crease Vertices")
        # Top Right
        pie.operator("mesh.knife_tool", icon="SCULPTMODE_HLT", text="Knife Tool")
        # Bottom Left
        pie.operator("mesh.rip_move", icon="VERTEXSEL", text="Rip Vertices")
        # Bottom Right
        pie.operator("mesh.vert_connect_path", icon="VERTEXSEL", text="Join Vertices")


class AllPie_MT_EditModeEdgePie(Menu):
    bl_idname = "ALLPIE_MT_EditModeEdgePie"
    bl_label = "EditMode Edge Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.loopcut_slide", icon="EDGESEL", text="Loop Cut")
        # Right
        pie.operator("mesh.bevel", icon="EDGE_BEVEL", text="Edge Bevel").affect = "EDGES"
        # Bottom
        pie.operator("mesh.extrude_edges_move", icon="EDGESEL", text="Extrude Edges")
        # Top
        pie.operator(
            "wm.call_menu", icon="EDGESEL", text="Edges Menu"
        ).name = "VIEW3D_MT_edit_mesh_edges"
        # Top Left
        pie.operator("transform.edge_crease", icon = "EDGE_CREASE",text="Crease Edges")
        # Top Right
        pie.operator("mesh.bridge_edge_loops", icon="EDGESEL", text="Bridge EdgeLoops")
        # Bottom Left
        pie.operator("mesh.mark_sharp", icon="EDGESEL", text="Clear Sharp").clear = True
        # Bottom Right
        pie.operator("mesh.mark_sharp", icon="EDGE_SHARP", text="Mark Sharp")


class AllPie_MT_EditModeFacePie(Menu):
    bl_idname = "ALLPIE_MT_EditModeFacePie"
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


class AllPie_MT_EditModeToolSelectPie(Menu):
    bl_label = "EditMode ToolSelect Pie"
    bl_idname = "ALLPIE_MT_EditModeToolSelectPie"

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


class AllPie_MT_EditModeModifierPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeModifierPie"
    bl_label = "EditMode Modifier Pie"

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
            "wm.search_single_menu", icon="VIEWZOOM", text="Add Modifier Search"
        ).menu_idname = "OBJECT_MT_modifier_add"
        # Top
        pie.operator(
            "wm.call_menu_pie", icon="EDGESEL", text="Edge Pie"
        ).name = "ALLPIE_MT_EditModeEdgePie"
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


class AllPie_MT_EditModeUVPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeUVPie"
    bl_label = "EditMode UV Unwrap Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()

        # # Left
        pie.operator(
            "uv.unwrap", icon="MOD_UVPROJECT", text="Unwrap Conformal"
        ).method = "ANGLE_BASED"
        # # Right
        pie.operator(
            "uv.unwrap", icon="MOD_UVPROJECT", text="Unwrap Minimum Stretch"
        ).method = "CONFORMAL"
        # Bottom
        pie.operator(
            "uv.unwrap", icon="UV", text="Unwrap Minimum Stretch"
        ).method = "MINIMUM_STRETCH"
        # Top
        pie.operator(
            "wm.call_menu", icon="UV", text="UV Menu"
        ).name = "VIEW3D_MT_uv_map"
        # Top Left
        pie.operator(
            "uv.follow_active_quads", icon="MOD_UVPROJECT", text="Follow Active Quads"
        )
        # Top Right
        pie.operator(
            "uv.smart_project", icon="MOD_UVPROJECT", text="Smart Project"
        )
        # Bottom Left
        pie.operator("mesh.mark_seam", icon="EDGESEL", text="Clear Seem").clear = True
        # Bottom Right
        pie.operator("mesh.mark_seam", icon="EDGE_SEAM", text="Mark Seem")


classes = (
    AllPie_MT_EditModeSelectionPie,
    AllPie_MT_EditModeDeletionPie,
    AllPie_MT_EditModeMergePie,
    AllPie_MT_EditModeModelPie,
    AllPie_MT_EditModeVertexPie,
    AllPie_MT_EditModeEdgePie,
    AllPie_MT_EditModeFacePie,
    AllPie_MT_EditModeToolSelectPie,
    AllPie_MT_EditModeModifierPie,
    AllPie_MT_EditModeUVPie,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
