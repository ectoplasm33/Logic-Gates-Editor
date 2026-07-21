__all__ = [
    'RENDER_SCALE',
    'logic_gate',
    'OR_gate',
    'AND_gate',
    'XOR_gate',
    'NOR_gate',
    'NAND_gate',
    'XNOR_gate',
    'buffer',
    'NOT_gate',
    'toggle_switch',
    'light',
    'horizontal_display',
    'vertical_display',
    'node',
    'wire_node',
    'wire_segment',
    'wire',
    'wire_attacher',
    'logic_object',
    'LOGIC_OBJECTS',
    'GATE_OBJECTS',
    'NO_INPUT_OBJECTS',
    'NO_OUTPUT_OBJECTS',
    'serialize_current_state',
    'deserialize_save',
]

RENDER_SCALE = 3.5

def _init_node_positions(
    default_positions: tuple[tuple[tuple[int, int], ...]],
    sizes: tuple[tuple[int, int]],
    /) -> tuple[tuple[tuple[tuple[int, int], ...]], ...]:
    l1 = []
    l2 = []
    l3 = []

    for size, nodes in zip(sizes, default_positions):
        if not nodes:
            l1.append(None)
            l2.append(None)
            l3.append(None)
            continue
        
        w, h = size

        l1.append(tuple((y, w - x) for x, y in nodes))
        l2.append(tuple((w - x, h - y) for x, y in nodes))
        l3.append(tuple((h - y, x) for x, y in nodes))

    return (
        default_positions,
        tuple(l1),
        tuple(l2),
        tuple(l3),
    )

def _init_bounding_rects(default_rects: tuple[tuple[int, int, int, int]], sizes: tuple[tuple[int, int]],/) -> tuple[tuple[tuple[int, int, int, int]]]:
    l1 = []
    l2 = []
    l3 = []

    for size, rect in zip(sizes, default_rects):
        if not rect:
            l1.append(None)
            l2.append(None)
            l3.append(None)
            continue
        
        w, h = size
        rx, ry, rw, rh = rect

        l1.append((ry, w - (rx + rw), rh, rw))
        l2.append((w - (rx + rw), h - (ry + rh), rw, rh))
        l3.append((h - (ry + rh), rx, rh, rw))

    return (
        default_rects,
        tuple(l1),
        tuple(l2),
        tuple(l3),
    )

def _init_render_sizes(sizes: tuple[tuple[int, int]], scale: int) -> tuple[tuple[int, int]]:
    l = []

    for size in sizes:
        if not size:
            l.append(None)
            continue

        w, h = size
        l.append((w*scale, h*scale))

    return l 

# parent class
class logic_gate:
    SIZES = (
        None,
        (150, 100),
        (150, 100),
        (150, 100),
        (150, 100),
        (150, 125),
        (150, 150),
        (150, 175),
        (150, 200),
    )
    SCALE = RENDER_SCALE
    RENDER_SIZES = _init_render_sizes(SIZES, SCALE)

    DEFAULT_ORIENT_NODES = (
        None,
        (
            (12.5,50.0),
            (137.5,50.0),
        ),
        (
            (12.5,37.5),
            (12.5,62.5),
            (137.5,50.0),
        ),
        (
            (12.5,25.0),
            (12.5,50.0),
            (12.5,75.0),
            (137.5,50.0),
        ),
        (
            (12.5,12.5),
            (12.5,37.5),
            (12.5,62.5),
            (12.5,87.5),
            (137.5,50.0),
        ),
        (
            (12.5,12.5),
            (12.5,37.5),
            (12.5,62.5),
            (12.5,87.5),
            (12.5,112.5),
            (137.5,62.5),
        ),
        (
            (12.5,12.5),
            (12.5,37.5),
            (12.5,62.5),
            (12.5,87.5),
            (12.5,112.5),
            (12.5,137.5),
            (137.5,75.0),
        ),
        (
            (12.5,12.5),
            (12.5,37.5),
            (12.5,62.5),
            (12.5,87.5),
            (12.5,112.5),
            (12.5,137.5),
            (12.5,162.5),
            (137.5,87.5),
        ),
        (
            (12.5,12.5),
            (12.5,37.5),
            (12.5,62.5),
            (12.5,87.5),
            (12.5,112.5),
            (12.5,137.5),
            (12.5,162.5),
            (12.5,187.5),
            (137.5,100.0),
        ),
    )
    NODE_POSITIONS = _init_node_positions(DEFAULT_ORIENT_NODES, SIZES)

    __slots__ = [
        'x', 'y',
        'cell',
        'input_count',
        'inputs', 'outputs',
        'in_wires', 'out_wires',
        'output',
        'orient',
        'prop_inst',
        'last_update_source',
        'render_key',
    ]

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int, default_output: bool, render_key: object,/) -> None:
        self.x = x
        self.y = y
        self.cell = cell
        
        self.input_count = input_count
        self.inputs = [None] * input_count
        self.in_wires = [None] * input_count

        self.output = default_output
        self.outputs = []
        self.out_wires = []

        self.orient = 0

        self.prop_inst = None
        self.last_update_source = None

        self.render_key = render_key

class OR_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        None, None,
        (39.2, 14.3, 67.8, 71.4),
        (39.2, 14.3, 67.8, 71.4),
        (39.2, 1.8, 67.8, 96.4),
        (39.2, 1.8, 67.8, 121.4),
        (39.2, 1.8, 67.8, 146.4),
        (39.2, 1.8, 67.8, 171.4),
        (39.2, 1.8, 67.8, 196.4),
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = (
        None, None,
        (
            (39.2, 14.3),
            (59, 15.5),
            (77, 21.5),
            (92, 32.8),
            (107, 50.0),
            (92, 67.2),
            (77, 78.5),
            (59, 84.5),
            (39.2, 85.7),
            (44.5, 67.0),
            (44.5, 35.0),
        ),
        (
            (39.2, 14.3),
            (59, 15.5),
            (77, 21.5),
            (92, 32.8),
            (107, 50.0),
            (92, 67.2),
            (77, 78.5),
            (59, 84.5),
            (39.2, 85.7),
            (44.5, 67.0),
            (44.5, 35.0),
        ),
        (
            (39.2, 1.8000000000000007),
            (59, 3.42016806722689),
            (77, 11.521008403361343),
            (92, 26.77759103641456),
            (107, 50.0),
            (92, 73.22240896358544),
            (77, 88.47899159663865),
            (59, 96.5798319327731),
            (39.2, 98.19999999999999),
            (44.5, 72.95238095238095),
            (44.5, 29.747899159663863),
        ),
        (
            (39.2, 1.8000000000000007),
            (59, 3.8403361344537807),
            (77, 14.042016806722689),
            (92, 33.25518207282913),
            (107, 62.5),
            (92, 91.74481792717087),
            (77, 110.95798319327731),
            (59, 121.15966386554622),
            (39.2, 123.2),
            (44.5, 91.4047619047619),
            (44.5, 36.99579831932773),
        ),
        (
            (39.2, 1.8000000000000007),
            (59, 4.260504201680671),
            (77, 16.56302521008403),
            (92, 39.73277310924368),
            (107, 75.0),
            (92, 110.2672268907563),
            (77, 133.43697478991598),
            (59, 145.73949579831933),
            (39.2, 148.20000000000002),
            (44.5, 109.85714285714285),
            (44.5, 44.24369747899159),
        ),
        (
            (39.2, 1.8000000000000007),
            (59, 4.680672268907562),
            (77, 19.084033613445378),
            (92, 46.21036414565826),
            (107, 87.5),
            (92, 128.78963585434175),
            (77, 155.91596638655463),
            (59, 170.31932773109244),
            (39.2, 173.20000000000002),
            (44.5, 128.30952380952382),
            (44.5, 51.491596638655466),
        ),
        (
            (39.2, 1.8000000000000007),
            (59, 5.1008403361344525),
            (77, 21.60504201680672),
            (92, 52.68795518207283),
            (107, 100.0),
            (92, 147.3120448179272),
            (77, 178.3949579831933),
            (59, 194.89915966386556),
            (39.2, 198.20000000000002),
            (44.5, 146.7619047619048),
            (44.5, 58.739495798319325),
        ),
    )

    INPUT_DEFAULT = 2

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: 
        logic_gate.__init__(self, x, y, cell, input_count, False, __DEFAULT_RENDER_KEY)
    
    def __repr__(self,/):
        return f'OR {id(self)}'

class AND_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        None, None,
        (44, 16.5, 59.7, 67.0),
        (44, 16.5, 59.7, 67.0),
        (44, 4.0, 59.7, 92.0),
        (44, 4.0, 59.7, 117.0),
        (44, 4.0, 59.7, 142.0),
        (44, 4.0, 59.7, 167.0),
        (44, 4.0, 59.7, 192.0),
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = (
        None, None,
        (
            (44, 16.5),
            (75.5, 16.5),
            (87.5, 20.5),
            (96.5, 28.3),
            (101.5, 36.7),
            (103.7, 43.8),
            (103.7, 56.2),
            (101.5, 63.3),
            (96.5, 71.7),
            (87.5, 79.5),
            (75.5, 83.5),
            (44, 83.5),
        ),
        (
            (44, 16.5),
            (75.5, 16.5),
            (87.5, 20.5),
            (96.5, 28.3),
            (101.5, 36.7),
            (103.7, 43.8),
            (103.7, 56.2),
            (101.5, 63.3),
            (96.5, 71.7),
            (87.5, 79.5),
            (75.5, 83.5),
            (44, 83.5),
        ),
        (
            (44, 4.0),
            (75.5, 4.0),
            (87.5, 9.492537313432836),
            (96.5, 20.202985074626866),
            (101.5, 31.737313432835823),
            (103.7, 41.4865671641791),
            (103.7, 58.5134328358209),
            (101.5, 68.26268656716417),
            (96.5, 79.79701492537313),
            (87.5, 90.50746268656717),
            (75.5, 96.0),
            (44, 96.0),
        ),
        (
            (44, 4.0),
            (75.5, 4.0),
            (87.5, 10.985074626865671),
            (96.5, 24.605970149253732),
            (101.5, 39.27462686567164),
            (103.7, 51.6731343283582),
            (103.7, 73.3268656716418),
            (101.5, 85.72537313432835),
            (96.5, 100.39402985074626),
            (87.5, 114.01492537313432),
            (75.5, 121.0),
            (44, 121.0),
        ),
        (
            (44, 4.0),
            (75.5, 4.0),
            (87.5, 12.477611940298507),
            (96.5, 29.008955223880598),
            (101.5, 46.811940298507466),
            (103.7, 61.859701492537305),
            (103.7, 88.14029850746269),
            (101.5, 103.18805970149252),
            (96.5, 120.99104477611941),
            (87.5, 137.52238805970148),
            (75.5, 146.0),
            (44, 146.0),
        ),
        (
            (44, 4.0),
            (75.5, 4.0),
            (87.5, 13.970149253731343),
            (96.5, 33.41194029850746),
            (101.5, 54.34925373134329),
            (103.7, 72.0462686567164),
            (103.7, 102.95373134328358),
            (101.5, 120.6507462686567),
            (96.5, 141.58805970149254),
            (87.5, 161.02985074626864),
            (75.5, 171.0),
            (44, 171.0),
        ),
        (
            (44, 4.0),
            (75.5, 4.0),
            (87.5, 15.462686567164178),
            (96.5, 37.81492537313433),
            (101.5, 61.88656716417911),
            (103.7, 82.23283582089552),
            (103.7, 117.76716417910448),
            (101.5, 138.11343283582087),
            (96.5, 162.18507462686566),
            (87.5, 184.53731343283582),
            (75.5, 196.0),
            (44, 196.0),
        ),
    )

    INPUT_DEFAULT = 2

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: 
        logic_gate.__init__(self, x, y, cell, input_count, False, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'AND {id(self)}'

class XOR_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = OR_gate.DEFAULT_ORIENT_BOUNDING_RECTSS
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = OR_gate.HITBOXES

    INPUT_DEFAULT = 2

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: 
        logic_gate.__init__(self, x, y, cell, input_count, False, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'XOR {id(self)}'

class NOR_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = OR_gate.DEFAULT_ORIENT_BOUNDING_RECTSS
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = OR_gate.HITBOXES

    INPUT_DEFAULT = 2

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: 
        logic_gate.__init__(self, x, y, cell, input_count, True, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'NOR {id(self)}'

class NAND_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = AND_gate.DEFAULT_ORIENT_BOUNDING_RECTSS
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = AND_gate.HITBOXES

    INPUT_DEFAULT = 2

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: 
        logic_gate.__init__(self, x, y, cell, input_count, True, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'NAND {id(self)}'

class XNOR_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = OR_gate.DEFAULT_ORIENT_BOUNDING_RECTSS
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = OR_gate.HITBOXES

    INPUT_DEFAULT = 2

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: 
        logic_gate.__init__(self, x, y, cell, input_count, True, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'XNOR {id(self)}'

class buffer(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        None,
        (43,22,64,56)
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = (
        None,
        (
            (41.5,20),
            (109.5,50),
            (41.4,80)
        )
    )

    INPUT_DEFAULT = 1

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: # input_count is listed to keep architecture consistent
        logic_gate.__init__(self, x, y, cell, input_count, False, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'BUFFER {id(self)}'

class NOT_gate(logic_gate):
    DEFAULT_ORIENT_BOUNDING_RECTSS = buffer.DEFAULT_ORIENT_BOUNDING_RECTSS
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, logic_gate.SIZES)
    HITBOXES = buffer.HITBOXES

    INPUT_DEFAULT = 1

    DEFAULT_RENDER_KEY = object()

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: # input_count is listed to keep architecture consistent
        logic_gate.__init__(self, x, y, cell, input_count, True, __DEFAULT_RENDER_KEY)

    def __repr__(self,/):
        return f'NOT {id(self)}'

class toggle_switch:
    INPUT_DEFAULT = 0
    SIZES = (
        (100,50),
    )
    SCALE = RENDER_SCALE
    RENDER_SIZES = _init_render_sizes(SIZES, SCALE)

    DEFAULT_ORIENT_NODES = (
        (
            (75,25),
        ),
    )
    NODE_POSITIONS = _init_node_positions(DEFAULT_ORIENT_NODES, SIZES)
    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        (0,0,50,50),
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, SIZES)
    HITBOXES = (
        (
            (0,4),
            (4,0),
            (46,0),
            (50, 4),
            (50,46),
            (46,50),
            (4,50),
            (0,46)
        ),
    )
 
    ON_KEY = object()
    OFF_KEY = object()

    DEFAULT_RENDER_KEY = OFF_KEY

    __slots__ = [
        'x', 'y',
        'cell',
        'input_count',
        'outputs',
        'out_wires',
        'output',
        'orient',
        'prop_inst',
        'last_update_source',
        'render_key',
    ]

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: # input_count is listed to keep architecture consistent
        self.x = x
        self.y = y
        self.cell = cell

        self.input_count = input_count
        self.outputs = []
        self.out_wires = []
        self.output = False

        self.orient = 0

        self.prop_inst = None
        self.last_update_source = None

        self.render_key = __DEFAULT_RENDER_KEY

    def __repr__(self,/):
        return f'toggle {id(self)}'

class light:
    INPUT_DEFAULT = 1

    SIZES = (
        None,
        (100,50)
    )
    SCALE = RENDER_SCALE
    RENDER_SIZES = _init_render_sizes(SIZES, SCALE)

    DEFAULT_ORIENT_NODES = (
        None,
        (
            (25,25),
        ),
    )
    NODE_POSITIONS = _init_node_positions(DEFAULT_ORIENT_NODES, SIZES)

    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        None,
        (50,0,50,50),
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, SIZES)
    HITBOXES = (
        None,
        (
            (50,4),
            (54,0),
            (96,0),
            (100, 4),
            (100,46),
            (96,50),
            (54,50),
            (50,46)
        ),
    )

    ON_KEY = object()
    OFF_KEY = object()

    DEFAULT_RENDER_KEY = OFF_KEY

    __slots__ = [
        'x', 'y',
        'cell',
        'input_count',
        'inputs',
        'in_wires',
        'output',
        'orient',
        'prop_inst',
        'last_update_source',
        'render_key'
    ]

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: # input_count is listed to keep architecture consistent
        self.x = x
        self.y = y
        self.cell = cell

        self.input_count = input_count
        self.inputs = [None]
        self.in_wires = [None]
        self.output = False

        self.orient = 0

        self.prop_inst = None
        self.last_update_source = None

        self.render_key = __DEFAULT_RENDER_KEY

    def __repr__(self,/):
        return f'light {id(self)}'

class horizontal_display:
    INPUT_DEFAULT = 4

    SIZES = (
        None,None,None,None,
        (100,150)
    )
    SCALE = RENDER_SCALE
    RENDER_SIZES = _init_render_sizes(SIZES, SCALE)

    DEFAULT_ORIENT_NODES = (
        None,None,None,None,
        (
            (87.5,125), (62.5,125), (37.5,125), (12.5,125),
        ),
    )
    NODE_POSITIONS = _init_node_positions(DEFAULT_ORIENT_NODES, SIZES)

    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        None,None,None,None,
        (0,0,100,100),
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, SIZES)
    HITBOXES = (
        None,None,None,None,
        (
            (0,4),
            (4,0),
            (96,0),
            (100, 4),
            (100,96),
            (96,100),
            (4,100),
            (0,96)
        ),
    )

    DISPLAY_0_KEY = object(); DISPLAY_1_KEY = object(); DISPLAY_2_KEY = object(); DISPLAY_3_KEY = object()
    DISPLAY_4_KEY = object(); DISPLAY_5_KEY = object(); DISPLAY_6_KEY = object(); DISPLAY_7_KEY = object()
    DISPLAY_8_KEY = object(); DISPLAY_9_KEY = object(); DISPLAY_A_KEY = object(); DISPLAY_B_KEY = object()
    DISPLAY_C_KEY = object(); DISPLAY_D_KEY = object(); DISPLAY_E_KEY = object(); DISPLAY_F_KEY = object()

    DISPLAY_KEYS = (
        DISPLAY_0_KEY, DISPLAY_1_KEY, DISPLAY_2_KEY, DISPLAY_3_KEY,
        DISPLAY_4_KEY, DISPLAY_5_KEY, DISPLAY_6_KEY, DISPLAY_7_KEY,
        DISPLAY_8_KEY, DISPLAY_9_KEY, DISPLAY_A_KEY, DISPLAY_B_KEY,
        DISPLAY_C_KEY, DISPLAY_D_KEY, DISPLAY_E_KEY, DISPLAY_F_KEY,
    )

    DEFAULT_RENDER_KEY = DISPLAY_0_KEY

    __slots__ = [
        'x', 'y',
        'cell',
        'input_count',
        'inputs',
        'in_wires',
        'output',
        'orient',
        'prop_inst',
        'last_update_source',
        'render_key',
    ]

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: # input_count is listed to keep architecture consistent
        self.x = x
        self.y = y
        self.cell = cell

        self.input_count = input_count
        self.inputs = [None, None, None, None]
        self.in_wires = [None, None, None, None]
        self.output = False

        self.orient = 0

        self.prop_inst = None
        self.last_update_source = None

        self.render_key = __DEFAULT_RENDER_KEY

    def __repr__(self,/):
        return f'hdisplay {id(self)}'
    
class vertical_display:
    INPUT_DEFAULT = 4

    SIZES = (
        None,None,None,None,
        (150,100)
    )
    SCALE = RENDER_SCALE
    RENDER_SIZES = _init_render_sizes(SIZES, SCALE)

    DEFAULT_ORIENT_NODES = (
        None,None,None,None,
        (
            (25,87.5), (25, 62.5), (25, 37.5), (25, 12.5),
        ),
    )
    NODE_POSITIONS = _init_node_positions(DEFAULT_ORIENT_NODES, SIZES)

    DEFAULT_ORIENT_BOUNDING_RECTSS = (
        None,None,None,None,
        (50,0,100,100),
    )
    BOUNDING_RECTS = _init_bounding_rects(DEFAULT_ORIENT_BOUNDING_RECTSS, SIZES)
    HITBOXES = (
        None,None,None,None,
        (
            (50,4),
            (54,0),
            (146,0),
            (150, 4),
            (150,96),
            (146,100),
            (54,100),
            (50,96)
        ),
    )

    DISPLAY_0_KEY = object(); DISPLAY_1_KEY = object(); DISPLAY_2_KEY = object(); DISPLAY_3_KEY = object()
    DISPLAY_4_KEY = object(); DISPLAY_5_KEY = object(); DISPLAY_6_KEY = object(); DISPLAY_7_KEY = object()
    DISPLAY_8_KEY = object(); DISPLAY_9_KEY = object(); DISPLAY_A_KEY = object(); DISPLAY_B_KEY = object()
    DISPLAY_C_KEY = object(); DISPLAY_D_KEY = object(); DISPLAY_E_KEY = object(); DISPLAY_F_KEY = object()

    DISPLAY_KEYS = (
        DISPLAY_0_KEY, DISPLAY_1_KEY, DISPLAY_2_KEY, DISPLAY_3_KEY,
        DISPLAY_4_KEY, DISPLAY_5_KEY, DISPLAY_6_KEY, DISPLAY_7_KEY,
        DISPLAY_8_KEY, DISPLAY_9_KEY, DISPLAY_A_KEY, DISPLAY_B_KEY,
        DISPLAY_C_KEY, DISPLAY_D_KEY, DISPLAY_E_KEY, DISPLAY_F_KEY,
    )

    DEFAULT_RENDER_KEY = DISPLAY_0_KEY

    __slots__ = [
        'x', 'y',
        'cell',
        'input_count',
        'inputs',
        'in_wires',
        'output',
        'orient',
        'prop_inst',
        'last_update_source',
        'render_key',
    ]

    def __init__(self, x: int, y: int, cell: tuple[int, int], input_count: int = INPUT_DEFAULT, __DEFAULT_RENDER_KEY = DEFAULT_RENDER_KEY,/) -> None: # input_count is listed to keep architecture consistent
        self.x = x
        self.y = y
        self.cell = cell

        self.input_count = input_count
        self.inputs = [None, None, None, None]
        self.in_wires = [None, None, None, None]
        self.output = False

        self.orient = 0

        self.prop_inst = None
        self.last_update_source = None

        self.render_key = __DEFAULT_RENDER_KEY

    def __repr__(self,/):
        return f'vdisplay {id(self)}'

class node:
    SIZE = (18, 18)
    SCALE = RENDER_SCALE
    RENDER_SIZE = (SIZE[0]*SCALE, SIZE[1]*SCALE)

class wire_node:
    SIZE = (18, 18)
    SCALE = RENDER_SCALE
    RENDER_SIZE = (SIZE[0]*SCALE, SIZE[1]*SCALE)
    
    __slots__ = [
        'x',
        'y',
        'cx',
        'cy',
        'seg1',
        'seg2',
    ]

    def __init__(self, x, y, cx = None, cy = None,/) -> None:
        self.x = x
        self.y = y
        self.cx = cx
        self.cy = cy
        self.seg1 = None
        self.seg2 = None

    def __repr__(self,/):
        return f'n: {id(self)}'

class wire_segment:
    __slots__ = [
        'node1',
        'node2',
        'wire',
    ]

    def __init__(self, node1: wire_node, node2: wire_node, parent_wire: wire,/) -> None:
        self.node1 = node1
        self.node2 = node2 
        self.wire = parent_wire

    def __repr__(self,/):
        return f'seg: {id(self)}'

class wire:
    __slots__ = [
        'tran_obj',
        'tran_idx',
        'recv_obj',
        'recv_idx',
        'nodes',
        'segments',
        'signal',
    ]

    def __init__(
        self,
        transmitter_obj: object,
        transmitter_idx: int,
        receiver_obj: object,
        receiver_idx: int,
        nodes: list[wire_node],
        segments: list[wire_segment] | None = None,
        /) -> None:
        self.tran_obj = transmitter_obj
        self.tran_idx = transmitter_idx
        self.recv_obj = receiver_obj
        self.recv_idx = receiver_idx
        self.nodes = nodes
        self.segments = segments

        self.signal = False

    def __repr__(self,/):
        return f'wire {id(self)}'

class wire_attacher:
    def __init__(self, logic_obj: object, node_idx: int, signal: bool, end_x: float, end_y: float,/) -> None:
        self.obj = logic_obj
        self.idx = node_idx
        self.signal = signal

        self.nodes = []

        self.end_x = end_x
        self.end_y = end_y

logic_object = OR_gate | AND_gate | XOR_gate | NOR_gate | NAND_gate | XNOR_gate \
    | buffer | NOT_gate | toggle_switch | light | horizontal_display | vertical_display

LOGIC_OBJECTS = (
    OR_gate,
    AND_gate,
    XOR_gate,
    NOR_gate,
    NAND_gate,
    XNOR_gate,
    buffer,
    NOT_gate,
    toggle_switch,
    light,
    horizontal_display,
    vertical_display,
)

GATE_OBJECTS = {OR_gate, AND_gate, XOR_gate, NOR_gate, NAND_gate, XNOR_gate, buffer, NOT_gate}
NO_INPUT_OBJECTS = {toggle_switch,}
NO_OUTPUT_OBJECTS = {light, horizontal_display, vertical_display}