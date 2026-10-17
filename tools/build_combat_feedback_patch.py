"""Revision 14: contextual heavy-shot input, tracked arm poses and clash UI.

Changes are startup guest patches. Disc assets and game outcomes are untouched.
The UI pass only handles parts whose texture is a loaded native pad resource.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from ppc_emit import Assembler

root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v13/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
def add(a,raw):
 assert not any(image[a-0x82000000:a-0x82000000+len(raw)])
 for x in p['array']:
  assert a+len(raw)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=a,(hex(a),hex(x['address']))
 p['array'].append({'address':a,'value':raw.hex()})
def hook(a,target,link=False):
 b=Assembler(a);b.branch(target,link)
 assert not any(x['address']==a for x in p['be32'])
 p['be32'].append({'address':a,'value':b.words[0]})
def jump(a,label):a.jump(label,0x48000000)
def mr(a,d,s):a.emit(0x7C000378|(s<<21)|(d<<16)|(s<<11))

# The two approach-clash panels bypass both existing icon getters.
for entry,site,choice in [(0x825EE000,0x822EC990,None),(0x825EE040,0x822ECA64,0),(0x825EE080,0x822ECB1C,1)]:
 assert image[site-0x82000000:site-0x82000000+4]==struct.pack('>I',0x48000001|((0x823498A8-site)&0x3fffffc))
 a=Assembler(entry)
 if choice is None:
  a.li(4,7);a.cmp(30,0);a.jump('chosen');a.li(4,9);a.label('chosen')
 else:a.li(4,(7,9)[choice])
 a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('original')
 mr(a,3,11);a.pointer(5,0x54583244);a.branch(0x823498A8)
 a.label('original');a.li(4,0);a.branch(0x823498A8)
 code=a.finish();assert len(code)<=0x40;add(entry,code);hook(site,entry,True)

# Post-update UI pass: remove the Kinect art behind mapped pad parts, then
# move the native seal's child record after the dummy icon's child record.
# Whole child records move together; node IDs, pointers and animation data stay
# attached. It runs after native animations have updated their visibility.
names=['i_pl_grp','p_ico_dummy_000','a_pl_attack_anm_grp','i_pl_attack',
       'a_pl_guard_anm_grp','i_pl_guard','i_ico_dummy_grp','i_pl_seal_anm_grp']
strings=bytearray();loc={}
for n in names:loc[n]=0x825EF500+len(strings);strings+=n.encode()+b'\0'
add(0x825EF500,bytes(strings))
a=Assembler(0x825EE100);a.d(37,1,1,-0x90);a.emit(0x7D8802A6);a.stw(12,0x84,1)
a.lwz(3,4,31);a.cmp(3,0);a.jump('out');a.pointer(4,loc['p_ico_dummy_000']);a.branch(0x82115458,True)
a.cmp(3,0);a.jump('out');a.stw(3,0x60,1);a.lwz(8,0x24,3)
a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('out')
a.lwz(9,0xD8,11);a.cmp(9,34);a.jump('out',0x40820000);a.lwz(11,0xDC,11);a.cmp(11,0);a.jump('out')
a.label('texture');a.lwz(10,0,11);a.emit(0x7C0A4000);a.jump('mapped');a.d(14,11,11,4);a.d(14,9,9,-1);a.cmp(9,0);a.jump('texture',0x40820000);jump(a,'out')
a.label('mapped')
a.lwz(3,4,31);a.pointer(4,loc['i_pl_grp']);a.branch(0x82115458,True);a.cmp(3,0);a.jump('out')
a.lwz(3,0xB8,3);a.cmp(3,0);a.jump('out');a.stw(3,0x64,1)
a.lwz(3,0x60,1);a.lwz(11,0x20,3);a.li(9,-5);a.emit(0x7D6B4838);a.stw(11,0x20,3)
for name in names[2:6]:
 a.lwz(3,0x64,1);a.pointer(4,loc[name]);a.branch(0x8211E910,True);a.cmp(3,0);a.jump('next_'+name)
 a.lwz(9,0xD0,3);a.li(10,-2);a.emit(0x7D295038);a.stw(9,0xD0,3);a.label('next_'+name)
a.lwz(3,0x64,1);a.pointer(4,loc['i_ico_dummy_grp']);a.branch(0x8211E910,True);a.cmp(3,0);a.jump('out');a.stw(3,0x68,1)
a.lwz(9,0xD0,3);a.ori(9,9,1);a.stw(9,0xD0,3)
a.lwz(3,0x64,1);a.pointer(4,loc['i_pl_seal_anm_grp']);a.branch(0x8211E910,True);a.cmp(3,0);a.jump('out');mr(a,7,3)
a.lwz(11,0x64,1);a.d(40,9,11,0xC);a.cmp(9,0);a.jump('out');a.emit(0x28090040);a.jump('out',0x41810000)
a.lwz(11,8,11);a.cmp(11,0);a.jump('out');a.li(6,0);a.li(5,0);a.lwz(8,0x68,1)
a.label('child');a.lwz(10,4,11);a.emit(0x7C0A4000);a.jump('not_dummy',0x40820000);mr(a,6,11)
a.label('not_dummy');a.emit(0x7C0A3800);a.jump('not_seal',0x40820000);mr(a,5,11)
a.label('not_seal');a.d(14,11,11,12);a.d(14,9,9,-1);a.cmp(9,0);a.jump('child',0x40820000)
a.cmp(5,0);a.jump('out');a.cmp(6,0);a.jump('out');a.emit(0x7C053040);a.jump('out',0x40800000)
# Swap the seal and dummy records so the native renderer visits the seal last.
for off in (0,4,8):a.lwz(9,off,5);a.lwz(10,off,6);a.stw(10,off,5);a.stw(9,off,6)
a.label('out');a.lwz(12,0x84,1);a.emit(0x7D8803A6);a.d(14,1,1,0x90);a.branch(0x825ED000)
code=a.finish();assert len(code)<0x500;add(a.address,code)
hd=next(x for x in p['array'] if x['address']==0x825ED900);raw=bytearray.fromhex(hd['value'])
b=Assembler(0x825ED900+len(raw)-4);b.branch(0x825EE100);raw[-4:]=b.finish();hd['value']=raw.hex()

# Context-dependent masks. r7 is the input result accumulator and remains zero
# on return. The original binding field load is replayed before selecting Y.
main=next(x for x in p['array'] if x['address']==0x825EB100);raw=bytearray.fromhex(main['value'])
off=raw.index(bytes.fromhex('8109000081290004'))+4;site=main['address']+off
a=Assembler(0x825EE600);a.lwz(9,4,9);a.pointer(7,0x826492D8);a.lwz(7,0,7)
a.cmp(7,4);a.jump('free');a.cmp(7,6);a.jump('out',0x40820000)
for i in (2,):a.cmp(4,i);a.jump('disabled')
for i in (3,6,7,8,10):a.cmp(4,i);a.jump('heavy')
a.label('free')
# These two recognizers are cinematic responses, not ordinary guard. Reading
# them while idle previously launched an unrelated close-range sequence.
for i in (0x2A,0x2C):a.cmp(4,i);a.jump('disabled')
jump(a,'out');a.label('heavy');a.li(8,0x10);a.li(9,0x20);jump(a,'out')
a.label('disabled');a.li(8,0);a.label('out');a.li(7,0);a.branch(site+4)
add(a.address,a.finish());b=Assembler(site);b.branch(a.address);raw[off:off+4]=b.finish()

# Keep high-resolution skeleton geometry meaningful during guard and heavy
# preparation. Neutral remains the default for all other inputs and scenes.
neutral=bytes.fromhex(next(x['value'] for x in p['array'] if x['address']==0x825EB100))[0x800:0x9C0]
for address,changes in [(0x825EE800,{5:(-.32,.49,2.43),6:(-.17,.76,2.21),7:(-.14,.80,2.17),9:(.32,.50,2.44),10:(.17,.75,2.22),11:(.14,.79,2.18)}),
                        (0x825EE9C0,{5:(-.32,.44,2.52),6:(-.19,.58,2.19),7:(-.17,.60,2.11)})]:
 pose=bytearray(neutral)
 for index,xyz in changes.items():struct.pack_into('>4f',pose,32+index*16,*xyz,1.)
 add(address,bytes(pose))
off=raw.index(bytes.fromhex('3d60825f396bb900'));site=main['address']+off
a=Assembler(0x825EEC00);a.pointer(11,0x825EB900)
a.pointer(9,0x826492D8);a.lwz(9,0,9);a.cmp(9,4);a.jump('normal');a.cmp(9,6);a.jump('out',0x40820000)
a.label('normal');a.pointer(9,0x826490DC);a.lwz(9,0,9);a.cmp(9,0);a.jump('out');a.lwz(9,0x98,9);a.cmp(9,0);a.jump('out');a.lwz(9,0x20,9)
a.andi(9,9,0x20);a.jump('shot');a.pointer(11,0x825EE800);jump(a,'out')
a.label('shot');a.pointer(9,0x826492D8);a.lwz(9,0,9);a.cmp(9,6);a.jump('out',0x40820000)
a.pointer(9,0x826490DC);a.lwz(9,0,9);a.lwz(9,0x98,9);a.lwz(9,0x20,9);a.andi(9,9,0x10);a.jump('out');a.pointer(11,0x825EE9C0)
a.label('out');a.branch(site+8)
add(a.address,a.finish());b=Assembler(site);b.branch(a.address);raw[off:off+8]=b.finish()+bytes.fromhex('60000000');main['value']=raw.hex()

# Icon getters follow the same ranged override, preserving every other map.
for entry,original,ids in [(0x825EED00,0x821DB5D4,(3,6,7,8,10)),(0x825EEE00,0x821DB660,(3,4,5,6))]:
 a=Assembler(entry);a.pointer(11,0x826492D8);a.lwz(11,0,11);a.cmp(11,6);a.jump('original',0x40820000)
 for i in ids:a.cmp(4,i);a.jump('heavy')
 jump(a,'original');a.label('heavy');a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('original');mr(a,3,11);a.li(4,4);a.pointer(5,0x54583244);a.branch(0x823498A8)
 a.label('original');a.branch(original);add(entry,a.finish())
 site=0x822DE720 if original==0x821DB5D4 else 0x822DAE40
 h=next(x for x in p['be32'] if x['address']==site);b=Assembler(site);b.branch(entry);h['value']=b.words[0]

p['name']='Gamepad feedback revision 14: guard, ranged Y and readable clash prompts'
p['desc']='Revision 13 compact art, contextual Y heavy shot, tracked guard/shot poses, missing approach buttons and native seal layering.'
out=root/'experiments/gamepad-feedback-v14';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
target=out/'4E4D084E.gamepad-feedback.patch.toml';target.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='development: native guard and UI regression pending',
 combat_feedback={'ranged_heavy_button':'Y held, mode6 only','approach_buttons':['LT','RB'],'guard':'tracked guard pose with B held; suppress free-fight cinematic guards','seal':'native seal and dummy child records reordered after UI update'})
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(target)
