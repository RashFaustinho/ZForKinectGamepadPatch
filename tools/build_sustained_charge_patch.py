"""Keep native charge-hand selection valid when RT was already held on entry.

The native start events 5/7 belong to the drawn-back arm, not to the follow-up
punch. They must read held RT; the punch remains edge-triggered X (event 0).
This also lets the tutorial show RT for Smash Charge and X for Smash Punch.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'experiments/gamepad-feedback-v10/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
main=next(x for x in p['array'] if x['address']==0x825EB100);raw=bytearray.fromhex(main['value'])
for i in (5,7):
 assert struct.unpack_from('>II',raw,0xA00+i*8)==(0x880,0x28)
 struct.pack_into('>II',raw,0xA00+i*8,0x800,0x20);m['button_texture_by_action'][i]=10
main['value']=raw.hex()
tuner=next(x for x in p['array'] if x['address']==0x821DB5D0);raw=bytearray.fromhex(tuner['value'])
for i in (5,7):raw[0x250+i]=10
for i in (4,5):raw[0x2A0+i]=10
tuner['value']=raw.hex()
p['name']='Gamepad feedback revision 11: sustained native charge preparation'
p['desc']='Revision 10 with RT held for native arm preparation, X for the follow-up punch, and matching tutorial prompts.'
out=root/'experiments/gamepad-feedback-v11';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 charge_start={'native_consumer':'0x822a4138','gestures':[5,7],'mask':'0x800','source':'pad held +20',
 'behavior':'Hold RT to draw the arm back; punch with X. Hand selection also works when RT was already held.'},
 status='development: sustained charge requires native runtime regression')
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(output)
