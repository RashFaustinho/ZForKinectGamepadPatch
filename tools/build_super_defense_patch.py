"""Revision 18: compact pad prompts for every native Super-defense variant.

The defender's three widgets bypass the action/common icon getters. Keep
their native eligibility, timing, Ki costs and animations; replace their
texture after the original update, then apply the existing final panel pass.
Player Super preparation pictures remain original.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from capstone import Cs,CS_ARCH_PPC,CS_MODE_32,CS_MODE_BIG_ENDIAN
from ppc_emit import Assembler

root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v17/4E4D084E.gamepad-feedback.patch.toml'
expected='3e8233d23a1ec5a4f986b65c22507e15ae5e96a7950a8b8ed1ab838023a83ab0'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
m=json.loads((source.parent/'manifest.json').read_text())
d=tomllib.loads(source.read_text());p=d['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
def add(address,raw):
 assert not any(image[address-0x82000000:address-0x82000000+len(raw)])
 for x in p['array']:assert address+len(raw)<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=address
 p['array'].append({'address':address,'value':raw.hex()})
def hook(address,target):
 assert not any(x['address']==address for x in p['be32'])
 a=Assembler(address);a.branch(target);p['be32'].append({'address':address,'value':a.words[0]})
def jump(a,label):a.jump(label,0x48000000)
def mr(a,d,s):a.emit(0x7C000378|(s<<21)|(d<<16)|(s<<11))

# These are the actual native RS slots, not repurposed glyphs. Verify the
# private original SPR's resource names and its 16 KiB storage allocations.
spr=Path('/workspace/artifacts/zforkinect/analysis/ui-boot-decoded/7.bin').read_bytes()[0x800:0x1800]
assert b'16_sys_r3_up.png\0' in spr and b'17_sys_r3_dn.png\0' in spr
assets=root/'assets/controller-defense';am=json.loads((assets/'manifest.json').read_text());blob=(assets/'buttons.lz4').read_bytes()
assert hashlib.sha256(blob).hexdigest()==am['sha256']
assert am['width']==am['height']==128 and am['content_scale']==.55 and len(am['textures'])==13
address=0x826BB800;assert address+len(blob)<=0x826C0000
old=next(x for x in p['array'] if x['address']==address);old['value']=blob.hex()
assert not any(image[address-0x82000000:address-0x82000000+len(blob)])
records=[]
for t in am['textures']:records.extend((t['index'],address+t['offset'],t['packed_bytes']))
records.extend((0xffffffff,0,0));table=struct.pack('>'+str(len(records))+'I',*records)
assert 0x825ED840+len(table)<=0x825ED900
next(x for x in p['array'] if x['address']==0x825ED840)['value']=table.hex()

# Native layout: kind 0 counter, 1 evade, 2 guard. Counter type 1 selects
# one of three character techniques; types 2..4 use three other recognizers.
# The masks below are verified against the unchanged bridge binding table.
main=bytes.fromhex(next(x['value'] for x in p['array'] if x['address']==0x825EB100))
actions=[0x30,0x34,0x38,0x39,0x3C,0x3F]
for action in actions:
 mask,field=struct.unpack_from('>II',main,0xA00+action*8)
 assert (mask,field)==(0x20000 if action==0x30 else 0x10000,0x1000)
assert struct.unpack_from('>II',main,0xA00+0xD*8)==(0x4000,0x20)
assert struct.unpack_from('>II',main,0xA00+0x2C*8)==(0x20,0x20)

entry=0x825EF800;native=0x822EF2B0;trampoline=0x825EFBE0
assert image[native-0x82000000:native-0x82000000+4]==bytes.fromhex('7d8802a6')
a=Assembler(entry);a.d(37,1,1,-0x90);a.emit(0x7D8802A6);a.stw(12,0x84,1);a.stw(31,0x80,1);a.stw(3,0x78,1)
a.branch(trampoline,True)
a.lwz(11,0x78,1);a.lwz(9,0x34,11)
a.cmp(9,0);a.jump('counter');a.cmp(9,1);a.jump('evade');a.cmp(9,2);a.jump('out',0x40820000)
a.li(4,2);jump(a,'mapped')
a.label('evade');a.lwz(9,0x38,11);a.d(14,9,9,-1);a.emit(0x28090003);a.jump('out',0x41810000)
a.li(4,15);jump(a,'mapped')
a.label('counter');a.lwz(9,0x3C,11);a.d(14,9,9,-1);a.emit(0x28090003);a.jump('out',0x41810000)
a.li(4,16);a.cmp(9,0);a.jump('mapped',0x40820000)
a.lwz(9,0x4C,11);a.emit(0x28090002);a.jump('out',0x41810000);a.cmp(9,0);a.jump('mapped',0x40820000);a.li(4,17)
a.label('mapped');a.stw(4,0x74,1)
a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('out')
a.lwz(9,0xD8,11);a.cmp(9,34);a.jump('out',0x40820000)
a.lwz(9,0xDC,11);a.cmp(9,0);a.jump('out')
mr(a,3,11);a.pointer(5,0x54583244);a.branch(0x823498A8,True);a.cmp(3,0);a.jump('out');a.stw(3,0x70,1)
a.lwz(11,0x78,1);a.lwz(31,0x40,11);a.cmp(31,0);a.jump('out');a.lwz(3,4,31);a.cmp(3,0);a.jump('out')
a.pointer(4,0x820F15F4);a.branch(0x82115458,True);a.cmp(3,0);a.jump('out')
a.lwz(9,0x70,1);a.stw(9,0x24,3);a.lwz(9,0x20,3);a.li(10,-5);a.emit(0x7D295038);a.ori(9,9,1);a.stw(9,0x20,3)
a.branch(0x825EE100,True)
a.label('out');a.lwz(31,0x80,1);a.lwz(12,0x84,1);a.emit(0x7D8803A6);a.d(14,1,1,0x90);a.emit(0x4E800020)
code=a.finish();assert len(code)<=trampoline-entry;add(entry,code)
a=Assembler(trampoline);a.emit(0x7D8802A6);a.branch(native+4);add(trampoline,a.finish());hook(native,entry)

# Initial visibility setup runs after the first texture update. Clean up
# after that setup too, preventing a one-frame return of the old pose groups.
entry2=0x825EFC00;native2=0x822EF728;stub2=0x825EFCE0
assert image[native2-0x82000000:native2-0x82000000+4]==bytes.fromhex('7d8802a6')
a=Assembler(entry2);a.d(37,1,1,-0x90);a.emit(0x7D8802A6);a.stw(12,0x84,1);a.stw(31,0x80,1);a.stw(3,0x78,1)
a.branch(stub2,True);a.lwz(11,0x78,1);a.lwz(31,0x40,11);a.cmp(31,0);a.jump('out');a.branch(0x825EE100,True)
a.label('out');a.lwz(31,0x80,1);a.lwz(12,0x84,1);a.emit(0x7D8803A6);a.d(14,1,1,0x90);a.emit(0x4E800020)
add(entry2,a.finish());a=Assembler(stub2);a.emit(0x7D8802A6);a.branch(native2+4);add(stub2,a.finish());hook(native2,entry2)

# Use the existing B-held recognizer for this exact Super-defense guard
# query. The original generic C is also a right sway in other contexts;
# remapping that generic action globally would break those contexts again.
cs=Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN)
ins=list(cs.disasm(image[0x252E18:0x2534F8],0x82252E18))
sites=[i.address for i,j,k in zip(ins,ins[1:],ins[2:]) if i.mnemonic=='li' and i.op_str=='r4, 0xc' and j.mnemonic=='lwz' and j.op_str=='r3, -0x6e28(r11)' and k.mnemonic=='bl' and k.op_str=='0x82197118']
assert len(sites)==1
guard_site=sites[0];assert not any(x['address']==guard_site for x in p['be32'])
p['be32'].append({'address':guard_site,'value':0x3880002C})

p['name']='Gamepad feedback revision 18: opponent Super defense prompts'
p['desc']='Revision 17 combat and arms, plus compact pad prompts for all native Super-defense selector variants. B guards, LS-left evades, RS up/down counters follow the actual technique. Original player Super poses retained.'
out=root/'experiments/gamepad-feedback-v18';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
target=out/'4E4D084E.gamepad-feedback.patch.toml';target.write_text(text)
m.update(input_sha256=expected,patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='development: Super-defense UI requires CPU and runtime verification')
m['super_defense']={'native_texture_update':hex(native),'wrapper':hex(entry),'bytes':len(code),'visibility_wrapper':hex(entry2),'native_visibility_setup':hex(native2),'guard_query':hex(guard_site),'guard_action':hex(0x2C),'counter_actions':actions,'counter_textures':[17,16,16,16,16,16],'evade_types':[1,2,3,4],'evade_texture':15,'guard_texture':2,'scope':'Native defender widgets only; player Super preparation art and all v17 combat payloads preserved.'}
m['hd_prompt_adapter'].update(assets='assets/controller-defense',source_sha256=am['sha256'],source_regions=[[hex(address),hex(address+len(blob))]],textures=am['textures'])
m.pop('runtime_report',None)
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(target)
