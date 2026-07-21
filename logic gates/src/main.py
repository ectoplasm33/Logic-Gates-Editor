'''
Logic gates simulator/editor

**Supported Gate Types:**
- OR
- AND
- XOR
- NOR
- NAND
- NXOR
- BUFFER
- NOT

**Auxiliary Components:**
- Toggle Switch
- Light
- 4-bit display

**Controls:**
- WASD camera movement
- scroll zooming
- R to rotate selection
- G to disable/enable grid snapping
- N to open prompt for new save
- drag selection
- ctrl+c to copy selection
- ctrl+v to paste selection
- ctrl+z to undo last action
- ctrl+shift+z | ctrl+y to redo

**Notes:**
This simulator is built on pygame.
Many sections of this simulator are inlined to favor performance.
'''
import pygame, time, os
from typing import TypeAlias
from math import trunc, floor, sqrt, inf

from logic_objects import (
    RENDER_SCALE,       logic_gate,         OR_gate,
    AND_gate,           XOR_gate,           NOR_gate,
    NAND_gate,          XNOR_gate,          buffer,
    NOT_gate,           toggle_switch,      light,
    horizontal_display, vertical_display,

    node,               wire_node,          wire_segment,
    wire,               wire_attacher,
    logic_object,       LOGIC_OBJECTS,
    GATE_OBJECTS,       NO_INPUT_OBJECTS,   NO_OUTPUT_OBJECTS
)
import storage
import serialization as serial
from actions import (
    attach_wire_action,
    node_insertion_action,
    place_objects_action,
    flip_switch_action,
    move_selection_action,
    rotate_selection_action,
    delete_selection_action,
    modify_input_count_action,
)
from constants import (
    DATA_DIR,    PNG_DIR,
    SAVE_BUTTON_FILE,       ARROW_OPEN_FILE,      ARROW_CLOSE_FILE,
    SETTINGS_BUTTON_FILE,
    SUCCESS_FILE,           FAIL_FILE,
    
    OBJECT_SIZES,           OBJECT_HALF_SIZES,       OBJECT_BOUNDS,
    OBJECT_HITBOXES,        OBJECT_NODE_POSITIONS,
)
from config import (
    load_config,
    update_config,
)

pygame.init()

_DISPLAY = pygame.display

_SCREEN_RESOLUTIONS = _DISPLAY.get_desktop_sizes()
_win_x, _win_y = _SCREEN_RESOLUTIONS[0]
_win_x = trunc(_win_x / 1.2); _win_y = trunc(_win_y / 1.2)
_hwx = _win_x / 2; _hwy = _win_y / 2
_WINDOW = _DISPLAY.set_mode((_win_x, _win_y), pygame.RESIZABLE)
_DISPLAY.set_caption('Logic Gates')

icon = pygame.image.load(os.path.join(PNG_DIR, 'window_icon.png')).convert()
_DISPLAY.set_icon(icon)

_WIN_BUFFER = pygame.Surface((_win_x, _win_y), pygame.SRCALPHA)

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
import behaviors

import render

class _render_manager:
    def __init__(self):
        self.render_objects = True

_RENDER_MANAGER = _render_manager()

class _saves_manager:
    def __init__(self):
        self.opened_file_path = None
        self.default_opened_file_path = None

    def update_opened_path(self, file_name: str, __DATA_DIR = DATA_DIR, __JOIN = os.path.join,/) -> None:
        self.opened_file_path = __JOIN(__DATA_DIR, file_name)

    def update_default_path(self, file_name: str, __DATA_DIR = DATA_DIR, __JOIN = os.path.join,/) -> None:
        self.default_opened_file_path = __JOIN(__DATA_DIR, file_name)

_SAVES_MANAGER = _saves_manager()

class _gui_manager:
    def __init__(self):
        self.open_interface = None
        self.active_prompt = None
        self.focused_input = None

_GUI_MANAGER = _gui_manager()

class _propagation_manager:
    def __init__(self):
        self.cyclic_circuit_objs = set() # set containing all of the objects that are part of a cyclic circuit
        self.cyclic_circuits = []        # list of sets of individual cyclic circuits
        self.cyclic_queue = []

        self.next_queue_update = None
        self.CYCLIC_CIRCUIT_UPDATE_FREQUENCY = 30

_PROP_MANAGER = _propagation_manager()

def _update_object_output(
    obj: logic_object, 
    OR_GATE = OR_gate, 
    AND_GATE = AND_gate, 
    XOR_GATE = XOR_gate, 
    NOR_GATE = NOR_gate, 
    NAND_GATE = NAND_gate, 
    XNOR_GATE = XNOR_gate, 
    BUFFER = buffer, 
    NOT_GATE = NOT_gate, 
    TOGGLE = toggle_switch, 
    LIGHT = light,
    HDISPLAY = horizontal_display,
    VDISPLAY = vertical_display,
    __HDISPLAY_KEYS = horizontal_display.DISPLAY_KEYS,
    __VDISPLAY_KEYS = vertical_display.DISPLAY_KEYS,
    __TOGGLE_ON = toggle_switch.ON_KEY, __TOGGLE_OFF = toggle_switch.OFF_KEY,
    __LIGHT_ON = light.ON_KEY, __LIGHT_OFF = light.OFF_KEY,
    __PROP_MANAGER = _PROP_MANAGER,
    /) -> None:
    this_prop_inst = object() # an object to represent this propagation instance 
    cyclic_objects = __PROP_MANAGER.cyclic_circuit_objs
    cyclic_queue = __PROP_MANAGER.cyclic_queue

    stack = [obj]

    i = 0

    while i < len(stack):
        obj = stack[i]
        obj.prop_inst = this_prop_inst
        i += 1
        
        if (cls:=obj.__class__) is OR_GATE:
            output = False
            for o in obj.inputs:
                if o and o.output:
                    output = True
                    break
        elif cls is AND_GATE:
            output = True
            for o in obj.inputs:
                if not (o and o.output):
                    output = False
                    break
        elif cls is XOR_GATE:
            output = False
            for o in obj.inputs:
                if o and o.output: output = not output
        elif cls is NOR_GATE:
            output = True
            for o in obj.inputs:
                if o and o.output:
                    output = False
                    break
        elif cls is NAND_GATE:
            output = False
            for o in obj.inputs:
                if not (o and o.output):
                    output = True
                    break
        elif cls is XNOR_GATE:
            output = True
            for o in obj.inputs:
                if o and o.output: output = not output
        elif cls is BUFFER:
            output = inpt.output if (inpt:=obj.inputs[0]) else False 
        elif cls is NOT_GATE:
            output = (not inpt.output) if (inpt:=obj.inputs[0]) else True 
        elif cls is LIGHT:
            obj.output = output = inpt.output if (inpt:=obj.inputs[0]) else False
            obj.render_key = __LIGHT_ON if output else __LIGHT_OFF
            continue
        elif cls is HDISPLAY:
            output = 0
            for j, inpt in enumerate(obj.inputs):
                if inpt and inpt.output:
                    output |= 1 << j

            obj.output = output
            obj.render_key = __HDISPLAY_KEYS[output]
            continue
        elif cls is VDISPLAY:
            output = 0
            for j, inpt in enumerate(obj.inputs):
                if inpt and inpt.output:
                    output |= 1 << j

            obj.output = output
            obj.render_key = __VDISPLAY_KEYS[output]
            continue
        elif cls is TOGGLE:
            output = obj.output
            for wr in obj.out_wires: wr.signal = output
            
            for out in obj.outputs:
                if out not in cyclic_objects or out not in cyclic_queue:
                    out.last_update_source = obj

                    stack.append(out)

            obj.render_key = __TOGGLE_ON if output else __TOGGLE_OFF
            continue

        if output is not obj.output:
            obj.output = output
            for wr in obj.out_wires: wr.signal = output

            for out in obj.outputs:
                if out not in cyclic_objects or out not in cyclic_queue:
                    # traverse the update path if this object was already updated to determine if there is cyclic behavior
                    if out.prop_inst is this_prop_inst: 
                        source = obj
                        cycle_detected = False
                        while (source:=source.last_update_source) and source.prop_inst is this_prop_inst:
                            if source is out: # reconstruct the circuit if the source can be traced back to itself
                                cycle_detected = True
                                circuit = [out]

                                source = obj
                                while source is not out:
                                    circuit.append(source)
                                    source = source.last_update_source
                                
                                cyclic_objects.update(circuit)
                                __PROP_MANAGER.cyclic_circuits.append(set(circuit))
                                cyclic_queue.append(out)
                                break
                        
                        if cycle_detected: continue 

                    out.last_update_source = obj

                    stack.append(out)

def _update_end_nodes_input_modification(
    obj: logic_object,
    input_count: int,
    INV_GRID_CELL_SIZE: float,
    NODE_POSOITIONS: list[tuple[int, int]],
    segment_cx: dict[list[wire_segment]],
    segment_cy: dict[list[wire_segment]],
    __FLOOR = floor,
    /) -> None:
    nx, ny = NODE_POSOITIONS[input_count]
    nx += (objx:=obj.x); ny += (objy:=obj.y)

    cx = __FLOOR(nx * INV_GRID_CELL_SIZE); cy = __FLOOR(ny * INV_GRID_CELL_SIZE)

    for wr in obj.out_wires:
        wr.tran_idx = input_count

        seg = wr.segments[0]

        n1 = (wrnodes:=wr.nodes)[0]; n2 = wrnodes[1]

        min_cx = n1.cx; max_cx = n2_cx = n2.cx
        min_cy = n1.cy; max_cy = n2_cy = n2.cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

        for x in range(min_cx, max_cx + 1):
            (l:=segment_cx[x]).remove(seg)
            if not l: del segment_cx[x]
        for y in range(min_cy, max_cy + 1):
            (l:=segment_cy[y]).remove(seg)
            if not l: del segment_cy[y]

        n1.x = nx; n1.y = ny

        n1.cx = min_cx = cx; n1.cy = min_cy = cy
        max_cx = n2_cx; max_cy = n2_cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

        for x in range(min_cx, max_cx + 1):
            if not (l:=segment_cx.get(x)):
                segment_cx[x] = {seg}
            else:
                l.add(seg)
        for y in range(min_cy, max_cy + 1):
            if not (l:=segment_cy.get(y)):
                segment_cy[y] = {seg}
            else:
                l.add(seg)

    for wr in obj.in_wires:
        if wr:
            seg = wr.segments[-1]

            n1 = (wrnodes:=wr.nodes)[-1]; n2 = wrnodes[-2]

            min_cx = n1.cx; max_cx = n2_cx = n2.cx
            min_cy = n1.cy; max_cy = n2_cy = n2.cy

            if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
            if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

            for x in range(min_cx, max_cx + 1):
                (l:=segment_cx[x]).remove(seg)
                if not l: del segment_cx[x]
            for y in range(min_cy, max_cy + 1):
                (l:=segment_cy[y]).remove(seg)
                if not l: del segment_cy[y]
            
            nx, ny = NODE_POSOITIONS[wr.recv_idx]

            nx += objx; ny += objy

            n1.x = nx; n1.y = ny

            n1.cx = min_cx = cx; n1.cy = min_cy = cy
            max_cx = n2_cx; max_cy = n2_cy

            if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
            if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

            for x in range(min_cx, max_cx + 1):
                if not (l:=segment_cx.get(x)):
                    segment_cx[x] = {seg}
                else:
                    l.add(seg)
            for y in range(min_cy, max_cy + 1):
                if not (l:=segment_cy.get(y)):
                    segment_cy[y] = {seg}
                else:
                    l.add(seg)

def _end_drag_action(
    selected_obj_list: list[logic_object],
    selected_node_list: list[wire_node],
    obj_action_data: list[logic_object, float, float],
    node_action_data: list[logic_object, float, float],
    action_log: list,
    log_depth: int,
    MAX_ACTION_LOG_LENGTH: int,
    __MOVE_SELECTION_ACTION = move_selection_action,
    /) -> None:
    it = iter(selected_obj_list)
    valid = False
    
    i = 1
    for obj in it:
        x = obj.x; y = obj.y

        y_idx = i+1
        if x != obj_action_data[i] or y != obj_action_data[y_idx]:
            valid = True
            obj_action_data[i] -= x
            obj_action_data[y_idx] -= y 
            i += 3
            break

        obj_action_data[i] = 0
        obj_action_data[y_idx] = 0  
        i += 3

    if valid:
        for obj in it:
            obj_action_data[i] -= obj.x
            obj_action_data[i+1] -= obj.y
            i += 3

        i = 1
        for n in selected_node_list:
            node_action_data[i] -= n.x
            node_action_data[i+1] -= n.y
            i += 3

        if log_depth:
            del action_log[-log_depth:]

        if len(action_log) > MAX_ACTION_LOG_LENGTH:
            del action_log[0]

        action_log.append(__MOVE_SELECTION_ACTION(obj_action_data, node_action_data))
    else:
        it = iter(selected_node_list)

        i = 1
        for n in it:
            x = n.x; y = n.y

            y_idx = i+1
            if x != node_action_data[i] or y != node_action_data[y_idx]:
                valid = True
                node_action_data[i] -= x
                node_action_data[y_idx] -= y 
                i += 3
                break

            node_action_data[i] = 0
            node_action_data[y_idx] = 0  
            i += 3

        if valid:
            for n in it:
                node_action_data[i] -= n.x
                node_action_data[i+1] -= n.y
                i += 3

            if log_depth:
                del action_log[-log_depth:]

            action_log.append(__MOVE_SELECTION_ACTION(obj_action_data, node_action_data))

def _update_segments_and_nodes(
    INV_GRID_CELL_SIZE: float, 
    nodes_to_update: list[wire_node], 
    wire_node_grid: dict[tuple[int, int], set[wire_node]],
    segment_cx: dict[int, set[wire_segment]], 
    segment_cy: dict[int, set[wire_segment]],
    __FLOOR = floor,
    /) -> None:
    segments_list = []
    segments_set = set()

    for i, n in enumerate(nodes_to_update):
        cx = __FLOOR(n.x * INV_GRID_CELL_SIZE); cy = __FLOOR(n.y * INV_GRID_CELL_SIZE)

        seg1 = n.seg1; seg2 = n.seg2
        
        if cx != n.cx or cy != n.cy:
            if seg1 and seg2:
                (l:=wire_node_grid[cell:=(n.cx, n.cy)]).remove(n)
                if not l: del wire_node_grid[cell]

                if not (l:=wire_node_grid.get(cell:=(cx,cy))):
                    wire_node_grid[cell] = {n}
                else:
                    l.add(n)

                if seg1 not in segments_set:
                    segments_list.append(seg1)
                    segments_set.add(seg1)
                if seg2 not in segments_set:
                    segments_list.append(seg2)
                    segments_set.add(seg2)

            elif seg1 and seg1 not in segments_set:
                segments_list.append(seg1)
                segments_set.add(seg1)
            elif seg2 and seg2 not in segments_set:
                segments_list.append(seg2)
                segments_set.add(seg2)
        else:
            nodes_to_update[i] = None

    for seg in segments_list:
        min_cx = (n1:=seg.node1).cx; max_cx = (n2:=seg.node2).cx
        min_cy = n1.cy; max_cy = n2.cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

        for x in range(min_cx, max_cx + 1):
            (l:=segment_cx[x]).remove(seg)
            if not l: del segment_cx[x]
        for y in range(min_cy, max_cy + 1):
            (l:=segment_cy[y]).remove(seg)
            if not l: del segment_cy[y]

    for n in nodes_to_update:
        if n: n.cx = __FLOOR(n.x * INV_GRID_CELL_SIZE); n.cy = __FLOOR(n.y * INV_GRID_CELL_SIZE)

    for seg in segments_list:
        n1_cx = (n1:=seg.node1).cx; n1_cy = n1.cy
        n2_cx = (n2:=seg.node2).cx; n2_cy = n2.cy

        if n1_cx < n2_cx: min_cx = n1_cx; max_cx = n2_cx
        else: min_cx = n2_cx; max_cx = n1_cx
        if n1_cy < n2_cy: min_cy = n1_cy; max_cy = n2_cy
        else: min_cy = n2_cy; max_cy = n1_cy

        for x in range(min_cx, max_cx + 1):
            if not (l:=segment_cx.get(x)):
                segment_cx[x] = {seg}
            else:
                l.add(seg)
        for y in range(min_cy, max_cy + 1):
            if not (l:=segment_cy.get(y)):
                segment_cy[y] = {seg}
            else:
                l.add(seg)

def _remove_segments_and_nodes(
    segments: list[wire_segment], 
    nodes: list[wire_node],
    segment_cx: dict[int, set[wire_segment]], 
    segment_cy: dict[int, set[wire_segment]],
    wire_node_grid: dict[tuple[int, int], set[wire_node]],
    /) -> None:
    n_cx = (n:=nodes[0]).cx; n_cy = n.cy
    for i, seg in enumerate(segments):
        n = nodes[i+1]

        min_cx = n_cx; min_cy = n_cy 
        max_cx = n_cx = n.cx; max_cy = n_cy = n.cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy 

        for x in range(min_cx, max_cx + 1):
            (l:=segment_cx[x]).remove(seg)
            if not l: del segment_cx[x]
        for y in range(min_cy, max_cy + 1):
            (l:=segment_cy[y]).remove(seg)
            if not l: del segment_cy[y]

    for i in range(1, len(nodes) - 1):
        n = nodes[i]
        (l:=wire_node_grid[cell:=(n.cx, n.cy)]).remove(n)
        if not l: del wire_node_grid[cell]

def _insert_segments_and_nodes(
    segments: list[wire_segment], 
    nodes: list[wire_node],
    segment_cx: dict[int, set[wire_segment]], 
    segment_cy: dict[int, set[wire_segment]],
    wire_node_grid: dict[tuple[int, int], set[wire_node]],
    /) -> None:
    n_cx = (n:=nodes[0]).cx; n_cy = n.cy
    for i, seg in enumerate(segments):
        n = nodes[i+1]

        min_cx = n_cx; min_cy = n_cy 
        max_cx = n_cx = n.cx; max_cy = n_cy = n.cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy 

        for x in range(min_cx, max_cx + 1):
            if not (l:=segment_cx.get(x)):
                segment_cx[x] = {seg}
            else:
                l.add(seg)
        for y in range(min_cy, max_cy + 1):
            if not (l:=segment_cy.get(y)):
                segment_cy[y] = {seg}
            else:
                l.add(seg)

    for i in range(1, len(nodes) - 1):
        n = nodes[i]
        if not (l:=wire_node_grid[cell:=(n.cx, n.cy)]):
            wire_node_grid[cell] = {n}
        else:
            l.add(n)

def _create_and_insert_segments(
    wr: wire,
    segments: list[wire_segment], 
    nodes: list[wire_node],
    segment_cx: dict[int, set[wire_segment]], 
    segment_cy: dict[int, set[wire_segment]],
    __WIRE_SEG = wire_segment,
    /) -> None:
    node1 = nodes[0]
    n_cx = node1.cx; n_cy = node1.cy

    for i in range(1, len(nodes)):
        node2 = nodes[i]

        segments.append(seg:=__WIRE_SEG(node1, node2, wr))

        node1.seg2 = seg
        node2.seg1 = seg

        min_cx = n_cx; min_cy = n_cy 
        max_cx = n_cx = node2.cx; max_cy = n_cy = node2.cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy 

        for x in range(min_cx, max_cx + 1):
            if not (l:=segment_cx.get(x)):
                segment_cx[x] = {seg}
            else:
                l.add(seg)
        for y in range(min_cy, max_cy + 1):
            if not (l:=segment_cy.get(y)):
                segment_cy[y] = {seg}
            else:
                l.add(seg)

        node1 = node2

def _remove_node_with_segments(
    node: wire_node,
    adj_node1: wire_node,
    seg1: wire_segment,
    adj_node2: wire_node,
    seg2: wire_segment,
    segment_cx: dict[int, set[wire_segment]], 
    segment_cy: dict[int, set[wire_segment]],
    wire_node_grid: dict[tuple[int, int], set[wire_node]],
    /) -> None:
    n_cx = node.cx; n_cy = node.cy

    (l:=wire_node_grid[cell:=(n_cx, n_cy)]).remove(node)
    if not l: del wire_node_grid[cell]

    min_cx = n_cx; max_cx = adj_node1.cx
    min_cy = n_cy; max_cy = adj_node1.cy

    if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
    if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

    for x in range(min_cx, max_cx + 1):
        (l:=segment_cx[x]).remove(seg1)
        if not l: del segment_cx[x]
    for y in range(min_cy, max_cy + 1):
        (l:=segment_cy[y]).remove(seg1)
        if not l: del segment_cy[y]

    min_cx = n_cx; max_cx = adj_node2.cx
    min_cy = n_cy; max_cy = adj_node2.cy

    if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
    if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

    for x in range(min_cx, max_cx + 1):
        (l:=segment_cx[x]).remove(seg2)
        if not l: del segment_cx[x]
    for y in range(min_cy, max_cy + 1):
        (l:=segment_cy[y]).remove(seg2)
        if not l: del segment_cy[y]

def _insert_node_with_segments(
    node: wire_node,
    adj_node1: wire_node,
    seg1: wire_segment,
    adj_node2: wire_node,
    seg2: wire_segment,
    segment_cx: dict[int, set[wire_segment]], 
    segment_cy: dict[int, set[wire_segment]],
    wire_node_grid: dict[tuple[int, int], set[wire_node]],
    /) -> None:
    n_cx = node.cx; n_cy = node.cy

    if not (l:=wire_node_grid.get(cell:=(n_cx, n_cy))):
        wire_node_grid[cell] = {node}
    else:
        l.add(node)

    min_cx = n_cx; max_cx = adj_node1.cx
    min_cy = n_cy; max_cy = adj_node1.cy

    if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
    if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

    for x in range(min_cx, max_cx + 1):
        if not (l:=segment_cx.get(x)):
            segment_cx[x] = {seg1}
        else:
            l.add(seg1)
    for y in range(min_cy, max_cy + 1):
        if not (l:=segment_cy.get(y)):
            segment_cy[y] = {seg1}
        else:
            l.add(seg1)

    min_cx = n_cx; max_cx = adj_node2.cx
    min_cy = n_cy; max_cy = adj_node2.cy

    if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx 
    if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

    for x in range(min_cx, max_cx + 1):
        if not (l:=segment_cx.get(x)):
            segment_cx[x] = {seg2}
        else:
            l.add(seg2)
    for y in range(min_cy, max_cy + 1):
        if not (l:=segment_cy.get(y)):
            segment_cy[y] = {seg2}
        else:
            l.add(seg2)

def _delete_action(
    object_list: list[logic_object],
    node_list: list[wire_node],
    wire_list: list[wire],
    object_set: set[logic_object],
    wire_set: set[wire],

    PROP_MANAGER: _propagation_manager,

    logic_objects: list[logic_object],
    object_grid: dict[tuple[int, int], logic_object],
    wire_node_grid: dict[tuple[int, int], set[wire_node]],
    segment_cx: dict[int, set[wire_segment]],
    segment_cy: dict[int, set[wire_segment]],

    action_log: list, 
    log_depth: int,
    MAX_ACTION_LOG_LENGTH: int,

    __GATE = GATE_OBJECTS,
    __NO_OUTPUT = NO_OUTPUT_OBJECTS,
    __NO_INPUT = NO_INPUT_OBJECTS,
    __UPDATE_OBJECT_OUTPUT = _update_object_output,
    __REMOVE_SEGMENTS_AND_NODES = _remove_segments_and_nodes,
    __REMOVE_NODE_WITH_SEGMENTS = _remove_node_with_segments,
    __DELETE_SELECTION_ACTION = delete_selection_action, 
    /) -> None:
    cyclic_objects = PROP_MANAGER.cyclic_circuit_objs
    cyclic_circuits = PROP_MANAGER.cyclic_circuits
    cyclic_queue = PROP_MANAGER.cyclic_queue

    internal_wires = []
    node_action_data = []

    for n in node_list:
        seg1 = n.seg1; seg2 = n.seg2

        wr = seg1.wire

        nodes = wr.nodes
        segments = wr.segments

        idx = nodes.index(n)
        del nodes[idx]
        
        node_action_data.append(n)
        node_action_data.append(idx)

        n1 = nodes[idx-1]
        n2 = nodes[idx]

        if seg1.node1 is n2 or seg1.node2 is n2:
            seg1, seg2 = seg2, seg1

        __REMOVE_NODE_WITH_SEGMENTS(n, n1, seg1, n2, seg2, segment_cx, segment_cy, wire_node_grid)

        del segments[idx]

        if seg1.node1 is n: seg1.node1 = n2
        else: seg1.node2 = n2

        if n2.seg1 is seg2: n2.seg1 = seg1
        else: n2.seg2 = seg1

        min_cx = n1.cx; max_cx = n2.cx
        min_cy = n1.cy; max_cy = n2.cy

        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

        for x in range(min_cx, max_cx + 1):
            if not (l:=segment_cx.get(x)):
                segment_cx[x] = {seg1}
            else:
                l.add(seg1)
        for y in range(min_cy, max_cy + 1):
            if not (l:=segment_cy.get(y)):
                segment_cy[y] = {seg1}
            else:
                l.add(seg1)

    for wr in wire_list:
        tran_obj = wr.tran_obj
        recv_obj = wr.recv_obj

        tran_obj.outputs.remove(recv_obj)
        tran_obj.out_wires.remove(wr)

        recv_obj.inputs[idx:=wr.recv_idx] = recv_obj.in_wires[idx] = None
        
        __REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

        if recv_obj not in object_set: __UPDATE_OBJECT_OUTPUT(recv_obj)

    for obj in object_list:
        (l:=object_grid[obj.cell]).remove(obj)
        if not l: del object_grid[obj.cell]

        logic_objects.remove(obj)
        
        # wire deletion
        cls = obj.__class__
        is_gate = cls in __GATE

        if is_gate or cls in __NO_OUTPUT:
            objinputs = obj.inputs
            objinwires = obj.in_wires
            for i, inpt in enumerate(objinputs):
                if inpt and inpt not in object_set:
                    wr = objinwires[i]

                    inpt.out_wires.remove(wr)
                    inpt.outputs.remove(obj)

                    # adds the wire to the deletion action
                    if wr not in wire_set:
                        wire_list.append(wr)

                    objinputs[i] = objinwires[i] = None
                
                    __REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

        if is_gate and obj in cyclic_objects:
            for i, circuit in enumerate(cyclic_circuits):
                if obj in circuit:
                    del cyclic_circuits[i]
                    cyclic_objects -= circuit

                    for q in cyclic_queue:
                        if q in circuit:
                            __UPDATE_OBJECT_OUTPUT(q)
                            break

            if not cyclic_circuits:
                PROP_MANAGER.next_queue_update = None
        
        if is_gate or cls in __NO_INPUT:
            objoutputs = obj.outputs
            objoutwires = obj.out_wires

            i = 0
            length = len(objoutputs)
            while i < length:
                out = objoutputs[i]

                if out:
                    wr = objoutwires[i]

                    if out not in object_set:
                        out.in_wires[idx:=wr.recv_idx] = out.inputs[idx] = None

                        # adds the wire to the deletion action
                        if wr not in wire_set:
                            wire_list.append(wr)

                        del objoutputs[i]
                        del objoutwires[i]
                        length -= 1
                    else:
                        if wr not in wire_set:
                            internal_wires.append(wr)

                        i += 1

                    __REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                    if out not in object_set: __UPDATE_OBJECT_OUTPUT(out)

    if log_depth:
        del action_log[-log_depth:]
        log_depth = 0

    if len(action_log) > MAX_ACTION_LOG_LENGTH:
        del action_log[0]

    action_log.append(__DELETE_SELECTION_ACTION(object_list, object_set, node_action_data, wire_list, internal_wires))

def main(
    UPDATE_OBJECT_OUTPUT                = _update_object_output,
    UPDATE_END_NODES_INPUT_MODIFICATION = _update_end_nodes_input_modification,
    END_DRAG_ACTION                     = _end_drag_action,
    UPDATE_SEGMENTS_AND_NODES           = _update_segments_and_nodes,
    REMOVE_SEGMENTS_AND_NODES           = _remove_segments_and_nodes,
    INSERT_SEGMENTS_AND_NODES           = _insert_segments_and_nodes,
    CREATE_AND_INSERT_SEGMENTS          = _create_and_insert_segments,
    REMOVE_NODE_WITH_SEGMENTS           = _remove_node_with_segments,
    INSERT_NODE_WITH_SEGMENTS           = _insert_node_with_segments,
    DELETE_ACTION                       = _delete_action,
    /) -> None:
    # cached values
    DISPLAY_FLIP                = pygame.display.flip
    EVENT_GET                   = pygame.event.get
    KEY_GET_PRESSED             = pygame.key.get_pressed
    KEY_GET_JUST_PRESSED        = pygame.key.get_just_pressed
    
    TRUNC                       = trunc
    FLOOR                       = floor

    SURFACE                     = pygame.Surface
    SRCALPHA                    = pygame.SRCALPHA

    TIME                        = time.perf_counter
    SLEEP                       = time.sleep

    OR_GATE                     = OR_gate
    AND_GATE                    = AND_gate
    XOR_GATE                    = XOR_gate
    NOR_GATE                    = NOR_gate
    NAND_GATE                   = NAND_gate
    XNOR_GATE                   = XNOR_gate
    BUFFER                      = buffer
    NOT_GATE                    = NOT_gate

    TOGGLE                      = toggle_switch
    LIGHT                       = light
    HDISPLAY                    = horizontal_display
    VDISPLAY                    = vertical_display

    WIRE                        = wire
    WIRE_NODE                   = wire_node
    WIRE_SEG                    = wire_segment

    PLACER                      = object_placer
    ATTACHER                    = wire_attacher

    SELECTION                   = selection_area

    ATTACH_WIRE_ACTION          = attach_wire_action
    NODE_INSERTION_ACTION       = node_insertion_action
    PLACE_OBJECTS_ACTION        = place_objects_action
    FLIP_SWITCH_ACTION          = flip_switch_action
    MOVE_SELECTION_ACTION       = move_selection_action 
    ROTATE_SELECTION_ACTION     = rotate_selection_action
    DELETE_SELECTION_ACTION     = delete_selection_action 
    MODIFY_INPUT_COUNT_ACTION   = modify_input_count_action

    GATE                        = GATE_OBJECTS
    NO_INPUT                    = NO_INPUT_OBJECTS
    NO_OUTPUT                   = NO_OUTPUT_OBJECTS

    DROPDOWN_NULL_SELECTION     = dropdown.NULL_SELECTION


    NOTIF_SLIDE_INTO_PLACE      = notification.SLIDE_INTO_PLACE
    NOTIF_PAUSE                 = notification.PAUSE
    NOTIF_SLIDE_BACK            = notification.SLIDE_BACK

    FILE_NOT_INITIALIZED_ERR    = storage.FILE_NOT_INITIALIZED_ERROR
    FILE_UNSUPPORTED_VER_ERR    = storage.FILE_UNSUPPORTED_VERSION_ERROR

    INF                         = inf 
    NEG_INF                     = -inf 

    # from constants.py
    SIZES = OBJECT_SIZES
    HALF_SIZES = OBJECT_HALF_SIZES
    BOUNDS = OBJECT_BOUNDS
    HITBOXES = OBJECT_HITBOXES

    w, h = logic_gate.SIZES[8]
    GATE_DIAG2 = w*w + h*h

    NODE_POSITIONS = OBJECT_NODE_POSITIONS
    NODE_SELECT_RADIUS = node.SIZE[0]/2 + 5
    NODE_SELECT_RADIUS2 = NODE_SELECT_RADIUS*NODE_SELECT_RADIUS

    WIRE_NODE_RADIUS = wire_node.SIZE[0] / 2
    WIRE_NODE_SELECT_RADIUS = WIRE_NODE_RADIUS + 5
    WIRE_NODE_SELECT_RADIUS2 = WIRE_NODE_SELECT_RADIUS*WIRE_NODE_SELECT_RADIUS

    NODE_HOVER_PROX_RADIUS2 = sqrt(GATE_DIAG2) + NODE_SELECT_RADIUS
    NODE_HOVER_PROX_RADIUS2 *= NODE_HOVER_PROX_RADIUS2

    CREATE_WIRE_NODE_PROX2 = 49

    SLIDER_KNOB_RADIUS = slider.KNOB_SIZE[0] / 2
    SLIDER_KNOB_SELECT_RADIUS2 = (SLIDER_KNOB_RADIUS + 5)**2

    GUI_SCROLL_STEP = 20 

    # events
    KEYDOWN                     = pygame.KEYDOWN
    MOUSEBUTTONDOWN             = pygame.MOUSEBUTTONDOWN
    MOUSEBUTTONUP               = pygame.MOUSEBUTTONUP
    MOUSEMOTION                 = pygame.MOUSEMOTION
    MOUSEWHEEL                  = pygame.MOUSEWHEEL
    QUIT                        = pygame.QUIT
    TEXTINPUT                   = pygame.TEXTINPUT
    WINDOWRESIZED               = pygame.WINDOWRESIZED
 
    # keys
    K_2                         = pygame.K_2          # modify input count 
    K_3                         = pygame.K_3
    K_4                         = pygame.K_4
    K_5                         = pygame.K_5
    K_6                         = pygame.K_6
    K_7                         = pygame.K_7
    K_8                         = pygame.K_8

    K_W                         = pygame.K_w
    K_A                         = pygame.K_a
    K_S                         = pygame.K_s
    K_D                         = pygame.K_d

    K_C                         = pygame.K_c          # copy
    K_G                         = pygame.K_g          # grid snapping 
    K_N                         = pygame.K_n          # new save
    K_R                         = pygame.K_r          # rotation
    K_V                         = pygame.K_v          # paste
    K_Y                         = pygame.K_y          # redo
    K_Z                         = pygame.K_z          # undo | redo

    K_LSHIFT                    = pygame.K_LSHIFT     # swift movement | commands | additive selection (OR)
    K_RSHIFT                    = pygame.K_RSHIFT
    K_ESCAPE                    = pygame.K_ESCAPE     
    K_CTRL                      = pygame.K_LCTRL      # commands       | commands | toggle selection (XOR)
    K_BACKSPACE                 = pygame.K_BACKSPACE  # object deletion and text input
    K_DELETE                    = pygame.K_DELETE     # object deletion
    K_ENTER                     = pygame.K_RETURN     
    K_LEFT                      = pygame.K_LEFT       # text input traversal
    K_RIGHT                     = pygame.K_RIGHT      # text input traversal

    # initialization
    win_x = _win_x; win_y = _win_y
    hwx = _hwx; hwy =_hwy
    WINDOW = _WINDOW; WIN_BUFFER = _WIN_BUFFER

    RENDER_MANAGER = _RENDER_MANAGER

    SAVES_MANAGER = _SAVES_MANAGER

    GUI_MANAGER = _GUI_MANAGER

    PROP_MANAGER = _PROP_MANAGER
    CYCLIC_UPDATE_FREQ = PROP_MANAGER.CYCLIC_CIRCUIT_UPDATE_FREQUENCY
    cyclic_objects = PROP_MANAGER.cyclic_circuit_objs
    cyclic_circuits = PROP_MANAGER.cyclic_circuits
    cyclic_queue = PROP_MANAGER.cyclic_queue

    TARGET_FPS = min(pygame.display.get_current_refresh_rate(), 120.0)
    TARGET_DELAY = 1 / TARGET_FPS
    delta_time = TARGET_DELAY
    
    # from constants.py
    #SAVE_FILE_PATH = PATH_TO_SAVE_FILE 
    #initialize_file(SAVE_FILE_PATH)

    logic_objects: list[logic_object] = []
    GRID_CELL_SIZE = max(logic_gate.SIZES[8])
    INV_GRID_CELL_SIZE = 1 / GRID_CELL_SIZE
    object_grid = {} # spatial partitioning to avoid O(n) searching for large circuits
    wire_node_grid = {}
    segment_cx = {} # separate dicts for the cell x and cell y wires occupy
    segment_cy = {}

    cam_speed = 1000
    swift_multiplier = 4

    # from render.py
    TEXTURES_BY_F = render.TEXTURES_BY_FILE 
    CMPLT_TEXTURES = render.COMPLETE_TEXTURES
    RENDER = render.render

    def _transfer_game_state() -> tuple[tuple[float, float, float], list[logic_object], tuple[set[logic_object], set[wire_node], set[wire]]]:
        return (
            (cam_x, cam_y, zoom), 
            logic_objects, 
            (selected_obj_set, selected_node_set, selected_wire_set)
        )
        
    def _update_game_state(save_state: tuple | int,/) -> None:
        nonlocal \
            cam_x, cam_y, zoom, \
            logic_objects, \
            PROP_MANAGER, cyclic_objects, cyclic_circuits, cyclic_queue, \
            selected_obj_list, selected_obj_set, \
            selected_node_list, selected_node_set, \
            selected_wire_list, selected_wire_set, \
            drag_obj_x, drag_obj_y, drag_node_x, drag_node_y, \
            object_grid, wire_node_grid, segment_cx, segment_cy, \
            action_log, log_depth, \
            SAVES_INTERFACE
        
        (
            (cam_x, cam_y, zoom),
            logic_objects,
            (cyclic_objects, cyclic_circuits, cyclic_queue),
            (selected_obj_list, selected_node_list, selected_wire_list),
            (object_grid, wire_node_grid, segment_cx, segment_cy)
        )\
        = save_state
        
        PROP_MANAGER.cyclic_circuit_objs = cyclic_objects
        PROP_MANAGER.cyclic_circuits = cyclic_circuits
        PROP_MANAGER.cyclic_queue = cyclic_queue
        PROP_MANAGER.next_queue_update = None

        selected_obj_set.clear(); selected_obj_set.update(selected_obj_list)
        selected_node_set.clear(); selected_node_set.update(selected_node_list)
        selected_wire_set.clear(); selected_wire_set.update(selected_wire_list)

        drag_obj_x = [None] * len(selected_obj_list); drag_obj_y = drag_obj_x.copy()
        drag_node_x = [None] * len(selected_node_list); drag_node_y = drag_node_x.copy()

        action_log.clear()
        log_depth = 0
    
    config_values = load_config(cam_speed, swift_multiplier, PROP_MANAGER.CYCLIC_CIRCUIT_UPDATE_FREQUENCY, '', '')

    default_save_file = defualt_save = ''

    if config_values[0] == 1: # version
        _, cam_speed, swift_multiplier, CYCLIC_UPDATE_FREQ, default_save_file, defualt_save = config_values
        cam_speed = TRUNC(cam_speed) # convert to int
        CYCLIC_UPDATE_FREQ = TRUNC(CYCLIC_UPDATE_FREQ)
        PROP_MANAGER.CYCLIC_CIRCUIT_UPDATE_FREQUENCY = CYCLIC_UPDATE_FREQ

    if default_save_file:
        SAVES_MANAGER.opened_file_path = _path = os.path.join(DATA_DIR, default_save_file)

        result = storage.initialize_file(_path)
        if result is storage.FILE_NOT_INITIALIZED_ERROR or result is storage.FILE_UNSUPPORTED_VERSION_ERROR:
            SAVES_MANAGER.opened_file_path = None

    data_dir_files = behaviors.scan_data_dir()
    save_list = storage.list_saves(SAVES_MANAGER.opened_file_path) if SAVES_MANAGER.opened_file_path is not None else []

    bar_icons = []
    for cls in LOGIC_OBJECTS:
        bar_icons.append(side_bar_icon(CMPLT_TEXTURES[cls][cls.INPUT_DEFAULT], cls))

    SIDE_BAR = side_bar(0, 0, 300, win_y, True, bar_icons, (10, 10))

    OBJECT_PLACER = object_placer()

    SETTINGS_BUTTON         = button(win_x - 47, 3, None, None, True, TEXTURES_BY_F[SETTINGS_BUTTON_FILE], behaviors.open_settings)
    SAVES_BUTTON            = button(win_x - 47, 50, None, None, True, TEXTURES_BY_F[SAVE_BUTTON_FILE], behaviors.open_saves_interface)
    OPEN_BUTTON             = button(3, 3, None, None, False, TEXTURES_BY_F[ARROW_OPEN_FILE], behaviors.open_side_bar)
    CLOSE_BUTTON            = button(303, 3, None, None, True, TEXTURES_BY_F[ARROW_CLOSE_FILE], behaviors.close_side_bar)
    EXIT_BUTTON             = button(win_x - 47, 3, 45, 45, False, 'Exit', behaviors.close_interface)

    OPEN_BUTTON.ties        = (SIDE_BAR, CLOSE_BUTTON)
    CLOSE_BUTTON.ties       = (SIDE_BAR, OPEN_BUTTON)

    _NOTIF_WIDTH = 400
    _NOTIF_HEIGHT = 46
    _NOTIF_X = (win_x - _NOTIF_WIDTH) // 2
    _NOTIF_Y = -_NOTIF_HEIGHT - 10

    _NOTIF_SLIDE_DX = 0
    _NOTIF_SLIDE_DY = _NOTIF_HEIGHT + 20

    DELETE_SUCCESS_NOTIF    = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[SUCCESS_FILE], 'Deleted save ')
    RENAME_SUCCESS_NOTIF    = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[SUCCESS_FILE], 'Renamed save to ')
    LOAD_SUCCESS_NOTIF      = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[SUCCESS_FILE], 'Loaded save ')
    SAVE_SUCCESS_NOTIF      = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[SUCCESS_FILE], 'Updated save ')
    NEW_SAVE_SUCCESS_NOTIF  = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[SUCCESS_FILE], 'Added new save ')
    NEW_FILE_SUCCESS_NOTIF  = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[SUCCESS_FILE], 'Added new file ')

    DELETE_FAIL_NOTIF       = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to delete save ')
    RENAME_FAIL_NOTIF       = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to rename save ')
    LOAD_FAIL_NOTIF         = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to load save ')
    SAVE_FAIL_NOTIF         = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to update save ')
    NEW_SAVE_FAIL_NOTIF     = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to add save ')
    NEW_FILE_FAIL_NOTIF     = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to add file ')
    READ_FILE_FAIL_NOTIF    = notification(_NOTIF_X, _NOTIF_Y, _NOTIF_WIDTH, _NOTIF_HEIGHT, False, _NOTIF_SLIDE_DX, _NOTIF_SLIDE_DY, TEXTURES_BY_F[FAIL_FILE], 'Failed to read file ')


    # loaded save notif          checkmark/green
    # saved save notif           checkmark/green
    # deleted save notif         trash can
    # failed to load save notif  x/red
    # failed tp delete           x/red
    # failed to save             x/red
    # failed to rename           x/red
    # created new file notif     checkmark/green

    _LEFT_ALIGN             = interface.X_LEFT_ALIGN
    _RIGHT_ALIGN            = interface.X_RIGHT_ALIGN
    _TOP_ALIGN              = interface.Y_TOP_ALIGN
    _BOTTOM_ALIGN           = interface.Y_BOTTOM_ALIGN

    _COLUMN_A               = 80
    _TOP                    = 80
    _SLIDER_WIDTH           = 350
    _ROW_Y_OFFSET           = 80
    _SLIDER_LABEL_OFFSET    = 40

    _DROPDOWN_WIDTH         = 350
    _DROPDOWN_LABEL_OFFSET  = 35
    _DROPDOWN_MAX_HEIGHT    = 300

    _COLUMN_B               = _COLUMN_A + _SLIDER_WIDTH + 40
    _COLUMN_C               = _COLUMN_B + _DROPDOWN_WIDTH + 40

    SETTINGS_LABEL          = text_label(20, 20, False, 'Settings')
    SPEED_LABEL             = text_label(_COLUMN_A, _TOP, False, 'Camera movement speed')
    MULTIPLIER_LABEL        = text_label(_COLUMN_A, _TOP+_ROW_Y_OFFSET, False, 'Camera swift speed multiplier')
    CYCLIC_LABEL            = text_label(_COLUMN_A, _TOP+_ROW_Y_OFFSET*2, False, 'Cyclic circuit update frequency')
    FILE_LABEL              = text_label(_COLUMN_B, _TOP, False, 'Default opened saves file')
    SAVE_LABEL              = text_label(_COLUMN_C, _TOP, False, 'Default loaded save')

    RECT1                   = rect(_COLUMN_B - 15, 0, 2, win_y, False)

    SPEED_SLIDER            = slider(_COLUMN_A, _TOP+_SLIDER_LABEL_OFFSET, _SLIDER_WIDTH, False, cam_speed, 500, 2000, 100)
    MULTIPLIER_SLIDER       = slider(_COLUMN_A, _TOP+_ROW_Y_OFFSET+_SLIDER_LABEL_OFFSET, _SLIDER_WIDTH, False, swift_multiplier, 2, 8, .25)
    CYCLIC_SLIDER           = slider(_COLUMN_A, _TOP+_ROW_Y_OFFSET*2+_SLIDER_LABEL_OFFSET, _SLIDER_WIDTH, False, PROP_MANAGER.CYCLIC_CIRCUIT_UPDATE_FREQUENCY, 5, 60, 1)

    FILE_DROPDOWN           = dropdown(_COLUMN_B, _TOP+_DROPDOWN_LABEL_OFFSET, _DROPDOWN_WIDTH, None, False, data_dir_files, _DROPDOWN_MAX_HEIGHT)
    SAVE_DROPDOWN           = dropdown(_COLUMN_C, _TOP+_DROPDOWN_LABEL_OFFSET, _DROPDOWN_WIDTH, None, False, save_list, _DROPDOWN_MAX_HEIGHT)

    SETTINGS_INTERFACE = interface(
        0, 0, win_x, win_y, False,
        [
            SETTINGS_LABEL,
            SPEED_LABEL, SPEED_SLIDER,
            MULTIPLIER_LABEL, MULTIPLIER_SLIDER,
            CYCLIC_LABEL, CYCLIC_SLIDER,
            RECT1,
            FILE_LABEL, FILE_DROPDOWN,
            SAVE_LABEL, SAVE_DROPDOWN,
            EXIT_BUTTON,

        ],
        [
            (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_RIGHT_ALIGN, _TOP_ALIGN),
        ] 
    )

    _BUTTON_X_OFFSET = 5

    SAVES_LABEL = text_label(20, 20, False, 'Saves')
    SAVE_FILES_LABEL = text_label(_COLUMN_A, _TOP, False, 'Selected save file')

    FILE_NEW_BUTTON = button(None, None, None, None, False, 'New', behaviors.prompt_action_input)
    FILE_NEW_BUTTON.x = x = _COLUMN_A + _DROPDOWN_WIDTH + 15 - FILE_NEW_BUTTON.w

    SAVE_FILES_DROPDOWN = dropdown(_COLUMN_A, _TOP + _DROPDOWN_LABEL_OFFSET, x - _COLUMN_A - _BUTTON_X_OFFSET, None, False, data_dir_files.copy(), _DROPDOWN_MAX_HEIGHT)
    
    FILE_NEW_BUTTON.y = SAVE_FILES_DROPDOWN.y + (SAVE_FILES_DROPDOWN.h - FILE_NEW_BUTTON.h) / 2

    SAVE_LIST_LABEL = text_label(_COLUMN_B, _TOP, False, 'Available saves')
    SAVE_LIST = scrollable_list(_COLUMN_B, _TOP + _DROPDOWN_LABEL_OFFSET, win_x - _COLUMN_B - _COLUMN_A, win_y - (_TOP + _DROPDOWN_LABEL_OFFSET) * 2, False, save_list.copy())
    
    _BUTTON_Y = SAVE_LIST.y + SAVE_LIST.h + 20
    x = SAVE_LIST.x + SAVE_LIST.w
    DELETE_BUTTON = button(None, _BUTTON_Y, None, None, False, 'Delete', behaviors.confirm_save_action)
    DELETE_BUTTON.x = x = x - DELETE_BUTTON.w

    RENAME_BUTTON = button(None, _BUTTON_Y, None, None, False, 'Rename', behaviors.prompt_action_input)
    RENAME_BUTTON.x = x = x - RENAME_BUTTON.w - _BUTTON_X_OFFSET

    SAVE_BUTTON = button(None, _BUTTON_Y, None, None, False, 'Save', behaviors.confirm_save_action)
    SAVE_BUTTON.x = x = x - SAVE_BUTTON.w - _BUTTON_X_OFFSET

    LOAD_BUTTON = button(None, _BUTTON_Y, None, None, False, 'Load', behaviors.confirm_save_action)
    LOAD_BUTTON.x = x = x - LOAD_BUTTON.w - _BUTTON_X_OFFSET

    NEW_BUTTON = button(None, _BUTTON_Y, None, None, False, 'New', behaviors.prompt_action_input)
    NEW_BUTTON.x = x = x - NEW_BUTTON.w - _BUTTON_X_OFFSET

    DELETE_BUTTON.inactive = \
    RENAME_BUTTON.inactive = \
    LOAD_BUTTON.inactive = \
    SAVE_BUTTON.inactive = True

    if default_save_file: SAVE_FILES_DROPDOWN.selected = SAVE_FILES_DROPDOWN.options.index(default_save_file)

    SAVES_INTERFACE = interface(
        0, 0, win_x, win_y, False,
        [
            SAVES_LABEL,
            SAVE_FILES_LABEL, FILE_NEW_BUTTON, SAVE_FILES_DROPDOWN,
            SAVE_LIST_LABEL, SAVE_LIST,
            DELETE_BUTTON,
            RENAME_BUTTON,
            SAVE_BUTTON,
            LOAD_BUTTON,
            NEW_BUTTON,
            EXIT_BUTTON,
        ],
        [
            (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_LEFT_ALIGN, _TOP_ALIGN), (_LEFT_ALIGN, _TOP_ALIGN),
            (_RIGHT_ALIGN, _BOTTOM_ALIGN),
            (_RIGHT_ALIGN, _BOTTOM_ALIGN),
            (_RIGHT_ALIGN, _BOTTOM_ALIGN),
            (_RIGHT_ALIGN, _BOTTOM_ALIGN),
            (_RIGHT_ALIGN, _BOTTOM_ALIGN),
            (_RIGHT_ALIGN, _TOP_ALIGN),
        ] 
    )

    if SAVES_MANAGER.opened_file_path: 
        idx = data_dir_files.index(default_save_file)
        FILE_DROPDOWN.selected = idx
        SAVE_FILES_DROPDOWN.selected = idx

    HANDLE_WINDOW_RESIZE = behaviors.handle_window_resize
    RESET_SAVE_LIST = behaviors.reset_save_list
    INITIALIZE_FILE = storage.initialize_file
    LIST_SAVES = storage.list_saves

    _CONFIRM_PROMPT_WIDTH    = 350
    _CONFIRM_PROMPT_HEIGHT   = 125
    _CONFIRM_PROMPT_X        = (win_x - _CONFIRM_PROMPT_WIDTH) // 2
    _CONFIRM_PROMPT_Y        = (win_y - _CONFIRM_PROMPT_HEIGHT) // 2

    _INPUT_PROMPT_WIDTH      = 450
    _INPUT_PROMPT_HEIGHT     = 150
    _INPUT_PROMPT_X          = (win_x - _INPUT_PROMPT_WIDTH) // 2
    _INPUT_PROMPT_Y          = (win_y - _INPUT_PROMPT_HEIGHT) // 2
    
    _INPUT_WIDTH            = _INPUT_PROMPT_WIDTH - 60
    _INPUT_HEIGHT           = 30

    DELETE_NO_BUTTON        = button(None, None, 100, None, False, 'No', behaviors.cancel_save_action)
    DELETE_YES_BUTTON       = button(None, None, 100, None, False, 'Yes', behaviors.delete_save)
    DELETE_SAVE_PROMPT      = confirmation_prompt(_CONFIRM_PROMPT_X, _CONFIRM_PROMPT_Y, _CONFIRM_PROMPT_WIDTH, _CONFIRM_PROMPT_HEIGHT, False, 'Permanently delete this save?', DELETE_NO_BUTTON, DELETE_YES_BUTTON)

    RENAME_PROMPT_INPUT     = text_input(None, None, _INPUT_WIDTH, None, False)
    RENAME_CANCEL_BUTTON    = button(None, None, 100, None, False, 'Cancel', behaviors.cancel_action_input)
    RENAME_OK_BUTTON        = button(None, None, 100, None, False, 'Ok', behaviors.rename_save)
    RENAME_SAVE_PROMPT      = input_prompt(_INPUT_PROMPT_X, _INPUT_PROMPT_Y, _INPUT_PROMPT_WIDTH, _INPUT_PROMPT_HEIGHT, False, 'Enter a new name for this save.', RENAME_PROMPT_INPUT, RENAME_CANCEL_BUTTON, RENAME_OK_BUTTON)

    SAVE_NO_BUTTON          = button(None, None, 100, None, False, 'No', behaviors.cancel_save_action)
    SAVE_YES_BUTTON         = button(None, None, 100, None, False, 'Yes', behaviors.overwrite_save)
    SAVE_SAVE_PROMPT        = confirmation_prompt(_CONFIRM_PROMPT_X, _CONFIRM_PROMPT_Y, _CONFIRM_PROMPT_WIDTH, _CONFIRM_PROMPT_HEIGHT, False, 'Do you want to overwrite this save?', SAVE_NO_BUTTON, SAVE_YES_BUTTON)

    LOAD_NO_BUTTON          = button(None, None, 100, None, False, 'No', behaviors.cancel_save_action)
    LOAD_YES_BUTTON         = button(None, None, 100, None, False, 'Yes', behaviors.load_save)
    LOAD_SAVE_PROMPT        = confirmation_prompt(_CONFIRM_PROMPT_X, _CONFIRM_PROMPT_Y, _CONFIRM_PROMPT_WIDTH, _CONFIRM_PROMPT_HEIGHT, False, 'Do you want to load this save?\nAll unsaved work will be lost.', LOAD_NO_BUTTON, LOAD_YES_BUTTON)

    NEW_SAVE_PROMPT_INPUT   = text_input(None, None, _INPUT_WIDTH, None, False)
    NEW_SAVE_CANCEL_BUTTON  = button(None, None, 100, None, False, 'Cancel', behaviors.cancel_action_input)
    NEW_SAVE_OK_BUTTON      = button(None, None, 100, None, False, 'Ok', behaviors.new_save)
    NEW_SAVE_PROMPT         = input_prompt(_INPUT_PROMPT_X, _INPUT_PROMPT_Y, _INPUT_PROMPT_WIDTH, _INPUT_PROMPT_HEIGHT, False, 'Enter a name for this save.', NEW_SAVE_PROMPT_INPUT, NEW_SAVE_CANCEL_BUTTON, NEW_SAVE_OK_BUTTON)

    FILE_PROMPT_INPUT       = text_input(None, None, _INPUT_WIDTH, None, False)
    FILE_CANCEL_BUTTON      = button(None, None, 100, None, False, 'Cancel', behaviors.cancel_action_input)
    FILE_OK_BUTTON          = button(None, None, 100, None, False, 'Ok', behaviors.new_save_file)
    FILE_NAME_PROMPT        = input_prompt(_INPUT_PROMPT_X, _INPUT_PROMPT_Y, _INPUT_PROMPT_WIDTH, _INPUT_PROMPT_HEIGHT, False, 'Enter a name for this file.', FILE_PROMPT_INPUT, FILE_CANCEL_BUTTON, FILE_OK_BUTTON)
    
    FILE_NEW_BUTTON.ties = (FILE_NAME_PROMPT, GUI_MANAGER)
    DELETE_BUTTON.ties = (DELETE_SAVE_PROMPT, GUI_MANAGER)
    RENAME_BUTTON.ties = (RENAME_SAVE_PROMPT, GUI_MANAGER)
    SAVE_BUTTON.ties = (SAVE_SAVE_PROMPT, GUI_MANAGER)
    LOAD_BUTTON.ties = (LOAD_SAVE_PROMPT, GUI_MANAGER)
    NEW_BUTTON.ties = (NEW_SAVE_PROMPT, GUI_MANAGER)

    DELETE_NO_BUTTON.ties = (DELETE_SAVE_PROMPT, GUI_MANAGER)
    DELETE_YES_BUTTON.ties = (
        DELETE_SAVE_PROMPT, 
        SAVE_LIST, 
        GUI_MANAGER,
        SAVES_MANAGER,
        (
            LOAD_BUTTON,
            SAVE_BUTTON,
            RENAME_BUTTON,
            DELETE_BUTTON,
        ),
        storage.delete_save, 
        storage.FILE_NOT_INITIALIZED_ERROR,
        storage.FILE_UNSUPPORTED_VERSION_ERROR,
        storage.INVALID_IDENTIFIER_ERROR,
        DELETE_SUCCESS_NOTIF,
        DELETE_FAIL_NOTIF,
    )

    RENAME_CANCEL_BUTTON.ties = (RENAME_SAVE_PROMPT, GUI_MANAGER)
    RENAME_OK_BUTTON.ties = (
        RENAME_SAVE_PROMPT, 
        SAVE_LIST, 
        GUI_MANAGER, 
        SAVES_MANAGER, 
        storage.rename_save,
        storage.FILE_NOT_INITIALIZED_ERROR,
        storage.FILE_UNSUPPORTED_VERSION_ERROR,
        storage.INVALID_IDENTIFIER_ERROR,
        RENAME_SUCCESS_NOTIF,
        RENAME_FAIL_NOTIF,
    )

    SAVE_NO_BUTTON.ties = (SAVE_SAVE_PROMPT, GUI_MANAGER)
    SAVE_YES_BUTTON.ties = (
        SAVE_SAVE_PROMPT, 
        SAVE_LIST, 
        GUI_MANAGER, 
        SAVES_MANAGER,
        PROP_MANAGER,
        _transfer_game_state, 
        serial.serialize_current_state, 
        storage.store_save,
        storage.FILE_NOT_INITIALIZED_ERROR,
        storage.FILE_UNSUPPORTED_VERSION_ERROR,
        storage.INVALID_IDENTIFIER_ERROR,
        SAVE_SUCCESS_NOTIF,
        SAVE_FAIL_NOTIF,
    )

    LOAD_NO_BUTTON.ties = (LOAD_SAVE_PROMPT, GUI_MANAGER)
    LOAD_YES_BUTTON.ties = (
        LOAD_SAVE_PROMPT, 
        SAVE_LIST, 
        EXIT_BUTTON,
        GUI_MANAGER, 
        SAVES_MANAGER, 
        storage.load_save, 
        serial.deserialize_save, 
        _update_game_state,
        storage.FILE_NOT_INITIALIZED_ERROR,
        storage.FILE_UNSUPPORTED_VERSION_ERROR,
        storage.INVALID_IDENTIFIER_ERROR,
        serial.INVALID_DATA_ERROR,
        serial.UNSUPPORTED_VERSION_ERROR,
        LOAD_SUCCESS_NOTIF,
        LOAD_FAIL_NOTIF,
    )

    NEW_SAVE_CANCEL_BUTTON.ties = (NEW_SAVE_PROMPT, GUI_MANAGER)
    NEW_SAVE_OK_BUTTON.ties = (
        NEW_SAVE_PROMPT, 
        SAVE_LIST,
        SAVE_DROPDOWN,
        GUI_MANAGER, 
        SAVES_MANAGER, 
        PROP_MANAGER,
        _transfer_game_state, 
        serial.serialize_current_state, 
        storage.store_save,
        storage.FILE_NOT_INITIALIZED_ERROR,
        storage.FILE_UNSUPPORTED_VERSION_ERROR,
        storage.INVALID_IDENTIFIER_ERROR,
        SURFACE,
        NEW_SAVE_SUCCESS_NOTIF,
        NEW_SAVE_FAIL_NOTIF,
    )

    FILE_CANCEL_BUTTON.ties = (FILE_NAME_PROMPT, GUI_MANAGER)
    FILE_OK_BUTTON.ties = (
        FILE_NAME_PROMPT,
        SAVE_LIST,
        FILE_DROPDOWN,
        SAVE_FILES_DROPDOWN,
        GUI_MANAGER,
        SAVES_MANAGER,
        storage.FILE_NOT_INITIALIZED_ERROR,
        storage.FILE_UNSUPPORTED_VERSION_ERROR,
        SURFACE,
        INITIALIZE_FILE,
        LIST_SAVES,
        RESET_SAVE_LIST,
        NEW_FILE_SUCCESS_NOTIF,
        NEW_FILE_FAIL_NOTIF,
    )

    SETTINGS_BUTTON.ties = (SETTINGS_INTERFACE, SAVES_BUTTON, GUI_MANAGER, RENDER_MANAGER)
    SAVES_BUTTON.ties = (
        SAVES_INTERFACE, 
        SETTINGS_BUTTON, 
        (
            LOAD_BUTTON,
            SAVE_BUTTON,
            RENAME_BUTTON,
            DELETE_BUTTON,
        ),
        GUI_MANAGER, 
        RENDER_MANAGER
    )
    
    EXIT_BUTTON.ties = (
        SETTINGS_INTERFACE, 
        SAVES_INTERFACE,
        SAVE_LIST,
        (
            DELETE_SAVE_PROMPT,
            LOAD_SAVE_PROMPT,
            SAVE_SAVE_PROMPT,
        ),
        (
            FILE_NAME_PROMPT,
            NEW_SAVE_PROMPT,
            RENAME_SAVE_PROMPT,
        ),
        SETTINGS_BUTTON, 
        SAVES_BUTTON,
        GUI_MANAGER,
        RENDER_MANAGER
    )

    BUTTONS = [
        OPEN_BUTTON,
        CLOSE_BUTTON,
        SETTINGS_BUTTON, 
        SAVES_BUTTON,
        FILE_NEW_BUTTON,
        DELETE_BUTTON,
        RENAME_BUTTON,
        SAVE_BUTTON,
        LOAD_BUTTON,
        NEW_BUTTON,
        EXIT_BUTTON,
        DELETE_NO_BUTTON,
        DELETE_YES_BUTTON,
        RENAME_CANCEL_BUTTON,
        RENAME_OK_BUTTON,
        LOAD_NO_BUTTON,
        LOAD_YES_BUTTON,
        SAVE_NO_BUTTON,
        SAVE_YES_BUTTON,
        NEW_SAVE_CANCEL_BUTTON,
        NEW_SAVE_OK_BUTTON,
        FILE_CANCEL_BUTTON,
        FILE_OK_BUTTON,
    ]
    NOTIFICATIONS = [
        DELETE_SUCCESS_NOTIF,
        RENAME_SUCCESS_NOTIF,
        LOAD_SUCCESS_NOTIF,
        SAVE_SUCCESS_NOTIF,
        NEW_SAVE_SUCCESS_NOTIF,
        NEW_FILE_SUCCESS_NOTIF,
        DELETE_FAIL_NOTIF,
        RENAME_FAIL_NOTIF,
        LOAD_FAIL_NOTIF,
        SAVE_FAIL_NOTIF,
        NEW_SAVE_FAIL_NOTIF,
        NEW_FILE_FAIL_NOTIF,
        READ_FILE_FAIL_NOTIF,
    ]
    SLIDERS = [
        SPEED_SLIDER,
        MULTIPLIER_SLIDER,
        CYCLIC_SLIDER,
    ]
    DROPDOWNS = [
        FILE_DROPDOWN,
        SAVE_DROPDOWN,
        SAVE_FILES_DROPDOWN,
    ]
    TEXT_INPUTS = [
        RENAME_PROMPT_INPUT,
        NEW_SAVE_PROMPT_INPUT,
        FILE_PROMPT_INPUT,
    ]

    GUI_ELEMENTS = [
        SIDE_BAR,
        OBJECT_PLACER,
        CLOSE_BUTTON,
        OPEN_BUTTON,
        SETTINGS_BUTTON,
        SAVES_BUTTON,
        SETTINGS_INTERFACE,
            SETTINGS_LABEL,
            SPEED_LABEL, SPEED_SLIDER,
            MULTIPLIER_LABEL, MULTIPLIER_SLIDER,
            CYCLIC_LABEL, CYCLIC_SLIDER,
            RECT1,
            FILE_LABEL, FILE_DROPDOWN,
            SAVE_LABEL, SAVE_DROPDOWN,
        SAVES_INTERFACE,
            SAVES_LABEL,
            SAVE_FILES_LABEL, FILE_NEW_BUTTON, SAVE_FILES_DROPDOWN,
            SAVE_LIST_LABEL, SAVE_LIST,
            DELETE_BUTTON,
            RENAME_BUTTON,
            SAVE_BUTTON,
            LOAD_BUTTON,
            NEW_BUTTON,
        EXIT_BUTTON,
        DELETE_SAVE_PROMPT,
            DELETE_NO_BUTTON,
            DELETE_YES_BUTTON,
        RENAME_SAVE_PROMPT,
            RENAME_PROMPT_INPUT,
            RENAME_CANCEL_BUTTON,
            RENAME_OK_BUTTON,
        LOAD_SAVE_PROMPT,
            LOAD_NO_BUTTON,
            LOAD_YES_BUTTON,
        SAVE_SAVE_PROMPT,
            SAVE_NO_BUTTON,
            SAVE_YES_BUTTON,
        NEW_SAVE_PROMPT,
            NEW_SAVE_PROMPT_INPUT,
            NEW_SAVE_CANCEL_BUTTON,
            NEW_SAVE_OK_BUTTON,
        FILE_NAME_PROMPT,
            FILE_PROMPT_INPUT,
            FILE_CANCEL_BUTTON,
            FILE_OK_BUTTON,
        DELETE_SUCCESS_NOTIF,
        RENAME_SUCCESS_NOTIF,
        LOAD_SUCCESS_NOTIF,
        SAVE_SUCCESS_NOTIF,
        NEW_SAVE_SUCCESS_NOTIF,
        NEW_FILE_SUCCESS_NOTIF,
        DELETE_FAIL_NOTIF,
        RENAME_FAIL_NOTIF,
        LOAD_FAIL_NOTIF,
        SAVE_FAIL_NOTIF,
        NEW_SAVE_FAIL_NOTIF,
        NEW_FILE_FAIL_NOTIF,
        READ_FILE_FAIL_NOTIF,
    ]

    mouse_x = mouse_y = 0
    lmb = rmb = False

    snap_to_grid = True
    SNAP_RES = 12.5
    INV_SNAP = 1 / SNAP_RES
    HALF_SNAP = SNAP_RES / 2

    cam_x = cam_y = 0
    zoom = 1

    selected_obj_list: list[logic_object] = []
    selected_obj_set: set[logic_object] = set()

    selected_node_list: list[wire_node] = []
    selected_node_set: set[wire_node] = set()

    selected_wire_list: list[wire] = []
    selected_wire_set: set[wire] = set()
    # selected bounds 
    min_x_bound = max_x_bound = 0
    min_y_bound = max_y_bound = 0
    # drag offsets
    offset_x = offset_y = 0
    # exact positions of the selected objects to support grid snapping
    drag_obj_x = []; drag_obj_y = []
    drag_node_x = []; drag_node_y = []

    # keep track of user actions for undo/redo
    action_log = []
    log_depth = 0
    MAX_ACTION_LOG_LENGTH = 1000

    node_placement_log = []
    node_log_depth = 0

    copied_objects = []
    copied_wires = []

    pasted_objects = []
    pasted_wire_nodes = []
    root_indices = []

    selected_node = None

    wr_attacher = None

    # drag selection
    selection = None 

    # mouse clicks
    clicked_obj = None
    clicked_wire_node = None
    clicked_wire = None

    click_handled = False
    clicked_logic_element = False
    clicked_grid = False
    last_click_x = last_click_y = None
    last_click_time = None

    slider_drag_dx = None
    dragging_slider = None

    drag_uninitiated = True
    obj_action_data = []
    node_action_data = []

    if defualt_save and SAVES_MANAGER.opened_file_path is not None:
        idx = save_list.index(defualt_save)
        SAVE_DROPDOWN.selected = idx
        SAVE_LIST.selected = idx
        LOAD_YES_BUTTON.handle(LOAD_YES_BUTTON)

    # main loop
    active = True
    while active:
        frame_start = TIME()

        keys = KEY_GET_PRESSED()
        jkeys = KEY_GET_JUST_PRESSED()

        jlmb = rlmb = jrmb = jmmb = False
        zoom_change = None

        for event in EVENT_GET():
            t: pygame.Event = event.type
            if t == MOUSEMOTION: mouse_x, mouse_y = event.pos
            elif t == MOUSEBUTTONDOWN:
                if (b:=event.button) == 1: lmb = jlmb = True
                elif b == 2: jmmb = True
                elif b == 3: rmb = jrmb = True
            elif t == MOUSEBUTTONUP:
                if (b:=event.button) == 1: lmb = False; rlmb = True
                elif b == 3: rmb = False
            elif t == MOUSEWHEEL: zoom_change = event.y
            elif t == TEXTINPUT:
                if (txt_inpt:=GUI_MANAGER.focused_input):
                    txt_inpt.input = f'{(input:=txt_inpt.input)[:(idx:=txt_inpt.caret_idx)]}{event.text}{input[idx:]}'
                    txt_inpt.caret_idx += len(event.text)

                    txt_inpt.input_surf = txt_inpt.font.render(txt_inpt.input, True, txt_inpt.font_color)

            elif t == WINDOWRESIZED:
                old_wx = win_x; old_wy = win_y
                win_x, win_y = WINDOW.get_size()
                hwx = win_x * 0.5; hwy = win_y * 0.5
                WIN_BUFFER = SURFACE((win_x, win_y), SRCALPHA)

                if old_wy != win_y:
                    SIDE_BAR.surf = s = SURFACE((SIDE_BAR.w, win_y), SIDE_BAR.SRCAPLHA_FLAG)
                    s.fill(SIDE_BAR.color)

                HANDLE_WINDOW_RESIZE(
                    old_wx, old_wy,
                    win_x, win_y,
                    SETTINGS_BUTTON,
                    SAVES_BUTTON,
                    SETTINGS_INTERFACE,
                    SAVES_INTERFACE,
                    SAVE_LIST,
                    DELETE_SAVE_PROMPT,
                    RENAME_SAVE_PROMPT,
                    LOAD_SAVE_PROMPT,
                    SAVE_SAVE_PROMPT,
                    NEW_SAVE_PROMPT,
                    FILE_NAME_PROMPT,
                )

            elif t == QUIT: active = False

        SHIFT_DOWN = keys[K_LSHIFT] or keys[K_RSHIFT]
        CTRL_DOWN  = keys[K_CTRL]

        over_gui_element = True if GUI_MANAGER.open_interface else False 
        no_interface = not over_gui_element

        if (txt_inpt:=GUI_MANAGER.focused_input):
            if jkeys[K_BACKSPACE]:
                if CTRL_DOWN:
                    p = txt_inpt.caret_idx - 1
                    input = txt_inpt.input
                    if len(input) == p: p -= 1

                    while p > 0 and input[p] == ' ': p -= 1
                    while p > 0 and input[p] != ' ': p -= 1
                    txt_inpt.input = input[:p] + input[txt_inpt.caret_idx:]
                    txt_inpt.caret_idx = p
                else:
                    input = txt_inpt.input
                    p = txt_inpt.caret_idx
                    txt_inpt.input = input[:p-1] + input[p:]
                txt_inpt.caret_idx = max(txt_inpt.caret_idx - 1, 0)

                txt_inpt.input_surf = txt_inpt.font.render(txt_inpt.input, True, txt_inpt.font_color)
            
            if jkeys[K_LEFT]:
                if CTRL_DOWN:
                    p = txt_inpt.caret_idx
                    input = txt_inpt.input
                    if len(input) == p: p -= 1

                    while p > 0 and input[p] == ' ': p -= 1
                    while p > 0 and input[p] != ' ': p -= 1
                    txt_inpt.caret_idx = p
                else:
                    txt_inpt.caret_idx = max(txt_inpt.caret_idx - 1, 0)

            if jkeys[K_RIGHT]:
                if CTRL_DOWN:
                    p = txt_inpt.caret_idx
                    input = txt_inpt.input
                    l = len(input)

                    while p < l and input[p] == ' ': p += 1
                    while p < l and input[p] != ' ': p += 1
                    txt_inpt.caret_idx = p
                else:
                    txt_inpt.caret_idx = min(txt_inpt.caret_idx + 1, len(txt_inpt.input))

        # gui
        button_pressed = False
        focused = False
        for b in BUTTONS:
            if b.visible and not b.inactive and (b.x < mouse_x and mouse_x < b.x + b.w) and (b.y < mouse_y and mouse_y < b.y + b.h) : 
                b.hover = True
                over_gui_element = True

                if jlmb: 
                    b.handle(b)
                    button_pressed = True
                    break
            else:
                b.hover = False

        gui_jlmb = jlmb and not button_pressed

        if dragging_slider:
            if rlmb:
                dragging_slider = None
            else:
                x = mouse_x + slider_drag_dx
                
                rnge = dragging_slider.range
                count = dragging_slider.step_mark_count
                span = dragging_slider.w - 7

                if dragging_slider.step:
                    value = FLOOR((x - 4) * count / span + 0.5) * dragging_slider.step
                    if value > rnge:
                        value = rnge
                    elif value < 0:
                        value = 0
                        
                    dragging_slider.slider_x = value / rnge * span + 4
                else:
                    end = dragging_slider.w - 3
                    if x > end:
                        x = end
                    elif x < 4:
                        x = 4
                    dragging_slider.slider_x = x

                    value = (x-4) / span * rnge
                
                value += dragging_slider.min_value

                if dragging_slider.value != value:
                    dragging_slider.value = value
                    dragging_slider.update_label()

                if dragging_slider is SPEED_SLIDER:
                    cam_speed = value
                elif dragging_slider is MULTIPLIER_SLIDER:
                    swift_multipluer = value
                elif dragging_slider is CYCLIC_SLIDER:
                    PROP_MANAGER.CYCLIC_CIRCUIT_UPDATE_FREQUENCY = CYCLIC_UPDATE_FREQ = value
                    PROP_MANAGER.next_queue_update = None

        elif gui_jlmb:
            for sldr in SLIDERS:
                if sldr.visible:
                    dx = mouse_x - (sldr.x + sldr.slider_x)
                    dy = mouse_y - (sldr.y + 3.5)

                    dst2 = dx*dx + dy*dy
                    if dst2 < SLIDER_KNOB_SELECT_RADIUS2:
                        dragging_slider = sldr
                        slider_drag_dx = sldr.slider_x - mouse_x
                        
                        break

        for drop in DROPDOWNS:
            if drop.visible:
                if drop.open:
                    if (drop.x <= mouse_x and mouse_x <= drop.x + drop.w) and (drop.y <= mouse_y and mouse_y <= drop.y + drop.open_h):
                        if zoom_change and drop.scrollable:
                            drop.scroll = scroll = drop.scroll - GUI_SCROLL_STEP * zoom_change

                            if scroll < 0:
                                drop.scroll = 0
                            elif scroll > drop.max_scroll:
                                drop.scroll = drop.max_scroll

                        if gui_jlmb:
                            idx = TRUNC((mouse_y + drop.scroll - drop.y + drop.border_thickness//2) // drop.option_h)

                            if idx > 0:
                                selected = drop.selected
                                if selected is DROPDOWN_NULL_SELECTION:
                                    drop.selected = idx - 1
                                elif idx < len(drop.options):
                                    if idx <= selected:
                                        drop.selected = idx - 1
                                    else:
                                        drop.selected = idx
                                else:
                                    drop.selected = DROPDOWN_NULL_SELECTION
                                
                                if drop.selected != selected:
                                    if drop is FILE_DROPDOWN:
                                        SAVE_DROPDOWN.selected = DROPDOWN_NULL_SELECTION

                                        if drop.selected is DROPDOWN_NULL_SELECTION:
                                            saves = []
                                        else:
                                            file_name = drop.options[drop.selected]
                                            SAVES_MANAGER.update_default_path(file_name)
                                            p = SAVES_MANAGER.default_opened_file_path

                                            saves = LIST_SAVES(p)
                                            if saves is FILE_NOT_INITIALIZED_ERR:
                                                INITIALIZE_FILE(p)
                                                saves = LIST_SAVES(p)

                                            if saves is FILE_UNSUPPORTED_VER_ERR or saves is FILE_NOT_INITIALIZED_ERR: 
                                                READ_FILE_FAIL_NOTIF.ani_start(f'\'{file_name}\'')
                                                saves = []

                                        option_count = len(saves)

                                        if option_count < len(SAVE_DROPDOWN.options) or not SAVE_DROPDOWN.scrollable:
                                            max_height = SAVE_DROPDOWN.max_height
                                            option_h = SAVE_DROPDOWN.option_h
                                            w = SAVE_DROPDOWN.w
                                            brdr = SAVE_DROPDOWN.border_thickness

                                            brdr_color = SAVE_DROPDOWN.border_color

                                            h = SAVE_DROPDOWN.h + option_count * option_h
                                            if h > max_height:
                                                SAVE_DROPDOWN.open_h = h = ((max_height - brdr) // option_h + 2) * option_h + brdr

                                                SAVE_DROPDOWN.max_scroll = option_h * (option_count + 1) - max_height
                                                SAVE_DROPDOWN.scrollable = True
                                            else:
                                                SAVE_DROPDOWN.open_h = h
                                                SAVE_DROPDOWN.scrollable = False
                                                SAVE_DROPDOWN.scroll = 0
                                            
                                            SAVE_DROPDOWN.open_surf = surf = SURFACE((w, h))

                                            surf.fill(brdr_color)
                                            surf.fill(SAVE_DROPDOWN.color, (brdr, brdr, w - brdr*2, h - brdr*2))

                                            for i in range(option_h, h, option_h):
                                                surf.fill(brdr_color, (0, i, w, brdr))

                                        SAVE_DROPDOWN.options = saves

                                        font = SAVE_DROPDOWN.font
                                        font_color = SAVE_DROPDOWN.font_color
                                        max_len = SAVE_DROPDOWN.max_option_len
                                        ellipsis_len, _ = font.size('...')

                                        SAVE_DROPDOWN.option_surfs = surfs = []
                                        for name in saves:
                                            if len(name) > 255: name = name[:255]

                                            w, _ = font.size(name)
                                            
                                            if w > max_len:
                                                while w > max_len:
                                                    name = name[:-1]
                                                    w, _ = font.size(name)
                                                    w += ellipsis_len
                                                
                                                name += '...'

                                            surfs.append(font.render(name, True, font_color))


                                    elif drop is SAVE_FILES_DROPDOWN:
                                        if drop.selected is DROPDOWN_NULL_SELECTION:
                                            RESET_SAVE_LIST(SAVE_LIST, [])
                                        else:
                                            file_name = drop.options[drop.selected]
                                            SAVES_MANAGER.update_opened_path(file_name)
                                            p = SAVES_MANAGER.opened_file_path
                                            
                                            saves = LIST_SAVES(p)
                                            if saves is FILE_NOT_INITIALIZED_ERR:
                                                INITIALIZE_FILE(p)
                                                saves = LIST_SAVES(p)

                                            if saves is FILE_UNSUPPORTED_VER_ERR or saves is FILE_NOT_INITIALIZED_ERR:
                                                saves = []
                                                READ_FILE_FAIL_NOTIF.ani_start(f'\'{file_name}\'')
                                            
                                            RESET_SAVE_LIST(SAVE_LIST, saves)

                            drop.open = False
                        
                
                elif (drop.x <= mouse_x and mouse_x <= drop.x + drop.w) and (drop.y <= mouse_y and mouse_y <= drop.y + drop.h):
                    if gui_jlmb: drop.open = True

        for inpt in TEXT_INPUTS:
            if inpt.visible and gui_jlmb and (inpt.x <= mouse_x and mouse_x <= inpt.x + inpt.w) and (inpt.y <= mouse_y and mouse_y <= inpt.y + inpt.h):
                GUI_MANAGER.focused_input = inpt

                inpt.focused = True

        if SAVE_LIST.visible and not GUI_MANAGER.active_prompt:
            if (SAVE_LIST.x <= mouse_x and mouse_x <= SAVE_LIST.x + SAVE_LIST.w) and \
                (SAVE_LIST.y <= mouse_y and mouse_y <= SAVE_LIST.y + SAVE_LIST.h):
                over_gui_element = True

                if SAVE_LIST.scrollable and zoom_change:
                    SAVE_LIST.scroll = scroll = SAVE_LIST.scroll - GUI_SCROLL_STEP * zoom_change

                    if scroll < 0:
                        SAVE_LIST.scroll = 0
                    elif scroll > SAVE_LIST.max_scroll:
                        SAVE_LIST.scroll = SAVE_LIST.max_scroll

                idx = TRUNC((mouse_y + SAVE_LIST.scroll - SAVE_LIST.y) // SAVE_LIST.item_height)

                if idx < len(SAVE_LIST.items):
                    SAVE_LIST.hover = idx

                    if gui_jlmb:
                        if ((y:=SAVE_LIST.y + SAVE_LIST.item_height * idx - SAVE_LIST.scroll) <= mouse_y and mouse_y <= y + SAVE_LIST.item_height):
                            SAVE_LIST.selected = idx
                            DELETE_BUTTON.inactive = \
                            RENAME_BUTTON.inactive = \
                            LOAD_BUTTON.inactive = \
                            SAVE_BUTTON.inactive = False
                        else:
                            SAVE_LIST.selected = None
                            DELETE_BUTTON.inactive = \
                            RENAME_BUTTON.inactive = \
                            LOAD_BUTTON.inactive = \
                            SAVE_BUTTON.inactive = True
                else:
                    SAVE_LIST.hover = None
            else:
                SAVE_LIST.hover = None

                if gui_jlmb:                
                    SAVE_LIST.selected = None
                    DELETE_BUTTON.inactive = \
                    RENAME_BUTTON.inactive = \
                    LOAD_BUTTON.inactive = \
                    SAVE_BUTTON.inactive = True     

        for notif in NOTIFICATIONS:
            if notif.visible:
                if (state:=notif.state) is NOTIF_SLIDE_INTO_PLACE:
                    dx = notif.slide_dx; dy = notif.slide_dy
                    dest_x = notif.start_x + dx; dest_y = notif.start_y + dy

                    factor = 20 * delta_time
                    notif.x += (dest_x - notif.x) * factor
                    notif.y += (dest_y - notif.y) * factor

                    if ((dx >= 0 and notif.x > dest_x - 0.01) or (dx < 0 and notif.x < dest_x + 0.01)) and \
                        ((dy >= 0 and notif.y > dest_y - 0.01) or (dy < 0 and notif.y < dest_y + 0.01)):
                        notif.x = dest_x; notif.y = dest_y
                        notif.pause_start = frame_start
                        notif.state = NOTIF_PAUSE

                elif state is NOTIF_PAUSE:
                    if frame_start - notif.pause_start > notif.duration:
                        notif.state = NOTIF_SLIDE_BACK

                elif state is NOTIF_SLIDE_BACK:
                    dest_x = notif.start_x; dest_y = notif.start_y

                    factor = 20 * delta_time
                    notif.x += (dest_x - notif.x) * factor
                    notif.y += (dest_y - notif.y) * factor

                    if (((dx:=notif.slide_dx) < 0 and notif.x > dest_x - 0.01) or (dx >= 0 and notif.x < dest_x + 0.01)) and \
                        (((dy:=notif.slide_dy) < 0 and notif.y > dest_y - 0.01) or (dy >= 0 and notif.y < dest_y + 0.01)):
                        notif.x = dest_x; notif.y = dest_y
                        notif.visible = False

        SIDE_BAR.hover_icon = None
        if no_interface and SIDE_BAR.visible and (SIDE_BAR.x <= mouse_x and mouse_x <= SIDE_BAR.x + SIDE_BAR.w) and \
            (SIDE_BAR.y <= mouse_y and mouse_y <= SIDE_BAR.y + SIDE_BAR.h):
            over_gui_element = True
            
            if not OBJECT_PLACER.active:
                x = SIDE_BAR.x + 10; y = SIDE_BAR.y + 10
                rects = SIDE_BAR.rects
                for i, (_x, _y, w, h) in enumerate(rects):
                    if ((dx:=x + _x) <= mouse_x and mouse_x <= dx + w) and ((oy:=y + _y) <= mouse_y and mouse_y <= oy + h):
                        SIDE_BAR.hover_icon = SIDE_BAR.icons[i]
                        break
        
        if not over_gui_element and zoom_change is not None: 
            zoom = min(zoom * 1.1**(zoom_change*swift_multiplier if SHIFT_DOWN else zoom_change), 5.559917)

        inv_zoom = 1 / zoom
        
        # cyclic circuit queue
        if cyclic_queue:
            if (next_update:=PROP_MANAGER.next_queue_update) is None:
                PROP_MANAGER.next_queue_update = next_update = FLOOR((frame_start) * CYCLIC_UPDATE_FREQ) + 1

            if frame_start * CYCLIC_UPDATE_FREQ > next_update:
                this_prop_inst = object()
                PROP_MANAGER.next_queue_update += 1

                next_queue = []

                for obj in cyclic_queue:
                    obj.prop_inst = this_prop_inst
            
                    if (cls:=obj.__class__) is OR_GATE:
                        output = False
                        for o in obj.inputs:
                            if o and o.output:
                                output = True
                                break
                    elif cls is AND_GATE:
                        output = True
                        for o in obj.inputs:
                            if not (o and o.output):
                                output = False
                                break
                    elif cls is XOR_GATE:
                        output = False
                        for o in obj.inputs:
                            if o and o.output: output = not output
                    elif cls is NOR_GATE:
                        output = True
                        for o in obj.inputs:
                            if o and o.output:
                                output = False
                                break
                    elif cls is NAND_GATE:
                        output = False
                        for o in obj.inputs:
                            if not (o and o.output):
                                output = True
                                break
                    elif cls is XNOR_GATE:
                        output = True
                        for o in obj.inputs:
                            if o and o.output: output = not output
                    elif cls is BUFFER:
                        output = inpt.output if (inpt:=obj.inputs[0]) is not None else False 
                    elif cls is NOT_GATE:
                        output = (not inpt.output) if (inpt:=obj.inputs[0]) is not None else True

                    unupdated_queue = True

                    if output is not obj.output:
                        obj.output = output
                        for wr in obj.out_wires: wr.signal = output

                        for out in obj.outputs:
                            if out in cyclic_objects:
                                next_queue.append(out)
                                unupdated_queue = False
                            elif output is not out.output:
                                UPDATE_OBJECT_OUTPUT(out)
                    
                    if unupdated_queue:
                        for i, circuit in enumerate(cyclic_circuits):
                            if obj in circuit:
                                del cyclic_circuits[i]
                                cyclic_objects -= circuit

                        if not cyclic_circuits:
                            PROP_MANAGER.next_queue_update = None
                            
                PROP_MANAGER.cyclic_queue = cyclic_queue = next_queue
 
        # camera movement
        if no_interface:
            scaled_speed = (cam_speed * swift_multiplier if SHIFT_DOWN else cam_speed) * delta_time * inv_zoom
            if keys[K_W]:
                cam_y -= scaled_speed
            elif keys[K_S]:
                cam_y += scaled_speed
            if keys[K_A]:
                cam_x -= scaled_speed
            elif keys[K_D]:
                cam_x += scaled_speed

        mx = (mouse_x - hwx)*inv_zoom + cam_x; my = (mouse_y - hwy)*inv_zoom + cam_y

        near_node = None
        if not over_gui_element:
            cx = FLOOR(mx * INV_GRID_CELL_SIZE); cy = FLOOR(my * INV_GRID_CELL_SIZE)
            min_dst = INF
            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    if (l:=object_grid.get((cx+ox,cy+oy))):
                        for obj in l:
                            dx = mx - obj.x; dy = my - obj.y
                            dst = dx*dx + dy*dy

                            if dst < NODE_HOVER_PROX_RADIUS2:
                                nodes = NODE_POSITIONS[obj.__class__][obj.orient][obj.input_count]

                                for i, (x, y) in enumerate(nodes):
                                    _dx = x - dx; _dy = y - dy
                                    dst2 = _dx*_dx + _dy*_dy

                                    if dst2 < NODE_SELECT_RADIUS2 and dst2 < min_dst:
                                        near_node = (obj, i)
                                        min_dst = dst2
        
        # determine whether or not to add a move selection action
        if rlmb and not drag_uninitiated:
            drag_uninitiated = True

            END_DRAG_ACTION(selected_obj_list, selected_node_list, obj_action_data, node_action_data, action_log, log_depth, MAX_ACTION_LOG_LENGTH)
            log_depth = 0

            obj_action_data = []
            node_action_data = []

        if jlmb or jmmb:
            if jlmb:
                last_click_time = frame_start

                if SIDE_BAR.hover_icon:
                    cls = SIDE_BAR.hover_icon.cls
                    OBJECT_PLACER.reset(mx, my, cls, (ic:=cls.INPUT_DEFAULT), HALF_SIZES[cls][ic])

                clicked_obj = clicked_wire_node = clicked_wire = None
                last_click_x = mouse_x; last_click_y = mouse_y
                clicked_grid = not (over_gui_element or near_node)
                clicked_logic_element = False
                lmb_was_click = True

            if clicked_grid or jmmb:
                terminate = False
                cx = FLOOR(mx * INV_GRID_CELL_SIZE); cy = FLOOR(my * INV_GRID_CELL_SIZE)
                for oy in (-1, 0, 1): 
                    for ox in (-1, 0, 1):
                        if (l:=object_grid.get((cx+ox,cy+oy))):
                            for obj in l:
                                bx, by, bw, bh = BOUNDS[cls:=obj.__class__][0][ic:=obj.input_count]

                                if (o:=obj.orient) == 0:
                                    rx = mx - obj.x; ry = my - obj.y
                                elif o == 1:
                                    w, _ = SIZES[cls][ic]
                                    rx = obj.y - my + w; ry = mx - obj.x 
                                elif o == 2:
                                    w, h = SIZES[cls][ic]
                                    rx = obj.x - mx + w; ry = obj.y - my + h
                                else:
                                    _, h = SIZES[cls][ic]
                                    rx = my - obj.y; ry = obj.x - mx + h

                                if (bx <= rx and rx <= bx+bw) and (by <= ry and ry <= by+bh):
                                    hitbox = HITBOXES[cls][ic]
                                    inside = False

                                    x1, y1 = hitbox[-1]
                                    for x2, y2 in hitbox: # ray-casting point-in-polygon detection algorithm
                                        if (rx <= x1) is not (rx <= x2) and \
                                        (((a:=ry <= y1) & (b:=ry <= y2)) or (a is not b and ((x1 < x2 and (y1 - y2)*(x1 - rx) > (x1 - x2)*(y1 - ry)) or (x1 > x2 and (y1 - y2)*(x1 - rx) < (x1 - x2)*(y1 - ry))))):
                                            inside = not inside
                                        
                                        x1 = x2; y1 = y2

                                    if inside:
                                        clicked_obj = obj
                                        click_handled = clicked_grid = False
                                        clicked_logic_element = True

                                        if selected_obj_list or selected_node_list:
                                            if selected_obj_list:
                                                obj = selected_obj_list[0]
                                                offset_x = obj.x - mx; offset_y = obj.y - my
                                            else:
                                                n = selected_node_list[0]
                                                offset_x = n.x - mx; offset_y = n.y - my

                                            for i, obj in enumerate(selected_obj_list):
                                                drag_obj_x[i] = obj.x
                                                drag_obj_y[i] = obj.y

                                            for i, n in enumerate(selected_node_list):
                                                drag_node_x[i] = n.x
                                                drag_node_y[i] = n.y
                                        terminate = True
                                        break

                        if terminate: break
                    if terminate: break

                if not clicked_obj:
                    cx = FLOOR(mx * INV_GRID_CELL_SIZE); cy = FLOOR(my * INV_GRID_CELL_SIZE)

                    min_dst = INF
                    for oy in (-1, 0, 1): 
                        for ox in (-1, 0, 1):
                            if (l:=wire_node_grid.get((cx+ox,cy+oy))):
                                for n in l:
                                    dx = n.x - mx; dy = n.y - my 
                                    dst2 = dx*dx + dy*dy

                                    if dst2 < WIRE_NODE_SELECT_RADIUS2 and dst2 < min_dst:
                                        clicked_wire_node = n
                                        click_handled = clicked_grid = False
                                        clicked_logic_element = True
                                        min_dst = dst2
                    
                    if clicked_wire_node and (selected_obj_list or selected_node_list):
                        if selected_obj_list:
                            obj = selected_obj_list[0]
                            offset_x = obj.x - mx; offset_y = obj.y - my
                        else:
                            n = selected_node_list[0]
                            offset_x = n.x - mx; offset_y = n.y - my

                        for i, obj in enumerate(selected_obj_list):
                            drag_obj_x[i] = obj.x
                            drag_obj_y[i] = obj.y

                        for i, n in enumerate(selected_node_list):
                            drag_node_x[i] = n.x
                            drag_node_y[i] = n.y

                if not (clicked_obj or clicked_wire_node):
                    cx = FLOOR(mx * INV_GRID_CELL_SIZE); cy = FLOOR(my * INV_GRID_CELL_SIZE)

                    x_segs = segment_cx.get(cx); y_segs = segment_cy.get(cy)

                    if x_segs and y_segs:
                        for seg in x_segs:
                            if seg in y_segs:
                                n1x = (n1:=seg.node1).x; n1y = n1.y
                                n2x = (n2:=seg.node2).x; n2y = n2.y

                                dx = n2x - n1x; dy = n2y - n1y

                                length2 = dx*dx + dy*dy
                                if length2 > 0:
                                    t = (dx*(mx - n1x) + dy*(my - n1y)) / length2
                                    if t > 1: t = 1  # clamp to the segments ends
                                    elif t < 0: t = 0

                                    x = n1x + t*dx
                                    y = n1y + t*dy
                                else:
                                    x = n1x
                                    y = n1y

                                dx = mx - x; dy = my - y

                                if dx*dx + dy*dy < CREATE_WIRE_NODE_PROX2:
                                    clicked_wire = seg.wire
                                    click_handled = clicked_grid = False

            if jmmb and (clicked_obj or clicked_wire_node or clicked_wire):
                if clicked_obj:
                    obj_list = [clicked_obj]
                    node_list = wire_list = empty = []
                    clicked_obj = None
                elif clicked_wire_node:
                    node_list = [clicked_wire_node]
                    obj_list = wire_list = empty = []
                    clicked_wire_node = None
                elif clicked_wire:
                    wire_list = [clicked_wire]
                    obj_list = node_list = empty = []
                    clicked_wire = None

                DELETE_ACTION(
                    obj_list,
                    node_list,
                    wire_list,
                    empty,
                    empty,
                    PROP_MANAGER,
                    logic_objects,
                    object_grid,
                    wire_node_grid,
                    segment_cx, segment_cy,
                    action_log,
                    log_depth,
                    MAX_ACTION_LOG_LENGTH
                )

                log_depth = 0

            if SHIFT_DOWN:
                if clicked_obj and clicked_obj not in selected_obj_set:
                    if not selected_obj_list:
                        offset_x = clicked_obj.x - mx; offset_y = clicked_obj.y - my

                    selected_obj_set.add(clicked_obj); selected_obj_list.append(clicked_obj)
                    drag_obj_x.append(clicked_obj.x); drag_obj_y.append(clicked_obj.y)

                    if clicked_obj.orient & 1:
                        h, w = SIZES[clicked_obj.__class__][clicked_obj.input_count]
                    else:
                        w, h = SIZES[clicked_obj.__class__][clicked_obj.input_count]

                    if (x:=clicked_obj.x) < min_x_bound: min_x_bound = x
                    if (y:=clicked_obj.y) < min_y_bound: min_y_bound = y
                    if x + w > max_x_bound: max_x_bound = x + w
                    if y + h > max_y_bound: max_y_bound = y + h

                elif clicked_wire_node and clicked_wire_node not in selected_node_set:
                    if not (selected_obj_list or selected_node_list):
                        offset_x = clicked_wire_node.x - mx; offset_y = clicked_wire_node.y - my

                    selected_node_set.add(clicked_wire_node); selected_node_list.append(clicked_wire_node)
                    drag_node_x.append(clicked_wire_node.x); drag_node_y.append(clicked_wire_node.y)

                    if (x:=clicked_wire_node.x) < min_x_bound: min_x_bound = x
                    elif x > max_x_bound: max_x_bound = x 
                    if (y:=clicked_wire_node.y) < min_y_bound: min_y_bound = y
                    elif y > max_y_bound: max_y_bound = y

                elif clicked_wire and clicked_wire not in selected_wire_set:
                    selected_wire_set.add(clicked_wire); selected_wire_list.append(clicked_wire)

                click_handled = True

            elif CTRL_DOWN:
                if clicked_obj:
                    if clicked_obj.orient & 1:
                        h, w = SIZES[clicked_obj.__class__][clicked_obj.input_count]
                    else:
                        w, h = SIZES[clicked_obj.__class__][clicked_obj.input_count]
                        
                    if clicked_obj in selected_obj_set:
                        selected_obj_set.remove(clicked_obj)
                        del selected_obj_list[idx:=selected_obj_list.index(clicked_obj)]
                        del drag_obj_x[idx]; del drag_obj_y[idx]

                        # recalculate bounds
                        if selected_obj_list or selected_node_list:
                            if clicked_obj.x - 0.01 <= min_x_bound:  # 0.01 offset to ensure no evaluation errors occur from floating point drift
                                for obj in selected_obj_list:
                                    if obj.x < min_x_bound: min_x_bound = obj.x
                                for n in selected_node_list:
                                    if n.x < min_x_bound: min_x_bound = n.x
                            if clicked_obj.x + w + 0.01 >= max_x_bound:
                                for obj in selected_obj_list:
                                    if obj.orient & 1: _, _w = SIZES[obj.__class__][obj.input_count]
                                    else: _w, _ = SIZES[obj.__class__][obj.input_count]
                                    if obj.x + _w > max_x_bound: max_x_bound = obj.x + _w
                                for n in selected_node_list:
                                    if n.x > max_x_bound: max_x_bound = n.x
                            if clicked_obj.y - 0.01 <= min_y_bound:
                                for obj in selected_obj_list:
                                    if obj.y < min_y_bound: min_y_bound = obj.y
                                for n in selected_node_list:
                                    if n.y < min_y_bound: min_y_bound = n.y
                            if clicked_obj.y + h + 0.01 >= max_y_bound:
                                for obj in selected_obj_list:
                                    if obj.orient & 1: _h, _ = SIZES[obj.__class__][obj.input_count]
                                    else: _, _h = SIZES[obj.__class__][obj.input_count]
                                    if obj.y + _h > max_y_bound: max_y_bound = obj.y + _h
                                for n in selected_node_list:
                                    if n.y > max_y_bound: max_y_bound = n.y           

                        clicked_grid = True
                        clicked_obj = None
                    else:
                        if not selected_obj_list:
                            offset_x = clicked_obj.x - mx; offset_y = clicked_obj.y - my

                        selected_obj_set.add(clicked_obj); selected_obj_list.append(clicked_obj)
                        drag_obj_x.append(clicked_obj.x); drag_obj_y.append(clicked_obj.y)

                        if (x:=clicked_obj.x) < min_x_bound: min_x_bound = x
                        if (y:=clicked_obj.y) < min_y_bound: min_y_bound = y
                        if x + w > max_x_bound: max_x_bound = x + w
                        if y + h > max_y_bound: max_y_bound = y + h

                elif clicked_wire_node:
                    if clicked_wire_node in selected_node_set:
                        selected_node_set.remove(clicked_wire_node)
                        del selected_node_list[idx:=selected_node_list.index(clicked_wire_node)]
                        del drag_node_x[idx]; del drag_node_y[idx]

                        # recalculate bounds
                        if selected_obj_list or selected_node_list:
                            if clicked_wire_node.x - 0.01 <= min_x_bound: # add 0.01 to ensure no evaluation errors occur from floating point drift
                                for obj in selected_obj_list:
                                    if obj.x < min_x_bound: min_x_bound = obj.x
                                for n in selected_node_list:
                                    if n.x < min_x_bound: min_x_bound = n.x
                            elif clicked_wire_node.x + 0.01 >= max_x_bound:
                                for obj in selected_obj_list:
                                    if obj.orient & 1: _, w = SIZES[obj.__class__][obj.input_count]
                                    else: w, _ = SIZES[obj.__class__][obj.input_count]
                                    if obj.x + w > max_x_bound: max_x_bound = obj.x + w
                                for n in selected_node_list:
                                    if n.x > max_x_bound: max_x_bound = n.x
                            if clicked_wire_node.y - 0.01 <= min_y_bound:
                                for obj in selected_obj_list:
                                    if obj.y < min_y_bound: min_y_bound = obj.y
                                for n in selected_node_list:
                                    if n.y < min_y_bound: min_y_bound = n.y
                            elif clicked_wire_node.y + 0.01 >= max_y_bound:
                                for obj in selected_obj_list:
                                    if obj.orient & 1: h, _ = SIZES[obj.__class__][obj.input_count]
                                    else: _, h = SIZES[obj.__class__][obj.input_count]
                                    if obj.y + h > max_y_bound: max_y_bound = obj.y + h
                                for n in selected_node_list:
                                    if n.y > max_y_bound: max_y_bound = n.y

                        clicked_grid = True
                        clicked_wire_node = None
                    else:
                        if not selected_obj_list:
                            offset_x = clicked_wire_node.x - mx; offset_y = clicked_wire_node.y - my

                        selected_node_set.add(clicked_wire_node); selected_node_list.append(clicked_wire_node)
                        drag_node_x.append(clicked_wire_node.x); drag_node_y.append(clicked_wire_node.y)

                        if (x:=clicked_wire_node.x) < min_x_bound: min_x_bound = x
                        elif x > max_x_bound: max_x_bound = x
                        if (y:=clicked_wire_node.y) < min_y_bound: min_y_bound = y
                        elif y > max_y_bound: max_y_bound = y

                elif clicked_wire:
                    if clicked_wire in selected_wire_set:
                        selected_wire_set.remove(clicked_wire); selected_wire_list.remove(clicked_wire)
                        clicked_wire = None
                    else:
                        selected_wire_set.add(clicked_wire); selected_wire_list.append(clicked_wire)

                click_handled = True

            elif not (clicked_obj or clicked_wire_node or clicked_wire) and clicked_grid: 
                selected_obj_list.clear(); selected_obj_set.clear() 
                selected_node_list.clear(); selected_node_set.clear()
                selected_wire_list.clear(); selected_wire_set.clear()
                drag_obj_x.clear(); drag_obj_y.clear()
                drag_node_x.clear(); drag_node_y.clear()

                click_handled = True

        if lmb and lmb_was_click:
            lmb_was_click = abs(last_click_x - mouse_x) < 4 and abs(last_click_y - mouse_y) < 4

        if clicked_obj and not click_handled and ((rlmb and lmb_was_click) or clicked_obj not in selected_obj_set):
            selected_node_list.clear(); selected_node_set.clear()
            selected_wire_list.clear(); selected_wire_set.clear()
            drag_node_x.clear(); drag_node_y.clear()

            selected_obj_set.clear(); selected_obj_set.add(clicked_obj)
            selected_obj_list = [clicked_obj]

            if clicked_obj.orient & 1:
                h, w = SIZES[clicked_obj.__class__][clicked_obj.input_count]
            else:
                w, h = SIZES[clicked_obj.__class__][clicked_obj.input_count]

            min_x_bound = clicked_obj.x; max_x_bound = min_x_bound + w
            min_y_bound = clicked_obj.y; max_y_bound = min_y_bound + h

            drag_obj_x = [min_x_bound]; drag_obj_y = [min_y_bound]

            offset_x = min_x_bound - mx; offset_y = min_y_bound - my

            click_handled = True

        elif clicked_wire_node and not click_handled and ((rlmb and lmb_was_click) or clicked_wire_node not in selected_node_set):
            selected_obj_list.clear(); selected_obj_set.clear() 
            selected_wire_list.clear(); selected_wire_set.clear()
            drag_obj_x.clear(); drag_obj_y.clear()

            selected_node_set.clear(); selected_node_set.add(clicked_wire_node)
            selected_node_list = [clicked_wire_node]
            
            min_x_bound = clicked_wire_node.x; max_x_bound = min_x_bound
            min_y_bound = clicked_wire_node.y; max_y_bound = min_y_bound
            
            drag_node_x = [min_x_bound]; drag_node_y = [min_y_bound]

            offset_x = min_x_bound - mx; offset_y = min_y_bound - my

            click_handled = True

        elif clicked_wire and not click_handled and ((rlmb and lmb_was_click) or clicked_wire not in selected_wire_set):
            selected_obj_list.clear(); selected_obj_set.clear() 
            selected_node_list.clear(); selected_node_set.clear()
            drag_obj_x.clear(); drag_obj_y.clear()
            drag_node_x.clear(); drag_node_y.clear()

            selected_wire_set.clear(); selected_wire_set.add(clicked_wire)
            selected_wire_list = [clicked_wire]

            click_handled = True

        if lmb and clicked_grid and not selection and (abs(last_click_x - mouse_x) > 4 or abs(last_click_y - mouse_y) > 4):
            selection = SELECTION(inv_zoom*(last_click_x - hwx) + cam_x, inv_zoom*(last_click_y - hwy) + cam_y, mx, my)
        
        if rlmb:
            if clicked_obj and rlmb and lmb_was_click and clicked_obj.__class__ is TOGGLE:
                clicked_obj.output = output = not clicked_obj.output
                for wr in clicked_obj.out_wires: wr.signal = output
                UPDATE_OBJECT_OUTPUT(clicked_obj)

                if log_depth:
                    del action_log[-log_depth:]
                    log_depth = 0

                if len(action_log) > MAX_ACTION_LOG_LENGTH:
                    del action_log[0]

                action_log.append(FLIP_SWITCH_ACTION(clicked_obj))

            clicked_obj = clicked_wire_node = clicked_wire = None

            # drag selection logic
            if selection:
                # reorder selection box points
                if (x1:=selection.x1) > (x2:=selection.x2): x1, x2 = x2, x1
                if (y1:=selection.y1) > (y2:=selection.y2): y1, y2 = y2, y1

                start_cx = FLOOR(x1 * INV_GRID_CELL_SIZE) - 1; end_cx = FLOOR(x2 * INV_GRID_CELL_SIZE)
                start_cy = FLOOR(y1 * INV_GRID_CELL_SIZE) - 1; end_cy = FLOOR(y2 * INV_GRID_CELL_SIZE)
                # these bounds bypass the rect check
                bp_start_cx = start_cx + 2; bp_start_cy = start_cy + 2 
                bp_end_cx = end_cx - 1; bp_end_cy = end_cy - 1

                right_end = end_cx + 1

                border_passes = (
                    (start_cx,  right_end,    start_cy,    bp_start_cy),   # top pass
                    (start_cx,  bp_start_cx,  bp_start_cy, bp_end_cy),     # left side pass
                    (bp_end_cx, right_end,    bp_start_cy, bp_end_cy),     # right side pass
                    (start_cx,  right_end,    bp_end_cy,   end_cy + 1)     # bottom pass
                )

                half_cell_area = (end_cx - start_cx + 1) * (end_cy - start_cy + 1) * 0.5

                selected_objs = []
                selected_nodes = []
                selected_wires = []

                visited_wires = set()

                # objects
                if len(object_grid) < half_cell_area:
                    for (cx, cy), l in object_grid.items():
                        if bp_start_cx <= cx and cx < bp_end_cx and bp_start_cy <= cy and cy < bp_end_cy: 
                            selected_objs += l
                        elif start_cx <= cx and cx <= end_cx and start_cy <= cy and cy <= end_cy:
                            for obj in l:
                                bx, by, bw, bh = BOUNDS[obj.__class__][obj.orient][obj.input_count]

                                if ((x:=obj.x + bx) + bw > x1 and x < x2) and ((y:=obj.y + by) + bh > y1 and y < y2):
                                    selected_objs.append(obj)
                                    
                elif bp_end_cx > bp_start_cx and bp_end_cy > bp_start_cy: # check if there's actually an inclusive zone
                    # outer edges
                    for start_x, end_x, start_y, end_y in border_passes:
                        for cy in range(start_y, end_y):
                            for cx in range(start_x, end_x):
                                if (l:=object_grid.get((cx, cy))):
                                    for obj in l:
                                        bx, by, bw, bh = BOUNDS[obj.__class__][obj.orient][obj.input_count]

                                        if ((x:=obj.x + bx) + bw > x1 and x < x2) and ((y:=obj.y + by) + bh > y1 and y < y2):
                                            selected_objs.append(obj)
                    # inclusive zone
                    for cy in range(bp_start_cy, bp_end_cy):
                        for cx in range(bp_start_cx, bp_end_cx):
                            if (l:=object_grid.get((cx, cy))): selected_objs += l

                else: # if there is no strictly inclusive zone all checks will inherently require a rect check
                    for cy in range(start_cy, end_cy + 1):
                        for cx in range(start_cx, end_cx + 1):
                            if (l:=object_grid.get((cx, cy))):
                                for obj in l:
                                    bx, by, bw, bh = BOUNDS[obj.__class__][obj.orient][obj.input_count]

                                    if ((x:=obj.x + bx) + bw > x1 and x < x2) and ((y:=obj.y + by) + bh > y1 and y < y2):
                                        selected_objs.append(obj)
                # wire nodes
                if len(wire_node_grid) < half_cell_area:
                    for (cx, cy), l in wire_node_grid.items():
                        if bp_start_cx <= cx and cx < bp_end_cx and bp_start_cy <= cy and cy < bp_end_cy: 
                            selected_nodes += l
                        elif start_cx <= cx and cx <= end_cx and start_cy <= cy and cy <= end_cy:
                            for n in l:
                                if ((x:=n.x) + WIRE_NODE_RADIUS > x1 and x - WIRE_NODE_RADIUS < x2) and ((y:=n.y) + WIRE_NODE_RADIUS > y1 and y - WIRE_NODE_RADIUS < y2):
                                    selected_nodes.append(n)

                elif bp_end_cx > bp_start_cx and bp_end_cy > bp_start_cy: # check if there's actually an inclusive zone
                    # outer edges
                    for start_x, end_x, start_y, end_y in border_passes:
                        for cy in range(start_y, end_y):
                            for cx in range(start_x, end_x):
                                if (l:=wire_node_grid.get((cx, cy))):
                                    for n in l:
                                        if ((x:=n.x) + WIRE_NODE_RADIUS > x1 and x - WIRE_NODE_RADIUS < x2) and ((y:=n.y) + WIRE_NODE_RADIUS > y1 and y - WIRE_NODE_RADIUS < y2):
                                            selected_nodes.append(n)
                    # inclusive zone
                    for cy in range(bp_start_cy, bp_end_cy):
                        for cx in range(bp_start_cx, bp_end_cx):
                            if (l:=wire_node_grid.get((cx, cy))):
                                selected_nodes += l
                                for n in l:
                                    if (wr:=n.seg1.wire) not in visited_wires:
                                        visited_wires.add(wr)
                                        selected_wires.append(wr)

                else: # if there is no strictly inclusive zone all checks will inherently require a rect check
                    for cy in range(start_cy, end_cy + 1):
                        for cx in range(start_cx, end_cx + 1):
                            if (l:=wire_node_grid.get((cx, cy))):
                                for n in l:
                                    if ((x:=n.x) + WIRE_NODE_RADIUS > x1 and x - WIRE_NODE_RADIUS < x2) and ((y:=n.y) + WIRE_NODE_RADIUS > y1 and y - WIRE_NODE_RADIUS < y2):
                                        selected_nodes.append(n)

                # wires
                if len(segment_cx) * len(segment_cy) < half_cell_area:
                    filtered_x = []

                    for cx, l in segment_cx.items():
                        if start_cx <= cx and cx <= end_cx:
                            filtered_x.append(l)

                    for cy, l_cy in segment_cy.items():
                        if start_cy <= cy and cy <= end_cy:
                            for l_cx in filtered_x:
                                for seg in l_cx:
                                    if (wr:=seg.wire) not in visited_wires and seg in l_cy:
                                        visited_wires.add(wr)

                                        node_found = False
                                        for n in (nodes:=wr.nodes):
                                            if x1 <= (nx:=n.x) and nx <= x2 and y1 <= (ny:=n.y) and ny < y2:
                                                selected_wires.append(wr)
                                                node_found = True
                                                break

                                        if node_found: continue

                                        node1 = next(it:=iter(nodes))
                                        for node2 in it:
                                            n1x = node1.x; n1y = node1.y
                                            n2x = node2.x; n2y = node2.y

                                            if (n1x > x1 or n2x > x1) and (n1x < x2 or n2x < x2) and (n1y > y1 or n2y > y1) and (n1y < y2 or n2y < y2): 
                                                dx = n2x - n1x
                                                dy = n2y - n1y

                                                if dx != 0:
                                                    m = dy / dx

                                                    yl = m*(x1 - n1x) + n1y
                                                    yr = m*(x2 - n1x) + n1y

                                                    if (y1 <= yl and yl < y2) or (y1 <= yr and yr <= y2) or (yl < y1) is not (yr < y1):
                                                        selected_wires.append(wr)
                                                        break

                                                elif x1 <= n1x <= x2:
                                                    selected_wires.append(wr)
                                                    break

                                            node1 = node2
                else:
                    for cx in range(start_cx, end_cx + 1):
                        for cy in range(start_cy, end_cy + 1):
                            x_segs = segment_cx.get(cx)
                            y_segs = segment_cy.get(cy)

                            if x_segs and y_segs:
                                for seg in x_segs:
                                    if (wr:=seg.wire) not in visited_wires and seg in y_segs:
                                        visited_wires.add(wr)

                                        node_found = False
                                        for n in (nodes:=wr.nodes):
                                            if x1 <= (nx:=n.x) and nx <= x2 and y1 <= (ny:=n.y) and ny < y2:
                                                selected_wires.append(wr)
                                                node_found = True
                                                break

                                        if node_found: continue

                                        node1 = next(it:=iter(nodes))
                                        for node2 in it:
                                            n1x = node1.x; n1y = node1.y
                                            n2x = node2.x; n2y = node2.y

                                            if (n1x > x1 or n2x > x1) and (n1x < x2 or n2x < x2) and (n1y > y1 or n2y > y1) and (n1y < y2 or n2y < y2): 
                                                dx = n2x - n1x
                                                dy = n2y - n1y

                                                if dx != 0:
                                                    m = dy / dx

                                                    yl = m*(x1 - n1x) + n1y
                                                    yr = m*(x2 - n1x) + n1y

                                                    if (y1 <= yl and yl < y2) or (y1 <= yr and yr <= y2) or (yl < y1) is not (yr < y1):
                                                        selected_wires.append(wr)
                                                        break

                                                elif x1 <= n1x <= x2:
                                                    selected_wires.append(wr)
                                                    break

                                            node1 = node2

                if SHIFT_DOWN:
                    for obj in selected_objs:
                        if obj not in selected_obj_set:
                            selected_obj_list.append(obj)
                    selected_obj_set.update(selected_objs)
                    for n in selected_nodes:
                        if n not in selected_node_set:
                            selected_node_list.append(n)
                    selected_node_set.update(selected_nodes)
                    for wr in selected_wires:
                        if wr not in selected_wire_set:
                            selected_wire_list.append(wr)
                    selected_wire_set.update(selected_wires)
                elif CTRL_DOWN:
                    for obj in selected_objs:
                        if obj in selected_obj_set:
                            selected_obj_list.remove(obj)
                            selected_obj_set.remove(obj)
                        else:
                            selected_obj_list.append(obj)
                            selected_obj_set.add(obj)
                    for n in selected_nodes:
                        if n in selected_node_set:
                            selected_node_list.remove(n)
                            selected_node_set.remove(n)
                        else:
                            selected_node_list.append(n)
                            selected_node_set.add(n)
                    for wr in selected_wires:
                        if wr in selected_wire_set:
                            selected_wire_list.remove(wr)
                            selected_wire_set.remove(wr)
                        else:
                            selected_wire_list.append(wr)
                            selected_wire_set.add(wr)
                else:
                    selected_obj_list = selected_objs
                    selected_obj_set.clear(); selected_obj_set.update(selected_objs)
                    selected_node_list = selected_nodes
                    selected_node_set.clear(); selected_node_set.update(selected_nodes)
                    selected_wire_list = selected_wires
                    selected_wire_set.clear(); selected_wire_set.update(selected_wires)

                min_x_bound = min_y_bound = INF
                max_x_bound = max_y_bound = NEG_INF

                if selected_node_list:
                    drag_node_x = [None] * len(selected_node_list); drag_node_y = drag_node_x.copy()
                    drag_node_x[0] = (n:=selected_node_list[0]).x; drag_node_y[0] = n.y

                    # recalculate bounds  
                    for n in selected_node_list:
                        if (x:=n.x) < min_x_bound: min_x_bound = x
                        elif x > max_x_bound: max_x_bound = x
                        if (y:=n.y) < min_y_bound: min_y_bound = y
                        elif y > max_y_bound: max_y_bound = y

                if selected_obj_list:
                    drag_obj_x = [None] * len(selected_obj_list); drag_obj_y = drag_obj_x.copy()
                    drag_obj_x[0] = (obj:=selected_obj_list[0]).x; drag_obj_y[0] = obj.y

                    # recalculate bounds  
                    for obj in selected_obj_list:
                        if obj.orient & 1: h, w = SIZES[obj.__class__][obj.input_count]
                        else: w, h = SIZES[obj.__class__][obj.input_count]

                        if (x:=obj.x) < min_x_bound: min_x_bound = x
                        if x + w > max_x_bound:      max_x_bound = x + w
                        if (y:=obj.y) < min_y_bound: min_y_bound = y
                        if y + h > max_y_bound:      max_y_bound = y + h

                selection = None

        # wire node insertion
        if jrmb and not over_gui_element:
            if wr_attacher:
                if snap_to_grid:
                    x = FLOOR((mx + HALF_SNAP) * INV_SNAP) * SNAP_RES
                    y = FLOOR((my + HALF_SNAP) * INV_SNAP) * SNAP_RES
                    wr_attacher.nodes.append(t:=(x, y))
                else:
                    wr_attacher.nodes.append(t:=(mx, my))

                if node_log_depth:
                    del node_placement_log[-node_log_depth:]
                    node_log_depth = 0

                node_placement_log.append(t)

            elif not near_node:
                cx = FLOOR(mx * INV_GRID_CELL_SIZE); cy = FLOOR(my * INV_GRID_CELL_SIZE)

                if snap_to_grid:
                    adj_mx = FLOOR((mx + HALF_SNAP) * INV_SNAP) * SNAP_RES
                    adj_my = FLOOR((my + HALF_SNAP) * INV_SNAP) * SNAP_RES
                    adj_cx = FLOOR(adj_mx * INV_GRID_CELL_SIZE)
                    adj_cy = FLOOR(adj_my * INV_GRID_CELL_SIZE)
                else:
                    adj_mx = mx
                    adj_my = my
                    adj_cx = cx
                    adj_cy = cy

                x_segs = segment_cx.get(cx); y_segs = segment_cy.get(cy)

                if x_segs and y_segs:
                    for seg in x_segs:
                        if seg in y_segs:
                            n1x = (n1:=seg.node1).x; n1y = n1.y
                            n2x = (n2:=seg.node2).x; n2y = n2.y

                            dx = n2x - n1x; dy = n2y - n1y

                            length2 = dx*dx + dy*dy
                            if length2 > 0:
                                t = (dx*(mx - n1x) + dy*(my - n1y)) / length2
                                if t > 1: t = 1  # clamp to the segments ends
                                elif t < 0: t = 0

                                x = n1x + t*dx
                                y = n1y + t*dy
                            else:
                                x = n1x
                                y = n1y

                            dx = mx - x; dy = my - y

                            if dx*dx + dy*dy < CREATE_WIRE_NODE_PROX2:
                                min_cx = n1.cx; min_cy = n1.cy
                                max_cx = n2.cx; max_cy = n2.cy 

                                if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
                                if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy
                                
                                for _x in range(min_cx, max_cx + 1): 
                                    (l:=segment_cx[_x]).remove(seg)
                                    if not l: del segment_cx[_x]
                                for _y in range(min_cy, max_cy + 1): 
                                    (l:=segment_cy[_y]).remove(seg)
                                    if not l: del segment_cy[_y]

                                wr_node = WIRE_NODE(adj_mx, adj_my, adj_cx, adj_cy)
                                
                                cell = (adj_cx,adj_cy)
                                if not (l:=wire_node_grid.get(cell)):
                                    wire_node_grid[cell] = {wr_node}
                                else:
                                    l.add(wr_node)

                                wr = seg.wire
                                segments = wr.segments
                                nodes = wr.nodes

                                seg_idx = segments.index(seg)
                                node_idx = nodes.index(n1)

                                if node_idx != 0 and nodes[node_idx - 1] is n2:
                                    wr_node_idx = node_idx

                                    n1, n2 = n2, n1
                                else:
                                    wr_node_idx = node_idx + 1
                                
                                nodes.insert(wr_node_idx, wr_node)
                                
                                new_seg = WIRE_SEG(wr_node, n2, wr)

                                segments.insert(seg_idx + 1, new_seg)

                                wr_node.seg1 = seg
                                wr_node.seg2 = new_seg

                                if seg.node2 is n2: seg.node2 = wr_node
                                else: seg.node1 = wr_node

                                if n2.seg1 is seg: n2.seg1 = new_seg
                                else: n2.seg2 = new_seg

                                INSERT_NODE_WITH_SEGMENTS(wr_node, n1, seg, n2, new_seg, segment_cx, segment_cy, wire_node_grid)

                                if log_depth:
                                    del action_log[-log_depth:]
                                    log_depth = 0

                                if len(action_log) > MAX_ACTION_LOG_LENGTH:
                                    del action_log[0]

                                action_log.append(NODE_INSERTION_ACTION(wr_node, wr_node_idx))

                                break

        # object connection
        if jlmb or (wr_attacher and rlmb):
            if not selected_node:
                selected_node = near_node
               
                if near_node:
                    last_click_time = frame_start
                
                    obj, idx = selected_node
                    if idx == obj.input_count:
                        signal = obj.output
                    else:
                        signal = False

                    wr_attacher = ATTACHER(obj, idx, signal, mouse_x, mouse_y)
                else:
                    wr_attacher = None
                    node_placement_log.clear()
                    node_log_depth = 0

            elif near_node:
                s_obj, s_idx = selected_node
                obj, idx = near_node

                if s_obj is not obj: 
                    s_input_count = s_obj.input_count
                    input_count = obj.input_count

                    if (s_input_count == s_idx) is not (input_count == idx): # ensure that an input is being connected to an output
                        out_obj, out_idx, in_obj, in_idx = (s_obj, s_idx, obj, idx) if idx < input_count else (obj, idx, s_obj, s_idx)

                        nx, ny = NODE_POSITIONS[out_obj.__class__][out_obj.orient][out_obj.input_count][-1]
                        
                        nx = out_obj.x + nx; ny = out_obj.y + ny
                        cx = FLOOR(nx * INV_GRID_CELL_SIZE); cy = FLOOR(ny * INV_GRID_CELL_SIZE)

                        nodes = [WIRE_NODE(nx, ny, cx, cy)]

                        attacher_nodes = wr_attacher.nodes 
                        
                        if idx == input_count: 
                            attacher_nodes.reverse()
                        
                        for nx, ny in wr_attacher.nodes:
                            cx = FLOOR(nx * INV_GRID_CELL_SIZE); cy = FLOOR(ny * INV_GRID_CELL_SIZE)
                            nodes.append(n:=WIRE_NODE(nx, ny, cx, cy))

                            if not (l:=wire_node_grid.get(cell:=(cx,cy))):
                                wire_node_grid[cell] = {n}
                            else:
                                l.add(n) 

                        nx, ny = NODE_POSITIONS[in_obj.__class__][in_obj.orient][in_obj.input_count][in_idx]
                        
                        nx = in_obj.x + nx; ny = in_obj.y + ny
                        cx = FLOOR(nx * INV_GRID_CELL_SIZE); cy = FLOOR(ny * INV_GRID_CELL_SIZE)

                        nodes.append(WIRE_NODE(nx, ny, cx, cy))

                        out_obj.out_wires.append(wr:=WIRE(out_obj, out_idx, in_obj, in_idx, nodes, (segments:=[])))

                        # if a wire is already connected to that input, delete it 
                        if (wires:=in_obj.in_wires)[in_idx]:
                            over_wire = wires[in_idx]
                            
                            tran_obj = over_wire.tran_obj
                            recv_obj = over_wire.recv_obj

                            tran_obj.outputs.remove(recv_obj)
                            tran_obj.out_wires.remove(over_wire)

                            recv_obj.inputs[idx:=over_wire.recv_idx] = recv_obj.in_wires[idx] = None

                            REMOVE_SEGMENTS_AND_NODES(over_wire.segments, over_wire.nodes, segment_cx, segment_cy, wire_node_grid)
                        else:
                            over_wire = None

                        wires[in_idx] = wr

                        out_obj.outputs.append(in_obj)
                        in_obj.inputs[in_idx] = out_obj

                        wr.signal = out_obj.output

                        CREATE_AND_INSERT_SEGMENTS(wr, segments, nodes, segment_cx, segment_cy)

                        UPDATE_OBJECT_OUTPUT(in_obj)

                        if log_depth:
                            del action_log[-log_depth:]
                            log_depth = 0

                        if len(action_log) > MAX_ACTION_LOG_LENGTH:
                            del action_log[0]

                        action_log.append(ATTACH_WIRE_ACTION(wr, over_wire))                        

                    selected_node = near_node = wr_attacher = None

                    node_placement_log.clear()
                    node_log_depth = 0
            else:
                selected_node = wr_attacher = None

                node_placement_log.clear()
                node_log_depth = 0

        if jkeys[K_ESCAPE]:
            if (prompt:=GUI_MANAGER.active_prompt):
                btn = prompt.cancel_btn
                btn.handle(btn)
            elif GUI_MANAGER.open_interface:
                EXIT_BUTTON.handle(EXIT_BUTTON)

            selected_node = None

        if jkeys[K_ENTER] and (prompt:=GUI_MANAGER.active_prompt):
            btn = prompt.ok_btn
            btn.handle(btn)
            
        if not GUI_MANAGER.focused_input:    
            if jkeys[K_BACKSPACE] or jkeys[K_DELETE]:
                if jkeys[K_DELETE] and SAVE_LIST.selected is not None:
                    DELETE_BUTTON.handle(DELETE_BUTTON)

                elif selected_obj_list or selected_node_list or selected_wire_list:
                    if not drag_uninitiated:
                        drag_uninitiated = True

                        END_DRAG_ACTION(selected_obj_list, selected_node_list, obj_action_data, node_action_data, action_log, log_depth, MAX_ACTION_LOG_LENGTH)
                        log_depth = 0

                        obj_action_data = []
                        node_action_data = []

                    DELETE_ACTION(
                        selected_obj_list,
                        selected_node_list,
                        selected_wire_list,
                        selected_obj_set,
                        selected_wire_set,
                        PROP_MANAGER,
                        logic_objects,
                        object_grid,
                        wire_node_grid,
                        segment_cx, segment_cy,
                        action_log,
                        log_depth,
                        MAX_ACTION_LOG_LENGTH
                    )

                    log_depth = 0

                    selected_obj_list = []; selected_obj_set = set()
                    selected_node_list.clear(); selected_node_set.clear()
                    selected_wire_list = []; selected_wire_set.clear()
                    drag_obj_x.clear(); drag_obj_y.clear()
                    drag_node_x.clear(); drag_node_y.clear()

            # new save
            if jkeys[K_N] and GUI_MANAGER.open_interface is SAVES_INTERFACE:
                NEW_BUTTON.handle(NEW_BUTTON)

            if jkeys[K_G]:
                snap_to_grid = not snap_to_grid

            num_pressed = None
            if jkeys[K_2]: num_pressed = 2
            elif jkeys[K_3]: num_pressed = 3
            elif jkeys[K_4]: num_pressed = 4
            elif jkeys[K_5]: num_pressed = 5
            elif jkeys[K_6]: num_pressed = 6
            elif jkeys[K_7]: num_pressed = 7
            elif jkeys[K_8]: num_pressed = 8

            if num_pressed and selected_obj_list:
                for obj in selected_obj_list:
                    if (cls:=obj.__class__) in GATE:
                        ic = obj.input_count

                        if ic != 1 and num_pressed != ic:
                            obj_action_data.append(obj)
                            obj_action_data.append(ic)

                            if num_pressed > ic:
                                obj.inputs += (l:=[None] * (num_pressed - ic))
                                obj.in_wires += l

                                obj_action_data.append(None)

                                if cls is AND_GATE or cls is NAND_GATE: 
                                    UPDATE_OBJECT_OUTPUT(obj)
                            else:
                                truncated = obj.in_wires[num_pressed:]

                                del obj.in_wires[num_pressed:]
                                del obj.inputs[num_pressed:]

                                for wr in truncated:
                                    if wr:
                                        tran_obj = wr.tran_obj

                                        tran_obj.out_wires.remove(wr)
                                        tran_obj.outputs.remove(obj)

                                        REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                                obj_action_data.append(truncated)

                                UPDATE_OBJECT_OUTPUT(obj)

                            obj.input_count = num_pressed

                            UPDATE_END_NODES_INPUT_MODIFICATION(obj, num_pressed, INV_GRID_CELL_SIZE, NODE_POSITIONS[cls][obj.orient][num_pressed], segment_cx, segment_cy)
                
                if obj_action_data:
                    if log_depth:
                        del action_log[-log_depth:]
                        log_depth = 0

                    if len(action_log) > MAX_ACTION_LOG_LENGTH:
                        del action_log[0]

                    action_log.append(MODIFY_INPUT_COUNT_ACTION(obj_action_data, num_pressed))

                    obj_action_data = []

            # copy selected objects
            if jkeys[K_C] and CTRL_DOWN:
                center_x = (min_x_bound + max_x_bound) * 0.5
                center_y = (min_y_bound + max_y_bound) * 0.5

                copied_objects.clear()
                root_indices.clear()

                for i, obj in enumerate(selected_obj_list):
                    copied_objects.append((obj.__class__, obj.x - center_x, obj.y - center_y, obj.orient, obj.input_count, obj.output))
                    # root objects are propagated to establish the state of the pasted selection
                    # cyclic queue objects are marked as roots as cyclic circuits have no topological root
                    if (cls:=obj.__class__) is TOGGLE or (obj in cyclic_objects and obj in cyclic_queue) or \
                        (not any(inpt in selected_obj_set for inpt in obj.inputs) and (cls is LIGHT or any(out in selected_obj_set for out in obj.outputs))):
                        root_indices.append(i)

                copied_indices = {
                    obj: i
                    for i, obj in enumerate(selected_obj_list)
                }

                # wire copying (stored as out_obj_idx, out_node_idx, in_obj_idx, in_node_idx, obj output, node displacements)
                copied_wires.clear()
                for obj in selected_obj_list:
                    if obj.__class__ not in NO_OUTPUT:
                        output = obj.output
                        for i, out in enumerate(obj.outputs):
                            if out in selected_obj_set:
                                wr = obj.out_wires[i]
                                wrnodes = wr.nodes

                                nodes = [] 
                                for i in range(1, len(wrnodes) - 1): # ignore both end point nodes
                                    nodes.append(((n:=wrnodes[i]).x - center_x, n.y - center_y))

                                copied_wires.append((copied_indices[obj], wr.tran_idx, copied_indices[out], wr.recv_idx, output, nodes))

            # paste copied objects
            if jkeys[K_V] and CTRL_DOWN and copied_objects:
                pasted_objects.clear()
                pasted_wire_nodes.clear()

                pasted_wires = []

                min_x_bound = min_y_bound = INF
                max_x_bound = max_y_bound = NEG_INF

                for cls, dx, dy, o, input_count, output in copied_objects:
                    x = mx + dx; y = my + dy

                    if snap_to_grid: 
                        x = FLOOR((x + HALF_SNAP) * INV_SNAP) * SNAP_RES
                        y = FLOOR((y + HALF_SNAP) * INV_SNAP) * SNAP_RES
                        
                    cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))

                    copy = cls(x, y, cell, input_count)
                    copy.orient = o
                    copy.output = output

                    if not (l:=object_grid.get(cell)):
                        object_grid[cell] = {copy}
                    else:
                        l.add(copy)

                    pasted_objects.append(copy)

                    if o & 1:
                        h, w = SIZES[cls][input_count]
                    else:
                        w, h = SIZES[cls][input_count]

                    if x < min_x_bound: min_x_bound = x
                    if y < min_y_bound: min_y_bound = y
                    if x + w > max_x_bound: max_x_bound = x + w
                    if y + h > max_y_bound: max_y_bound = y + h

                drag_obj_x = [None] * len(pasted_objects); drag_obj_y = drag_obj_x.copy()

                for out_obj_idx, out_node_idx, in_obj_idx, in_node_idx, signal, rel_nodes in copied_wires:
                    out_obj = pasted_objects[out_obj_idx]; in_obj = pasted_objects[in_obj_idx]

                    tran_nx, tran_ny = NODE_POSITIONS[out_obj.__class__][out_obj.orient][out_obj.input_count][out_node_idx]
                    recv_nx, recv_ny = NODE_POSITIONS[in_obj.__class__][in_obj.orient][in_obj.input_count][in_node_idx]

                    nodes = [WIRE_NODE((x:=out_obj.x + tran_nx), (y:=out_obj.y + tran_ny), FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))]

                    for dx, dy in rel_nodes:
                        x = mx + dx; y = my + dy
                        
                        if snap_to_grid:
                            x = FLOOR((x + HALF_SNAP) * INV_SNAP) * SNAP_RES 
                            y = FLOOR((y + HALF_SNAP) * INV_SNAP) * SNAP_RES

                        cx = FLOOR(x * INV_GRID_CELL_SIZE); cy = FLOOR(y * INV_GRID_CELL_SIZE)

                        nodes.append(n:=WIRE_NODE(x, y, cx, cy))

                        if not (l:=wire_node_grid.get(cell:=(cx,cy))):
                            wire_node_grid[cell] = {n}
                        else:
                            l.add(n)

                        pasted_wire_nodes.append(n)
                    
                    nodes.append(WIRE_NODE((x:=in_obj.x + recv_nx), (y:=in_obj.y + recv_ny), FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE)))

                    wr = WIRE(out_obj, out_node_idx, in_obj, in_node_idx, nodes, (segments:=[]))
                    wr.signal = signal

                    pasted_wires.append(wr)

                    CREATE_AND_INSERT_SEGMENTS(wr, segments, nodes, segment_cx, segment_cy)

                    out_obj.outputs.append(in_obj)
                    out_obj.out_wires.append(wr)

                    in_obj.inputs[in_node_idx] = out_obj
                    in_obj.in_wires[in_node_idx] = wr

                for i in root_indices:
                    root = pasted_objects[i]
                    UPDATE_OBJECT_OUTPUT(root)
                    
                    if root.__class__ not in NO_OUTPUT:
                        output = root.output
                        for wr in root.out_wires:
                            wr.signal = output

                selected_wire_list.clear(); selected_wire_set.clear()

                logic_objects += pasted_objects
                selected_obj_list = pasted_objects.copy()
                selected_obj_set.clear(); selected_obj_set.update(selected_obj_list)

                drag_node_x = [None] * len(pasted_wire_nodes); drag_node_y = drag_node_x.copy()

                selected_node_list = pasted_wire_nodes.copy()
                selected_node_set.clear(); selected_node_set.update(selected_node_list)

                if selected_obj_list:
                    drag_obj_x[0] = (obj:=selected_obj_list[0]).x; drag_obj_y[0] = obj.y
                else:
                    drag_node_x[0] = (n:=selected_node_list[0]).x; drag_node_y[0] = n.y

                if log_depth:
                    del action_log[-log_depth:]
                    log_depth = 0

                if len(action_log) > MAX_ACTION_LOG_LENGTH:
                    del action_log[0]

                action_log.append(PLACE_OBJECTS_ACTION(pasted_objects.copy(), pasted_wires.copy()))

            Z_PRESSED = jkeys[K_Z]
            if Z_PRESSED and CTRL_DOWN and not SHIFT_DOWN and drag_uninitiated:
                if wr_attacher:
                    if len(node_placement_log) == node_log_depth:
                        selected_node = wr_attacher = None

                        node_log_depth = 0
                        node_placement_log.clear()
                    else:
                        node_log_depth += 1

                        del wr_attacher.nodes[-1]

                elif log_depth < len(action_log):
                    action = action_log[~log_depth]
                    log_depth += 1

                    if (cls:=action.__class__) is ATTACH_WIRE_ACTION:
                        wr = action.wire
                        tran_obj = wr.tran_obj
                        recv_obj = wr.recv_obj
                        recv_idx = wr.recv_idx

                        tran_obj.outputs.remove(recv_obj)
                        tran_obj.out_wires.remove(wr)

                        recv_obj.inputs[recv_idx] = recv_obj.in_wires[recv_idx] = None

                        REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        if (wr:=action.over_wire):
                            tran_obj = wr.tran_obj
                            recv_obj = wr.recv_obj
                            recv_idx = wr.recv_idx

                            tran_obj.out_wires.append(wr)
                            recv_obj.in_wires[recv_idx] = wr

                            tran_obj.outputs.append(recv_obj)
                            recv_obj.inputs[recv_idx] = tran_obj

                            wr.signal = tran_obj.output

                            INSERT_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        UPDATE_OBJECT_OUTPUT(recv_obj)

                    elif cls is NODE_INSERTION_ACTION:
                        n = action.node
                        seg1 = n.seg1; seg2 = n.seg2
                        wr = seg1.wire
                        recv_obj = wr.recv_obj

                        nodes = wr.nodes
                        idx = action.idx

                        n1 = nodes[idx-1]
                        n2 = nodes[idx+1]

                        REMOVE_NODE_WITH_SEGMENTS(n, n1, seg1, n2, seg2, segment_cx, segment_cy, wire_node_grid)

                        wr.segments.remove(seg2)
                        nodes.remove(n)

                        if seg1.node1 is n: seg1.node1 = n2
                        else: seg1.node2 = n2

                        if n2.seg1 is seg2: n2.seg1 = seg1
                        else: n2.seg2 = seg1

                        if n1.seg1 is seg2: n1.seg1 = seg1
                        else: n1.seg2 = seg1

                        min_cx = n1.cx; max_cx = n2.cx
                        min_cy = n1.cy; max_cy = n2.cy

                        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
                        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

                        for x in range(min_cx, max_cx + 1):
                            if not (l:=segment_cx.get(x)):
                                segment_cx[x] = {seg1}
                            else:
                                l.add(seg1)
                        for y in range(min_cy, max_cy + 1):
                            if not (l:=segment_cy.get(y)):
                                segment_cy[y] = {seg1}
                            else:
                                l.add(seg1)

                    elif cls is PLACE_OBJECTS_ACTION:
                        for wr in action.wires:
                            tran_obj = wr.tran_obj
                            recv_obj = wr.recv_obj

                            tran_obj.outputs.remove(recv_obj)
                            tran_obj.out_wires.remove(wr)

                            recv_obj.inputs[idx:=wr.recv_idx] = recv_obj.in_wires[idx] = None
                            
                            nodes = wr.nodes
                            
                            REMOVE_SEGMENTS_AND_NODES(wr.segments, nodes, segment_cx, segment_cy, wire_node_grid)
                            
                            for n in nodes:
                                if n in selected_node_set:
                                    selected_node_set.remove(n)
                                    selected_node_list.remove(n)

                            if wr in selected_wire_set:
                                selected_wire_set.remove(wr)
                                selected_wire_list.remove(wr)

                        objects = action.objects
                        for obj in objects:
                            (l:=object_grid[obj.cell]).remove(obj)
                            if not l: del object_grid[obj.cell]

                            if obj in selected_obj_set:
                                selected_obj_set.remove(obj)
                                selected_obj_list.remove(obj)

                        del logic_objects[logic_objects.index(objects[0]):logic_objects.index(objects[-1]) + 1]

                    elif cls is FLIP_SWITCH_ACTION:
                        obj = action.toggle
                        obj.output = output = not obj.output
                        for wr in obj.out_wires: wr.signal = output
                        UPDATE_OBJECT_OUTPUT(obj)

                    elif cls is MOVE_SELECTION_ACTION:
                        min_x_bound = min_y_bound = INF
                        max_x_bound = max_y_bound = NEG_INF

                        nodes_to_update = []

                        obj_data = action.object_data
                        node_data = action.node_data

                        # append the envolved objections in the action to elements and mark them as None 
                        for i in range(0, len(obj_data), 3):
                            obj = obj_data[i]
                            obj.x = x = obj.x + obj_data[i+1]; obj.y = y = obj.y + obj_data[i+2]

                            if (o:=obj.orient) & 1:
                                h, w = SIZES[cls:=obj.__class__][ic:=obj.input_count]
                            else:
                                w, h = SIZES[cls:=obj.__class__][ic:=obj.input_count]

                            if x < min_x_bound:     min_x_bound = x
                            if x + w > max_x_bound: max_x_bound = x + w
                            if y < min_y_bound:     min_y_bound = y
                            if y + h > max_y_bound: max_y_bound = y + h

                            nodes = NODE_POSITIONS[cls:=obj.__class__][obj.orient][ic]

                            # update wire positions
                            is_gate = cls in GATE
                            if is_gate or cls in NO_OUTPUT:
                                for wr in obj.in_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.recv_idx]

                                        (n:=wr.nodes[-1]).x = x + nx 
                                        n.y = y + ny

                                        nodes_to_update.append(n)

                            if is_gate or cls in NO_INPUT:
                                for wr in obj.out_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.tran_idx]

                                        (n:=wr.nodes[0]).x = x + nx 
                                        n.y = y + ny

                                        nodes_to_update.append(n)

                            # grid cell relocation 
                            cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))
                            if cell != obj.cell:
                                (l:=object_grid[obj.cell]).remove(obj)
                                if not l: del object_grid[obj.cell]

                                if not (l:=object_grid.get(cell)):
                                    object_grid[cell] = {obj}
                                else:
                                    l.add(obj)

                                obj.cell = cell

                        for i in range(0, len(node_data), 3):
                            nodes_to_update.append(n:=node_data[i])
                            n.x = x = n.x + node_data[i+1]; n.y = y = n.y + node_data[i+2]

                            if x < min_x_bound:   min_x_bound = x
                            elif x > max_x_bound: max_x_bound = x
                            if y < min_y_bound:   min_y_bound = y
                            elif y > max_y_bound: max_y_bound = y

                        UPDATE_SEGMENTS_AND_NODES(INV_GRID_CELL_SIZE, nodes_to_update, wire_node_grid, segment_cx, segment_cy)

                    elif cls is ROTATE_SELECTION_ACTION:
                        center_x = action.center_x
                        center_y = action.center_y

                        dx = min_x_bound - center_x; dy = min_y_bound - center_y
                        min_x_bound = center_x + dy; max_x_bound = center_x - dy
                        min_y_bound = center_y + dx; max_y_bound = center_y - dx

                        nodes_to_update = action.nodes.copy()

                        for obj in action.objects:
                            if (o:=obj.orient) & 1:
                                h, _ = SIZES[cls:=obj.__class__][ic:=obj.input_count]
                            else:
                                _, h = SIZES[cls:=obj.__class__][ic:=obj.input_count]

                            x = center_x + center_y - obj.y - h; y = center_y - center_x + obj.x

                            cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))

                            old_cell = obj.cell
                            if cell != old_cell:
                                (l:=object_grid[old_cell]).remove(obj)
                                if not l: del object_grid[old_cell]

                                if not (l:=object_grid.get(cell)):
                                    object_grid[cell] = {obj}
                                else:
                                    l.add(obj)

                                obj.cell = cell

                            o = (o - 1) & 0b11

                            obj.x = x; obj.y = y
                            obj.orient = o

                            nodes = NODE_POSITIONS[cls][o][ic]

                            # update wire positions
                            is_gate = cls in GATE
                            if is_gate or cls in NO_OUTPUT:
                                for wr in obj.in_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.recv_idx]

                                        (n:=wr.nodes[-1]).x = obj.x + nx 
                                        n.y = obj.y + ny

                                        nodes_to_update.append(n)

                            if is_gate or cls in NO_INPUT:
                                for wr in obj.out_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.tran_idx]

                                        (n:=wr.nodes[0]).x = obj.x + nx 
                                        n.y = obj.y + ny

                                        nodes_to_update.append(n)

                        for n in action.nodes:
                            n.x, n.y = center_x + center_y - n.y, center_y - center_x + n.x

                        UPDATE_SEGMENTS_AND_NODES(INV_GRID_CELL_SIZE, nodes_to_update, wire_node_grid, segment_cx, segment_cy)

                    elif cls is DELETE_SELECTION_ACTION:
                        objects = action.objects
                        obj_set = action.objects_set

                        logic_objects += objects

                        for obj in objects:
                            if not (l:=object_grid.get(obj.cell)):
                                object_grid[cell] = {obj}
                            else:
                                l.add(obj)

                        for wr in action.internal_wires:
                            INSERT_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        for wr in action.wires:
                            tran_obj = wr.tran_obj
                            recv_obj = wr.recv_obj
                            recv_idx = wr.recv_idx

                            tran_obj.outputs.append(recv_obj)
                            tran_obj.out_wires.append(wr)

                            recv_obj.inputs[recv_idx] = tran_obj
                            recv_obj.in_wires[recv_idx] = wr

                            INSERT_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                            if recv_obj not in obj_set: UPDATE_OBJECT_OUTPUT(recv_obj)

                        node_data = action.node_data

                        # iterate in reverse to preserve node ordering
                        for i in range(len(node_data)-1, -1, -2):
                            wr_node = node_data[i-1]
                            idx = node_data[i]

                            wr = wr_node.seg1.wire

                            segments = wr.segments
                            nodes = wr.nodes

                            n1 = nodes[idx-1]
                            n2 = nodes[idx]

                            seg = segments[idx-1]

                            if wr_node.seg1 is not seg: new_seg = wr_node.seg1
                            else: new_seg = wr_node.seg2 

                            min_cx = n1.cx; max_cx = n2.cx
                            min_cy = n1.cy; max_cy = n2.cy

                            if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
                            if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

                            for x in range(min_cx, max_cx + 1):
                                (l:=segment_cx[x]).remove(seg)
                                if not l: del segment_cx[x]
                            for y in range(min_cy, max_cy + 1):
                                (l:=segment_cy[y]).remove(seg)
                                if not l: del segment_cy[y]

                            nodes.insert(idx, wr_node)
                            segments.insert(idx, new_seg)

                            if n2.seg1 is seg: n2.seg1 = new_seg
                            else: n2.seg2 = new_seg

                            if seg.node1 is n2: seg.node1 = wr_node
                            else: seg.node2 = wr_node

                            INSERT_NODE_WITH_SEGMENTS(wr_node, n1, seg, n2, new_seg, segment_cx, segment_cy, wire_node_grid)

                    elif cls is MODIFY_INPUT_COUNT_ACTION:
                        current_input_count = action.input_count

                        obj_data = action.object_data

                        for i in range(0, len(obj_data), 3):
                            obj = obj_data[i]
                            prior_count = obj_data[i+1]

                            if current_input_count < prior_count:
                                truncated = obj_data[i+2]

                                obj.in_wires += truncated
                                inputs = obj.inputs 
                                inputs += [None] * (prior_count - current_input_count)

                                for j, wr in enumerate(truncated):
                                    if wr:
                                        tran_obj = wr.tran_obj

                                        inputs[current_input_count + j] = tran_obj

                                        tran_obj.outputs.append(obj)
                                        tran_obj.out_wires.append(wr)
                                        
                                        INSERT_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                                UPDATE_OBJECT_OUTPUT(obj)
                            
                            else:
                                del obj.inputs[prior_count:]
                                del obj.in_wires[prior_count:]

                                if (cls:=obj.__class__) is AND_GATE or cls is NAND_GATE:
                                    UPDATE_OBJECT_OUTPUT(obj)
                            
                            obj.input_count = prior_count

                            UPDATE_END_NODES_INPUT_MODIFICATION(obj, prior_count, INV_GRID_CELL_SIZE, NODE_POSITIONS[obj.__class__][obj.orient][prior_count], segment_cx, segment_cy)

            if ((Z_PRESSED and CTRL_DOWN and SHIFT_DOWN) or (jkeys[K_Y] and CTRL_DOWN)) and drag_uninitiated:
                if node_placement_log:
                    if node_log_depth > 0:
                        n = node_placement_log[-node_log_depth]
                        node_log_depth -= 1

                        wr_attacher.nodes.append(n)

                elif log_depth > 0:    
                    action = action_log[-log_depth]
                    log_depth -= 1

                    if (cls:=action.__class__) is ATTACH_WIRE_ACTION:
                        if (wr:=action.over_wire):
                            tran_obj = wr.tran_obj
                            recv_obj = wr.recv_obj

                            tran_obj.outputs.remove(recv_obj)
                            tran_obj.out_wires.remove(wr)

                            recv_obj.inputs[idx:=wr.recv_idx] = recv_obj.in_wires[idx] = None
                            
                            REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        wr = action.wire
                        tran_obj = wr.tran_obj
                        recv_obj = wr.recv_obj
                        recv_idx = wr.recv_idx

                        tran_obj.out_wires.append(wr)
                        recv_obj.in_wires[recv_idx] = wr

                        tran_obj.outputs.append(recv_obj)
                        recv_obj.inputs[recv_idx] = tran_obj

                        wr.signal = tran_obj.output

                        INSERT_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        UPDATE_OBJECT_OUTPUT(recv_obj)
                    
                    elif cls is NODE_INSERTION_ACTION:
                        wr_node = action.node
                        wr = wr_node.seg1.wire

                        segments = wr.segments
                        nodes = wr.nodes

                        idx = action.idx
                        n1 = nodes[idx - 1]
                        n2 = nodes[idx]

                        seg = segments[idx - 1]

                        min_cx = n1.cx; min_cy = n1.cy
                        max_cx = n2.cx; max_cy = n2.cy 

                        if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
                        if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy
                        
                        for _x in range(min_cx, max_cx + 1): 
                            (l:=segment_cx[_x]).remove(seg)
                            if not l: del segment_cx[_x]
                        for _y in range(min_cy, max_cy + 1): 
                            (l:=segment_cy[_y]).remove(seg)
                            if not l: del segment_cy[_y]

                        cell = (wr_node.cx, wr_node.cy)
                        if not (l:=wire_node_grid.get(cell)):
                            wire_node_grid[cell] = {wr_node}
                        else:
                            l.add(wr_node)

                        nodes.insert(idx, wr_node)
                        
                        new_seg = WIRE_SEG(wr_node, n2, wr)

                        segments.insert(idx, new_seg)

                        wr_node.seg1 = seg
                        wr_node.seg2 = new_seg

                        if seg.node2 is n2: seg.node2 = wr_node
                        else: seg.node1 = wr_node

                        if n2.seg1 is seg: n2.seg1 = new_seg
                        else: n2.seg2 = new_seg

                        INSERT_NODE_WITH_SEGMENTS(wr_node, n1, seg, n2, new_seg, segment_cx, segment_cy, wire_node_grid)

                    elif cls is PLACE_OBJECTS_ACTION:
                        for wr in action.wires:
                            tran_obj = wr.tran_obj
                            recv_obj = wr.recv_obj

                            tran_obj.outputs.append(recv_obj)
                            tran_obj.out_wires.append(wr)

                            recv_obj.inputs[idx:=wr.recv_idx] = tran_obj
                            recv_obj.in_wires[idx] = wr
                            
                            INSERT_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        objects = action.objects
                        for obj in objects:
                            if not (l:=object_grid.get(obj.cell)):
                                object_grid[cell] = {obj}
                            else:
                                l.add(obj)

                        logic_objects += objects

                    elif cls is FLIP_SWITCH_ACTION:
                        obj = action.toggle
                        obj.output = output = not obj.output
                        for wr in obj.out_wires: wr.signal = output
                        UPDATE_OBJECT_OUTPUT(obj)

                    elif cls is MOVE_SELECTION_ACTION:
                        min_x_bound = min_y_bound = INF
                        max_x_bound = max_y_bound = NEG_INF

                        nodes_to_update = []

                        obj_data = action.object_data
                        node_data = action.node_data

                        # append the envolved objections in the action to elements and mark them as None 
                        for i in range(0, len(obj_data), 3):
                            obj = obj_data[i]
                            obj.x = x = obj.x - obj_data[i+1]; obj.y = y = obj.y - obj_data[i+2]

                            if (o:=obj.orient) & 1:
                                h, w = SIZES[cls:=obj.__class__][ic:=obj.input_count]
                            else:
                                w, h = SIZES[cls:=obj.__class__][ic:=obj.input_count]

                            if x < min_x_bound:     min_x_bound = x
                            if x + w > max_x_bound: max_x_bound = x + w
                            if y < min_y_bound:     min_y_bound = y
                            if y + h > max_y_bound: max_y_bound = y + h

                            nodes = NODE_POSITIONS[cls][obj.orient][ic]

                            # update wire positions
                            is_gate = cls in GATE
                            if is_gate or cls in NO_OUTPUT:
                                for wr in obj.in_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.recv_idx]

                                        (n:=wr.nodes[-1]).x = x + nx 
                                        n.y = y + ny

                                        nodes_to_update.append(n)

                            if is_gate or cls in NO_INPUT:
                                for wr in obj.out_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.tran_idx]

                                        (n:=wr.nodes[0]).x = x + nx 
                                        n.y = y + ny

                                        nodes_to_update.append(n)

                            # grid cell relocation 
                            cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))
                            if cell != obj.cell:
                                (l:=object_grid[obj.cell]).remove(obj)
                                if not l: del object_grid[obj.cell]

                                if not (l:=object_grid.get(cell)):
                                    object_grid[cell] = {obj}
                                else:
                                    l.add(obj)

                                obj.cell = cell

                        for i in range(0, len(node_data), 3):
                            nodes_to_update.append(n:=node_data[i])
                            n.x = x = n.x - node_data[i+1]; n.y = y = n.y - node_data[i+2]

                            if x < min_x_bound:   min_x_bound = x
                            elif x > max_x_bound: max_x_bound = x
                            if y < min_y_bound:   min_y_bound = y
                            elif y > max_y_bound: max_y_bound = y

                        UPDATE_SEGMENTS_AND_NODES(INV_GRID_CELL_SIZE, nodes_to_update, wire_node_grid, segment_cx, segment_cy)

                    elif cls is ROTATE_SELECTION_ACTION:
                        center_x = action.center_x
                        center_y = action.center_y

                        dx = min_x_bound - center_x; dy = min_y_bound - center_y
                        min_x_bound = center_x + dy; max_x_bound = center_x - dy
                        min_y_bound = center_y + dx; max_y_bound = center_y - dx

                        nodes_to_update = action.nodes.copy()

                        for obj in action.objects:
                            if (o:=obj.orient) & 1:
                                _, w = SIZES[cls:=obj.__class__][ic:=obj.input_count]
                            else:
                                w, _ = SIZES[cls:=obj.__class__][ic:=obj.input_count]

                            x = center_x - center_y + obj.y; y = center_y + center_x - obj.x - w

                            cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))

                            old_cell = obj.cell
                            if cell != old_cell:
                                (l:=object_grid[old_cell]).remove(obj)
                                if not l: del object_grid[old_cell]

                                if not (l:=object_grid.get(cell)):
                                    object_grid[cell] = {obj}
                                else:
                                    l.add(obj)

                                obj.cell = cell

                            o = (o + 1) & 0b11

                            obj.x = x; obj.y = y
                            obj.orient = o

                            nodes = NODE_POSITIONS[cls][o][ic]

                            # update wire positions
                            is_gate = cls in GATE
                            if is_gate or cls in NO_OUTPUT:
                                for wr in obj.in_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.recv_idx]

                                        (n:=wr.nodes[-1]).x = obj.x + nx 
                                        n.y = obj.y + ny

                                        nodes_to_update.append(n)

                            if is_gate or cls in NO_INPUT:
                                for wr in obj.out_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.tran_idx]

                                        (n:=wr.nodes[0]).x = obj.x + nx 
                                        n.y = obj.y + ny

                                        nodes_to_update.append(n)

                        for n in action.nodes:
                            n.x, n.y = center_x - center_y + n.y, center_y + center_x - n.x

                        UPDATE_SEGMENTS_AND_NODES(INV_GRID_CELL_SIZE, nodes_to_update, wire_node_grid, segment_cx, segment_cy)

                    elif cls is DELETE_SELECTION_ACTION:
                        obj_set = action.objects_set

                        node_data = action.node_data
                        
                        for i in range(0, len(node_data), 2):
                            n = node_data[i]
                            idx = node_data[i+1]

                            seg1 = n.seg1; seg2 = n.seg2

                            wr = seg1.wire

                            n_cx = n.cx; n_cy = n.cy

                            nodes = wr.nodes
                            segments = wr.segments

                            del nodes[idx]

                            n1 = nodes[idx-1]
                            n2 = nodes[idx]

                            if seg1.node1 is n2 or seg1.node2 is n2:
                                seg1, seg2 = seg2, seg1

                            REMOVE_NODE_WITH_SEGMENTS(n, n1, seg1, n2, seg2, segment_cx, segment_cy, wire_node_grid)

                            del segments[idx]

                            if seg1.node1 is n: seg1.node1 = n2
                            else: seg1.node2 = n2

                            if n2.seg1 is seg2: n2.seg1 = seg1
                            else: n2.seg2 = seg1

                            min_cx = n1.cx; max_cx = n2.cx
                            min_cy = n1.cy; max_cy = n2.cy

                            if min_cx > max_cx: min_cx, max_cx = max_cx, min_cx
                            if min_cy > max_cy: min_cy, max_cy = max_cy, min_cy

                            for x in range(min_cx, max_cx + 1):
                                if not (l:=segment_cx.get(x)):
                                    segment_cx[x] = {seg1}
                                else:
                                    l.add(seg1)
                            for y in range(min_cy, max_cy + 1):
                                if not (l:=segment_cy.get(y)):
                                    segment_cy[y] = {seg1}
                                else:
                                    l.add(seg1)

                        for wr in action.wires:
                            tran_obj = wr.tran_obj
                            recv_obj = wr.recv_obj

                            tran_obj.outputs.remove(recv_obj)
                            tran_obj.out_wires.remove(wr)

                            recv_obj.inputs[idx:=wr.recv_idx] = recv_obj.in_wires[idx] = None
                            
                            REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                            if recv_obj not in obj_set: UPDATE_OBJECT_OUTPUT(recv_obj)

                        for wr in action.internal_wires:
                            REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                        objects = action.objects

                        for obj in objects:
                            (l:=object_grid[obj.cell]).remove(obj)
                            if not l: del object_grid[obj.cell]
                            logic_objects.remove(obj)

                        # del logic_objects[-len(objects):]

                    elif cls is MODIFY_INPUT_COUNT_ACTION:
                        following_input_count = action.input_count

                        obj_data = action.object_data

                        for i in range(0, len(obj_data), 3):
                            obj = obj_data[i]
                            prior_count = obj_data[i+1]

                            if following_input_count > prior_count:
                                obj.in_wires += (l:=[None] * (following_input_count - prior_count))
                                obj.inputs  += l

                                if (cls:=obj.__class__) is AND_GATE or cls is NAND_GATE:
                                    UPDATE_OBJECT_OUTPUT(obj)
                            else:
                                del obj.inputs[following_input_count:]
                                del obj.in_wires[following_input_count:]

                                for wr in obj_data[i+2]:
                                    if wr:
                                        tran_obj = wr.tran_obj

                                        tran_obj.out_wires.remove(wr)
                                        tran_obj.outputs.remove(obj)
                                        
                                        REMOVE_SEGMENTS_AND_NODES(wr.segments, wr.nodes, segment_cx, segment_cy, wire_node_grid)

                                UPDATE_OBJECT_OUTPUT(obj)
                            
                            obj.input_count = following_input_count

                            UPDATE_END_NODES_INPUT_MODIFICATION(obj, following_input_count, INV_GRID_CELL_SIZE, NODE_POSITIONS[obj.__class__][obj.orient][following_input_count], segment_cx, segment_cy)

            # rotate
            if jkeys[K_R]:
                if OBJECT_PLACER.active:
                    OBJECT_PLACER.orient = (OBJECT_PLACER.orient + 1) & 0b11
                elif selected_obj_list or selected_node_list: 
                    lmb_was_click = False

                    center_x = (min_x_bound + max_x_bound) * 0.5
                    center_y = (min_y_bound + max_y_bound) * 0.5

                    nodes_to_update = selected_node_list.copy()

                    dx = min_x_bound - center_x; dy = min_y_bound - center_y
                    min_x_bound = center_x + dy; max_x_bound = center_x - dy
                    min_y_bound = center_y + dx; max_y_bound = center_y - dx 

                    if not drag_uninitiated:
                        drag_uninitiated = True

                        END_DRAG_ACTION(selected_obj_list, selected_node_list, obj_action_data, node_action_data, action_log, log_depth, MAX_ACTION_LOG_LENGTH)
                        log_depth = 0

                        obj_action_data = []
                        node_action_data = []

                    if selected_obj_list:
                        obj = selected_obj_list[0]

                        if obj.orient & 1:
                            _, w = SIZES[cls:=obj.__class__][obj.input_count]
                        else:
                            w, _ = SIZES[cls:=obj.__class__][obj.input_count]
                            
                        offset_x += center_x - center_y + obj.y - drag_obj_x[0]; offset_y += center_y + center_x - obj.x - w - drag_obj_y[0]

                        for i, obj in enumerate(selected_obj_list):
                            if (o:=obj.orient) & 1:
                                _, w = SIZES[cls:=obj.__class__][ic:=obj.input_count]
                            else:
                                w, _ = SIZES[cls:=obj.__class__][ic:=obj.input_count]

                            x = center_x - center_y + obj.y; y = center_y + center_x - obj.x - w

                            cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))

                            old_cell = obj.cell
                            if cell != old_cell:
                                (l:=object_grid[old_cell]).remove(obj)
                                if not l: del object_grid[old_cell]

                                if not (l:=object_grid.get(cell)):
                                    object_grid[cell] = {obj}
                                else:
                                    l.add(obj)

                                obj.cell = cell
    
                            o = (o + 1) & 0b11

                            obj.x = drag_obj_x[i] = x; obj.y = drag_obj_y[i] = y
                            obj.orient = o

                            nodes = NODE_POSITIONS[cls][o][ic]

                            # update wire positions
                            is_gate = cls in GATE
                            if is_gate or cls in NO_OUTPUT:
                                for wr in obj.in_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.recv_idx]

                                        (n:=wr.nodes[-1]).x = obj.x + nx 
                                        n.y = obj.y + ny

                                        nodes_to_update.append(n)

                            if is_gate or cls in NO_INPUT:
                                for wr in obj.out_wires:
                                    if wr is not None:
                                        nx, ny = nodes[wr.tran_idx]

                                        (n:=wr.nodes[0]).x = obj.x + nx 
                                        n.y = obj.y + ny

                                        nodes_to_update.append(n)
                    else:
                        n = selected_node_list[0]
                            
                        offset_x += center_x - center_y + n.y - drag_node_x[0]; offset_y += center_y + center_x - n.x - drag_node_y[0]

                    for i, n in enumerate(selected_node_list):
                        x = center_x - center_y + n.y; y = center_y + center_x - n.x

                        n.x = drag_node_x[i] = x; n.y = drag_node_y[i] = y

                    UPDATE_SEGMENTS_AND_NODES(INV_GRID_CELL_SIZE, nodes_to_update, wire_node_grid, segment_cx, segment_cy)

                    if log_depth:
                        del action_log[-log_depth:]
                        log_depth = 0

                    if len(action_log) > MAX_ACTION_LOG_LENGTH:
                        del action_log[0]

                    action_log.append(ROTATE_SELECTION_ACTION(selected_obj_list.copy(), selected_node_list.copy(), center_x, center_y))

        # dragging
        if lmb and (clicked_obj or clicked_wire_node) and clicked_logic_element and (selected_obj_list or selected_node_list):      
            # first object establishes how much each following object should be displaced
            if selected_obj_list:
                dx = (x:=mx + offset_x) - drag_obj_x[0]; dy = (y:=my + offset_y) - drag_obj_y[0]
            else:
                dx = (x:=mx + offset_x) - drag_node_x[0]; dy = (y:=my + offset_y) - drag_node_y[0]

            min_x_bound = min_y_bound = INF
            max_x_bound = max_y_bound = NEG_INF

            nodes_to_update = selected_node_list.copy()

            for i, obj in enumerate(selected_obj_list):
                if drag_uninitiated:
                    obj_action_data += (obj, obj.x, obj.y)

                drag_obj_x[i] = x = drag_obj_x[i] + dx
                drag_obj_y[i] = y = drag_obj_y[i] + dy      

                if snap_to_grid: 
                    x = FLOOR((x + HALF_SNAP) * INV_SNAP) * SNAP_RES
                    y = FLOOR((y + HALF_SNAP) * INV_SNAP) * SNAP_RES

                obj.x = x; obj.y = y

                if (o:=obj.orient) & 1:
                    h, w = SIZES[cls:=obj.__class__][ic:=obj.input_count]
                else:
                    w, h = SIZES[cls:=obj.__class__][ic:=obj.input_count]

                if x < min_x_bound:     min_x_bound = x
                if x + w > max_x_bound: max_x_bound = x + w
                if y < min_y_bound:     min_y_bound = y
                if y + h > max_y_bound: max_y_bound = y + h

                nodes = NODE_POSITIONS[cls][obj.orient][ic]

                # update wire positions
                is_gate = cls in GATE
                if is_gate or cls in NO_OUTPUT:
                    for wr in obj.in_wires:
                        if wr is not None:
                            nx, ny = nodes[wr.recv_idx]

                            (n:=wr.nodes[-1]).x = x + nx 
                            n.y = y + ny

                            nodes_to_update.append(n)

                if is_gate or cls in NO_INPUT:
                    for wr in obj.out_wires:
                        if wr is not None:
                            nx, ny = nodes[wr.tran_idx]

                            (n:=wr.nodes[0]).x = x + nx 
                            n.y = y + ny

                            nodes_to_update.append(n)

                # grid cell relocation 
                cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))
                if cell != obj.cell:
                    (l:=object_grid[obj.cell]).remove(obj)
                    if not l: del object_grid[obj.cell]

                    if not (l:=object_grid.get(cell)):
                        object_grid[cell] = {obj}
                    else:   
                        l.add(obj)

                    obj.cell = cell

            for i, n in enumerate(selected_node_list):
                if drag_uninitiated:
                    node_action_data += (n, n.x, n.y)

                drag_node_x[i] = x = drag_node_x[i] + dx
                drag_node_y[i] = y = drag_node_y[i] + dy      

                if snap_to_grid: 
                    x = FLOOR((x + HALF_SNAP) * INV_SNAP) * SNAP_RES
                    y = FLOOR((y + HALF_SNAP) * INV_SNAP) * SNAP_RES

                n.x = x; n.y = y

                if x < min_x_bound:   min_x_bound = x
                elif x > max_x_bound: max_x_bound = x
                if y < min_y_bound:   min_y_bound = y
                elif y > max_y_bound: max_y_bound = y

            UPDATE_SEGMENTS_AND_NODES(INV_GRID_CELL_SIZE, nodes_to_update, wire_node_grid, segment_cx, segment_cy)

            drag_uninitiated = False
                                
        if OBJECT_PLACER.active:
            x = mx
            y = my
            if snap_to_grid: 
                x = FLOOR((x + HALF_SNAP) * INV_SNAP) * SNAP_RES
                y = FLOOR((y + HALF_SNAP) * INV_SNAP) * SNAP_RES

            OBJECT_PLACER.x = x
            OBJECT_PLACER.y = y   
                
            if rlmb:
                if not over_gui_element:
                    if (o:=OBJECT_PLACER.orient) & 1:
                        h, w = HALF_SIZES[cls:=OBJECT_PLACER.cls][ic:=OBJECT_PLACER.input_count]
                    else:
                        w, h = HALF_SIZES[cls:=OBJECT_PLACER.cls][ic:=OBJECT_PLACER.input_count]

                    x -= w; y -= h
                    cell = (FLOOR(x * INV_GRID_CELL_SIZE), FLOOR(y * INV_GRID_CELL_SIZE))
                    logic_objects.append(obj:=cls(x, y, cell, ic))
                    obj.orient = o

                    if not (l:=object_grid.get(cell)):
                        object_grid[cell] = {obj}
                    else:
                        l.add(obj)

                    if log_depth:
                        del action_log[-log_depth:]
                        log_depth = 0

                    if len(action_log) > MAX_ACTION_LOG_LENGTH:
                        del action_log[0]

                    action_log.append(PLACE_OBJECTS_ACTION([obj], []))

                OBJECT_PLACER.active = False

        if wr_attacher:
            wr_attacher.end_x = mouse_x
            wr_attacher.end_y = mouse_y
            obj = wr_attacher.obj
            if wr_attacher.idx == obj.input_count: 
                wr_attacher.signal = obj.output

        if selection:
            selection.x2 = mx
            selection.y2 = my

        RENDER(
            WIN_BUFFER, 
            (win_x, win_y, hwx, hwy), 
            (cam_x, cam_y, zoom), 
            GRID_CELL_SIZE, 
            logic_objects, 
            selected_obj_set, 
            selected_node_set,
            selected_wire_set,
            RENDER_MANAGER,
            GUI_ELEMENTS,
            near_node, 
            wr_attacher, 
            selection
        )

        WINDOW.blit(WIN_BUFFER)

        DISPLAY_FLIP()

        if (frame_time := TIME() - frame_start) < TARGET_DELAY:
            SLEEP(TARGET_DELAY - frame_time)
            delta_time = TARGET_DELAY
        else:
            delta_time = frame_time

    pygame.quit()

    update_config(
        cam_speed,
        swift_multiplier,
        PROP_MANAGER.CYCLIC_CIRCUIT_UPDATE_FREQUENCY,
        ('' if FILE_DROPDOWN.selected is DROPDOWN_NULL_SELECTION else FILE_DROPDOWN.options[FILE_DROPDOWN.selected]),
        ('' if SAVE_DROPDOWN.selected is DROPDOWN_NULL_SELECTION else SAVE_DROPDOWN.options[SAVE_DROPDOWN.selected]),
    )

if __name__ == '__main__':
    main()
