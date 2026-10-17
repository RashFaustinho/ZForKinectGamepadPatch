"""LOCAL ONLY: record the active selector pointer and its caller, read-only probes.

The guest logger records the selector and three input caller/frame pairs in
reserved diagnostic padding. It does not select menu items or alter the battle. Never distribute this diagnostic variant.
"""
import hashlib
import json
import tomllib
from pathlib import Path
from ppc_emit import Assembler

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml'
data = tomllib.loads(source.read_text())['patch'][0]
hook = next(x for x in data['be32'] if x['address'] == 0x8211A720)
delta = hook['value'] & 0x3FFFFFC
if delta & 0x2000000: delta -= 0x4000000
target = hook['address'] + delta
entry = 0x825EB780
for item in data['array']:
    value = bytes.fromhex(item['value']); start = item['address']
    if start <= entry < start+len(value):
        assert not any(value[entry-start:entry-start+32])
a = Assembler(entry)
a.pointer(11,0x8266E180);a.stw(3,0x38,11)
a.emit(0x7d2802a6);a.stw(9,0x3C,11);a.branch(target)
b = Assembler(hook['address']);b.branch(entry)
text = source.read_text().replace(f'value = 0x{hook["value"]:08X}',f'value = 0x{b.words[0]:08X}',1)
text += f'\n[[patch.array]]\naddress = 0x{entry:08X}\nvalue = "{a.finish().hex()}"\n'
# Capture callers of the inputs under investigation. This sits inside the
# disabled Tuner update body; the three pairs use unused diagnostic padding.
main = next(x for x in data['array'] if x['address'] == 0x825EB100)
payload = bytes.fromhex(main['value'])
offset = payload.index(bytes.fromhex('38e0000028040042'))
common = main['address']+offset
logger = 0x821DB88C
a = Assembler(logger)
for i, action in enumerate((0,0xD,0x26)):
    a.cmp(4,action);a.jump(f'next_{i}',0x40820000)
    a.pointer(11,0x8266E180);a.emit(0x7d2802a6)
    a.stw(9,0x50+i*8,11);a.lwz(9,4,11);a.stw(9,0x54+i*8,11)
    a.jump('out',0x48000000);a.label(f'next_{i}')
a.label('out');a.li(7,0);a.branch(common+4)
assert logger+len(a.words)*4 <= 0x821DB930
branch = Assembler(common);branch.branch(logger)
replaced = payload[:offset]+branch.finish()+payload[offset+4:]
text = text.replace(payload.hex(),replaced.hex(),1)
text += f'\n[[patch.array]]\naddress = 0x{logger:08X}\nvalue = "{a.finish().hex()}"\n'
out = ROOT/'experiments/diagnostic-feedback'
out.mkdir(exist_ok=True)
(out/'4E4D084E.local-feedback-probe.patch.toml').write_text(text)
(out/'manifest.json').write_text(json.dumps({'local_only':True,'base_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2)+'\n')
print(out)
