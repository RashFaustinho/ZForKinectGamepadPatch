"""LOCAL ONLY: cycle gesture filters with D-pad Up; no runtime code writes.

Writes only a reserved diagnostic word. Filters actions 0/5/7 at the virtual
input query; all simulation, damage and animation remain native.
"""
import json
import tomllib
from pathlib import Path
from ppc_emit import Assembler

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'experiments/diagnostic-feedback/4E4D084E.local-feedback-probe.patch.toml'
patch=tomllib.loads(source.read_text())['patch'][0]
hook=next(x for x in patch['be32'] if x['address']==0x82195550)
delta=hook['value']&0x3FFFFFC
if delta&0x2000000:delta-=0x4000000
target=hook['address']+delta
entry=0x825EBD40
main=next(x for x in patch['array'] if x['address']==0x825EB100)
payload=bytes.fromhex(main['value'])
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert not any(image[entry-0x82000000:entry-0x82000000+256])
a=Assembler(entry)
a.pointer(11,0x826490DC);a.lwz(11,0,11);a.cmp(11,0);a.jump('out')
a.lwz(11,0x98,11);a.cmp(11,0);a.jump('out');a.lwz(9,0x28,11)
a.andi(9,9,1);a.jump('out')
a.pointer(10,0x8266E1CC);a.lwz(8,0,10)
a.d(14,8,8,1);a.andi(8,8,3);a.stw(8,0,10)
a.label('out');a.branch(target)
code=a.finish();assert len(code)<=96
branch=Assembler(hook['address']);branch.branch(entry)
text=source.read_text().replace(f'value = 0x{hook["value"]:08X}',f'value = 0x{branch.words[0]:08X}',1)
text+=f'\n[[patch.array]]\naddress = 0x{entry:08X}\nvalue = "{code.hex()}"\n'
# The old logger branches to the first compare in the shared int/float query.
offset=payload.index(bytes.fromhex('28040042'))
common=main['address']+offset
filter_entry=0x825EBDA0
f=Assembler(filter_entry)
f.pointer(11,0x8266E1CC);f.lwz(9,0,11)
f.cmp(9,0);f.jump('out')
for action,mode in ((0,1),(5,2),(7,3)):
    f.cmp(4,action);f.jump(f'next_{action}',0x40820000)
    f.cmp(9,mode);f.jump('out');f.li(4,67);f.jump('out',0x48000000)
    f.label(f'next_{action}')
f.label('out');f.emit(0x28040042);f.branch(common+4)
filter_code=f.finish();assert len(filter_code)<=160
b=Assembler(common);b.branch(filter_entry)
changed=payload[:offset]+b.finish()+payload[offset+4:]
text=text.replace(payload.hex(),changed.hex(),1)
text+=f'\n[[patch.array]]\naddress = 0x{filter_entry:08X}\nvalue = "{filter_code.hex()}"\n'
out=ROOT/'experiments/diagnostic-input-layouts';out.mkdir(exist_ok=True)
(out/'4E4D084E.local-input-layouts.patch.toml').write_text(text)
(out/'manifest.json').write_text(json.dumps({'local_only':True,'modes':{'0':[0,5,7],'1':[0],'2':[5],'3':[7]},'frame_code_bytes':len(code),'filter_bytes':len(filter_code)},indent=2)+'\n')
print(out)
