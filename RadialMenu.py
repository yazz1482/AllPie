import bpy
import gpu
import math
import blf

from gpu_extras.batch import batch_for_shader
from bpy.props import StringProperty
from . import Preferences
from .core import runtime as ConfigRuntime
from .core.operator_validation import validate_operator_preset

# Compatibility views are compiled once from the JSON-backed runtime cache.
# The modal menu continues to consume the same legacy menu-item structure.
MENUS = ConfigRuntime.MENUS
SPACE_MENUS = ConfigRuntime.SPACE_MENUS
MENU_NAMES = ConfigRuntime.MENU_NAMES


# MODAL SETTINGS
SLICES = 8
OUTER_RADIUS = 135
MARK_RADIUS = 120
MARK_POINT_RADIUS = 4

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


def _report_execution_issue(message, report=None, level="WARNING"):
    """Send an operator failure to both Blender's UI reports and the console."""
    text = str(message)
    print(f"[AllPie {level.title()}] {text}")

    # Operator.report is the native Blender notification path. Since this is
    # called from ModalRadialMenu.modal(), Blender can display the report in
    # the UI when the radial operator finishes, while the console message
    # remains available for debugging.
    if report is not None:
        try:
            report({level}, text)
        except Exception as report_error:
            print(
                "[AllPie Warning] Could not display the UI report: "
                f"{type(report_error).__name__}: {report_error}"
            )


def execute_slot(index, menu, report=None):
    if menu is None:
        return

    item = next((item for item in menu if item["slot"] == index), None)
    if item is None:
        return

    operator_id = item.get("operator", "")
    props = item.get("props", {})
    invoke = item.get("invoke", False)
    action_label = item.get("label", operator_id or "Unnamed Action")

    try:
        check = validate_operator_preset(operator_id, props, check_poll=True)
        if check.errors:
            details = "; ".join(
                f"{issue.path}: {issue.message}" for issue in check.errors[:4]
            )
            if len(check.errors) > 4:
                details += f"; and {len(check.errors) - 4} more validation error(s)"
            _report_execution_issue(
                f"Action '{action_label}' could not run: {details}",
                report,
                level="ERROR",
            )
            return

        if not check.registered or check.operator is None:
            details = "; ".join(issue.message for issue in check.warnings[:2]) or "operator is unavailable"
            _report_execution_issue(
                f"Could not execute '{operator_id}' ({action_label}): {details}",
                report,
            )
            return

        if check.poll_ok is False:
            _report_execution_issue(
                f"Could not execute '{operator_id}' ({action_label}): operator is not "
                "available in the current mode, selection or editor",
                report,
            )
            return

        for issue in check.warnings:
            print(f"[AllPie Warning] {issue}")

        call_properties = check.execution_properties
        if invoke:
            result = check.operator("INVOKE_DEFAULT", True, **call_properties)
        else:
            result = check.operator(**call_properties)

        if isinstance(result, set) and "CANCELLED" in result:
            _report_execution_issue(
                f"Operator '{operator_id}' ({action_label}) cancelled without completing",
                report,
            )
        elif isinstance(result, set) and not result.intersection({
            "FINISHED",
            "RUNNING_MODAL",
            "INTERFACE",
            "PASS_THROUGH",
        }):
            # Some UI operators (notably wm.call_panel in Blender 5.2) return
            # INTERFACE when they successfully open their own interface. This
            # is a valid success result, not an unexpected status. Keep the
            # normal operator statuses and PASS_THROUGH valid as well.
            _report_execution_issue(
                f"Operator '{operator_id}' ({action_label}) returned an unexpected status: {sorted(result)}",
                report,
            )
    except Exception as error:
        # Imported configurations may reference optional third-party operators
        # or context-dependent identifiers that no longer exist. Surface the
        # failure in Blender as well as the console without interrupting the
        # radial menu's normal modal cleanup path.
        _report_execution_issue(
            f"Could not execute '{operator_id}' ({action_label}): "
            f"{type(error).__name__}: {error}",
            report,
        )


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

    if self.gesture_endpoint_batch is not None:
        self.gesture_endpoint_batch.draw(self.separator_shader)


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
    self.gesture_endpoint_batch = None
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

    segments = 16
    verts = [(x, y), (self.cx, self.cy)]
    indices = []

    for i in range(segments):
        angle = math.tau * i / segments
        verts.append((
            x + math.cos(angle) * MARK_POINT_RADIUS,
            y + math.sin(angle) * MARK_POINT_RADIUS,
        ))

    center_offset = 2 + segments

    for i in range(segments):
        next_i = (i + 1) % segments
        indices.append((0, 2 + i, 2 + next_i))
        indices.append((1, center_offset + i, center_offset + next_i))

    for i in range(segments):
        angle = math.tau * i / segments
        verts.append((
            self.cx + math.cos(angle) * MARK_POINT_RADIUS,
            self.cy + math.sin(angle) * MARK_POINT_RADIUS,
        ))

    self.gesture_endpoint_batch = batch_for_shader(
        self.separator_shader,
        "TRIS",
        {"pos": verts},
        indices=indices,
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
    self.gesture_endpoint_batch = None
    context.area.tag_redraw()


def _remove_all_radial_keymaps(kc):
    """Remove every AllPie modal keymap item, including stale reload copies.

    Tracking only ``addon_keymaps`` is insufficient after Blender reloads an
    addon module: the old keymap items can survive while the Python list is
    recreated. Scan the addon keyconfig itself so changed shortcuts cannot be
    shadowed by stale duplicate entries.
    """
    for km in tuple(kc.keymaps):
        for kmi in tuple(km.keymap_items):
            if kmi.idname != "view3d.modal_radial_menu":
                continue
            try:
                km.keymap_items.remove(kmi)
            except (ReferenceError, RuntimeError):
                pass
    addon_keymaps.clear()


def rebuild_keymaps():
    """Recreate AllPie keymaps after a menu shortcut or context is edited."""
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    _remove_all_radial_keymaps(kc)

    keymap_names = dict.fromkeys(
        definition[1] for definition in Preferences.get_keybind_definitions()
    )
    for keymap_name in keymap_names:
        register_keymaps(kc, keymap_name)


def register_keymaps(kc, name):
    """Register shortcuts directly from the JSON-backed runtime config."""
    for (
        pref_id,
        keymap_name,
        default_key,
        default_value,
        menu_id,
        modifiers,
        default_enabled,
    ) in Preferences.get_keybind_definitions():
        if keymap_name != name or default_key == "NONE":
            continue

        km = kc.keymaps.get(keymap_name)
        if km is None:
            km = kc.keymaps.new(name=keymap_name)

        kmi = km.keymap_items.new(
            "view3d.modal_radial_menu",
            default_key,
            default_value,
            shift=bool(modifiers.get("shift", False)),
            ctrl=bool(modifiers.get("ctrl", False)),
            alt=bool(modifiers.get("alt", False)),
            oskey=bool(modifiers.get("oskey", False)),
            hyper=bool(modifiers.get("hyper", False)),
        )
        kmi.active = bool(default_enabled)
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
        self.gesture_endpoint_batch = None
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
                execute_slot(active, self.menu, report=self.report)
            else:
                finish(self, context)
            return {"FINISHED"}

        if event.type == "ESC":
            finish(self, context)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


addon_keymaps = []


def register():
    ConfigRuntime.initialize()
    bpy.utils.register_class(ModalRadialMenu)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        _remove_all_radial_keymaps(kc)
        keymap_names = dict.fromkeys(
            definition[1] for definition in Preferences.get_keybind_definitions()
        )
        for keymap_name in keymap_names:
            register_keymaps(kc, keymap_name)


def unregister():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is not None:
        _remove_all_radial_keymaps(kc)
    else:
        addon_keymaps.clear()
    bpy.utils.unregister_class(ModalRadialMenu)


if __name__ == "__main__":
    register()
