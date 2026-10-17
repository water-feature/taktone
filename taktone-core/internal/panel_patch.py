"""Measured Digitone button translation and startup payload copy."""
from metadata_paths import json_path
from firmware_profiles import profile_for
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tooling/elekloader-upstream'))
from elekloader import syx
from elekloader.codec.aplib import pack_section
from build_hybrid import DEV

BASE = 0x40000400
TABLE = 0x47BE0000
# DN semantic code -> DT semantic code. Extra DN-only keys emit stock DT's
# unused code zero for now. MIDI supplies TRK; VOICE supplies SAMPLE; SYN2 is unassigned.
KEYS = {0: 0, 1: 1, 2: 2, 3: 0, 4: 3, 5: 4, 6: 5, 7: 6,
        8: 7, 9: 8, 10: 9, 11: 10, 12: 11, 13: 12, 14: 13,
        15: 14, 16: 15, 17: 16, 18: 17, 19: 18, 20: 19,
        21: 20, 22: 0, 23: 21, 24: 22, 25: 23, 54: 48}
KEYS.update({i: i - 2 for i in range(26, 42)})
KEYS.update({i: 0 for i in range(42, 46)})
KEYS.update({i: i - 6 for i in range(46, 54)})


def make_patch(original, *, payload_base=TABLE):
    TABLE = payload_base
    profile = profile_for(original)
    main = bytearray(original)
    records = json.loads((json_path(ROOT / 'panel-dn.json')).read_text())
    assert len(records) == 56
    forward = [0] * 56
    for r in records:
        codes = {e[0] for e in r['down']}
        assert len(codes) == 1, r
        forward[r['channel'] * 8 + r['bit']] = KEYS[codes.pop()]
    inverse = [0xFFFFFFFF] * 49
    for wire, code in enumerate(forward):
        if code and inverse[code] == 0xFFFFFFFF:
            inverse[code] = wire
    assert all(x != 0xFFFFFFFF for x in inverse[1:])
    payload = struct.pack('>105I', *(forward + inverse))
    changes = []

    def replace(address, before, after):
        offset = address - BASE
        assert main[offset:offset + len(before)] == before, hex(address)
        assert len(before) == len(after)
        main[offset:offset + len(before)] = after
        changes.append(dict(address=hex(address), before=before.hex(), after=after.hex()))

    # All absolute operands referencing the two original button tables.
    for old, new, expected in [(0x4018E89C, TABLE, 3),
                                (0x4018E7D8, TABLE + 56 * 4, 5)]:
        old = profile.address(old)
        needle = struct.pack('>I', old)
        offsets = [i for i in range(len(main) - 3) if main[i:i + 4] == needle]
        assert len(offsets) == expected, (hex(old), offsets)
        for offset in offsets:
            replace(BASE + offset, needle, struct.pack('>I', new))

    # Copy the added tables out of the image before stock startup clears BSS.
    # Preserve scratch registers, then tail-call the displaced stock routine.
    # The destination lies beyond the stock BSS end (0x439d0000).
    stub_at = BASE + len(main)
    assert stub_at % 4 == 0
    stub = bytearray.fromhex('2f002f082f09')  # save d0/a0/a1
    stub += bytes.fromhex('41f9') + bytes(4)  # lea payload,a0
    stub += bytes.fromhex('43f9') + struct.pack('>I', TABLE)
    stub += bytes([0x70, len(payload) // 4 - 1])
    stub += bytes.fromhex('22d853806afa')  # copy long; subq; bpl copy
    stub += bytes.fromhex('225f205f201f')  # restore a1/a0/d0
    stub += bytes.fromhex('4ef9') + struct.pack('>I', 0x40001C94)
    struct.pack_into('>I', stub, 8, stub_at + len(stub))
    replace(0x40000538, bytes.fromhex('4eb940001c94'),
            bytes.fromhex('4eb9') + struct.pack('>I', stub_at))
    main.extend(stub + payload)
    return bytes(main), dict(base_version=profile.version, changes=changes, table_address=hex(TABLE),
        stub_address=hex(stub_at), stub_size=len(stub), table_size=len(payload),
        forward=forward, inverse=inverse,
        limitations=['Original Digitone mk1 only; Digitone Keys excluded', 'Physical worst-case deadlines and shutdown power margin unmeasured'])
