"""Build 1.1.2 from frozen 1.1.1: RGBA8 faces and complete mash-panel cleanup.

Keep the compact drawing footprint and the accepted-action arm alternation.
The original bounded LZ4 decoder is reused; new physical buffers are obtained
from the game's texture pool, committed only on complete decode, and freed by
the original texture destructor (metadata ownership bit 8).
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from patch_format import read, serialize, effective_bytes
from ppc_emit import Assembler

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/gamepad-v1.1.1-europe/4E4D084E.gamepad.patch.toml"
SOURCE_SHA = "93cf01aa395fff1bd4a32ef6034a5036214169eeaad82f82b61c25007446eee0"
IMAGE = Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin")
ENTRY = 0x825EC580
SOURCE_REGIONS = (
    (0x826BB800, 0x826C0000),
    (0x8210EEA8, 0x82110000),
    (0x8266EC20, 0x82670000),
)


def build(output):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    image = IMAGE.read_bytes()
    assert (
        hashlib.sha256(image).hexdigest()
        == "72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b"
    )
    doc = read(SOURCE)
    p = doc["patch"][0]

    def replace(address, raw):
        for item in p["array"]:
            begin = item["address"]
            previous = bytes.fromhex(item["value"])
            offset = address - begin
            if 0 <= offset and offset + len(raw) <= len(previous):
                item["value"] = (
                    previous[:offset] + raw + previous[offset + len(raw) :]
                ).hex()
                return
        raise ValueError(f"Unknown replacement {address:X}")

    a = Assembler(ENTRY)
    labels = {}

    def label(name):
        labels[name] = a.address + len(a.words) * 4
        a.label(name)

    def jump(name):
        a.jump(name, 0x48000000)

    def face_or(name):
        a.lwz(3, 0, 12)
        a.d(14, 3, 3, -2)
        a.emit(0x28030003)  # cmplwi r3,3
        a.jump(name, 0x41810000)

    label("init")
    a.li(0, 0)
    a.stw(0, 0x70, 1)
    a.stw(12, 0x60, 1)
    a.branch(0x825ED934)

    label("allocate")
    face_or("source")
    a.emit(0x7C0802A6)  # mflr r0
    a.stw(0, 0x74, 1)
    a.pointer(3, 0x826494A0)
    a.lwz(3, 0, 3)
    a.cmp(3, 0)
    a.jump("allocation_failed")
    a.pointer(4, 0x40000)
    a.li(5, 0x1000)
    a.li(6, 1)  # Same physical pool/alignment/direction as native texture creation.
    a.branch(0x823791D8, True)
    a.cmp(3, 0)
    a.jump("allocation_failed")
    a.stw(3, 0x70, 1)
    a.lwz(7, 0x10, 3)
    a.cmp(7, 0)
    a.jump("allocation_failed")
    a.andi(0, 7, 0xFFF)
    a.jump("allocation_failed", 0x40820000)
    a.pointer(5, 0x30000)
    a.emit(0x7CE72A14)  # add r7,r7,r5: decode indices into the final quarter
    a.stw(7, 0x6C, 1)
    a.pointer(5, 0x10000)
    a.emit(0x7CA72A14)  # add r5,r7,r5
    a.lwz(0, 0x74, 1)
    a.emit(0x7C0803A6)  # mtlr r0
    a.lwz(12, 0x60, 1)
    label("source")
    a.lwz(6, 4, 12)
    a.lwz(3, 8, 12)
    a.lwz(4, 0, 12)
    a.d(14, 4, 4, -2)
    a.emit(0x28040003)
    a.jump("source_ready", 0x41810000)
    a.d(14, 6, 6, 512)
    a.d(14, 3, 3, -512)
    label("source_ready")
    a.branch(0x825EDA14)
    label("allocation_failed")
    a.lwz(0, 0x74, 1)
    a.emit(0x7C0803A6)
    jump("cleanup")

    label("commit")
    face_or("small")
    a.lwz(4, 0x70, 1)
    a.lwz(4, 0x10, 4)
    a.lwz(5, 0x6C, 1)
    a.lwz(6, 4, 12)
    a.pointer(3, 0x10000)
    a.emit(0x7C6903A6)  # mtctr r3
    label("expand")
    a.d(34, 7, 5, 0)
    a.emit(0x2807007F)  # cmplwi r7,127; all lookups stay in the palette
    a.jump("cleanup", 0x41810000)
    a.emit(0x54E7103A)  # slwi r7,r7,2
    a.emit(0x7D46382E)  # lwzx r10,r6,r7
    a.stw(10, 0, 4)
    a.d(14, 5, 5, 1)
    a.d(14, 4, 4, 4)
    a.jump("expand", 0x42000000)
    a.li(3, 0xAA)
    a.stw(3, 0, 8)
    a.lwz(3, 0x70, 1)
    a.lwz(3, 0x10, 3)
    a.stw(3, 4, 8)
    a.pointer(3, 0x40000)
    a.stw(3, 0xC, 8)
    a.li(3, 256)
    a.d(44, 3, 8, 0x10)
    a.d(44, 3, 8, 0x12)
    a.li(3, 0)
    a.stw(3, 0x20, 8)
    a.pointer(3, 0x02000002)
    a.stw(3, 0x54, 9)
    a.lwz(3, 0x70, 1)
    a.lwz(3, 0x10, 3)
    a.ori(3, 3, 6)
    a.stw(3, 0x58, 9)
    a.pointer(3, 0x001FE0FF)
    a.stw(3, 0x5C, 9)
    a.pointer(3, 0x01280D10)
    a.stw(3, 0x60, 9)
    a.li(3, 0)
    a.stw(3, 0x70, 1)  # Ownership now belongs to the native resource.
    jump("cleanup")
    label("small")
    a.li(3, 128)
    a.branch(0x825EDB40)

    label("cleanup")
    a.lwz(4, 0x70, 1)
    a.cmp(4, 0)
    a.jump("next")
    a.emit(0x7C0802A6)
    a.stw(0, 0x74, 1)
    a.pointer(3, 0x826494A0)
    a.lwz(3, 0, 3)
    a.branch(0x823794B8, True)
    a.lwz(0, 0x74, 1)
    a.emit(0x7C0803A6)
    label("next")
    a.lwz(12, 0x60, 1)
    a.branch(0x825EDB84)
    code = a.finish()
    assert ENTRY + len(code) <= 0x825EC800
    assert not any(image[ENTRY - 0x82000000 : ENTRY - 0x82000000 + len(code)])
    p["array"] = [x for x in p["array"] if x["address"] != ENTRY]
    p["array"].append({"address": ENTRY, "value": code.hex()})
    for site, name in [
        (0x825ED930, "init"),
        (0x825EDA0C, "allocate"),
        (0x825EDB3C, "commit"),
        (0x825EDB80, "cleanup"),
    ]:
        hook = Assembler(site)
        hook.branch(labels[name])
        replace(site, hook.finish())
    assets = ROOT / "assets/controller-rgba"
    manifest = json.loads((assets / "manifest.json").read_text())
    blob = (assets / "buttons.lz4").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == manifest["sha256"]
    p["array"] = [
        x
        for x in p["array"]
        if x["address"] not in {0x826BB800, 0x8210EEA8, 0x8266EC20}
    ]
    capacities = [end - start for start, end in SOURCE_REGIONS]
    groups = [[] for _ in capacities]
    textures = sorted(manifest["textures"], key=lambda t: -t["packed_bytes"])

    def pack(index):
        if index == len(textures):
            return True
        t = textures[index]
        cost = (
            (t["packed_bytes"] + 3) & ~3
            if t.get("gpu_format") == 6
            else t["packed_bytes"]
        )
        for i in range(len(capacities)):
            if capacities[i] >= cost:
                capacities[i] -= cost
                groups[i].append(t)
                if pack(index + 1):
                    return True
                groups[i].pop()
                capacities[i] += cost
        return False

    assert pack(0), "Independent compressed textures do not fit verified padding"
    locations = {}
    for (start, end), group in zip(SOURCE_REGIONS, groups):
        raw = bytearray()
        for t in group:
            if t.get("gpu_format") == 6:
                raw.extend(bytes((-len(raw)) % 4))
            locations[t["index"]] = start + len(raw)
            raw.extend(blob[t["offset"] : t["offset"] + t["packed_bytes"]])
        assert start + len(raw) <= end
        assert not any(image[start - 0x82000000 : start - 0x82000000 + len(raw)])
        memory = effective_bytes(doc)
        assert not any(start + i in memory for i in range(len(raw)))
        p["array"].append({"address": start, "value": raw.hex()})
    records = []
    for t in manifest["textures"]:
        records.extend((t["index"], locations[t["index"]], t["packed_bytes"]))
    records.extend((0xFFFFFFFF, 0, 0))
    replace(0x825ED840, struct.pack(">" + str(len(records)) + "I", *records))
    # Assign the mash glyph without the original Kinect-loader count/ready
    # condition, then hide the old pose groups after complete native updates.
    meter = 0x825ED700
    a = Assembler(meter)
    a.d(37, 1, 1, -0x90)
    a.emit(0x7D8802A6)
    a.stw(12, 0x84, 1)
    a.stw(31, 0x80, 1)
    a.stw(3, 0x78, 1)
    a.pointer(11, 0x82649134)
    a.lwz(11, 0, 11)
    a.cmp(11, 0)
    a.jump("out")
    a.lwz(9, 0xD8, 11)
    a.cmp(9, 34)
    a.jump("out", 0x40820000)
    a.lwz(9, 0xDC, 11)
    a.cmp(9, 0)
    a.jump("out")
    a.emit(0x7D635B78)
    a.li(4, 3)
    a.pointer(5, 0x54583244)
    a.branch(0x823498A8, True)
    a.cmp(3, 0)
    a.jump("out")
    a.stw(3, 0x74, 1)
    a.lwz(11, 0x78, 1)
    a.lwz(31, 0x34, 11)
    a.cmp(31, 0)
    a.jump("out")
    a.lwz(3, 4, 31)
    a.cmp(3, 0)
    a.jump("out")
    a.pointer(4, 0x820F15F4)
    a.branch(0x82115458, True)
    a.cmp(3, 0)
    a.jump("out")
    a.lwz(9, 0x74, 1)
    a.stw(9, 0x24, 3)
    a.lwz(9, 0x20, 3)
    a.li(10, -5)
    a.emit(0x7D295038)
    a.ori(9, 9, 1)
    a.stw(9, 0x20, 3)
    a.branch(0x825EE100, True)
    a.label("out")
    a.lwz(31, 0x80, 1)
    a.lwz(12, 0x84, 1)
    a.emit(0x7D8803A6)
    a.d(14, 1, 1, 0x90)
    a.emit(0x4E800020)
    meter_code = a.finish()
    assert len(meter_code) <= 0x100

    def add(address, raw):
        memory = effective_bytes(doc)
        assert not any(address + i in memory for i in range(len(raw)))
        assert not any(image[address - 0x82000000 : address - 0x82000000 + len(raw)])
        p["array"].append({"address": address, "value": raw.hex()})

    add(meter, meter_code)
    wrappers = []
    for entry, native, trampoline, existing in [
        (0x825EF300, 0x822EE188, 0x825EF3E0, True),
        *[
            (0x825EDCE0 + i * 0x80, n, 0x825EDCE0 + i * 0x80 + 0x70, False)
            for i, n in enumerate((0x822EDCA0, 0x822DFF20, 0x822E03D8, 0x822EE270))
        ],
        (0x825EF940, 0x822F1608, 0x825EF9B0, False),
        (0x825EF9C0, 0x822F0F80, 0x825EFA30, False),
    ]:
        assert image[native - 0x82000000 : native - 0x82000000 + 4] == bytes.fromhex(
            "7d8802a6"
        )
        a = Assembler(entry)
        a.d(37, 1, 1, -0x90)
        a.emit(0x7D8802A6)
        a.stw(12, 0x84, 1)
        a.stw(31, 0x80, 1)
        a.stw(3, 0x78, 1)
        a.branch(trampoline, True)
        a.lwz(3, 0x78, 1)
        a.branch(meter, True)
        a.lwz(31, 0x80, 1)
        a.lwz(12, 0x84, 1)
        a.emit(0x7D8803A6)
        a.d(14, 1, 1, 0x90)
        a.emit(0x4E800020)
        raw = a.finish()
        assert entry + len(raw) < trampoline
        if existing:
            old = next(x for x in p["array"] if x["address"] == entry)
            old["value"] = raw.hex()
        else:
            add(entry, raw)
            a = Assembler(trampoline)
            a.emit(0x7D8802A6)
            a.branch(native + 4)
            add(trampoline, a.finish())
            a = Assembler(native)
            a.branch(entry)
            assert not any(x["address"] == native for x in p["be32"])
            p["be32"].append({"address": native, "value": a.words[0]})
        wrappers.append(
            {
                "native": hex(native),
                "wrapper": hex(entry),
                "trampoline": hex(trampoline),
            }
        )
    p["name"] = "Gamepad conversion 1.1.2 (Europe)"
    p["desc"] = (
        "Clean RGBA8 face-button contours and X prompts throughout native mash/clash panels; preserves the validated guard and alternating attacks."
    )
    output.mkdir(parents=True, exist_ok=True)
    target = output / SOURCE.name
    text = serialize(doc)
    if target.exists() and target.read_text() != text:
        raise FileExistsError(
            "Different candidate exists; select a new output directory"
        )
    target.write_text(text)
    m = json.loads((SOURCE.parent / "manifest.json").read_text())
    m.pop("validation", None)
    m.update(
        version="1.1.2",
        status="candidate: guard and glyph validation pending",
        input_sha256=SOURCE_SHA,
        patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        validation_report="docs/update-1.1.2.md",
        records=len(p["be32"]) + len(p["array"]),
    )
    m["hd_prompt_adapter"].update(
        assets="assets/controller-rgba",
        source_sha256=manifest["sha256"],
        textures=manifest["textures"],
        source_regions=[[hex(start), hex(end)] for start, end in SOURCE_REGIONS],
        face_dimensions=[256, 256],
        face_decoded_bytes=262144,
        format="RGBA8 faces (native format 6); unchanged BC3 for nine other textures",
        writes="Four separately allocated native-owned 256 KiB physical face buffers; nine checked existing 16 KiB buffers; matching resource metadata and fetch headers; private stack scratch only.",
        face_allocation="Native physical texture pool 826494A0; allocator 823791D8; 4096 alignment; ownership bit 8; destructor 82358A98",
        allocation_helpers={k: hex(v) for k, v in labels.items()},
    )
    m["clash_prompt"] = {
        "helper": hex(meter),
        "bytes": len(meter_code),
        "wrappers": wrappers,
        "texture_index": 3,
        "policy": "Assign X independently of the legacy Kinect texture count, then apply shared pose/UV/seal cleanup after complete native strike/clash widget updates. No input, progress, OK/NG result or combat writes.",
    }
    previous = output / "manifest.json"
    if previous.exists():
        old = json.loads(previous.read_text())
        if (
            old.get("patch_sha256") == m["patch_sha256"]
            and old.get("validation", {}).get("version") == "1.1.2"
        ):
            for key in ("status", "validation"):
                m[key] = old[key]
    (output / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(target, "helper bytes", len(code))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "experiments/gamepad-v1.1.2-europe"
    )
    build(parser.parse_args().output)
