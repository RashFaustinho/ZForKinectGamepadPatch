"""Verify diagnostic prompt wrappers preserve their real callers' registers."""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_PROT_READ,UC_PROT_EXEC
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR,UC_PPC_REG_CTR
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base',type=Path,default=root/'experiments/diagnostic-boss-regression/4E4D084E.local-action-coordinates.patch.toml')
parser.add_argument('--patch',type=Path,default=root/'experiments/diagnostic-prompts/4E4D084E.local-prompts.patch.toml')
args=parser.parse_args();base=tomllib.loads(args.base.read_text())['patch'][0];source=args.patch
patch=tomllib.loads(source.read_text())['patch'][0]
cpu=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);cpu.mem_map(0x82000000,0x700000);cpu.mem_map(0x100000,0x10000)
cpu.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in patch['array']:cpu.mem_write(x['address'],bytes.fromhex(x['value']))
for x in patch['be32']:cpu.mem_write(x['address'],struct.pack('>I',x['value']))
cpu.mem_protect(0x82000000,0x5F0000,UC_PROT_READ|UC_PROT_EXEC)
def put(a,v):cpu.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(cpu.mem_read(a,4),'big')
checks=[]
for kind,hook in enumerate((0x822DE720,0x822DAE40,0x822EBBB8,0x822E4218,0x822E3AF8,0x822E0EEC)):
 old=next(x['value'] for x in base['be32'] if x['address']==hook);delta=old&0x3FFFFFC
 if delta&0x2000000:delta-=0x4000000
 target=hook+delta
 for slot in range(67):
  for n in range(32):cpu.reg_write(UC_PPC_REG_0+n,0x100000+n*16)
  cpu.reg_write(UC_PPC_REG_0+4,slot)
  if kind==2:put(0x100030+0x24,slot);put(0x100030+0x10,0)
  if kind==3:cpu.reg_write(UC_PPC_REG_0+30,slot)
  if kind==4:cpu.reg_write(UC_PPC_REG_0+28,(8-slot)&0xFFFFFFFF)
  if kind==5:put(0x1001F0+0x78,slot)
  before={n:cpu.reg_read(UC_PPC_REG_0+n) for n in list(range(3,9))+list(range(14,32))}
  cpu.reg_write(UC_PPC_REG_LR,0x12345678);cpu.reg_write(UC_PPC_REG_CTR,0x87654321)
  cpu.emu_start(hook,target,count=100)
  assert cpu.reg_read(UC_PPC_REG_PC)==target
  assert all(cpu.reg_read(UC_PPC_REG_0+n)==v for n,v in before.items())
  assert cpu.reg_read(UC_PPC_REG_LR)==(hook+4 if old&1 else 0x12345678)
  assert cpu.reg_read(UC_PPC_REG_CTR)==0x87654321
  block=0x8266E220+kind*0x20
  assert get(block)==slot and get(block+16+(slot//32)*4)&(1<<(slot%32))
  checks.append([hex(hook),slot])
timestamps=any(x['address']==0x8266E2E0 for x in patch['array'])
if timestamps:
 put(0x826490DC,0x105000);put(0x105098,0x106000);put(0x106020,0x400);put(0x106028,0x400);put(0x8266E184,1777)
 for n,v in ((3,0x109000),(4,0x23),(5,3)):cpu.reg_write(UC_PPC_REG_0+n,v)
 cpu.reg_write(UC_PPC_REG_LR,0x10F000);cpu.emu_start(0x82197118,0x10F000,count=500)
 assert cpu.reg_read(UC_PPC_REG_0+3)==3 and get(0x8266E2E0+0x23*4)==1777
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':len(checks),'checks':checks,'per_action_timestamp_verified':timestamps}
(source.parent/'cpu-checks.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed',len(checks),'prompt wrapper cases')
