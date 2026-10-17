"""Revision 16: separate the native defensive gate from rightward movement.

8220A250 polls 822A25A8 case 7 (gesture C) before the actual lateral gates
9/A (gestures 28/29, followed by D/E). Case 7 sets FP flag 2 and state 27;
with the former C=LS-right binding it steals every rightward request.
Use B for that defensive path in free combat and held right for gate 29.
Other contexts, charge controls, tracked poses and final UI layers survive.
"""
import hashlib,json,tomllib
from pathlib import Path
from ppc_emit import Assembler

root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v15/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]

def replace(address,code,limit):
 old=next(x for x in p['array'] if x['address']==address)
 assert len(code)<=limit
 for x in p['array']:
  if x is not old:assert address+len(code)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=address
 old['value']=code.hex()

main=bytes.fromhex(next(x['value'] for x in p['array'] if x['address']==0x825EB100))
from capstone import Cs,CS_ARCH_PPC,CS_MODE_32,CS_MODE_BIG_ENDIAN
sites=[i.address for i in Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN).disasm(main[:0x800],0x825EB100) if i.mnemonic=='b' and i.op_str=='0x825ee600']
assert len(sites)==1;resume=sites[0]+4
a=Assembler(0x825EE600);a.lwz(9,4,9);a.pointer(7,0x826492D8);a.lwz(7,0,7)
a.cmp(7,4);a.jump('close');a.cmp(7,6);a.jump('out',0x40820000)
a.cmp(4,2);a.jump('disabled')
for i in (3,6,7,8,10):a.cmp(4,i);a.jump('heavy')
a.jump('free',0x48000000)
# Gesture 3 belongs to the ordinary-strike dispatcher. Let held RT reach
# sustained gesture 6 instead of repeatedly firing an uncharged strike.
a.label('close');a.cmp(4,3);a.jump('disabled')
a.label('free')
for i in (0x2A,0x2C):a.cmp(4,i);a.jump('disabled')
a.cmp(4,0xC);a.jump('guard');a.cmp(4,0x29);a.jump('right');a.jump('out',0x48000000)
a.label('guard');a.li(8,0x20);a.li(9,0x20);a.jump('out',0x48000000)
a.label('right');a.li(9,0x20);a.jump('out',0x48000000)
a.label('heavy');a.li(8,0x10);a.li(9,0x20);a.jump('out',0x48000000)
a.label('disabled');a.li(8,0)
a.label('out');a.li(7,0);a.branch(resume);replace(a.address,a.finish(),0x200)

# These two icon getters share the same context rule as the input helper.
# Common slot 9 is the native C/SwayRight entry, not the right-step E entry.
for entry,original,guard,heavy in [(0x825EED00,0x821DB5D4,0xC,(3,6,7,8,10)),(0x825EEE00,0x821DB660,9,(3,4,5,6))]:
 a=Assembler(entry);a.emit(0x7C8A2378);a.pointer(11,0x826492D8);a.lwz(11,0,11)
 a.cmp(11,4);a.jump('normal');a.cmp(11,6);a.jump('original',0x40820000)
 a.label('normal');a.cmp(4,guard);a.jump('guard')
 a.cmp(11,6);a.jump('original',0x40820000)
 for i in heavy:a.cmp(4,i);a.jump('heavy')
 a.jump('original',0x48000000)
 a.label('guard');a.li(4,2);a.jump('mapped',0x48000000)
 a.label('heavy');a.li(4,4)
 a.label('mapped');a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('fallback')
 a.emit(0x7D635B78);a.pointer(5,0x54583244);a.branch(0x823498A8)
 # Restore the exact requested index if native pad resources are missing.
 a.label('fallback');a.emit(0x7D445378)
 a.label('original');a.branch(original);replace(entry,a.finish(),0x100)

# The live action-history HUD uses explicit UV endpoints, separately from
# the clash panels. Its original side argument mirrors the RT lettering.
# Replay its CR6 comparison for original art; loaded native pad resources
# instead take the original, unmirrored UV branch. No texture bytes change.
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
site=0x822DF944;entry=0x825EF600
assert image[site-0x82000000:site-0x82000000+4]==bytes.fromhex('2f1d0000')
assert not any(image[entry-0x82000000:entry-0x82000000+0x100])
a=Assembler(entry);a.lwz(11,0x24,3);a.pointer(4,0x82649134);a.lwz(4,0,4);a.cmp(4,0);a.jump('original')
a.lwz(5,0xD8,4);a.cmp(5,34);a.jump('original',0x40820000);a.lwz(4,0xDC,4);a.cmp(4,0);a.jump('original')
a.label('find');a.lwz(6,0,4);a.emit(0x7C065800);a.jump('pad');a.d(14,4,4,4);a.d(14,5,5,-1);a.cmp(5,0);a.jump('find',0x40820000)
a.label('original');a.emit(0x2F1D0000);a.branch(site+4)
a.label('pad');a.li(6,0);a.emit(0x2F060000);a.branch(site+4)
code=a.finish()
for x in p['array']:assert entry+len(code)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=entry
p['array'].append({'address':entry,'value':code.hex()});a=Assembler(site);a.branch(entry)
assert not any(x['address']==site for x in p['be32']);p['be32'].append({'address':site,'value':a.words[0]})

p['name']='Gamepad feedback revision 16: independent right step and B guard'
p['desc']='Revision 15 with independent B guard and held rightward step, matching B prompts, native RT charge before the X punch nearby, and readable unmirrored HUD button lettering.'
out=root/'experiments/gamepad-feedback-v16';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
target=out/'4E4D084E.gamepad-feedback.patch.toml';target.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='experimental: native steps, B guard, charged strike and readable Vulkan HUD confirmed',
 step_guard={'modes':[4,6],'native_priority_gate':'822A25A8 case 7 / gesture C','defense_button':'B held','right_step_gate':'29 held, E held','contextual_action_icon':{'C':'B'},'contextual_common_icon':{'9':'B'},'charged_strike':'Near mode 4 suppress ordinary strike gesture 3 so RT reaches native sustained charge 6; hold RT then punch X.','hud_uv':{'hook':hex(site),'helper':hex(entry),'policy':'Only loaded native pad resources use normal UV endpoints; original art retains the native side comparison.'}})
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(target)
