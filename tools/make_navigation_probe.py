"""Create a LOCAL selector-logging variant; never package it for players.

The only new writes record the selector pointer and its caller in private
scratch fields. It neither chooses menu items nor changes native battle data.
"""

import argparse, copy, hashlib, json
from pathlib import Path
from patch_format import read, serialize
from ppc_emit import Assembler

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--patch", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
d = copy.deepcopy(read(a.patch))
g = d["patch"][0]
m = json.loads((a.patch.parent / "manifest.json").read_text())
site = 0x8211A720
if m["region"] == "USA":
    site = int(
        json.loads((a.patch.parent / "address-map.json").read_text())["native_anchors"][
            hex(site)
        ]["target"],
        16,
    )
hook = next(x for x in g["be32"] if x["address"] == site)
disp = hook["value"] & 0x3FFFFFC
if disp & 0x2000000:
    disp -= 0x4000000
target = site + disp
entry = 0x825EB780
asm = Assembler(entry)
asm.pointer(11, 0x8266E180)
asm.stw(3, 0x38, 11)
asm.emit(0x7D2802A6)
asm.stw(9, 0x3C, 11)
asm.branch(target)
raw = asm.finish()
main = next(x for x in g["array"] if x["address"] == 0x825EB100)
blob = bytearray.fromhex(main["value"])
offset = entry - main["address"]
assert not any(blob[offset : offset + len(raw)])
blob[offset : offset + len(raw)] = raw
main["value"] = blob.hex()
asm = Assembler(site)
asm.branch(entry)
hook["value"] = asm.words[0]
g["name"] = "LOCAL navigation logger: " + g["name"]
a.output.mkdir(parents=True, exist_ok=False)
out = a.output / "4E4D084E.local-navigation.patch.toml"
out.write_text(serialize(d))
m.update(
    base_sha256=hashlib.sha256(a.patch.read_bytes()).hexdigest(),
    patch_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
    local_only=True,
)
m["status"] = (
    "LOCAL selector observer; gameplay validation belongs to the base public artifact"
)
if "validation" in m:
    m["validation_of_base_artifact"] = m.pop("validation")
(a.output / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print(out)
