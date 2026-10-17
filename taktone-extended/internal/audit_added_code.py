"""Audit injected code, supplementing cfisa with CFPRM MOVE EA restrictions."""
from metadata_paths import json_path
import json
import sys
import argparse
from pathlib import Path

from panel_patch import ROOT, BASE, TABLE, syx
from audio_patch import codec_selector

sys.path.insert(0, str(ROOT / 'source'))
from emu import cfisa as cf


def audit(code, address):
    errors = []
    offset = 0
    count = 0
    while offset < len(code):
        def read16(pos):
            assert offset + pos + 2 <= len(code), hex(address + offset)
            return int.from_bytes(code[offset + pos:offset + pos + 2], 'big')
        ins = cf.decode(read16, address + offset)
        reason = None
        if ins.flags & (cf.ILLEGAL | cf.FPU | cf.LINEF):
            reason = 'unsupported opcode'
        opcode = read16(0)
        if opcode >> 12 in (1, 2, 3):
            # CFPRM MOVE matrix: restrict memory-to-memory and immediate
            # destinations. ISA_B permits immediate -> d16(An) byte/word.
            if ins.src == cf.D16 and ins.dst in (cf.IDX, cf.ABS):
                reason = 'MOVE displacement source to indexed/absolute destination'
            if ins.src in (cf.IDX, cf.ABS, cf.IMM) and ins.dst in (cf.D16, cf.IDX, cf.ABS):
                if not (ins.src == cf.IMM and ins.dst == cf.D16 and ins.size in (1, 2)):
                    reason = 'MOVE source/destination combination forbidden by CFPRM'
        if (opcode & 0xFFC0) == 0x4C00 and ((opcode >> 3) & 7) not in (0,2,3,4,5):
            reason = 'MUL.L source effective address forbidden by CFPRM longword table'
        if ins.length > 6:
            reason = 'Instruction exceeds ColdFire six-byte maximum'
        if reason:
            errors.append(dict(address=hex(address + offset), instruction=ins.op, reason=reason))
        assert ins.length > 0
        offset += ins.length
        count += 1
    assert offset == len(code)
    return count, errors


def audit_core(image, original, details):
    """Audit copied executable spans and the in-place shutdown copy."""
    table = int(details['table_address'],16)
    payload = image[-details['table_size']:]
    blocks = [(BASE+len(original), image[len(original):len(original)+details['stub_size']])]
    for name in ('slot_stub','selector_stub'):
        address = int(details[name],16)
        size = details[name+'_size']
        blocks.append((address,payload[address-table:address-table+size]))
    address = int(details['audio_codec_selector'],16)
    blocks.append((address,payload[address-table:address-table+len(codec_selector())]))
    address = int(details['audio_old_codec_stub'],16)
    end = payload.index(bytes.fromhex('4ef940068fea'),address-table)+6
    blocks.append((address,payload[address-table:end]))
    from shutdown_patch import COPY_AT,COPY_AFTER
    blocks.append((COPY_AT,image[COPY_AT-BASE:COPY_AT-BASE+len(COPY_AFTER)]))
    for bad in ('13fc000147be01e2','4c3c200001000193'):
        assert audit(bytes.fromhex(bad),0x40000000)[1], 'Audit must reject unsupported encodings'
    count=0
    for address,code in blocks:
        instructions,errors=audit(code,address)
        assert not errors,errors
        count+=instructions
    return dict(instructions=count,errors=[],scope='Core executable stubs and shutdown copy')
