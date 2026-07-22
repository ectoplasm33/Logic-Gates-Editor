from os import scandir
from constants import DATA_DIR, CONFIG_FILE
from gui import (
    button,
    interface,
    confirmation_prompt,
    input_prompt,
    scrollable_list,
)

__all__ = [
    'scan_data_dir',
    'reset_save_list',
    'handle_window_resize',
    'open_side_bar',
    'close_side_bar',
    'open_settings',
    'open_saves_interface',
    'close_interface',
    'confirm_save_action',
    'cancel_save_action',
    'prompt_action_input',
    'cancel_action_input',
    'new_save',
    'load_save',
    'overwrite_save',
    'rename_save',
    'delete_save',
    'new_save_file',
]

def scan_data_dir() -> list[str]:
    config = CONFIG_FILE
    files = []

    for item in scandir(DATA_DIR):
        if item.is_file() and item.name != config:
            files.append(item.name)

    return files

def reset_save_list(save_list, items,/) -> None:
    save_list.items = items
    save_list.item_surfs = surfs = []

    font = save_list.font
    font_color = save_list.font_color

    for item in items:
        surfs.append(font.render(item, True, font_color))

    if (list_height:=len(items) * save_list.item_height) > save_list.h:
        save_list.scrollable = True
        save_list.scroll = 0
        save_list.max_scroll = list_height - save_list.h
    else:
        save_list.scrollable = False
        save_list.scroll = \
        save_list.max_scroll = 0

def handle_window_resize(
    old_wx: int, old_wy: int,
    win_x: int, win_y: int,
    settings_button: button,
    saves_button: button, 
    settings_interface: interface,
    saves_interface: interface,
    save_list: scrollable_list,
    delete_prompt: confirmation_prompt,
    rename_prompt: input_prompt,
    load_prompt: confirmation_prompt,
    save_prompt: confirmation_prompt,
    new_save_prompt: input_prompt, 
    new_file_prompt: input_prompt,  
    /) -> None:
    dx = win_x - old_wx; dy = win_y - old_wy

    settings_button.x += dx
    saves_button.x += dx

    R = settings_interface.X_RIGHT_ALIGN
    XC = settings_interface.X_CENTER_ALIGN
    YC = settings_interface.Y_CENTER_ALIGN
    B = settings_interface.Y_BOTTOM_ALIGN
    
    for intr in (settings_interface, saves_interface):
        x = intr.x; y = intr.y
        intr.h = height = intr.h + dy
        intr.w = width = intr.w + dx

        x_end = x + width; y_end = y + height

        for w, (ax, ay), ox, oy in zip(
            intr.widgets, 
            intr.alignments, 
            intr.x_offsets, 
            intr.y_offsets
            ):
            if ax is XC:
                w.x = int(x + width * ox - w.w*0.5)       
            elif ax is R:
                w.x = x_end + ox

            if ay is YC:
                w.y = int(y + height * oy - w.h*0.5)
            elif ay is B:
                w.y = y_end + oy

    save_list.w += dx
    save_list.h = height = save_list.h + dy

    list_h = len(save_list.items) * save_list.item_height

    if list_h > height:
        save_list.scrollable = True
        save_list.max_scroll = list_h - height

        if save_list.scroll > save_list.max_scroll:
            save_list.scroll = save_list.max_scroll
    else:
        save_list.scrollable = False
        save_list.scroll = \
        save_list.max_scroll = 0

    font = save_list.font
    font_color = save_list.font_color

    max_item_len = save_list.w - save_list.text_x_offset * 2
    ellipsis_len, _ = font.size('...')

    item_surfs = save_list.item_surfs
    for i, item in enumerate(save_list.items):
        s = f'{item}'

        w, _ = font.size(s)
        
        if w > max_item_len:
            if len(s) > 500: s = s[:500]

            while w > max_item_len:
                s = s[:-1]
                w, _ = font.size(s)
                w += ellipsis_len
            
            s += '...'

        item_surfs[i] = font.render(s, True, font_color)

    for prompt in (delete_prompt, load_prompt, save_prompt):
        cancel_btn = prompt.cancel_btn; ok_btn = prompt.ok_btn
        
        dy = ok_btn.y - prompt.y
        w = prompt.w

        prompt.x = x = (win_x - w) // 2
        prompt.y = y = (win_y - prompt.h) // 2

        cancel_btn.x = x + (w*.5 - cancel_btn.w)//2
        ok_btn.x = x + (w*1.5 - ok_btn.w)//2

        cancel_btn.y = ok_btn.y = y + dy

    for prompt in (rename_prompt, new_save_prompt, new_file_prompt):
        cancel_btn = prompt.cancel_btn; ok_btn = prompt.ok_btn
        input = prompt.text_input

        btn_dy = ok_btn.y - prompt.y; input_dy = input.y - prompt.y
        w = prompt.w

        prompt.x = x = (win_x - w) // 2
        prompt.y = y = (win_y - prompt.h) // 2

        cancel_btn.x = x + (w*.5 - cancel_btn.w)//2
        ok_btn.x = x + (w*1.5 - ok_btn.w)//2

        cancel_btn.y = ok_btn.y = y + btn_dy

        input.x = (w - input.w) // 2 + x
        input.y = y + input_dy

def open_side_bar(btn: button,/) -> None:
    side_bar, close_btn = btn.ties

    side_bar.visible = close_btn.visible = True
    btn.visible = False

def close_side_bar(btn: button,/) -> None:
    side_bar, open_btn = btn.ties

    open_btn.visible = True
    side_bar.visible = btn.visible = False

def open_settings(btn: button,/) -> None:
    settings_interface, saves_btn, gui_manager, render_manager = btn.ties

    gui_manager.open_interface = settings_interface
    settings_interface.visible = True
    btn.visible = saves_btn.visible = False

    render_manager.render_objects = False

    for widget in settings_interface.widgets:
        widget.visible = True

def open_saves_interface(btn: button,/) -> None:
    saves_interface, settings_btn, save_action_btns, gui_manager, render_manager = btn.ties

    gui_manager.open_interface = saves_interface
    saves_interface.visible = True
    btn.visible = settings_btn.visible = False

    render_manager.render_objects = False

    for widget in saves_interface.widgets:
        widget.visible = True

    for b in save_action_btns:
        b.inactive = True

def close_interface(btn: button,/) -> None:
    settings_interface, saves_interface, save_list, \
    confirm_prompts, input_prompts, \
    settings_btn, saves_btn, \
    gui_manager, render_manager = btn.ties
    
    if settings_interface.visible:
        settings_interface.visible = False
        for widget in settings_interface.widgets:
            widget.visible = False
    else:
        for widget in saves_interface.widgets:
            widget.visible = False

        saves_interface.visible = False

        save_list.selected = None

        for prompt in confirm_prompts:
            prompt.visible = \
            prompt.cancel_btn.visible = \
            prompt.ok_btn.visible = False

        for prompt in input_prompts:
            input = prompt.text_input

            prompt.visible = \
            prompt.cancel_btn.visible = \
            prompt.ok_btn.visible = \
            input.visible = input.focused = False

            input.input = ''
            input.input_surf = input.font.render('', False, 0)
            input.caret_idx = 0

    settings_btn.visible = saves_btn.visible = True
    btn.visible = False

    gui_manager.active_prompt = gui_manager.focused_input = \
    gui_manager.open_interface = None
    render_manager.render_objects = True

# prompt handles
def confirm_save_action(btn: button,/) -> None:
    prompt, gui_manager = btn.ties

    if gui_manager.active_prompt: return

    gui_manager.active_prompt = prompt
    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = True

def cancel_save_action(btn: button,/) -> None:
    prompt, gui_manager = btn.ties

    gui_manager.active_prompt = None
    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = False

def prompt_action_input(btn: button,/) -> None:
    prompt, gui_manager = btn.ties

    if gui_manager.active_prompt: return

    gui_manager.active_prompt = prompt
    input = prompt.text_input
    gui_manager.focused_input = input
    input.focused = True

    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = \
    prompt.text_input.visible = True

def cancel_action_input(btn: button,/) -> None:
    prompt, gui_manager = btn.ties

    input = prompt.text_input

    input.input = ''
    input.input_surf = input.font.render('', False, 0)
    input.caret_idx = 0

    gui_manager.active_prompt = gui_manager.focused_input = None

    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = \
    input.visible = input.focused = False

# save list handles
def new_save(btn: button,/) -> None:
    prompt, save_list, drop, gui_manager, save_manager, prop_manager, \
    transfer_game_state, serialize, storage_save, \
    NOT_INITIALIZED, UNSUPPORTED_VER, INVALID_IDENTIFIER, surface, \
    success_notif, fail_notif = btn.ties

    input = prompt.text_input
    save_name = input.input

    if save_name in save_list.items: 
        fail_notif.ani_start(f'\'{save_name}\'')
        return

    cam, objects, sets = transfer_game_state()
    serialized = serialize(cam, objects, prop_manager, sets)
    result = storage_save(save_manager.opened_file_path, save_name, serialized)

    if result is NOT_INITIALIZED or result is UNSUPPORTED_VER or result is INVALID_IDENTIFIER:
        fail_notif.ani_start(f'\'{save_name}\'')
        return 

    save_list.items.append(save_name)
    save_list.item_surfs.append(save_list.font.render(save_name, True, save_list.font_color))

    if save_list.scrollable:
        save_list.max_scroll += save_list.item_height

    drop.options.append(save_name)
    
    s = save_name
    w, _ = drop.font.size(s)
    if w > drop.max_option_len:

        font = drop.font
        ellipsis_len, _ = font.size('...')
        max_len = drop.max_option_len

        if len(s) > 255: s = s[:255]

        while w > max_len:
            s = s[:-1]
            w, _ = font.size(s)
            w += ellipsis_len
        
        s += '...'

    drop.option_surfs.append(drop.font.render(s, True, drop.font_color))

    if not drop.scrollable:
            option_count = len(drop.options)

            max_height = drop.max_height
            option_h = drop.option_h
            w = drop.w
            brdr = drop.border_thickness

            brdr_color = drop.border_color

            if drop.h + option_count * option_h > max_height:
                drop.open_h = h = ((max_height - brdr) // option_h + 2) * option_h + brdr

                drop.max_scroll = option_h * (option_count + 1) - max_height
                drop.scrollable = True
            else:
                h = drop.open_h = drop.open_h + option_h

                drop.scrollable = False
                drop.scroll = 0

            drop.open_surf = surf = surface((w, h))

            surf.fill(brdr_color)
            surf.fill(drop.color, (brdr, brdr, w - brdr*2, h - brdr*2))

            for i in range(option_h, h, option_h):
                surf.fill(brdr_color, (0, i, w, brdr))

    input.input = ''
    input.input_surf = input.font.render('', False, 0)
    input.caret_idx = 0

    gui_manager.active_prompt = gui_manager.focused_input = None

    success_notif.ani_start(f'\'{save_name}\'')

    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = \
    input.visible = input.focused = False

def load_save(btn: button,/) -> None:
    prompt, save_list, exit_btn, gui_manager, save_manager, \
    storage_load, deserialize, update_game_state, \
    NOT_INITIALIZED, STORAGE_UNSUPPORTED_VER, INVALID_IDENTIFIER, \
    INVALID_DATA, SERIAL_UNSUPPORTED_VER, \
    success_notif, fail_notif = btn.ties

    save_name = save_list.items[save_list.selected]

    save_data = storage_load(save_manager.opened_file_path, save_name)

    if save_data is NOT_INITIALIZED or save_data is STORAGE_UNSUPPORTED_VER or save_data is INVALID_IDENTIFIER:
        fail_notif.ani_start(f'\'{save_name}\'')
        return
    
    state = deserialize(save_data)

    if state is INVALID_DATA or state is SERIAL_UNSUPPORTED_VER:
        fail_notif.ani_start(f'\'{save_name}\'')
        return

    update_game_state(state)

    gui_manager.active_prompt = None
    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = False

    success_notif.ani_start(f'\'{save_name}\'')

    exit_btn.handle(exit_btn)

def overwrite_save(btn: button,/) -> None:
    prompt, save_list, gui_manager, save_manager, prop_manager, \
    transfer_game_state, serialize, storage_save, \
    NOT_INITIALIZED, UNSUPPORTED_VER, INVALID_IDENTIFIER, \
    success_notif, fail_notif = btn.ties

    save_name = save_list.items[save_list.selected]

    cam, objects, sets = transfer_game_state()
    serialized = serialize(cam, objects, prop_manager, sets)
    result = storage_save(save_manager.opened_file_path, save_name, serialized)

    if result is NOT_INITIALIZED or result is UNSUPPORTED_VER or result is INVALID_IDENTIFIER:
        fail_notif.ani_start(f'\'{save_name}\'')
        return

    success_notif.ani_start(f'\'{save_name}\'')

    gui_manager.active_prompt = None
    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = False

def rename_save(btn: button,/) -> None:
    prompt, save_list, gui_manager, save_manager, storage_rename, \
    NOT_INITIALIZED, UNSUPPORTED_VER, INVALID_IDENTIFIER, \
    success_notif, fail_notif = btn.ties

    items = save_list.items
    selected = save_list.selected

    stale_name = items[selected]
    input = prompt.text_input
    new_name = input.input

    result = storage_rename(save_manager.opened_file_path, stale_name, new_name)

    if result is NOT_INITIALIZED or result is UNSUPPORTED_VER or result is INVALID_IDENTIFIER:
        fail_notif.ani_start(f'\'{stale_name}\'')
        return

    items[selected] = new_name
    save_list.item_surfs[selected] = save_list.font.render(new_name, True, save_list.font_color)

    input.input = ''
    input.input_surf = input.font.render('', False, 0)
    input.caret_idx = 0

    gui_manager.active_prompt = gui_manager.focused_input = None

    success_notif.ani_start(f'\'{new_name}\'')

    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = \
    input.visible = input.focused = False

def delete_save(btn: button,/) -> None:
    prompt, save_list, gui_manager, save_manager, buttons, \
    storage_delete, \
    NOT_INITIALIZED, UNSUPPORTED_VER, INVALID_IDENTIFIER, \
    success_notif, fail_notif = btn.ties

    selected = save_list.selected
    save_name = save_list.items[selected]

    result = storage_delete(save_manager.opened_file_path, save_name)

    if result is NOT_INITIALIZED or result is UNSUPPORTED_VER or result is INVALID_IDENTIFIER:
        fail_notif.ani_start(f'\'{save_name}\'')
        return
    
    del save_list.items[selected] 
    del save_list.item_surfs[selected]

    save_list.selected = None

    if len(save_list.items) * save_list.item_height <= save_list.h: 
        save_list.scrollable = False
        save_list.scroll = 0
    else:
        save_list.max_scroll -= save_list.item_height
    
        if save_list.scroll > save_list.max_scroll:
            save_list.scroll = save_list.max_scroll

    for b in buttons:
        b.inactive = True

    success_notif.ani_start(f'\'{save_name}\'')

    gui_manager.active_prompt = None
    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = False

# ------
def new_save_file(btn: button,/) -> None:
    prompt, save_list, default_drop, open_drop, \
    gui_manager, saves_manager, \
    NOT_INITIALIZED, UNSUPPORTED_VER, \
    surface, storage_init, storage_list, reset_list, \
    success_notif, fail_notif = btn.ties

    input = prompt.text_input

    file_name = input.input

    if '.' not in file_name:
        file_name += '.sav'

    if file_name in open_drop.options: 
        fail_notif.ani_start(f'\'{file_name}\'')
        return

    saves_manager.update_opened_path(file_name)

    result = storage_init(path := saves_manager.opened_file_path)

    if result is NOT_INITIALIZED or result is UNSUPPORTED_VER:
        fail_notif.ani_start(f'\'{file_name}\'')
        return

    saves_manager.opened_file_path = path

    open_drop.selected = len(open_drop.options)

    for drop in (open_drop, default_drop):
        drop.options.append(file_name)

        s = file_name
        w, _ = drop.font.size(s)
        if w > drop.max_option_len:
            font = drop.font
            ellipsis_len, _ = font.size('...')
            max_len = drop.max_option_len

            if len(s) > 255: s = s[:255]

            while w > max_len:
                s = s[:-1]
                w, _ = font.size(s)
                w += ellipsis_len
            
            s += '...'

        drop.option_surfs.append(drop.font.render(s, True, drop.font_color))

        if not drop.scrollable:
            option_count = len(drop.options)

            max_height = drop.max_height
            option_h = drop.option_h
            w = drop.w
            brdr = drop.border_thickness

            brdr_color = drop.border_color

            if drop.h + option_count * option_h > max_height:
                drop.open_h = h = ((max_height - brdr) // option_h + 2) * option_h + brdr

                drop.max_scroll = option_h * (option_count + 1) - max_height
                drop.scrollable = True
            else:
                h = drop.open_h = drop.open_h + option_h

                drop.scrollable = False
                drop.scroll = 0

            drop.open_surf = surf = surface((w, h))

            surf.fill(brdr_color)
            surf.fill(drop.color, (brdr, brdr, w - brdr*2, h - brdr*2))

            for i in range(option_h, h, option_h):
                surf.fill(brdr_color, (0, i, w, brdr))

    reset_list(save_list, storage_list(path))

    input.input = ''
    input.input_surf = input.font.render('', False, 0)
    input.caret_idx = 0

    gui_manager.active_prompt = gui_manager.focused_input = None

    success_notif.ani_start(f'\'{file_name}\'')

    prompt.visible = \
    prompt.cancel_btn.visible = \
    prompt.ok_btn.visible = \
    input.visible = input.focused = False
