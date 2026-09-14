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


# HOTKEYS
MESH_HOTKEYS = EditModePies.MESH_HOTKEYS
SCULPT_HOTKEYS = SculptModePies.SCULPT_HOTKEYS
OBJECT_HOTKEYS = ObjectModePies.OBJECT_HOTKEYS


# MODAL SETTINGS
SLICES = 6

INNER_RADIUS = 75
OUTER_RADIUS = 175
TEXT_RADIUS = 120
DEADZONE = 22
SEGMENTS = 24

HOLD_TIME = 0.125

SLICE_COLOR = (0.08, 0.08, 0.08, 0.90)
ACTIVE_SLICE_COLOR = (0.99, 0.99, 1.00, 0.40)

SEPARATOR_COLORS = (
    (0.55, 0.55, 0.55, 0.9),
    (0.45, 0.35, 0.75, 0.9),
)

OUTLINE_WIDTH = 3.5


# SET ACTIVE MENU
def set_menu(self, space, x, y):

    self.space = space

    if space and self.menu_id in SPACE_MENUS:
        self.menu = SPACE_MENUS[self.menu_id]
    else:
        self.menu = MENUS.get(self.menu_id)

    self.slices = SLICES
    self.active = -1

    build_geometry(self)
    update_active(self, x, y)


# EXECUTE OPERATOR
def execute_slot(index, menu):

    item = next(
        (item for item in menu if item["slot"] == index),
        None
    )

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
        print(f"[AllPie] Warning: {error}")

# UPDATE ACTIVE
def update_active(self, x, y):

    dx = x - self.cx
    dy = y - self.cy

    if math.hypot(dx, dy) < DEADZONE:
        self.active = -1
        return

    angle = math.atan2(dy, dx)

    angle = (math.pi / 2 - angle) % math.tau
    angle = (angle + math.pi / self.slices) % math.tau

    self.active = int( angle / (math.tau / self.slices))


# BUILD GEOMETRY
def build_geometry(self):

    self.batches = []
    separator_verts = []
    self.labels = []

    slice_angle = math.tau / self.slices
    start_angle = math.radians(120)

    for i in range(self.slices):

        start = start_angle - i * slice_angle
        end = start - slice_angle

        verts = []

        for j in range(SEGMENTS + 1):

            angle = ( start + (end - start) * j / SEGMENTS)

            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            verts.append(( self.cx + cos_a * INNER_RADIUS, self.cy + sin_a * INNER_RADIUS))

            verts.append(( self.cx + cos_a * OUTER_RADIUS, self.cy + sin_a * OUTER_RADIUS))

        indices = []

        for j in range(SEGMENTS):

            n = j * 2

            indices.append(( n, n + 1, n + 3))

            indices.append(( n, n + 3, n + 2))

        self.batches.append( batch_for_shader( self.shader, "TRIS", {"pos": verts}, indices=indices))

        separator_verts.extend(( verts[0], verts[1]))

    self.separator_batch = batch_for_shader( self.separator_shader, "LINES", {"pos": separator_verts})

    # Cache labels
    font_id = 0

    blf.size( font_id, 15)

    line_height = blf.dimensions( font_id, "Ag")[1]

    for item in self.menu:

        i = item["slot"]
        name = item["label"]

        angle = ( math.pi / 2 - i * math.tau / self.slices)

        x = ( self.cx + math.cos(angle) * TEXT_RADIUS)
        y = ( self.cy + math.sin(angle) * TEXT_RADIUS)

        lines = name.split("\n")
        total_height = line_height * len(lines)

        text_lines = []

        for line_index, line in enumerate(lines):

            width, _ = blf.dimensions( font_id, line)

            line_y = ( y + total_height / 2 - (line_index + 1) * line_height)

            text_lines.append(( line, x - width / 2, line_y))

        self.labels.append(( i, text_lines))


# DRAW MENU
def draw_menu(self):

    if getattr(self, "finished", True):
        return

    if not self.menu_visible:
        return

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("ALPHA")

    # Draw slices
    self.shader.bind()

    for i, batch in enumerate(self.batches):

        self.shader.uniform_float(
            "color",
            ACTIVE_SLICE_COLOR
            if i == self.active
            else SLICE_COLOR
        )

        batch.draw( self.shader)

    # Draw separators
    separator_color = SEPARATOR_COLORS[self.space]

    self.separator_shader.bind()

    self.separator_shader.uniform_float( "color", separator_color)

    gpu.state.line_width_set( OUTLINE_WIDTH)

    self.separator_batch.draw( self.separator_shader)

    gpu.state.line_width_set( 1.0)

    # Draw labels
    font_id = 0

    for i, text_lines in self.labels:

        if i == self.active:

            blf.color( font_id, 0.0, 0.0, 0.0, 1.0)

        else:

            blf.color( font_id, 0.8, 0.8, 0.8, 1.0)

        for line, x, y in text_lines:

            blf.position( font_id, x, y, 0)
            blf.draw( font_id, line)

    gpu.state.blend_set( "NONE")
    gpu.state.depth_test_set( "LESS_EQUAL")


# FINISH
def finish(self, context):

    self.finished = True
    self.menu_visible = False

    if self.hold_timer_active:

        context.window_manager.event_timer_remove( self.hold_timer)

        self.hold_timer = None
        self.hold_timer_active = False

    if self.handle is not None:

        bpy.types.SpaceView3D.draw_handler_remove( self.handle, "WINDOW")

        self.handle = None

    self.batches.clear()
    self.separator_batch = None

    context.area.tag_redraw()



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

        self.hold_timer = context.window_manager.event_timer_add( HOLD_TIME, window=context.window)

        self.hold_timer_active = True

        self.shader = gpu.shader.from_builtin( "UNIFORM_COLOR")

        self.separator_shader = gpu.shader.from_builtin( "UNIFORM_COLOR")

        set_menu( self, False, event.mouse_region_x, event.mouse_region_y)

        self.handle = bpy.types.SpaceView3D.draw_handler_add( draw_menu, (self,), "WINDOW", "POST_PIXEL")

        context.window_manager.modal_handler_add( self)

        context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    def modal(self, context, event):

        # Hold timer
        if (
            event.type == "TIMER"
            and self.hold_timer_active
        ):

            self.menu_visible = True

            context.window_manager.event_timer_remove( self.hold_timer)

            self.hold_timer = None
            self.hold_timer_active = False

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Mouse movement
        if event.type == "MOUSEMOVE":

            old_active = self.active

            update_active( self, event.mouse_region_x, event.mouse_region_y)

            if self.active != old_active:
                context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Space toggle
        if ( event.type == "SPACE" and event.value == "PRESS"):

            set_menu( self, not self.space, event.mouse_region_x, event.mouse_region_y)

            self.menu_visible = True

            if self.hold_timer_active:

                context.window_manager.event_timer_remove( self.hold_timer)

                self.hold_timer = None
                self.hold_timer_active = False

            context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # Opening key
        if event.type == self.hotkey:

            if event.value == "RELEASE":

                active = self.active

                if active >= 0:

                    finish( self, context)

                    execute_slot( active, self.menu)

                else:

                    finish( self, context)

                return {"FINISHED"}

            return {"RUNNING_MODAL"}

        # Cancel
        if event.type == "ESC":

            finish( self, context)

            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


addon_keymaps = []

# FIND LIVE KEYMAP ITEM
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


# UPDATE SINGLE KEYMAP
def update_keymap(pref_id):

    prefs = Preferences.get_preferences()

    if prefs is None:
        return

    keybind = Preferences.get_keybind_store(
        prefs,
        pref_id
    )

    if keybind is None:
        return

    km, kmi = find_keymap_item(
        pref_id
    )

    if kmi is None:
        return

    kmi.active = keybind.enabled


# REGISTER KEYMAPS
def register_keymaps(kc, name):

    prefs = Preferences.get_preferences()

    if prefs is None:
        return

    Preferences.initialize_keybinds(
        prefs
    )

    for (
        pref_id,
        keymap_name,
        default_key,
        default_value,
        menu_id,
        modifiers,
    ) in Preferences.get_keybind_definitions():

        if keymap_name != name:
            continue

        keybind = Preferences.get_keybind_store( prefs, pref_id)

        if keybind is None:
            continue

        km = kc.keymaps.get( keymap_name)

        if km is None:

            km = kc.keymaps.new( name=keymap_name)

        kmi = km.keymap_items.new(
            "view3d.modal_radial_menu",
            keybind.key,
            keybind.value,
            shift=keybind.shift,
            ctrl=keybind.ctrl,
            alt=keybind.alt,
        )

        kmi.active = keybind.enabled

        kmi.properties.menu_id = menu_id
        kmi.properties.hotkey = kmi.type
        kmi.properties.pref_id = pref_id

        addon_keymaps.append(( km, kmi))


def register():

    bpy.utils.register_class( ModalRadialMenu)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:

        register_keymaps( kc, "Mesh")

        register_keymaps( kc, "Sculpt")

        register_keymaps( kc, "Object Mode")


def unregister():

    Preferences.sync_all_keymaps_to_preferences()

    for km, kmi in addon_keymaps:

        try:
            km.keymap_items.remove(
                kmi
            )

        except ReferenceError:
            pass

    addon_keymaps.clear()

    bpy.utils.unregister_class( ModalRadialMenu)


if __name__ == "__main__":
    register()
