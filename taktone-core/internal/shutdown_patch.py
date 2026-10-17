"""Aligned longword shutdown copies without a panel diagnostic indicator."""
from recovery_patch import make_recovery_patch
from panel_patch import BASE, TABLE

COPY_AT = 0x4008D5AE
COPY_BEFORE = bytes.fromhex('45f008001392080052800c800000800066ee')
COPY_AFTER = bytes.fromhex('203c0000200022d8538066fa4e714e714e71')


def make_shutdown_patch(original, *, payload_base=TABLE):
    TABLE = payload_base
    image, details = make_recovery_patch(original, payload_base=TABLE)
    main = bytearray(image[:len(original)])
    stub = bytearray(image[len(original):len(original) + details['stub_size']])
    payload = bytearray(image[-details['table_size']:])
    at = COPY_AT - BASE
    assert main[at:at + len(COPY_BEFORE)] == COPY_BEFORE
    assert len(COPY_BEFORE) == len(COPY_AFTER)
    main[at:at + len(COPY_AFTER)] = COPY_AFTER
    details['changes'].append(dict(address=hex(COPY_AT), before=COPY_BEFORE.hex(),
        after=COPY_AFTER.hex(), purpose='Copy 32 KiB shutdown buffer as aligned longwords'))
    main.extend(stub + payload)
    details.update(version='TT1A', table_size=len(payload), save_warning=False,
        shutdown_copy='8192 longwords instead of 32768 individual bytes per chunk',
        limitations=['Original Digitone mk1 only; Digitone Keys excluded',
                     'Physical shutdown power margin unmeasured'])
    return bytes(main), details
