"""Compose the instruction-corrected core audio adaptation."""
from metadata_paths import json_path
import json

from audio_patch import make_audio_patch
from panel_patch import TABLE, ROOT, syx, pack_section, DEV


def make_recovery_patch(original, *, payload_base=TABLE):
    TABLE = payload_base
    image, details = make_audio_patch(original, payload_base=TABLE)
    details.update(version='XDT5', hardware_fault_fixed='LED initialization immediate-to-absolute MOVE',
        fault_address_in_xdt4='0x47be0350',
        replacement='MOVEQ #1,D0; MOVE.B D0,absolute flag',
        limitations=['Original Digitone mk1 only; Digitone Keys excluded', 'Physical worst-case deadlines and shutdown power margin unmeasured'])
    return image, details
