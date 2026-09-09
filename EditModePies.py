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
        ).select_bigger = False


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
        pie.operator("mesh.dissolve_verts", icon="VERTEXSEL", text="Vertices Dissolve")
        # Bottom Right
        pie.operator("mesh.dissolve_faces", icon="FACESEL", text="Face Dissolve")


class AllPie_MT_EditModeMergePie(Menu):
    bl_idname = "ALLPIE_MT_EditModeMergePie"
    bl_label = "Separate/Merge Pie"

# bpy.ops.mesh.separate(type='SELECTED')
    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="At Cursor"
        ).type = "CURSOR"
        # Right
        pie.operator(
            "mesh.remove_doubles", icon="AUTOMERGE_OFF", text="Merge By Distance"
        )
        # Bottom
        op = pie.operator("mesh.merge", text="At Center", icon="FULLSCREEN_EXIT")
        op.type = "CENTER"
        # Top
        pie.operator("mesh.separate", icon="AUTOMERGE_ON", text="Separate Selection").type = "SELECTED"
        # Top Left
        pie.operator("mesh.separate", icon="AUTOMERGE_ON", text="Separate By Material").type = "MATERIAL"
        # Top Right
        pie.operator("mesh.separate", icon="AUTOMERGE_ON", text="Separate By Loose Parts").type = "LOOSE"
        try:
            # This will raise an error if the option isn't available.
            op.type = "CENTER"
            # Bottom Left
            pie.operator(
                "mesh.merge", text="At First", icon="TRACKING_REFINE_BACKWARDS"
            ).type = "FIRST"
            # Bottom Right
            pie.operator(
                "mesh.merge", text="At Last", icon="TRACKING_REFINE_FORWARDS"
            ).type = "LAST"
        except:
            op.type = "CENTER"


class AllPie_MT_EditModeVertexPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeVertexPie"
    bl_label = "EditMode Vertex Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.vert_connect_path", icon="VERTEXSEL", text="Join Vertices")
        # Right
        pie.operator(
            "mesh.bevel", icon="MOD_BEVEL", text="Vertex Bevel"
        ).affect = "VERTICES"

        # Bottom
        pie.operator("screen.redo_last", icon="FILE_REFRESH", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu", icon="VERTEXSEL", text="Vertex Menu"
        ).name = "VIEW3D_MT_edit_mesh_vertices"
        # Top Left
        pie.operator("mesh.rip_move", icon="VERTEXSEL", text="Rip Vertices")
        # Top Right
        pie.operator("mesh.knife_tool", icon="SCULPTMODE_HLT", text="Knife Tool")
        # Bottom Left
        pie.operator(
            "mesh.merge", icon="AUTOMERGE_OFF", text="Merge At Center"
        ).type = "CENTER"
        # Bottom Right
        pie.operator(
            "mesh.extrude_vertices_move", icon="VERTEXSEL", text="Extrude Vertices"
        )


class AllPie_MT_EditModeEdgePie(Menu):
    bl_idname = "ALLPIE_MT_EditModeEdgePie"
    bl_label = "EditMode Edge Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.edge_face_add", icon="SNAP_FACE", text="Fill")
        # Right
        pie.operator("mesh.bevel", icon="MOD_BEVEL", text="Edge Bevel").affect = "EDGES"
        # Bottom
        pie.operator("screen.redo_last", icon="FILE_REFRESH", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu_pie", icon="EDGESEL", text="Edge Mark Menu"
        ).name = "ALLPIE_MT_EditModeEdgeNestedPie"
        # Top Left
        pie.operator(
            "mesh.bridge_edge_loops", icon="MOD_OPACITY", text="Bridge EdgeLoops"
        )
        # Top Right
        pie.operator("mesh.loopcut_slide", icon="SPLIT_VERTICAL", text="Loop Cut")
        # Bottom Left
        pie.operator("mesh.fill_grid", icon="MESH_GRID", text="Grid Fill")
        # Bottom Right
        pie.operator("mesh.extrude_edges_move", icon="EDGESEL", text="Extrude Edges")


class AllPie_MT_EditModeEdgeNestedPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeEdgeNestedPie"
    bl_label = "EditMode Edge Nested Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator(
            "transform.edge_bevelweight", icon="EDGE_BEVEL", text="Edge Bevel Weight"
        )
        # Right
        pie.operator("transform.edge_crease", icon="EDGE_CREASE", text="Edge Crease")
        # Bottom
        pie.operator("screen.redo_last", icon="FILE_REFRESH", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu", icon="EDGESEL", text="Edges Menu"
        ).name = "VIEW3D_MT_edit_mesh_edges"
        # Top Left
        pie.operator("mesh.mark_sharp", icon="EDGESEL", text="Clear Sharp").clear = True
        # Top Right
        pie.operator("mesh.mark_sharp", icon="EDGE_SHARP", text="Mark Sharp")
        # Bottom Left
        pie.operator("mesh.mark_seam", icon="EDGESEL", text="Clear Seam").clear = True
        # Bottom Right
        pie.operator("mesh.mark_seam", icon="EDGE_SEAM", text="Mark Seam")


class AllPie_MT_EditModeFacePie(Menu):
    bl_idname = "ALLPIE_MT_EditModeFacePie"
    bl_label = "EditMode Face Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("mesh.flip_normals", icon="FACESEL", text="Flip Normals")
        # Right
        pie.operator(
            "mesh.extrude_region_shrink_fatten",
            icon="FACESEL",
            text="Extrude Along Normals",
        )
        # Bottom
        pie.operator("screen.redo_last", icon="FILE_REFRESH", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu", icon="FACESEL", text="Faces Menu"
        ).name = "VIEW3D_MT_edit_mesh_faces"
        # Top Left
        pie.operator("mesh.poke", icon="FACESEL", text="Poke")
        # Top Right
        pie.operator(
            "mesh.extrude_faces_move", icon="FACESEL", text="Extrude Individual"
        )
        # Bottom Left
        pie.operator("mesh.inset", icon="FACESEL", text="Inset")
        # Bottom Right
        pie.operator("mesh.extrude_region_move", icon="FACESEL", text="Extrude")


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
            "wm.tool_set_by_id", icon="SELECT_SET", text="Box Select"
        ).name = "builtin.select_box"
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



class AllPie_MT_EditModeUVPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeUVPie"
    bl_label = "EditMode UV Unwrap Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()

        # # Left
        pie.operator(
            "uv.unwrap", icon="MOD_UVPROJECT", text="Unwrap Conformal"
        ).method = "CONFORMAL"
        # # Right
        pie.operator(
            "uv.unwrap", icon="UV", text="Unwrap Minimum Stretch"
        ).method = "MINIMUM_STRETCH"
        # Bottom
        pie.operator("screen.redo_last", icon="RECOVER_LAST", text="Redo Menu")
        # Top
        pie.operator(
            "wm.call_menu", icon="UV", text="UV Menu"
        ).name = "VIEW3D_MT_uv_map"
        # Top Left
        pie.operator(
            "uv.follow_active_quads", icon="MOD_UVPROJECT", text="Follow Active Quads"
        )
        # Top Right
        pie.operator("uv.smart_project", icon="MOD_UVPROJECT", text="Smart Project")
        # Bottom Left
        pie.operator("mesh.mark_seam", icon="EDGESEL", text="Clear Seam").clear = True
        # Bottom Right
        pie.operator("mesh.mark_seam", icon="EDGE_SEAM", text="Mark Seam")

class AllPie_MT_EditModeOriginPie(Menu):
    bl_idname = "ALLPIE_MT_EditModeOriginPie"
    bl_label = "EditMode Origin/Snap Pie"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # Left
        pie.operator("cop.originset", icon="ORIENTATION_GLOBAL", text="Origin To Cursor").OriginToCursor = True
        # Right
        pie.operator("view3d.snap_cursor_to_selected", icon="ORIENTATION_CURSOR", text="Cursor To Selected")
        # # Bottom
        pie.operator("cop.originset", icon="OBJECT_ORIGIN", text="Origin To Selected").OriginToSelected = True
        # # Top
        pie.operator(
            "wm.call_panel", icon="SNAP_INCREMENT", text="Snapping Menu"
        ).name = "VIEW3D_PT_snapping"
        # # Top Left
        pie.operator("cop.originset", icon="TRANSFORM_ORIGINS", text="Origin To Geometry").OriginToGeo = True
        # # Top Right
        pie.operator("view3d.snap_cursor_to_center", icon="PIVOT_CURSOR", text="Cursor To Origin")
        # # Bottom Left
        pie.operator("cop.originset", icon="ORIENTATION_NORMAL", text="Geometry To Origin").GeoToOrigin = True
        # # Bottom Right
        pie.operator("view3d.snap_selected_to_cursor", icon="ORIENTATION_NORMAL", text="Selected To Cursor").use_offset=True


classes = (
    AllPie_MT_EditModeSelectionPie,
    AllPie_MT_EditModeDeletionPie,
    AllPie_MT_EditModeMergePie,
    AllPie_MT_EditModeVertexPie,
    AllPie_MT_EditModeEdgePie,
    AllPie_MT_EditModeEdgeNestedPie,
    AllPie_MT_EditModeFacePie,
    AllPie_MT_EditModeToolSelectPie,
    AllPie_MT_EditModeUVPie,
    AllPie_MT_EditModeOriginPie
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
