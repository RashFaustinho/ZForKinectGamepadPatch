"""Build 1.1.0 from frozen 1.0.0: smoother face glyphs and native X arm sides.

Only normal X selects alternating sides. Native callers still accept actions,
choose their own states, create projectiles and apply damage. No actor fields
are written by these helpers. The reviewed 1.0.0 artifact is never overwritten.
"""

import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
from patch_format import effective_bytes, read, serialize
from ppc_emit import Assembler

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml"
BASE_SHA = "bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50"
IMAGE = Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin")
STATE = 0x8266EC00
PREPOSE = 0x825ED200
SIDE = 0x825ED400
FILTER = 0x825ED600
POSE_SIDE = 0x825ED680
ACCEPT_CALLERS = (0x822A4448, 0x822A465C)
LINEAR_FACE_FETCH = 0x01280D10  # linear min/mag, base mip, unchanged RGBA swizzle


def branch(a, label):
    a.jump(label, 0x48000000)


def cmpw(a, x, y):
    a.emit(0x7C000000 | (x << 16) | (y << 11))


def build(image_path=IMAGE, output=None):
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError("Frozen predecessor changed")
    image = image_path.read_bytes()
    if (
        hashlib.sha256(image).hexdigest()
        != "72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b"
    ):
        raise ValueError("Unsupported European image")
    doc = copy.deepcopy(read(BASE))
    p = doc["patch"][0]
    baseline = effective_bytes(doc)

    def replace(address, raw):
        for item in p["array"]:
            start = item["address"]
            old = bytes.fromhex(item["value"])
            if start <= address and address + len(raw) <= start + len(old):
                offset = address - start
                item["value"] = (old[:offset] + raw + old[offset + len(raw) :]).hex()
                return
        raise ValueError(
            f"Replacement is not contained in a known payload: {address:X}"
        )

    def add(address, raw):
        if any(image[address - 0x82000000 : address - 0x82000000 + len(raw)]) or any(
            address + i in effective_bytes(doc) for i in range(len(raw))
        ):
            raise ValueError("New payload overlaps original data or another patch")
        p["array"].append({"address": address, "value": raw.hex()})

    # This is writable image padding after the charged trajectory, before idata.
    assert not any(image[STATE - 0x82000000 : STATE - 0x82000000 + 20])
    assert not any(STATE + i in baseline for i in range(20))
    # Preserve all caller-owned pose arguments; only r8/r9/r11 are scratch here.
    a = Assembler(PREPOSE)
    a.pointer(11, 0x82649298)
    a.lwz(9, 0, 11)
    a.cmp(9, 0)
    a.jump("clear")
    a.lwz(9, 0x54, 9)
    a.cmp(9, 0)
    a.jump("clear")
    a.lwz(8, 0xC, 9)
    a.cmp(8, 0)
    a.jump("clear", 0x40820000)
    a.lwz(9, 0x2FC0, 9)
    a.cmp(9, 0)
    a.jump("clear")
    a.pointer(11, STATE)
    a.lwz(8, 0xC, 11)
    cmpw(a, 8, 9)
    a.jump("owner_ok")
    a.stw(9, 0xC, 11)
    a.li(8, 2)
    a.stw(8, 0, 11)
    a.stw(8, 4, 11)
    a.li(8, -1)
    a.stw(8, 8, 11)
    a.li(8, 0)
    a.stw(8, 0x10, 11)
    a.label("owner_ok")
    a.lwz(8, 0x2530, 9)
    a.cmp(8, 0)
    a.jump("keep_side")
    a.cmp(8, -1)
    a.jump("keep_side")
    a.li(8, 0)
    a.stw(8, 0x10, 11)
    a.label("keep_side")
    a.pointer(9, 0x826492D8)
    a.lwz(8, 0, 9)
    a.cmp(8, 4)
    a.jump("normal")
    a.cmp(8, 6)
    a.jump("out", 0x40820000)
    a.label("normal")
    a.pointer(9, 0x826490DC)
    a.lwz(9, 0, 9)
    a.cmp(9, 0)
    a.jump("out")
    a.lwz(9, 0x98, 9)
    a.cmp(9, 0)
    a.jump("out")
    a.lwz(8, 0x28, 9)
    a.andi(8, 8, 0x80)
    a.jump("out")
    a.lwz(8, 0, 11)
    a.stw(8, 4, 11)
    branch(a, "out")
    a.label("clear")
    a.pointer(11, STATE)
    a.li(8, 0)
    for off in (0, 4, 0xC, 0x10):
        a.stw(8, off, 11)
    a.li(8, -1)
    a.stw(8, 8, 11)
    a.label("out")
    a.branch(0x825EC000)
    raw = a.finish()
    assert len(raw) < SIDE - PREPOSE
    add(PREPOSE, raw)
    a = Assembler(0x825EEC00)
    a.branch(PREPOSE)
    replace(a.address, a.finish())
    # Integer-query result: stable for every query of the current X request.
    # Advance only in the actual native setters, once per frame, after their
    # input-suppression checks. Boolean/tutorial/gate queries never advance it.
    a = Assembler(SIDE)
    a.cmp(3, 0)
    a.jump("out")
    a.cmp(4, 0)
    a.jump("out", 0x40820000)
    a.pointer(11, 0x826492D8)
    a.lwz(8, 0, 11)
    a.cmp(8, 4)
    a.jump("normal")
    a.cmp(8, 6)
    a.jump("out", 0x40820000)
    a.label("normal")
    a.pointer(7, STATE)
    a.lwz(8, 0xC, 7)
    a.cmp(8, 0)
    a.jump("out")
    a.pointer(11, 0x8266E800)
    a.lwz(8, 0, 11)
    a.cmp(8, 0)
    a.jump("out", 0x40820000)  # Y-release punch keeps native side
    a.pointer(11, 0x826490DC)
    a.lwz(11, 0, 11)
    a.cmp(11, 0)
    a.jump("out")
    a.lwz(11, 0x98, 11)
    a.cmp(11, 0)
    a.jump("out")
    a.lwz(8, 0x28, 11)
    a.andi(8, 8, 0x80)
    a.jump("out")
    a.lwz(8, 4, 7)
    a.cmp(8, 1)
    a.jump("selected")
    a.cmp(8, 2)
    a.jump("out", 0x40820000)
    a.label("selected")
    a.emit(0x7D034378)  # mr r3,r8
    a.emit(0x7D4802A6)  # mflr r10; never alter the native LR
    for caller in ACCEPT_CALLERS:
        a.pointer(9, caller)
        cmpw(a, 10, 9)
        a.jump("accept")
    branch(a, "out")
    a.label("accept")
    a.pointer(11, 0x8266E184)
    a.lwz(9, 0, 11)
    a.lwz(8, 8, 7)
    cmpw(a, 8, 9)
    a.jump("out")
    a.stw(9, 8, 7)
    a.stw(3, 0x10, 7)
    a.d(26, 3, 8, 3)
    a.stw(8, 0, 7)
    a.label("out")
    a.emit(0x4E800020)
    raw = a.finish()
    assert len(raw) < FILTER - SIDE
    add(SIDE, raw)
    cs = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    main = bytes(baseline[0x825EB100 + i] for i in range(0x800))
    ins = list(cs.disasm(main, 0x825EB100))
    returns = [
        b.address
        for a, b in zip(ins, ins[1:])
        if a.mnemonic == "mr" and a.op_str == "r3, r7" and b.mnemonic == "blr"
    ]
    assert len(returns) == 1
    a = Assembler(returns[0])
    a.branch(SIDE)
    replace(a.address, a.finish())
    # Preserve the committed X side through the cosmetic idle tail. Native
    # action reset clears actor+2538 before that motion has finished. Heavy Y,
    # charged release and other native actions keep their own side selection.
    pose = next(x for x in p["array"] if x["address"] == 0x825EC000)
    raw = bytes.fromhex(pose["value"])
    needle = struct.pack(">II", 0x81262538, 0x2C090001)
    assert raw.count(needle) == 1
    pose_site = 0x825EC000 + raw.index(needle)
    a = Assembler(POSE_SIDE)
    a.pointer(8, 0x8266E800)
    a.lwz(9, 0xC, 8)
    a.cmp(9, 1)
    a.jump("native", 0x40820000)
    a.lwz(9, 8, 8)
    a.cmp(9, 10)
    a.jump("normal")
    a.cmp(9, 29)
    a.jump("native", 0x40820000)
    a.label("normal")
    a.pointer(8, STATE)
    a.lwz(9, 0x10, 8)
    a.cmp(9, 2)
    a.jump("right")
    a.cmp(9, 1)
    a.jump("native", 0x40820000)
    a.li(9, 0)
    branch(a, "out")
    a.label("right")
    a.li(9, 1)
    branch(a, "out")
    a.label("native")
    a.lwz(9, 0x2538, 6)
    a.label("out")
    a.branch(pose_site + 4)
    add(POSE_SIDE, a.finish())
    a = Assembler(pose_site)
    a.branch(POSE_SIDE)
    replace(pose_site, a.finish())
    # Native metadata allocation remains 128x128/16KiB. Only the four round
    # glyphs get linear sampling; no buffers or UV footprint are enlarged.
    loader = next(x for x in p["array"] if x["address"] == 0x825ED900)
    raw = bytes.fromhex(loader["value"])
    needle = struct.pack(">II", 0x38600D10, 0x90690060)
    assert raw.count(needle) == 1
    site = 0x825ED900 + raw.index(needle)
    a = Assembler(FILTER)
    a.lwz(3, 0, 12)
    a.d(14, 3, 3, -2)
    a.emit(0x28030003)
    a.jump("point", 0x41810000)
    a.pointer(3, LINEAR_FACE_FETCH)
    a.branch(site + 4)
    a.label("point")
    a.li(3, 0xD10)
    a.branch(site + 4)
    add(FILTER, a.finish())
    a = Assembler(site)
    a.branch(FILTER)
    replace(site, a.finish())
    assets = ROOT / "assets/controller-smooth"
    am = json.loads((assets / "manifest.json").read_text())
    blob = (assets / "buttons.lz4").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == am["sha256"] and len(blob) <= 0x4800
    old = next(x for x in p["array"] if x["address"] == 0x826BB800)
    assert not any(image[0x6BB800 : 0x6BB800 + len(blob)])
    old["value"] = blob.hex()
    records = []
    for t in am["textures"]:
        records.extend((t["index"], 0x826BB800 + t["offset"], t["packed_bytes"]))
    records.extend((0xFFFFFFFF, 0, 0))
    replace(0x825ED840, struct.pack(">" + str(len(records)) + "I", *records))
    p["name"] = "Gamepad conversion 1.1.0 (Europe)"
    p["desc"] = (
        "Compact smoother A/B/X/Y prompts and native right-left alternating X punches/Ki Blasts; retains 1.0.0 controls, arms, QTEs and content support."
    )
    out = output or ROOT / "experiments/gamepad-v1.1.0-europe"
    out.mkdir(exist_ok=True)
    target = out / "4E4D084E.gamepad.patch.toml"
    text = serialize(doc)
    if target.exists() and target.read_text() != text:
        raise FileExistsError("Different candidate exists")
    target.write_text(text)
    m = json.loads((BASE.parent / "manifest.json").read_text())
    for obsolete in (
        "validation",
        "loaded_bytes_identical_to_revision19",
        "reviewed_bytes_preserved_except_guard_priority",
    ):
        m.pop(obsolete, None)
    m.update(
        version="1.1.0",
        region="Europe",
        status="candidate: CPU and native runtime checks required",
        input_sha256=BASE_SHA,
        patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    )
    m.update(
        original_image_sha256=hashlib.sha256(image).hexdigest(),
        module_hash="C9561ED1F9AFFED4",
        validation_report="docs/update-1.1.0.md",
        runtime_report="runtime-checks.json",
        records=len(p["be32"]) + len(p["array"]),
    )
    m["charge_start"] = {
        "native_consumer": "0x822A4138",
        "near": "Hold Y then release; retain the five-native-frame visual lead-in",
        "far": "Y heavy Ki",
        "normal_X": "Alternating native sides without charging",
    }
    m["hd_prompt_adapter"].update(
        assets="assets/controller-smooth",
        source_sha256=am["sha256"],
        textures=am["textures"],
        source_regions=[["0x826bb800", hex(0x826BB800 + len(blob))]],
        face_fetch_word3=hex(LINEAR_FACE_FETCH),
        sampling="Linear min/mag for A/B/X/Y; unchanged point sampling for other labels",
    )
    m["alternating_X"] = {
        "state": hex(STATE),
        "prepose": hex(PREPOSE),
        "integer_result": hex(SIDE),
        "pose_side": hex(POSE_SIDE),
        "committed_side": hex(STATE + 0x10),
        "accepted_callers": [hex(x) for x in ACCEPT_CALLERS],
        "first_side": "right",
        "policy": "Latch next side on X edge; advance only at native accepted-action setters, once per frame. No actor, HP, energy or phase writes. Committed X side survives the visual idle tail after the actor clears its side. Charged Y, RT, QTE and other action paths retain their native side.",
    }
    existing = out / "manifest.json"
    if existing.exists():
        old = json.loads(existing.read_text())
        if (
            old.get("patch_sha256") == m["patch_sha256"]
            and old.get("validation", {}).get("version") == "1.1.0"
        ):
            for key in ("status", "validation"):
                m[key] = old[key]
    (out / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=IMAGE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.image, args.output)
