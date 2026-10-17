"""Digitone codec bring-up with Digitakt audio buffers."""
from metadata_paths import json_path
from firmware_profiles import profile_for, DT153
import json
import struct

from autosave_patch import make_autosave_patch, ROOT, BASE, syx, pack_section, DEV
from led_patch import Asm
from panel_patch import TABLE


def codec_selector(*, profile=DT153):
    a = Asm()
    a.absolute('2039', profile.address(0x401F55C0))
    a.emit('028000080000')
    a.branch('6600', 'old')
    a.emit('7000103900000000220002810000001f0c8100000004')
    a.branch('6f00', 'old')  # revision <= 4
    a.emit('08000007')       # high hardware-ID bit selects old protocol
    a.branch('6600', 'old')
    a.absolute('4ef9', 0x40068F66)
    a.label('old')
    a.absolute('4ef9', 0x40068FC2)
    return a.finish()


def make_audio_patch(original, *, payload_base=TABLE):
    TABLE = payload_base
    profile = profile_for(original)
    image, details = make_autosave_patch(original, payload_base=TABLE)
    main = bytearray(image[:len(original)])
    stub = bytearray(image[len(original):len(original) + details['stub_size']])
    payload = bytearray(image[-details['table_size']:])
    while len(payload) % 4:
        payload.append(0)
    selector_at = TABLE + len(payload)
    payload.extend(codec_selector(profile=profile))
    while len(payload) % 4:
        payload.append(0)
    old_at = TABLE + len(payload)
    old = Asm()
    old.emit('4e9348780064')                 # SSI setup, then native delay 100
    old.absolute('4eb9', profile.address(0x400E8A70))
    old.emit('588f')
    # Original three old-codec register calls; initialize A2 as stock does.
    old.code.extend(original[0x40068FC2 - BASE:0x40068FE4 - BASE])
    old.emit('4fef0018')                     # discard original codec arguments
    old.absolute('4ef9', 0x40068FEA)
    payload.extend(old.finish())
    while len(payload) % 4:
        payload.append(0)

    def replace(at, before, after):
        offset = at - BASE
        assert main[offset:offset + len(before)] == before, hex(at)
        assert len(before) == len(after)
        main[offset:offset + len(after)] = after
        details['changes'].append(dict(address=hex(at), before=before.hex(), after=after.hex()))

    # Match native DN SSI1_RCR.RSCKP selection; keep DT buffer/DMA addresses.
    replace(0x40000FC8, bytes.fromhex('203c00000488'), bytes.fromhex('203c00000480'))
    replace(0x40000FD6, bytes.fromhex('223c00000480'), bytes.fromhex('223c00000488'))
    replace(0x40068F4C, original[0x40068F4C - BASE:0x40068F54 - BASE],
            bytes.fromhex('4ef9') + struct.pack('>I', selector_at) + bytes.fromhex('4e71'))
    replace(0x40068FC2, original[0x40068FC2 - BASE:0x40068FCA - BASE],
            bytes.fromhex('4ef9') + struct.pack('>I', old_at) + bytes.fromhex('4e71'))
    # The original DN's newer codec reset is PF7, not DT's PE1.
    for at, before, after in [
        (0x40068F66, '70fd', '707f'),
        (0x40068F68, '143c0001', '143c0007'),
        (0x40068F6C, '05f9ec094010', '13c0ec094029'),
        (0x40068F78, '13c0ec094028', '05f9ec094011'),
        (0x40068F86, '7202', '7280'),
        (0x40068F8C, '13c1ec09401c', '13c1ec09401d'),
        (0x40068FBA, '05b9ec094010', '4e714e714e71'),
    ]:
        replace(at, bytes.fromhex(before), bytes.fromhex(after))
    assert stub[18:20] == bytes.fromhex('203c')
    struct.pack_into('>I', stub, 20, len(payload) // 4 - 1)
    main.extend(stub + payload)
    details.update(version='XDT4', table_size=len(payload), audio_changed=True,
        audio_codec_selector=hex(selector_at), audio_old_codec_stub=hex(old_at),
        audio_changes=['Native DN receive clock-edge selection',
            'Native DN codec revision threshold and selection',
            'Native DN PF7 codec reset and retained output direction',
            'SSI start and settling delay before old-codec register writes'],
        fpga_startup_added=False, secondary_cpu_boot_added=False,
        limitations=['Original Digitone mk1 only; Digitone Keys excluded', 'Physical worst-case deadlines and shutdown power margin unmeasured'])
    return bytes(main), details
