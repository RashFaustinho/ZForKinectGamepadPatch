"""Select the same normal/alternate pose catalog as native 8211CE50.

Battle resource flag 8000 chooses a second 21-pose catalog. The Great Ape
uses this catalog: its slot 14 is approach (A), not the normal catalog's
charged punch (RT). Preserve the RT override for camera QTE types 6/7.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from ppc_emit import Assembler
root=Path(__file__).resolve().parents[1];source=root/'experiments/gamepad-feedback-v9/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0];image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
regs={};stack={};relative={}
for w, in struct.iter_unpack('>I',image[0x11CE50:0x11CF90]):
 op=w>>26;rt=(w>>21)&31;ra=(w>>16)&31;imm=w&65535
 if op==14 and ra==0:regs[rt]=imm
 elif op==14 and ra==1:relative[rt]=imm;regs.pop(rt,None)
 elif op==36 and rt in regs and (ra==1 or ra in relative):stack[imm+(relative.get(ra,0) if ra!=1 else 0)]=regs[rt]
 elif op in (14,15,32):regs.pop(rt,None);relative.pop(rt,None)
catalog=[stack[0xB0+i*4] for i in range(21)]
assert catalog==[0x14,0x15,0x16,0x17,0x18,0x19,0x1A,0x1B,0x1C,0,1,2,3,0x26,0x27,0xD,0xE,0xF,0x10,0,0]
indices=[m['button_texture_by_action'][i] for i in catalog];assert 255 not in indices
entry=0x825EDC00;table=0x825EDF00;assert not any(image[entry-0x82000000:table-0x82000000+21])
a=Assembler(entry)
# Keep the original camera-QTE guard, but route its normal fallback through
# the catalog selector. It uses volatile r9/r11 and leaves the widget in r3.
old=next(x for x in p['array'] if x['address']==0x825EBD40)
guard=bytes.fromhex(old['value']);assert len(guard)==100
a.words=list(struct.unpack('>25I',guard[:-4]+bytes(4)))
# Relocate local conditional branches unchanged; replace absolute branches.
for i,w in enumerate(a.words):
 if w>>26==18:
  off=w&0x3FFFFFC
  if off&0x2000000:off-=0x4000000
  target=0x825EBD40+i*4+off
  a.words[i]=0x48000000|((target-(entry+i*4))&0x3FFFFFC)
# The last instruction now falls through to the catalog selector.
a.words.pop()
a.pointer(11,0x82649108);a.lwz(11,0,11);a.cmp(11,0);a.jump('normal')
a.lwz(11,0x2C,11);a.cmp(11,0);a.jump('normal')
a.lwz(11,0xC,11);a.andi(11,11,0x8000);a.jump('normal')
a.lwz(11,0x24,3);a.lwz(9,0x10,3);a.emit(0x7C8B4A14)
a.emit(0x28040014);a.jump('normal',0x41810000)
a.pointer(11,table);a.emit(0x7D2B20AE)
a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('normal')
a.emit(0x7D635B78);a.emit(0x7D244B78);a.pointer(5,0x54583244);a.branch(0x823498A8)
a.label('normal');a.branch(0x825EB600)
code=a.finish();assert entry+len(code)<=table
p['array'] += [{'address':entry,'value':code.hex()},{'address':table,'value':bytes(indices).hex()}]
hook=next(x for x in p['be32'] if x['address']==0x822EBBB8);b=Assembler(hook['address']);b.branch(entry);hook['value']=b.words[0]
p['name']='Gamepad feedback revision 10: HD buttons and both native QTE catalogs'
p['desc']='Revision 9 plus correct buttons for the alternate native pose catalog, including Great Ape approach prompts; camera QTEs keep RT.'
out=root/'experiments/gamepad-feedback-v10';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 status='development: alternate catalog and HD prompts require final runtime validation',
 alternate_pose_catalog={'entry':hex(entry),'bytes':len(code),'table':hex(table),'native_actions':catalog,'texture_indices':indices,
 'native_selector':'82649108 -> +2C -> +C & 8000','source':'8211CE50 constant initialization'})
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(output)
