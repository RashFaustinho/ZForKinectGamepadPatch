"""Execute the generated PowerPC routines on an isolated Unicorn PPC CPU.

Checks actual emitted instructions, not a Python copy of the input logic.
Requires unicorn 2.1.4; original image is used only for constants/zero padding.
Gameplay and visual validation remain separate.
"""
import argparse
import json
import hashlib
import struct
import tomllib
from pathlib import Path
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import UC_PPC_REG_LR, UC_PPC_REG_0, UC_PPC_REG_PC, UC_PPC_REG_MSR

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--patch',type=Path,default=ROOT/'experiments/gamepad-layout-v2/4E4D084E.virtual-player.patch.toml')
parser.add_argument('--report-name',default='cpu-checks.json')
args=parser.parse_args()
source=args.patch
image = Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
patch = tomllib.loads(source.read_text())['patch'][0]
cpu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
cpu.mem_map(0x82000000, 0x700000)
cpu.mem_map(0x100000, 0x20000)
cpu.mem_write(0x82000000, image)
for item in patch['array']: cpu.mem_write(item['address'], bytes.fromhex(item['value']))
for item in patch['be32']: cpu.mem_write(item['address'], struct.pack('>I',item['value']))
def put(a,v): cpu.mem_write(a,struct.pack('>I',v))
def get(a): return struct.unpack('>I',cpu.mem_read(a,4))[0]
def reg(n,v): cpu.reg_write(UC_PPC_REG_0+n,v)
def run(a,end): cpu.emu_start(a,end,count=4000); assert cpu.reg_read(UC_PPC_REG_PC)==end
put(0x826491d8,0x100000);put(0x10001c,0x101000)
put(0x826490dc,0x105000);put(0x105098,0x106000)
put(0x82649298,0x107000);put(0x107054,0x108000)
reg(31,0x10c000)
reg(1,0x11f000) # ABI stack for the first-person trajectory adapter.
def frame(mode=6,ki=0,held=0,pressed=0,released=0):
    put(0x826492d8,mode);cpu.mem_write(0x108868,struct.pack('>f',ki))
    for off,val in ((0x20,held),(0x28,pressed),(0x2c,released)):put(0x106000+off,val)
    run(0x82195550,0x82195554)
def query(action):
    reg(3,0x100000);reg(4,action);reg(5,3);cpu.reg_write(UC_PPC_REG_LR,0x110000)
    run(0x82197118,0x110000)
    return cpu.reg_read(UC_PPC_REG_0+3)
checks=[]
frame(ki=49,held=0x20000,pressed=0x20000)
assert get(0x8266e1a4)==0 and query(0x2d)==0
checks.append('Lower impulse below 50 Ki is rejected')
frame(ki=100,held=0x20000)
assert query(0x2d)==0 and query(0x11)==0
checks.append('Holding the stick after a rejected edge neither queues nor charges')
frame(ki=50,held=0x20000,pressed=0x20000)
assert get(0x8266e1a4)==300 and query(0x2d)==3
frame(ki=50,released=0x20000)
assert get(0x8266e1a4)==299 and query(0x2d)==3
checks.append('Lower impulse at 50 Ki starts before release; release does not rearm')
frame(mode=10,ki=0)
assert query(0x2d)==0 and query(0x30)==3
for _ in range(400):frame(mode=10,ki=0)
assert query(0x30)==3
checks.append('A long native super keeps its continuation gesture beyond 300 frames')
frame(ki=100)
assert query(0x2d)==0 and query(0x30)==0
checks.append('Native cinematic clears initiation while retaining follow-ups; no second cast')
frame(mode=10,ki=0,pressed=0x10000)
assert query(0x31)==0 and query(0x34)==3
checks.append('Scripted super continuation accepts an impulse at zero Ki without arming initiation')
frame(ki=0)
frame(ki=99,pressed=0x10000)
assert query(0x31)==0
frame(ki=100,pressed=0x10000)
assert query(0x31)==3 and query(0x35)==3
checks.append('Upper and Spirit initiation require 100 Ki')
frame(held=2)
assert query(0x11)==3 and query(0x19)==3
checks.append('D-pad Down supplies normal and boss native aura charge')
frame(pressed=0x4000)
assert query(0x1b)==3 and query(0x1c)==0
frame(pressed=0x8000)
assert query(0x1c)==3 and query(0x1b)==0
checks.append('Boss lateral gestures have distinct left/right edges')
frame(mode=9,ki=0,held=0x800)
assert query(0x1d)==3 and query(0x31)==0
checks.append('Boss scripted charge on RT is available independently of normal super energy gates')
frame(pressed=0x80)
bridge_payload=bytes.fromhex(next(x['value'] for x in patch['array'] if x['address']==0x825EB100))
charge_binding,charge_source=struct.unpack_from('>II',bridge_payload,0xA00+5*8)
assert query(0)==3 and query(5)==(3 if charge_source==0x28 and charge_binding&0x80 else 0) and query(0x12)==0
frame(pressed=0x40)
assert query(0)==0 and query(5)==0 and query(0x12)==3
checks.append('X supplies native close/ranged attacks; battle A supplies approach, not Ki blast')
for action,mask in ((1,0x100),(4,0x200),(0x23,0x400),(0x21,0x800)):
    frame(pressed=mask,held=mask)
    assert query(action)==3
checks.append('Four contextual shoulder/trigger choices have distinct inputs')
put(0x100024,0x112000);put(0x10800c,1)
for action,index in ((0,0),(0x19,69),(0x1d,73)):
    put(0x100030+action*4,index);put(0x10013c+action*4,1)
frame(mode=7,held=2)
assert get(0x112000+(0x6bc+69)*4)==3
frame(mode=9,held=0x800)
assert get(0x112000+(0x6bc+73)*4)==3 and get(0x112000+(0x6bc+69)*4)==0
frame(mode=9,pressed=0x80)
assert get(0x112000+0x6bc*4)==3
checks.append('Boss inputs also update discrete recognizers using the runtime index/type table')
for action in (0x24,0x2a,0x2c):
    put(0x100030+action*4,59);put(0x10013c+action*4,1)
frame(mode=9,held=0x200)
assert get(0x112000+(0x6bc+59)*4)==3
frame(mode=9,held=0x20)
assert get(0x112000+(0x6bc+59)*4)==3
frame(mode=9)
assert get(0x112000+(0x6bc+59)*4)==0
checks.append('Shared native recognizers combine active aliases and clear after release')
frame(mode=9,pressed=0x80)
put(0x10800c,0);frame(mode=6)
assert get(0x112000+0x6bc*4)==3
checks.append('Normal fights leave the native recognizer states unchanged')
cpu.reg_write(UC_PPC_REG_MSR, cpu.reg_read(UC_PPC_REG_MSR) | 0x2000)
qte=0x114000
def qte_frame(held=0,kind=1):
    put(0x10800c,kind);put(0x106020,held)
    reg(3,qte);cpu.reg_write(UC_PPC_REG_LR,0x110000)
    run(0x8211a430,0x110000)
    assert cpu.reg_read(UC_PPC_REG_0+3)==qte
put(qte+0x34,0);put(qte+0x44,0);cpu.mem_write(qte+0x48,struct.pack('>f',.25))
qte_frame(held=0x20)
assert get(qte+0x44)==0 and get(qte+0x34)==0
for _ in range(3):qte_frame(held=0x800)
assert get(qte+0x34)==0 and get(qte+0x44)==0x3f400000
qte_frame(held=0x800)
assert get(qte+0x34)==1 and get(qte+0x44)==0x3f800000 and get(qte+0x20)&1
checks.append('RT supplies type-6 boss QTE input; native accumulation and threshold advance the step')
put(qte+0x34,0);put(qte+0x44,0);put(0x100468,0x115000);put(0x11500c,1)
qte_frame(kind=0)
assert get(qte+0x44)==0x3e800000
checks.append('Other battle kinds preserve the original type-6 Kinect input path')
put(0x82649180,0x116000);put(0x11621c,0);put(0x116028,1)
device=0x117000;put(device+0x20,0x12345678)
reg(3,device);cpu.reg_write(UC_PPC_REG_LR,0x110000);run(0x82193038,0x110000)
assert cpu.reg_read(UC_PPC_REG_0+3)==1 and get(device)==1
assert get(device+0x20)==0x12345678 and get(device+0x28)==0 and get(device+0x30)==1
put(0x116028,0);reg(3,device);cpu.reg_write(UC_PPC_REG_LR,0x110000)
run(0x82193038,0x110000)
assert cpu.reg_read(UC_PPC_REG_0+3)==0 and get(device)==0
checks.append('Storage selection chooses Xenia HDD only for a signed-in user and preserves the notification handle')
frame(pressed=0x20)
put(0x10e000,2);put(0x10e004,0)
reg(3,0x10e000);cpu.reg_write(UC_PPC_REG_LR,0x110000)
run(0x8211a720,0x110000)
assert get(0x10e02c)==4 and get(0x10e040)==0x3f800000
checks.append('B returns from a back-only selector with no selectable items')
reg(3,0x100000);reg(4,0x10d000);cpu.reg_write(UC_PPC_REG_LR,0x110000)
run(0x821dc5b0,0x110000)
assert cpu.mem_read(0x10d000,16)==struct.pack('>4f',*([-4096.]*4))
checks.append('Both menu hand coordinates are placed outside the canvas')
result={'engine':'Unicorn 2.1.4 PPC32 BE',
        'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'checks':checks,'passed':len(checks)}
(source.parent/args.report_name).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
