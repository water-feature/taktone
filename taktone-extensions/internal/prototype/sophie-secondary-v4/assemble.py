"""Assemble the project's existing Ghidra-style source with GNU binutils."""
import re
import subprocess
from pathlib import Path

def assemble(source, base, constants, name):
    out = Path(__file__).resolve().parents[2] / 'candidates' / name
    out.mkdir(exist_ok=True)
    lines = ['.text'] + [f'.equ {k},0x{v:x}' for k,v in constants.items()]
    for line in source.splitlines():
        line = line.split(';',1)[0].strip().replace('@','')
        if not line:
            continue
        if line.endswith(':'):
            lines += ['.global '+line[:-1],line]
            continue
        line = re.sub(r'\{([^}]+)\}',lambda m:'/'.join(m[1].split()),line)
        line = re.sub(r'\(([^,()]+)\)\.([lw])',r'\1',line)
        line = re.sub(r'\(([^,()]+),(A[0-6]|SP),(D[0-7])\*1\)',r'\1(%\2,%\3.l)',line)
        line = re.sub(r'\(([^,()]+),(A[0-6]|SP)\)',r'\1(%\2)',line)
        line = re.sub(r'(?<![%\w])\b(D[0-7]|A[0-6]|SP)\b',r'%\1',line)
        if line.startswith('moveq '):
            line=line.replace('moveq ','moveq #',1)
        lines.append(line)
    asm=out/'source.s'
    asm.write_text('\n'.join(lines)+'\n')
    subprocess.run(['m68k-elf-as','-mcpu=54418','-o',str(out/'code.o'),str(asm)],check=True)
    subprocess.run(['m68k-elf-ld','-Ttext',hex(base),'-e',hex(base),'-o',str(out/'code.elf'),str(out/'code.o')],check=True)
    subprocess.run(['m68k-elf-objcopy','-O','binary','-j','.text',str(out/'code.elf'),str(out/'runtime.bin')],check=True)
    symbols={}
    for row in subprocess.check_output(['m68k-elf-nm',str(out/'code.elf')],text=True).splitlines():
        fields=row.split()
        if len(fields)==3 and fields[1].lower()=='t':
            symbols[fields[2]]=int(fields[0],16)
    return (out/'runtime.bin').read_bytes(),symbols
