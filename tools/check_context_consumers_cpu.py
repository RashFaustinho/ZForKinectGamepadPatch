"""Execute original contextual-strike consumer with the emitted pad bridge.

This verifies the original dispatcher's four distinct results and action
records, including native input suppression. ABI register save/restore helpers
are stubbed because this isolated CPU runs in 32-bit mode. It does not prove that a battle
has reached that prompt or establish its visible animation.
"""
import hashlib
import argparse
import json
import struct
import tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_LR,UC_PPC_REG_PC

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml')
source=parser.parse_args().patch
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
cpu=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN)
cpu.mem_map(0x82000000,0x700000);cpu.mem_map(0x100000,0x40000);cpu.mem_write(0x82000000,image)
p=tomllib.loads(source.read_text())['patch'][0]
for x in p['array']:cpu.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:cpu.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):cpu.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(cpu.mem_read(a,4),'big')
put(0x826490DC,0x105000);put(0x105098,0x106000);put(0x826491D8,0x109000)
put(0x826492A0,0);put(0x8264933C,0x10A000);put(0x10A000,2)
put(0x112580,0x118000)
def abi_helpers(uc,address,size,user):
    if address==0x8251D7B4:uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
    elif address==0x8251D804:uc.reg_write(UC_PPC_REG_PC,0x130000)
cpu.hook_add(UC_HOOK_CODE,abi_helpers)
rows=[]
for button,mask,expected,action in [('LB',0x100,1,0x1E),('RB',0x200,2,0x1F),('LT',0x400,3,0x20),('RT',0x800,4,0x21),('none',0,0,None)]:
    for suppressed in (0,1):
        put(0x106020,mask);put(0x106028,mask);put(0x118264,suppressed)
        put(0x112530,0xFFFFFFFF);put(0x112534,0)
        cpu.reg_write(UC_PPC_REG_0+1,0x12F000);cpu.reg_write(UC_PPC_REG_0+3,0x110000)
        cpu.reg_write(UC_PPC_REG_LR,0x130000)
        try:cpu.emu_start(0x8229CEA0,0x130000,count=1500)
        except Exception as exc:raise RuntimeError(f'Native consumer stopped at {cpu.reg_read(UC_PPC_REG_PC):X}') from exc
        assert cpu.reg_read(UC_PPC_REG_PC)==0x130000
        result=cpu.reg_read(UC_PPC_REG_0+3);last=get(0x112530)
        assert result==expected,(button,result)
        assert last==(action if action is not None and not suppressed else 0xFFFFFFFF),(button,last)
        rows.append({'button':button,'suppressed':bool(suppressed),'native_result':result,'native_last_action':hex(last)})
report={'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':__doc__.strip(),'passed':True,'cases':rows}
out=source.parent/'context-consumers-cpu.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(rows),'output':str(out)}))
