from struct import Struct
from zlib import compress, decompress

from logic_objects import (
    OR_gate,            AND_gate,           XOR_gate,
    NOR_gate,           NAND_gate,          XNOR_gate,
    buffer,             NOT_gate,
    toggle_switch,      light,
    horizontal_display, vertical_display,

    wire_node,          wire_segment,       wire,

    GATE_OBJECTS,       NO_OUTPUT_OBJECTS,
    
    logic_object,       LOGIC_OBJECTS,
)

__all__ = [
    'serialize_current_state',
    'deserialize_save',
]

INVALID_DATA_ERROR = object()
UNSUPPORTED_VERSION_ERROR = object()

_SERIALIZATION_OBJECT_TYPE_KEY = {
    cls: i
    for i, cls in enumerate(LOGIC_OBJECTS)
}

_DESERIALIZATION_OBJECT_TYPE_KEY = {
    i: cls 
    for i, cls in enumerate(LOGIC_OBJECTS)
}

_RENDER_KEYS = {
    OR_gate:            OR_gate.DEFAULT_RENDER_KEY,
    AND_gate:           AND_gate.DEFAULT_RENDER_KEY,
    XOR_gate:           XOR_gate.DEFAULT_RENDER_KEY,
    NOR_gate:           NOR_gate.DEFAULT_RENDER_KEY,
    NAND_gate:          NAND_gate.DEFAULT_RENDER_KEY,
    XNOR_gate:          XNOR_gate.DEFAULT_RENDER_KEY,
    buffer:             buffer.DEFAULT_RENDER_KEY,
    NOT_gate:           NOT_gate.DEFAULT_RENDER_KEY,
    toggle_switch:      (toggle_switch.ON_KEY, toggle_switch.OFF_KEY),
    light:              (light.ON_KEY, light.OFF_KEY),
    horizontal_display: horizontal_display.DISPLAY_KEYS,
    vertical_display:   vertical_display.DISPLAY_KEYS,
}

def BYTES(n: int, size: int, signed: bool = False, __BYTES=int.to_bytes,/): 
    if signed:
        m = 1 << ((size << 3) - 1)
        return __BYTES(n, size, 'little', signed=signed) if -m <= n < m else (b'\x00' * (size - 1) + b'\x80' if n < 0 else b'\xff' * (size - 1) + b'\x7f')
    else:
        return __BYTES(n, size, 'little') if n < (1 << (size << 3)) else b'\xff' * size

def serialize_current_state(
    cam: tuple[float, float, float], 
    logic_objects: list[logic_object], 
    prop_manager,
    selected: tuple[set[logic_object], set[wire_node], set[wire]],
    __BYTES       = BYTES,
    __PACK        = Struct('<d').pack,
    __GATE        = GATE_OBJECTS,
    __NO_OUTPUT   = NO_OUTPUT_OBJECTS,
    __OBJECT_TYPE = _SERIALIZATION_OBJECT_TYPE_KEY,
    /) -> bytes:
    
    INDEX_SIZE = 4
    OBJECT_TYPE_SIZE = 1
    CELL_SIZE = 8
    NUM_INPUT_SIZE = 1
    OUTPUT_SIZE = 1
    ORIENT_SIZE = 1
    NODE_COUNT_SIZE = 2

    cam_x, cam_y, zoom = cam
    obj_set, node_set, wire_set = selected

    save_data = bytearray(b'\x01\x00\x00\x00') # serialization version (little endian)
    
    save_data += __PACK(cam_x)
    save_data += __PACK(cam_y)
    save_data += __PACK(zoom)

    object_indices = {
        obj: i
        for i, obj in enumerate(logic_objects)
    }

    wires = []
    selected_objs = []
    selected_nodes = []
    selected_wires = []

    save_data += __BYTES(len(logic_objects), INDEX_SIZE)

    for i, obj in enumerate(logic_objects):
        cls = obj.__class__

        save_data += __BYTES(__OBJECT_TYPE[cls], OBJECT_TYPE_SIZE)

        save_data += __PACK(obj.x)
        save_data += __PACK(obj.y)

        cx, cy = obj.cell
        save_data += __BYTES(cx, CELL_SIZE, True)
        save_data += __BYTES(cy, CELL_SIZE, True)

        save_data += __BYTES(obj.input_count, NUM_INPUT_SIZE)

        if (out:=obj.output) is False:
            out = 0
        elif out is True:
            out = 1

        save_data += __BYTES(out, OUTPUT_SIZE)

        save_data += __BYTES(obj.orient, ORIENT_SIZE)

        if cls in __GATE or cls in __NO_OUTPUT:
            for wr in obj.in_wires:
                if wr: wires.append(wr)

        if obj in obj_set: selected_objs.append(i)
    
    save_data += __BYTES(len(wires), INDEX_SIZE)

    for i, wr in enumerate(wires):
        save_data += __BYTES(object_indices[wr.tran_obj], INDEX_SIZE)
        save_data += __BYTES(wr.tran_idx, NUM_INPUT_SIZE)

        recv_obj_idx = object_indices[wr.recv_obj]

        save_data += __BYTES(recv_obj_idx, INDEX_SIZE)
        save_data += __BYTES(wr.recv_idx, NUM_INPUT_SIZE)

        save_data += b'\x01' if wr.signal else b'\x00'

        nodes = wr.nodes
        save_data += __BYTES(len(nodes), NODE_COUNT_SIZE)

        for j, n in enumerate(nodes):
            save_data += __PACK(n.x)
            save_data += __PACK(n.y)
            save_data += __BYTES(n.cx, CELL_SIZE, True)
            save_data += __BYTES(n.cy, CELL_SIZE, True)

            if n in node_set: selected_nodes.append((i, j))

        if wr in wire_set: selected_wires.append((recv_obj_idx, wr.recv_idx))
    
    cyclic_objects = prop_manager.cyclic_circuit_objs

    save_data += __BYTES(len(cyclic_objects), INDEX_SIZE)

    for obj in cyclic_objects:
        save_data += __BYTES(object_indices[obj], INDEX_SIZE)

    cyclic_circuits = prop_manager.cyclic_circuits

    save_data += __BYTES(len(cyclic_circuits), INDEX_SIZE)

    for circuit in cyclic_circuits:
        save_data += __BYTES(len(circuit), INDEX_SIZE)
        for obj in circuit:
            save_data += __BYTES(object_indices[obj], INDEX_SIZE)

    cyclic_queue = prop_manager.cyclic_queue

    save_data += __BYTES(len(cyclic_queue), INDEX_SIZE)

    for obj in cyclic_queue:
        save_data += __BYTES(object_indices[obj], INDEX_SIZE)

    save_data += __BYTES(len(selected_objs), INDEX_SIZE)

    for obj_idx in selected_objs:
        save_data += __BYTES(obj_idx, INDEX_SIZE)

    save_data += __BYTES(len(selected_nodes), INDEX_SIZE)

    for wire_idx, node_idx in selected_nodes:
        save_data += __BYTES(wire_idx, INDEX_SIZE)
        save_data += __BYTES(node_idx, NODE_COUNT_SIZE)

    save_data += __BYTES(len(selected_wires), INDEX_SIZE)

    for obj_idx, node_idx in selected_wires:
        save_data += __BYTES(obj_idx, INDEX_SIZE)
        save_data += __BYTES(node_idx, NUM_INPUT_SIZE)

    return compress(save_data)

def deserialize_save(
    save_data: bytes,
    __INT           = int.from_bytes,
    __UNPACK        = Struct('<d').unpack,
    __DUAL_UNPACK   = Struct('<dd').unpack,
    __OBJECT_TYPE   = _DESERIALIZATION_OBJECT_TYPE_KEY,
    __RENDER_KEYS   = _RENDER_KEYS,
    __DEFAULT_KEYS  = {OR_gate, AND_gate, XOR_gate, NOR_gate, NAND_gate, XNOR_gate, buffer, NOT_gate},
    __TOGGLE        = toggle_switch,
    __LIGHT         = light,
    __HDISPLAY      = horizontal_display,
    __VDISPLAY      = vertical_display,
    __WIRE          = wire,
    __WIRE_NODE     = wire_node,
    __WIRE_SEG      = wire_segment,
    /) -> tuple[
    tuple[float, float, float], 
    list[logic_object], 
    tuple[set[logic_object], list[set[logic_object]], list[logic_object]], 
    tuple[list[logic_object], list[wire_node], list[wire]],
    tuple[dict[tuple[int, int], logic_object], dict[tuple[int, int], wire_node], dict[int, wire_segment], dict[int, wire_segment]]
    ]:
    try:
        decompressed = decompress(save_data)
    except:
        return INVALID_DATA_ERROR
    
    mv = memoryview(decompressed)
    if len(mv) >= 4:
        version_tag = __INT(mv[:4], 'little')
    else:
        return INVALID_DATA_ERROR

    if version_tag == 1:
        INDEX_SIZE = 4
        OBJECT_TYPE_SIZE = 1
        CELL_SIZE = 8
        NUM_INPUT_SIZE = 1
        ORIENT_SIZE = 1
        NODE_COUNT_SIZE = 2

        o = 4 # offset 

        cam = __DUAL_UNPACK(mv[o:o+16]) + __UNPACK(mv[o+16:o+24])
        o += 24

        logic_objects = []
        cyclic_objects = set()
        cyclic_circuits = []
        cyclic_queue = []
        selected_objs = []
        selected_nodes = []
        selected_wires = []
        wires = []

        object_grid = {}
        wire_node_grid = {}
        segment_cx = {}
        segment_cy = {}

        obj_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE

        for _ in range(obj_count):
            obj_cls = __OBJECT_TYPE[__INT(mv[o:o+OBJECT_TYPE_SIZE], 'little')]
            o += OBJECT_TYPE_SIZE

            x, y = __DUAL_UNPACK(mv[o:o+16])
            o += 16

            cx = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
            o += CELL_SIZE
            cy = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
            o += CELL_SIZE
            cell = (cx, cy)

            input_count = __INT(mv[o:o+NUM_INPUT_SIZE], 'little')
            o += NUM_INPUT_SIZE

            if obj_cls is not __HDISPLAY:
                output = True if __INT(mv[o:o+1], 'little') else False
            else:
                output = __INT(mv[o:o+1], 'little')
            o += 1

            orient = __INT(mv[o:o+ORIENT_SIZE], 'little')
            o += ORIENT_SIZE

            if obj_cls in __DEFAULT_KEYS:
                key = __RENDER_KEYS[obj_cls]
            elif obj_cls is __TOGGLE or obj_cls is __LIGHT:
                if output: key, _ = __RENDER_KEYS[obj_cls]
                else: _, key = __RENDER_KEYS[obj_cls]
            elif obj_cls is __HDISPLAY or obj_cls is __VDISPLAY:
                key = __RENDER_KEYS[obj_cls][output]

            obj = obj_cls(x, y, cell, input_count, key)
            obj.output = output
            obj.orient = orient

            logic_objects.append(obj)

            if not (l:=object_grid.get(cell)):
                object_grid[cell] = {obj}
            else:
                l.add(obj)

        wire_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE

        for _ in range(wire_count):
            tran_obj_idx = __INT(mv[o:o+INDEX_SIZE], 'little')
            o += INDEX_SIZE
            tran_idx = __INT(mv[o:o+NUM_INPUT_SIZE], 'little')
            o += NUM_INPUT_SIZE

            recv_obj_idx = __INT(mv[o:o+INDEX_SIZE], 'little')
            o += INDEX_SIZE
            recv_idx = __INT(mv[o:o+NUM_INPUT_SIZE], 'little')
            o += NUM_INPUT_SIZE

            signal = True if __INT(mv[o:o+1], 'little') else False
            o += 1

            node_count = __INT(mv[o:o+NODE_COUNT_SIZE], 'little')
            o += NODE_COUNT_SIZE

            nodes = []

            x, y = __DUAL_UNPACK(mv[o:o+16])
            o += 16

            cx = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
            o += CELL_SIZE
            cy = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
            o += CELL_SIZE
            
            nodes.append(__WIRE_NODE(x, y, cx, cy))

            for _ in range(node_count-2):
                x, y = __DUAL_UNPACK(mv[o:o+16])
                o += 16

                cx = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
                o += CELL_SIZE
                cy = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
                o += CELL_SIZE
                
                nodes.append(n:=__WIRE_NODE(x, y, cx, cy))

                if not (l:=wire_node_grid.get((cx, cy))):
                    wire_node_grid[(cx, cy)] = {n}
                else:
                    l.add(n)

            x, y = __DUAL_UNPACK(mv[o:o+16])
            o += 16

            cx = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
            o += CELL_SIZE
            cy = __INT(mv[o:o+CELL_SIZE], 'little', signed=True)
            o += CELL_SIZE
            
            nodes.append(__WIRE_NODE(x, y, cx, cy))

            segments = []

            tran_obj = logic_objects[tran_obj_idx]
            recv_obj = logic_objects[recv_obj_idx]
            wr = __WIRE(tran_obj, tran_idx, recv_obj, recv_idx, nodes, segments)
            wr.signal = signal
            wires.append(wr)

            if nodes:
                node1 = next(it:=iter(nodes))
                for node2 in it:
                    segments.append(seg:=__WIRE_SEG(node1, node2, wr))
                    node1.seg1 = seg
                    node2.seg2 = seg
                
                    min_cx = node1.cx; max_cx = node2.cx
                    min_cy = node1.cy; max_cy = node2.cy

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

            tran_obj.outputs.append(recv_obj)
            tran_obj.out_wires.append(wr)

            recv_obj.inputs[recv_idx] = tran_obj
            recv_obj.in_wires[recv_idx] = wr

        cyclic_object_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE
        for _ in range(cyclic_object_count):
            cyclic_objects.add(logic_objects[__INT(mv[o:o+INDEX_SIZE], 'little')])
            o += INDEX_SIZE

        cyclic_circuit_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE
        for _ in range(cyclic_circuit_count):
            circuit_size = __INT(mv[o:o+INDEX_SIZE], 'little')
            o += INDEX_SIZE
            circuit = set()
            for _ in range(circuit_size):
                circuit.add(logic_objects[__INT(mv[o:o+INDEX_SIZE], 'little')])
                o += INDEX_SIZE
            cyclic_circuits.append(circuit)

        cyclic_queue_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE
        for _ in range(cyclic_queue_count):
            cyclic_queue.append(logic_objects[__INT(mv[o:o+INDEX_SIZE], 'little')])
            o += INDEX_SIZE

        selected_obj_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE
        for _ in range(selected_obj_count):
            selected_objs.append(logic_objects[__INT(mv[o:o+INDEX_SIZE], 'little')])
            o += INDEX_SIZE

        selected_node_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE
        for _ in range(selected_node_count):
            wire_idx = __INT(mv[o:o+INDEX_SIZE], 'little')
            o += INDEX_SIZE
            node_idx = __INT(mv[o:o+NODE_COUNT_SIZE], 'little')
            o += NODE_COUNT_SIZE
            selected_nodes.append(wires[wire_idx].nodes[node_idx])

        selected_wire_count = __INT(mv[o:o+INDEX_SIZE], 'little')
        o += INDEX_SIZE
        for _ in range(selected_wire_count):
            obj_idx = __INT(mv[o:o+INDEX_SIZE], 'little')
            o += INDEX_SIZE
            node_idx = __INT(mv[o:o+NUM_INPUT_SIZE], 'little')
            o += NUM_INPUT_SIZE
            selected_wires.append(logic_objects[obj_idx].in_wires[node_idx])

        return (
            cam,
            logic_objects,
            (cyclic_objects, cyclic_circuits, cyclic_queue),
            (selected_objs, selected_nodes, selected_wires),
            (object_grid, wire_node_grid, segment_cx, segment_cy)
        )

    return UNSUPPORTED_VERSION_ERROR # unsupported version
