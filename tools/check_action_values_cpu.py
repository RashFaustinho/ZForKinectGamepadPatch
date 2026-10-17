"""Run every patched action API on PowerPC; check numeric output and sides.

This tests the numeric input interface. Native animation, first-person geometry
and context-dependent QTE acceptance require separate runtime captures.
"""
import argparse
import hashlib
import json
import math
import struct
import tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_LR,UC_PPC_REG_PC,UC_PPC_REG_MSR,UC_PPC_REG_FPR1

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--patch',type=Path,default=ROOT/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml')
args=parser.parse_args()
source=args.patch
patch=tomllib.loads(source.read_text())['patch'][0]
cpu=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN)
cpu.mem_map(0x82000000,0x700000);cpu.mem_map(0x100000,0x20000)
cpu.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in patch['array']:cpu.mem_write(x['address'],bytes.fromhex(x['value']))
for x in patch['be32']:cpu.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):cpu.mem_write(a,struct.pack('>I',v))
def reg(n,v):cpu.reg_write(UC_PPC_REG_0+n,v)
put(0x826490DC,0x105000);put(0x105098,0x106000)
cpu.reg_write(UC_PPC_REG_MSR,0x2000)
main=bytes.fromhex(next(x['value'] for x in patch['array'] if x['address']==0x825EB100))
names=json.loads(Path('/workspace/artifacts/zforkinect/analysis/action-mapping.json').read_text())
rows=[]
for action in range(67):
    mask,offset=struct.unpack_from('>II',main,0xA00+action*8)
    row={'action':hex(action),'native_name':names[action]['name'],'native_type':names[action]['type'],
         'pad_mask':hex(mask),'source':hex(offset),'checks':[]}
    for active in (False,True):
        for address in (0x106020,0x106028,0x8266E1AC,0x8266E1B0):put(address,0)
        target={0x20:0x106020,0x28:0x106028,0x1000:0x8266E1AC,0x1004:0x8266E1B0}[offset]
        put(target,mask if active else 0)
        for entry,kind in ((0x82197118,'integer'),(0x82197250,'float')):
            for sides in (1,2,3):
                reg(3,0x100000);reg(4,action);reg(5,sides)
                cpu.reg_write(UC_PPC_REG_LR,0x110000)
                cpu.emu_start(entry,0x110000,count=160)
                assert cpu.reg_read(UC_PPC_REG_PC)==0x110000
                if kind=='integer':
                    value=cpu.reg_read(UC_PPC_REG_0+3);assert value==(3 if active else 0)
                else:
                    value=struct.unpack('>d',struct.pack('>Q',cpu.reg_read(UC_PPC_REG_FPR1)))[0]
                    assert math.isfinite(value) and value==(1.0 if active else 0.0)
                row['checks'].append({'active':active,'api':kind,'sides':sides,'value':value})
    rows.append(row)
coverage=None
if source.parent.name=='diagnostic-action-coordinates':
    words=struct.unpack('>6I',cpu.mem_read(0x8266E1D0,24))
    assert words==(0xFFFFFFFF,0xFFFFFFFF,7)*2,words
    coverage={'queried':67,'accepted':67,'bitmap_words':[hex(x) for x in words]}
result={'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':True,
        'diagnostic_coverage':coverage,'action_count':len(rows),'numeric_checks':sum(len(x['checks']) for x in rows),
        'scope':__doc__.strip(),'actions':rows}
output=source.parent/'action-values-cpu.json';output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'actions':len(rows),'numeric_checks':result['numeric_checks'],'passed':True,'path':str(output)}))
