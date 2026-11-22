"""Browser entry point: call the unchanged core CLI inside a disposable worker."""
import contextlib
import io
import json
from pathlib import Path
import sys


def _browser_build(input_name, has_reference=False, has_ram_map=False):
    import convert
    from patch_data import sha
    # Input name is only used as a filename, never Python or shell code.
    safe = ''.join(c for c in input_name if c.isascii() and (c.isalnum() or c in '._-'))
    safe = safe[:160]
    if not safe.lower().endswith('.syx'):
        safe = 'firmware.syx'
    source = Path('/work/input') / safe
    Path('/work/input.bin').rename(source)
    reference = '/work/reference.syx' if has_reference else str(source)
    sys.argv = ['patch.py', str(source), '--digitakt', reference,
                '--digitone', '/work/digitone.syx', '--out', '/work/output']
    if has_ram_map:
        sys.argv += ['--ram-map', '/work/ram.json']
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            convert.main()
        except SystemExit as error:
            if error.code:
                report_path = Path('/work/output/conversion-report.json')
                message = (json.loads(report_path.read_text()).get('error')
                           if report_path.exists() else log.getvalue().strip())
                raise ValueError(message or 'Firmware compatibility check failed') from None
    folder = Path('/work/output')
    report = json.loads((folder / 'conversion-report.json').read_text())
    if report['status'] == 'rejected':
        raise ValueError(report.get('error', 'Firmware rejected'))
    files = []
    for path in sorted(folder.glob('*.syx')):
        files.append({'name': path.name, 'path': str(path), 'bytes': path.stat().st_size,
                      'sha256': sha(path.read_bytes())})
    if len(files) != 2:
        raise ValueError('Expected both verified receiver envelopes')
    return json.dumps({'files': files, 'report': report})


def browser_build(input_name, has_reference=False, has_ram_map=False):
    try:
        return _browser_build(input_name, has_reference, has_ram_map)
    except Exception as error:
        return json.dumps({'error': str(error) or 'Firmware validation failed'})
