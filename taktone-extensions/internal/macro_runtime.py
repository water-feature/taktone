"""Build and statically audit the four-macro ColdFire runtime.

This module emits code/data only. Packaging requires the persistence hooks
and integration qualification; it never sends firmware to an instrument.
"""
from metadata_paths import json_path
import json
import hashlib
from pathlib import Path
import struct
from ghidra_assemble import assemble
from audit_added_code import audit

ROOT = Path(__file__).resolve().parent
CODE = 0x431B0000
STATE = 0x431B8000
TABLE = 0x431C0000
FIELDS = ['FUNC','DOWN','HELD','PATTERN','UI_DEPTH','ENC_DEPTH','TRACK',
    'HOLD_PATTERN_TOKEN','PROJECT_ID','PENDING_OWNER','LOAD_PENDING','INITIALIZED',
    'DIRTY','BOOT_RESTORED','ERROR','CTRL','UI_DIRTY','SAVE_RESULT','PENDING_SLOT',
    'PLAY_CONSUMED','CLEAR_DEPTH','ACTIVE_WIDGET','QUERY_LOCK','AUDIO_PTR','AUDIO_DIRTY','LOAD_STATUS','DIAG_SEQ','EDIT_SEQ','PREVIOUS_ID','LOAD_REASON','RAM_READY','SCENE_CLIP_VALID','SCENE_TRANSPORT_MASK']
CONSTANTS = {name: STATE + index * 4 for index, name in enumerate(FIELDS)}
CONSTANTS.update(TABLE=TABLE, SCENE_MAGIC=0x53434E33, PROJECT_GLOBAL=0x421F9B90,
    PATTERN_GLOBAL=0x4199DC38, LED_INIT=0x431A01E2,
    LED_CACHE=STATE+0x100, LED_PACKET=STATE+0x104, LED_SELECTOR_PACKET=STATE+0x110,
    SELECTOR_STATE=0x431a01d0, ROW_DIRTY_MAP=STATE+0x140, SCENE_CLIP=0x43254000,
    AUDIO_A=STATE+0x400,AUDIO_B=STATE+0xc00,
    HEADER=0x43240000, NATIVE_HEADER=0x431BC000,
    CLIP_META=STATE+0x120, CLIP_NEXT=STATE+0x130, CLIP_TABLE=0x43250000, SCRATCH=0x43248000, PACK=0x432C0000, SAVED_TABLE=0x433C0000, STAGING=0x43440000, AUDIO_RESTORE=0x431BD000,
    DIAG_RING=0x431BE000, SHUT_HEADER=0x434C0000, SHUT_PACK=0x43500000,
    RESERVE_START=0x4319D6B0, RESERVE_END=0x4399D6B0,
    GUARD_LOW=0x4319D6B0, GUARD_HIGH=0x4399D6AC, GUARD_MAGIC=0x58445443)


def getter(name, original, domain):
    return f'''
{name}:
 tst.l (@UI_DEPTH).l
 beq.w @{name}_stock
 lea (-16,SP),SP
 movem.l {{ D2 D3 A2 A3}},(SP)
 jsr @macro_pointer
 tst.l D0
 beq.w @{name}_fallback
 movea.l D0,A3
 move.l (24,SP),-(SP)
 jsr 0x40078d80
 addq.l #4,SP
 tst.l D0
 bmi.w @{name}_fallback
 cmpi.l #52,D0
 bhi.w @{name}_fallback
 move.l D0,D2
 {domain}
 cmpi.l #8,D0
 bhi.w @{name}_fallback
 moveq 53,D1
 muls.l D1,D0
 add.l D0,D2
 moveq 0,D0
 move.l D0,(@QUERY_LOCK).l
 tst.l (@CLEAR_DEPTH).l
 bne.w @{name}_clear
 move.l (4,A3),D0
 cmpi.l #@SCENE_MAGIC,D0
 bne.w @{name}_fallback
 move.l D2,D0
 lsr.l #3,D0
 lea (8,A3),A0
 adda.l D0,A0
 moveq 7,D1
 and.l D2,D1
 moveq 0,D0
 move.b (A0),D0
 btst.l D1,D0
 beq.w @{name}_fallback
 moveq 1,D0
 move.l D0,(@QUERY_LOCK).l
 lea (68,A3),A0
 move.w (0,A0,D2*2),D0
 ext.l D0
 movem.l (SP),{{ D2 D3 A2 A3}}
 lea (16,SP),SP
 rts
{name}_clear:
 move.l D2,D0
 lsr.l #3,D0
 lea (8,A3),A0
 adda.l D0,A0
 moveq 7,D1
 and.l D2,D1
 addq.l #1,(@EDIT_SEQ).l
 bclr.b D1,(A0)
 lea (68,A3),A0
 moveq 0,D0
 move.w D0,(0,A0,D2*2)
 move.l A3,D0
 jsr @macro_row_dirty
 addq.l #1,(@EDIT_SEQ).l
 moveq 1,D0
 move.l D0,(@DIRTY).l
 move.l D0,(@UI_DIRTY).l
 move.l D0,(@AUDIO_DIRTY).l
 bra.w @{name}_fallback
{name}_fallback:
 movem.l (SP),{{ D2 D3 A2 A3}}
 lea (16,SP),SP
{name}_stock:
 jmp {hex(original)}
'''


def build(old_frame, extra_source='', extra_constants=None):
    constants = dict(CONSTANTS, OLD_FRAME=old_frame)
    constants.update(extra_constants or {})
    source = (ROOT / 'macros_runtime.s').read_text()
    source += getter('macro_get_sound', 0x4000FA80,
        'move.l (@TRACK).l,D0\n cmpi.l #7,D0\n bhi.w @macro_get_sound_fallback')
    # Global FX/master pages cannot p-lock. Their IDs overlap the audio-track
    # index map, so neither scene display nor encoder-push clear may use it.
    source += '\nmacro_get_fx:\n jmp 0x4000fd52\n'
    source += '''
set_original:
 lea (-0x2c,SP),SP
 movem.l { D2 D3 D4 D5 D6 D7 A2 A3},(SP)
 jmp 0x4000fefe
'''
    source += (ROOT/'macros_storage.s').read_text()
    source += (ROOT/'macros_pattern.s').read_text()
    source += (ROOT/'macros_partial.s').read_text()
    source += extra_source
    blob, symbols = assemble(source, CODE, constants)
    assert CODE + len(blob) < STATE, 'runtime overlaps state'
    count, errors = audit(blob, CODE)
    inputs={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in
        ('macros_runtime.s','macros_storage.s','macros_pattern.s','macros_partial.s',
         'macro_runtime.py','ghidra_assemble.py','TaktoneAssembleBatch.java')}
    report = dict(instructions=count, bytes=len(blob), errors=errors,input_sha256=inputs,
        symbols={k:hex(v) for k,v in symbols.items()}, constants={k:hex(v) for k,v in constants.items()})
    (json_path(ROOT / 'candidates/macro-runtime/audit.json')).write_text(json.dumps(report, indent=2)+'\n')
    assert not errors, errors
    data = bytearray(0x200)
    for name in ('HELD','PATTERN','PROJECT_ID','PREVIOUS_ID'):
        struct.pack_into('>i', data, constants[name]-STATE, -1)
    data[0x100:0x104] = b'\xff'*4
    data[0x104:0x110] = bytes.fromhex('b02e00b12e00b22e00b32e00')
    struct.pack_into('>I',data,constants['AUDIO_DIRTY']-STATE,1)
    struct.pack_into('>I',data,constants['RAM_READY']-STATE,1)
    return blob, symbols, bytes(data)


