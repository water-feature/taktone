"""Developer tool: export Python-only patch data from a source-built candidate."""
import argparse,json,sys
from pathlib import Path
from patch_data import create
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tooling/elekloader-upstream'))
from elekloader import syx

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('digitakt','digitone','candidate'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--out',type=Path,help='Defaults to the selected current OS profile recipe')
    a=p.parse_args()
    dt,dn,candidate=[syx.Syx.load(getattr(a,name)) for name in ('digitakt','digitone','candidate')]
    release=json.loads((ROOT/'release.json').read_text())
    recipe=create(dt,dn,candidate.section(3),release['release'])
    if a.out is None:
        from firmware_profiles import profile_for
        a.out=ROOT/('patch-data-'+profile_for(dt.section(3)).version+'.json')
    a.out.write_text(json.dumps(recipe,separators=(',',':'))+'\n')
    print('Exported '+str(a.out))

if __name__=='__main__':main()
