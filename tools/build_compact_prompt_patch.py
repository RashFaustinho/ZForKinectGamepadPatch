"""Use smaller, centered 128 px button artwork, keeping native panel layouts."""
import hashlib,json,struct,tomllib
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'experiments/gamepad-feedback-v11/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
assets=root/'assets/controller-small';am=json.loads((assets/'manifest.json').read_text());blob=(assets/'buttons.lz4').read_bytes()
assert am['width']==am['height']==128 and am['content_scale']==.55
assert hashlib.sha256(blob).hexdigest()==am['sha256']
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes();address=0x826BB800
assert address+len(blob)<=0x826C0000 and not any(image[address-0x82000000:address-0x82000000+len(blob)])
records=[]
for t in am['textures']:records.extend((t['index'],address+t['offset'],t['packed_bytes']))
records.extend((0xffffffff,0,0));table=struct.pack('>'+str(len(records))+'I',*records)
record=next(x for x in p['array'] if x['address']==0x825ED840);assert len(bytes.fromhex(record['value']))==len(table);record['value']=table.hex()
p['array']=[x for x in p['array'] if not (0x826BB800<=x['address']<0x826C0000 or 0x8210F000<=x['address']<0x82110000)]
p['array'].append({'address':address,'value':blob.hex()})
p['name']='Gamepad feedback revision 13: compact Xbox prompts'
p['desc']='Revision 11 gameplay and both native pose catalogs, with smaller centered controller artwork and transparent space inside the original panels.'
out=root/'experiments/gamepad-feedback-v13';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 status='experimental: compact icons verified in Vulkan; native boss completion and save verified; see runtime-checks.json for coverage')
m.pop('only_changed_guest_offsets',None) # Historical v5 delta, not a v13 change list.
m['static_prompt_adapter']['menu_glyph']='Plain UTF-16LE B in native text style'
m['boss_extra_pose_override'].update(guard='0x825edc00',guard_bytes=m['alternate_pose_catalog']['bytes'])
m['hd_prompt_adapter'].update(assets='assets/controller-small',content_scale=.55,source_sha256=am['sha256'],
 source_regions=[[hex(address),hex(address+len(blob))]],textures=am['textures'])
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(output)
