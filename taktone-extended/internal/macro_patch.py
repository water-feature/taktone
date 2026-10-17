"""XDT15 scene integration; building does not transmit firmware."""
from metadata_paths import json_path
import json
import hashlib
import struct
from panel_patch import ROOT, BASE, syx
PAYLOAD = 0x431A0000
from shutdown_patch import make_shutdown_patch
import macro_runtime as rt


def make_macro_patch(original, reassemble=True):
    image, details = make_shutdown_patch(original, payload_base=PAYLOAD)
    from audit_added_code import audit_core
    details['core_instruction_audit'] = audit_core(image,original,details)
    main = bytearray(image[:len(original)])
    stub = bytearray(image[len(original):len(original)+details['stub_size']])
    payload = bytearray(image[-details['table_size']:])
    if reassemble:
        code, labels, state = rt.build(0x4000268E)
    else:
        folder=ROOT/'candidates/macro-runtime'
        code=(folder/'runtime.bin').read_bytes()
        report=json.loads((json_path(folder/'audit.json')).read_text())
        assert report.get('input_sha256'),'Reassemble: cached runtime lacks source hashes'
        for path,digest in report['input_sha256'].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest, 'Reassemble changed source: '+path
        labels={k:int(v,16) for k,v in report['symbols'].items()}
        state=bytearray(0x200)
        for name in ('HELD','PATTERN','PROJECT_ID','PREVIOUS_ID'):
            struct.pack_into('>i',state,rt.CONSTANTS[name]-rt.STATE,-1)
        state[0x100:0x104]=b'\xff'*4
        state[0x104:0x110]=bytes.fromhex('b02e00b12e00b22e00b32e00')
        struct.pack_into('>I',state,rt.CONSTANTS['AUDIO_DIRTY']-rt.STATE,1)
        struct.pack_into('>I',state,rt.CONSTANTS['RAM_READY']-rt.STATE,1)
    def replace(at, before, after, purpose):
        at0=at-BASE
        assert main[at0:at0+len(before)]==before,hex(at)
        assert len(before)==len(after)
        main[at0:at0+len(after)]=after
        details['changes'].append(dict(address=hex(at),before=before.hex(),after=after.hex(),purpose=purpose))
    for at, stock, name in [(0x4000B770,0x400084FE,'macro_key'),
        (0x4000B7BA,0x40008550,'macro_encoder'),(0x4000A770,0x400CA34C,'macro_tick'),
        (0x4000A7D6,0x400CA382,'macro_draw'),(0x40077E9A,0x40074B9E,'macro_render'),
        (0x400E6006,0x4000268E,'macro_frame')]:
        replace(at,b'\x4e\xb9'+struct.pack('>I',stock),b'\x4e\xb9'+struct.pack('>I',labels[name]),name)
    replace(0x4000FEF6,bytes.fromhex('4fefffd448d70cfc'),
        b'\x4e\xf9'+struct.pack('>I',labels['macro_set'])+b'\x4e\x71','Capture macro edits before native setter')
    for at,stock,name in [(0x4017EB80,0x4000FA80,'macro_get_sound'),
        (0x4017EC00,0x4000FD52,'macro_get_fx')]:
        replace(at,struct.pack('>I',stock),struct.pack('>I',labels[name]),name)
    for at,before,name in [(0x40092480,'4fefffe048d7040c','macro_project_load'),
        (0x4001692A,'4fefffcc48d77c1c','macro_project_save'),
        (0x4008DA22,'7201203940202448','macro_shutdown'),
        (0x400849A0,'4fefffe448d70c7c','macro_pattern_clear'),
        (0x400165AC,'4fefffec48d70c1c','macro_pattern_save'),
        (0x4001669A,'4fefffe848d70c3c','macro_kit_save'),
        (0x400162A0,'4fefffe848d70c1c','macro_pattern_reload')]:
        replace(at,bytes.fromhex(before),b'\x4e\xf9'+struct.pack('>I',labels[name])+b'\x4e\x71',name)
    for at,before,name in [(0x40033076,'4e56ffb048d73cfc','macro_grid_key'),
        (0x4003B272,'4e56ffcc48d71cfc','macro_source_key'),
        (0x40031802,'4fefffb848d77cfc','macro_grid'),
        (0x4003171c,'4fefffd848d70c04','macro_display')]:
        replace(at,bytes.fromhex(before),b'\x4e\xf9'+struct.pack('>I',labels[name])+b'\x4e\x71',name)
    needle=struct.pack('>I',0x400E88C0)
    for offset in range(0x40014000-BASE,0x4001B000-BASE):
        if main[offset:offset+4]==needle:
            assert main[offset-2:offset] in [bytes.fromhex(x)for x in ('4eb9','49f9','47f9','4bf9')]
            replace(BASE+offset,needle,struct.pack('>I',labels['macro_pattern_memcpy']),'Carry macro data through project pattern clipboard copies')
    for wire,key in zip((38,39,54,55),range(49,53)):
        assert struct.unpack_from('>I',payload,wire*4)[0]==0
        struct.pack_into('>I',payload,wire*4,key)
        details['forward'][wire]=key
    # The original 49-entry reverse map ends immediately before LED data.
    # Synthetic scene IDs need valid reverse entries for native key-state,
    # suppression and consumption APIs, even when our UI hook consumes them.
    inverse = details['inverse'] + [38,39,54,55]
    inverse_at = rt.STATE + len(state)
    for change in list(details['changes']):
        if change.get('before') == struct.pack('>I',0x4018E7D8).hex():
            at = int(change['address'],16)
            replace(at,struct.pack('>I',PAYLOAD+56*4),
                struct.pack('>I',inverse_at),'Complete reverse map for scene buttons')
    details.update(inverse=inverse,scene_inverse_table=hex(inverse_at))
    payload.extend(bytes(rt.STATE+len(state)-PAYLOAD-len(payload)))
    payload[rt.CODE-PAYLOAD:rt.CODE-PAYLOAD+len(code)]=code
    payload[rt.STATE-PAYLOAD:rt.STATE-PAYLOAD+len(state)]=state
    payload.extend(struct.pack('>'+str(len(inverse))+'I',*inverse))
    struct.pack_into('>I',stub,20,len(payload)//4-1)
    tail=stub.index(bytes.fromhex('4ef940001c94'))
    struct.pack_into('>I',stub,tail+2,labels['macro_startup_clear'])
    # Reserve the upper half of the native buddy heap before its first use.
    replace(0x4020BB24,struct.pack('>I',20),struct.pack('>I',19),'Buddy maximum order for 8 MiB')
    replace(0x4020BB28,struct.pack('>I',0x100000),struct.pack('>I',0x80000),'Buddy capacity in 16-byte units')
    replace(0x400004B2,bytes.fromhex('4feffff048d700f0'),b'\x4e\xf9'+struct.pack('>I',labels['macro_bss_clear'])+b'\x4e\x71','BSS clear excludes reserved heap')
    details.update(memory_reservation=dict(start='0x4319d6b0',end_exclusive='0x4399d6b0',bytes=8<<20,native_heap_bytes=8<<20,method='Reduce native buddy heap order/capacity; retain free-list metadata outside reservation; split BSS clear'),
        version='XDT15',table_size=len(payload),macro_code=hex(rt.CODE),
        macro_code_size=len(code),macro_symbols={k:hex(v)for k,v in labels.items()},
        macro_table=hex(rt.TABLE),macro_table_size=0x80000,
        macro_persistence=True,status='locally rebuilt scenes layer',hardware_tested=False,
        scene_controls={'copy':'hold scene + REC','paste':'hold scene + STOP','clear':'hold scene + PLAY'},
        scene_capture='Audio-track sound providers only; non-plockable FX/master providers rejected',
        macro_format_version=4,macro_sparse_storage=True,
        macro_zero_ram_start=hex(rt.TABLE),macro_zero_ram_size=0x330000,
        macro_storage=dict(header_chunk=111,first_data_chunk=112,max_data_chunks=16,
            bytes_per_pattern=4096,normal_projects_base_sector=0x80000,
            temporary_project_base_sector=0x7e000,autosave_sectors=[0x7a000,0x7c000]),
        limitations=['Original Digitone mk1 only; Digitone Keys excluded', 'Physical worst-case deadlines and shutdown power margin unmeasured', 'Scene extensions are absent from stock Transfer exports', 'Scene interpolation and MIDI-track targets are unimplemented'])
    return bytes(main+stub+payload),details


def package(image,details):
    from panel_patch import pack_section,DEV
    from retarget_transport import rewrap
    dt=syx.Syx.load(ROOT.parent/'firmware/Digitakt_OS1.53.syx')
    dn=syx.Syx.load(ROOT.parent/'firmware/Digitone_and_Digitone_Keys_OS1.43.syx')
    # Elektron's version field is fixed at four characters; F denotes build 15.
    raw=syx.write(dn,pack_section(image),DEV,version='XDTF')
    for suffix,data,stock in [('recovery',raw,dn),
        ('from-XDT',rewrap(syx.Syx(raw),dt),syx.Syx(rewrap(dn,dt)))]:
        facts=syx.verify(data,stock,image,DEV,version='XDTF')
        facts.update(details)
        target=ROOT/('candidates/XDT15'+('-recovery' if suffix=='recovery' else '')+'.syx')
        assert not target.exists(),'Preserve existing candidates; explicitly version further builds'
        target.write_bytes(data)
        json_path(target.with_suffix('.json')).write_text(json.dumps(facts,indent=2)+'\n')
        print(target,flush=True)


if __name__=='__main__':
    dt=syx.Syx.load(ROOT.parent/'firmware/Digitakt_OS1.53.syx')
    image,details=make_macro_patch(dt.section(3))
    (ROOT/'candidates/macro-runtime/development-main.bin').write_bytes(image)
    (json_path(ROOT/'candidates/macro-runtime/development-main.json')).write_text(json.dumps(details,indent=2)+'\n')
    print('Built development image:',len(image),'bytes')
    import sys
    if '--package' in sys.argv:package(image,details)
