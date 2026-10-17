"""Run original 822A4138 to verify RT initializes a charged strike's hand.

The native close-distance predicate and ABI helpers are stubbed in this 32-bit
fixture; the original selection body and both actual input APIs execute.
"""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v9/4E4D084E.gamepad-feedback.patch.toml');source=ap.parse_args().patch
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x40000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes());p=tomllib.loads(source.read_text())['patch'][0]
main=bytes.fromhex(next(x['value'] for x in p['array'] if x['address']==0x825EB100))
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(c.mem_read(a,4),'big')
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
def fixture(uc,a,size,user):
 if a==0x8251D7B8:uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 if a==0x8251D808:uc.reg_write(UC_PPC_REG_PC,0x130000)
 if a==0x82206248:reg(3,1);uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
c.hook_add(UC_HOOK_CODE,fixture)
put(0x826490DC,0x105000);put(0x105098,0x106000);put(0x826491D8,0x109000);put(0x112580,0x118000)
rows=[]
for mode,expected in [(4,5),(5,5),(6,7)]:
 for button,mask,edge in [('RT',0x800,0x800),('RT_already_held',0x800,0),('Y',0x10,0x10),('Y_already_held',0x10,0),('X',0x80,0x80),('none',0,0)]:
  for suppressed in (False,True):
   put(0x826492D8,mode);put(0x106020,mask);put(0x106028,edge);put(0x118264,int(suppressed))
   for off in (0x2530,0x2538):put(0x110000+off,0xFFFFFFFF)
   reg(1,0x12F000);reg(3,0x110000);reg(4,2);c.reg_write(UC_PPC_REG_LR,0x130000)
   c.emu_start(0x822A4138,0x130000,count=3000)
   assert c.reg_read(UC_PPC_REG_PC)==0x130000
   action=get(0x112530);side=get(0x112538)
   binding,field=struct.unpack_from('>II',main,0xA00+expected*8)
   manifest=json.loads((source.parent/'manifest.json').read_text())
   if 'combat_feedback' in manifest and mode==6:binding,field=0x10,0x20
   if 'animated_combat' in manifest and mode==4:binding,field=0x10,0x20
   want=bool(binding&(mask if field==0x20 else edge)) and not suppressed
   assert action==(expected if want else 0xFFFFFFFF),(mode,button,action)
   assert side==(0 if want else 0xFFFFFFFF),(mode,button,side)
   rows.append({'mode':mode,'button':button,'suppressed':suppressed,'native_action':hex(action),'native_side':hex(side)})
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':len(rows),'cases':rows}
(source.parent/'charge-start-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed',len(rows),'native charge-hand selection cases')
