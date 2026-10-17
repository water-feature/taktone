"""Exercise compiled scene runtime with Unicorn after a developer source build.

Requires the optional unicorn package; the end-user patcher does not use it.
Run from the repository root: python3 internal/tests/verify_scenes.py
"""
import json
import struct
import sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.m68k_const import *

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from macro_runtime import CODE, TABLE, CONSTANTS as C
from panel_patch import BASE, syx

labels = {k: int(v, 16) for k, v in json.loads(
    (ROOT / 'reports/candidates/macro-runtime/audit.json').read_text())['symbols'].items()}
u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
u.mem_map(0x40000000, 0x8000000)
u.mem_map(0x80000000, 0x10000)
u.mem_write(BASE, syx.Syx.load(ROOT.parent / 'firmware/TT2D-recovery.syx').section(3))
u.mem_write(CODE, (ROOT / 'candidates/macro-runtime/runtime.bin').read_bytes())
STACK, STOP = 0x47fff000, 0x40001000


def put(at, value):
    u.mem_write(at, struct.pack('>I', value & 0xffffffff))


def get(at):
    return int.from_bytes(u.mem_read(at, 4), 'big')


def call(name, *args, end=STOP):
    u.mem_write(STACK, struct.pack('>' + 'I' * (len(args) + 1), STOP, *args))
    u.reg_write(UC_M68K_REG_SR, 0x2700)
    u.reg_write(UC_M68K_REG_A7, STACK)
    u.emu_start(labels[name], end, count=15_000_000)
    assert u.reg_read(UC_M68K_REG_PC) == end, name
    assert u.reg_read(UC_M68K_REG_A7) == STACK + (4 if end == STOP else 0), name


def default_records(at, count):
    assert bytes(u.mem_read(at, count * 1024)) == (b'\x01' + bytes(1023)) * count


call('macro_startup_clear', end=0x40001c94)
default_records(TABLE, 512)
u.mem_write(TABLE, b'\xa5' * 0x80000)
u.reg_write(UC_M68K_REG_A4, TABLE)
call('macro_default_table')
default_records(TABLE, 512)

# Real sparse load: an old project with zero stored rows has a valid checksum
# of zero records. Validate that checksum before normalizing empty scenes.
header = bytearray(32768)
h = 0x811c9dc5
for _ in range(0x20000):
    h = (h * 0x01000193) & 0xffffffff
struct.pack_into('>6I', header, 0, 0x584d4143, 4, 0x80000, h, h ^ 0xffffffff, 123)
widget, vtable, provider, ctrl, event = 0x42001000, 0x42002000, 0x42003000, 0x42004000, 0x42005000
MAPPER = 0x400308fe
manager, descriptors, page = 0x42007000, 0x42008000, 0x42009000
provider = manager + 0xec + 0x6a0 + 3 * 20
mapping_calls = []


def endpoint(uc, at, size, user):
    sp = uc.reg_read(UC_M68K_REG_A7)
    ret = get(sp)
    result = 0
    if at == 0x40137822:
        result = 0x42500000
    elif at == 0x400e29ec:
        assert get(sp + 4) == 0x80000 + 0x1bc0
        assert get(sp + 8) == len(header)
        uc.mem_write(get(sp + 12), bytes(header))
    elif at == MAPPER:
        mapping_calls.append(get(sp + 8))
        return  # Observe the actual native mapper; do not replace it.
    elif at == 0x400657b2:
        result = page
    elif at == 0x4013865a:
        result = 0x4200a000
    elif at == 0x4001d24e:
        result = get(C['TRACK'])
    elif at == 0x4000fa80:
        result = 987
    elif at not in (0x401385c0, 0x401385e6, 0x400ca382):
        raise AssertionError(hex(at))
    for reg in (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_A0, UC_M68K_REG_A1):
        uc.reg_write(reg, 0xa5a5a5a5)
    uc.reg_write(UC_M68K_REG_D0, result)
    uc.reg_write(UC_M68K_REG_A7, sp + 4)
    uc.reg_write(UC_M68K_REG_PC, ret)


for at in (0x40137822, 0x401385c0, 0x401385e6, 0x400e29ec,
           MAPPER, 0x400657b2, 0x4013865a, 0x4001d24e, 0x4000fa80, 0x400ca382):
    u.hook_add(UC_HOOK_CODE, endpoint, begin=at, end=at)
put(C['PROJECT_ID'], 123)
u.reg_write(UC_M68K_REG_D0, 0x80000)
u.mem_write(TABLE, b'\xa5' * 0x80000)
call('macro_load')
assert get(C['LOAD_STATUS']) == 1
default_records(TABLE, 512)
# Corrupt checksum must reject the image before defaults/publication.
header[12] ^= 1
u.mem_write(TABLE, b'\xa5' * 0x80000)
u.reg_write(UC_M68K_REG_D0, 0x80000)
call('macro_load')
assert get(C['LOAD_STATUS']) == 3
assert bytes(u.mem_read(TABLE, 1024)) == b'\xa5' * 1024
header[12] ^= 1
# Explicitly disabled and learned scenes survive default normalization.
u.mem_write(TABLE, bytes(0x80000))
put(TABLE + 1024 + 4, C['SCENE_MAGIC'])
put(TABLE + 2048 + 4, C['SCENE_MAGIC'])
u.mem_write(TABLE + 2048 + 8, b'\x01')
u.mem_write(TABLE + 2048 + 68, b'\x00\x2a')
before = bytes(u.mem_read(TABLE + 1024, 2048))
u.reg_write(UC_M68K_REG_A4, TABLE)
call('macro_default_unedited_scenes')
assert bytes(u.mem_read(TABLE + 1024, 2048)) == before
assert u.mem_read(TABLE, 1) == b'\x01'

# A clean native draw skips rendering: keep its last grid for push mapping.
# Execute the firmware's real grid mapper and provider resolver/vtables.
put(widget, 0x40183514)
put(widget + 0x68, manager)
put(widget + 0x7c, descriptors)
put(widget + 0x90, 0)
put(descriptors, 0)
put(provider, 0x4017eb58)
for knob in range(8):
    put(page + 8 + 4 * knob, 0x6c + knob)
put(C['ACTIVE_WIDGET'], widget)
u.mem_write(ctrl + 0x20, b'\x00')
call('macro_draw', ctrl, 0)
assert get(C['ACTIVE_WIDGET']) == widget
put(C['ACTIVE_WIDGET'], 0)  # Native dispatch supplies the live widget.
put(C['HELD'], 2)
put(C['PATTERN'], 0)
put(C['TRACK'], 3)
put(C['RAM_READY'], 1)
scene = TABLE + 2048
for knob in range(8):
    index = 3 * 53 + get(0x401a9d9c + (0x6c + knob) * 52 + 4)
    byte = scene + 8 + index // 8
    bit = 1 << (index % 8)
    u.mem_write(byte, bytes([u.mem_read(byte, 1)[0] | bit]))
    u.mem_write(scene + 68 + index * 2, b'\x12\x34')
    u.mem_write(event, struct.pack('>6I', 0, 0, 0, 40 + knob, 1, 127))
    call('macro_grid_key', widget, event)
    assert not (u.mem_read(byte, 1)[0] & bit), knob
    assert bytes(u.mem_read(scene + 68 + index * 2, 2)) == bytes(2), knob
    assert get(C['HELD']) == 2
assert mapping_calls == list(range(8))
# FX/master and an unmapped knob cannot erase an audio-track lock.
before = bytes(u.mem_read(scene, 1024))
put(page + 8, 0x5b)
put(manager + 0xec + 0x784, 0x4017ebd8)
u.mem_write(event, struct.pack('>6I', 0, 0, 0, 40, 1, 127))
call('macro_grid_key', widget, event)
assert bytes(u.mem_read(scene, 1024)) == before
put(page + 8, 0)
call('macro_grid_key', widget, event)
assert bytes(u.mem_read(scene, 1024)) == before
# A real page redraw without a grid invalidates the cached mapper.
u.mem_write(ctrl + 0x20, b'\x01')
call('macro_draw', ctrl, 0)
assert get(C['ACTIVE_WIDGET']) == 0
# With no scene held, the wrapper must preserve the native LINK frame.
# Stop immediately after the displaced prologue and inspect frame/stack.
put(C['HELD'], 0xffffffff)
u.mem_write(STACK, struct.pack('>3I', STOP, widget, event))
u.reg_write(UC_M68K_REG_SR, 0x2700)
u.reg_write(UC_M68K_REG_A7, STACK)
u.reg_write(UC_M68K_REG_A6, 0x4200b000)
u.emu_start(labels['macro_grid_key'], 0x4003307e, count=10000)
assert u.reg_read(UC_M68K_REG_A6) == STACK - 4
assert u.reg_read(UC_M68K_REG_A7) == STACK - 84
assert get(STACK - 4) == 0x4200b000
print('Passed: startup defaults; real sparse project load; bad checksum rejection; '
      'saved state preservation; clean-frame grid retention; A-H lock clearing with no cached widget through native mapper/provider code; FX/unmapped rejection; page invalidation.')
