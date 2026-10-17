"""Developer-only Unicorn check of a generated adapter's startup chain.

Requires a local Unicorn build supporting ColdFire. Stock initialization is
replaced with RTS in emulator memory to observe return through the chain.
This exercises loader copying/clearing, not boot or hardware compatibility.
"""
import argparse
import json
import struct
from pathlib import Path
from convert import syx, BASE
from mod_adapter import HOOK, STOCK_INIT


def check(modified_path, output_dir):
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.m68k_const import (UC_CPU_M68K_CFV4E, UC_M68K_REG_D0,
        UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC)
    report = json.loads((output_dir/'conversion-report.json').read_text())
    mod = syx.Syx.load(modified_path).section(3)
    normal_name = report['output_files']['update']
    main = syx.Syx.load(output_dir/normal_name).section(3)
    info = report.get('mod_loader')
    core_start, core_end = report['core_ram']['start'],report['core_ram']['end']
    source = report['core_payload_source']-BASE
    expected_core = main[source:source+core_end-core_start]
    expected_mod = mod[info['source']-BASE:info['source']-BASE+info['copy_bytes']] if info else b''
    cases = []
    for hardware_bit in (0,1):
        uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        uc.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
        uc.mem_map(0x40000000,0x08000000)
        uc.mem_map(0xFC070000,0x1000)
        uc.mem_map(0xFC040000,0x1000)
        uc.mem_write(BASE,main)
        uc.mem_write(0xFC070000,struct.pack('>H',hardware_bit))
        if info:
            uc.mem_write(info['start'],b'\xa5'*(info['end']-info['start']))
        uc.mem_write(core_start-4,b'\xa5'*(core_end-core_start+8))
        uc.mem_write(STOCK_INIT,bytes.fromhex('4e75'))
        uc.reg_write(UC_M68K_REG_SR,0x2000)
        uc.reg_write(UC_M68K_REG_A7,0x47B00000)
        seeds={UC_M68K_REG_D0:0x12345678,UC_M68K_REG_A0:0x41234560,UC_M68K_REG_A1:0x42345670}
        for reg,value in seeds.items():uc.reg_write(reg,value)
        visits=[]
        def hook(machine,address,size,user):
            if info and address == info['loader']:
                assert all(machine.reg_read(reg)==value for reg,value in seeds.items()), 'Core clobbered mod-entry registers'
                visits.append('mod')
            if address == STOCK_INIT:
                if not info:
                    assert all(machine.reg_read(reg)==value for reg,value in seeds.items()), 'Core clobbered initializer-entry registers'
                visits.append('stock')
        uc.hook_add(UC_HOOK_CODE,hook)
        uc.emu_start(HOOK,HOOK+6,count=300000)
        assert visits==(['mod','stock'] if info else ['stock']),visits
        assert uc.reg_read(UC_M68K_REG_PC)==HOOK+6,'Startup did not return to caller'
        assert uc.reg_read(UC_M68K_REG_A7)==0x47B00000,'Unbalanced startup stack'
        assert bytes(uc.mem_read(core_start,len(expected_core)))==expected_core,'Core copy corrupted'
        if info:
            assert bytes(uc.mem_read(info['start'],len(expected_mod)))==expected_mod,'Mod copy corrupted'
            assert not any(uc.mem_read(info['copy_end'],info['clear_bytes'])),'Mod BSS not cleared'
        if not info or not (core_start-4 < info['end'] and core_start > info['start']):
            assert bytes(uc.mem_read(core_start-4,4))==b'\xa5'*4,'Core copy underrun'
        assert bytes(uc.mem_read(core_end,4))==b'\xa5'*4,'Core copy overrun'
        cases.append(dict(hardware_bit=hardware_bit,passed=True,initializer_visits=visits,
                          mod_entry_registers_preserved=True,stack_balanced=True,
                          core_and_mod_copies_correct=True,mod_bss_cleared=True if info else None))
        del uc
    result=dict(scope='Startup loaders only; stock initializer stubbed with RTS; no boot or audio qualification',cases=cases)
    (output_dir/'startup-emulation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modified',type=Path)
    parser.add_argument('output_dir',type=Path)
    args=parser.parse_args()
    print(json.dumps(check(args.modified,args.output_dir),indent=2))
