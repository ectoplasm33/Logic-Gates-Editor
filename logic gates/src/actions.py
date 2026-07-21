__all__ = [
    'attach_wire_action',
    'node_insertion_action',
    'place_objects_action',
    'flip_switch_action',
    'move_selection_action',
    'rotate_selection_action',
    'delete_selection_action',
    'modify_input_count_action',
]

cell = tuple[int, int]

class attach_wire_action:
    def __init__(self, wire: object, overwritten_wire: object,/) -> None:
        self.wire = wire
        self.over_wire = overwritten_wire

    def __repr__(self,/):
        return f'atchwr: {id(self)}'

class node_insertion_action:
    def __init__(self, node: object, idx: int,/) -> None:
        self.node = node
        self.idx = idx

    def __repr__(self,/):
        return f'nodei: {id(self)}'

class place_objects_action:
    def __init__(self, objects: list[object], wires: list[object],/) -> None:
        self.objects = objects
        self.wires = wires

    def __repr__(self,/):
        return f'place: {id(self)}'
    
class flip_switch_action:
    def __init__(self, toggle: object,/) -> None:
        self.toggle = toggle

    def __repr__(self,/):
        return f'tog: {id(self)}'

class move_selection_action:
    def __init__(self, object_data: list[object, float, float], node_data: list[object, float, float],/) -> None:
        '''
        list format: instance | dx | dy
        '''
        self.object_data = object_data
        self.node_data = node_data

    def __repr__(self,/):
        return f'move: {id(self)}'

class rotate_selection_action:
    def __init__(self, objects: list[object], nodes: list[object], center_x: float, center_y: float,/) -> None:
        self.objects = objects
        self.nodes = nodes
        self.center_x = center_x
        self.center_y = center_y

    def __repr__(self,/):
        return f'rot: {id(self)}'
    
class delete_selection_action:
    def __init__(self, 
        objects: list[object],
        objects_set: set[object],
        node_data: list[object, int], 
        wires: list[object], 
        internal_wires: list[object],
        /) -> None:
        '''
        node_data format: instance | index
        '''
        self.objects = objects
        self.objects_set = objects_set
        self.node_data = node_data
        self.wires = wires
        self.internal_wires = internal_wires

    def __repr__(self,/):
        return f'del: {id(self)}'
    
class modify_input_count_action:
    def __init__(self, object_data: list[object, int, list[object] | None], input_count: int,/) -> None:
        '''
        object_data format: instance | prior input count | truncated inputs
        '''
        self.object_data = object_data
        self.input_count = input_count