'''
Write and read saves in a binary file.
Ability to manage an arbitrary amount of files.

file format:

version (u32) | number of saves (u32) | save data bounds offset (u32) | name data zero start and end bounds (u32) | name data | save data zero start and end bounds (u32) | save data
'''
from os.path import exists
from struct import Struct
from typing import TypeAlias

file_path: TypeAlias = str

_VERSION = 1

_cached_files = {}
_cached_versions = {}
_cached_names = {}

_LITTLE_ENDIAN_U32 = Struct('<I')
_SINGLE_PACK = _LITTLE_ENDIAN_U32.pack
_SINGLE_UNPACK = _LITTLE_ENDIAN_U32.unpack

_DUAL_LITTLE_ENDIAN_U32 = Struct('<II')
_DUAL_UNPACK = _DUAL_LITTLE_ENDIAN_U32.unpack

_UINT_SHIFT = 2
_UINT_SIZE = 4
_HEADER_SIZE = _UINT_SIZE * 3

_BUFFER_SHIFT = 18
_BUFFER_SIZE = 1 << _BUFFER_SHIFT
_buffer = memoryview(bytearray(_BUFFER_SIZE))

FILE_NOT_INITIALIZED_ERROR = object()
FILE_UNSUPPORTED_VERSION_ERROR = object()
INVALID_IDENTIFIER_ERROR = object()

__all__ = [
    'FILE_NOT_INITIALIZED_ERROR',
    'FILE_UNSUPPORTED_VERSION_ERROR',
    'INVALID_IDENTIFIER_ERROR',
    'initialize_file',
    'list_saves',
    'store_save',
    'load_save',
    'delete_save',
    'rename_save',
]

def _progress_file_contents(
    start_offset: int, 
    section_size: int, 
    shift_amount: int, 
    file, 
    __BUFFER_SIZE = _BUFFER_SIZE,
    __BUFFER = _buffer, 
    __MASK = _BUFFER_SIZE - 1,
    /) -> None:
    tail_size = section_size & __MASK

    tail_offset = start_offset + section_size - tail_size
    
    file.seek(tail_offset)
    file.readinto(__BUFFER[:tail_size])

    file.seek(tail_offset + shift_amount)
    file.write(__BUFFER[:tail_size]) 

    for offset in range(tail_offset - __BUFFER_SIZE, start_offset - 1, -__BUFFER_SIZE):
        file.seek(offset)
        file.readinto(__BUFFER)

        file.seek(offset + shift_amount)
        file.write(__BUFFER)

def _regress_file_contents(
    start_offset: int, 
    section_size: int, 
    shift_amount: int, 
    file, 
    __BUFFER_SIZE = _BUFFER_SIZE,
    __BUFFER = _buffer, 
    __MASK = _BUFFER_SIZE - 1,
    /) -> None:
    tail_size = section_size & __MASK

    tail_offset = start_offset + section_size - tail_size

    for offset in range(start_offset, tail_offset, __BUFFER_SIZE):
        file.seek(offset)
        file.readinto(__BUFFER)

        file.seek(offset - shift_amount)
        file.write(__BUFFER)

    file.seek(tail_offset)
    file.readinto(__BUFFER[:tail_size])

    file.seek(tail_offset - shift_amount)
    file.write(__BUFFER[:tail_size]) 

def _update_stale_bounds(
    start_offset: int, 
    section_size: int, 
    delta: int,
    file,
    __UINT = _UINT_SIZE,
    __BUFFER_SIZE = _BUFFER_SIZE,
    __BUFFER = _buffer, 
    __MASK = _BUFFER_SIZE - 1,

    __PACK = _SINGLE_PACK,
    __UNPACK = _SINGLE_UNPACK,
    /) -> None:
    tail_size = section_size & __MASK

    tail_offset = start_offset + section_size - tail_size
    
    buffer_range = range(0, __BUFFER_SIZE, __UINT)

    file.seek(start_offset)
    for offset in range(start_offset, tail_offset, __BUFFER_SIZE):
        file.readinto(__BUFFER)

        for o in buffer_range:
            bound, = __UNPACK(__BUFFER[o:o+__UINT])
            __BUFFER[o:o+__UINT] = __PACK(bound + delta)

        file.seek(offset)
        file.write(__BUFFER)

    file.readinto(__BUFFER[:tail_size])

    for o in range(0, tail_size, __UINT):
        bound, = __UNPACK(__BUFFER[o:o+__UINT])
        __BUFFER[o:o+__UINT] = __PACK(bound + delta)

    file.seek(tail_offset)
    file.write(__BUFFER[:tail_size])

def _default_initialize(path: file_path, file,/) -> None:
    UINT = _UINT_SIZE; PACK = _SINGLE_PACK

    file.write(PACK(_VERSION) + bytes(UINT) + PACK(16) + bytes(UINT*2))

    _cached_versions[path] = _VERSION

_GLOBALS_FETCH = (
    _HEADER_SIZE,
    _SINGLE_PACK,
    _SINGLE_UNPACK,
    _DUAL_UNPACK,
    _UINT_SHIFT,
    _UINT_SIZE,
    _BUFFER_SHIFT,
    _BUFFER_SIZE,
    _buffer,
)

_HELPERS_FETCH = (
    _progress_file_contents,
    _regress_file_contents,
    _update_stale_bounds,
)

def initialize_file(path: file_path,/) -> object | None:
    '''
    Internally cache the names of the given file.

    Create and initialize a file if the given file does not exist.

    Default initalizes a file if the file is empty.
    '''
    if not (file_cache := _cached_files.get(path)):
        _cached_files[path] = file_cache = {}
        _cached_names[path] = name_cache = []
    else:
        file_cache.clear()
        name_cache = _cached_names[path]
        name_cache.clear()

    if not exists(path):
        with open(path, 'wb') as f:
            _default_initialize(path, f)
    else:
        HEADER_SIZE, _, UNPACK, _, SHIFT, UINT, _, BUFFER_SIZE, buffer = _GLOBALS_FETCH

        with open(path, 'rb+') as f:
            f.seek(0,2)

            size = f.tell()
            if size == 0:
                _default_initialize(path, f)

                return
            elif size < 4:
                return FILE_NOT_INITIALIZED_ERROR
            else:
                f.seek(0)

            version, = UNPACK(f.read(UINT))

            _cached_versions[path] = version

            if version == 1:
                save_count, = UNPACK(f.read(UINT))

                ends_offset = HEADER_SIZE + UINT
                
                name_bounds_size = save_count << SHIFT

                name_data_offset = ends_offset + name_bounds_size

                tail_size = name_bounds_size & (BUFFER_SIZE - 1)

                tail_offset = ends_offset + name_bounds_size - tail_size
                
                buffer_range = range(0, BUFFER_SIZE, UINT)

                queued_name_offset = name_data_offset
                i = 0
                for offset in range(ends_offset, tail_offset, BUFFER_SIZE):
                    f.seek(offset)
                    f.readinto(buffer)

                    f.seek(queued_name_offset)
                    
                    beginning = queued_name_offset - name_data_offset
                    for o in buffer_range:
                        end, = UNPACK(buffer[o:o+UINT])

                        name = f.read(end - beginning).decode('utf-8')

                        file_cache[name] = i
                        name_cache.append(name)
                        i += 1
                        
                        beginning = end

                    queued_name_offset = name_data_offset + beginning

                f.seek(tail_offset)
                f.readinto(buffer[:tail_size])

                f.seek(queued_name_offset)

                beginning = queued_name_offset - name_data_offset
                for o in range(0, tail_size, UINT):
                    end, = UNPACK(buffer[o:o+UINT])

                    name = f.read(end - beginning).decode('utf-8')

                    file_cache[name] = i
                    name_cache.append(name)
                    i += 1
                    
                    beginning = end
            else:
                return FILE_UNSUPPORTED_VERSION_ERROR

def list_saves(path: file_path,/) -> list[str] | object:
    '''
    Return a list of the cached names in a file.
    '''
    if (version := _cached_versions.get(path)) is None: return FILE_NOT_INITIALIZED_ERROR

    if version == 1:
        return _cached_names[path].copy()
    else:
        return FILE_UNSUPPORTED_VERSION_ERROR

def store_save(path: file_path, identifier: str | int, data:  bytes,/) -> object | None:
    '''
    Update a given save's contents.

    Add a new save if the given save doesn't exist.
    '''
    if (version := _cached_versions.get(path)) is None: return FILE_NOT_INITIALIZED_ERROR

    file_cache = _cached_files[path]

    if version == 1:
        save_count = len(file_cache)

        if isinstance(identifier, str):
            index = file_cache.get(identifier)

            if index is None:
                file_cache[identifier] = save_count
        else:
            if identifier >= save_count or identifier < 0: return INVALID_IDENTIFIER_ERROR

            index = identifier

        HEADER_SIZE, PACK, UNPACK, DUAL_UNPACK, \
        SHIFT, UINT, BUFFER_SHIFT, BUFFER_SIZE, \
        buffer \
            = _GLOBALS_FETCH
        
        progress_section, regress_section, update_stale_bounds = _HELPERS_FETCH

        # add a new save
        if len(file_cache) > save_count:
            data_size = len(data)

            name = identifier.encode('utf-8')
            name_size = len(name)

            _cached_names[path].append(identifier)

            save_bounds_shift = name_size + UINT
            save_data_shift = save_bounds_shift + UINT
            
            with open(path, 'rb+') as f:
                f.seek(0, 2)
                for _ in range(save_data_shift >> BUFFER_SHIFT):
                    f.write(buffer)
                f.write(buffer[:save_data_shift & (BUFFER_SIZE - 1)]) # mask

                f.seek(UINT*2)
                save_bounds_offset, = UNPACK(f.read(UINT))
                
                bounds_size = (save_count << SHIFT) + UINT
                save_data_offset = save_bounds_offset + bounds_size

                f.seek(save_data_offset - UINT)
                save_data_size, = UNPACK(f.read(UINT))

                f.seek(HEADER_SIZE + bounds_size - UINT)
                name_data_size, = UNPACK(f.read(UINT))

                progress_section(save_data_offset, save_data_size, save_data_shift, f)

                save_data_offset += save_data_shift
                
                f.seek(0, 2)
                f.write(data)

                f.seek(save_data_offset - UINT)
                f.write(PACK(save_data_size + data_size))

                progress_section(save_bounds_offset, bounds_size, save_bounds_shift, f)

                save_bounds_offset += save_bounds_shift

                name_bounds_end = HEADER_SIZE + bounds_size

                progress_section(name_bounds_end, name_data_size, UINT, f)

                f.seek(name_bounds_end)
                f.write(PACK(name_data_size + name_size))

                name_bounds_end += UINT

                f.seek(name_bounds_end + name_data_size)
                f.write(name)

                f.seek(UINT)
                f.write(PACK(save_count + 1))

                f.write(PACK(save_bounds_offset))
        else:
            data_size = len(data)
            
            with open(path, 'rb+') as f:
                f.seek(UINT*2)
                save_bounds_offset, = UNPACK(f.read(UINT))

                start_bound_offset = save_bounds_offset + (index << SHIFT)
                end_bound_offset = start_bound_offset + UINT

                f.seek(start_bound_offset)
                data_start, stale_data_end = DUAL_UNPACK(f.read(UINT*2))

                bounds_size = (save_count << SHIFT) + UINT
                save_data_offset = save_bounds_offset + bounds_size
                f.seek(save_data_offset - UINT)
                save_data_end, = UNPACK(f.read(UINT))

                save_data_shift = data_size - (stale_data_end - data_start)

                if save_data_shift < 0:
                    regress_section(save_data_offset + stale_data_end, save_data_end - stale_data_end, -save_data_shift, f)

                    f.seek(save_data_shift, 2)
                    f.truncate()
                else:
                    f.seek(0, 2)
                    for _ in range(save_data_shift >> BUFFER_SHIFT):
                        f.write(buffer)
                    f.write(buffer[:save_data_shift & (BUFFER_SIZE - 1)]) # mask
                    
                    progress_section(save_data_offset + stale_data_end, save_data_end - stale_data_end, save_data_shift, f)

                f.seek(save_bounds_offset + bounds_size + data_start)
                f.write(data)

                f.seek(end_bound_offset)
                f.write(PACK(stale_data_end + save_data_shift))

                stale_bound_size = (save_count - index - 1) << SHIFT

                update_stale_bounds(end_bound_offset + UINT, stale_bound_size, save_data_shift, f)
    else:
        return FILE_UNSUPPORTED_VERSION_ERROR

def load_save(path: file_path, identifier: str | int,/) -> bytes | object:
    '''
    Return the given save's data.

    Return ```None``` if it doesn't exist.
    '''
    if (version := _cached_versions.get(path)) is None: return FILE_NOT_INITIALIZED_ERROR

    file_cache = _cached_files[path]

    if version == 1:
        save_count = len(file_cache)

        if isinstance(identifier, str):
            index = file_cache.get(identifier)

            if index is None: return INVALID_IDENTIFIER_ERROR
        else:
            if identifier > save_count - 1 or identifier < 0: return INVALID_IDENTIFIER_ERROR

            index = identifier

        _, _, UNPACK, DUAL_UNPACK, \
        SHIFT, UINT, _, _, \
        _ \
            = _GLOBALS_FETCH
        
        with open(path, 'rb') as f:
            start_bound = index << SHIFT
            bounds_size = (save_count << SHIFT) + UINT

            f.seek(UINT*2)
            save_bounds_offset, = UNPACK(f.read(UINT))

            f.seek(save_bounds_offset + start_bound)
            data_start, data_end = DUAL_UNPACK(f.read(UINT*2))

            f.seek(save_bounds_offset + bounds_size + data_start)
            return f.read(data_end - data_start)
    else:
        return FILE_UNSUPPORTED_VERSION_ERROR

def delete_save(path: file_path, identifier: str | int,/) -> object | None:
    '''
    Delete a given save and remove its internal cache.

    Completely deletes data: not lazy deletion
    '''
    if (version := _cached_versions.get(path)) is None: return FILE_NOT_INITIALIZED_ERROR

    file_cache = _cached_files[path]

    if version == 1:
        save_count = len(file_cache)

        if isinstance(identifier, str):
            index = file_cache.get(identifier)

            if index is None: return INVALID_IDENTIFIER_ERROR
        else:
            if identifier >= save_count or identifier < 0: return INVALID_IDENTIFIER_ERROR

            index = identifier

        names = _cached_names[path]

        del file_cache[names[index]]
        del names[index]

        for i in range(index, len(names)):
            file_cache[names[i]] -= 1

        HEADER_SIZE, PACK, UNPACK, DUAL_UNPACK, \
        SHIFT, UINT, _, _, \
        _ \
            = _GLOBALS_FETCH
        
        _, regress_section, update_stale_bounds = _HELPERS_FETCH

        with open(path, 'rb+') as f:
            f.seek(UINT*2)
            save_bounds_offset, = UNPACK(f.read(UINT))
            
            start_bound = index << SHIFT
            end_bound = start_bound + UINT

            bounds_size = (save_count << SHIFT) + UINT
            stale_bound_size = (save_count - index - 1) << SHIFT

            name_bounds_end = HEADER_SIZE + bounds_size

            f.seek(HEADER_SIZE + start_bound)
            name_start, stale_name_end = DUAL_UNPACK(f.read(UINT*2))
            name_size = stale_name_end - name_start
            
            f.seek(name_bounds_end - UINT)
            name_data_size, = UNPACK(f.read(UINT))

            f.seek(save_bounds_offset + start_bound)

            data_start, stale_data_end = DUAL_UNPACK(f.read(UINT*2))
            data_size = stale_data_end - data_start
            
            save_data_offset = save_bounds_offset + bounds_size

            f.seek(save_data_offset - UINT)
            save_data_size, = UNPACK(f.read(UINT))

            name_end_bound_offset = HEADER_SIZE + end_bound
            regress_section(name_end_bound_offset + UINT, stale_bound_size + name_start, UINT, f)

            trailing_name_shift = UINT + name_size
            regress_section(name_bounds_end + stale_name_end, name_data_size - stale_name_end + end_bound, trailing_name_shift, f)

            save_data_shift = trailing_name_shift + UINT

            regress_section(save_bounds_offset + end_bound + UINT, stale_bound_size + data_start, save_data_shift, f)

            trailing_save_shift = save_data_shift + data_size
            regress_section(save_data_offset + stale_data_end, save_data_size - stale_data_end, trailing_save_shift, f)
            
            save_bounds_offset -= trailing_name_shift

            update_stale_bounds(name_end_bound_offset, stale_bound_size, -name_size, f)
            update_stale_bounds(save_bounds_offset + end_bound, stale_bound_size, -data_size, f)

            f.seek(UINT)
            f.write(PACK(save_count - 1))

            f.write(PACK(save_bounds_offset))

            f.seek(-trailing_save_shift,2)
            f.truncate()
    else:
        return FILE_UNSUPPORTED_VERSION_ERROR
    
def rename_save(path: file_path, identifier: str | int, new_name: str,/) -> object | None:
    '''
    Rename a given save.

    Updates the stored name and updates internal cache. 
    '''
    if (version := _cached_versions.get(path)) is None: return FILE_NOT_INITIALIZED_ERROR

    file_cache = _cached_files[path]

    if version == 1:
        save_count = len(file_cache)

        if isinstance(identifier, str):
            index = file_cache.get(identifier)

            if index is None: return INVALID_IDENTIFIER_ERROR
        else:
            if identifier >= save_count or identifier < 0: return INVALID_IDENTIFIER_ERROR

            index = identifier

        names = _cached_names[path]

        stale_name = names[index]
        del file_cache[stale_name]

        names[index] = new_name
        file_cache[new_name] = index

        HEADER_SIZE, PACK, UNPACK, DUAL_UNPACK, \
        SHIFT, UINT, BUFFER_SHIFT, BUFFER_SIZE, \
        buffer \
            = _GLOBALS_FETCH
        
        progress_section, regress_section, update_stale_bounds = _HELPERS_FETCH

        encoded = new_name.encode()
        name_size = len(encoded)

        with open(path, 'rb+') as f:
            f.seek(UINT*2)
            save_bounds_offset, = UNPACK(f.read(UINT))
            
            start_bound_offset = HEADER_SIZE + (index << SHIFT)
            end_bound_offset = start_bound_offset + UINT
            bounds_size = (save_count << SHIFT) + UINT

            f.seek(start_bound_offset)
            name_start, stale_name_end = DUAL_UNPACK(f.read(UINT*2))
            stale_name_size = stale_name_end - name_start

            f.seek(save_bounds_offset + bounds_size - UINT)
            save_data_size, = UNPACK(f.read(UINT))

            name_data_shift = name_size - stale_name_size

            name_data_offset = HEADER_SIZE + bounds_size

            shift_start = name_data_offset + stale_name_end
            if name_data_shift < 0:
                regress_section(shift_start, save_bounds_offset + bounds_size + save_data_size - shift_start, -name_data_shift, f)

                f.seek(name_data_shift, 2)
                f.truncate()
            else:
                f.seek(0, 2)
                for _ in range(name_data_shift >> BUFFER_SHIFT):
                    f.write(buffer)
                f.write(buffer[:name_data_shift & (BUFFER_SIZE - 1)]) # mask
                
                progress_section(shift_start, save_bounds_offset + bounds_size + save_data_size - shift_start, name_data_shift, f)
            
            f.seek(name_data_offset + name_start)
            f.write(encoded)
            
            f.seek(end_bound_offset)
            f.write(PACK(stale_name_end + name_data_shift))

            stale_bound_size = (save_count - index - 1) << SHIFT
            update_stale_bounds(end_bound_offset + UINT, stale_bound_size, name_data_shift, f)

            f.seek(UINT*2)
            f.write(PACK(save_bounds_offset + name_data_shift))
    else:
        return FILE_UNSUPPORTED_VERSION_ERROR