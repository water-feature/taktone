"""Use the native Digitone capacitor-ready input for autosave."""
from metadata_paths import json_path
import json

from led_patch import make_led_patch
from panel_patch import TABLE, BASE, ROOT, syx, pack_section, DEV

STATUS_AT = 0x40001FA6
DT_STATUS = bytes.fromhex('1039ec0940187220c0814e75')
DN_STATUS = bytes.fromhex('1039ec09401e7208c0814e75')


def make_autosave_patch(original, *, payload_base=TABLE):
    TABLE = payload_base
    image, details = make_led_patch(original, payload_base=TABLE)
    image = bytearray(image)
    offset = STATUS_AT - BASE
    assert image[offset:offset + len(DT_STATUS)] == DT_STATUS
    image[offset:offset + len(DN_STATUS)] = DN_STATUS
    details['changes'].append(dict(address=hex(STATUS_AT),
        before=DT_STATUS.hex(), after=DN_STATUS.hex(),
        purpose='Read native Digitone supercapacitor charge status: port G bit 3'))
    details.update(version='XDT3', autosave_changed=True,
        autosave_status_pin='GPIO port G bit 3, matching stock DN 1.43',
        limitations=['Original Digitone mk1 only; Digitone Keys excluded', 'Physical worst-case deadlines and shutdown power margin unmeasured'])
    return bytes(image), details
