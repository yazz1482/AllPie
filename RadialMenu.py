import bpy
import gpu
import math
import time
import blf

from gpu_extras.batch import batch_for_shader
from bpy.props import StringProperty
from . import Preferences
from .core import runtime as ConfigRuntime
from .core.operator_validation import validate_operator_preset
from .core.schema import keymap_registration_spec

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


_DRAW_SPACE_TYPES = {
    "VIEW_3D": "SpaceView3D",
    "IMAGE_EDITOR": "SpaceImageEditor",
    "NODE_EDITOR": "SpaceNodeEditor",
}


def _is_uv_editor_context(context):
    """Return whether an Image Editor area is currently showing UV editing.

    Blender uses the same IMAGE_EDITOR space for both the Image Editor and UV
    Editor. ``SpaceImageEditor.show_uvedit`` is the runtime distinction: it is
    true when UV editing is active, even though ``ui_mode`` can still be VIEW.
    """
    area = getattr(context, "area", None)
    if getattr(area, "type", None) != "IMAGE_EDITOR":
        return False

    space = getattr(context, "space_data", None)
    if space is None:
        spaces = getattr(area, "spaces", None)
        space = getattr(spaces, "active", None) if spaces is not None else None

    try:
        return bool(getattr(space, "show_uvedit", False))
    except (AttributeError, ReferenceError, RuntimeError):
        return False


def _resolve_context_menu_id(menu_id, context):
    """Resolve editor-specific mode menus and suppress Image modes in UV editing.

    Blender uses one IMAGE_EDITOR space class for both the Image Editor and UV
    Editor. Their keymaps can therefore overlap. The Image Editor's View/Paint/
    Mask menu is valid only when UV editing is not active.
    """
    area = getattr(context, "area", None)
    if getattr(area, "type", None) != "IMAGE_EDITOR":
        return None if menu_id == "IMAGE.MODE" else menu_id

    is_uv_editor = _is_uv_editor_context(context)
    if menu_id == "IMAGE.MODE":
        return None if is_uv_editor else menu_id

    source_menu = ConfigRuntime.REGISTRY.get_menu(menu_id)
    if source_menu is None or str(source_menu.keymap).casefold() != "common":
        return menu_id

    if menu_id == "OBJECT.MODE":
        if is_uv_editor:
            return None
        image_mode = ConfigRuntime.REGISTRY.get_menu("IMAGE.MODE")
        return "IMAGE.MODE" if image_mode is not None and image_mode.enabled else None

    return menu_id


def _draw_space_class(area_type):
    """Resolve the Blender Space subclass used to draw in an editor area."""
    class_name = _DRAW_SPACE_TYPES.get(str(area_type or ""))
    space_class = getattr(bpy.types, class_name, None) if class_name else None
    if space_class is None:
        raise RuntimeError(f"AllPie does not support drawing in the {area_type!r} editor")
    return space_class


def _pointer_id(value):
    """Return a stable RNA pointer for a window, area or region when available."""
    if value is None:
        return None
    try:
        return value.as_pointer()
    except (AttributeError, ReferenceError, RuntimeError):
        return None


def _is_origin_region(self, context):
    """Ensure the draw callback only renders in the viewport that opened the menu."""
    return (
        _pointer_id(getattr(context, "window", None)) == self.origin_window_ptr
        and _pointer_id(getattr(context, "area", None)) == self.origin_area_ptr
        and _pointer_id(getattr(context, "region", None)) == self.origin_region_ptr
    )


def _tag_origin_redraw(self):
    """Redraw only the invoking viewport, tolerating areas closed during a modal session."""
    for region in (getattr(self, "origin_region", None),):
        if region is not None:
            try:
                region.tag_redraw()
            except (ReferenceError, RuntimeError):
                pass


def _get_origin_mouse_position(self, event):
    """Convert window-relative mouse coordinates into the invoking region's space."""
    region = getattr(self, "origin_region", None)
    try:
        region_x = region.x
        region_y = region.y
    except (AttributeError, ReferenceError, RuntimeError):
        region_x = self.origin_region_x
        region_y = self.origin_region_y

    return event.mouse_x - region_x, event.mouse_y - region_y


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
    """Switch menu data only when the requested layout actually exists."""
    requested_space = bool(space)
    if requested_space:
        target_menu = SPACE_MENUS.get(self.menu_id)
        if target_menu is None:
            return False
    else:
        target_menu = MENUS.get(self.menu_id)

    self.space = requested_space
    self.menu = target_menu or []
    self.slices = SLICES
    self.active = -1
    self.menu_name = MENU_NAMES.get(self.menu_id, "")

    build_geometry(self)
    update_active(self, x, y)
    return True


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


def _is_expected_noop_cancelled(operator_id, properties, context):
    """Return True when a cancelled operator has already reached its target state.

    Blender's mesh.select_mode reports CANCELLED when the requested selection
    mode is already active and the operator therefore has nothing to change.
    This is a successful no-op from the user's perspective, not an execution
    failure worth reporting from the radial menu.
    """
    if operator_id != "mesh.select_mode" or context is None:
        return False

    # Explicit disable/toggle actions have different semantics. Only suppress
    # the common set/enable case used by AllPie's built-in selection presets.
    action = properties.get("action")
    if action not in (None, "ENABLE"):
        return False

    mode_index = {"VERT": 0, "EDGE": 1, "FACE": 2}.get(properties.get("type"))
    if mode_index is None:
        return False

    tool_settings = getattr(context, "tool_settings", None)
    if tool_settings is None:
        scene = getattr(context, "scene", None)
        tool_settings = getattr(scene, "tool_settings", None)
    if tool_settings is None:
        return False

    try:
        selection_modes = tool_settings.mesh_select_mode
        return bool(selection_modes[mode_index])
    except (AttributeError, IndexError, ReferenceError, TypeError):
        return False


def _execute_slot_in_context(index, menu, report=None, context=None):
    if menu is None:
        return

    item = next((item for item in menu if item["slot"] == index), None)
    if item is None:
        return

    operator_id = item.get("operator", "")
    # Empty radial positions are now represented explicitly so the full pie
    # remains visible even when nothing has been assigned. Selecting one in
    # normal mode is a harmless no-op.
    if not operator_id:
        return
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
            if not _is_expected_noop_cancelled(operator_id, props, context):
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


def execute_slot(
    index,
    menu,
    report=None,
    context=None,
    origin_window=None,
    origin_area=None,
    origin_region=None,
):
    """Execute an action in the editor that originally opened the radial menu.

    Blender's modal context may follow the pointer as it crosses editor areas.
    Keep both operator.poll() and the operator call inside an override built
    from the invoking window, area and region so editor-specific actions see
    the context in which their radial menu was opened.
    """
    if (
        context is not None
        and origin_window is not None
        and origin_area is not None
        and origin_region is not None
    ):
        try:
            with context.temp_override(
                window=origin_window,
                area=origin_area,
                region=origin_region,
            ):
                _execute_slot_in_context(index, menu, report=report, context=context)
            return
        except Exception as error:
            _report_execution_issue(
                "Could not restore the original editor context for this action: "
                f"{type(error).__name__}: {error}",
                report,
                level="ERROR",
            )
            return

    _execute_slot_in_context(index, menu, report=report, context=context)


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

    self.box_outline_batch = (
        batch_for_shader(self.separator_shader, "LINES", {"pos": outline_verts})
        if outline_verts else None
    )


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


def _is_assignment_mode(operator):
    """Identify the dedicated assignment operator by its registered type.

    Separate Blender operator IDs keep last-used operator properties from
    leaking assignment state into ordinary radial-menu keymap invocations.
    """
    return bool(getattr(type(operator), "_allpie_assignment_mode", False))


def draw_assignment_info(self, font_color):
    """Show the captured action and active slot group in assignment mode."""
    if not _is_assignment_mode(self):
        return

    action_name = (
        getattr(self, "assignment_operator_label", "")
        or getattr(self, "assignment_operator_id", "")
        or "Captured Operator"
    )
    action_text = f"Assign: {action_name}"
    group_text = "Spaced Slots" if self.space else "Main Slots"
    help_text = "Space: switch  ·  Click: assign  ·  Esc: cancel"

    blf.color(FONT_ID, *font_color)
    blf.size(FONT_ID, max(11, FONT_SIZE - 2))
    action_width, _ = blf.dimensions(FONT_ID, action_text)
    group_width, _ = blf.dimensions(FONT_ID, group_text)
    blf.position(FONT_ID, self.cx - action_width / 2, self.cy - 8, 0)
    blf.draw(FONT_ID, action_text)
    blf.position(FONT_ID, self.cx - group_width / 2, self.cy - 25, 0)
    blf.draw(FONT_ID, group_text)

    blf.size(FONT_ID, max(9, FONT_SIZE - 5))
    help_width, _ = blf.dimensions(FONT_ID, help_text)
    blf.position(FONT_ID, self.cx - help_width / 2, self.cy - 41, 0)
    blf.draw(FONT_ID, help_text)


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
    if self.box_outline_batch is not None:
        self.separator_shader.bind()
        self.separator_shader.uniform_float("color", outline_color)
        gpu.state.line_width_set(OUTLINE_WIDTH)
        self.box_outline_batch.draw(self.separator_shader)
        gpu.state.line_width_set(1.0)

    font_color = self.font_colors[self.space]
    draw_labels(self)
    draw_menu_name(self, font_color)
    draw_assignment_info(self, font_color)

    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set("LESS_EQUAL")


def draw(self):
    if getattr(self, "finished", True):
        return

    context = bpy.context
    if not _is_origin_region(self, context):
        return

    if self.menu_visible:
        draw_menu(self)
    else:
        draw_gesture(self)


def _pointer_inside_origin_region(self, x, y):
    """Return whether a region-relative pointer sample lies in the draw area."""
    region = getattr(self, "origin_region", None)
    try:
        width = int(region.width)
        height = int(region.height)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return False
    return 0 <= x <= width and 0 <= y <= height


def update_pointer(self, event):
    """Apply one pointer sample consistently to selection and gesture state."""
    x, y = _get_origin_mouse_position(self, event)

    if (
        _is_assignment_mode(self)
        and not _pointer_inside_origin_region(self, x, y)
    ):
        # The assignment pie may be drawn in a different editor from the
        # button that launched it. Do not let a pointer outside that editor's
        # Window region select one of the eight directions.
        self.active = -1
        self.gesture_batch = None
        self.gesture_endpoint_batch = None
        _tag_origin_redraw(self)
        return

    update_active(self, x, y)
    update_gesture(self, x, y)
    _tag_origin_redraw(self)


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


def _remove_hold_timer(self):
    timer = getattr(self, "hold_timer", None)
    self.hold_timer = None
    self.hold_timer_active = False

    if timer is None:
        return

    window_manager = getattr(self, "window_manager", None)
    if window_manager is None:
        return

    try:
        window_manager.event_timer_remove(timer)
    except Exception as error:
        print(f"[AllPie Warning] Could not remove radial hold timer: {error}")


def finish(self, context=None):
    """Release every modal resource exactly once, even on cancellation paths."""
    if getattr(self, "finished", True):
        return

    # Mark finished before releasing resources so a redraw cannot use partially
    # cleared state and repeated cleanup calls remain harmless.
    self.finished = True
    self.menu_visible = False

    _remove_hold_timer(self)

    handle = getattr(self, "handle", None)
    self.handle = None
    if handle is not None:
        try:
            draw_space_type = getattr(self, "draw_space_type", None)
            if draw_space_type is None:
                raise RuntimeError("The original radial draw space is unavailable")
            draw_space_type.draw_handler_remove(handle, "WINDOW")
        except Exception as error:
            print(f"[AllPie Warning] Could not remove radial draw handler: {error}")

    self.box_batches = []
    self.box_outline_batch = None
    self.gesture_batch = None
    self.gesture_endpoint_batch = None
    _tag_origin_redraw(self)


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

        space_type, region_type = keymap_registration_spec(keymap_name)
        km = kc.keymaps.new(
            name=keymap_name,
            space_type=space_type,
            region_type=region_type,
        )

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


def _schedule_captured_slot_assignment(self, slot_number, spaced):
    """Continue into AllPie's existing replacement/configuration workflow.

    The radial modal must finish before invoking another popup operator. Keep
    the original viewport context and use Blender's timer queue, matching the
    deferred-popup pattern already used by the operator editor.
    """
    window = getattr(self, "origin_window", None)
    area = getattr(self, "origin_area", None)
    region = getattr(self, "origin_region", None)
    properties = {
        "menu_id": self.menu_id,
        "slot_number": int(slot_number),
        "spaced": bool(spaced),
        "operator_id": self.assignment_operator_id,
        "operator_label": self.assignment_operator_label,
        "context_name": self.assignment_context_name,
        "button_properties_json": self.assignment_button_properties_json or "{}",
        "button_unsupported_properties_json": (
            self.assignment_button_unsupported_properties_json or "[]"
        ),
    }

    def invoke_assignment():
        try:
            operator = bpy.ops.allpie.assign_captured_operator_slot
            if window is not None and area is not None and region is not None:
                with bpy.context.temp_override(window=window, area=area, region=region):
                    result = operator("INVOKE_DEFAULT", **properties)
            else:
                result = operator("INVOKE_DEFAULT", **properties)
            if isinstance(result, set) and "CANCELLED" in result:
                print("[AllPie] The captured operator slot assignment was cancelled")
        except Exception as error:
            print(
                "[AllPie] Could not continue the radial assignment workflow: "
                f"{type(error).__name__}: {error}"
            )
        return None

    try:
        bpy.app.timers.register(invoke_assignment, first_interval=0.0)
    except Exception as error:
        print(
            "[AllPie] Could not schedule the captured operator assignment: "
            f"{type(error).__name__}: {error}"
        )


# RADIAL MENU
class _RadialMenuOperatorMixin:
    """Shared modal implementation for normal and assignment radial menus."""

    def invoke(self, context, event):
        # A shared Image Paint keymap can also be active in the Image Editor.
        # Resolve Common Mode only for normal invocation; assignment mode must
        # respect the exact menu the user selected in the context-menu workflow.
        if not _is_assignment_mode(self):
            resolved_menu_id = _resolve_context_menu_id(self.menu_id, context)
            if resolved_menu_id is None:
                return {"CANCELLED"}
            self.menu_id = resolved_menu_id

        # Initialize cleanup-safe state before creating any Blender resources.
        self.finished = False
        self.menu_visible = False
        self.handle = None
        self.draw_space_type = None
        self.hold_timer = None
        self.hold_timer_active = False
        self.box_batches = []
        self.box_outline_batch = None
        self.gesture_batch = None
        self.gesture_endpoint_batch = None

        self.window_manager = context.window_manager
        self.origin_window = context.window
        self.origin_area = context.area
        self.origin_region = context.region
        self.origin_window_ptr = _pointer_id(context.window)
        self.origin_area_ptr = _pointer_id(context.area)
        self.origin_region_ptr = _pointer_id(context.region)
        self.origin_region_x = context.region.x
        self.origin_region_y = context.region.y

        if _is_assignment_mode(self):
            # Assignment mode opens as a visible editor immediately and is
            # centered in the viewport, even when the source button lived in a
            # sidebar region. The deferred invoke may not have a live input event.
            self.cx = context.region.width * 0.5
            self.cy = context.region.height * 0.5
        else:
            if event is None:
                self.report({"ERROR"}, "AllPie needs the opening input event to start a normal radial menu")
                return {"CANCELLED"}
            self.cx = event.mouse_region_x
            self.cy = event.mouse_region_y
        self.active = -1
        self.opening_key = getattr(event, "type", "")

        try:
            if context.area is None or context.region is None or context.region.type != "WINDOW":
                raise RuntimeError("AllPie must be invoked from an editor Window region")
            self.draw_space_type = _draw_space_class(context.area.type)

            prefs = Preferences.get_preferences()
            self.hold_time = prefs.hold_time if prefs is not None else HOLD_TIME
            self.deadzone = prefs.deadzone if prefs is not None else DEADZONE
            cache_colors(self, prefs)

            self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
            self.separator_shader = gpu.shader.from_builtin("UNIFORM_COLOR")
            set_menu(self, False, self.cx, self.cy)

            if not _is_assignment_mode(self):
                self.hold_timer = self.window_manager.event_timer_add(
                    self.hold_time,
                    window=self.origin_window,
                )
                self.hold_timer_active = True
                self.hold_deadline = time.perf_counter() + self.hold_time
            else:
                self.menu_visible = True
                _remove_hold_timer(self)

            self.handle = self.draw_space_type.draw_handler_add(
                draw,
                (self,),
                "WINDOW",
                "POST_PIXEL",
            )
            self.window_manager.modal_handler_add(self)
            _tag_origin_redraw(self)
            return {"RUNNING_MODAL"}

        except Exception as error:
            finish(self, context)
            self.report({"ERROR"}, f"Could not start radial menu: {type(error).__name__}: {error}")
            return {"CANCELLED"}

    def modal(self, context, event):
        if self.finished:
            return {"CANCELLED"}

        if event.type == "WINDOW_DEACTIVATE":
            finish(self, context)
            return {"CANCELLED"}

        if event.type == "TIMER" and self.hold_timer_active:
            # Blender can deliver TIMER events from other systems. Only reveal
            # the menu once the configured hold duration has actually elapsed.
            if time.perf_counter() >= self.hold_deadline:
                self.menu_visible = True
                _remove_hold_timer(self)
                _tag_origin_redraw(self)
            return {"RUNNING_MODAL"}

        if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
            update_pointer(self, event)
            return {"RUNNING_MODAL"}

        if event.type == "SPACE" and event.value == "PRESS" and not getattr(event, "is_repeat", False):
            x, y = _get_origin_mouse_position(self, event)
            if set_menu(self, not self.space, x, y):
                self.menu_visible = True
                _remove_hold_timer(self)
                _tag_origin_redraw(self)
            return {"RUNNING_MODAL"}

        if _is_assignment_mode(self):
            # Assignment mode never executes an existing action. A left click
            # selects the highlighted destination; Escape/right-click cancels.
            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                x, y = _get_origin_mouse_position(self, event)
                if _pointer_inside_origin_region(self, x, y):
                    update_active(self, x, y)
                else:
                    self.active = -1
                if self.active >= 0:
                    slot_number = self.active + 1
                    spaced = bool(self.space)
                    finish(self, context)
                    _schedule_captured_slot_assignment(self, slot_number, spaced)
                    return {"FINISHED"}
                return {"RUNNING_MODAL"}

            if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
                finish(self, context)
                return {"CANCELLED"}

            return {"RUNNING_MODAL"}

        if event.type == self.opening_key and event.value == "RELEASE":
            active = self.active
            menu = self.menu
            finish(self, context)
            if active >= 0:
                execute_slot(
                    active,
                    menu,
                    report=self.report,
                    context=context,
                    origin_window=self.origin_window,
                    origin_area=self.origin_area,
                    origin_region=self.origin_region,
                )
            return {"FINISHED"}

        if event.type == "ESC" and event.value == "PRESS":
            finish(self, context)
            return {"CANCELLED"}

        # All other events are intentionally captured while the radial menu is
        # active. Do not return PASS_THROUGH: viewport navigation is disabled.
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        finish(self, context)


class ModalRadialMenu(_RadialMenuOperatorMixin, bpy.types.Operator):
    """Normal radial menu operator used by AllPie's shortcut keymaps."""

    bl_idname = "view3d.modal_radial_menu"
    bl_label = "Radial Menu"
    _allpie_assignment_mode = False

    menu_id: StringProperty()
    hotkey: StringProperty()
    pref_id: StringProperty()


class ModalRadialAssignment(_RadialMenuOperatorMixin, bpy.types.Operator):
    """Dedicated assignment operator that cannot execute menu actions."""

    bl_idname = "view3d.modal_radial_assignment"
    bl_label = "Assign Operator to Radial Slot"
    _allpie_assignment_mode = True

    menu_id: StringProperty()
    assignment_operator_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    assignment_operator_label: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    assignment_context_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    assignment_button_properties_json: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    assignment_button_unsupported_properties_json: StringProperty(options={"HIDDEN", "SKIP_SAVE"})


addon_keymaps = []


def register():
    ConfigRuntime.initialize()
    bpy.utils.register_class(ModalRadialMenu)
    bpy.utils.register_class(ModalRadialAssignment)

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
    bpy.utils.unregister_class(ModalRadialAssignment)
    bpy.utils.unregister_class(ModalRadialMenu)


if __name__ == "__main__":
    register()
