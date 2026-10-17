"""Execute the boss prompt guard and real glyph adapter for every extra slot."""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v6/4E4D084E.gamepad-feedback.patch.toml')
source=parser.parse_args().patch
p=tomllib.loads(source.read_text())['patch'][0];manifest=json.loads((source.parent/'manifest.json').read_text())
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x40000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
calls=[]
def texture(uc,a,size,user):
 if a==0x823498A8:
  calls.append([uc.reg_read(UC_PPC_REG_0+n) for n in (3,4,5)])
  reg(3,0xF0000000+calls[-1][1]);uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
c.hook_add(UC_HOOK_CODE,texture)
put(0x82649134,0x111000);put(0x82649298,0x112000);put(0x112054,0x113000);put(0x115010,0)
rows=[]
catalogs=[('normal',manifest['extra_pose_texture_indices'])]
if 'alternate_pose_catalog' in manifest:catalogs.append(('alternate',manifest['alternate_pose_catalog']['texture_indices']))
for catalog,indices in catalogs:
 put(0x82649108,0x116000);put(0x11602C,0x117000);put(0x11700C,0x8000 if catalog=='alternate' else 0)
 for kind in (0,1):
  for state in (0,1,2,3,4):
   for qtype in (0,5,6,7,8):
    for slot,normal in enumerate(indices):
     put(0x11300C,kind);put(0x113000+0x2FD0,0x114000);put(0x114004,state);put(0x114008,qtype)
     put(0x115024,slot);reg(3,0x115000);reg(1,0x12F000);c.reg_write(UC_PPC_REG_LR,0x130000)
     calls.clear();c.emu_start(0x822EBBB8,0x130000,count=200)
     expected=10 if kind==1 and state in (1,2) and qtype in (6,7) else normal
     assert calls==[[0x111000,expected,0x54583244]],(catalog,kind,state,qtype,slot,calls)
     rows.append({'catalog':catalog,'kind':kind,'state':state,'type':qtype,'slot':slot,'texture':expected})
put(0x82649108,0)
for missing in ('manager','context','qte'):
 put(0x82649298,0 if missing=='manager' else 0x112000)
 put(0x112054,0 if missing=='context' else 0x113000)
 put(0x113000+0x2FD0,0 if missing=='qte' else 0x114000)
 put(0x115024,11);reg(3,0x115000);c.reg_write(UC_PPC_REG_LR,0x130000);calls.clear()
 c.emu_start(0x822EBBB8,0x130000,count=200);assert calls==[[0x111000,3,0x54583244]]
report={'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':__doc__+' Native texture factory is stubbed; no visual claim.',
        'passed':len(rows)+3,'cases':rows,'missing_pointer_cases':3}
(source.parent/'boss-prompts-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed',report['passed'],'boss prompt cases')
