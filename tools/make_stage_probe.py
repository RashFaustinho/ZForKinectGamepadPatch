"""Build a LOCAL diagnostic patch granting access to five Saiyan story stages.

This is not a distributable gamepad patch. It preserves the gamepad payload,
adds a separate startup hook, and sets only the unlock bit in the transient
story progress table. Never use it with a valuable profile or package it.
"""
import hashlib
import json
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'experiments/gamepad-layout-v2/4E4D084E.virtual-player.patch.toml'
image = Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
patch = tomllib.loads(source.read_text())
stub = 0x825EB600
if any(image[stub-0x82000000:stub-0x82000000+128]):
    raise SystemExit('Diagnostic code cave is not empty')
payload = bytes.fromhex(patch['patch'][0]['array'][0]['value'])
if any(payload[stub-0x825EB100:stub-0x825EB100+128]):
    raise SystemExit('Diagnostic stub overlaps the gamepad payload')
def branch(a, b): return 0x48000000 | ((b-a) & 0x3fffffc)
words = [0x3d608265, 0x816b920c, 0x2c0b0000, 0x4182004c,
         0x816b0000, 0x2c0b0000, 0x41820040]
for i in range(5):
    offset = 0x28 + i*0x94
    words += [0x812b0000|offset, 0x61290001, 0x912b0000|offset]
original = patch['patch'][0]['be32'][0]['value']
hook_delta=original&0x3fffffc
if hook_delta&0x2000000:hook_delta-=0x4000000
words += [branch(stub+len(words)*4, 0x82195550+hook_delta)]
# Fix both null checks from their actual instruction positions.
for i in (3,6): words[i] = 0x41820000 | ((len(words)-1-i)*4)
text = source.read_text()
text = text.replace(f'value = 0x{original:08X}', f'value = 0x{branch(0x82195550,stub):08X}', 1)
text += f'\n[[patch.array]]\naddress = 0x{stub:08X}\nvalue = "'+b''.join(struct.pack('>I',w) for w in words).hex()+'"\n'
# Default the five-item stage selector to the fifth stage for headless tests.
# Other selectors and all battle logic continue through the gamepad routine.
selector_hook = next(p for p in patch['patch'][0]['be32'] if p['address']==0x8211A720)
instruction = selector_hook['value']
delta = instruction & 0x3fffffc
if delta & 0x2000000:delta-=0x4000000
selector_target = selector_hook['address']+delta
selection_stub = 0x825EB780
selection = [0x7d0802a6, 0x3d208230, 0x6129e6b8, 0x7c084840,
             0x41820010, 0x39290010, 0x7c084840, 0x40820018,
             0x81230004, 0x2c090005, 0x4082000c, 0x39200004, 0x91230034]
# LR identifies the two calls from the STORY STAGE selector (8230E420).
# A five-item main menu must not be redirected into a different game mode.
selection += [branch(selection_stub+len(selection)*4,selector_target)]
if any(payload[selection_stub-0x825EB100:selection_stub-0x825EB100+len(selection)*4]):
    raise SystemExit('Stage selection stub overlaps gamepad code')
text=text.replace(f'value = 0x{instruction:08X}',f'value = 0x{branch(selector_hook["address"],selection_stub):08X}',1)
text += f'\n[[patch.array]]\naddress = 0x{selection_stub:08X}\nvalue = "'+b''.join(struct.pack('>I',w) for w in selection).hex()+'"\n'
out = ROOT/'experiments/diagnostic-stage-access'
out.mkdir(exist_ok=True)
(out/'4E4D084E.local-stage-probe.patch.toml').write_text(text)
(out/'manifest.json').write_text(json.dumps({'purpose':'LOCAL TEST ONLY: transient stage access; never distribute',
 'base_patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'stage_flags':[hex(0x28+i*0x94) for i in range(5)]},indent=2)+'\n')
print(out)
