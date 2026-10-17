"""Run the original two-gesture Super recognizer with synthesized pad input.

Only Xenon's std/ld spill helpers are emulated for Unicorn PPC32. The native
gesture queries, earliest-valid boundaries, result calculation and progress
increments execute unchanged. No renderer or gameplay completion claim.
"""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v19/4E4D084E.gamepad-feedback.patch.toml');source=ap.parse_args().patch
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
def execute(patch,technique):
 c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x100000);c.mem_write(0x82000000,image)
 for x in patch['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
 for x in patch['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
 def put(a,v):c.mem_write(a,struct.pack('>I',v&0xffffffff))
 def get(a):return int.from_bytes(c.mem_read(a,4),'big')
 def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
 def g(n):return c.reg_read(UC_PPC_REG_0+n)
 def ret():c.reg_write(UC_PPC_REG_PC,c.reg_read(UC_PPC_REG_LR))
 def abi(uc,a,n,_):
  if 0x82194FD8<=a<0x82195120:
   word=int.from_bytes(uc.mem_read(a,4),'big');op=word>>26
   if op in (58,62) and word&3==0:
    r=(word>>21)&31;ra=(word>>16)&31;imm=word&0xfffc;imm=imm if imm<32768 else imm-65536;addr=(g(ra)+imm)&0xffffffff
    if op==62:uc.mem_write(addr,struct.pack('>Q',g(r)))
    else:reg(r,int.from_bytes(uc.mem_read(addr,8),'big'))
    uc.reg_write(UC_PPC_REG_PC,a+4);return
  if 0x8251D780<=a<=0x8251D7C4 and (a-0x8251D780)%4==0:
   for r in range(14+(a-0x8251D780)//4,32):put(g(1)-0x98+(r-14)*8+4,g(r))
   put(g(1)-8,g(12));ret()
  if 0x8251D7D0<=a<=0x8251D814 and (a-0x8251D7D0)%4==0:
   for r in range(14+(a-0x8251D7D0)//4,32):reg(r,get(g(1)-0x98+(r-14)*8+4))
   reg(12,get(g(1)-8));uc.reg_write(UC_PPC_REG_LR,g(12));ret()
 c.hook_add(UC_HOOK_CODE,abi)
 obj=0x130000;put(0x826491D8,0x109000);put(0x109460,obj)
 put(0x826492D8,10);put(0x826490DC,0x105000);put(0x105098,0x106000)
 put(0x8266E1AC,0x20000 if technique==0 else 0x10000)
 for off,v in ((0,2),(4,technique),(8,0),(0x18,0x140000),(0x20,0x150000),(0x3C,10),(0x40,20),(0x44,30),(0x48,40),(0x4C,1),(0x50,1)):put(obj+off,v)
 put(0x140008,0);put(0x150094,4);put(0x150098,4)
 rows=[]
 for _ in range(45):
  reg(1,0x1EF000);reg(3,obj);reg(4,1)
  for r in range(14,32):reg(r,0x55550000+r)
  c.reg_write(UC_PPC_REG_LR,0x1F0000)
  try:c.emu_start(0x82194E30,0x1F0000,count=3000)
  except Exception as exc:raise RuntimeError(hex(c.reg_read(UC_PPC_REG_PC))) from exc
  assert c.reg_read(UC_PPC_REG_PC)==0x1F0000 and g(1)==0x1EF000
  assert all(g(r)==0x55550000+r for r in range(14,32))
  rows.append({'frame':get(obj+0x10),'state':get(obj),'result':get(obj+0x14),'prepare_quality':get(obj+0x4C),'shoot_quality':get(obj+0x50)})
  if get(obj)==1:break
 return rows
old=tomllib.loads((root/'experiments/gamepad-feedback-v18/4E4D084E.gamepad-feedback.patch.toml').read_text())['patch'][0]
new=tomllib.loads(source.read_text())['patch'][0];cases=[]
for t in range(6):
 before=execute(old,t);after=execute(new,t)
 assert before[-1]['result']==1 and before[-1]['frame']==1,(t,before)
 assert after[-1]=={'frame':21,'state':1,'result':3,'prepare_quality':3,'shoot_quality':3},(t,after)
 assert all(r['prepare_quality']==1 for r in after[:10])
 assert all(r['shoot_quality']==1 for r in after[:20])
 cases.append({'technique':t,'old_early_result':before[-1],'native_timed_result':after[-1],'trace':after})
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':True,'technique_count':6,'cases':cases}
(source.parent/'super-timing-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed all six native two-gesture Super timing variants')
