import pygame
from typing import TypeAlias, Callable, Any

from serialization import serialize_current_state, deserialize_save
from storage import (
    list_saves,
    store_save,
    load_save,
    delete_save,
    rename_save,
)

__all__ = [
    'widget',
    'rect',
    'text_label',
    'button',
    'slider',
    'dropdown',
    'text_input',
    'interface',
    'confirmation_prompt',
    'input_prompt',
    'notification',
    'scrollable_list',
    'side_bar',
    'side_bar_icon',
    'selection_area',
]

Font = pygame.font.Font

class _GUI_scheme:
    font: Font = pygame.font.SysFont('freesansbold', 16)
    font_color = (248,248,248,255)
    text_input_color = (22,22,22,255)
    color = (41,41,41,255)
    border_color = (18,18,18,255)
    border_thickness = 2    
    corner_radius = 5

    slider_label_y_offset = 19

    dropdown_color = (25,25,25,255)
    dropdown_arrow_x_offset = 10
    dropdown_arrow_width = 20
    dropdown_arrow_height = 10

    btn_text_offset = (9, 5)

    prompt_padding = 30
    prompt_text_offset = (15,15)
    prompt_input_y_offset = 45
    prompt_button_y_offset = 20

    notification_icon_offset = 10 + border_thickness
    notification_padding = 15
    notification_color = (25,25,25,255)

    list_x_offset = 10
    list_bg_color = (22,22,22,255)
    list_item_color = (26,26,26,255)
    list_hightlight_color = (50,50,50,255)
    
    side_bar_color = (0,0,0,127) 
    icon_width = 125

class widget:
    def __init__(self, x: int, y: int, width: int | None, height: int | None, visible: bool,/) -> None:
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        self.visible = visible

class rect(widget):
    def __init__(self, 
        x: int, y: int, 
        width: int, height: int, 
        visible: bool,
        color: tuple[int, int, int] | None = None,
        /) -> None:
        super().__init__(x, y, width, height, visible)

        self.color = color if color else _GUI_scheme.border_color

class text_label(widget):
    def __init__(self,
        x: int, y: int, 
        visible: bool, 
        text: str, 
        color: tuple[int, int, int] | None = None,
        /) -> None:
        super().__init__(x, y, None, None, visible)

        self.color = color = color if color else _GUI_scheme.font_color

        self.text = text
        self.surf = _GUI_scheme.font.render(text, True, color)

        self.w, self.h = self.surf.get_size()

class button(widget):
    def __init__(self, 
        x: int, y: int, 
        width: int, height: int, 
        visible: bool, 
        graphic: str | pygame.Surface,
        handle: Callable,
        /) -> None:
        super().__init__(x, y, width, height, visible)

        self.hover = False
        self.inactive = False

        if isinstance(graphic, str):
            text_surf = _GUI_scheme.font.render(graphic, True, _GUI_scheme.font_color)

            ox, oy = _GUI_scheme.btn_text_offset
            self.w = width if width else text_surf.get_width() + ox*2
            self.h = height if height else text_surf.get_height() + oy*2

            surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.rect(surf, _GUI_scheme.border_color, (0, 0, self.w, self.h), border_radius=_GUI_scheme.corner_radius)
            thickness = _GUI_scheme.border_thickness
            pygame.draw.rect(surf, _GUI_scheme.color, (thickness, thickness, self.w - thickness*2, self.h - thickness*2), border_radius=_GUI_scheme.corner_radius - thickness)
            if width:
                ox = (self.w - text_surf.get_width()) // 2
            if height:
                oy = (self.h - text_surf.get_height()) // 2
            surf.blit(text_surf, (ox, oy+2)) # +2 aligns the text towards the center 

            self.surf = surf
        else:
            self.w, self.h = graphic.get_size()
            self.surf = graphic

        self.hover_surf = self.surf.copy()
        self.hover_surf.fill((20,20,20), special_flags=pygame.BLEND_RGB_ADD)
        self.inactive_surf = self.surf.copy()
        self.inactive_surf.fill((127,127,127), special_flags=pygame.BLEND_RGB_MULT)
        self.inactive_surf.fill((20,20,20), special_flags=pygame.BLEND_RGB_ADD)

        self.ties: tuple[Any, ...] | None = None
        # objects or values associated with a button's action

        self.handle = handle

class slider(widget):
    KNOB_SIZE = (22,22)
    LABEL_FONT = pygame.font.SysFont('freesansbold', 13)

    def __init__(self, 
        x: int, y: int, 
        width: int, 
        visible: bool, 
        value: int | float,
        min_value: int | float,
        max_value: int | float,
        step: int | float,
        /) -> None:
        super().__init__(x, y - 3.5, width, 7, visible)

        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

        self.surf = surf = pygame.Surface((width, 7), pygame.SRCALPHA)
        pygame.draw.rect(surf, (142,142,142), (0, 0, width, 7), border_radius=3)
        pygame.draw.rect(surf, (181,181,181), (3, 2, width-6, 3))
        surf.set_at((2,3), (181,181,181))
        surf.set_at((width-3,3), (181,181,181))
        
        self.range = max_value - min_value
        if step:
            self.step_mark_count = int(self.range // step)
            step_size = (width - 7) / self.step_mark_count

            for i in range(1, self.step_mark_count):
                _x = int(i*step_size) + 3
                surf.fill((142,142,142), (_x, 2, 2,3)) 
        else:
            self.step_mark_count = None
        
        self.slider_x = ((value - min_value) / self.range) * (width - 7) + 4 

        self.drag = False

        self.font = self.LABEL_FONT
        self.font_color = _GUI_scheme.font_color

        self.label = None
        self.label_x = 0
        self.label_y = _GUI_scheme.slider_label_y_offset
        self.update_label()

    def update_label(self,/) -> None:
        self.label = self.font.render(f'{self.value}', True, self.font_color)

        w, h = self.label.get_size()
        self.label_x = self.slider_x - w * 0.5

class dropdown(widget):
    _GUI_scheme.font.set_bold(True)
    
    NULL_SELECTION = object()
    NULL_SURFACE = _GUI_scheme.font.render('No selection', True, _GUI_scheme.font_color)
    
    _GUI_scheme.font.set_bold(False)

    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        options: list[str | int | float],
        max_height: int = None,
        /) -> None:
        super().__init__(x, y, width, height, visible)

        self.options = options
        
        self.font = font = _GUI_scheme.font
        self.font_color = font_color = _GUI_scheme.font_color 
        self.color = _GUI_scheme.dropdown_color
        self.border_color = _GUI_scheme.border_color
        self.border_thickness = brdr = _GUI_scheme.border_thickness

        if height is None:
            self.h = height = font.size(' ')[1] + 20
            self.option_y_offset = 11
        else:
            self.option_y_offset = (height - font.size(' ')[1]) / 2 + 1
        self.option_x_offset = 10

        txo = _GUI_scheme.dropdown_arrow_x_offset
        tw = _GUI_scheme.dropdown_arrow_width
        th = _GUI_scheme.dropdown_arrow_height
        self.tx = width - txo - tw
        self.ty = height//2 - th//2 + 1


        self.closed_tri = tc = pygame.Surface((tw, th), pygame.SRCALPHA)
        self.open_tri = to = tc.copy()

        pygame.draw.polygon(tc, self.border_color, ((0,0), (tw-1, 0), (tw//2, th-1)))
        tc.set_at((tw//2-1, th-1), self.border_color) # polygon() misses this pixel
        pygame.draw.polygon(to, self.border_color, ((-1,th-1), (tw-1, th-1), (tw//2, -1)))
        
        closed_surf = pygame.Surface((width, height))
        closed_surf.fill(self.border_color)
        closed_surf.fill(self.color, (brdr, brdr, width - brdr*2, height - brdr*2))

        self.option_h = option_height = height - brdr

        size = len(options) 
        self.open_h = h = height + option_height * size
        self.max_scroll = 0
        self.scroll = 0

        self.max_height = max_height if max_height else 1e300

        if max_height and h > max_height:
            self.open_h = max_height
            h = ((max_height - brdr) // option_height + 2) * option_height + brdr

            self.max_scroll = self.option_h * (size + 1) - max_height 
            self.scrollable = True
        else:
            self.scrollable = False

        open_surf = pygame.Surface((width, h))
        open_surf.fill(self.border_color)
        open_surf.fill(self.color, (brdr, brdr, width - brdr*2, h - brdr*2))

        for i in range(option_height, h, option_height):
            open_surf.fill(self.border_color, (0, i, width, brdr))

        self.closed_surf = closed_surf
        self.open_surf = open_surf

        self.max_option_len = max_option_len = width - self.option_x_offset*2 - tw - txo
        ellipsis_len, _ = font.size('...')

        option_surfs = []
        for option in options:
            s = f'{option}'

            if len(s) > 255: s = s[:255]

            w, _ = font.size(s)
            
            if w > max_option_len:
                while w > max_option_len:
                    s = s[:-1]
                    w, _ = font.size(s)
                    w += ellipsis_len
                
                s += '...'

            option_surfs.append(font.render(s, True, font_color))

        self.option_surfs = option_surfs

        self.open = False
        self.selected = self.NULL_SELECTION

class text_input(widget):
    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        /) -> None:
        super().__init__(x, y, width, height, visible)

        self.font = font = _GUI_scheme.font
        self.font_color = _GUI_scheme.font_color

        if height is None:
            self.h = height = font.size(' ')[1] + 20
            self.y_offset = 11
        else:
            self.y_offset = (height - font.size(' ')[1]) / 2 + 1
        self.x_offset = 5

        self.surf = surf = pygame.Surface((width, height))
        surf.fill(_GUI_scheme.border_color)
        brdr = _GUI_scheme.border_thickness
        surf.fill(_GUI_scheme.text_input_color, (brdr, brdr, width - brdr*2, height - brdr*2))

        self.input = ''
        self.input_surf = font.render(self.input, True, self.font_color)
        self.caret_idx = 0

        self.focused = False

class interface(widget):
    X_LEFT_ALIGN = object()
    X_CENTER_ALIGN = object()
    X_RIGHT_ALIGN = object()

    Y_TOP_ALIGN = object()
    Y_CENTER_ALIGN = object()
    Y_BOTTOM_ALIGN = object()

    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        widgets: list[widget],
        alignments: list[tuple[object, object]],
        color: tuple[int, int, int] | None = None,
        /) -> None: 
        super().__init__(x, y, width, height, visible)

        self.widgets = widgets
        self.alignments = alignments

        x_end = x + width
        y_end = y + height

        self.x_offsets = x_offsets = []
        self.y_offsets = y_offsets = []

        R = self.X_RIGHT_ALIGN
        XC = self.X_CENTER_ALIGN
        L = self.X_LEFT_ALIGN
        T = self.Y_TOP_ALIGN
        YC = self.Y_CENTER_ALIGN
        B = self.Y_BOTTOM_ALIGN

        for w, (ax, ay) in zip(widgets, alignments):
            if ax is L:
                x_offsets.append(w.x - x)
            elif ax is XC:
                x_offsets.append((w.x + w.w/2 - x) / width)
            elif ax is R:
                x_offsets.append(w.x - x_end)

            if ay is T:
                y_offsets.append(w.y - y)
            elif ay is YC:
                y_offsets.append((w.y + w.h/2 - y) / height)
            elif ay is B:
                y_offsets.append(w.y - y_end)

        self.color = color if color else _GUI_scheme.color

class confirmation_prompt(widget):
    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        prompt_text: str,
        cancel_btn: button,
        ok_btn: button,
        /) -> None: 
        super().__init__(x, y, width, height, visible)

        self.prompt_text = prompt_text
        text_surf = _GUI_scheme.font.render(prompt_text, True, _GUI_scheme.font_color)

        if not width: self.w = text_surf.get_width() + _GUI_scheme.prompt_padding * 2

        surf = pygame.Surface((self.w, height), pygame.SRCALPHA)
        pygame.draw.rect(surf, _GUI_scheme.border_color, (0, 0, self.w, height), border_radius=_GUI_scheme.corner_radius)
        thickness = _GUI_scheme.border_thickness
        pygame.draw.rect(surf, _GUI_scheme.color, (thickness, thickness, self.w - thickness*2, height - thickness*2), border_radius=_GUI_scheme.corner_radius - thickness)
        surf.blit(text_surf, _GUI_scheme.prompt_text_offset)
        self.surf = surf

        self.cancel_btn = cancel_btn
        self.ok_btn = ok_btn

        cancel_btn.x = x + (width*.5 - cancel_btn.w)//2
        ok_btn.x = x + (width*1.5 - ok_btn.w)//2

        _y = y + height
        ok_btn.y = _y - _GUI_scheme.prompt_button_y_offset - ok_btn.h
        cancel_btn.y = _y - _GUI_scheme.prompt_button_y_offset - cancel_btn.h

class input_prompt(widget):
    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        prompt_text: str,
        text_input: text_input,
        cancel_btn: button,
        ok_btn: button,
        /) -> None: 
        super().__init__(x, y, width, height, visible)
        
        self.prompt_text = prompt_text
        text_surf = _GUI_scheme.font.render(prompt_text, True, _GUI_scheme.font_color)

        if not width: self.w = text_surf.get_width() + _GUI_scheme.prompt_padding * 2

        surf = pygame.Surface((self.w, height), pygame.SRCALPHA)
        pygame.draw.rect(surf, _GUI_scheme.border_color, (0, 0, self.w, height), border_radius=_GUI_scheme.corner_radius)
        brdr = _GUI_scheme.border_thickness
        pygame.draw.rect(surf, _GUI_scheme.color, (brdr, brdr, self.w - brdr*2, height - brdr*2), border_radius=_GUI_scheme.corner_radius - brdr)
        surf.blit(text_surf, _GUI_scheme.prompt_text_offset)
        self.surf = surf

        self.text_input = text_input
        text_input.x = (width - text_input.w) // 2 + x
        text_input.y = y + _GUI_scheme.prompt_input_y_offset

        self.cancel_btn = cancel_btn
        self.ok_btn = ok_btn

        cancel_btn.x = x + (width*.5 - cancel_btn.w)//2
        ok_btn.x = x + (width*1.5 - ok_btn.w)//2

        _y = y + height
        ok_btn.y = _y - _GUI_scheme.prompt_button_y_offset - ok_btn.h
        cancel_btn.y = _y - _GUI_scheme.prompt_button_y_offset - cancel_btn.h

class notification(widget):
    DEFAULT_DURATION = 3

    SLIDE_INTO_PLACE = object()
    PAUSE = object()
    SLIDE_BACK = object()

    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        slide_dx: int, slide_dy: int,
        icon: pygame.Surface,
        text: str,
        duration: int | float = DEFAULT_DURATION,
        color: tuple[int, int, int] | None = None,
        /) -> None: 
        super().__init__(x, y, width, height, visible)

        self.font = _GUI_scheme.font
        self.font_color = _GUI_scheme.font_color

        self.color = color = color if color else self.font_color

        self.slide_dx = slide_dx
        self.slide_dy = slide_dy

        self.start_x = x
        self.start_y = y

        icon_w, icon_h = icon.get_size()
        icon_offset = _GUI_scheme.notification_icon_offset

        self.icon = icon
        self.text = text
        text_surf = _GUI_scheme.font.render(text, True, color)
        text_h = text_surf.get_height()

        self.text_y_offset = (height - text_h)//2 + 2
        tx = icon_offset + icon_w + 10

        self.text_x_end = tx + text_surf.get_width()

        if not width: self.w = text_surf.get_width() + _GUI_scheme.notification_padding + tx 

        surf = pygame.Surface((self.w, height), pygame.SRCALPHA)
        pygame.draw.rect(surf, _GUI_scheme.border_color, (0, 0, self.w, height), border_radius=_GUI_scheme.corner_radius)
        brdr = _GUI_scheme.border_thickness
        pygame.draw.rect(surf, _GUI_scheme.notification_color, (brdr, brdr, self.w - brdr*2, height - brdr*2), border_radius=_GUI_scheme.corner_radius - brdr)
        surf.blit(icon, (icon_offset, (self.text_y_offset - 2 - (icon_h - text_h)//2)))
        surf.blit(text_surf, (tx, self.text_y_offset))
        self.surf = surf

        self.text_surf = None

        self.pause_start = 0
        self.duration = duration

        # only valid when self.visible
        self.state = self.SLIDE_INTO_PLACE

    def ani_start(self, text: str, __SLIDE_INTO_PLACE = SLIDE_INTO_PLACE) -> None:
        self.x = self.start_x
        self.y = self.start_y

        if len(text) > 200: text = text[:200]

        font = self.font
        max_len = self.w - self.text_x_end - 10
        w, _ = font.size(text)
        
        if w > max_len:
            ellipsis_len, _ = font.size('...')
            while w > max_len:
                text = text[:-1]
                w, _ = font.size(text)
                w += ellipsis_len
            
            text += '...'

        self.text_surf = self.font.render(text, True, self.font_color)

        self.visible = True
        self.state =  __SLIDE_INTO_PLACE

class scrollable_list(widget):
    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        items: list[str],
        background_color: tuple[int, int, int, int] = None,
        /) -> None: 
        super().__init__(x, y, width, height, visible)

        self.items = items

        self.font = font = _GUI_scheme.font
        self.font_color = font_color = _GUI_scheme.font_color

        self.bg_color = background_color if background_color else _GUI_scheme.list_bg_color
        self.item_color = _GUI_scheme.list_item_color
        self.hightlight_color = _GUI_scheme.list_hightlight_color

        self.item_height = font.size(' ')[1] + 20
        
        self.text_x_offset = _GUI_scheme.list_x_offset
        self.text_y_offset = 11

        max_item_len = width - self.text_x_offset * 2
        ellipsis_len, _ = font.size('...')

        item_surfs = []
        for item in items:
            s = f'{item}'

            w, _ = font.size(s)
            
            if w > max_item_len:
                if len(s) > 500: s = s[:500]

                while w > max_item_len:
                    s = s[:-1]
                    w, _ = font.size(s)
                    w += ellipsis_len
                
                s += '...'
                
            item_surfs.append(font.render(item, True, font_color))
        
        self.item_surfs = item_surfs

        self.hover = None
        self.selected = None

        self.scroll = 0
        
        if (list_height:=len(items) * self.item_height) > height:
            self.scrollable = True
            self.max_scroll = list_height - height
        else:
            self.scrollable = False
            self.max_scroll = 0

class side_bar(widget):
    SRCAPLHA_FLAG = pygame.SRCALPHA

    def __init__(self, 
        x: int, y: int, 
        width: int, height: int,
        visible: bool,
        icons: list[side_bar_icon], icon_spacing: tuple[int, int],/) -> None:
        super().__init__(x, y, width, height, visible)

        self.color = _GUI_scheme.side_bar_color

        self.surf = pygame.Surface((width,height), self.SRCAPLHA_FLAG)
        self.surf.fill(self.color)
        self.spacing_x, self.spacing_y = icon_spacing
        self.icons = icons

        self.hover_icon = None

        self.rects = []
        _w = _GUI_scheme.icon_width + self.spacing_x
        self.icons_per_row = (width - 20 + self.spacing_x) // _w

        _y = 0; max_h = 0; abs_max_h = 0
        for i, icon in enumerate(icons):
            max_h = max(max_h, icon.h)
            self.rects.append(((i % self.icons_per_row) * _w, _y, icon.w, icon.h))
            if i % self.icons_per_row == self.icons_per_row - 1: 
                _y += max_h + self.spacing_y
                abs_max_h = max(abs_max_h, max_h)
                max_h = 0
        _y += max_h

        self.hlght_surf = pygame.Surface((_w, abs_max_h), self.SRCAPLHA_FLAG)

        self.scroll = 0
        self.max_scroll = _y - height

class side_bar_icon:
    def __init__(self, surf: pygame.Surface, obj_class: type,/) -> None:
        self.surf = pygame.transform.smoothscale_by(surf, _GUI_scheme.icon_width / surf.get_width())
        self.cls = obj_class
        self.w, self.h = self.surf.get_size()
        self.input_count = obj_class.INPUT_DEFAULT

class object_placer:
    def __init__(self) -> None:
        self.cls = None
        self.x = None 
        self.y = None
        self.input_count = None
        self.half_w = None
        self.half_h = None
        self.orient = None

        self.active = False

    def reset(self, mx: float, my: float, obj_class: type, input_count: int, half_size: tuple[float | int, float | int],/) -> None:
        self.cls = obj_class
        self.x = mx 
        self.y = my 
        self.input_count = input_count
        self.half_w, self.half_h = half_size
        self.orient = 0

        self.active = True

class selection_area:
    def __init__(self, x1, y1, x2, y2,/):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2