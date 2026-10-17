"""Revision 15: finish panel changes after the native pose animation pass.

The native callers enable pose groups after their UI update call. Wrapping
their complete texture-update functions avoids those later writes undoing the
generic UI epilogue pass. Inputs and skeletons are byte-identical to v14.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from ppc_emit import Assembler
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v14/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
def add(address,raw):
 assert not any(image[address-0x82000000:address-0x82000000+len(raw)])
 for x in p['array']:assert address+len(raw)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=address
 p['array'].append({'address':address,'value':raw.hex()})
def branch(address,target,link=False):
 a=Assembler(address);a.branch(target,link);return a.finish()
def hook(address,target):
 assert not any(x['address']==address for x in p['be32'])
 p['be32'].append({'address':address,'value':int.from_bytes(branch(address,target),'big')})
# The shared bounded pass now returns to its caller. Preserve the old UI
# epilogue chain through an explicit caller, rather than falling through it.
ui=next(x for x in p['array'] if x['address']==0x825EE100);raw=bytearray.fromhex(ui['value'])
assert raw[-4:]==branch(0x825EE100+len(raw)-4,0x825ED000)
raw[-4:]=bytes.fromhex('4e800020');ui['value']=raw.hex()
a=Assembler(0x825EE500);a.d(37,1,1,-0x80);a.emit(0x7D8802A6);a.stw(12,0x70,1)
a.branch(0x825EE100,True);a.lwz(12,0x70,1);a.emit(0x7D8803A6);a.d(14,1,1,0x80);a.branch(0x825ED000);add(a.address,a.finish())
hd=next(x for x in p['array'] if x['address']==0x825ED900);raw=bytearray.fromhex(hd['value'])
raw[-4:]=branch(0x825ED900+len(raw)-4,0x825EE500);hd['value']=raw.hex()

# The attack meter accepts any ordinary strike. X is the unambiguous prompt;
# its native animation used to rotate through four Kinect punch pictures.
site=0x822EE1D4
# Locate the verified native factory call inside this small function.
calls=[]
for address in range(0x822EE188,0x822EE270,4):
 if image[address-0x82000000:address-0x82000000+4]==branch(address,0x823498A8,True):calls.append(address)
assert len(calls)==1;site=calls[0]
a=Assembler(0x825EE0C0);a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('original')
a.emit(0x7D635B78);a.li(4,3);a.pointer(5,0x54583244);a.branch(0x823498A8)
a.label('original');a.li(4,0);a.branch(0x823498A8);code=a.finish();assert len(code)<=0x40;add(a.address,code)
p['be32'].append({'address':site,'value':int.from_bytes(branch(site,0x825EE0C0,True),'big')})

wrappers=[]
for entry,native,count in [(0x825EF000,0x822EC8F8,2),(0x825EF100,0x822E4190,4),
                           (0x825EF200,0x822E3A88,4),(0x825EF300,0x822EE188,1)]:
 assert image[native-0x82000000:native-0x82000000+4]==bytes.fromhex('7d8802a6')
 trampoline=entry+0xE0
 a=Assembler(entry);a.d(37,1,1,-0x90);a.emit(0x7D8802A6);a.stw(12,0x84,1);a.stw(31,0x80,1);a.stw(3,0x78,1)
 a.branch(trampoline,True)
 for i in range(count):
  a.lwz(11,0x78,1);a.lwz(31,0x34+4*i,11);a.cmp(31,0);a.jump('next'+str(i))
  a.branch(0x825EE100,True);a.label('next'+str(i))
 a.lwz(31,0x80,1);a.lwz(12,0x84,1);a.emit(0x7D8803A6);a.d(14,1,1,0x90);a.emit(0x4E800020)
 code=a.finish();assert len(code)<=0xE0;add(entry,code)
 a=Assembler(trampoline);a.emit(0x7D8802A6);a.branch(native+4);add(trampoline,a.finish());hook(native,entry)
 wrappers.append({'native':hex(native),'wrapper':hex(entry),'panels':count})
p['name']='Gamepad feedback revision 15: final clash layers and contextual combat'
p['desc']='Revision 14 inputs and tracked poses, with Xbox prompts applied after native pose-group updates, native prohibition seals above buttons, and X on the approach attack meter.'
out=root/'experiments/gamepad-feedback-v15';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
target=out/'4E4D084E.gamepad-feedback.patch.toml';target.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='experimental: CPU checks and Vulkan contextual-panel capture passed',
 final_panel_pass={'wrappers':wrappers,'attack_meter_hook':hex(site),'attack_meter_texture':3,'shared_pass':'0x825ee100','hd_next_adapter':'0x825ee500'})
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(target)
