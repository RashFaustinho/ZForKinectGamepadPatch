"""Use RT for the boss QTEs whose separate camera flags are supplied by RT.

Normal prompts and type-5 gesture sequences retain their individual buttons.
Only type 6/7, opening/active, in the Great Ape actor context override a pose.
"""
import hashlib,json,tomllib
from pathlib import Path
from ppc_emit import Assembler
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v5/4E4D084E.gamepad-feedback.patch.toml'
manifest=json.loads((source.parent/'manifest.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['patch_sha256']
data=tomllib.loads(source.read_text());p=data['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
entry=0x825EBD40;assert not any(image[entry-0x82000000:entry-0x82000000+0x100])
a=Assembler(entry)
a.pointer(11,0x82649298);a.lwz(11,0,11);a.cmp(11,0);a.jump('normal')
a.lwz(11,0x54,11);a.cmp(11,0);a.jump('normal')
a.lwz(9,0xC,11);a.cmp(9,1);a.jump('normal',0x40820000)
a.lwz(11,0x2FD0,11);a.cmp(11,0);a.jump('normal')
a.lwz(9,4,11);a.d(14,9,9,-1);a.emit(0x28090001);a.jump('normal',0x41810000)
a.lwz(9,8,11);a.d(14,9,9,-6);a.emit(0x28090001);a.jump('normal',0x41810000)
a.li(4,3);a.branch(0x825EB60C) # existing extra slot 3 -> native RT glyph
a.label('normal');a.branch(0x825EB600)
code=a.finish();assert len(code)<=0x100
p['array'].append({'address':entry,'value':code.hex()})
hook=next(x for x in p['be32'] if x['address']==0x822EBBB8)
b=Assembler(hook['address']);b.branch(entry);hook['value']=b.words[0]
p['name']='Gamepad feedback revision 6: context-aware Xbox QTE prompts'
p['desc']='Revision 5 with RT shown for Great Ape camera-flag QTE types 6/7, preserving their native timing and success logic.'
out=root/'experiments/gamepad-feedback-v6';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(data[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
manifest.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
    status='development: context-aware boss prompt; native and visual validation separate',
    boss_extra_pose_override={'battle_kind':1,'qte_states':[1,2],'qte_types':[6,7],'texture_index':10,
                              'hook':hex(hook['address']),'guard':hex(entry),'guard_bytes':len(code)})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(output)
