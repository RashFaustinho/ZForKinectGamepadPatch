"""LOCAL ONLY: supply boss recognizer states before the Kinect logic call too."""
import struct
import tomllib
from pathlib import Path
from ppc_boss_input import build

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'experiments/diagnostic-boss-queries/4E4D084E.local-boss-query.patch.toml'
patch=tomllib.loads(source.read_text())['patch'][0]
entry=0x825ebd20
hook=0x8219554c
native=0x821b4bf8
def branch(a,t):return 0x48000000|((t-a)&0x3fffffc)
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert struct.unpack_from('>I',image,hook-0x82000000)[0]==branch(hook,native)|1
code=build(native,entry=entry)
assert not any(image[entry-0x82000000:entry-0x82000000+len(code)])
for a in patch['array']:
    lo=max(a['address'],entry);hi=min(a['address']+len(bytes.fromhex(a['value'])),entry+len(code))
    assert hi<=lo or not any(bytes.fromhex(a['value'])[lo-a['address']:hi-a['address']])
text=source.read_text()+f'\n[[patch.be32]]\naddress = 0x{hook:08X}\nvalue = 0x{branch(hook,entry)|1:08X}\n'
text+=f'\n[[patch.array]]\naddress = 0x{entry:08X}\nvalue = "{code.hex()}"\n'
out=ROOT/'experiments/diagnostic-boss-prelogic';out.mkdir(exist_ok=True)
(out/'4E4D084E.local-boss-prelogic.patch.toml').write_text(text)
print(out,len(code))
