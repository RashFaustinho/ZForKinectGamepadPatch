"""LOCAL ONLY: count native prompt texture requests without changing textures.

Wraps the already patched getters with tail branches. Only volatile r9-r11
are used; r3-r8, LR, CTR and the render loop's nonvolatile registers survive.
The counters occupy verified unused alignment padding, never game objects.
"""
import argparse
import hashlib
import json
import struct
import tomllib
from pathlib import Path
from ppc_emit import Assembler

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,default=root/'experiments/diagnostic-boss-regression/4E4D084E.local-action-coordinates.patch.toml')
parser.add_argument('--out',type=Path,default=root/'experiments/diagnostic-prompts')
args=parser.parse_args();source=args.source
data=tomllib.loads(source.read_text());patch=data['patch'][0]
original=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(original).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
def available(address,size):
    return not any(original[address-0x82000000:address-0x82000000+size]) and all(
        address+size<=x['address'] or x['address']+len(bytes.fromhex(x['value']))<=address
        for x in patch['array'])
entry=next(a for a in (0x825EC000,0x825ED200) if available(a,0x600));scratch=0x8266E220
timestamp_entry=next(a for a in (0x825EC800,0x825EF700) if available(a,0x40))
assert not any(original[scratch-0x82000000:scratch-0x82000000+0xC0])
classes=[('action',0x822DE720),('common',0x822DAE40),('extra',0x822EBBB8),
         ('four_choices',0x822E4218),('four_responses',0x822E3AF8),('defender',0x822E0EEC)]
for kind,(name,hook) in enumerate(classes):
    old=next(x for x in patch['be32'] if x['address']==hook)
    displacement=old['value']&0x3FFFFFC
    if displacement&0x2000000:displacement-=0x4000000
    target=hook+displacement
    assert old['value']&0xFC000002==0x48000000
    a=Assembler(entry+kind*0x100)
    if kind<2:a.emit(0x7C892378) # mr r9,r4
    elif kind==2:
        a.lwz(9,0x24,3);a.lwz(10,0x10,3);a.emit(0x7D295214) # add r9,r9,r10
    elif kind==3:a.emit(0x7FC9F378) # mr r9,r30
    elif kind==4:a.d(8,9,28,8) # subfic r9,r28,8
    else:a.lwz(9,0x78,31)
    a.emit(0x28090042);a.jump('out',0x41810000)
    block=scratch+kind*0x20
    a.pointer(11,block);a.stw(9,0,11)
    a.pointer(10,0x8266E184);a.lwz(10,0,10);a.stw(10,4,11)
    a.stw(3,8,11);a.emit(0x7D4802A6);a.stw(10,12,11) # mflr r10
    a.emit(0x552AD97E);a.emit(0x554A103A) # srwi r10,r9,5; slwi r10,r10,2
    a.d(14,11,11,16);a.emit(0x7D6B5214) # add r11,r11,r10
    a.andi(9,9,31);a.li(10,1);a.emit(0x7D4A4830) # slw r10,r10,r9
    a.lwz(9,0,11);a.emit(0x7D4A4B78);a.stw(10,0,11)
    a.label('out');a.branch(target)
    code=a.finish();assert len(code)<=0x100
    patch['array'].append({'address':a.address,'value':code.hex()})
    b=Assembler(hook);b.branch(a.address,link=bool(old['value']&1));old['value']=b.words[0]
# Only data-section alignment padding may receive counters. Xenia protects
# executable pages: a zero-filled code cave is suitable for instructions,
# but cannot be assumed writable by a guest store.
patch['array'].append({'address':scratch,'value':bytes(0xC0).hex()})
# Per-action timestamps avoid losing an accepted contextual response when
# another accepted alias is polled later in the same frame.
timestamps=scratch+0xC0;assert not any(original[timestamps-0x82000000:timestamps-0x82000000+67*4])
accepted=next(x for x in patch['array'] if x['address']==0x825EB7A0)
old=bytes.fromhex(accepted['value']);assert old[:4]==bytes.fromhex('28040042')
a=Assembler(timestamp_entry);a.emit(0x28040042);a.jump('out',0x41810000)
a.pointer(11,timestamps);a.emit(0x5489103A);a.pointer(10,0x8266E184);a.lwz(10,0,10);a.emit(0x7D4B492E)
a.label('out');a.emit(0x28040042);a.branch(0x825EB7A4)
patch['array'].append({'address':a.address,'value':a.finish().hex()})
b=Assembler(0x825EB7A0);b.branch(a.address);accepted['value']=(b.finish()+old[4:]).hex()
patch['array'].append({'address':timestamps,'value':bytes(67*4).hex()})
patch['name']='LOCAL diagnostic: unchanged native prompt textures with request counters'
out=args.out;out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(data[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(patch[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in patch['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in patch['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.local-prompts.patch.toml';output.write_text(text)
(out/'manifest.json').write_text(json.dumps({'local_only':True,'base_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'patch_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'classes':{name:hex(scratch+i*0x20) for i,(name,_) in enumerate(classes)},
    'accepted_action_frames':hex(timestamps),
    'wrapper_entry':hex(entry),'timestamp_entry':hex(timestamp_entry),
    'scope':__doc__.strip()},indent=2)+'\n')
print(output)
