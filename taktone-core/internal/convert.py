"""Conservative conversion of compatible stock or modified Digitakt 1.53/1.54 applications."""
import argparse
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace
from patch import EXPECTED, ROOT, syx, DEV, pack_section, rewrap
from patch_data import apply, sha
from firmware_profiles import PROFILES, identify_base

BASE = 0x40000400
# Reserve the entire gap containing core's copied panel/audio payload.
RESERVED = [(0x47BE0000, 0x47C00000)]
GUARD = 32


def ranges(offsets):
    result = []
    for i in offsets:
        if result and result[-1][1] == i:
            result[-1][1] = i + 1
        else:
            result.append([i, i + 1])
    return result


def merge(stock, modified, core, allocations=()):
    """Return a candidate and report; never silently overwrite a mod's edits."""
    if len(modified) != len(stock):
        raise ValueError('Application length differs from stock; appended or relocated builds require individual integration')
    if len(core) < len(stock):
        raise ValueError('Core recipe unexpectedly truncates stock')
    changed = [i for i, (a, b) in enumerate(zip(stock, modified)) if a != b]
    patches = ranges(i for i, (a, b) in enumerate(zip(stock, core)) if a != b)
    conflicts = []
    for start, end in ranges(changed):
        hits = [[BASE + a, BASE + b] for a, b in patches
                if start < b + GUARD and end > a - GUARD]
        if hits:
            conflicts.append(dict(start=BASE + start, end=BASE + end,
                                  reason='Core patch or its 32-byte context', core_ranges=hits))
    for allocation in allocations:
        def number(v):
            return int(v, 0) if isinstance(v, str) else int(v)
        start, end = number(allocation['start']), number(allocation['end'])
        if not 0x40000000 <= start < end <= 0x48000000:
            raise ValueError('RAM allocations must be nonempty main-CPU physical ranges within 0x40000000..0x48000000; normalize aliases first')
        # The added image is loaded here before startup copies its payload.
        occupied = RESERVED + [(BASE + len(stock), BASE + len(core))]
        if any(start < b and end > a for a, b in occupied):
            conflicts.append(dict(start=start, end=end, reason='Declared RAM overlaps core payload or appended image'))
    report = dict(status='conflict' if conflicts else 'static-checks-passed',
                  modified_bytes=len(changed), modified_ranges=[dict(start=BASE+a, end=BASE+b) for a,b in ranges(changed)],
                  conflicts=conflicts, context_guard_bytes=GUARD,
                  reserved_ram=[dict(start=a, end=b) for a,b in RESERVED],
                  hardware_tested=False,
                  limitations=['Same length does not prove code retained stock addresses.',
                               'Context guards do not cover every function or dependency called by core.',
                               'RAM declarations are user supplied; undeclared allocations and runtime behavior cannot be inferred.',
                               'Static checks do not establish hardware compatibility.'])
    if conflicts:
        return None, report
    image = bytearray(core)
    for i in changed:
        image[i] = modified[i]
    if any(image[i] != modified[i] for i in changed):
        raise ValueError('Modified byte preservation failed')
    report['image_sha256'] = sha(image)
    return bytes(image), report


def output_names(input_path):
    stem = 'taktone-' + input_path.stem
    return stem+'.syx', stem+'-recovery.syx'


def choose_input(folder):
    """Use a supplied mod first; otherwise offer the available stock versions."""
    stock_hashes = {p.file_sha256 for p in PROFILES}
    stock, modified = [], []
    for path in sorted(folder.glob('*.syx')):
        if path.name.startswith('taktone-'):
            continue
        if path.name in {'Digitone_and_Digitone_Keys_OS1.43.syx',
                         'TC01.syx','TC01-recovery.syx','TT1A.syx','TT1A-recovery.syx'}:
            continue
        digest = sha(path.read_bytes())
        if digest == EXPECTED['digitone']:
            continue
        (stock if digest in stock_hashes else modified).append(path)
    choices = modified or stock
    if not choices:
        raise ValueError('Put the Digitakt firmware you want to convert in firmware/, together with the required original firmware files.')
    if len(choices) == 1:
        return choices[0]
    if not sys.stdin.isatty():
        raise ValueError('More than one input in firmware/. Keep one firmware to convert alongside the required original files, or run interactively to choose: '+', '.join(p.name for p in choices))
    print('Which firmware do you want to convert?')
    for i,path in enumerate(choices,1):
        print(str(i)+'. '+path.name)
    try:
        selected = int(input('Number: '))
    except (ValueError, EOFError):
        raise ValueError('Enter the number of a listed firmware file') from None
    if not 1 <= selected <= len(choices):
        raise ValueError('Enter the number of a listed firmware file')
    return choices[selected-1]


def main():
    parser = argparse.ArgumentParser(prog='patch.py', description=__doc__)
    parser.add_argument('modified', type=Path, nargs='?', help='Stock or modified Digitakt 1.53/1.54 SysEx')
    parser.add_argument('--digitakt', type=Path, help='Exact stock base reference; otherwise detect from supported references in firmware/')
    parser.add_argument('--digitone', type=Path, default=ROOT.parent/'firmware/Digitone_and_Digitone_Keys_OS1.43.syx')
    parser.add_argument('--out', type=Path, default=ROOT.parent/'converted')
    parser.add_argument('--ram-map', type=Path, help='JSON list of main-CPU RAM ranges: [{"start":"0x...","end":"0x..."}], end exclusive')
    parser.add_argument('--check', action='store_true', help='Analyze without packing firmware')
    args = parser.parse_args()
    if not __debug__:
        parser.error('Run Python without -O; container checks require assertions')
    report = dict(status='rejected', hardware_tested=False)
    try:
        if args.modified is None:
            args.modified = choose_input(ROOT.parent/'firmware')
        print('Input: '+args.modified.name, flush=True)
        dn_raw = args.digitone.read_bytes()
        if sha(dn_raw) != EXPECTED['digitone']:
            raise ValueError('Unsupported stock Digitone reference')
        dn = syx.Syx(dn_raw)
        references = []
        if args.digitakt:
            raw = args.digitakt.read_bytes()
            profile = next((p for p in PROFILES if sha(raw)==p.file_sha256), None)
            if profile is None:
                raise ValueError('Unsupported stock Digitakt reference; expected exact 1.53 or 1.54')
            references.append((profile, syx.Syx(raw)))
        else:
            for profile in PROFILES:
                path = ROOT.parent/'firmware'/profile.filename
                if path.exists():
                    raw = path.read_bytes()
                    if sha(raw) != profile.file_sha256:
                        raise ValueError('Unsupported stock reference hash: '+str(path))
                    references.append((profile,syx.Syx(raw)))
        mod = syx.Syx.load(args.modified)
        profile, dt, detection = identify_base(mod,references)
        original, modified = dt.section(3), mod.section(3)
        dtdev = SimpleNamespace(**vars(DEV))
        dtdev.name = 'Digitakt mk1'
        # Fully validate the input, including transport and unchanged non-main sections.
        syx.verify(mod.raw, dt, modified, dtdev)
        recipe_name = 'patch-data-'+profile.version+'.json'
        recipe = json.loads((ROOT/recipe_name).read_text())
        core = apply(recipe, dt, dn)
        allocations = json.loads(args.ram_map.read_text()) if args.ram_map else []
        if len(modified) > len(original):
            from mod_adapter import adapt
            image, report = adapt(original, modified, core, allocations)
        else:
            image, report = merge(original, modified, core, allocations)
            if image is not None:
                from shutdown_patch import make_shutdown_patch
                from audit_added_code import audit_core
                source_core, details = make_shutdown_patch(original)
                if source_core != core:
                    raise ValueError('Core source differs from pinned recipe')
                report.update(adapter='same-layout', image_bytes=len(image),
                              core_ram=dict(start=int(details['table_address'],16),
                                            end=int(details['table_address'],16)+details['table_size']),
                              core_stub=BASE+len(original),
                              core_payload_source=BASE+len(original)+details['stub_size'],
                              instruction_audit=audit_core(core,original,details),
                              startup_chain=[BASE+len(original),0x40001C94])
        report.update(input_sha256=dict(stock_digitakt=dt.sha256, stock_digitone=dn.sha256, modified=mod.sha256),
                      ram_map_supplied=args.ram_map is not None, core_version=recipe['version'],
                      base_version=profile.version, base_identification=detection,
                      output_version=mod.header[0x14:0x18].decode('ascii'),
                      panel_mapping={'SYN2':'unassigned','VOICE':'SAMPLE'},
                      input_filename=args.modified.name)
        if image is None:
            raise ValueError('Conflicting modifications; see conversion-report.json')
        if not args.check:
            print('Packing candidate; this can take a few minutes.', flush=True)
            # Preserve the input boot version; filenames still identify a conversion.
            version = report['output_version']
            packed = pack_section(image)
            # Retain the historical exact-release check for unmodified 1.53.
            if profile.version=='1.53' and mod.sha256==profile.file_sha256:
                release = json.loads((ROOT/'release.json').read_text())
                legacy_recipe = json.loads((ROOT/'patch-data.json').read_text())
                legacy_image = apply(legacy_recipe,dt,dn)
                legacy_packed = pack_section(legacy_image)
                legacy = syx.write(dn, legacy_packed, DEV, version=release['release'])
                for name,data in [('TT1A-recovery.syx',legacy),('TT1A.syx',rewrap(syx.Syx(legacy),dt))]:
                    if sha(data)!=release['output_sha256'][name]:
                        raise ValueError('Stock 1.53 exact release hash differs: '+name)
                report['stock_153_release_hashes_verified'] = True
            recovery = syx.write(dn, packed, DEV, version=version)
            running = rewrap(syx.Syx(recovery), dt)
            normal_name, recovery_name = output_names(args.modified)
            outputs = {recovery_name: recovery, normal_name: running}
            report['output_files'] = {'update':normal_name,'recovery':recovery_name}
            report['container_checks'] = {
                recovery_name: syx.verify(recovery, dn, image, DEV, version=version),
                normal_name: syx.verify(running, syx.Syx(rewrap(dn, dt)), image, DEV, version=version)}
            if syx.Syx(recovery).container != syx.Syx(running).container:
                raise ValueError('Output envelopes contain different firmware')
            # Both outputs are verified before writing either.
            args.out.mkdir(parents=True, exist_ok=True)
            for name, raw in outputs.items():
                target = args.out/name
                input_paths = {args.modified.resolve(), args.digitone.resolve()}
                input_paths.update((ROOT.parent/'firmware'/p.filename).resolve() for p in PROFILES)
                if args.digitakt:
                    input_paths.add(args.digitakt.resolve())
                if target.resolve() in input_paths:
                    raise ValueError('Output would overwrite an input')
            for name, raw in outputs.items():
                (args.out/name).write_bytes(raw)
            report['output_sha256'] = {name: sha(raw) for name,raw in outputs.items()}
            report['status'] = 'candidate-built-hardware-untested'
    except (ValueError, OSError, KeyError, TypeError, AssertionError, IndexError, struct.error) as exc:
        report['error'] = str(exc)
        if report.get('status') != 'conflict':
            report['status'] = 'rejected'
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'conversion-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status']+': '+str(args.out/'conversion-report.json'))
    if 'error' in report:
        parser.exit(1, report['error']+'\n')


if __name__ == '__main__':
    main()
