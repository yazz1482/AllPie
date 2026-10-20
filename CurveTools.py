import bpy
import gpu
import math

from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import ( location_3d_to_region_2d, region_2d_to_location_3d,)


# COLORS

CURVE_COLOR = (0.10, 0.70, 1.00, 1.0)
CURVE_SELECTED_COLOR = (1.00, 0.45, 0.08, 1.0)

HANDLE_LINE_COLOR = (0.65, 0.65, 0.65, 0.85)
HANDLE_SELECTED_LINE_COLOR = (1.00, 0.45, 0.08, 1.0)

POINT_FILL_COLOR = (0.10, 0.70, 1.00, 1.0)
POINT_OUTLINE_COLOR = (0.05, 0.05, 0.05, 1.0)

POINT_SELECTED_FILL_COLOR = (1.00, 0.45, 0.08, 1.0)
POINT_SELECTED_OUTLINE_COLOR = (1.00, 0.80, 0.40, 1.0)

HANDLE_FILL_COLOR = (0.70, 0.70, 0.70, 1.0)
HANDLE_OUTLINE_COLOR = (0.05, 0.05, 0.05, 1.0)

HANDLE_SELECTED_FILL_COLOR = (1.00, 0.45, 0.08, 1.0)
HANDLE_SELECTED_OUTLINE_COLOR = (1.00, 0.80, 0.40, 1.0)


# SETTINGS
CURVE_LINE_WIDTH = 5.0
SELECTED_CURVE_LINE_WIDTH = 6.0

HANDLE_LINE_WIDTH = 2.0
SELECTED_HANDLE_LINE_WIDTH = 3.0

POINT_RADIUS = 7.0
SELECTED_POINT_RADIUS = 9.0

HANDLE_RADIUS = 4.5
SELECTED_HANDLE_RADIUS = 6.0

HANDLE_HIT_RADIUS = 11.0
POINT_HIT_RADIUS = 10.0

CIRCLE_SEGMENTS = 20


# BEZIER MATH
def bezier_point(p0, h0, h1, p1, t):
    u = 1.0 - t

    return (
        u * u * u * p0
        + 3.0 * u * u * t * h0
        + 3.0 * u * t * t * h1
        + t * t * t * p1
    )


def make_bezier_segments(points, cyclic, steps=24):
    segments = []

    count = len(points)

    if count < 2:
        return segments

    segment_count = count if cyclic else count - 1

    for i in range(segment_count):
        a = points[i]
        b = points[(i + 1) % count]

        p0 = a.co.copy()
        h0 = a.handle_right.copy()
        h1 = b.handle_left.copy()
        p1 = b.co.copy()

        previous = bezier_point( p0, h0, h1, p1, 0.0,)

        for j in range(1, steps + 1):
            t = j / steps

            current = bezier_point( p0, h0, h1, p1, t,)
            segments.append( ( previous.copy(), current.copy(),))
            previous = current

    return segments


def transform_point(obj, co):
    return obj.matrix_world @ co


# ACTIVE CURVE
def get_active_curve():
    obj = bpy.context.object

    if obj is None:
        return None

    if obj.type != 'CURVE':
        return None

    if obj.mode != 'EDIT':
        return None

    return obj


# CURVE DATA
def build_curve_data(obj):
    curve_segments = []
    selected_curve_segments = []

    handle_segments = []
    selected_handle_segments = []

    handle_points = []
    selected_handle_points = []

    points = []
    selected_points = []

    for spline in obj.data.splines:

        if spline.hide:
            continue

        # BEZIER
        if spline.type == 'BEZIER':

            bezier_points = spline.bezier_points

            for point in bezier_points:

                world_co = transform_point( obj, point.co,)

                points.append(world_co)

                if point.select_control_point:
                    selected_points.append(world_co)

                # Left handle
                handle_left = transform_point( obj, point.handle_left,)
                handle_segments.append( ( world_co, handle_left,))
                handle_points.append( handle_left)

                if point.select_left_handle:
                    selected_handle_segments.append( ( world_co, handle_left,))
                    selected_handle_points.append( handle_left)

                # Right handle
                handle_right = transform_point( obj, point.handle_right,)
                handle_segments.append( ( world_co, handle_right,))
                handle_points.append( handle_right)

                if point.select_right_handle:
                    selected_handle_segments.append( ( world_co, handle_right,))
                    selected_handle_points.append( handle_right)

            # Curve
            local_segments = make_bezier_segments( bezier_points, spline.use_cyclic_u,)

            for p0, p1 in local_segments:
                curve_segments.append( ( transform_point(obj, p0), transform_point(obj, p1),))

        # POLY / NURBS
        elif spline.type in {'POLY', 'NURBS'}:

            spline_points = spline.points
            coords = []

            for point in spline_points:

                local_co = Vector( ( point.co.x, point.co.y, point.co.z,))
                world_co = transform_point( obj, local_co,)
                coords.append(world_co)
                points.append(world_co)

                if point.select:
                    selected_points.append( world_co)

            for i in range(len(coords) - 1):

                segment = ( coords[i], coords[i + 1],)

                curve_segments.append( segment)

                if ( spline.points[i].select and spline.points[i + 1].select):
                    selected_curve_segments.append( segment)

            if spline.use_cyclic_u and len(coords) > 2:

                segment = ( coords[-1], coords[0],)

                curve_segments.append( segment)

                if ( spline.points[-1].select and spline.points[0].select):
                    selected_curve_segments.append( segment)

    return (
        curve_segments,
        selected_curve_segments,
        handle_segments,
        selected_handle_segments,
        handle_points,
        selected_handle_points,
        points,
        selected_points,
    )

# GPU HELPERS
def flatten_segments(segments):
    result = []

    for a, b in segments:
        result.append(a)
        result.append(b)

    return result


def get_line_shader():
    return gpu.shader.from_builtin( 'POLYLINE_UNIFORM_COLOR')


def draw_lines(segments, color, width):
    if not segments:
        return

    shader = get_line_shader()

    viewport = gpu.state.viewport_get()

    shader.uniform_float( "viewportSize", ( viewport[2], viewport[3],),)
    shader.uniform_float( "lineWidth", width,)
    shader.uniform_float( "color", color,)

    batch = batch_for_shader( shader, 'LINES', { "pos": flatten_segments(segments), },)
    batch.draw(shader)


# SCREEN-SPACE CIRCLE
def get_screen_circle( context, position, radius, segments=CIRCLE_SEGMENTS,):
    region = context.region
    rv3d = context.space_data.region_3d

    center_2d = location_3d_to_region_2d( region, rv3d, position,)

    if center_2d is None:
        return None

    result = []

    for i in range(segments):

        angle = math.tau * i / segments

        screen_x = ( center_2d.x + math.cos(angle) * radius)
        screen_y = ( center_2d.y + math.sin(angle) * radius)

        world_position = region_2d_to_location_3d( region, rv3d, ( screen_x, screen_y,), position,)
        result.append( world_position)

    return result


# FILLED CIRCLE
def draw_filled_circle( context, position, radius, fill_color, outline_color, outline_width=2.0,):
    circle = get_screen_circle( context, position, radius,)

    if not circle:
        return

    # Fill
    fill_shader = gpu.shader.from_builtin( 'UNIFORM_COLOR')

    vertices = [position]
    vertices.extend(circle)
    vertices.append(circle[0])

    batch = batch_for_shader( fill_shader, 'TRI_FAN', { "pos": vertices, },)

    fill_shader.uniform_float( "color", fill_color,)

    batch.draw(fill_shader)

    # Outline
    line_shader = get_line_shader()

    viewport = gpu.state.viewport_get()

    line_shader.uniform_float( "viewportSize", ( viewport[2], viewport[3],),)
    line_shader.uniform_float( "lineWidth", outline_width,)
    line_shader.uniform_float( "color", outline_color,)

    outline_vertices = list(circle)
    outline_vertices.append(circle[0])
    outline_batch = batch_for_shader( line_shader, 'LINE_STRIP', { "pos": outline_vertices, },)
    outline_batch.draw(line_shader)


def draw_circle_group( context, positions, radius, fill_color, outline_color, outline_width,):
    if not positions:
        return

    for position in positions:
        draw_filled_circle( context, position, radius, fill_color, outline_color, outline_width,)


# 2D DISTANCE
def get_2d_distance(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]

    return math.sqrt( dx * dx + dy * dy)


# CONTROL POINT HIT TEST
def get_nearby_control_point( context, obj, mouse_x, mouse_y,):
    region = context.region
    rv3d = context.space_data.region_3d

    closest_distance = POINT_HIT_RADIUS

    for spline in obj.data.splines:

        if spline.hide:
            continue

        if spline.type != 'BEZIER':
            continue

        for point in spline.bezier_points:

            world_co = transform_point( obj, point.co,)

            screen_co = location_3d_to_region_2d( region, rv3d, world_co,)

            if screen_co is None:
                continue

            distance = get_2d_distance( ( screen_co.x, screen_co.y,), ( mouse_x, mouse_y,),)

            if distance < closest_distance:
                return True

    return False


# HANDLE HIT TEST
def find_handle_under_mouse( context, obj, mouse_x, mouse_y,):
    region = context.region
    rv3d = context.space_data.region_3d

    if get_nearby_control_point( context, obj, mouse_x, mouse_y,):
        return None

    closest = None
    closest_distance = HANDLE_HIT_RADIUS

    for spline_index, spline in enumerate( obj.data.splines):

        if spline.hide:
            continue

        if spline.type != 'BEZIER':
            continue

        for point_index, point in enumerate( spline.bezier_points):

            # Left
            handle_left = transform_point( obj, point.handle_left,)
            screen_left = location_3d_to_region_2d( region, rv3d, handle_left,)

            if screen_left is not None:

                distance = get_2d_distance( ( screen_left.x, screen_left.y,), ( mouse_x, mouse_y,),)

                if distance < closest_distance:

                    closest_distance = distance
                    closest = ( spline_index, point_index, 'LEFT',)

            # Right
            handle_right = transform_point( obj, point.handle_right,)
            screen_right = location_3d_to_region_2d( region, rv3d, handle_right,)

            if screen_right is not None:

                distance = get_2d_distance( ( screen_right.x, screen_right.y,), ( mouse_x, mouse_y,),)

                if distance < closest_distance:

                    closest_distance = distance
                    closest = ( spline_index, point_index, 'RIGHT',)

    return closest


# HANDLE SELECTION
def deselect_all_handles(obj):

    for spline in obj.data.splines:

        if spline.type != 'BEZIER':
            continue

        for point in spline.bezier_points:

            point.select_left_handle = False
            point.select_right_handle = False


def get_selected_handles(obj):
    result = []

    for spline_index, spline in enumerate( obj.data.splines):

        if spline.type != 'BEZIER':
            continue

        for point_index, point in enumerate( spline.bezier_points):

            if point.select_left_handle:

                result.append( ( spline_index, point_index, 'LEFT',))

            if point.select_right_handle:

                result.append( ( spline_index, point_index, 'RIGHT',))

    return result


# HANDLE WORLD POSITION
def get_handle_world_position( obj, spline_index, point_index, side,):
    spline = obj.data.splines[ spline_index ]
    point = spline.bezier_points[ point_index ]

    if side == 'LEFT':
        return transform_point( obj, point.handle_left,)

    return transform_point( obj, point.handle_right,)


# HANDLE DRAG
def update_handle_drag( self, context, mouse_x, mouse_y,):
    if not self._dragging_handle:
        return

    if self._drag_start_world is None:
        return

    obj = context.object

    if obj is None:
        return

    region = context.region
    rv3d = context.space_data.region_3d

    current_world = region_2d_to_location_3d( region, rv3d, ( mouse_x, mouse_y,), self._drag_start_world,)

    if current_world is None:
        return

    world_delta = ( current_world - self._drag_start_world)
    local_delta = ( obj.matrix_world.inverted().to_3x3() @ world_delta)

    for ( spline_index, point_index, side, original_position,) in self._drag_handles:

        spline = obj.data.splines[ spline_index ]
        point = spline.bezier_points[ point_index ]
        new_position = ( original_position + local_delta)

        if side == 'LEFT':

            point.handle_left_type = 'FREE'
            point.handle_left = new_position

        else:

            point.handle_right_type = 'FREE'
            point.handle_right = new_position

    context.view_layer.update()

    if self._area:
        self._area.tag_redraw()


def start_handle_drag( self, context, hit, mouse_x, mouse_y, extend=False,):
    obj = context.object

    if obj is None:
        return False

    if not extend:
        deselect_all_handles(obj)

    spline_index, point_index, side = hit
    spline = obj.data.splines[ spline_index ]
    point = spline.bezier_points[ point_index ]

    if side == 'LEFT':
        point.select_left_handle = True
    else:
        point.select_right_handle = True

    selected_handles = get_selected_handles( obj)

    if not selected_handles:
        return False

    drag_handles = []

    for ( selected_spline_index, selected_point_index, selected_side,) in selected_handles:

        selected_spline = obj.data.splines[ selected_spline_index ]

        selected_point = ( selected_spline.bezier_points[ selected_point_index ])

        if selected_side == 'LEFT':

            original_position = ( selected_point.handle_left.copy())

        else:

            original_position = ( selected_point.handle_right.copy())

        drag_handles.append( ( selected_spline_index, selected_point_index,
                              selected_side, original_position,))

    start_world = get_handle_world_position( obj, spline_index, point_index, side,)

    self._dragging_handle = True
    self._drag_start_mouse = ( mouse_x, mouse_y,)
    self._drag_start_world = start_world
    self._drag_handles = drag_handles

    context.view_layer.update()

    if self._area:
        self._area.tag_redraw()

    return True


def finish_handle_drag( self, context,):
    self._dragging_handle = False
    self._drag_start_mouse = None
    self._drag_start_world = None
    self._drag_handles = None

    if self._area:
        self._area.tag_redraw()


# MAIN DRAW
def draw_curve_overlay():

    context = bpy.context

    if context.area is None:
        return

    if context.area.type != 'VIEW_3D':
        return

    obj = get_active_curve()

    if obj is None:
        return

    (
        curve_segments,
        selected_curve_segments,
        handle_segments,
        selected_handle_segments,
        handle_points,
        selected_handle_points,
        points,
        selected_points,
    ) = build_curve_data(obj)

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')

    # Main curve
    draw_lines( curve_segments, CURVE_COLOR, CURVE_LINE_WIDTH,)
    # Selected curve
    draw_lines( selected_curve_segments, CURVE_SELECTED_COLOR, SELECTED_CURVE_LINE_WIDTH,)
    # Handle lines
    draw_lines( handle_segments, HANDLE_LINE_COLOR, HANDLE_LINE_WIDTH,)
    # Selected handle lines
    draw_lines( selected_handle_segments, HANDLE_SELECTED_LINE_COLOR, SELECTED_HANDLE_LINE_WIDTH,)
    # Handle circles
    draw_circle_group( context, handle_points, HANDLE_RADIUS, HANDLE_FILL_COLOR, HANDLE_OUTLINE_COLOR, 1.5,)

    # Selected handle circles
    draw_circle_group( context, selected_handle_points,
        SELECTED_HANDLE_RADIUS, HANDLE_SELECTED_FILL_COLOR, HANDLE_SELECTED_OUTLINE_COLOR, 2.0,)

    # Control points
    draw_circle_group( context, points, POINT_RADIUS, POINT_FILL_COLOR, POINT_OUTLINE_COLOR, 2.0,)

    # Selected control points
    draw_circle_group( context, selected_points,
        SELECTED_POINT_RADIUS, POINT_SELECTED_FILL_COLOR, POINT_SELECTED_OUTLINE_COLOR, 2.5,)

    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.blend_set('NONE')


# OPERATOR
class ALLPIE_OT_VisualCurveTool( bpy.types.Operator):

    bl_idname = "allpie.visual_curve_tool"
    bl_label = "Visual Curve Tool"
    bl_description = "Visual curve editing tool"

    _timer = None
    _handler = None
    _area = None
    _space = None
    _old_display_handle = None

    _dragging_handle = False
    _drag_start_mouse = None
    _drag_start_world = None
    _drag_handles = None

    # MODAL
    def modal( self, context, event,):
        obj = context.object

        # EXIT
        if event.type == 'ESC':

            if self._dragging_handle:

                finish_handle_drag( self, context,)

                return {'RUNNING_MODAL'}

            self.finish(context)

            return {'FINISHED'}

        # VALIDATION
        if ( obj is None or obj.type != 'CURVE' or obj.mode != 'EDIT'):

            self.finish(context)

            return {'FINISHED'}

        # HANDLE DRAG
        if self._dragging_handle:

            if event.type == 'MOUSEMOVE':

                update_handle_drag( self, context, event.mouse_region_x, event.mouse_region_y,)

                return {'RUNNING_MODAL'}

            if ( event.type == 'LEFTMOUSE' and event.value == 'RELEASE'):

                finish_handle_drag( self, context,)

                return {'RUNNING_MODAL'}

            if event.type in { 'MIDDLEMOUSE', 'RIGHTMOUSE', }:

                return {'PASS_THROUGH'}

            return {'RUNNING_MODAL'}

        # HANDLE PRESS
        if ( event.type == 'LEFTMOUSE' and event.value == 'PRESS'):

            hit = find_handle_under_mouse( context, obj, event.mouse_region_x, event.mouse_region_y,)

            if hit is not None:

                start_handle_drag( self, context, 
                                  hit, event.mouse_region_x, event.mouse_region_y, extend=event.shift,)

                return {'RUNNING_MODAL'}

        # TIMER
        if event.type == 'TIMER':

            if self._area:
                self._area.tag_redraw()

        # Let Blender handle regular point selection,
        # tweak tool, navigation, etc.
        return {'PASS_THROUGH'}

    # INVOKE
    def invoke( self, context, event,):

        if context.area.type != 'VIEW_3D':

            self.report( {'WARNING'}, "Visual Curve Tool requires a 3D View",)
            return {'CANCELLED'}

        obj = context.object

        if obj is None:

            self.report( {'WARNING'}, "Select a curve",)
            return {'CANCELLED'}

        if obj.type != 'CURVE':

            self.report( {'WARNING'}, "Select a curve",)
            return {'CANCELLED'}

        if obj.mode != 'EDIT':

            self.report( {'WARNING'}, "Enter Curve Edit Mode",)
            return {'CANCELLED'}

        self._area = context.area
        self._space = context.space_data

        # HIDE NATIVE HANDLES
        try:

            self._old_display_handle = ( self._space.overlay.display_handle)
            self._space.overlay.display_handle = 'NONE'

        except Exception:

            self._old_display_handle = None

        # DRAW HANDLER
        self._handler = (
            bpy.types.SpaceView3D.draw_handler_add( draw_curve_overlay, (), 'WINDOW', 'POST_VIEW',))

        # TIMER
        self._timer = ( context.window_manager.event_timer_add( 0.03, window=context.window,))
        # MODAL
        context.window_manager.modal_handler_add( self)
        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    # FINISH
    def finish( self, context,):
        self._dragging_handle = False
        self._drag_start_mouse = None
        self._drag_start_world = None
        self._drag_handles = None

        # Remove draw handler
        if self._handler is not None:

            try:

                bpy.types.SpaceView3D.draw_handler_remove( self._handler, 'WINDOW',)

            except Exception:
                pass

            self._handler = None

        # Remove timer
        if self._timer is not None:

            try:

                context.window_manager.event_timer_remove( self._timer)

            except Exception:
                pass

            self._timer = None

        # Restore native handles
        if ( self._space is not None and self._old_display_handle is not None):

            try:

                self._space.overlay.display_handle = ( self._old_display_handle)

            except Exception:
                pass

        if self._area is not None:
            self._area.tag_redraw()


# REGISTER
classes = ( ALLPIE_OT_VisualCurveTool,)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):

        try:
            bpy.utils.unregister_class(cls)

        except Exception:
            pass
