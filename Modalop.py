import bpy
import gpu
import math
import blf

from gpu_extras.batch import batch_for_shader
from bpy.props import StringProperty
from . import CustomOperators


# ============================================================
# MENU HELPERS
# ============================================================

def OP(name, operator, **props):
    return ("OPERATOR", name, operator, props, False)


def INVOKE(name, operator, **props):
    return ("OPERATOR", name, operator, props, True)


# ============================================================
# MENUS
# ============================================================

EDGE_MENU = [
    # OP("Mark Sharp", "mesh.mark_sharp"),
    # OP("Mark Seam", "mesh.mark_seam"),
    # OP("Clear Sharp", "mesh.mark_sharp", clear=True),
    INVOKE("LoopCut", "mesh.loopcut_slide"),
    INVOKE("LoopCut", "mesh.loopcut_slide"),
    INVOKE("Extrude", "mesh.extrude_region_move"),
    INVOKE("Bevel", "mesh.bevel"),
]


EDGE_SHIFT_MENU = [
    OP("Mark Sharp", "mesh.mark_sharp"),
    OP("Clear Sharp", "mesh.mark_sharp", clear=True),
    OP("Clear Seam", "mesh.mark_seam", clear=True),
    OP("Mark Seam", "mesh.mark_seam"),
]


VERTEX_MENU = [
    OP("Merge", "mesh.merge"),
    INVOKE("Extrude", "mesh.extrude_region_move"),
    OP("Dissolve", "mesh.dissolve_verts"),
    INVOKE("Bevel", "mesh.bevel"),
]


FACE_MENU = [
    INVOKE("Extrude", "mesh.extrude_region_move"),
    INVOKE("Inset", "mesh.inset"),
    OP("Dissolve", "mesh.dissolve_faces"),
    INVOKE("Bevel", "mesh.bevel"),
]


ORIGIN_MENU = [
    OP("Geo To Origin", "cop.originset", GeoToOrigin=True),
    OP("Origin To Geo", "cop.originset", OriginToGeo=True),
    OP("Origin To Cursor", "cop.originset", OriginToCursor=True),
    OP("Origin To Selected", "cop.originset", OriginToSelected=True),
]


essentialspath = "brushes/essentials_brushes-mesh_sculpt.blend/Brush/"

Grab = essentialspath + "GRAB"
Clay = essentialspath + "CLAY STRIPS"
Drawsharp = essentialspath + "DRAW SHARP"
Draw = essentialspath + "DRAW"
Scrape = essentialspath + "SCRAPE/FILL"
Inflate = essentialspath + "INFLATE/DEFLATE"


BRUSH_MENU = [
    OP("DRAW SHARP", "brush.asset_activate", asset_library_type="ESSENTIALS", relative_asset_identifier=Drawsharp),
    OP("Inflate", "brush.asset_activate", asset_library_type="ESSENTIALS", relative_asset_identifier=Inflate),
    OP("DRAW", "brush.asset_activate", asset_library_type="ESSENTIALS", relative_asset_identifier=Draw),
    OP("GRAB", "brush.asset_activate", asset_library_type="ESSENTIALS", relative_asset_identifier=Grab),
    OP("SCRAPE", "brush.asset_activate", asset_library_type="ESSENTIALS", relative_asset_identifier=Scrape),
    OP("CLAY STRIPS", "brush.asset_activate", asset_library_type="ESSENTIALS", relative_asset_identifier=Clay),
]


# ============================================================
# MENU REGISTRY
# ============================================================

MENUS = {
    "EDGE": EDGE_MENU,
    "VERTEX": VERTEX_MENU,
    "FACE": FACE_MENU,
    "ORIGIN": ORIGIN_MENU,
    "BRUSH": BRUSH_MENU,
}


SHIFT_MENUS = {
    "EDGE": EDGE_SHIFT_MENU,
}


# ============================================================
# MODAL SETTINGS
# ============================================================

INNER_RADIUS = 75
OUTER_RADIUS = 175
TEXT_RADIUS = 120
DEADZONE = 22
SEGMENTS = 24

OUTLINE_COLOR = (0.35, 0.35, 0.35, 0.8)
OUTLINE_WIDTH = 1.0


# ============================================================
# GET ACTIVE MENU
# ============================================================

def get_menu(menu_id, shift=False):

    if shift and menu_id in SHIFT_MENUS:
        return SHIFT_MENUS[menu_id]

    return MENUS[menu_id]


# ============================================================
# EXECUTE OPERATOR
# ============================================================

def execute_slot(index, menu):

    item = menu[index]
    operator = item[2]
    props = item[3]
    invoke = item[4]

    module, operator = operator.split(".")
    op = getattr(getattr(bpy.ops, module), operator)

    if invoke:
        op("INVOKE_DEFAULT", **props)
    else:
        op(**props)


# ============================================================
# UPDATE ACTIVE
# ============================================================

def update_active(self, x, y):

    dx = x - self.cx
    dy = y - self.cy

    if math.hypot(dx, dy) < DEADZONE:
        self.active = -1
        return

    angle = math.atan2(dy, dx)

    if angle < 0:
        angle += math.tau

    self.active = int(angle / (math.tau / self.slices))


# ============================================================
# BUILD GEOMETRY
# ============================================================

def build_geometry(self):

    self.batches = []
    outline_verts = []

    for i in range(self.slices):

        start = i * math.tau / self.slices
        end = (i + 1) * math.tau / self.slices
        verts = []

        for j in range(SEGMENTS + 1):

            angle = start + (end - start) * j / SEGMENTS
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            verts.append((self.cx + cos_a * INNER_RADIUS, self.cy + sin_a * INNER_RADIUS))
            verts.append((self.cx + cos_a * OUTER_RADIUS, self.cy + sin_a * OUTER_RADIUS))

        indices = []

        for j in range(SEGMENTS):

            n = j * 2
            indices.append((n, n + 1, n + 3))
            indices.append((n, n + 3, n + 2))

        self.batches.append(batch_for_shader(self.shader, "TRIS", {"pos": verts}, indices=indices))
        outline_verts.extend((verts[0], verts[1]))

    self.outline_batch = batch_for_shader(self.outline_shader, "LINES", {"pos": outline_verts})


# ============================================================
# DRAW MENU
# ============================================================

def draw_menu(self):

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("ALPHA")

    # Draw slices

    self.shader.bind()

    for i, batch in enumerate(self.batches):

        self.shader.uniform_float(
            "color",
            (0.99, 0.99, 1.00, 0.40) if i == self.active else (0.08, 0.08, 0.08, 0.90)
        )

        batch.draw(self.shader)

    # Draw separator lines

    self.outline_shader.bind()
    self.outline_shader.uniform_float("color", OUTLINE_COLOR)

    gpu.state.line_width_set(OUTLINE_WIDTH)
    self.outline_batch.draw(self.outline_shader)
    gpu.state.line_width_set(1.0)

    # Draw labels

    font_id = 0
    blf.size(font_id, 15)

    for i, item in enumerate(self.menu):

        name = item[1]
        angle = i * math.tau / self.slices + math.tau / self.slices / 2

        x = self.cx + math.cos(angle) * TEXT_RADIUS
        y = self.cy + math.sin(angle) * TEXT_RADIUS

        width, height = blf.dimensions(font_id, name)

        if i == self.active:
            blf.color(font_id, 0.0, 0.0, 0.0, 1.0)
        else:
            blf.color(font_id, 0.8, 0.8, 0.8, 1.0)

        blf.position(font_id, x - width / 2, y - height / 2, 0)
        blf.draw(font_id, name)

    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set("LESS_EQUAL")


# ============================================================
# FINISH
# ============================================================

def finish(self, context):

    if self.handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(self.handle, "WINDOW")
        self.handle = None

    self.batches.clear()
    self.outline_batch = None

    context.area.tag_redraw()


# ============================================================
# RADIAL MENU
# ============================================================

class ModalRadialMenu(bpy.types.Operator):

    bl_idname = "view3d.modal_radial_menu"
    bl_label = "Radial Menu"

    menu_id: StringProperty()
    hotkey: StringProperty()

    def invoke(self, context, event):

        self.shift = False
        self.menu = get_menu(self.menu_id, False)
        self.slices = len(self.menu)

        self.cx = event.mouse_region_x
        self.cy = event.mouse_region_y
        self.active = -1

        self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self.outline_shader = gpu.shader.from_builtin("UNIFORM_COLOR")

        build_geometry(self)

        self.handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_menu, (self,), "WINDOW", "POST_PIXEL"
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    def modal(self, context, event):

        # Mouse movement

        if event.type == "MOUSEMOVE":

            old_active = self.active
            update_active(self, event.mouse_region_x, event.mouse_region_y)

            if self.active != old_active:
                context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Space toggle

        if event.type == "SPACE" and event.value == "PRESS":

            self.shift = not self.shift
            self.menu = get_menu(self.menu_id, self.shift)
            self.slices = len(self.menu)
            self.active = -1

            build_geometry(self)
            update_active(self, event.mouse_region_x, event.mouse_region_y)

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Release opening key

        if event.type == self.hotkey and event.value == "RELEASE":

            active = self.active

            if active >= 0:
                finish(self, context)
                execute_slot(active, self.menu)
            else:
                finish(self, context)

            return {"FINISHED"}

        # Ignore repeated opening-key presses while modal

        if event.type == self.hotkey:
            return {"RUNNING_MODAL"}

        # Cancel

        if event.type == "ESC":

            finish(self, context)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


# ============================================================
# KEYMAP
# ============================================================

addon_keymaps = []


# ============================================================
# REGISTER
# ============================================================

def register():

    bpy.utils.register_class(ModalRadialMenu)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:

        km = kc.keymaps.new(name="Mesh")

        # Edge menu - E

        kmi = km.keymap_items.new("view3d.modal_radial_menu", "E", "PRESS")
        kmi.properties.menu_id = "EDGE"
        kmi.properties.hotkey = "E"
        addon_keymaps.append((km, kmi))

        # Vertex menu - W

        kmi = km.keymap_items.new("view3d.modal_radial_menu", "W", "PRESS")
        kmi.properties.menu_id = "VERTEX"
        kmi.properties.hotkey = "W"
        addon_keymaps.append((km, kmi))

        # Face menu - F

        kmi = km.keymap_items.new("view3d.modal_radial_menu", "F", "PRESS")
        kmi.properties.menu_id = "FACE"
        kmi.properties.hotkey = "F"
        addon_keymaps.append((km, kmi))

        # Origin menu - D

        kmi = km.keymap_items.new("view3d.modal_radial_menu", "D", "PRESS")
        kmi.properties.menu_id = "ORIGIN"
        kmi.properties.hotkey = "D"
        addon_keymaps.append((km, kmi))

        km = kc.keymaps.new(name="Sculpt")

        # Brush menu - W

        kmi = km.keymap_items.new("view3d.modal_radial_menu", "W", "PRESS")
        kmi.properties.menu_id = "BRUSH"
        kmi.properties.hotkey = "W"
        addon_keymaps.append((km, kmi))


# ============================================================
# UNREGISTER
# ============================================================

def unregister():

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()

    bpy.utils.unregister_class(ModalRadialMenu)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    register()
