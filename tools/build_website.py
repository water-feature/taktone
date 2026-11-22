"""Stage the browser patcher, current Python sources and pinned Pyodide runtime.

No firmware, generated candidates, emulator state or user data enter the site.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'taktone-core/internal'
RUNTIME_VERSION = '0.27.7'
RUNTIME_FILES = ('pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm',
                 'python_stdlib.zip', 'pyodide-lock.json')


def build(out, cache):
    out = out.resolve()
    # Never allow a staging directory to replace tracked source.
    if out == ROOT or ROOT.is_relative_to(out) or out.is_relative_to(ROOT / 'website') or out.is_relative_to(ROOT / 'taktone-core') or out.is_relative_to(ROOT / 'taktone-extended'):
        raise ValueError('Use a separate output directory, such as dist/')
    out.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / 'website').iterdir():
        if path.suffix in ('.html', '.css', '.js') or path.name in ('.nojekyll', 'PX-RE-LICENSE', 'PX-RE-NOTICE'):
            shutil.copyfile(path, out / path.name)
    paths = sorted(p for p in SOURCE.rglob('*') if p.is_file() and
                   ('__pycache__' not in p.parts) and
                   (p.suffix == '.py' and not p.name.startswith(('test_', 'verify_')) or
                    p.name in ('patch-data.json', 'patch-data-1.53.json', 'patch-data-1.54.json',
                               'release.json', 'panel-dn.json', 'LICENSE', 'NOTICE')))
    # ZIP timestamps/permissions are fixed so identical sources produce identical archives.
    with zipfile.ZipFile(out / 'core.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            entry = zipfile.ZipInfo('core/internal/' + path.relative_to(SOURCE).as_posix(), (2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, path.read_bytes())
        entry = zipfile.ZipInfo('core/internal/browser_bridge.py', (2020, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o644 << 16
        archive.writestr(entry, (ROOT / 'website/browser_bridge.py').read_bytes())
    cache.mkdir(parents=True, exist_ok=True)
    vendor = out / 'runtime'
    vendor.mkdir(exist_ok=True)
    pins = json.loads((ROOT / 'website/runtime-lock.json').read_text())
    if pins['version'] != RUNTIME_VERSION or set(pins['files']) != set(RUNTIME_FILES):
        raise ValueError('Runtime lock and builder version differ')
    for name in RUNTIME_FILES:
        path = cache / name
        if not path.exists():
            data = urllib.request.urlopen(f'https://cdn.jsdelivr.net/pyodide/v{RUNTIME_VERSION}/full/{name}', timeout=120).read()
            if hashlib.sha256(data).hexdigest() != pins['files'][name]:
                raise ValueError('Runtime download hash differs: ' + name)
            path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest() != pins['files'][name]:
            raise ValueError('Cached runtime hash differs: ' + name)
        shutil.copyfile(path, vendor / name)
    # Preserve Pyodide and CPython license notices in every deployed copy.
    shutil.copyfile(ROOT / 'website/PYODIDE-LICENSE', vendor / 'LICENSE')
    shutil.copyfile(ROOT / 'website/PYTHON-LICENSE', vendor / 'LICENSE-PYTHON')
    (out / 'source-manifest.json').write_text(json.dumps({
        'core_sha256': hashlib.sha256((out / 'core.zip').read_bytes()).hexdigest(),
        'sources': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [*paths, ROOT / 'website/browser_bridge.py']},
        'runtime': pins,
    }, indent=2) + '\n')
    print('Built browser patcher: ' + str(out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/pyodide-0.27.7')
    args = parser.parse_args()
    build(args.out, args.cache)
