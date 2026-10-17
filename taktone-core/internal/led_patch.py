"""Translate LED slots and packed selectors at the UART boundary."""
from metadata_paths import json_path
from firmware_profiles import profile_for, DT153
import json
from pathlib import Path
import struct
import sys

from panel_patch import BASE, TABLE, ROOT, make_patch, syx, pack_section, DEV

LED_MAP = list(range(18)) + [19, 20] + list(range(22, 41)) + [255] + list(range(42, 46))
assert len(LED_MAP) == 44


class Asm:
    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.branches = []

    def emit(self, hexbytes):
        self.code.extend(bytes.fromhex(hexbytes))

    def absolute(self, opcode, address):
        self.emit(opcode)
        self.code.extend(struct.pack('>I', address))

    def label(self, name):
        self.labels[name] = len(self.code)

    def branch(self, opcode, name):
        self.emit(opcode)
        self.branches.append((len(self.code), name))
        self.emit('0000')

    def finish(self):
        for offset, name in self.branches:
            struct.pack_into('>h', self.code, offset, self.labels[name] - offset)
        return bytes(self.code)


def slot_code(lut, flag, init_packet, init_size, *, profile=DT153):
    a = Asm()
    a.emit('2f002f082f09')  # save d0/a0/a1
    a.absolute('4a39', flag)  # tst.b init flag
    a.branch('6600', 'normal')
    # ColdFire rejects immediate -> absolute MOVE (8-byte instruction).
    # D0 is already saved: use MOVEQ plus register -> absolute MOVE instead.
    a.emit('7001')
    a.absolute('13c0', flag)
    a.absolute('4879', init_packet)
    a.absolute('2f3c', init_size)
    a.absolute('4eb9', 0x400024C0)
    a.emit('508f')
    a.label('normal')
    a.emit('206f0014700010280001')  # buffer at 20(sp); zero d0; LED byte
    a.absolute('43f9', lut)
    a.emit('103108000c0000ff')  # LUT[d0]; compare invalid 255
    a.branch('6700', 'skip')
    a.emit('11400001225f205f201f')  # store physical ID; restore registers
    a.absolute('4ef9', 0x400024C0)  # original TX routine, original arguments
    a.label('skip')
    a.emit('225f205f201f4e75')  # no physical counterpart for DT's unknown LED
    return a.finish()


def selector_code(lut, state, *, profile=DT153):
    a = Asm()
    a.emit('4fefffe048d70cfc')  # reserve 32; save d2-d7/a2-a3
    a.emit('282f0024262f0028e58c7a03')  # group*4 -> d4; packed slots -> d3; loop 4
    a.absolute('45f9', lut)
    a.absolute('47f9', state)
    a.label('loop')
    a.emit('7c001c3248000c0600ff')
    a.branch('6700', 'next')
    a.emit('2006028000000003e3887203e1a9e48e7e001e336800')
    # d0=physical bit shift, d1=mask, d6=physical group, d7=old packed slots
    a.emit('4681ce812203028100000003e1a98e8117876800')
    a.emit('2f072f06')  # packed slots, physical group
    a.absolute('4eb9', profile.address(0x400E6238))  # original two-byte selector emitter
    a.emit('508f')
    a.label('next')
    a.emit('e48b52845385')  # next two source bits, next LED, decrement loop
    a.branch('6a00', 'loop')
    a.emit('4cd70cfc4fef00204e75')
    return a.finish()


def make_led_patch(original, *, payload_base=TABLE):
    TABLE = payload_base
    profile = profile_for(original)
    patched, details = make_patch(original, payload_base=TABLE)
    main = bytearray(patched[:len(original)])
    button_data = struct.pack('>105I', *(details['forward'] + details['inverse']))
    payload = bytearray(button_data + bytes(LED_MAP))
    lut_at = TABLE + len(button_data)
    state_at = TABLE + len(payload)
    payload.extend(bytes(18))
    flag_at = TABLE + len(payload)
    payload.extend(bytes(2))  # initialized flag plus alignment
    unused = sorted(set(range(72)) - (set(LED_MAP) - {255}))
    packet = bytes(v for led in unused for slot in range(4) for v in (0xB0 + slot, led, 0))
    packet_at = TABLE + len(payload)
    payload.extend(packet)
    while len(payload) % 4:
        payload.append(0)
    slot_at = TABLE + len(payload)
    slots = slot_code(lut_at, flag_at, packet_at, len(packet), profile=profile)
    payload.extend(slots)
    while len(payload) % 4:
        payload.append(0)
    selector_at = TABLE + len(payload)
    selectors = selector_code(lut_at, state_at, profile=profile)
    payload.extend(selectors)
    while len(payload) % 4:
        payload.append(0)

    def replace(address, before, after):
        offset = address - BASE
        assert bytes(main[offset:offset + len(before)]) == before, hex(address)
        assert len(before) == len(after)
        main[offset:offset + len(before)] = after
        details['changes'].append(dict(address=hex(address), before=before.hex(), after=after.hex()))

    for site in [0x400E64EC, 0x400E67B8]:
        replace(profile.address(site), bytes.fromhex('4eb9400024c0'), bytes.fromhex('4eb9') + struct.pack('>I', slot_at))
    replace(profile.address(0x4020DB00), struct.pack('>I', profile.address(0x400E6238)), struct.pack('>I', selector_at))

    # Same original startup hook as XDT1, with a larger copy count and aligned
    # payload. The RAM functions are copied before stock BSS clearing.
    stub_at = BASE + len(main)
    stub = bytearray.fromhex('2f002f082f0941f9') + bytes(4)
    stub += bytes.fromhex('43f9') + struct.pack('>I', TABLE)
    stub += bytes.fromhex('203c') + struct.pack('>I', len(payload) // 4 - 1)
    stub += bytes.fromhex('22d853806afa225f205f201f4ef9') + struct.pack('>I', 0x40001C94)
    while len(stub) % 4:
        stub.extend(bytes.fromhex('4e71'))
    struct.pack_into('>I', stub, 8, stub_at + len(stub))
    main.extend(stub + payload)
    details.update(version='XDT2', led_map=LED_MAP, led_lut=hex(lut_at),
        selector_state=hex(state_at), led_init_flag=hex(flag_at), led_init_packet=hex(packet_at),
        led_init_size=len(packet), unused_dn_leds=unused,
        slot_stub=hex(slot_at), slot_stub_size=len(slots), selector_stub=hex(selector_at),
        selector_stub_size=len(selectors), stub_size=len(stub), table_size=len(payload),
        limitations=['Original Digitone mk1 only; Digitone Keys excluded', 'Physical worst-case deadlines and shutdown power margin unmeasured'])
    return bytes(main), details
