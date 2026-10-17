"""Create taktone firmware using Python's standard library and stock inputs."""
import argparse
import json
from pathlib import Path
import sys
from build_hybrid import DEV
from patch_data import apply,sha

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tooling/elekloader-upstream'))
from elekloader import syx
from elekloader.codec.aplib import pack_section
from retarget_transport import rewrap

EXPECTED={
 'digitakt':'9bdd44bb6102fb25c143cfab97bc92b7a89c463f795d3112dce89771e29bcc92',
 'digitone':'c5a54cc05b921f2e4bd814834c5365c2a5aa01d7772a9a2961fac1c3095bf9aa'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digitakt',type=Path,default=ROOT.parent/'firmware/Digitakt_OS1.53.syx')
    parser.add_argument('--digitone',type=Path,default=ROOT.parent/'firmware/Digitone_and_Digitone_Keys_OS1.43.syx')
    parser.add_argument('--out',type=Path,default=ROOT.parent/'firmware')
    args=parser.parse_args()
    if not __debug__:parser.error('Run Python without -O; required verification uses assertions.')
    inputs={}
    for key,digest in EXPECTED.items():
        data=getattr(args,key).read_bytes()
        if sha(data)!=digest:parser.error('Unsupported '+key+' firmware; expected SHA-256 '+digest)
        inputs[key]=syx.Syx(data)
    dt,dn=inputs['digitakt'],inputs['digitone']
    for stock in (dt,dn):
        if syx.write(stock,stock.stored[3],DEV)!=stock.raw:
            raise ValueError('Stock container round trip differs')
    recipe=json.loads((ROOT/'patch-data.json').read_text())
    release=json.loads((ROOT/'release.json').read_text())
    if recipe['version']!=release['release']:raise ValueError('Patch data and release version differ')
    image=apply(recipe,dt,dn)
    print('Packing '+recipe['version']+'...',flush=True)
    raw=syx.write(dn,pack_section(image),DEV,version=recipe['version'])
    outputs={};checks={}
    stem='taktone-extended-'+recipe['version']
    for suffix,data,reference in [('recovery',raw,dn),
            ('from-XDT',rewrap(syx.Syx(raw),dt),syx.Syx(rewrap(dn,dt)))]:
        name=stem+('-recovery' if suffix=='recovery' else '')+'.syx'
        checks[name]=syx.verify(data,reference,image,DEV,version=recipe['version'])
        if sha(data)!=release['output_sha256'][name]:raise ValueError('Release output hash differs: '+name)
        outputs[name]=data
    # Validate both envelopes before writing either output.
    args.out.mkdir(parents=True,exist_ok=True)
    for name,data in outputs.items():(args.out/name).write_bytes(data)
    report=dict(version=recipe['version'],variant=release['variant'],input_sha256=EXPECTED,
                output_sha256={name:sha(data) for name,data in outputs.items()},
                verification='Stock round trips, patch image, both containers and exact release hashes passed',
                hardware_tested=release.get('hardware_tested',False),
                hardware_validation=release.get('hardware_validation'),container_checks=checks)
    (args.out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Created '+', '.join(outputs)+' in '+str(args.out.resolve()))

if __name__=='__main__':main()
