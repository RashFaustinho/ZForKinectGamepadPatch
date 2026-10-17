"""Replace the static approach icon and the menu's localized hand label.

Uses native Xbox glyphs. The loaded Left Hand message becomes the B glyph in
RAM after checking its PBC resource name, size and UTF-16 BOM. No disc asset
is edited. Original UI updates and visibility rules still run.
"""
import hashlib,json,tomllib
from pathlib import Path
from ppc_emit import Assembler
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v6/4E4D084E.gamepad-feedback.patch.toml'
manifest=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['patch_sha256']
data=tomllib.loads(source.read_text());p=data['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
hook=0x82114DDC;entry=0x825ED000;name=0x825ED800
assert image[hook-0x82000000:hook-0x82000000+4]==bytes.fromhex('38210060')
assert not any(image[entry-0x82000000:entry-0x82000000+0x1000])
a=Assembler(entry)
# Keep the original function's frame and r31 (its UI object). Its saved LR
# remains at stack+58, so native calls may use LR before the original epilogue.
a.d(37,1,1,-0x80) # private frame: keep scratch beyond outgoing ABI argument slots
a.pointer(11,0x826490E0);a.lwz(11,0,11);a.cmp(11,0);a.jump('icon')
a.lwz(11,0x20,11);a.cmp(11,0);a.jump('icon')
for off,value in ((0,0x5354504B),(0xC80,0x5042435F),(0xC84,0x4B4E5F30)):
 a.lwz(9,off,11);a.pointer(10,value);a.emit(0x7C095000);a.jump('icon',0x40820000)
a.lwz(9,8,11);a.cmp(9,99);a.jump('icon',0x40820000)
a.lwz(9,0xC74,11);a.emit(0x28090006);a.jump('icon',0x41800000)
a.lwz(9,0xC70,11);a.emit(0x28090001);a.jump('icon',0x41800000)
a.emit(0x7D4B4A14) # add r10,r11,r9: original localized message address
a.d(40,9,10,0);a.emit(0x2809FFFE);a.jump('icon',0x40820000)
a.li(9,0xCB25);a.d(44,9,10,2);a.li(9,0);a.d(44,9,10,4)
a.label('icon')
a.lwz(11,0x14,31);a.cmp(11,0);a.jump('out')
a.lwz(3,4,31);a.cmp(3,0);a.jump('out')
a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('out')
a.pointer(4,name);a.branch(0x82115458,link=True)
a.cmp(3,0);a.jump('out');a.stw(3,0x60,1)
a.pointer(11,0x82649134);a.lwz(3,0,11);a.li(4,5);a.pointer(5,0x54583244);a.branch(0x823498A8,link=True)
a.cmp(3,0);a.jump('out');a.lwz(11,0x60,1);a.stw(3,0x24,11)
a.lwz(10,0x20,11);a.li(9,-5);a.emit(0x7D2A5038);a.ori(10,10,1);a.stw(10,0x20,11)
a.label('out');a.d(14,1,1,0x80);a.d(14,1,1,0x60);a.branch(hook+4)
code=a.finish();assert len(code)<=0x400
p['array'].append({'address':entry,'value':code.hex()});p['array'].append({'address':name,'value':b'p_jump_ico_000\0'.hex()})
b=Assembler(hook);b.branch(entry);p['be32'].append({'address':hook,'value':b.words[0]})
p['name']='Gamepad feedback revision 7: static and contextual Xbox prompts'
p['desc']='Revision 6 plus A on the approach HUD icon and the native B glyph instead of the menu hand label; original assets and UI visibility preserved.'
out=root/'experiments/gamepad-feedback-v7';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(data[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
manifest.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 status='development: static prompt additions require runtime validation',
 static_prompt_adapter={'hook':hex(hook),'entry':hex(entry),'bytes':len(code),'part_name':'p_jump_ico_000','texture':5,
   'menu_message':'PBC_KN_066','menu_glyph':'U+25CB -> native Xbox B texture','original_ui_frame_bytes':0x60})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(output)
