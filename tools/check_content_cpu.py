"""Execute the card adapter and native QR classifier on an isolated PPC CPU."""
import hashlib
import argparse
import json
import struct
import tomllib
from pathlib import Path
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_LR, UC_PPC_REG_PC
from build_content_unlock import QR, MENU, UNLOCK, STATE

ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=ROOT/'experiments/gamepad-unlocked/4E4D084E.gamepad-unlocked.patch.toml');ap.add_argument('--report-name',default='content-cpu.json');args=ap.parse_args();source=args.patch
manifest=json.loads((source.parent/'manifest.json').read_text())
preserve_inactive='powerup_selection' in manifest
catalog=json.loads((ROOT/'experiments/content-unlock/catalog.json').read_text())
cpu=Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
cpu.mem_map(0x82000000,0x700000);cpu.mem_map(0x100000,0x100000)
cpu.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
patch=tomllib.loads(source.read_text())['patch'][0]
for item in patch['array']:cpu.mem_write(item['address'],bytes.fromhex(item['value']))
for item in patch['be32']:cpu.mem_write(item['address'],struct.pack('>I',item['value']))
def put(a,v):cpu.mem_write(a,struct.pack('>I',v))
def get(a):return struct.unpack('>I',cpu.mem_read(a,4))[0]
def reg(n,v):cpu.reg_write(UC_PPC_REG_0+n,v)
def run(a,end):
    cpu.emu_start(a,end,count=30000)
    assert cpu.reg_read(UC_PPC_REG_PC)==end
put(0x826490dc,0x100000);put(0x100098,0x101000)
obj=0x102000
def scan(index,pressed):
    put(STATE+4,index);put(0x101028,pressed);put(obj,1)
    reg(3,obj);cpu.reg_write(UC_PPC_REG_LR,0x110000)
    run(QR,0x110000)
    return cpu.reg_read(UC_PPC_REG_0+3)
checks=[]
assert scan(0,0)==0 and get(obj)==1
assert scan(0,0x20)==0
for index,e in enumerate(catalog['qr_entries']):
    assert scan(index,0x40)==1 and get(obj)==3
    assert (get(obj+0xc),get(obj+0x10),get(obj+0x14))==(e['code'],e['argument'],0)
checks.append('All 85 catalog entries produce the exact decoded native QR fields only on pad input')
assert scan(84,0x200)==1 and get(STATE+4)==0
assert scan(0,0x100)==1 and get(STATE+4)==84
assert scan(0,0x800)==1 and get(STATE+4)==67
assert scan(67,0x400)==1 and get(STATE+4)==78
assert scan(78,0x800)==1 and get(STATE+4)==67
assert scan(0xffffffff,0x40)==1 and get(STATE+4)==0
checks.append('Shoulders wrap the complete catalog; triggers select and wrap all 12 power-up codes')
# Run the original classifier, with a minimal factual reconstruction of its
# table and ABI save/restore helpers replaced only inside this isolated CPU.
put(0x82649234,0);put(0x8264922c,0x114000)
put(0x114040,0x115000);put(0x115000,392);put(0x114084,0x116000)
for i in range(392):
    put(0x116000+i*32+0x10,0xffffffff);put(0x116000+i*32+0x14,0xffffffff)
for row in catalog['character_variants']:
    put(0x116000+row['row']*32+0x10,row['qr_code'])
    put(0x116000+row['row']*32+0x14,row['qr_argument'])
cpu.mem_write(0x8251d7bc,bytes.fromhex('9181fff84e800020'))
cpu.mem_write(0x8251d80c,bytes.fromhex('8181fff87d8803a64e800020'))
reg(1,0x1f0000)
counts={}
for e in catalog['qr_entries']:
    reg(3,e['code']);reg(4,e['argument']);cpu.reg_write(UC_PPC_REG_LR,0x110000)
    run(0x822ff238,0x110000)
    result=cpu.reg_read(UC_PPC_REG_0+3)
    assert result in (1,2,3,4),(e,result)
    counts[result]=counts.get(result,0)+1
assert counts=={1:67,2:12,3:3,4:3},counts
checks.append('The original 822FF238 instructions accept every catalog pair: 67/12/3/3 across its four categories')
# Exercise adapter call preservation with the native initializer as a mocked
# callee. Real initializer effects are checked separately on Xenia.
base=0x120000;put(0x8264920c,0x119000);put(0x119000,base)
put(0x82649358,0x118000)
called=[]
def native_initializer(uc,address,size,user):
    assert uc.reg_read(UC_PPC_REG_0+3)==base+0x20
    called.append(address);put(base+0x2eec,get(base+0x2eec)&~7)
    for off in range(0x2f00,0x2f18,4):put(base+off,0xffffffff)
    for n in range(3,13):reg(n,0xdead0000+n)
    uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
cpu.hook_add(UC_HOOK_CODE,native_initializer,begin=0x821befc0,end=0x821befc0)
def initialize(flags):
    put(base+0x2eec,flags)
    reg(1,0x1f0000);reg(3,0x102030);cpu.reg_write(UC_PPC_REG_LR,0x110000)
    run(MENU,MENU+4)
    assert cpu.reg_read(UC_PPC_REG_0+3)==0x102030
    assert cpu.reg_read(UC_PPC_REG_0+1)==0x1f0000
    assert cpu.reg_read(UC_PPC_REG_LR)==0x110000
initialize(0)
assert get(base+0x2eec)==(1 if preserve_inactive else 5) and get(base+0x2f00)==0
assert [get(base+o) for o in (0x2ef4,0x2ef8,0x2efc)]==[23,391,391]
assert get(0x118008)==1 and get(STATE+8)==1
for i in range(6):put(base+0x2f00+i*4,9+i)
for i,o in enumerate((0x2ef4,0x2ef8,0x2efc)):put(base+o,50+i)
initialize(7)
assert get(base+0x2eec)==7
assert [get(base+0x2f00+i*4) for i in range(6)]==list(range(9,15))
assert [get(base+o) for o in (0x2ef4,0x2ef8,0x2efc)]==[50,51,52]
checks.append('Unlock adapter preserves menu pointer, stack, LR and selected items; requests one native save of the changed content')
if preserve_inactive:
    for flags in (0,1,3,5,7,0xA1,0xA5):
        values=[get(base+0x2f00+i*4) for i in range(6)]
        initialize(flags)
        assert get(base+0x2eec)==flags|1
        if flags&4:assert [get(base+0x2f00+i*4) for i in range(6)]==values
    # The original gameplay checker must see no active power-up after the
    # native reset flag is cleared, including after menu initialization.
    put(0x826492A0,0)
    for active,expected in ((True,1),(False,0)):
        for i in range(6):put(base+0x2f00+i*4,0xffffffff)
        put(base+0x2f00,0);put(base+0x2eec,5 if active else 1);initialize(5 if active else 1)
        reg(3,0);cpu.reg_write(UC_PPC_REG_LR,0x110000);run(0x82203BF0,0x110000)
        assert cpu.reg_read(UC_PPC_REG_0+3)==expected
    checks.append('Inactive/active power-up flag survives menu initialization; original gameplay checker distinguishes the two states')
result={'engine':'Unicorn 2.1.4 PPC32 BE','patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'checks':checks,'passed':len(checks),'native_classifier_categories':counts,
        'limits':'Native classifier executed; native unlock initializer mocked for ABI preservation checks. Xenia gameplay/load tests are separate.'}
(source.parent/args.report_name).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
