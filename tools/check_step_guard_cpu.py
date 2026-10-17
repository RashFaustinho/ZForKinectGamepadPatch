"""Execute original free-combat priority gates and contextual icon adapters.

The native gate branches, permission function and actual patched input API run
on PowerPC. Only the texture factory is a recording callback. This catches the
right-stick alias that the old single-action binding checks did not cover.
"""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_LR,UC_PPC_REG_PC,UC_PPC_REG_MSR
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v16/4E4D084E.gamepad-feedback.patch.toml');source=ap.parse_args().patch
p=tomllib.loads(source.read_text())['patch'][0]
animated='animated_combat' in json.loads((source.parent/'manifest.json').read_text())
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x100000)
c.reg_write(UC_PPC_REG_MSR,0x2000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
def run(a,end):
 c.reg_write(UC_PPC_REG_LR,end);c.emu_start(a,end,count=5000);assert c.reg_read(UC_PPC_REG_PC)==end
put(0x826490DC,0x105000);put(0x105098,0x106000);put(0x826491D8,0x109000);put(0x826492A0,0)
rows=[]
for mode in (4,6):
 put(0x826492D8,mode)
 for button,mask in [('none',0),('left',0x4000),('right',0x8000),('B',0x20),('right_and_B',0x8020)]:
  for edge in (0,mask):
   put(0x106020,mask);put(0x106028,edge)
   accepted={}
   for gate,start in [('defensive_C',0x822A2DAC),('left_28',0x822A2E0C),('right_29',0x822A2E3C)]:
    reg(1,0x1EF000);reg(24,0);reg(31,0x109000);run(start,0x822A3290)
    accepted[gate]=c.reg_read(UC_PPC_REG_0+24)
   assert accepted['defensive_C']==int(bool(mask&0x20)),(mode,button,edge,accepted)
   assert accepted['left_28']==int(bool(mask&0x4000))
   assert accepted['right_29']==int(bool(mask&0x8000))
   for action,want in [(0xB,bool(mask&0x20)),(0xC,bool(mask&0x20)),(0xD,bool(mask&0x4000)),(0xE,bool(mask&0x8000))]:
    reg(3,0x109000);reg(4,action);run(0x82197118,0x1F0000);assert c.reg_read(UC_PPC_REG_0+3)==(3 if want else 0)
   rows.append({'mode':mode,'button':button,'edge':bool(edge),'gates':accepted})
# QTE/cinematic modes keep the previous C binding. No global table is changed.
for mode in (0,5,7,8,9,10):
 put(0x826492D8,mode)
 for button,mask in [('right',0x8000),('B',0x20)]:
  put(0x106020,mask);put(0x106028,0);reg(4,0xC);run(0x82197118,0x1F0000)
  assert c.reg_read(UC_PPC_REG_0+3)==(3 if button=='right' else 0)
textures=[]
def factory(uc,a,n,user):
 if a in (0x8251D7A8,0x8251E9A4,0x8251E9F0):uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 if a in (0x8251D7F8,0x8251D80C):uc.reg_write(UC_PPC_REG_PC,0x1F0000)
 if a==0x823498A8:
  textures.append(uc.reg_read(UC_PPC_REG_0+4));reg(3,0x150000);uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
c.hook_add(UC_HOOK_CODE,factory)
# Execute the complete original dispatcher: RT must not enter its first
# ordinary-strike branch, and must reach the sustained close charge gate.
put(0x112580,0x118000);put(0x8264933C,0);put(0x826492D8,4)
charge_rows=[]
charge_mask=0x10 if animated else 0x800
for held in (0,charge_mask):
 for edge in (0,held):
  put(0x106020,held);put(0x106028,edge)
  for kind in (0,1):
   reg(1,0x1EF000);reg(3,0x110000);reg(4,kind);run(0x822A25A8,0x1F0000)
   result=c.reg_read(UC_PPC_REG_0+3);assert result==int(kind==1 and held==charge_mask),(kind,held,edge,result)
   charge_rows.append({'button':'Y' if animated else 'RT','held':bool(held),'edge':bool(edge),'native_dispatcher_case':kind,'result':result})
icon_rows=[]
for entry,guard,heavy,fallback in [(0x825EED00,0xC,(3,6,7,8,10),0x821DB5D4),(0x825EEE00,9,(3,4,5,6),0x821DB660)]:
 for mode in (4,6):
  put(0x826492D8,mode)
  for index in (guard,*heavy):
   put(0x82649134,0x140000);reg(4,index);textures.clear()
   # At close range only the defensive entry is overridden.
   mapped_close=(5,6) if entry==0x825EED00 else (3,4)
   if mode==4 and index!=guard and not (animated and index in mapped_close):run(entry,fallback);assert c.reg_read(UC_PPC_REG_0+4)==index;continue
   run(entry,0x1F0000);assert textures==[2 if index==guard else 4]
   icon_rows.append({'entry':hex(entry),'mode':mode,'index':index,'texture':textures[0]})
   put(0x82649134,0);reg(4,index);run(entry,fallback);assert c.reg_read(UC_PPC_REG_0+4)==index
uv_rows=[]
for kind,side in [('pad',0),('pad',1),('original',0),('original',1),('missing_loader',1),('bad_count',1),('missing_table',1)]:
 put(0x82649134,0 if kind=='missing_loader' else 0x140000)
 put(0x1400D8,33 if kind=='bad_count' else 34);put(0x1400DC,0 if kind=='missing_table' else 0x141000)
 c.mem_write(0x141000,bytes(34*4));put(0x14100C,0x150000)
 put(0x121024,0x150000 if kind!='original' else 0x150100)
 put(0x121020,1);reg(1,0x1EF000);reg(3,0x121000);reg(29,side);reg(9,1);reg(10,0x820E0000)
 run(0x822DF944,0x1F0000)
 uv=struct.unpack('>4f',c.mem_read(0x121050,16))
 expected=(0.,0.,1.,1.) if kind=='pad' or side==0 else (1.,0.,0.,1.)
 assert uv==expected,(kind,side,uv)
 assert c.reg_read(UC_PPC_REG_0+3)==0x121000 and c.reg_read(UC_PPC_REG_0+29)==side
 uv_rows.append({'resource':kind,'native_side':side,'uv':uv})
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'priority_gate_cases':rows,'unchanged_cinematic_cases':12,'original_charge_priority_cases':charge_rows,'icons':icon_rows,'original_HUD_UV_cases':uv_rows,'passed':True}
(source.parent/'step-guard-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'priority_cases':len(rows),'icon_cases':len(icon_rows)}))
