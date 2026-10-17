"""Build isolated TT2D from frozen XDT15; never send firmware to hardware.

Compile the original DigiSophie C engine for MCF54418; assemble the driver
and kernel from the adjacent source files. No synthesis runs on main.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from panel_patch import syx, BASE, DEV, pack_section
from assemble import assemble
from audit_added_code import audit
from retarget_transport import rewrap

OUT = ROOT / 'candidates/TT2D-build'
RAM = 0x43580000
STATE = 0x4b584000
S6 = 0x4b585000
S7 = 0x4b586000
ENGINE = 0x40020000
KERNEL = 0x40022000
VOICE = 0x40024000
LOCAL = 0x40023100

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    dt = syx.Syx.load(ROOT.parent / 'firmware/Digitakt_OS1.53.syx')
    dn = syx.Syx.load(ROOT.parent / 'firmware/Digitone_and_Digitone_Keys_OS1.43.syx')
    baseline_path = ROOT / 'candidates/XDT15-recovery.syx'
    baseline = syx.Syx.load(baseline_path)
    frozen = (ROOT / 'candidates/XDT15-build/development-main.bin').read_bytes()
    assert baseline.section(3) == frozen
    mod = json.loads((HERE / 'upstream/target.json').read_text())
    assert sha(dt.section(3)) == mod['section3_sha256']
    flags=['-mcpu=54418','-msoft-float','-Os','-ffreestanding','-fno-builtin',
           '-fno-common','-fno-pic','-fwrapv','-fno-jump-tables']
    subprocess.run(['m68k-elf-gcc',*flags,'-I',str(HERE/'upstream'),'-c',str(HERE/'layout.c'),
                    '-o',str(OUT/'layout.o')],check=True)
    subprocess.run(['m68k-elf-gcc',*flags,'-c',str(HERE/'upstream/sophie.c'),
                    '-o',str(OUT/'sophie.o')],check=True)
    subprocess.run(['m68k-elf-gcc',*flags,'-I',str(HERE),'-c',str(HERE/'kernel.c'),
                    '-o',str(OUT/'kernel.o')],check=True)
    subprocess.run(['m68k-elf-ld','-T',str(HERE/'engine.ld'),'-e','render_c',
                    '-o',str(OUT/'engine.elf'),str(OUT/'sophie.o'),str(OUT/'kernel.o')],check=True)
    subprocess.run(['m68k-elf-objcopy','-O','binary',str(OUT/'engine.elf'),str(OUT/'engine.bin')],check=True)
    engine=(OUT/'engine.bin').read_bytes()
    symbols={row.split()[2]:int(row.split()[0],16) for row in
             subprocess.check_output(['m68k-elf-nm',str(OUT/'engine.elf')],text=True).splitlines()
             if len(row.split())==3}
    sc = dict(INIT_C=symbols['init_c'],RENDER_C=symbols['render_c'])
    kernel, sl = assemble((HERE / 'secondary.s').read_text(), KERNEL, sc,
                          'TT2D-secondary-asm')
    assert KERNEL + len(kernel) < VOICE
    secondary = bytearray(dn.section(7))
    secondary.extend(bytes(ENGINE - BASE - len(secondary)))
    secondary.extend(engine)
    secondary.extend(bytes(KERNEL - BASE - len(secondary)))
    secondary.extend(kernel)
    def patch(buf, at, expected, new):
        off = at - BASE
        assert buf[off:off+len(expected)] == expected, hex(at)
        assert len(expected) == len(new)
        buf[off:off+len(new)] = new
    patch(secondary, 0x40000b7a, bytes.fromhex('4eb940000bfc'),
          b'\x4e\xb9' + struct.pack('>I', sl['secondary_init']))
    patch(secondary, 0x40000b80, bytes.fromhex('4eb940003890'), b'\x4e\x71' * 3)
    original_irq = bytes(secondary[0x400008fa-BASE:0x40000900-BASE])
    patch(secondary, 0x400008fa, original_irq,
          b'\x4e\xf9' + struct.pack('>I', sl['secondary_irq']))
    image = bytearray(frozen)
    old_frame = struct.unpack_from('>I', image, 0x400e6008-BASE)[0]
    # Integrate only core's machine subsystem, preserving XDT15's own UI/render hooks.
    core=json.loads((HERE/'upstream/core-mod.json').read_text())
    defs='\n'.join(f'.equ {k},{v}' for k,v in core['defsym'].items())+'\n'
    (OUT/'machines.s').write_text(defs+(HERE/'upstream/machines.s').read_text()+
        '\n.section .run,"ax"\n.global core_machines\ncore_machines: .long ds_machine,0\n')
    objects=[]
    for name,path in [('machines',OUT/'machines.s'),('ui',HERE/'ui.s')]:
        obj=OUT/(name+'.o');objects.append(str(obj))
        subprocess.run(['m68k-elf-as','-mcpu=54418','-I',str(HERE/'upstream'),'-o',str(obj),str(path)],check=True)
    for name in ['audio','ui']:
        obj=OUT/(name+'-c.o');objects.append(str(obj))
        subprocess.run(['m68k-elf-gcc',*flags,'-I',str(HERE),'-I',str(HERE/'upstream'),'-c',str(HERE/(name+'.c')),'-o',str(obj)],check=True)
    ld=OUT/'main-extra.ld'
    ld.write_text('SECTIONS { . = 0x43581000; .text : { *(.run) *(.text*) EXTRA_TEXT_END = .; *(.rodata*) } '
                  '.bss 0x4b584100 (NOLOAD) : { *(.bss*) *(COMMON) } '
                  '/DISCARD/ : { *(.comment) *(.eh_frame*) } }')
    subprocess.run(['m68k-elf-ld','-T',str(ld),'-e','audio_c','-o',str(OUT/'extra.elf'),*objects],check=True)
    subprocess.run(['m68k-elf-objcopy','-O','binary','-j','.text',str(OUT/'extra.elf'),str(OUT/'extra.bin')],check=True)
    extra=(OUT/'extra.bin').read_bytes()
    assert len(extra)<=0x3000
    ex={row.split()[2]:int(row.split()[0],16) for row in subprocess.check_output(
        ['m68k-elf-nm',str(OUT/'extra.elf')],text=True).splitlines() if len(row.split())==3}
    assert max(v for k,v in ex.items() if 0x4b584100<=v<0x4b585000)<0x4b585000
    mc = dict(STATUS=STATE, BOOT_TICKS=STATE+4, SEQ=STATE+8,
              PENDING_TRIG=STATE+12, COMPLETED=STATE+16, MISSES=STATE+20,
              MISSES_RUN=STATE+24, PA4=STATE+28, S6=S6, S7=S7,
              OLD_FRAME=old_frame,AUDIO_C=ex['audio_c'],MACHINE_TICK=ex['core_mtick'],
              FAIL_STAGE=STATE+32,HELLO=STATE+36,ACK=STATE+40)
    driver, ml = assemble((HERE / 'main.s').read_text(), RAM, mc,
                          'TT2D-main-asm')
    assert len(driver) < 0x1000
    # Entire new region is initialized through the uncached DDR alias before
    # the original XDT15 startup stub runs. Its scene clear ends at RAM.
    payload = bytearray(0x6000 + 0x43804)
    payload[:len(driver)] = driver
    payload[0x1000:0x1000+len(extra)]=extra
    serial6 = bytearray(b'\xff' * 8 + dn.section(6) + bytes(4))
    serial6[9] = 0x0f
    assert len(serial6) == 1504
    payload[0x5000:0x5000+len(serial6)] = serial6
    assert len(secondary) < 0x43800
    payload[0x6000] = 0xaa
    payload[0x6001:0x6001+len(secondary)] = secondary
    assert RAM + len(payload) < 0x4399d6ac
    old_startup = struct.unpack_from('>I', image, 0x4000053a-BASE)[0]
    startup_at = BASE + len(image)
    # 42-byte copy wrapper: uses no potentially forbidden EA combination.
    startup = bytearray.fromhex('2f002f082f0941f9')
    startup.extend(struct.pack('>I', startup_at+42))
    startup.extend(bytes.fromhex('43f9')+struct.pack('>I',RAM+0x08000000))
    startup.extend(bytes.fromhex('203c')+struct.pack('>I',len(payload)//4))
    startup.extend(bytes.fromhex('22d8538066fa225f205f201f4ef9'))
    startup.extend(struct.pack('>I',old_startup))
    assert len(startup)==42
    image.extend(startup+payload)
    patch(image,0x40000538,b'\x4e\xb9'+struct.pack('>I',old_startup),
          b'\x4e\xb9'+struct.pack('>I',startup_at))
    patch(image,0x400e6006,b'\x4e\xb9'+struct.pack('>I',old_frame),
          b'\x4e\xb9'+struct.pack('>I',ml['main_poll']))
    patch(image,0x40077fba,bytes.fromhex('49f94199e444'),
          b'\x4e\xb9'+struct.pack('>I',ml['main_audio']))
    # Apply stock-checked machine hooks, then Sophie-specific presentation hooks.
    sites=[]
    for site in core['sites']:
        if site.get('target','').startswith('core_m') or site.get('target')=='core_samp_tab' or (site['op']=='bytes'):
            sites.append(site)
    for site in json.loads((HERE/'upstream/mod.json').read_text())['sites']:
        if site['addr']!='0x40077fba': sites.append(site)
    sites += [dict(addr='0x4003b314',stock='0c8000000087',op='jsr',target='ds_samp_d0'),
              dict(addr='0x4003b5b2',stock='0c8200000087',op='jsr',target='ds_samp_d2')]
    sites += [dict(addr='0x40022138',stock='4bf940078f0c',op='keep2',target='ds_init_range')]
    for site in sites:
        at=int(site['addr'],16);expected=bytes.fromhex(site['stock']);op=site['op']
        if op=='bytes': new=bytes.fromhex(site['new'])
        else:
            dest=ex[site['target']]
            if op=='keep2': new=expected[:2]+struct.pack('>I',dest)
            else: new=(b'\x4e\xf9' if op=='jmp' else b'\x4e\xb9')+struct.pack('>I',dest)
            new+=b'\x4e\x71'*((len(expected)-len(new))//2)
        patch(image,at,expected,new)
    patch(image,0x40077f8e,bytes.fromhex('4eb940075184'),b'\x4e\xb9'+struct.pack('>I',ml['main_source']))
    from metadata_paths import json_path
    baseline_meta=json.loads(json_path(baseline_path.with_suffix('.json')).read_text())
    ms=baseline_meta['macro_symbols']
    payload_at=len(frozen)-baseline_meta['table_size'];payload_ram=int(baseline_meta['table_address'],16)
    begin=payload_at+int(ms['macro_set'],16)-payload_ram
    end=payload_at+int(ms['macro_rebuild_overlay'],16)-payload_ram
    needle=bytes.fromhex('4eb940078f0c')
    assert frozen[begin:end].count(needle)==1
    scene_range_at=BASE+frozen.index(needle,begin,end)
    patch(image,scene_range_at,needle,b'\x4e\xb9'+struct.pack('>I',ex['ds_scene_range']))
    hooks=[(scene_range_at,6),(0x40000538,6),(0x400e6006,6),(0x40077fba,6),(0x40077f8e,6)]
    hooks += [(int(site['addr'],16),len(bytes.fromhex(site['stock'])))for site in sites]
    allowed={i for at,n in hooks for i in range(at-BASE,at-BASE+n)}
    assert all(a==z or i in allowed for i,(a,z) in enumerate(zip(image,frozen)))
    audits=[]
    extra_spans=[('core_machine','core_samp_tab'),('core_mtick','core_machines'),('ds_layout','ui_code_end'),('ds_empty_val_text','ui_status_end'),('u7','EXTRA_TEXT_END')]
    for at,blob in [(RAM,driver),(KERNEL,kernel),(startup_at,startup),
                    (ENGINE,engine[:symbols['ENGINE_TEXT_END']-ENGINE])]:
        count,errors=audit(blob,at)
        audits.append(dict(address=hex(at),bytes=len(blob),instructions=count,errors=errors))
    for start,end in extra_spans:
        at=ex[start];blob=extra[at-(RAM+0x1000):ex[end]-(RAM+0x1000)]
        count,errors=audit(blob,at)
        audits.append(dict(address=hex(at),bytes=len(blob),instructions=count,errors=errors))
    assert not any(a['errors'] for a in audits),audits
    for name,data in [('main.bin',image),('secondary.bin',secondary),
                      ('payload.bin',payload),('engine.bin',engine)]:
        (OUT/name).write_bytes(data)
    report=dict(version='TT2D',hardware_tested=False,baseline_sha256=baseline.sha256,
                main_sha256=sha(image),secondary_sha256=sha(secondary),
                main_symbols=ml,extra_symbols=ex,changed_spans=hooks,machine_sites=sites,secondary_symbols=sl,main_constants=mc,
                secondary_constants=sc,region=dict(start=hex(RAM),end=hex(RAM+len(payload))),
                instruction_audits=audits,
                engine_source_sha256=sha((HERE/'upstream/sophie.c').read_bytes()),
                compiler=subprocess.check_output(['m68k-elf-gcc','--version'],text=True).splitlines()[0],
                compiler_flags=flags)
    # Non-main container sections, including 6 and 7, remain byte-exact DN.
    # The driver serial-uploads its embedded customized section 7 instead.
    raw=syx.write(dn,pack_section(bytes(image)),DEV,version='TT2D')
    report['container']=syx.verify(raw,dn,bytes(image),DEV,version='TT2D')
    from metadata_paths import json_path
    baseline_info=json.loads(json_path(baseline_path.with_suffix('.json')).read_text())
    for suffix,data in [('recovery',raw),('from-XDT',rewrap(syx.Syx(raw),dt))]:
        path=ROOT/('candidates/TT2D'+('-recovery' if suffix=='recovery' else '')+'.syx')
        # Reproducible rebuilds may replace TT2D only. Never touch XDT15.
        path.write_bytes(data)
        reference=dn if suffix=='recovery' else syx.Syx(rewrap(dn,dt))
        facts=syx.verify(data,reference,bytes(image),DEV,version='TT2D')
        info=dict(xdt15_baseline=baseline_info)
        for key in ('macro_symbols','inverse','forward','scene_controls',
                    'scene_capture','memory_reservation','macro_format_version'):
            info[key]=baseline_info[key]
        info.update(facts,version='TT2D',hardware_tested=False,
                    status='local rebuild; see README for hardware-tested release status',
                    secondary_cpu_boot_added=True,fpga_startup_added=True,sophie_tracks=list(range(1,9)),
                    main_sha256=sha(image),secondary_sha256=sha(secondary),
                    xsp4_build_report='candidates/TT2D-build/build.json',
                    limitations=['Physical worst-case deadlines and CPU utilization unmeasured',
                                 'One-block source latency',
                                 'Scene extensions absent from stock Transfer exports'])
        json_path(path.with_suffix('.json')).write_text(json.dumps(info,indent=2)+'\n')
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='built; container and instruction checks passed',main_bytes=len(image),
                         secondary_bytes=len(secondary),region=report['region']),indent=2))

if __name__=='__main__':
    main()
