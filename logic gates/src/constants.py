'''
constant values
- files
- directories
- object data
'''
from logic_objects import (
    LOGIC_OBJECTS,
)
from os.path import dirname, join

LOC                 = dirname(dirname(__file__))

TEXTURES_DIRECTORY  = join(LOC, 'textures')
DATA_DIR            = join(LOC, 'data')
OBJ_DIR             = join(TEXTURES_DIRECTORY, 'objects')
PNG_DIR             = join(TEXTURES_DIRECTORY, 'png')

OR_GATE_DIR         = join(OBJ_DIR, 'OR_gate')
AND_GATE_DIR        = join(OBJ_DIR, 'AND_gate')
XOR_GATE_DIR        = join(OBJ_DIR, 'XOR_gate')
NOR_GATE_DIR        = join(OBJ_DIR, 'NOR_gate')
NAND_GATE_DIR       = join(OBJ_DIR, 'NAND_gate')
XNOR_GATE_DIR       = join(OBJ_DIR, 'XNOR_gate')

TOGGLE_SWITCH_DIR   = join(OBJ_DIR, 'toggle_switch')
LIGHT_DIR           = join(OBJ_DIR, 'light')

HDISPLAY_DIR        = join(OBJ_DIR, 'horizontal_display')
VDISPLAY_DIR        = join(OBJ_DIR, 'vertical_display')

CONFIG_FILE         = '.config'

OR_GATE_FILES = (
    None,
    None,
    'OR_gate_2.svg',
    'OR_gate_3.svg',
    'OR_gate_4.svg',
    'OR_gate_5.svg',
    'OR_gate_6.svg',
    'OR_gate_7.svg',
    'OR_gate_8.svg',
)
AND_GATE_FILES = (
    None,
    None,
    'AND_gate_2.svg',
    'AND_gate_3.svg',
    'AND_gate_4.svg',
    'AND_gate_5.svg',
    'AND_gate_6.svg',
    'AND_gate_7.svg',
    'AND_gate_8.svg',
)
XOR_GATE_FILES = (
    None,
    None,
    'XOR_gate_2.svg',
    'XOR_gate_3.svg',
    'XOR_gate_4.svg',
    'XOR_gate_5.svg',
    'XOR_gate_6.svg',
    'XOR_gate_7.svg',
    'XOR_gate_8.svg',
)
NOR_GATE_FILES = (
    None,
    None,
    'NOR_gate_2.svg',
    'NOR_gate_3.svg',
    'NOR_gate_4.svg',
    'NOR_gate_5.svg',
    'NOR_gate_6.svg',
    'NOR_gate_7.svg',
    'NOR_gate_8.svg',
)
NAND_GATE_FILES = (
    None,
    None,
    'NAND_gate_2.svg',
    'NAND_gate_3.svg',
    'NAND_gate_4.svg',
    'NAND_gate_5.svg',
    'NAND_gate_6.svg',
    'NAND_gate_7.svg',
    'NAND_gate_8.svg',
)
XNOR_GATE_FILES = (
    None,
    None,
    'XNOR_gate_2.svg',
    'XNOR_gate_3.svg',
    'XNOR_gate_4.svg',
    'XNOR_gate_5.svg',
    'XNOR_gate_6.svg',
    'XNOR_gate_7.svg',
    'XNOR_gate_8.svg',
)

HORIZONTAL_DISPLAY_FILES = (
    'hdisplay_0x0.svg',
    'hdisplay_0x1.svg',
    'hdisplay_0x2.svg',
    'hdisplay_0x3.svg',
    'hdisplay_0x4.svg',
    'hdisplay_0x5.svg',
    'hdisplay_0x6.svg',
    'hdisplay_0x7.svg',
    'hdisplay_0x8.svg',
    'hdisplay_0x9.svg',
    'hdisplay_0xA.svg',
    'hdisplay_0xB.svg',
    'hdisplay_0xC.svg',
    'hdisplay_0xD.svg',
    'hdisplay_0xE.svg',
    'hdisplay_0xF.svg',
)

VERTICAL_DISPLAY_FILES = (
    'vdisplay_0x0.svg',
    'vdisplay_0x1.svg',
    'vdisplay_0x2.svg',
    'vdisplay_0x3.svg',
    'vdisplay_0x4.svg',
    'vdisplay_0x5.svg',
    'vdisplay_0x6.svg',
    'vdisplay_0x7.svg',
    'vdisplay_0x8.svg',
    'vdisplay_0x9.svg',
    'vdisplay_0xA.svg',
    'vdisplay_0xB.svg',
    'vdisplay_0xC.svg',
    'vdisplay_0xD.svg',
    'vdisplay_0xE.svg',
    'vdisplay_0xF.svg',
)

BUFFER_FILE                 = 'buffer.svg'
NOT_GATE_FILE               = 'not_gate.svg'

TOGGLE_OFF_FILE             = 'toggle_off.svg'
TOGGLE_ON_FILE              = 'toggle_on.svg'
TOG_OFF_HLGHT_FILE          = 'toggle_off_hlght.svg'
TOG_ON_HLGHT_FILE           = 'toggle_on_hlght.svg'

LIGHT_OFF_FILE              = 'light_off.svg'
LIGHT_ON_FILE               = 'light_on.svg'
LT_OFF_HLGHT_FILE           = 'light_off_hlght.svg'
LT_ON_HLGHT_FILE            = 'light_on_hlght.svg'

NODE_FILE                   = 'node.svg'

ARROW_CLOSE_FILE            = 'arrow_close.png'
ARROW_OPEN_FILE             = 'arrow_open.png'
SAVE_BUTTON_FILE            = 'save_button.png'
SETTINGS_BUTTON_FILE        = 'settings.png'

SUCCESS_FILE                = 'success.png'
FAIL_FILE                   = 'fail.png'
SLIDER_KNOB_FILE            = 'slider_knob.png'

def _HALF(tup: tuple) -> tuple:
    l = []

    for size in tup:
        if not size:
            l.append(None)
            continue
        
        w, h = size
        l.append((w / 2, h / 2))

    return tuple(l)

OBJECT_SIZES = {}
OBJECT_HALF_SIZES = {}
OBJECT_BOUNDS = {}  
OBJECT_HITBOXES = {}
OBJECT_NODE_POSITIONS = {}

for cls in LOGIC_OBJECTS:
    size = cls.SIZES

    OBJECT_SIZES[cls]           = size
    OBJECT_HALF_SIZES[cls]      = _HALF(size)
    OBJECT_BOUNDS[cls]          = cls.BOUNDING_RECTS
    OBJECT_HITBOXES[cls]        = cls.HITBOXES
    OBJECT_NODE_POSITIONS[cls]  = cls.NODE_POSITIONS