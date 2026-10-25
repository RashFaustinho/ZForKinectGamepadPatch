"""Build 1.1.1 from frozen 1.1.0 with separately owned 256 px face textures.

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
SOURCE = ROOT / "experiments/gamepad-v1.1.0-europe/4E4D084E.gamepad.patch.toml"
SOURCE_SHA = "b96c0f8355a851985e6643d9c0da4ec88f85b2c464a1ca0ac7ddb2185070210a"
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
    a.pointer(4, 0x10000)
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
    a.stw(7, 0x6C, 1)
    a.pointer(5, 0x10000)
    a.emit(0x7CA72A14)  # add r5,r7,r5
    a.lwz(0, 0x74, 1)
    a.emit(0x7C0803A6)  # mtlr r0
    a.lwz(12, 0x60, 1)
    label("source")
    a.lwz(6, 4, 12)
    a.branch(0x825EDA10)
    label("allocation_failed")
    a.lwz(0, 0x74, 1)
    a.emit(0x7C0803A6)
    jump("cleanup")

    label("commit")
    face_or("small")
    a.li(3, 0xAA)
    a.stw(3, 0, 8)
    a.lwz(3, 0x6C, 1)
    a.stw(3, 4, 8)
    a.pointer(3, 0x10000)
    a.stw(3, 0xC, 8)
    a.li(3, 256)
    a.d(44, 3, 8, 0x10)
    a.d(44, 3, 8, 0x12)
    a.pointer(3, 0x18000000)
    a.stw(3, 0x20, 8)
    a.pointer(3, 0x02000002)
    a.stw(3, 0x54, 9)
    a.lwz(3, 0x6C, 1)
    a.ori(3, 3, 20)
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
    memory = effective_bytes(doc)
    assert not any(ENTRY + i in memory for i in range(len(code)))
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
    assets = ROOT / "assets/controller-hd256"
    manifest = json.loads((assets / "manifest.json").read_text())
    blob = (assets / "buttons.lz4").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == manifest["sha256"]
    p["array"] = [x for x in p["array"] if x["address"] != 0x826BB800]
    capacities = [end - start for start, end in SOURCE_REGIONS]
    groups = [[] for _ in capacities]
    textures = sorted(manifest["textures"], key=lambda t: -t["packed_bytes"])

    def pack(index):
        if index == len(textures):
            return True
        t = textures[index]
        for i in range(len(capacities)):
            if capacities[i] >= t["packed_bytes"]:
                capacities[i] -= t["packed_bytes"]
                groups[i].append(t)
                if pack(index + 1):
                    return True
                groups[i].pop()
                capacities[i] += t["packed_bytes"]
        return False

    assert pack(0), "Independent compressed textures do not fit verified padding"
    locations = {}
    for (start, end), group in zip(SOURCE_REGIONS, groups):
        raw = bytearray()
        for t in group:
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
    # An explicit tucked guard: elbows down at the torso, both fists raised
    # near the head, less forward reach than the strike/shot trajectories.
    # Only the B pose changes. Shoulder/root/legs and the native guard gates
    # remain identical, as do normal X and charged Y motion tables.
    guard_joints = {
        5: (-0.27, 0.40, 2.50),
        6: (-0.15, 0.79, 2.36),
        7: (-0.12, 0.84, 2.33),
        9: (0.27, 0.40, 2.50),
        10: (0.15, 0.79, 2.36),
        11: (0.12, 0.84, 2.33),
    }
    for index, xyz in guard_joints.items():
        replace(0x825EE800 + 32 + index * 16, struct.pack(">4f", *xyz, 1.0))
    p["name"] = "Gamepad conversion 1.1.1 (Europe)"
    p["desc"] = (
        "Explicit tucked B guard and compact 256 px face buttons with native-owned physical storage; preserves alternating X attacks and gamepad controls."
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
        version="1.1.1",
        status="candidate: guard and glyph validation pending",
        input_sha256=SOURCE_SHA,
        patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        validation_report="docs/update-1.1.1.md",
        records=len(p["be32"]) + len(p["array"]),
    )
    m["hd_prompt_adapter"].update(
        assets="assets/controller-hd256",
        source_sha256=manifest["sha256"],
        textures=manifest["textures"],
        source_regions=[[hex(start), hex(end)] for start, end in SOURCE_REGIONS],
        face_dimensions=[256, 256],
        face_decoded_bytes=65536,
        writes="Four separately allocated native-owned 64 KiB physical face buffers; nine checked existing 16 KiB buffers; matching resource metadata and fetch headers; private stack scratch only.",
        face_allocation="Native physical texture pool 826494A0; allocator 823791D8; 4096 alignment; ownership bit 8; destructor 82358A98",
        allocation_helpers={k: hex(v) for k, v in labels.items()},
    )
    m["guard_pose"] = {
        "address": "0x825ee800",
        "joints": guard_joints,
        "policy": "B selects the full guard before cosmetic X/Y motion; symmetric fists near face, tucked elbows; native guard acceptance, timing and gameplay unchanged.",
    }
    previous = output / "manifest.json"
    if previous.exists():
        old = json.loads(previous.read_text())
        if (
            old.get("patch_sha256") == m["patch_sha256"]
            and old.get("validation", {}).get("version") == "1.1.1"
        ):
            for key in ("status", "validation"):
                m[key] = old[key]
    (output / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(target, "helper bytes", len(code))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "experiments/gamepad-v1.1.1-europe"
    )
    build(parser.parse_args().output)
