'''
Config file manager.
'''
from os.path import join, exists
from struct import Struct
from typing import Any
from constants import DATA_DIR, CONFIG_FILE

_CONFIG_FILE_PATH = join(DATA_DIR, CONFIG_FILE)

_LITTLE_ENDIAN_U32 = Struct('<I')
_U32_PACK = _LITTLE_ENDIAN_U32.pack
_U32_UNPACK = _LITTLE_ENDIAN_U32.unpack

_UINT_SIZE = 4

_LITTLE_ENDIAN_F64 = Struct('<d')
_F64_PACK = _LITTLE_ENDIAN_F64.pack
_F64_UNPACK = _LITTLE_ENDIAN_F64.unpack

_FLOAT_SIZE = 8

_VERSION = 1

UNSUPPORTED_VERSION_ERROR = -1

def _default_initialize(
    file,
    default_cam_speed: int | float,
    default_swift_mult: int | float,
    default_cyclic_freq: int,
    default_save_file: str,
    default_save: str,
    /) -> None:
    U32_PACK = _U32_PACK
    F64_PACK = _F64_PACK
    
    file.write(U32_PACK(_VERSION))
    file.write(F64_PACK(default_cam_speed))
    file.write(F64_PACK(default_swift_mult))
    file.write(F64_PACK(default_cyclic_freq))
    encoded = default_save_file.encode('utf-8')
    file.write(U32_PACK(len(encoded)))
    file.write(encoded)
    encoded = default_save.encode('utf-8')
    file.write(U32_PACK(len(encoded)))
    file.write(encoded)

def load_config(
    default_cam_speed: int | float,
    default_swift_mult: int | float,
    default_cyclic_freq: int,
    default_save_file: str,
    default_save: str,
    /) -> tuple[Any]:
    PATH = _CONFIG_FILE_PATH

    if not exists(PATH):
        with open(PATH, 'wb') as f:
            _default_initialize(
                f,
                default_cam_speed,
                default_swift_mult,
                default_cyclic_freq,
                default_save_file,
                default_save,
            )

        return (
            _VERSION,
            default_cam_speed,
            default_swift_mult,
            default_cyclic_freq,
            default_save_file,
            default_save,
        )
    else:
        UINT = _UINT_SIZE
        FLOAT = _FLOAT_SIZE

        U32_UNPACK = _U32_UNPACK
        F64_UNPACK = _F64_UNPACK

        with open(PATH, 'rb+') as f:
            f.seek(0,2)
            size = f.tell()
            f.seek(0)

            if size < 4:
                _default_initialize(
                    f,
                    default_cam_speed,
                    default_swift_mult,
                    default_cyclic_freq,
                    default_save_file,
                    default_save,
                )

                return (
                    _VERSION,
                    default_cam_speed,
                    default_swift_mult,
                    default_cyclic_freq,
                    default_save_file,
                    default_save,
                )

            version, = U32_UNPACK(f.read(UINT))

            if version == 1:
                cam_speed, = F64_UNPACK(f.read(FLOAT))
                swift_mult, = F64_UNPACK(f.read(FLOAT))
                cyclic_freq, = F64_UNPACK(f.read(FLOAT))

                length, = U32_UNPACK(f.read(UINT))
                save_file = f.read(length).decode('utf-8')

                length, = U32_UNPACK(f.read(UINT))
                save_name = f.read(length).decode('utf-8')

                return (
                    version,
                    cam_speed,
                    swift_mult,
                    cyclic_freq,
                    save_file,
                    save_name
                )

            else:
                return UNSUPPORTED_VERSION_ERROR
            
def update_config(
    cam_speed: int | float,
    swift_mult: int | float,
    cyclic_freq: int,
    save_file: str,
    save_name: str,
    /) -> None:
    U32_PACK = _U32_PACK
    F64_PACK = _F64_PACK

    with open(_CONFIG_FILE_PATH, 'rb+') as f:
        version, = _U32_UNPACK(f.read(_UINT_SIZE))

        if version == 1:
            f.write(F64_PACK(cam_speed))
            f.write(F64_PACK(swift_mult))
            f.write(F64_PACK(cyclic_freq))
            encoded = save_file.encode('utf-8')
            f.write(U32_PACK(len(encoded)))
            f.write(encoded)
            encoded = save_name.encode('utf-8')
            f.write(U32_PACK(len(encoded)))
            f.write(encoded)
            f.truncate()