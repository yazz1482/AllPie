import bpy
import gpu
import math
import blf
from gpu_extras.batch import batch_for_shader
from bpy.props import StringProperty
from . import CustomOperators

# MENUS
EDGE_MENU = {
    0: ("Mark Sharp", "mesh.mark_sharp", {}),
    1: ("Mark Seam", "mesh.mark_seam", {}),
    2: ("Clear Sharp", "mesh.mark_sharp", {"clear": True}),
    3: ("LoopCut", "mesh.loopcut_slide", {}, True),
    4: ("Extrude", "mesh.extrude_region_move", {}, True),
    5: ("Bevel", "mesh.bevel", {}, True),
}

VERTEX_MENU = {
    0: ("Merge", "mesh.merge", {}),
    1: ("Extrude", "mesh.extrude_region_move", {}, True),
    2: ("Dissolve", "mesh.dissolve_verts", {}),
    3: ("Bevel", "mesh.bevel", {}, True),
}

FACE_MENU = {
    0: ("Extrude", "mesh.extrude_region_move", {}, True),
    1: ("Inset", "mesh.inset", {}, True),
    2: ("Dissolve", "mesh.dissolve_faces", {}, True),
    3: ("Bevel", "mesh.bevel", {}, True),
}

ORIGIN_MENU = {
    0: ("Geo To Origin", "cop.originset", {"GeoToOrigin": True}),
    1: ("Origin To Geo", "cop.originset", {"OriginToGeo": True}),
    2: ("Origin To Cursor", "cop.originset", {"OriginToCursor": True}),
    3: ("Origin To Selected", "cop.originset", {"OriginToSelected": True}),
}

essentialspath = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"
Grab = essentialspath + "GRAB"
Clay = essentialspath + "CLAY STRIPS"
Drawsharp = essentialspath + "DRAW SHARP"
Draw = essentialspath + "DRAW"
Scrape = essentialspath + "SCRAPE/FILL"
Inflate = essentialspath + "INFLATE/DEFLATE"

BRUSH_MENU = {
        0: ("DRAW SHARP", "brush.asset_activate", {"asset_library_type": "ESSENTIALS", "relative_asset_identifier": Drawsharp}),
        1: ("Inflate", "brush.asset_activate", {"asset_library_type": "ESSENTIALS", "relative_asset_identifier": Inflate}),
        2: ("DRAW", "brush.asset_activate", {"asset_library_type": "ESSENTIALS", "relative_asset_identifier": Draw}),
        3: ("GRAB", "brush.asset_activate", {"asset_library_type": "ESSENTIALS", "relative_asset_identifier": Grab}),
        4: ("SCRAPE", "brush.asset_activate", {"asset_library_type": "ESSENTIALS", "relative_asset_identifier": Scrape}),
        5: ("CLAY STRIPS", "brush.asset_activate", {"asset_library_type": "ESSENTIALS", "relative_asset_identifier": Clay}),
}

MENUS = {
    "EDGE": EDGE_MENU,
    "VERTEX": VERTEX_MENU,
    "FACE": FACE_MENU,
    "ORIGIN": ORIGIN_MENU,
    "BRUSH": BRUSH_MENU,
}

# MODAL SETTINGS
INNER_RADIUS = 75
OUTER_RADIUS = 175
TEXT_RADIUS = 120
DEADZONE = 22
SEGMENTS = 24
OUTLINE_COLOR = (0.35, 0.35, 0.35, 0.8)
ACTIVE_OUTLINE_COLOR = (1.0, 1.0, 1.0, 1.0)
OUTLINE_WIDTH = 1.0

# EXECUTE MENU ITEM
def execute_slot(index, menu):

    item = menu[index]
    name = item[0]
    op_path = item[1]
    props = item[2]

    invoke = item[3] if len(item) > 3 else False
    module, operator = op_path.split(".")
    op = getattr(getattr(bpy.ops, module), operator)

    if invoke:
        op("INVOKE_DEFAULT", **props)
    else:
        op(**props)


# RADIAL MENU
class ModalRadialMenu(bpy.types.Operator):
    bl_idname = "view3d.modal_radial_menu"
    bl_label = "Radial Menu"

    menu_id: StringProperty()
    hotkey: StringProperty()

    def invoke(self, context, event):

        # Get menu from registry
        self.menu = MENUS[self.menu_id]
        self.slices = len(self.menu)
        # Menu center
        self.cx = event.mouse_region_x
        self.cy = event.mouse_region_y
        self.active = -1
        # Shaders
        self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self.outline_shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        # Build slice geometry
        self.batches = []
        self.outline_batches = []

        for i in range(self.slices):

            start = i * math.tau / self.slices
            end = (i + 1) * math.tau / self.slices
            verts = []

            # Inner + outer point for every angle
            for j in range(SEGMENTS + 1):

                t = j / SEGMENTS
                angle = start + (end - start) * t
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)

                # Inner point
                verts.append(( self.cx + cos_a * INNER_RADIUS, self.cy + sin_a * INNER_RADIUS,))
                # Outer point
                verts.append(( self.cx + cos_a * OUTER_RADIUS, self.cy + sin_a * OUTER_RADIUS,))

            # Build triangles
            indices = []

            for j in range(SEGMENTS):

                n = j * 2

                indices.append((n, n + 1, n + 3))
                indices.append((n, n + 3, n + 2))

            batch = batch_for_shader( self.shader, "TRIS", {"pos": verts}, indices=indices,)

            self.batches.append(batch)

            # Slice separator
            outline_verts = [verts[0], verts[1]]
            outline_batch = batch_for_shader( self.outline_shader, "LINES", {"pos": outline_verts},)

            self.outline_batches.append(outline_batch)

        # Draw handler
        self.handle = bpy.types.SpaceView3D.draw_handler_add( self.draw_menu, (), "WINDOW", "POST_PIXEL",)

        # Start modal
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    # UPDATE ACTIVE SLICE
    def update_active(self, x, y):

        dx = x - self.cx
        dy = y - self.cy
        distance = math.hypot(dx, dy)
        # Dead zone
        if distance < DEADZONE:

            self.active = -1
            return

        # Mouse direction -> angle
        angle = math.atan2(dy, dx)

        if angle < 0:
            angle += math.tau

        # Angle -> slice index
        self.active = int( angle / (math.tau / self.slices))

    # MODAL
    def modal(self, context, event):

        # Mouse movement
        if event.type == "MOUSEMOVE":

            old_active = self.active
            self.update_active( event.mouse_region_x, event.mouse_region_y,)

            if self.active != old_active:
                context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Release opening key
        if event.type == self.hotkey and event.value == "RELEASE":

            active = self.active
            # Remove radial menu first
            self.finish(context)

            # Execute selected item
            if active >= 0:
                execute_slot(active, self.menu)

            return {"FINISHED"}

        # Cancel
        if event.type == "ESC":

            self.finish(context)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    # DRAW
    def draw_menu(self):

        shader = self.shader
        outline_shader = self.outline_shader

        # Draw over viewport
        gpu.state.depth_test_set("NONE")
        gpu.state.blend_set("ALPHA")

        # Draw slices
        for i, batch in enumerate(self.batches):

            shader.bind()

            if i == self.active:

                shader.uniform_float( "color", (0.99, 0.99, 1.00, 0.40),)

            else:

                shader.uniform_float( "color", (0.08, 0.08, 0.08, 0.90),)

            batch.draw(shader)

        # Draw separator lines
        outline_shader.bind()
        gpu.state.line_width_set(OUTLINE_WIDTH)

        for i, batch in enumerate(self.outline_batches):

            if i == self.active:

                outline_shader.uniform_float( "color", ACTIVE_OUTLINE_COLOR,)

            else:

                outline_shader.uniform_float( "color", OUTLINE_COLOR,)

            batch.draw(outline_shader)
        gpu.state.line_width_set(1.0)

        # Draw labels
        font_id = 0

        blf.size(font_id, 15)

        for i in range(self.slices):

            name = self.menu[i][0]

            # Middle of slice
            angle = ( i * math.tau / self.slices + math.tau / self.slices / 2)

            x = self.cx + math.cos(angle) * TEXT_RADIUS
            y = self.cy + math.sin(angle) * TEXT_RADIUS

            width, height = blf.dimensions(font_id, name)

            # Selected text
            if i == self.active:

                blf.color( font_id, 0.0, 0.0, 0.0, 1.0,)

            else:

                blf.color( font_id, 0.8, 0.8, 0.8, 1.0,)

            blf.position( font_id, x - width / 2, y - height / 2, 0,)
            blf.draw(font_id, name)

        # Restore GPU state
        gpu.state.blend_set("NONE")
        gpu.state.depth_test_set("LESS_EQUAL")

    # FINISH
    def finish(self, context):

        if self.handle is not None:

            bpy.types.SpaceView3D.draw_handler_remove( self.handle, "WINDOW",)
            self.handle = None

        self.batches.clear()
        self.outline_batches.clear()

        context.area.tag_redraw()


# KEYMAP
addon_keymaps = []


# REGISTER
def register():

    bpy.utils.register_class(ModalRadialMenu)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:

        km = kc.keymaps.new(name="Mesh")

        # Edge menu - E
        kmi = km.keymap_items.new( "view3d.modal_radial_menu", "E", "PRESS",)
        kmi.properties.menu_id = "EDGE"
        kmi.properties.hotkey = "E"
        addon_keymaps.append((km, kmi))

        # Vertex menu - W
        kmi = km.keymap_items.new( "view3d.modal_radial_menu", "W", "PRESS",)
        kmi.properties.menu_id = "VERTEX"
        kmi.properties.hotkey = "W"
        addon_keymaps.append((km, kmi))

        # Face menu - F
        kmi = km.keymap_items.new( "view3d.modal_radial_menu", "F", "PRESS",)
        kmi.properties.menu_id = "FACE"
        kmi.properties.hotkey = "F"
        addon_keymaps.append((km, kmi))

        # Face menu - D
        kmi = km.keymap_items.new( "view3d.modal_radial_menu", "D", "PRESS",)
        kmi.properties.menu_id = "ORIGIN"
        kmi.properties.hotkey = "D"
        addon_keymaps.append((km, kmi))

        km = kc.keymaps.new(name="Sculpt")
        # Face menu - D
        kmi = km.keymap_items.new( "view3d.modal_radial_menu", "W", "PRESS",)
        kmi.properties.menu_id = "BRUSH"
        kmi.properties.hotkey = "W"
        addon_keymaps.append((km, kmi))

# UNREGISTER
def unregister():

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()

    bpy.utils.unregister_class(ModalRadialMenu)

if __name__ == "__main__":
    register()
