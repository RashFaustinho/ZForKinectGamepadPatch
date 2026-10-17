"""Revision 17: native charge/release on Y and deterministic first-person arms.

Keep the original arm meshes, hand-pose clip and renderer. Supply an authored
strike/shot trajectory instead of an absent camera's stationary waist joints.
Only accepted normal-combat actor states use the trajectory; other contexts
keep their original virtual skeleton. HP, energy, native timing and animation
state machines are never forced.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from ppc_emit import Assembler

root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v16/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
def replace(address,code,limit):
 old=next(x for x in p['array'] if x['address']==address)
 assert len(code)<=limit,(hex(address),len(code),limit)
 for x in p['array']:
  if x is not old:assert address+len(code)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=address
 old['value']=code.hex()
def add(address,code):
 assert not any(image[address-0x82000000:address-0x82000000+len(code)])
 for x in p['array']:assert address+len(code)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=address
 p['array'].append({'address':address,'value':code.hex()})
def jump(a,n):a.jump(n,0x48000000)
def mr(a,d,s):a.emit(0x7C000378|(s<<21)|(d<<16)|(s<<11))

# Per-frame adapter runs before the existing skeleton and both derived copies.
# r3, r4, r5, r6, r7, r10, r12 and LR belong to its caller and must survive.
# State is confined to checked writable alignment padding, not actor fields.
STATE=0x8266E800;POSE=0x8266E600;ENTRY=0x825EC000;TABLE=0x825EC800;CHARGE=0x825ECE00
CHARGED_TABLE=0x8266E900
sections=json.loads(Path('/workspace/artifacts/zforkinect/analysis/code-analysis.json').read_text())['sections']
assert max(0x82000000+s['rva']+max(s['virtual_size'],s['raw_size']) for s in sections if s['name'] in ('.data','.XBMOVIE','.NSPCH'))<=POSE
assert STATE+0x40<0x82000000+next(s['rva'] for s in sections if s['name']=='.idata')
assert not any(image[POSE-0x82000000:STATE-0x82000000+0x40])
a=Assembler(ENTRY)
a.d(37,1,1,-0x60)
for r in (4,5,6,7,10,12):a.stw(r,0x20+(r-4)*4,1)
a.pointer(11,0x825EB900);a.pointer(7,STATE);a.li(8,0)
for off in (0,0x24,0x28):a.stw(8,off,7)
a.pointer(9,0x826492D8);a.lwz(9,0,9);a.cmp(9,4);a.jump('mode');a.cmp(9,6);a.jump('clear',0x40820000)
a.label('mode');mr(a,12,9)
a.pointer(9,0x82649298);a.lwz(9,0,9);a.cmp(9,0);a.jump('clear');a.lwz(9,0x54,9);a.cmp(9,0);a.jump('clear')
a.lwz(8,0xC,9);a.cmp(8,0);a.jump('clear',0x40820000);a.lwz(6,0x2FC0,9);a.cmp(6,0);a.jump('clear')
a.pointer(9,0x826490DC);a.lwz(9,0,9);a.cmp(9,0);a.jump('clear');a.lwz(9,0x98,9);a.cmp(9,0);a.jump('clear')
a.lwz(5,0x20,9);a.lwz(4,0x2C,9);a.lwz(8,0x1130,6)
# A new accepted attack restarts its trajectory, including repeated jabs with
# an idle gap. Completing an earlier trajectory through idle is cosmetic.
a.lwz(9,0x1C,7);a.emit(0x7C094000);a.jump('same_native')
for state in (10,29,32):a.cmp(8,state);a.jump('new_native')
jump(a,'same_native');a.label('new_native');a.li(9,0);a.stw(9,8,7);a.stw(9,0xC,7);a.stw(9,0x10,7)
a.label('same_native');a.stw(8,0x1C,7)
# A short visual lead-in lets the released fist extend before the native hit
# switches to its external combo camera. These are virtual input bits only.
# Cancel the pending input as soon as its native actor/context is lost.
a.lwz(9,0x18,7);a.emit(0x7C093000);a.jump('not_armed',0x40820000)
a.cmp(12,4);a.jump('not_armed',0x40820000);a.cmp(8,13);a.jump('not_armed',0x40820000)
a.andi(9,5,0x30);a.jump('not_armed',0x40820000)
a.lwz(9,0x20,7);a.cmp(9,0);a.jump('pending',0x40820000)
a.lwz(9,4,7);a.cmp(9,0);a.jump('not_armed');a.andi(9,4,0x10);a.jump('not_armed');a.li(9,1);a.stw(9,0x20,7);jump(a,'release_ready')
a.label('pending');a.d(14,9,9,1);a.cmp(9,6);a.jump('launch')
a.stw(9,0x20,7);jump(a,'release_ready')
a.label('launch');a.li(9,0);a.stw(9,0x20,7);a.li(9,1);a.stw(9,0,7);a.li(9,0x10);a.stw(9,0x28,7)
a.label('release_ready');a.li(9,0x10);a.stw(9,0x24,7);jump(a,'update_arm')
a.label('not_armed');a.li(9,0);a.stw(9,0x20,7)
a.label('update_arm');a.li(9,0);a.cmp(12,4);a.jump('arm_done',0x40820000);a.andi(9,5,0x10);a.stw(9,0x24,7)
# Keep the preparation virtual input through the release trajectory.
a.lwz(9,0x20,7);a.cmp(9,0);a.jump('held_charge');a.li(9,0x10);a.stw(9,0x24,7)
a.label('held_charge');a.lwz(9,0,7);a.cmp(9,0);a.jump('arm_state');a.li(9,0x10);a.stw(9,0x24,7)
a.label('arm_state');a.li(9,0);a.cmp(8,13);a.jump('arm_done',0x40820000);a.andi(9,5,0x10)
a.label('arm_done');a.stw(9,4,7);a.stw(6,0x18,7)
# Guard stays native and has priority over cosmetic trajectories.
a.andi(9,5,0x20);a.jump('animation');a.pointer(11,0x825EE800);jump(a,'reset_visual')
a.label('animation');a.li(4,0)
a.cmp(8,10);a.jump('punch');a.cmp(8,29);a.jump('punch');a.cmp(8,32);a.jump('punch')
a.cmp(8,13);a.jump('idle_tail',0x40820000)
a.andi(9,5,0x10);a.jump('released');a.li(4,2);jump(a,'clock')
a.label('released');a.lwz(9,0x20,7);a.cmp(9,0);a.jump('charged_punch',0x40820000)
a.lwz(9,0,7);a.cmp(9,0);a.jump('charged_punch',0x40820000)
a.lwz(9,0xC,7);a.cmp(9,1);a.jump('reset_visual',0x40820000)
a.label('punch');a.li(4,1)
jump(a,'clock')
a.label('charged_punch');a.li(4,3);jump(a,'clock')
a.label('idle_tail')
for state in (0,1,20):a.cmp(8,state);a.jump('tail')
jump(a,'reset_visual');a.label('tail');a.lwz(9,0xC,7);a.cmp(9,1);a.jump('ready',0x40820000)
a.lwz(9,0x10,7);a.cmp(9,15);a.jump('ready',0x40800000);a.lwz(8,8,7);a.li(4,1);jump(a,'clock')
# A pad has a stable ready stance between attacks, rather than waist-height
# hands that repeatedly leave the first-person frustum and fade back in.
a.label('ready');a.li(9,0)
for off in (8,0xC,0x10):a.stw(9,off,7)
a.pointer(4,TABLE+15*96);jump(a,'copy')
a.label('clock');a.lwz(9,8,7);a.emit(0x7C094000);a.jump('new',0x40820000);a.lwz(9,0xC,7);a.emit(0x7C092000);a.jump('new',0x40820000)
a.lwz(9,0x10,7);a.d(14,9,9,1);a.cmp(9,15);a.jump('tick',0x40810000);a.li(9,15);jump(a,'tick')
a.label('new');a.li(9,0)
a.label('tick');a.stw(9,0x10,7);a.stw(8,8,7);a.stw(4,0xC,7)
a.cmp(4,2);a.jump('charge');a.cmp(4,3);a.jump('charged_table')
a.emit(0x1D290060);a.pointer(4,TABLE);a.emit(0x7C844A14);jump(a,'copy')
a.label('charged_table');a.cmp(9,5);a.jump('charged_index',0x40810000);a.li(9,5)
a.label('charged_index');a.emit(0x1D290060);a.pointer(4,CHARGED_TABLE);a.emit(0x7C844A14);jump(a,'copy')
a.label('charge');a.pointer(4,CHARGE)
a.label('copy');a.pointer(11,0x825EB900);a.pointer(5,POSE);a.li(9,112);a.emit(0x7D2903A6)
a.label('base');a.lwz(8,0,11);a.stw(8,0,5);a.d(14,11,11,4);a.d(14,5,5,4);a.jump('base',0x42000000)
a.pointer(5,POSE);a.lwz(9,0x2538,6);a.cmp(9,1);a.jump('right')
for j,index in enumerate((5,6,7,9,10,11)):
 for k in range(4):a.lwz(8,j*16+k*4,4);a.stw(8,32+index*16+k*4,5)
jump(a,'pose_done')
# Mirror and exchange the left/right trajectory for native side 1.
a.label('right')
for j,index in enumerate((9,10,11,5,6,7)):
 for k in range(4):
  a.lwz(8,j*16+k*4,4)
  if k==0:a.emit(0x6D088000) # xoris r8,r8,0x8000: negate float sign
  a.stw(8,32+index*16+k*4,5)
a.label('pose_done');a.pointer(11,POSE);jump(a,'out')
a.label('clear');a.li(8,0)
for off in (4,0x18,0x1C,0x20,0x24,0x28):a.stw(8,off,7)
a.label('reset_visual');a.li(8,0);a.stw(8,8,7);a.stw(8,0xC,7);a.stw(8,0x10,7)
a.label('out')
for r in (4,5,6,7,10,12):a.lwz(r,0x20+(r-4)*4,1)
a.d(14,1,1,0x60)
# Return directly to the old skeleton-copy loop after its pointer setup.
main=bytes.fromhex(next(x['value'] for x in p['array'] if x['address']==0x825EB100))
from capstone import Cs,CS_ARCH_PPC,CS_MODE_32,CS_MODE_BIG_ENDIAN
cs=Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN)
sites=[i.address for i in cs.disasm(main[:0x800],0x825EB100) if i.mnemonic=='b' and i.op_str=='0x825eec00'];assert len(sites)==1
a.branch(sites[0]+8);code=a.finish();assert len(code)<0x800;add(ENTRY,code)
a=Assembler(0x825EEC00);a.branch(ENTRY);replace(a.address,a.finish(),0x100)

# Six native elbow/wrist/hand vectors per frame. Forward, recoil, settle.
# Author the trajectory here; it is not described as an extracted CPU clip.
base=[(-.32,.44,2.48),(-.24,.57,2.25),(-.22,.61,2.18),(.32,.44,2.48),(.24,.57,2.25),(.22,.61,2.18)]
extension=[(-.32,.49,2.43),(-.15,.78,2.12),(-.12,.83,2.04),*base[3:]]
windup=[(-.32,.49,2.43),(-.17,.76,2.21),(-.14,.80,2.17),*base[3:]]
frames=[]
for t in range(16):
 f=(0.,.12,.35,.70,1.,1.,.82,.60,.38,.20,.08,0.,0.,0.,0.,0.)[t]
 frames.append(b''.join(struct.pack('>4f',*(b+(e-b)*f for b,e in zip(v,w)),1.) for v,w in zip(base,extension)))
add(TABLE,b''.join(frames));add(CHARGE,b''.join(struct.pack('>4f',*v,1.) for v in windup))
charged=b''.join(b''.join(struct.pack('>4f',*(b+(e-b)*f for b,e in zip(v,w)),1.) for v,w in zip(windup,extension)) for f in (0.,.12,.35,.70,1.,1.))
assert CHARGED_TABLE+len(charged)<0x82670000;add(CHARGED_TABLE,charged)

# Contextual native action API; keep B/right fixes, far Y heavy and QTE maps.
sites=[i.address for i in cs.disasm(main[:0x800],0x825EB100) if i.mnemonic=='b' and i.op_str=='0x825ee600'];assert len(sites)==1
a=Assembler(0x825EE600);a.lwz(9,4,9);a.pointer(7,0x826492D8);a.lwz(7,0,7)
a.cmp(7,4);a.jump('close');a.cmp(7,6);a.jump('out',0x40820000)
a.cmp(4,2);a.jump('disabled')
for i in (3,6,7,8,10):a.cmp(4,i);a.jump('heavy')
jump(a,'free')
a.label('close')
a.cmp(4,2);a.jump('uppercut');a.cmp(4,3);a.jump('disabled')
for i in (5,6):a.cmp(4,i);a.jump('charge')
a.cmp(4,0);a.jump('release');jump(a,'free')
a.label('charge');a.li(8,0x10);a.li(9,0x20);a.pointer(7,STATE);a.lwz(7,0x24,7);a.cmp(7,0);a.jump('out');a.li(9,0x24);a.pointer(11,STATE);jump(a,'out')
a.label('release');a.pointer(7,STATE);a.lwz(7,0,7);a.cmp(7,0);a.jump('out');a.li(8,0x10);a.li(9,0x28);a.pointer(11,STATE);jump(a,'out')
a.label('free')
for i in (0x2A,0x2C):a.cmp(4,i);a.jump('disabled')
a.cmp(4,0xC);a.jump('guard');a.cmp(4,0x29);a.jump('right');jump(a,'out')
a.label('guard');a.li(8,0x20);a.li(9,0x20);jump(a,'out')
a.label('right');a.li(9,0x20);jump(a,'out')
a.label('uppercut');a.li(8,0x800);a.li(9,0x28);jump(a,'out')
a.label('heavy');a.li(8,0x10);a.li(9,0x20);jump(a,'out')
a.label('disabled');a.li(8,0)
a.label('out');a.li(7,0);a.branch(sites[0]+4);replace(a.address,a.finish(),0x200)

# Charge prompts now show Y close as well as far; normal X stays X.
for entry,original,guard,heavy,close in [(0x825EED00,0x821DB5D4,0xC,(3,6,7,8,10),(5,6)),(0x825EEE00,0x821DB660,9,(3,4,5,6),(3,4))]:
 a=Assembler(entry);mr(a,10,4);a.pointer(11,0x826492D8);a.lwz(11,0,11)
 a.cmp(11,4);a.jump('close');a.cmp(11,6);a.jump('original',0x40820000)
 a.cmp(4,guard);a.jump('guard')
 for i in heavy:a.cmp(4,i);a.jump('heavy')
 jump(a,'original');a.label('close');a.cmp(4,guard);a.jump('guard')
 a.cmp(4,2);a.jump('uppercut')
 if entry==0x825EED00:
  a.cmp(4,0);a.jump('close_indices',0x40820000);a.pointer(11,STATE);a.lwz(11,8,11);a.cmp(11,13);a.jump('heavy')
 a.label('close_indices')
 for i in close:a.cmp(4,i);a.jump('heavy')
 jump(a,'original');a.label('guard');a.li(4,2);jump(a,'mapped');a.label('uppercut');a.li(4,10);jump(a,'mapped');a.label('heavy');a.li(4,4)
 a.label('mapped');a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('fallback')
 mr(a,3,11);a.pointer(5,0x54583244);a.branch(0x823498A8)
 a.label('fallback');mr(a,4,10);a.label('original');a.branch(original);replace(entry,a.finish(),0x100)

p['name']='Gamepad feedback revision 17: Y charge/release and animated arms'
p['desc']='Near Y held charges and release punches; far Y remains heavy Ki. Accepted melee and shots use authored first-person arm trajectories with original character meshes. Compact pad prompts and native choice seals preserved.'
out=root/'experiments/gamepad-feedback-v17';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
target=out/'4E4D084E.gamepad-feedback.patch.toml';target.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='development: charge release and visual motion pending verification',
 animated_combat={'entry':hex(ENTRY),'trajectory_table':hex(TABLE),'charge_pose':hex(CHARGE),'dynamic_pose':hex(POSE),'state':hex(STATE),'native_states':[10,13,29,32],'frame_count':16,'animation_source':'Authored deterministic first-person joint trajectories; original native meshes, hand-pose clip and renderer. Not an extracted CPU action clip.','near_charge':'Y held; release extends the fist for five native frames, then sends one native punch with charge retained. Context/actor interruption cancels it.','near_uppercut':'RT edge','release_lead_in_frames':5})
m['step_guard']['charged_strike']=m['animated_combat']['near_charge']
m['animated_combat']['idle_ready_states']=[0,1,20]
m['animated_combat']['charged_punch_table']=hex(CHARGED_TABLE)
m['animated_combat']['charged_punch_frames']=6
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(target)
