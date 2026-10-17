"""Replay scene lock clears through native UI dispatch in a captured 1.53 UI.

Developer regression using an optional Unicorn installation and a local
macros-xdt15-restored gui.snap capture; snapshot data is never distributed.
Run: python3 internal/tests/verify_native_scene_pages.py /path/to/gui.snap
"""
import pickle,zlib,sys,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_M68K,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.m68k_const import *
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
from macro_runtime import CODE,TABLE,CONSTANTS as C
from panel_patch import syx,BASE
class SnapshotReader(pickle.Unpickler):
 def find_class(self,*args):raise ValueError('Unexpected object in snapshot')
with Path(sys.argv[1]).open('rb') as f:blob=SnapshotReader(f).load()
u=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN);u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
u.mem_map(0x40000000,128<<20);u.mem_map(0x80000000,1<<20)
for a,data in blob['pages'].items():
 raw=zlib.decompress(data)
 if 0x40000000<=a<0x48000000 or 0x80000000<=a<0x80100000:u.mem_write(a,raw)
image=syx.Syx.load(r.parent/'firmware/Digitakt_OS1.53.syx').section(3)
u.mem_write(BASE,image);u.mem_write(CODE,(r/'candidates/macro-runtime/runtime.bin').read_bytes())
labels={k:int(v,16)for k,v in json.loads((r/'reports/candidates/macro-runtime/audit.json').read_text())['symbols'].items()}
def get(a):return int.from_bytes(u.mem_read(a,4),'big')
def put(a,v):u.mem_write(a,struct.pack('>I',v&0xffffffff))
stack=0x47fff000;stop=0x40001000
def call(at,*args):
 u.mem_write(stack,struct.pack('>'+str(len(args)+1)+'I',stop,*args));u.reg_write(UC_M68K_REG_SR,0x2700);u.reg_write(UC_M68K_REG_A7,stack)

 try:u.emu_start(at,stop,count=100000)
 except Exception:
  print('failed pc',hex(u.reg_read(UC_M68K_REG_PC)));raise
 assert u.reg_read(UC_M68K_REG_PC)==stop,hex(u.reg_read(UC_M68K_REG_PC))
 return u.reg_read(UC_M68K_REG_D0)
u.mem_write(0x40033076,b'\x4e\xf9'+struct.pack('>I',labels['macro_grid_key'])+b'\x4e\x71')
u.mem_write(0x4003b272,b'\x4e\xf9'+struct.pack('>I',labels['macro_source_key'])+b'\x4e\x71')

original_widget=get(C['ACTIVE_WIDGET'])
references=[]
for base,comp in blob['pages'].items():
 if not 0x42000000<=base<0x43000000:continue
 data=zlib.decompress(comp);pos=data.find(struct.pack('>I',original_widget))
 while pos>=0:
  references.append(base+pos);pos=data.find(struct.pack('>I',original_widget),pos+4)
for name,widget,expected in [('SRC',0x42a8ceb0,0x401848d4),('FLTR',0x42a8d2b0,0x40184290),('AMP',0x42a8d8b0,0x401af558),('LFO',0x42a8d4b0,0x4018414c)]:
 assert get(widget)==expected, 'Snapshot does not contain the expected initialized page'
 for a in references:put(a,widget)
 for knob in range(8):
  pid=call(get(get(widget)+0x9c),widget,knob)
  idx=call(0x40078d80,pid)
  put(C['HELD'],0);put(C['PATTERN'],0);put(C['TRACK'],0);put(C['RAM_READY'],1);put(C['ACTIVE_WIDGET'],0)
  u.mem_write(TABLE,bytes(4096));put(TABLE,0x01000000);put(TABLE+4,C['SCENE_MAGIC'])
  u.mem_write(TABLE+8+idx//8,bytes([1<<(idx%8)]));u.mem_write(TABLE+68+2*idx,b'\x12\x34')
  event=0x47ff0000
  call(0x400c30fc,event,40+knob,1,0,127)
  call(labels['macro_key'],get(C['CTRL'])-0x40,event)
  assert u.mem_read(TABLE+8+idx//8,1)==b'\0',(name,knob,idx)
  assert u.mem_read(TABLE+68+2*idx,2)==b'\0\0',(name,knob,idx)
 print(name+': 8/8 encoder presses cleared through native UI dispatch with no cached grid')
