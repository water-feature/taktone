"""Recognize the observed 96-byte mod loader; preserve mod payload addresses."""
import struct
from patch_data import sha
from firmware_profiles import profile_for

BASE = 0x40000400
HOOK = 0x40000538
STOCK_INIT = 0x40001C94
RAM_LOW, RAM_HIGH = 0x47BE0000, 0x47C00000
# The entire observed loader is checked, including its hardware setup, final
# tail jump and padding. Only the four immediate fields below may differ.
TEMPLATE = bytes.fromhex(
    '41f94025caa043f947be0000203c00003c5922d8538066fa'
    '43f947bef164203c0000282267064299538066fa'
    '3039fc07000008000000661a103c001c13c0fc04002d428033c0fc070000'
    '700333c0fc0700004ef940001c940000000000000000')
FIELDS = (2, 8, 14, 26, 32)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError('RAM addresses must be integers or hexadecimal strings')
    return int(value, 0) if isinstance(value, str) else value


def allocations_from_json(values):
    if not isinstance(values, list):
        raise ValueError('RAM map must be a JSON list')
    result = []
    for item in values:
        start, end = number(item['start']), number(item['end'])
        if not 0x40000000 <= start < end <= 0x48000000:
            raise ValueError('RAM ranges must use main-CPU physical addresses within 0x40000000..0x48000000')
        result.append((start, end))
    return result


def recognize(stock, modified):
    if len(modified) <= len(stock):
        raise ValueError('Template adapter requires an appended mod payload')
    profile = profile_for(stock)
    at = HOOK - BASE
    expected_target = BASE + len(stock)
    if modified[at:at+6] != bytes.fromhex('4eb9') + struct.pack('>I', expected_target):
        raise ValueError('Unrecognized mod startup call or relocated loader')
    stub = modified[len(stock):len(stock)+len(TEMPLATE)]
    def normalized(data):
        data = bytearray(data)
        for i in FIELDS:
            data[i:i+4] = bytes(4)
        return bytes(data)
    if len(stub) != len(TEMPLATE) or normalized(stub) != normalized(TEMPLATE):
        raise ValueError('Unrecognized mod startup instructions; no adaptation performed')
    source, dest, count, clear, zeros = [struct.unpack_from('>I', stub, i)[0] for i in (2, 8, 14, 26, 32)]
    end = clear + zeros * 4
    if source != expected_target + len(TEMPLATE) or source + count * 4 != BASE + len(modified):
        raise ValueError('Mod copy source/size does not exactly cover the appended payload')
    if not count or not zeros or any(x % 4 for x in (source, dest, clear)):
        raise ValueError('Mod loader requires nonempty aligned copy and clear ranges')
    # Exclude native sample pool below this gap and audio ring above it.
    if not profile.mod_ram_low <= dest < clear <= end <= RAM_HIGH or clear != dest + count * 4:
        raise ValueError('Mod RAM initialization is outside the supported gap or not contiguous')
    # The tail-called stock routine must remain intact.
    pos = STOCK_INIT - BASE
    if modified[pos:pos+12] != stock[pos:pos+12]:
        raise ValueError('Mod changed the displaced stock initialization routine')
    return dict(loader=expected_target, source=source, start=dest, copy_end=clear, end=end,
                copy_bytes=count*4, clear_bytes=zeros*4, loader_bytes=len(TEMPLATE))


def choose_ram(size, occupied):
    candidate = RAM_LOW
    for start, end in sorted(occupied):
        if end <= candidate:
            continue
        if candidate + size <= start:
            break
        candidate = (end + 255) & ~255
    if candidate + size > RAM_HIGH:
        raise ValueError('No supported RAM gap for core below the native audio ring')
    return candidate


def adapt(stock, modified, recipe_core, allocations=()):
    from convert import ranges, GUARD
    from shutdown_patch import make_shutdown_patch
    from audit_added_code import audit_core, audit
    info = recognize(stock, modified)
    extra = allocations_from_json(list(allocations))
    baseline, baseline_details = make_shutdown_patch(stock)
    if baseline != recipe_core:
        raise ValueError('Core source differs from pinned recipe; cannot safely relocate')
    size = baseline_details['table_size']
    table = choose_ram(size, [(info['start'], info['end'])] + extra)
    core, details = make_shutdown_patch(stock, payload_base=table)
    patch_spans = [(int(x['address'], 16)-BASE, bytes.fromhex(x['before']), bytes.fromhex(x['after']))
                   for x in details['changes']]
    changes = ranges(i for i, (a,b) in enumerate(zip(stock, modified)) if a != b)
    conflicts = []
    for start, end in changes:
        # Only bytes within the six-byte startup call may be adapted.
        if HOOK-BASE <= start and end <= HOOK-BASE+6:
            continue
        hits = [dict(start=BASE+a, end=BASE+a+len(before)) for a,before,after in patch_spans
                if start < a+len(before)+GUARD and end > a-GUARD]
        if hits:
            conflicts.append(dict(start=BASE+start, end=BASE+end, reason='Core patch or context', core_ranges=hits))
    report = dict(status='conflict' if conflicts else 'static-checks-passed', adapter='observed-mod-loader-v1',
                  conflicts=conflicts, hardware_tested=False, mod_loader=info,
                  modified_bytes=sum(b-a for a,b in changes),
                  modified_ranges=[dict(start=BASE+a,end=BASE+b) for a,b in changes],
                  core_patches=[change for change in details['changes'] if int(change['address'],16) != HOOK],
                  appended_mod_bytes=len(modified)-len(stock),
                  core_ram=dict(start=table, end=table+size), context_guard_bytes=GUARD,
                  declared_ram=[dict(start=a,end=b) for a,b in extra],
                  limitations=['Observed startup RAM ranges and optional user declarations do not establish all runtime allocations.',
                               'Context guards do not cover every function or dependency called by core.',
                               'Preserving mod code does not prove its assumptions hold on Digitone hardware.',
                               'Static and container checks do not establish hardware compatibility.'])
    if conflicts:
        return None, report
    image = bytearray(modified)
    allowed = set(range(HOOK-BASE, HOOK-BASE+6))
    for at, before, after in patch_spans:
        if at == HOOK-BASE:
            continue
        if modified[at:at+len(before)] != before:
            raise ValueError('Mod differs at a complete core patch instruction/operand')
        image[at:at+len(after)] = after
        allowed.update(range(at,at+len(after)))
    image.extend(bytes(-len(image) % 4))
    stub_at = BASE + len(image)
    stub = bytearray(core[len(stock):len(stock)+details['stub_size']])
    # The source-built stub saves/restores D0/A0/A1. Copy core, restore them,
    # then tail-call the untouched mod loader, which tail-calls stock once.
    tail = stub.find(bytes.fromhex('4ef9') + struct.pack('>I', STOCK_INIT))
    if tail < 0 or stub[tail+6:] not in (b'', bytes.fromhex('4e71')):
        raise ValueError('Unexpected core startup tail')
    struct.pack_into('>I', stub, 8, stub_at + len(stub))
    struct.pack_into('>I', stub, tail+2, info['loader'])
    image.extend(stub + core[-size:])
    image[HOOK-BASE:HOOK-BASE+6] = bytes.fromhex('4eb9') + struct.pack('>I',stub_at)
    if any(a != b and i not in allowed for i,(a,b) in enumerate(zip(modified,image))):
        raise ValueError('Mod byte preservation failed')
    if image[len(stock):len(modified)] != modified[len(stock):]:
        raise ValueError('Appended mod payload preservation failed')
    if any(a < BASE+len(image) and b > BASE+len(modified) for a,b in extra):
        raise ValueError('Declared RAM overlaps appended core load image')
    report['instruction_audit'] = audit_core(core, stock, details)
    count, errors = audit(bytes(stub), stub_at)
    if errors:
        raise ValueError('Chained startup instruction audit failed: '+str(errors))
    report.update(core_stub=stub_at, core_payload_source=stub_at+len(stub),
                  image_sha256=sha(image), image_bytes=len(image), mod_payload_sha256=sha(modified[len(stock):]),
                  preservation='All input bytes retained except declared core patch spans and startup call; appended mod bytes identical',
                  adapted_startup=dict(address=HOOK,before=modified[HOOK-BASE:HOOK-BASE+6].hex(),after=image[HOOK-BASE:HOOK-BASE+6].hex()),
                  startup_chain=[stub_at,info['loader'],STOCK_INIT], startup_instruction_count=count)
    return bytes(image), report
