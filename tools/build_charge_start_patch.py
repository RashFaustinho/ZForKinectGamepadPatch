"""Give native charge preparation its required discrete hand-start event.

822A4138 selects the hand from gesture 5 (close) or 7 (ranged). Binding only
the sustained intensity gestures 6/A to RT leaves side +2538 at -1, so the
original follow-up punch can never be queried. Keep X and add the RT edge to
these two start events. No animation, charge amount or phase is forced.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v8/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
main=next(x for x in p['array'] if x['address']==0x825EB100);raw=bytearray.fromhex(main['value']);old=bytes(raw)
for i in (5,7):
 assert struct.unpack_from('>II',raw,0xA00+i*8)==(0x80,0x28)
 struct.pack_into('>II',raw,0xA00+i*8,0x880,0x28)
assert sum(x!=y for x,y in zip(old,raw))==2
main['value']=raw.hex()
p['name']='Gamepad feedback revision 9: HD prompts and native charged strikes'
p['desc']='Revision 8 plus the discrete RT hand-start events needed by the original close and ranged charged-strike handlers; X remains the follow-up punch.'
out=root/'experiments/gamepad-feedback-v9';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 status='development: charged-strike hand selection requires runtime validation',
 charge_start={'native_consumer':'0x822a4138','gestures':[5,7],'mask':'0x880','source':'pad pressed +28',
 'behavior':'RT initializes the native hand on charge entry; X is retained for the original punch event'})
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(output)
