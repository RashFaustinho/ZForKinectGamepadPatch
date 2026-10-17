"""Revision 19: preserve the native choice to remove a power-up card.

Preserve revision 18's defense rendering and v17 arm trajectories. Stop the
all-content initializer from forcing the active-card flag on every main-menu
entry, align the scripted guard consumer with B, and time synthesized Super
follow-ups against the native recognizer's earliest-valid frames.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from ppc_emit import Assembler
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v18/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
x=next(x for x in p['array'] if x['address']==0x82302508);raw=bytes.fromhex(x['value'])
assert raw.count(bytes.fromhex('61090005'))==1
offset=raw.index(bytes.fromhex('61090005'));x['value']=raw.replace(bytes.fromhex('61090005'),bytes.fromhex('61090001')).hex()
# The camera's two follow-up gestures have native earliest-valid frames.
# A constantly asserted pad window otherwise registers both gestures early,
# making the original recognizer reject the shot. Delay only the synthesized
# follow-up bits until each native lower bound; never write its result/state.
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
main=next(x for x in p['array'] if x['address']==0x825EB100);raw=bytearray.fromhex(main['value'])
pattern=bytes.fromhex('3d608267812be1ac');assert raw.count(pattern)==1
site=0x825EB100+raw.index(pattern);entry=0x825EFD00
a=Assembler(entry);a.emit(0x3D608267);a.emit(0x812BE1AC)
a.pointer(11,0x826492D8);a.lwz(11,0,11);a.cmp(11,10);a.jump('out',0x40820000)
a.pointer(11,0x826491D8);a.lwz(11,0,11);a.cmp(11,0);a.jump('out');a.lwz(11,0x460,11);a.cmp(11,0);a.jump('out')
a.lwz(7,0,11);a.cmp(7,2);a.jump('first');a.cmp(7,3);a.jump('out',0x40820000)
a.lwz(0,0x40,11);a.jump('compare',0x48000000)
a.label('first');a.lwz(0,0x3C,11)
a.label('compare');a.lwz(7,0x10,11);a.emit(0x7C070040);a.jump('out',0x40800000);a.li(9,0)
a.label('out');a.li(7,0);a.branch(site+8);code=a.finish()
assert len(code)<=0x200 and not any(image[entry-0x82000000:entry-0x82000000+len(code)])
for r in p['array']:assert entry+len(code)<=r['address'] or r['address']+len(bytes.fromhex(r['value']))<=entry
p['array'].append({'address':entry,'value':code.hex()})
a=Assembler(site);a.branch(entry);off=site-0x825EB100;raw[off:off+8]=a.finish()+bytes.fromhex('60000000');main['value']=raw.hex()
# Scripted/tutored Super defenses use a second native guard consumer.
# Keep its input consistent with the same B texture and the normal consumer.
scripted_guard=0x8225C098
assert image[scripted_guard-0x82000000:scripted_guard-0x82000000+12]==bytes.fromhex('3880000c806b91d84bf3b079')
assert not any(r['address']==scripted_guard for r in p['be32'])
p['be32'].append({'address':scripted_guard,'value':0x3880002C})
p['name']='Gamepad feedback revision 19: Super defense and optional power-up cards'
p['desc']='Compact opponent Super-defense prompts, native-timed pad Super follow-ups, revision 17 combat and arms. Preserve active/inactive power-up choice instead of re-equipping Shield at the main menu.'
out=root/'experiments/gamepad-feedback-v19';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
target=out/'4E4D084E.gamepad-feedback.patch.toml';target.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='development: optional power-up persistence requires native verification')
m['powerup_selection']={'change_address':hex(0x82302508+offset),'before':'ori r9,r8,5','after':'ori r9,r8,1','preserves':'Existing active flag and all six native selected-item slots; native removal can stay saved.','removal':'Native Options menu; no bonus, damage or result text is hidden artificially.'}
m['super_followup_timing']={'hook':hex(site),'entry':hex(entry),'bytes':len(code),'scope':'Synthesized follow-up bits in mode 10 only. The original recognizer waits for its +3C / +40 earliest-valid frame and computes its own result.','writes':'No recognizer, battle phase, HP, Ki or animation fields.'}
m['super_defense']['guard_queries']=[m['super_defense']['guard_query'],hex(scripted_guard)]
m.pop('runtime_report',None)
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(target)
