"""LOCAL ONLY: log the last action query other than global super-prep polls."""
import struct
import tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'experiments/diagnostic-stage-access/4E4D084E.local-stage-probe.patch.toml'
patch=tomllib.loads(source.read_text())['patch'][0]
payload=bytes.fromhex(patch['array'][0]['value'])
offset=payload.index(bytes.fromhex('38e0000028040042'))
common=patch['array'][0]['address']+offset
entry=0x825ebf80
def branch(a,t):return 0x48000000|((t-a)&0x3fffffc)
# r4 is the query ID. Keep r3, r4, r5, r6 and LR intact.
words=[0x2c04002d,0x41820014,0x2c040031,0x4182000c,
       0x3d608267,0x908be1b8,0x38e00000,branch(entry+28,common+4)]
# scratch base is 82670000; E1B8 is a signed displacement.
words[5]=0x908be1b8
code=b''.join(struct.pack('>I',w) for w in words)
assert not any(payload[entry-0x825eb100:entry-0x825eb100+len(code)])
replacement=payload[:offset]+struct.pack('>I',branch(common,entry))+payload[offset+4:]
text=source.read_text().replace(payload.hex(),replacement.hex(),1)
text+=f'\n[[patch.array]]\naddress = 0x{entry:08X}\nvalue = "{code.hex()}"\n'
out=ROOT/'experiments/diagnostic-boss-queries';out.mkdir(exist_ok=True)
(out/'4E4D084E.local-boss-query.patch.toml').write_text(text)
print(out,hex(common))
