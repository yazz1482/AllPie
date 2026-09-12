import bpy
import gpu
import math
import blf

from gpu_extras.batch import batch_for_shader

# MENU

MENU = {
    0: ("Mark Sharp",   "mesh.mark_sharp",              {}),
    2: ("Clear Sharp",  "mesh.mark_sharp",              {"clear": True}),
    1: ("Mark Seam",    "mesh.mark_seam",               {}),
    #4: ("Clear Seam",   "mesh.mark_seam",               {"clear": True}),
    #4: ("Crease",  "transform.edge_crease",        {}, True),
    #5: ("Bevel Weight", "transform.edge_bevelweight",   {}, True),
    4: ("Extrude",       "mesh.extrude_region_move",    {}, True),
    5: ("Bevel",       "mesh.bevel",    {}, True),
    3: ("LoopCut",       "mesh.loopcut_slide",    {}, True),
}
# SETTINGS
SLICES = len(MENU)
INNER_RADIUS = 75
OUTER_RADIUS = 165
TEXT_RADIUS = 120
DEADZONE = 18
SEGMENTS = 24

# EXECUTE MENU ITEM
def execute_slot(index):

    item = MENU[index]
    name = item[0]
    op_path = item[1]
    props = item[2]

    # Optional 4th value.
    # If omitted, normal execution is used.
    invoke = item[3] if len(item) > 3 else False
    module, operator = op_path.split(".")
    op = getattr( getattr(bpy.ops, module), operator,)

    if invoke:
        op("INVOKE_DEFAULT", **props)
    else:
        op(**props)

# RADIAL MENU
class ModalRadialMenu(bpy.types.Operator):
    bl_idname = "view3d.modal_radial_menu"
    bl_label = "Radial Menu"

    # INVOKE
    def invoke(self, context, event):

        # Menu center
        self.cx = event.mouse_region_x
        self.cy = event.mouse_region_y
        self.active = -1

        # Shader
        self.shader = gpu.shader.from_builtin(
            "UNIFORM_COLOR"
        )
        # Build slice geometry
        self.batches = []

        for i in range(SLICES):

            start = i * math.tau / SLICES
            end = (i + 1) * math.tau / SLICES
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

                indices.append(( n, n + 1, n + 3,))
                indices.append(( n, n + 3, n + 2,))

            batch = batch_for_shader( self.shader, "TRIS", {"pos": verts}, indices=indices,)

            self.batches.append(batch)

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
        self.active = int( angle / (math.tau / SLICES))

    # MODAL
    def modal(self, context, event):

        # Mouse movement
        if event.type == "MOUSEMOVE":

            old_active = self.active

            self.update_active( event.mouse_region_x, event.mouse_region_y,)

            # Only redraw when selection changes
            if self.active != old_active:

                context.area.tag_redraw()

            return {"RUNNING_MODAL"}

        # F release
        if event.type == "F" and event.value == "RELEASE":

            active = self.active

            # Remove radial menu first
            self.finish(context)

            # Execute selected item
            if active >= 0:

                execute_slot(active)

            return {"FINISHED"}

        # Cancel
        if event.type == "ESC":

            self.finish(context)

            return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    # DRAW
    def draw_menu(self):

        shader = self.shader

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

        # Draw labels
        font_id = 0

        blf.size( font_id, 15,)

        for i in range(SLICES):

            name = MENU[i][0]

            # Middle of slice
            angle = ( i * math.tau / SLICES + math.tau / SLICES / 2)

            x = ( self.cx + math.cos(angle) * TEXT_RADIUS)

            y = ( self.cy + math.sin(angle) * TEXT_RADIUS)

            width, height = blf.dimensions( font_id, name,)

            # Selected text
            if i == self.active:

                blf.color( font_id, 0.0, 0.0, 0.0, 1.0,)

            else:

                blf.color( font_id, 0.8, 0.8, 0.8, 1.0,)

            blf.position( font_id, x - width / 2, y - height / 2, 0,)

            blf.draw( font_id, name,)

        # Restore GPU state
        gpu.state.blend_set("NONE")
        gpu.state.depth_test_set("LESS_EQUAL")

    # FINISH
    def finish(self, context):

        if self.handle is not None:

            bpy.types.SpaceView3D.draw_handler_remove( self.handle, "WINDOW",)

            self.handle = None

        self.batches.clear()

        context.area.tag_redraw()


# KEYMAP
addon_keymaps = []

# REGISTER
def register():

    bpy.utils.register_class( ModalRadialMenu)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:

        # Mesh = Mesh Edit Mode keymap
        km = kc.keymaps.new( name="Mesh",)
        kmi = km.keymap_items.new( "view3d.modal_radial_menu", "F", "PRESS",)
        addon_keymaps.append( (km, kmi))

# UNREGISTER
def unregister():

    for km, kmi in addon_keymaps:

        km.keymap_items.remove(kmi)

    addon_keymaps.clear()

    bpy.utils.unregister_class( ModalRadialMenu)

# RUN
if __name__ == "__main__":
    register()
