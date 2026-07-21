'''
Dedicated renderer. 

Initializes textures on import.
'''

import pygame, os
from math import ceil
from typing import TypeAlias, SupportsIndex

from logic_objects import (
    RENDER_SCALE,              
    OR_gate,  AND_gate,           XOR_gate,
    NOR_gate, NAND_gate,          XNOR_gate,
    buffer,   NOT_gate,           toggle_switch,
    light,    horizontal_display, vertical_display,

    node,     wire_node,          wire,
    wire_attacher,

    logic_object,       LOGIC_OBJECTS,

    NO_OUTPUT_OBJECTS,
)
from constants import (
    OR_GATE_FILES,            AND_GATE_FILES,           XOR_GATE_FILES,
    NOR_GATE_FILES,           NAND_GATE_FILES,          XNOR_GATE_FILES,
    BUFFER_FILE,              NOT_GATE_FILE,            TOGGLE_OFF_FILE,
    TOGGLE_ON_FILE,           TOG_OFF_HLGHT_FILE,       TOG_ON_HLGHT_FILE,
    LIGHT_OFF_FILE,           LIGHT_ON_FILE,            LT_OFF_HLGHT_FILE,
    LT_ON_HLGHT_FILE,

    HORIZONTAL_DISPLAY_FILES, VERTICAL_DISPLAY_FILES,
    
    NODE_FILE,                ARROW_CLOSE_FILE,         ARROW_OPEN_FILE,
    SAVE_BUTTON_FILE,         SETTINGS_BUTTON_FILE,     
    SUCCESS_FILE,             FAIL_FILE,                SLIDER_KNOB_FILE,
    
    PNG_DIR,                  OBJ_DIR,                  OR_GATE_DIR,  
    AND_GATE_DIR,             XOR_GATE_DIR,             NOR_GATE_DIR, 
    NAND_GATE_DIR,            XNOR_GATE_DIR,        
    TOGGLE_SWITCH_DIR,        LIGHT_DIR,
    HDISPLAY_DIR,             VDISPLAY_DIR,

    OBJECT_SIZES,             OBJECT_BOUNDS,            OBJECT_NODE_POSITIONS,
)
from gui import (
    rect,
    text_label,
    button,
    slider,
    dropdown,
    text_input,
    interface,
    confirmation_prompt,
    input_prompt,
    notification,
    scrollable_list,
    side_bar,
    side_bar_icon,
    object_placer,
    selection_area,
)

__all__ = [
    'TEXTURES_BY_FILE',
    'TEXTURES_BY_KEY',
    'COMPLETE_TEXTURES',
    'TRANSPARENT_COMPLETE_TEXTURES',
    'render',
]

path: TypeAlias = str
DO_NOT_PASS_ARG: TypeAlias = None


_LOAD_SVG = pygame.image.load_sized_svg
_LOAD = pygame.image.load
_JOIN = os.path.join

TEXTURES_BY_FILE = {
    BUFFER_FILE:                       _LOAD_SVG(_JOIN(OBJ_DIR, BUFFER_FILE), buffer.RENDER_SIZES[buffer.INPUT_DEFAULT]).convert_alpha(),
    NOT_GATE_FILE:                     _LOAD_SVG(_JOIN(OBJ_DIR, NOT_GATE_FILE), NOT_gate.RENDER_SIZES[NOT_gate.INPUT_DEFAULT]).convert_alpha(),
    TOGGLE_OFF_FILE:                   _LOAD_SVG(_JOIN(TOGGLE_SWITCH_DIR, TOGGLE_OFF_FILE), toggle_switch.RENDER_SIZES[toggle_switch.INPUT_DEFAULT]).convert_alpha(),
    TOGGLE_ON_FILE:                    _LOAD_SVG(_JOIN(TOGGLE_SWITCH_DIR, TOGGLE_ON_FILE), toggle_switch.RENDER_SIZES[toggle_switch.INPUT_DEFAULT]).convert_alpha(),
    LIGHT_OFF_FILE:                    _LOAD_SVG(_JOIN(LIGHT_DIR, LIGHT_OFF_FILE), light.RENDER_SIZES[light.INPUT_DEFAULT]).convert_alpha(),
    LIGHT_ON_FILE:                     _LOAD_SVG(_JOIN(LIGHT_DIR, LIGHT_ON_FILE), light.RENDER_SIZES[light.INPUT_DEFAULT]).convert_alpha(),
    NODE_FILE:                         _LOAD_SVG(_JOIN(OBJ_DIR, NODE_FILE), node.RENDER_SIZE).convert_alpha(),

    ARROW_CLOSE_FILE:                  _LOAD(_JOIN(PNG_DIR, ARROW_CLOSE_FILE)).convert_alpha(),
    ARROW_OPEN_FILE:                   _LOAD(_JOIN(PNG_DIR, ARROW_OPEN_FILE)).convert_alpha(),
    SAVE_BUTTON_FILE:                  _LOAD(_JOIN(PNG_DIR, SAVE_BUTTON_FILE)).convert_alpha(),
    SETTINGS_BUTTON_FILE:              _LOAD(_JOIN(PNG_DIR, SETTINGS_BUTTON_FILE)).convert_alpha(),
    
    SUCCESS_FILE:                      _LOAD(_JOIN(PNG_DIR, SUCCESS_FILE)).convert_alpha(),
    FAIL_FILE:                         _LOAD(_JOIN(PNG_DIR, FAIL_FILE)).convert_alpha(),
    SLIDER_KNOB_FILE:                  _LOAD(_JOIN(PNG_DIR, SLIDER_KNOB_FILE)).convert_alpha(),
}

TEXTURES_BY_KEY = {
    buffer.DEFAULT_RENDER_KEY:         (None, TEXTURES_BY_FILE[BUFFER_FILE],),
    NOT_gate.DEFAULT_RENDER_KEY:       (None, TEXTURES_BY_FILE[NOT_GATE_FILE],),
    toggle_switch.OFF_KEY:             (TEXTURES_BY_FILE[TOGGLE_OFF_FILE],), 
    toggle_switch.ON_KEY:              (TEXTURES_BY_FILE[TOGGLE_ON_FILE],),
    light.OFF_KEY:                     (None, TEXTURES_BY_FILE[LIGHT_OFF_FILE],),
    light.ON_KEY:                      (None, TEXTURES_BY_FILE[LIGHT_ON_FILE],),
}

_size = horizontal_display.RENDER_SIZES[horizontal_display.INPUT_DEFAULT]
for file, key in zip(HORIZONTAL_DISPLAY_FILES, horizontal_display.DISPLAY_KEYS):
    t = _LOAD_SVG(_JOIN(HDISPLAY_DIR, file), _size).convert_alpha()

    TEXTURES_BY_FILE[file] = t
    TEXTURES_BY_KEY[key] = (None, None, None, None, t)

_size = vertical_display.RENDER_SIZES[vertical_display.INPUT_DEFAULT]
for file, key in zip(VERTICAL_DISPLAY_FILES, vertical_display.DISPLAY_KEYS):
    t = _LOAD_SVG(_JOIN(VDISPLAY_DIR, file), _size).convert_alpha()

    TEXTURES_BY_FILE[file] = t
    TEXTURES_BY_KEY[key] = (None, None, None, None, t)

for cls, directory, files in (
    (OR_gate, OR_GATE_DIR, OR_GATE_FILES), 
    (AND_gate, AND_GATE_DIR, AND_GATE_FILES), 
    (XOR_gate, XOR_GATE_DIR, XOR_GATE_FILES), 
    (NOR_gate, NOR_GATE_DIR, NOR_GATE_FILES), 
    (NAND_gate, NAND_GATE_DIR, NAND_GATE_FILES), 
    (XNOR_gate, XNOR_GATE_DIR, XNOR_GATE_FILES)
    ):
    _sizes = cls.RENDER_SIZES

    l = []

    for i, file in enumerate(files):
        if file:
            t = _LOAD_SVG(_JOIN(directory, file), _sizes[i]).convert_alpha()

            TEXTURES_BY_FILE[file] = t
            l.append(t)
        else:
            l.append(None)

    TEXTURES_BY_KEY[cls.DEFAULT_RENDER_KEY] = tuple(l) 

COMPLETE_TEXTURES = {}

TRANSPARENT_COMPLETE_TEXTURES = {}

_HIGHLIGHTED_TEXTURES = {
    toggle_switch.OFF_KEY:     (_LOAD_SVG(_JOIN(TOGGLE_SWITCH_DIR, TOG_OFF_HLGHT_FILE), toggle_switch.RENDER_SIZES[toggle_switch.INPUT_DEFAULT]).convert_alpha(),),
    toggle_switch.ON_KEY:      (_LOAD_SVG(_JOIN(TOGGLE_SWITCH_DIR, TOG_ON_HLGHT_FILE), toggle_switch.RENDER_SIZES[toggle_switch.INPUT_DEFAULT]).convert_alpha(),),
    light.OFF_KEY:             (None, _LOAD_SVG(_JOIN(LIGHT_DIR, LT_OFF_HLGHT_FILE), light.RENDER_SIZES[light.INPUT_DEFAULT]).convert_alpha(),),
    light.ON_KEY:              (None, _LOAD_SVG(_JOIN(LIGHT_DIR, LT_ON_HLGHT_FILE), light.RENDER_SIZES[light.INPUT_DEFAULT]).convert_alpha(),),
}

_keys = [
    OR_gate.DEFAULT_RENDER_KEY,
    AND_gate.DEFAULT_RENDER_KEY,
    XOR_gate.DEFAULT_RENDER_KEY,
    NOR_gate.DEFAULT_RENDER_KEY,
    NAND_gate.DEFAULT_RENDER_KEY,
    XNOR_gate.DEFAULT_RENDER_KEY,
    buffer.DEFAULT_RENDER_KEY,
    NOT_gate.DEFAULT_RENDER_KEY,
]
_keys += horizontal_display.DISPLAY_KEYS
_keys += vertical_display.DISPLAY_KEYS

for key in _keys:
    textures = TEXTURES_BY_KEY[key]

    l = []

    for tex in textures:
        if tex:
            tx =  tex.copy()
            t = tx.copy()
            add = t.copy()
            add.fill((160,160,160), special_flags=pygame.BLEND_RGB_MULT)
            t.blit(add, (0,0), special_flags=pygame.BLEND_RGB_ADD)
            l.append(t)
        else:
            l.append(None)

    _HIGHLIGHTED_TEXTURES[key] = tuple(l)

tx =  TEXTURES_BY_FILE[NODE_FILE].copy()
t = tx.copy()
add = t.copy()
add.fill((160,160,160), special_flags=pygame.BLEND_RGB_MULT)
t.blit(add, (0,0), special_flags=pygame.BLEND_RGB_ADD)
_HIGHLIGHTED_TEXTURES[node] = t

_NODE_TEXTURE = TEXTURES_BY_FILE[NODE_FILE]
_NODE_RADIUS = _NODE_TEXTURE.get_width() / 2 # pre-render complete textures to avoid rendering nodes (mostly for gui elements)
for cls in LOGIC_OBJECTS:
    textures =  TEXTURES_BY_KEY[cls.DEFAULT_RENDER_KEY]

    nodes = OBJECT_NODE_POSITIONS[cls][0]

    l = []
    trans_l = []

    for tex, _nodes in zip(textures, nodes):
        if tex:
            tex = tex.copy()
            tex.fblits([(_NODE_TEXTURE, (dx * RENDER_SCALE - _NODE_RADIUS, dy * RENDER_SCALE - _NODE_RADIUS)) for dx, dy in _nodes])
            
            l.append(tex)

            tex = tex.copy()
            tex.fill((255,255,255,160), special_flags=pygame.BLEND_RGBA_MULT)

            trans_l.append(tex)
        else: 
            l.append(None)
            trans_l.append(None)
    
    COMPLETE_TEXTURES[cls] = tuple(l)
    TRANSPARENT_COMPLETE_TEXTURES[cls] = tuple(trans_l)

_SCALED_KEYS = (
    (OR_gate,            [OR_gate.DEFAULT_RENDER_KEY]),
    (AND_gate,           [AND_gate.DEFAULT_RENDER_KEY]),
    (XOR_gate,           [XOR_gate.DEFAULT_RENDER_KEY]),
    (NOR_gate,           [NOR_gate.DEFAULT_RENDER_KEY]),
    (NAND_gate,          [NAND_gate.DEFAULT_RENDER_KEY]), 
    (XNOR_gate,          [XNOR_gate.DEFAULT_RENDER_KEY]),
    (buffer,             [buffer.DEFAULT_RENDER_KEY]),
    (NOT_gate,           [NOT_gate.DEFAULT_RENDER_KEY]),
    (toggle_switch,      [toggle_switch.OFF_KEY, toggle_switch.ON_KEY]),
    (light,              [ light.OFF_KEY, light.ON_KEY]),
    (horizontal_display, horizontal_display.DISPLAY_KEYS),
    (vertical_display,   vertical_display.DISPLAY_KEYS),
)

_SCALED_TEXTURES = {}
_ZOOM_TEXTURE_KEYS = {}

for cls, keys in _SCALED_KEYS:
    l1 = []
    l2 = []

    hitboxes = cls.HITBOXES

    for key in keys:
        l1.clear()
        l2.clear()

        for hb in hitboxes:
            if hb:
                # eight slots for hightlighted and orientation combinations
                l1.append([None, None, None, None, None, None, None, None])
                l2.append([None, None, None, None, None, None, None, None])
            else:
                l1.append(None)
                l2.append(None)

        _SCALED_TEXTURES[key] = tuple(l1)
        _ZOOM_TEXTURE_KEYS[key] = tuple(l2)

class _cache_manager:
    def __init__(self, texture_dict: dict, zoom_keys_dict: dict, node_texture: pygame.Surface, hlght_node: pygame.Surface) -> None:
        self.cached_zoom = 0

        self.cached_grid_spacing = 50
        self.cached_inv_spacing = 1 / self.cached_grid_spacing

        self.cached_textures = texture_dict
        self.zoom_keys = zoom_keys_dict

        self.node_texture = node_texture
        self.cached_node = None

        self.hlght_node_texture = hlght_node
        self.cached_hlght_node = None
        
        self.cached_placer_texture = None
        self.obj_placer_orient = 0

def render(
    surf: pygame.Surface, 
    surf_dimensions:        tuple[int, int, float, float], 
    cam:                    tuple[float, float, float], 
    grid_size:              float | int, 
    logic_objects:          list[logic_object], 
    selected_obj_set:       set[logic_object],
    selected_node_set:      set[wire_node],
    selected_wire_set:      set[wire],
    render_manager:         object,
    gui_elements:           list[object],
    hlght_node:             tuple[logic_object, SupportsIndex],
    attacher:               wire_attacher,
    selection:              selection_area,
    # default parameters t  o improve performance
    __INV_RENDER_SCALE:     DO_NOT_PASS_ARG        = 1 / RENDER_SCALE, # constants.py
    __TEXTURES:             DO_NOT_PASS_ARG | dict = TEXTURES_BY_KEY,
    __HLGHT_TEXTURES:       DO_NOT_PASS_ARG | dict = _HIGHLIGHTED_TEXTURES,
    __TRANSP_TEXTURES:      DO_NOT_PASS_ARG | dict = TRANSPARENT_COMPLETE_TEXTURES,
    __CACHE_MANAGER:        DO_NOT_PASS_ARG        = _cache_manager(   # persistant object to keep track of cached textures
                                                                      _SCALED_TEXTURES, 
                                                                      _ZOOM_TEXTURE_KEYS,
                                                                      TEXTURES_BY_FILE[NODE_FILE], 
                                                                      _HIGHLIGHTED_TEXTURES[node]
                                                                  ), 
    __SIZES:                DO_NOT_PASS_ARG | dict = OBJECT_SIZES,
    __NODE_RADIUS:          DO_NOT_PASS_ARG        = node.SIZE[0] / 2,
    __WIRE_NODE_RADIUS:     DO_NOT_PASS_ARG        = wire_node.SIZE[0] / 2,
    __SLIDER_KNOB:          DO_NOT_PASS_ARG        = TEXTURES_BY_FILE[SLIDER_KNOB_FILE],
    __SLIDER_KNOB_RADIUS:   DO_NOT_PASS_ARG        = slider.KNOB_SIZE[0] / 2,
    __DROPDOWN_NULL_SELECT: DO_NOT_PASS_ARG        = dropdown.NULL_SELECTION,
    __DROPDOWN_NULL_SURF:   DO_NOT_PASS_ARG        = dropdown.NULL_SURFACE,
    __NODE_POSITIONS:       DO_NOT_PASS_ARG | dict = OBJECT_NODE_POSITIONS, # constants.py
    __BOUNDS:               DO_NOT_PASS_ARG        = OBJECT_BOUNDS, # constants.py
    __NO_OUTPUT_OBJECTS:    DO_NOT_PASS_ARG        = NO_OUTPUT_OBJECTS,
    # gui classes
    __GUI_RECT:             DO_NOT_PASS_ARG = rect,
    __TEXT_LABEL:           DO_NOT_PASS_ARG = text_label,
    __BUTTON:               DO_NOT_PASS_ARG = button,
    __SLIDER:               DO_NOT_PASS_ARG = slider,
    __DROPDOWN:             DO_NOT_PASS_ARG = dropdown,
    __TEXT_INPUT:           DO_NOT_PASS_ARG = text_input,
    __INTERFACE:            DO_NOT_PASS_ARG = interface,
    __CONFIRMATION_PROMPT:  DO_NOT_PASS_ARG = confirmation_prompt,
    __INPUT_PROMPT:         DO_NOT_PASS_ARG = input_prompt,
    __NOTIFICATION:         DO_NOT_PASS_ARG = notification,
    __SCROLLABLE_LIST:      DO_NOT_PASS_ARG = scrollable_list,
    __SIDE_BAR:             DO_NOT_PASS_ARG = side_bar,
    __OBJECT_PLACER:        DO_NOT_PASS_ARG = object_placer,
    # functions
    __RECT:                 DO_NOT_PASS_ARG = pygame.draw.rect, 
    __LINES:                DO_NOT_PASS_ARG = pygame.draw.lines,
    __SCALE_BY:             DO_NOT_PASS_ARG = pygame.transform.smoothscale_by,
    __ROTATE:               DO_NOT_PASS_ARG = pygame.transform.rotate,
    __CEIL:                 DO_NOT_PASS_ARG = ceil,
    /) -> None:
    surf_x, surf_y, hsx, hsy = surf_dimensions
    cam_x, cam_y, zoom = cam
    inv_zoom = 1 / zoom
    texture_scale = zoom * __INV_RENDER_SCALE
    
    if __CACHE_MANAGER.cached_zoom != zoom: # invalidate caches/cache textures for the new zoom level
        __CACHE_MANAGER.cached_grid_spacing     = 50 if zoom > 0.25 else 100 if zoom > 0.1 else 200
        __CACHE_MANAGER.cached_inv_spacing      = 1 / __CACHE_MANAGER.cached_grid_spacing
        __CACHE_MANAGER.cached_node             = __SCALE_BY(__CACHE_MANAGER.node_texture, texture_scale)
        __CACHE_MANAGER.cached_hlght_node       = __SCALE_BY(__CACHE_MANAGER.hlght_node_texture, texture_scale)
        __CACHE_MANAGER.cached_placer_texture   = None  

    if render_manager.render_objects:
        # grid lines
        surf.fill((224,224,224,255))  
        
        if zoom > .05: 
            grid_spacing = __CACHE_MANAGER.cached_grid_spacing
            inv_grid_spacing = __CACHE_MANAGER.cached_inv_spacing

            step = grid_spacing * zoom 
            start = hsx + zoom*(__CEIL((cam_x - hsx*inv_zoom)*inv_grid_spacing)*grid_spacing - cam_x) 
            for i in range(__CEIL(surf_x / step)): 
                surf.fill((183,183,183,255), (start + i*step,0,1,surf_y)) 
            
            start = hsy + zoom*(__CEIL((cam_y - hsy*inv_zoom)*inv_grid_spacing)*grid_spacing - cam_y) 
            for i in range(__CEIL(surf_y / step)): 
                surf.fill((183,183,183,255), (0,start + i*step,surf_x,1))

        cached_textures = __CACHE_MANAGER.cached_textures
        zoom_keys = __CACHE_MANAGER.zoom_keys
        NODE = __CACHE_MANAGER.cached_node
        HLGHT_NODE = __CACHE_MANAGER.cached_hlght_node
        if hlght_node:
            node_obj, node_idx = hlght_node
        else:
            node_obj = node_idx = None

        if selection:
            if (x1:=selection.x1) > (x2:=selection.x2): x1, x2 = x2, x1
            if (y1:=selection.y1) > (y2:=selection.y2): y1, y2 = y2, y1

        blit_list = []

        # wires
        wire_width = __CEIL(5 * zoom - 0.5)
        if wire_width == 0: 
            wire_width = 1

        hwnr = __WIRE_NODE_RADIUS * zoom
        nodes = []

        for obj in logic_objects: 
            if obj.__class__ not in __NO_OUTPUT_OBJECTS:
                for wr in obj.out_wires:
                    nodes.clear()
                    
                    # assigns wrnodes to wr.nodes, assigns n to the first node in the list, and assigns x and y the screen coordinates
                    nodes.append(((x:=hsx + zoom*((n:=(wrnodes:=wr.nodes)[0]).x - cam_x)), (y:=hsy + zoom*(n.y - cam_y))))

                    min_x = max_x = x
                    min_y = max_y = y
                    
                    wire_node_count = len(wrnodes) - 2
                    for i in range(1, wire_node_count + 1):
                        nodes.append(((x:=hsx + zoom*((n:=wrnodes[i]).x - cam_x)), (y:=hsy + zoom*(n.y - cam_y))))

                        blit_list.append(
                            (HLGHT_NODE if n in selected_node_set or 
                            (selection and (_x:=n.x) + __WIRE_NODE_RADIUS > x1 and _x - __WIRE_NODE_RADIUS < x2 
                            and (_y:=n.y) + __WIRE_NODE_RADIUS > y1 and _y - __WIRE_NODE_RADIUS < y2) 
                            else NODE, (x - hwnr, y - hwnr)))

                        if x < min_x: min_x = x
                        elif x > max_x: max_x = x
                        if y < min_y: min_y = y
                        elif y > max_y: max_y = y

                    nodes.append(((x:=hsx + zoom*((n:=wrnodes[-1]).x - cam_x)), (y:=hsy + zoom*(n.y - cam_y))))

                    if x < min_x: min_x = x
                    elif x > max_x: max_x = x
                    if y < min_y: min_y = y
                    elif y > max_y: max_y = y
                    
                    if min_x - hwnr < surf_x and max_x + hwnr > 0 and min_y - hwnr < surf_y and max_y + hwnr > 0:
                        __LINES(surf, (0,204,51) if wr in selected_wire_set else (45,120,218) if wr.signal else (16,16,16), False, nodes, width=wire_width)    
                    elif wire_node_count:
                        del blit_list[-wire_node_count:]

            # wire attacher
            if attacher:
                obj = attacher.obj
                nx, ny = __NODE_POSITIONS[obj.__class__][obj.orient][obj.input_count][attacher.idx]

                nodes.clear()
                nodes.append((hsx + zoom*(obj.x + nx - cam_x), hsy + zoom*(obj.y + ny - cam_y)))

                for nx, ny in attacher.nodes:
                    nodes.append(((x:=hsx + zoom*(nx - cam_x)), (y:=hsy + zoom*(ny - cam_y))))
                    blit_list.append((NODE, (x - hwnr, y - hwnr)))

                nodes.append((attacher.end_x, attacher.end_y))

                __LINES(surf, (45,120,218) if attacher.signal else (16,16,16), False, nodes, width=wire_width)

        # logic objects
        hnr = __NODE_RADIUS * zoom

        for obj in logic_objects:
            if (o:=obj.orient) & 1:
                h, w = __SIZES[cls:=obj.__class__][input_count:=obj.input_count]
            else :
                w, h = __SIZES[cls:=obj.__class__][input_count:=obj.input_count]

            if (x:=hsx + zoom*((objx:=obj.x) - cam_x)) < surf_x and x + w*zoom > 0 and (y:=hsy + zoom*((objy:=obj.y) - cam_y)) < surf_y and y + h*zoom > 0:    
                if selection and (objx > x1 - grid_size and objx < x2) and (objy > y1 - grid_size and objy < y2):
                    bx, by, bw, bh = __BOUNDS[cls][o][input_count]

                    if obj in selected_obj_set or ((_x:=objx + bx) + bw > x1 and _x < x2) and ((_y:=objy + by) + bh > y1 and _y < y2):
                        orient_key = o + 4
                    else:
                        orient_key = o
                elif obj in selected_obj_set:
                    orient_key = o + 4
                else:
                    orient_key = o

                tex = cached_textures[key:=obj.render_key][input_count][orient_key]; 

                # textures are dynamically scaled/rotated when needed and only invalidated when
                # the current zoom level no longer matches their scaled zoom level
                if zoom_keys[key][input_count][orient_key] != zoom:
                    tex = __SCALE_BY(__TEXTURES[key][input_count] if orient_key < 4 else __HLGHT_TEXTURES[key][input_count], texture_scale)

                    if o > 0: tex = __ROTATE(tex, 90*o)

                    cached_textures[key][input_count][orient_key] = tex
                    zoom_keys[key][input_count][orient_key] = zoom
            
            
                nodes = __NODE_POSITIONS[cls][o][input_count]
                
                blit_list.append((tex, (x, y)))

                x -= hnr; y -= hnr
                
                for i, (nx, ny) in enumerate(nodes):
                    blit_list.append((HLGHT_NODE if node_obj is obj and i == node_idx else NODE, (x + nx*zoom, y + ny*zoom)))

        surf.fblits(blit_list)

        if selection:
            x1 = hsx + zoom*(x1 - cam_x); y1 = hsy + zoom*(y1 - cam_y)
            x2 = hsx + zoom*(x2 - cam_x); y2 = hsy + zoom*(y2 - cam_y)
            
            surf.fill((142,189,250), (x1, y1, x2 - x1, y2 - y1), 3) # flag 3 is pygame.BLEND_RGB_MULT


    for element in gui_elements:
        if (cls:=element.__class__) is __OBJECT_PLACER:
            if element.active:
                if not __CACHE_MANAGER.cached_placer_texture or __CACHE_MANAGER.obj_placer_orient != element.orient:
                    tex = __SCALE_BY(__TRANSP_TEXTURES[cls:=element.cls][cls.INPUT_DEFAULT], texture_scale)
                    if (o:=element.orient) > 0: tex = __ROTATE(tex, 90*o)
                    __CACHE_MANAGER.cached_placer_texture = tex
                    __CACHE_MANAGER.obj_placer_orient = o

                w, h = (element.half_h, element.half_w) if element.orient & 1 else (element.half_w, element.half_h)

                surf.blit(__CACHE_MANAGER.cached_placer_texture, (hsx + zoom*(element.x - w - cam_x), hsy + zoom*(element.y - h - cam_y)))
            else:
                __CACHE_MANAGER.cached_placer_texture = None

        elif element.visible:
            if cls is __GUI_RECT:
                surf.fill(element.color, (element.x, element.y, element.w, element.h))
            elif cls is __TEXT_LABEL:
                surf.blit(element.surf, (element.x, element.y))
            elif cls is __BUTTON:
                surf.blit(element.inactive_surf if element.inactive else (element.hover_surf if element.hover else element.surf), (element.x, element.y))
            elif cls is __SLIDER:
                x = element.x; y = element.y
                surf.blit(element.surf, (x, y))
                surf.blit(__SLIDER_KNOB, (x + element.slider_x - __SLIDER_KNOB_RADIUS, y - __SLIDER_KNOB_RADIUS + 3.5))
                surf.blit(element.label, (x + element.label_x, y + element.label_y))
            elif cls is __DROPDOWN:
                if element.open:
                    y = element.y
                    text_x = element.x + element.option_x_offset
                    y_offset = element.option_y_offset
                    option_h = element.option_h

                    if element.scrollable:
                        x = element.x
                        w = element.w
                        open_h = element.open_h
                        brdr = element.border_thickness
                        option_surfs = element.option_surfs
                        option_count = len(option_surfs)

                        surf.fill(element.border_color, (x, y, w, open_h))
                        surf.fill(element.color, (x + brdr, y+brdr, w-brdr*2, option_h - brdr))

                        selected = element.selected
                        if selected is __DROPDOWN_NULL_SELECT:
                            surf.blit(__DROPDOWN_NULL_SURF, (text_x, y + y_offset))
                        else:
                            surf.blit(element.option_surfs[selected], (text_x, y + y_offset))

                        offset = element.scroll % option_h

                        _y = y + option_h

                        surf.blit(element.open_surf, (x, _y + brdr), (0,brdr+offset,w, open_h - option_h - brdr*2))

                        i = element.scroll // option_h
                        if selected is not __DROPDOWN_NULL_SELECT and i >= selected: i += 1

                        nsurf = option_surfs[i] if i < option_count else __DROPDOWN_NULL_SURF

                        if offset < y_offset - brdr:
                            surf.blit(nsurf, (text_x, _y + y_offset - offset))
                        else:
                            surf.blit(nsurf, (text_x, _y + brdr), (0, offset - y_offset + brdr, w, option_h))

                        _y += y_offset - offset

                        for _y in range(_y + option_h, y+open_h - option_h, option_h):
                            i += 1
                            if i == selected: i += 1

                            surf.blit(option_surfs[i], (text_x, _y))

                        i += 1
                        _y += option_h

                        nsurf = option_surfs[i] if i < option_count and selected != i else __DROPDOWN_NULL_SURF

                        surf.blit(nsurf, (text_x, _y), (0,0, w, y + open_h - _y - brdr))
                        
                    else:
                        surf.blit(element.open_surf, (element.x, y))

                        selected = element.selected
                        if selected is __DROPDOWN_NULL_SELECT:
                            surf.blit(__DROPDOWN_NULL_SURF, (text_x, y + y_offset))
                        else:
                            surf.blit(element.option_surfs[selected], (text_x, y + y_offset))
                            surf.blit(__DROPDOWN_NULL_SURF, (text_x, y + y_offset + element.open_h - option_h))

                        y += element.h

                        for i, s in enumerate(element.option_surfs):
                            if i != selected:
                                surf.blit(s, (text_x, y + y_offset))
                                y += option_h

                    surf.blit(element.open_tri, (element.x + element.tx, element.y + element.ty))

                else:
                    surf.blit(element.closed_surf, (element.x, element.y))

                    selected = element.selected
                    if selected is __DROPDOWN_NULL_SELECT:
                        surf.blit(__DROPDOWN_NULL_SURF, (element.x + element.option_x_offset, element.y + element.option_y_offset))
                    else:
                        surf.blit(element.option_surfs[selected], (element.x + element.option_x_offset, element.y + element.option_y_offset))

                    surf.blit(element.closed_tri, (element.x + element.tx, element.y + element.ty))

            elif cls is __TEXT_INPUT:
                surf.blit(element.surf, (element.x, element.y))

                x = element.x
                y = element.y

                font = element.font
                input = element.input

                input_w, h = font.size(input)

                x_offset = element.x_offset

                offset_width = element.w - x_offset
                text_width_limit = offset_width - x_offset

                if input_w > text_width_limit:
                    offset = input_w - offset_width
                else:
                    offset = 0
                    x += x_offset

                caret_offset, _ = font.size(input[:element.caret_idx])
                caret_pos = caret_offset - offset

                if offset and caret_pos < 30:
                    if caret_offset > 30:
                        offset += caret_pos - 30
                        caret_pos -= caret_pos - 30

                        offset_width += 5
                    else:
                        offset = 0
                        x += x_offset
                        caret_pos = caret_offset
                
                rect = (offset, 0, offset_width, h) if offset else (0, 0, offset_width, h)

                y += element.y_offset
                surf.blit(element.input_surf, (x, y), rect)

                if element.focused: surf.fill(element.font_color, (x + caret_pos, y-2, 1, 18))

            elif cls is __INTERFACE:
                surf.fill(element.color, (element.x, element.y, element.w, element.h))
            elif cls is __CONFIRMATION_PROMPT:
                surf.blit(element.surf, (element.x, element.y))
            elif cls is __INPUT_PROMPT:
                surf.blit(element.surf, (element.x, element.y))
            elif cls is __NOTIFICATION:
                surf.blit(element.surf, (element.x, element.y))
                surf.blit(element.text_surf, (element.x + element.text_x_end, element.y + element.text_y_offset))
            elif cls is __SCROLLABLE_LIST:
                x = element.x; y = element.y
                w = element.w; h = element.h

                hover = element.hover
                selected = element.selected

                scroll = element.scroll
                item_height = element.item_height

                text_x = x + element.text_x_offset
                y_offset = element.text_y_offset

                item_surfs = element.item_surfs

                hlght_color = element.hightlight_color
                
                if element.scrollable:
                    surf.fill(element.item_color, (x, y, w, h))
                    
                    i = scroll // item_height

                    _h = (i+1)*item_height - scroll

                    if i == hover or i == selected: surf.fill(hlght_color, (x, y, w, _h))
                    surf.blit(item_surfs[i], (text_x, y), (0, item_height - _h - y_offset, w, item_height))

                    for _y in range(y + _h, y + h - item_height, item_height):
                        i += 1
                        if i == hover or i == selected: surf.fill(hlght_color, (x, _y, w, item_height))
                        surf.blit(item_surfs[i], (text_x, _y + y_offset))

                    i += 1
                    if i < len(item_surfs):
                        _y += item_height
                        _h = y + h - _y

                        if i == hover or i == selected: surf.fill(hlght_color, (x, _y, w, _h))
                        surf.blit(item_surfs[i], (text_x, _y+y_offset), (0, 0, w, _h - y_offset))

                else:
                    surf.fill(element.bg_color, (x, y, w, h))
                    surf.fill(element.item_color, (x, y, w, len(item_surfs) * item_height))

                    for i, item_surf in enumerate(item_surfs):
                        _y = y + i*item_height
                        if i == hover or i == selected: surf.fill(hlght_color, (x, _y, w, item_height))
                        surf.blit(item_surf, (text_x, _y + y_offset))

            elif cls is __SIDE_BAR:
                x = element.x; y = element.y
                hover = element.hover_icon

                surf.blit(element.surf, (x,y))

                x += 10; y += 10
                rects = element.rects
                for i, icon in enumerate(element.icons):
                    _x, _y, w, h = rects[i]
                    surf.blit(icon.surf, (x + _x, y + _y))
                    if icon is hover:
                        (hsurf:=element.hlght_surf).fill((0,0,0,0))
                        hsurf.fill((45,120,218,230), (0, 0, w, h))
                        hsurf.fill((0,0,0,0), (3, 3, w-6, h-6))
                        surf.blit(hsurf, (x + _x, y + _y))