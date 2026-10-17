"""Execute the final bridge, native charge gate and arm data flow on PPC.

Includes real held/edge/release sequences, cancellation across contexts,
single-frame release, both native arm sides, finite geometry in all three
NUI buffers, and unchanged B/right/far-Y behavior. Native gameplay timing and
visual quality require the separate Xenia observations.
"""
import argparse,hashlib,json,math,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR,UC_PPC_REG_MSR
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v17/4E4D084E.gamepad-feedback.patch.toml');source=ap.parse_args().patch
p=tomllib.loads(source.read_text())['patch'][0]
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x100000)
c.reg_write(UC_PPC_REG_MSR,0x2000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(c.mem_read(a,4),'big')
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
def run(a,end):
 c.emu_start(a,end,count=10000);assert c.reg_read(UC_PPC_REG_PC)==end,hex(c.reg_read(UC_PPC_REG_PC))
put(0x826491D8,0x100000);put(0x10001C,0x101000);put(0x826490DC,0x105000);put(0x105098,0x106000)
put(0x82649298,0x107000);put(0x107054,0x108000);put(0x10800C,0);put(0x108000+0x2FC0,0x140000);put(0x142580,0x148000)
reg(1,0x1EF000);reg(31,0x10C000)
def frame(mode=4,state=0,held=0,edge=0,release=0,side=0):
 put(0x826492D8,mode);put(0x141130,state);put(0x142538,side)
 for off,v in ((0x20,held),(0x28,edge),(0x2C,release)):put(0x106000+off,v)
 run(0x82195550,0x82195554)
 assert c.reg_read(UC_PPC_REG_0+1)==0x1EF000
def query(action):
 reg(3,0x100000);reg(4,action);reg(5,3);c.reg_write(UC_PPC_REG_LR,0x1F0000);run(0x82197118,0x1F0000)
 return c.reg_read(UC_PPC_REG_0+3)
checks=[]
frame(held=0x10,edge=0x10)
assert query(0)==0 and query(2)==0 and query(3)==0 and query(5)==3 and query(6)==3
frame(state=13,held=0x10)
assert query(0)==0 and query(5)==3 and query(6)==3
for _ in range(35):frame(state=13,held=0x10);assert query(0)==0
frame(state=13,release=0x10)
assert query(0)==0 and query(6)==3 and get(0x8266E800)==0
for t in range(4):
 frame(state=13);assert query(0)==0 and query(6)==3
frame(state=13)
assert query(0)==3 and query(6)==3 and get(0x8266E800)==1
frame(state=13)
assert query(0)==0 and query(6)==0 and get(0x8266E800)==0
checks.append('Y holds native charge; release animates the fist for five frames then supplies one native punch with charge retained')
for mode,state in [(6,20),(5,12),(8,46),(7,0),(4,37),(0,0)]:
 frame(state=13,held=0x10);frame(mode=mode,state=state,release=0x10)
 assert get(0x8266E800)==0 and query(0)==0
checks.append('Leaving close charge or entering a cinematic never synthesizes a punch')
for mode,state in [(6,20),(5,12),(8,46),(4,37)]:
 frame(state=13,held=0x10);frame(state=13,release=0x10);frame(mode=mode,state=state)
 for _ in range(8):frame(mode=mode,state=state);assert get(0x8266E800)==0 and get(0x8266E820)==0
checks.append('Interruptions during the release trajectory cancel the pending punch')
frame(state=13,held=0x10);put(0x108000+0x2FC0,0x150000);frame(state=13,release=0x10)
assert get(0x8266E800)==0;put(0x108000+0x2FC0,0x140000)
checks.append('Actor replacement cancels the previous actor\'s charge release')
for mode in (4,6):
 for held,expected in [(0x20,0xC),(0x8000,0x29),(0x4000,0x28)]:
  frame(mode=mode,held=held);assert query(expected)==3
  assert query(0xC)==(3 if held==0x20 else 0)
frame(mode=6,state=32,held=0x10)
assert query(3)==3 and query(6)==3 and query(7)==3 and query(2)==0
checks.append('B guard, both steps and far Y heavy remain distinct')
for mode,state in [(4,0),(4,1),(6,20)]:
 frame(mode=mode,state=state)
 for _ in range(20):frame(mode=mode,state=state)
 ready=bytes(c.mem_read(0x1010D0,320))
 for _ in range(20):frame(mode=mode,state=state);assert bytes(c.mem_read(0x1010D0,320))==ready and query(0xC)==0
 assert struct.unpack('>f',ready[7*16+4:7*16+8])[0]>.5
checks.append('Idle keeps a stable raised ready stance without activating guard')
frame(held=0x800,edge=0x800);assert query(2)==3 and query(6)==0
checks.append('The previous near Y uppercut remains available on RT without starting charge')
trajectories=[]
for state in (10,29,32):
 for side in (0,1):
  frame(state=0);samples=[]
  for t in range(16):
   frame(state=state,side=side)
   joints=bytes(c.mem_read(0x1010D0,320))
   assert joints==bytes(c.mem_read(0x101B80,320))==bytes(c.mem_read(0x102600,320))
   assert all(math.isfinite(f) for f in struct.unpack('>80f',joints))
   samples.append(struct.unpack_from('>3f',joints,(7 if side==0 else 11)*16))
  assert len(set(samples))>=8 and samples[0][2]>samples[4][2] and samples[11]==samples[0]
  trajectories.append({'native_state':state,'side':side,'hands':samples})
checks.append('Accepted jab/normal shot/heavy shot animate forward and recoil on both sides in every joint buffer')
frame(state=0);frame(mode=6,state=29);frame(mode=6,state=29)
tail=[]
for t in range(12):
 frame(mode=6,state=20);tail.append(tuple(struct.unpack('>3f',c.mem_read(0x1010D0+7*16,12))))
assert min(v[2] for v in tail)<tail[-1][2] and len(set(tail))>=7
frame(mode=6,state=29);assert get(0x8266E810)==0
checks.append('A short shot state completes its visual motion through idle; a new shot restarts the motion')
frame(state=13,held=0x10);charge=bytes(c.mem_read(0x1010D0,320));frame(state=13,release=0x10)
for _ in range(4):frame(state=13)
assert bytes(c.mem_read(0x1010D0,320))!=charge
checks.append('Charge pose switches to a visible punch trajectory after release')
# Verify the adapter's ABI at its real continuation, before the caller's copy.
frame(state=0)
preserved={3:0x12345,4:0xA4,5:0xA5,6:0xA6,7:0x1010B0,10:0x101000,12:0xAC}
for n,v in preserved.items():reg(n,v)
c.reg_write(UC_PPC_REG_LR,0x1D1234)
c.ctl_flush_tb() # The continuation lies inside a previously cached block.
run(0x825EC000,0x825EB158)
assert all(c.reg_read(UC_PPC_REG_0+n)==v for n,v in preserved.items())
assert c.reg_read(UC_PPC_REG_LR)==0x1D1234 and c.reg_read(UC_PPC_REG_0+1)==0x1EF000
checks.append('The pose adapter preserves caller arguments, destination pointer, stack and link register')
textures=[]
def factory(uc,a,size,user):
 if a==0x823498A8:
  textures.append(uc.reg_read(UC_PPC_REG_0+4));uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
c.hook_add(UC_HOOK_CODE,factory)
put(0x82649134,0x160000)
for entry,index,mode,state,expected in [(0x825EED00,5,4,13,4),(0x825EED00,6,4,13,4),(0x825EED00,0,4,13,4),(0x825EED00,2,4,0,10),(0x825EEE00,2,4,0,10),(0x825EEE00,3,4,13,4),(0x825EED00,3,6,32,4)]:
 put(0x826492D8,mode);put(0x8266E808,state);reg(4,index);textures.clear();c.reg_write(UC_PPC_REG_LR,0x1F0000)
 run(entry,0x1F0000);assert textures==[expected],(entry,index,textures)
checks.append('Charge and release prompts show Y; the retained uppercut shows RT; far heavy stays Y')
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checks':checks,'trajectories':trajectories,'passed':True}
(source.parent/'animated-combat-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
