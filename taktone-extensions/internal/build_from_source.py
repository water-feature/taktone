"""Build firmware locally from user-supplied stock files; never sends MIDI."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    'digitakt': '9bdd44bb6102fb25c143cfab97bc92b7a89c463f795d3112dce89771e29bcc92',
    'digitone': 'c5a54cc05b921f2e4bd814834c5365c2a5aa01d7772a9a2961fac1c3095bf9aa',
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digitakt', type=Path, default=ROOT.parent/'firmware/Digitakt_OS1.53.syx', help='Stock Digitakt OS 1.53 SysEx')
    parser.add_argument('--digitone', type=Path, default=ROOT.parent/'firmware/Digitone_and_Digitone_Keys_OS1.43.syx', help='Stock Digitone OS 1.43 SysEx')
    parser.add_argument('--out', type=Path, default=ROOT.parent/'firmware', help='Output directory (default: firmware/)')
    args = parser.parse_args()
    if not __debug__:
        parser.error('Python optimization (-O) disables required patch assertions; run without -O.')
    # Check both inputs before copying or building anything.
    for key in EXPECTED:
        path = getattr(args, key)
        if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED[key]:
            parser.error(f'{key}: unsupported firmware; expected stock hash {EXPECTED[key]}')
    firmware = ROOT.parent/'firmware'
    firmware.mkdir(exist_ok=True)
    for key, name in [('digitakt','Digitakt_OS1.53.syx'), ('digitone','Digitone_and_Digitone_Keys_OS1.43.syx')]:
        src = getattr(args,key).resolve(); dst = firmware/name
        if src != dst.resolve():
            shutil.copyfile(src,dst)
    (ROOT/'candidates').mkdir(exist_ok=True)
    from panel_patch import syx, DEV, pack_section
    dt = syx.Syx.load(firmware/'Digitakt_OS1.53.syx')
    dn = syx.Syx.load(firmware/'Digitone_and_Digitone_Keys_OS1.43.syx')
    for stock in (dt,dn):
        if syx.write(stock,stock.stored[3],DEV) != stock.raw:
            raise RuntimeError('Stock container round trip failed')
    print('Building '+VERSION+'; compilation and compression can take a few minutes.',flush=True)
    build(dt,dn)
    args.out.mkdir(parents=True,exist_ok=True)
    outputs = {}
    for path in sorted((ROOT/'candidates').glob(OUTPUT_GLOB)):
        target = args.out/path.name
        if path.resolve() != target.resolve():
            shutil.copyfile(path,target)
        outputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if len(outputs) != 2:
        raise RuntimeError('Expected both recovery and running-XDT envelopes')
    report = dict(version=VERSION, variant="no-panel-diagnostics", input_sha256=EXPECTED, output_sha256=outputs,
                  verification='Stock round trips and both generated container verifications passed',
                  hardware='NOTE LED and Sophie DSP knob indicators removed; TT2A has not been hardware-tested')
    (args.out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print('Output: '+str(args.out.resolve()))

VERSION = 'TT2A'
OUTPUT_GLOB = 'TT2A*.syx'

def build(dt,dn):
    from macro_patch import make_macro_patch
    from metadata_paths import json_path
    from panel_patch import syx, DEV, pack_section
    from retarget_transport import rewrap
    image, details = make_macro_patch(dt.section(3))
    folder = ROOT/'candidates/XDT15-build'
    folder.mkdir(exist_ok=True)
    (folder/'development-main.bin').write_bytes(image)
    raw = syx.write(dn,pack_section(image),DEV,version='XDTF')
    syx.verify(raw,dn,image,DEV,version='XDTF')
    baseline = ROOT/'candidates/XDT15-recovery.syx'
    baseline.write_bytes(raw)
    json_path(baseline.with_suffix('.json')).write_text(json.dumps(details,indent=2)+'\n')
    # Import by file path: the hyphenated source directory is deliberate.
    import importlib.util
    here = ROOT/'prototype/sophie-secondary-v4'
    sys.path.insert(0,str(here))
    spec = importlib.util.spec_from_file_location('sophie_build',here/'build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()

if __name__ == '__main__':
    main()
