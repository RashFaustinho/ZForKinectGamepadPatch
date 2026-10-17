"""Complete all 21 extra prompt slots using the native resource catalog.

Produces revision 5 without overwriting the validated revision 4 or its reports.
Only two prompt lookup tables differ; input logic and game assets are identical.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='ec4d3c7ce5952369c7388874b9cbb0497b36e37903cfbf1dcb022048d1fbeff8'
data=tomllib.loads(source.read_text());patch=data['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
# Read the actual li/stw constant initialization in 8211CE50, rather than
# treating unknown pose-slot numbers or watcher names as input semantics.
registers={};stores={}
for word, in struct.iter_unpack('>I',image[0x11CE50:0x11CF90]):
 op=word>>26;rt=(word>>21)&31;ra=(word>>16)&31;imm=word&65535
 if op==14 and ra==0:registers[rt]=imm if imm<32768 else imm-65536
 elif op==36 and ra==1 and rt in registers:stores[imm]=registers[rt]
 elif op in (14,15,32):registers.pop(rt,None)
catalog=[stores[0x50+i*4] for i in range(21)]
assert catalog==[0x1E,0x1F,0x20,0x21,0x2A,0x2B,0x28,0x29,0x25,0x23,0x24,0,1,2,3,0x26,0x27,0xD,0xE,0xF,0x10]
manifest=json.loads((source.parent/'manifest.json').read_text())
action_map=manifest['button_texture_by_action'][:]
# The close sway accepts both LT and LS-left. Display LS-left consistently
# with the four-response panel; the defender's front response still shows LT.
action_map[0x28]=15
extra_map=[action_map[a] for a in catalog]
assert 255 not in extra_map
tuner=next(x for x in patch['array'] if x['address']==0x821DB5D0)
payload=bytearray.fromhex(tuner['value']);before=bytes(payload)
payload[0x250:0x250+67]=bytes(action_map)
payload[0x210:0x210+21]=bytes(extra_map) # 821DB7E0
assert all(a==b or i in {0x250+0x28,*range(0x210,0x225)} for i,(a,b) in enumerate(zip(before,payload)))
tuner['value']=payload.hex()
patch['name']='Gamepad feedback revision 5: complete extra Xbox prompt table'
patch['desc']='Revision 4 input and coordinate fixes; all 21 extra gesture widgets use their mapped Xbox buttons; Special poses preserved.'
out=root/'experiments/gamepad-feedback-v5';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(data[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(patch[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in patch['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in patch['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
manifest.update(status='development: completed native prompt table; visual coverage tracked separately',
    input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
    button_texture_by_action=action_map,extra_pose_texture_indices=extra_map,
    native_extra_pose_actions=catalog,native_catalog_function='8211CE50',
    native_catalog_prefix_sha256=hashlib.sha256(image[0x11CE50:0x11CF90]).hexdigest(),
    only_changed_guest_offsets=[hex(0x821DB5D0+i) for i,(a,b) in enumerate(zip(before,payload)) if a!=b])
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(output)
