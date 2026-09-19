import bpy
import gpu
import math
import blf

from gpu_extras.batch import batch_for_shader
from bpy.props import StringProperty
from . import CustomOperators
from . import EditModePies
from . import SculptModePies
from . import ObjectModePies
from . import Preferences


# MENU REGISTRY
MENUS = {
    **EditModePies.MENUS,
    **SculptModePies.MENUS,
    **ObjectModePies.MENUS,
}

SPACE_MENUS = {
    **EditModePies.SPACE_MENUS,
    **SculptModePies.SPACE_MENUS,
    **ObjectModePies.SPACE_MENUS,
}

MENU_NAMES = {
    **EditModePies.MENU_NAMES,
    **ObjectModePies.MENU_NAMES,
    **SculptModePies.MENU_NAMES,
}


# MODAL SETTINGS
SLICES = 8
OUTER_RADIUS = 135
MARK_RADIUS = 120

MIN_BOX_WIDTH = 110
MIN_BOX_HEIGHT = 35

BOX_PADDING_X = 10
BOX_PADDING_Y = 10

DEADZONE = 25
HOLD_TIME = 0.150

FONT_ID = 0
FONT_SIZE = 15
OUTLINE_WIDTH = 1.75
MENU_NAME_OFFSET = 12

# COLORS
SLOT_COLOR = (0.08, 0.08, 0.08, 0.90)
ACTIVE_SLOT_COLOR = (0.50, 0.50, 0.50, 0.20)
OUTLINE_COLORS = (
    (0.55, 0.55, 0.55, 1.0),
    (0.45, 0.35, 0.75, 1.0),
)
ACTIVE_FONT_COLOR = (1.0, 1.0, 1.0, 1.0)
FONT_COLOR = (0.45, 0.35, 0.75, 1.0)
MARK_COLOR = (0.50, 0.50, 0.50, 0.20)


def cache_colors(self, prefs):
    if prefs is not None:
        self.slot_colors = (tuple(prefs.slot_color), tuple(prefs.spaced_slot_color))
        self.active_slot_colors = (tuple(prefs.active_slot_color), tuple(prefs.spaced_active_slot_color))
        self.font_colors = (tuple(prefs.font_color), tuple(prefs.spaced_font_color))
        self.active_font_colors = (tuple(prefs.active_font_color), tuple(prefs.spaced_active_font_color))
        self.outline_colors = (tuple(prefs.outline_color), tuple(prefs.spaced_outline_color))
        self.mark_color = tuple(prefs.mark_color)
    else:
        self.slot_colors = (SLOT_COLOR, SLOT_COLOR)
        self.active_slot_colors = (ACTIVE_SLOT_COLOR, ACTIVE_SLOT_COLOR)
        self.font_colors = (FONT_COLOR, FONT_COLOR)
        self.active_font_colors = (ACTIVE_FONT_COLOR, ACTIVE_FONT_COLOR)
        self.outline_colors = OUTLINE_COLORS
        self.mark_color = MARK_COLOR


def get_box_rect(self, angle, width, height):
    dir_x = math.cos(angle)
    dir_y = math.sin(angle)

    factor_x = 0.0 if dir_x > 0.01 else -1.0 if dir_x < -0.01 else -0.5
    factor_y = 0.0 if dir_y > 0.99 else -1.0 if dir_y < -0.99 else -0.5

    left = self.cx + dir_x * OUTER_RADIUS + factor_x * width
    bottom = self.cy + dir_y * OUTER_RADIUS + factor_y * height
    right = left + width
    top = bottom + height

    return left, bottom, right, top


def set_menu(self, space, x, y):
    self.space = space

    if space and self.menu_id in SPACE_MENUS:
        self.menu = SPACE_MENUS[self.menu_id]
    else:
        self.menu = MENUS.get(self.menu_id)

    self.slices = SLICES
    self.active = -1
    self.menu_name = MENU_NAMES.get(self.menu_id, "")

    build_geometry(self)
    update_active(self, x, y)


def execute_slot(index, menu):
    if menu is None:
        return

    item = next((item for item in menu if item["slot"] == index), None)
    if item is None:
        return

    operator = item["operator"]
    props = item.get("props", {})
    invoke = item.get("invoke", False)
    module, operator = operator.split(".")
    op = getattr(getattr(bpy.ops, module), operator)

    try:
        if invoke:
            op("INVOKE_DEFAULT", True, **props)
        else:
            op(**props)
    except RuntimeError as error:
        print(f"[AllPie Warning] {error}")


def update_active(self, x, y):
    dx = x - self.cx
    dy = y - self.cy

    if math.hypot(dx, dy) < self.deadzone:
        self.active = -1
        return

    angle = math.atan2(dy, dx)
    angle = (math.pi / 2 - angle) % math.tau
    angle = (angle + math.pi / self.slices) % math.tau
    self.active = int(angle / (math.tau / self.slices))


def build_geometry(self):
    self.box_batches = []
    outline_verts = []
    self.labels = []

    slice_angle = math.tau / self.slices
    start_angle = math.pi / 2 + slice_angle / 2

    blf.size(FONT_ID, FONT_SIZE)
    line_height = blf.dimensions(FONT_ID, "Ag")[1]

    for item in self.menu:
        i = item["slot"]
        name = item["label"]
        angle = start_angle - (i + 0.5) * slice_angle
        lines = name.split("\n")
        line_widths = [blf.dimensions(FONT_ID, line)[0] for line in lines]
        text_width = max(line_widths, default=0)
        text_height = len(lines) * line_height
        box_width = max(MIN_BOX_WIDTH, text_width + BOX_PADDING_X * 2)
        box_height = max(MIN_BOX_HEIGHT, text_height + BOX_PADDING_Y * 2)

        left, bottom, right, top = get_box_rect(self, angle, box_width, box_height)
        x = (left + right) * 0.5
        y = (bottom + top) * 0.5

        verts = (
            (left, bottom),
            (right, bottom),
            (right, top),
            (left, top),
        )

        batch = batch_for_shader(self.shader, "TRIS", {"pos": verts}, indices=((0, 1, 2), (0, 2, 3)))
        self.box_batches.append((i, batch))

        outline_verts.extend((
            verts[0], verts[1],
            verts[1], verts[2],
            verts[2], verts[3],
            verts[3], verts[0],
        ))

        total_height = len(lines) * line_height
        text_lines = []
        for line_index, line in enumerate(lines):
            width, _ = blf.dimensions(FONT_ID, line)
            line_y = y + total_height / 2 - (line_index + 1) * line_height
            text_lines.append((line, x - width / 2, line_y))

        self.labels.append((i, text_lines))

    self.box_outline_batch = batch_for_shader(self.separator_shader, "LINES", {"pos": outline_verts})


def draw_mark(self):
    if self.gesture_batch is None:
        return

    self.separator_shader.bind()
    self.separator_shader.uniform_float("color", self.mark_color)
    gpu.state.line_width_set(OUTLINE_WIDTH)
    self.gesture_batch.draw(self.separator_shader)
    gpu.state.line_width_set(1.0)


def draw_boxes(self):
    self.shader.bind()
    slot_color = self.slot_colors[self.space]
    active_slot_color = self.active_slot_colors[self.space]

    for slot, batch in self.box_batches:
        self.shader.uniform_float("color", active_slot_color if slot == self.active else slot_color)
        batch.draw(self.shader)


def draw_labels(self):
    blf.size(FONT_ID, FONT_SIZE)
    font_color = self.font_colors[self.space]
    active_font_color = self.active_font_colors[self.space]

    for slot, text_lines in self.labels:
        blf.color(FONT_ID, *(active_font_color if slot == self.active else font_color))
        for line, x, y in text_lines:
            blf.position(FONT_ID, x, y, 0)
            blf.draw(FONT_ID, line)


def draw_menu_name(self, font_color):
    blf.size(FONT_ID, FONT_SIZE)
    blf.color(FONT_ID, *font_color)
    menu_name_width, _ = blf.dimensions(FONT_ID, self.menu_name)
    blf.position(FONT_ID, self.cx - menu_name_width / 2, self.cy + MENU_NAME_OFFSET, 0)
    blf.draw(FONT_ID, self.menu_name)


def draw_gesture(self):
    if getattr(self, "finished", True) or self.gesture_batch is None:
        return

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("ALPHA")
    draw_mark(self)
    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set("LESS_EQUAL")


def draw_menu(self):
    if getattr(self, "finished", True) or not self.menu_visible:
        return

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("ALPHA")

    draw_mark(self)
    draw_boxes(self)

    outline_color = self.outline_colors[self.space]
    self.separator_shader.bind()
    self.separator_shader.uniform_float("color", outline_color)
    gpu.state.line_width_set(OUTLINE_WIDTH)
    self.box_outline_batch.draw(self.separator_shader)
    gpu.state.line_width_set(1.0)

    font_color = self.font_colors[self.space]
    draw_labels(self)
    draw_menu_name(self, font_color)

    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set("LESS_EQUAL")


def draw(self):
    if self.menu_visible:
        draw_menu(self)
    else:
        draw_gesture(self)


def update_gesture(self, x, y):
    self.gesture_batch = None
    dx = x - self.cx
    dy = y - self.cy
    distance = math.hypot(dx, dy)

    if distance < self.deadzone:
        return

    if distance > MARK_RADIUS:
        scale = MARK_RADIUS / distance
        x = self.cx + dx * scale
        y = self.cy + dy * scale

    self.gesture_batch = batch_for_shader(
        self.separator_shader,
        "LINES",
        {"pos": [(self.cx, self.cy), (x, y)]},
    )


def finish(self, context):
    self.finished = True
    self.menu_visible = False

    if self.hold_timer_active:
        context.window_manager.event_timer_remove(self.hold_timer)
        self.hold_timer = None
        self.hold_timer_active = False

    if self.handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(self.handle, "WINDOW")
        self.handle = None

    self.box_batches.clear()
    self.box_outline_batch = None
    self.gesture_batch = None
    context.area.tag_redraw()


def find_keymap_item(pref_id):
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return None, None

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if kmi.idname != "view3d.modal_radial_menu":
                continue
            if getattr(kmi.properties, "pref_id", None) == pref_id:
                return km, kmi

    return None, None


def update_keymap(pref_id):
    prefs = Preferences.get_preferences()
    if prefs is None:
        return

    keybind = Preferences.get_keybind_store(prefs, pref_id)
    if keybind is None:
        return

    km, kmi = find_keymap_item(pref_id)
    if kmi is None:
        return

    kmi.active = keybind.enabled


def register_keymaps(kc, name):
    prefs = Preferences.get_preferences()
    if prefs is None:
        return

    Preferences.initialize_keybinds(prefs)

    for pref_id, keymap_name, default_key, default_value, menu_id, modifiers in Preferences.get_keybind_definitions():
        if keymap_name != name:
            continue

        keybind = Preferences.get_keybind_store(prefs, pref_id)
        if keybind is None:
            continue

        km = kc.keymaps.get(keymap_name)
        if km is None:
            km = kc.keymaps.new(name=keymap_name)

        kmi = km.keymap_items.new(
            "view3d.modal_radial_menu",
            keybind.key,
            "PRESS",
            shift=keybind.shift,
            ctrl=keybind.ctrl,
            alt=keybind.alt,
        )
        kmi.active = keybind.enabled
        kmi.properties.menu_id = menu_id
        kmi.properties.hotkey = kmi.type
        kmi.properties.pref_id = pref_id
        addon_keymaps.append((km, kmi))


# RADIAL MENU
class ModalRadialMenu(bpy.types.Operator):
    bl_idname = "view3d.modal_radial_menu"
    bl_label = "Radial Menu"

    menu_id: StringProperty()
    hotkey: StringProperty()
    pref_id: StringProperty()

    def invoke(self, context, event):
        self.cx = event.mouse_region_x
        self.cy = event.mouse_region_y
        self.active = -1
        self.menu_visible = False
        self.finished = False
        self.gesture_batch = None
        self.opening_key = event.type

        prefs = Preferences.get_preferences()
        self.hold_time = prefs.hold_time if prefs is not None else HOLD_TIME
        self.deadzone = prefs.deadzone if prefs is not None else DEADZONE
        cache_colors(self, prefs)

        self.hold_timer = context.window_manager.event_timer_add(self.hold_time, window=context.window)
        self.hold_timer_active = True
        self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self.separator_shader = gpu.shader.from_builtin("UNIFORM_COLOR")

        set_menu(self, False, event.mouse_region_x, event.mouse_region_y)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(draw, (self,), "WINDOW", "POST_PIXEL")
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "TIMER" and self.hold_timer_active:
            self.menu_visible = True
            context.window_manager.event_timer_remove(self.hold_timer)
            self.hold_timer = None
            self.hold_timer_active = False
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":
            update_active(self, event.mouse_region_x, event.mouse_region_y)
            update_gesture(self, event.mouse_region_x, event.mouse_region_y)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "SPACE" and event.value == "PRESS":
            set_menu(self, not self.space, event.mouse_region_x, event.mouse_region_y)
            self.menu_visible = True

            if self.hold_timer_active:
                context.window_manager.event_timer_remove(self.hold_timer)
                self.hold_timer = None
                self.hold_timer_active = False

            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == self.opening_key and event.value == "RELEASE":
            active = self.active
            if active >= 0:
                finish(self, context)
                execute_slot(active, self.menu)
            else:
                finish(self, context)
            return {"FINISHED"}

        if event.type == "ESC":
            finish(self, context)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


addon_keymaps = []


def register():
    bpy.utils.register_class(ModalRadialMenu)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        register_keymaps(kc, "Mesh")
        register_keymaps(kc, "Sculpt")
        register_keymaps(kc, "Object Mode")


def unregister():
    Preferences.sync_all_keymaps_to_preferences()

    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except ReferenceError:
            pass

    addon_keymaps.clear()
    bpy.utils.unregister_class(ModalRadialMenu)


if __name__ == "__main__":
    register()
