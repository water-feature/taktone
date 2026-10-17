"""Two-pass label assembly using the local Ghidra ColdFire assembler.

Ghidra is used offline and does not patch its loaded firmware. Every emitted
instruction is subsequently subject to the separate ColdFire ISA audit.
"""
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
def headless():
    configured = os.environ.get('GHIDRA_HEADLESS')
    if configured:
        return configured
    home = os.environ.get('GHIDRA_HOME')
    if home:
        candidate = Path(home) / 'support' / ('analyzeHeadless.bat' if os.name == 'nt' else 'analyzeHeadless')
        if candidate.is_file():
            return str(candidate)
    import shutil
    found = shutil.which('analyzeHeadless')
    if found:
        return found
    raise RuntimeError('Set GHIDRA_HOME to the Ghidra installation or GHIDRA_HEADLESS to analyzeHeadless.')


def project():
    folder = ROOT / 'candidates' / 'assembler-project'
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / 'Assembler.gpr').exists():
        seed = folder / 'seed.bin'
        seed.write_bytes(bytes.fromhex('4e714e75'))
        command = [headless(), str(folder), 'Assembler', '-import', str(seed),
                   '-loader', 'BinaryLoader', '-processor', '68000:BE:32:Coldfire', '-noanalysis']
        with (folder / 'import.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError((folder / 'import.log').read_text()[-6000:])
    return folder


def assemble(source, base, constants, name='macro-runtime'):
    rows = []
    for line in source.splitlines():
        line = line.split(';', 1)[0].strip()
        if line:
            rows.append(('label', line[:-1]) if line.endswith(':') else ('ins', line))
    labels = {text for kind, text in rows if kind == 'label'}
    assert not labels.intersection(constants)
    folder = ROOT / 'candidates' / name
    folder.mkdir(exist_ok=True)
    result = None
    symbols = {}
    for stage in (1, 2):
        requests = []
        expected = []
        offset = 0
        instruction = 0
        def substitute(match):
            key = match.group(1)
            if key in constants:
                return hex(constants[key])
            assert key in labels, key
            return hex(symbols[key] if stage == 2 else base + 0x1000)
        for kind, text in rows:
            if kind == 'label':
                if stage == 2:
                    assert symbols[text] == base + offset
                continue
            at = base + (offset if stage == 2 else instruction * 16)
            asm = re.sub(r'@([A-Za-z_][A-Za-z_0-9]*)', substitute, text)
            asm = re.sub(r'^(jsr|jmp) (0x[0-9a-fA-F]+)$', r'\1 \2.l', asm)
            if re.match(r'^(move|cmp|tst|clr|and|or|eor|not)\.(b|w) ', asm):
                suffix = asm.split()[0][-1]
                asm = re.sub(r'(?<![A-Za-z0-9])D([0-7])(?=,|$)', lambda m: 'D'+m[1]+suffix, asm)
            requests.append(f'{at:x}\t{asm}')
            if stage == 2:
                expected.append(result[instruction])
                offset += len(result[instruction])
            instruction += 1
        path = folder / f'pass{stage}.tsv'
        out = folder / f'pass{stage}-result.tsv'
        path.write_text('\n'.join(requests) + '\n')
        command = [headless(), str(project()), 'Assembler',
            '-process', 'seed.bin', '-noanalysis', '-scriptPath', str(ROOT),
            '-postScript', 'TaktoneAssembleBatch.java', str(path), str(out)]
        with (folder / f'pass{stage}.log').open('w') as log:
            run = subprocess.run(command, env=os.environ.copy(),
                stdout=log, stderr=subprocess.STDOUT)
        assert run.returncode == 0 and out.exists(), (folder / f'pass{stage}.log').read_text()[-6000:]
        lines = out.read_text().splitlines()
        assert len(lines) == len(requests)
        current = [bytes.fromhex(line.split('\t')[1]) for line in lines]
        if stage == 2:
            assert [len(x) for x in current] == [len(x) for x in expected], 'unstable assembly lengths'
        result = current
        offset = 0
        instruction = 0
        for kind, text in rows:
            if kind == 'label':
                symbols[text] = base + offset
            else:
                offset += len(result[instruction])
                instruction += 1
    blob = b''.join(result)
    (folder / 'runtime.bin').write_bytes(blob)
    return blob, symbols


if __name__ == '__main__':
    blob, labels = assemble('start:\n moveq 1,D0\n bne.w @start\n rts', 0x47BF0000, {}, 'assembler-test')
    assert blob == bytes.fromhex('70016600fffc4e75')
    print('PASS: two-pass ColdFire assembly', labels)
