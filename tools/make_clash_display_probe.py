"""LOCAL UI fixture: request the native Super-mash panel's show animation.

Only tutorial course 5, selected existing group 4 / lesson 118 is affected.
The public native widget update still performs all animation and icon drawing.
This fixture writes the UI show-request field +28 only. It does not create a
real Super clash, force its result, or change actors, combat phases, Ki or HP.
"""

import argparse, hashlib, json
from pathlib import Path
from patch_format import read, serialize, effective_bytes
from ppc_emit import Assembler

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
d = read(a.source)
patch = d["patch"][0]
hook = next(x for x in patch["be32"] if x["address"] == 0x822F0F80)
offset = hook["value"] & 0x3FFFFFC
offset -= 0x4000000 if offset & 0x2000000 else 0
target = hook["address"] + offset
entry = 0x825EFA80
x = Assembler(entry)
x.pointer(11, 0x8264933C)
x.lwz(11, 0, 11)
x.cmp(11, 0)
x.jump("out")
for off, value in ((0, 5), (0xD0, 4), (0x2C, 118)):
    x.lwz(9, off, 11)
    x.cmp(9, value)
    x.jump("out", 0x40820000)
x.lwz(9, 0x48, 3)
x.cmp(9, 0)
x.jump("out")
x.lwz(9, 0x40, 3)
x.cmp(9, 0)
x.jump("out", 0x40820000)
x.lwz(9, 0x28, 3)
x.cmp(9, 0)
x.jump("out", 0x40820000)
x.li(9, 1)
x.stw(9, 0x28, 3)
x.label("out")
x.branch(target)
raw = x.finish()
memory = effective_bytes(d)
assert entry + len(raw) <= 0x825EFBE0 and not any(
    entry + i in memory for i in range(len(raw))
)
image = Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin").read_bytes()
assert not any(image[entry - 0x82000000 : entry - 0x82000000 + len(raw)])
patch["array"].append({"address": entry, "value": raw.hex()})
x = Assembler(hook["address"])
x.branch(entry)
hook["value"] = x.words[0]
patch["name"] = "LOCAL UI DISPLAY ONLY: Super mash panel and current glyphs"
a.out.mkdir(parents=True, exist_ok=False)
out = a.out / "4E4D084E.local-clash-display.patch.toml"
out.write_text(serialize(d))
(a.out / "manifest.json").write_text(
    json.dumps(
        {
            "scope": __doc__,
            "input_sha256": hashlib.sha256(a.source.read_bytes()).hexdigest(),
            "patch_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "UI_show_request_only": True,
            "entry": hex(entry),
            "bytes": len(raw),
            "hook": hex(hook["address"]),
        },
        indent=2,
    )
    + "\n"
)
print(out)
