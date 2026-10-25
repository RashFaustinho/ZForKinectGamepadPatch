"""Port authored PPC payloads using unique normalized native-code anchors.

No uniform region delta is assumed. Branch displacements and constructed code
pointers are normalized only for matching; full source/target image digests are
pinned. Authored islands map contiguously, native code maps by unique context.
The report contains identifiers/hashes, never proprietary executable bytes.
"""

import argparse
import bisect
import copy
import hashlib
import json
import re
import struct
from pathlib import Path

from patch_format import read, serialize

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x82000000
TEXT = 0x82110000
TEXT_END = 0x825EB040
EU_SHA = "72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b"
USA_SHA = "12ce5c89e9ee9b6903745bfd459222f628c88e804363895dd54e79d1094cd088"
USA_MODULE = "8FDD4F4AB147612A"
DATA_ARRAYS = {
    0x8210EEA8,
    0x8266EC20,
    0x8210EC00,
    0x825EC800,
    0x825ECE00,
    0x825ED800,
    0x825ED840,
    0x825EDF00,
    0x825EE800,
    0x825EE9C0,
    0x825EF500,
    0x8266E180,
    0x8266E1C0,
    0x8266E900,
    0x826BB800,
}


def normalized(data):
    words = list(
        struct.unpack(
            ">" + str((TEXT_END - TEXT) // 4) + "I", data[TEXT - BASE : TEXT_END - BASE]
        )
    )
    for i, w in enumerate(words):
        op = w >> 26
        if op == 18:
            words[i] = w & 0xFC000003
        elif op == 16:
            words[i] = w & 0xFFFF0003
        elif op == 15 and not (w & 0x1F0000):
            reg = (w >> 21) & 31
            for j in range(i + 1, min(i + 6, len(words))):
                q = words[j]
                kind = q >> 26
                ra = (q >> 16) & 31
                rt = (q >> 21) & 31
                if kind in (14, 32, 34, 40, 48, 50) and ra == reg:
                    value = ((w & 65535) << 16) + (
                        (q & 65535) - 65536 if q & 32768 else q & 65535
                    )
                    if 0x82000400 <= value < 0x820FC000 or TEXT <= value < TEXT_END:
                        words[i] = w & 0xFFFF0000
                        words[j] = q & 0xFFFF0000
                    if kind in (14, 32, 34, 40) and rt == reg:
                        break
                elif kind in (14, 15, 32, 34, 40) and rt == reg:
                    break
                if kind == 18:
                    break

    return struct.pack(">" + str(len(words)) + "I", *words)


class NativeMap:
    def __init__(self, eu, usa, islands=()):
        if (
            hashlib.sha256(eu).hexdigest() != EU_SHA
            or hashlib.sha256(usa).hexdigest() != USA_SHA
        ):
            raise ValueError("Unknown original image")
        self.eu = eu
        self.usa = usa
        self.a = normalized(eu)
        self.b = normalized(usa)
        self.cache = {}
        self.islands = list(islands)
        self.functions = [
            (x, ((y >> 8) & 0x3FFFFF) * 4)
            for x, y in struct.iter_unpack(">II", eu[0xFC000:0x10EB88])
        ]
        self.starts = [x for x, n in self.functions]
        self.data_cache = {}

    def native(self, address):
        if not TEXT <= address < TEXT_END:
            return address
        if address in self.cache:
            return self.cache[address]["target"]
        i = bisect.bisect_right(self.starts, address) - 1
        begin, length = self.functions[i]
        end = begin + length
        options = []
        if address >= end:
            # Leaf functions and shared ABI helpers may have no unwind entry.
            begin = end
            end = self.starts[i + 1] if i + 1 < len(self.starts) else TEXT_END
        for size in (64, 96, 128, 192, 256, 32, 16):
            for back in dict.fromkeys((0, 16, 32, 64, 96, *range(4, 132, 4))):
                start = address - back
                if start < begin or start + size > end or start + size < address + 4:
                    continue
                raw = self.a[start - TEXT : start - TEXT + size]
                one = self.b.find(raw)
                if one < 0 or one % 4 or self.b.find(raw, one + 1) >= 0:
                    continue
                options.append(
                    (TEXT + one + back, size, back, hashlib.sha256(raw).hexdigest())
                )
                if len(options) > 3:
                    break
            if len(options) > 3:
                break
        if not options and address in (begin, begin + 4):
            # Some equivalent regional widgets differ early in their bodies.
            # For an entry trampoline only, identify the containing function
            # using a unique long interior anchor, equal unwind length and a
            # matching normalized prologue. Do not infer interior relocations.
            functions = [
                (x, ((y >> 8) & 0x3FFFFF) * 4)
                for x, y in struct.iter_unpack(">II", self.usa[0xFC000:0x10EB88])
            ]
            starts = [x for x, n in functions]
            candidates = {}
            for offset in range(0, length - 127, 4):
                raw = self.a[begin + offset - TEXT : begin + offset - TEXT + 128]
                at = self.b.find(raw)
                if at < 0 or at % 4 or self.b.find(raw, at + 1) >= 0:
                    continue
                hit = TEXT + at
                j = bisect.bisect_right(starts, hit) - 1
                target, n = functions[j]
                if n != length or hit - target != offset:
                    continue
                if (
                    self.a[begin - TEXT : begin - TEXT + 16]
                    != self.b[target - TEXT : target - TEXT + 16]
                ):
                    continue
                candidates[target] = (offset, hashlib.sha256(raw).hexdigest())
            if len(candidates) == 1:
                target, (offset, digest) = next(iter(candidates.items()))
                info = {
                    "target": target + address - begin,
                    "normalized_anchor_bytes": 128,
                    "anchor_before": -offset,
                    "anchor_sha256": digest,
                    "method": "unique interior anchor, equal unwind length, matching prologue; entry only",
                }
                self.cache[address] = info
                return info["target"]
        if not options or len({x for x, s, b, h in options}) != 1:
            raise ValueError(
                f"No unambiguous native anchor for {address:08X}: {options}"
            )
        target, size, back, digest = options[0]
        self.cache[address] = {
            "target": target,
            "normalized_anchor_bytes": size,
            "anchor_before": back,
            "anchor_sha256": digest,
        }
        return target

    def __call__(self, address):
        for source, end, target in self.islands:
            if source <= address < end:
                return target + address - source
        if 0x82000400 <= address < 0x820FC000:
            return self.data(address)
        return self.native(address)

    def data(self, address):
        if address in self.data_cache:
            return self.data_cache[address]["target"]
        i = address - BASE
        if self.eu[i : i + 16] == self.usa[i : i + 16]:
            return address
        end = self.eu.find(b"\0", i, min(i + 256, 0xFC000))
        raw = self.eu[i : end + 1] if end >= 0 else b""
        candidates = []
        if len(raw) >= 5 and all(32 <= x < 127 for x in raw[:-1]):
            candidates.append(raw)
        candidates.extend(self.eu[i : i + n] for n in (64, 32, 16))
        for raw in candidates:
            one = self.usa.find(raw, 0x400, 0xFC000)
            if one >= 0 and self.usa.find(raw, one + 1, 0xFC000) < 0:
                self.data_cache[address] = {
                    "target": BASE + one,
                    "anchor_bytes": len(raw),
                    "anchor_sha256": hashlib.sha256(raw).hexdigest(),
                }
                return BASE + one
        raise ValueError(f"No exact data/string anchor for {address:08X}")

    def word(self, pc, w):
        op = w >> 26
        new_pc = self(pc)
        if op not in (16, 18):
            return w
        if w & 2:
            raise ValueError("Absolute branch requires explicit review")
        mask, sign, limit = (
            (0x3FFFFFC, 0x2000000, 0x2000000) if op == 18 else (0xFFFC, 0x8000, 0x8000)
        )
        delta = w & mask
        if delta & sign:
            delta -= sign * 2
        target = self(pc + delta)
        offset = target - new_pc
        if offset % 4 or not -limit <= offset < limit:
            raise ValueError("Ported branch out of range")
        return (w & ~mask) | (offset & mask)

    def code(self, address, raw):
        words = list(struct.unpack(">" + str(len(raw) // 4) + "I", raw))
        original = list(words)
        for i, w in enumerate(original):
            if not w:
                continue
            # A previous lis may already have rewritten this instruction's low half.
            # Only branch words are replaced here; do not undo pointer fixups later.
            if w >> 26 in (16, 18):
                words[i] = self.word(address + i * 4, w)
            if w >> 26 != 15 or w & 0x1F0000:
                continue
            reg = (w >> 21) & 31
            new_high = None
            for j in range(i + 1, min(i + 6, len(words))):
                q = original[j]
                kind = q >> 26
                ra = (q >> 16) & 31
                rt = (q >> 21) & 31
                if kind in (14, 32, 34, 40, 48, 50) and ra == reg:
                    value = ((w & 65535) << 16) + (
                        (q & 65535) - 65536 if q & 32768 else q & 65535
                    )
                    target = self(value)
                    high = (target + 0x8000) >> 16 & 65535
                    if target != value:
                        if new_high is not None and new_high != high:
                            raise ValueError(
                                "Shared lis needs incompatible target pages"
                            )
                        new_high = high
                        words[i] = (w & 0xFFFF0000) | high
                        words[j] = (q & 0xFFFF0000) | (target & 65535)
                    if kind in (14, 32, 34, 40) and rt == reg:
                        break
                elif kind in (14, 15, 32, 34, 40) and rt == reg:
                    break
                if kind == 18:
                    break

        return struct.pack(">" + str(len(words)) + "I", *words)


def port_document(document, eu, us):
    doc = copy.deepcopy(document)
    p = doc["patch"][0]
    mapper = NativeMap(eu, us)
    islands = []
    for x in p["array"]:
        a = x["address"]
        n = len(x["value"]) // 2
        if TEXT <= a < 0x825EB100:
            target = mapper.native(a)
            islands.append((a, a + n, target))
    mapper.islands = islands
    changes = []
    for item in p["be32"]:
        old = item["address"]
        target = mapper(old)
        index = old - TEXT
        new_index = target - TEXT
        if mapper.a[index : index + 4] != mapper.b[new_index : new_index + 4]:
            raise ValueError(f"Native hook instruction differs: {old:X}")
        item["address"] = target
        item["value"] = mapper.word(old, item["value"])
        changes.append(
            {"kind": "native_hook", "source": hex(old), "target": hex(target)}
        )
    for item in p["array"]:
        old = item["address"]
        raw = bytes.fromhex(item["value"])
        target = mapper(old)
        if old not in DATA_ARRAYS:
            size = (
                0x800 if old == 0x825EB100 else 0x200 if old == 0x821DB5D0 else len(raw)
            )
            raw = mapper.code(old, raw[:size]) + raw[size:]
        # Shared fixed caves/data must still be zero in the target executable.
        if old >= 0x825EB100 or old == 0x8210EC00:
            if any(us[target - BASE : target - BASE + len(raw)]):
                raise ValueError(f"Target cave is occupied: {target:X}")
        item["address"] = target
        item["value"] = raw.hex()
        if target != old:
            changes.append(
                {
                    "kind": "authored_island",
                    "source": hex(old),
                    "target": hex(target),
                    "bytes": len(raw),
                }
            )
    ranges = sorted(
        (x["address"], x["address"] + (4 if k == "be32" else len(x["value"]) // 2))
        for k in ("be32", "array")
        for x in p[k]
    )
    if any(b > c for (a, b), (c, d) in zip(ranges, ranges[1:])):
        raise ValueError("Ported payloads overlap")
    doc["hash"] = USA_MODULE
    return doc, mapper, changes, islands


def build(source=None, europe_image=None, usa_image=None, output=None):
    source = (
        source or ROOT / "experiments/gamepad-v1.1.0-europe/4E4D084E.gamepad.patch.toml"
    )
    eu = (
        europe_image or Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin")
    ).read_bytes()
    us = (
        usa_image or Path("/workspace/artifacts/zforkinect/usa/analysis/Dbkn.image.bin")
    ).read_bytes()
    doc, mapper, changes, islands = port_document(read(source), eu, us)
    p = doc["patch"][0]
    doc["hash"] = USA_MODULE
    source_manifest = json.loads((source.parent / "manifest.json").read_text())
    version = source_manifest.get("version", "1.1.0")
    p["name"] = f"Gamepad conversion {version} (USA)"
    p["desc"] = (
        "American executable port: compact smoother A/B/X/Y, native alternating right-left X punches/Ki Blasts, all 1.0.0 controls and QTE/card support."
    )
    if version == "1.1.1":
        p["desc"] = (
            "American executable port: tucked B guard, compact 256 px face buttons, native alternating X attacks and existing gamepad controls."
        )
    if version == "1.1.2":
        p["desc"] = (
            "American executable port: clean RGBA8 face contours and X on native mash/clash panels; preserves the validated guard and alternating attacks."
        )
    out = output or ROOT / "experiments/gamepad-v1.1.0-usa"
    out.mkdir(exist_ok=True)
    target = out / "4E4D084E.gamepad.patch.toml"
    text = serialize(doc)
    if target.exists() and target.read_text() != text:
        raise FileExistsError("Different USA candidate exists")
    target.write_text(text)

    def metadata(x):
        if isinstance(x, str) and re.fullmatch(r"(?:0x)?[0-9a-fA-F]{8}", x):
            v = int(x, 16)
            if TEXT <= v < TEXT_END:
                return hex(mapper(v))
        if isinstance(x, list):
            return [metadata(y) for y in x]
        if isinstance(x, dict):
            return {metadata(k): metadata(v) for k, v in x.items()}
        return x

    m = metadata(json.loads((source.parent / "manifest.json").read_text()))
    m.update(
        region="USA",
        status="candidate: relocated native CPU and runtime checks required",
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        patch_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        original_image_sha256=USA_SHA,
        module_hash=USA_MODULE,
    )
    # Original-region summaries refer to native bytes of this target build.
    for address, info in m["original_regions"].items():
        i = int(address, 16) - BASE
        info["sha256"] = hashlib.sha256(us[i : i + info["bytes"]]).hexdigest()
    existing = out / "manifest.json"
    if existing.exists():
        old = json.loads(existing.read_text())
        if (
            old.get("patch_sha256") == m["patch_sha256"]
            and old.get("validation", {}).get("version") == version
        ):
            for key in ("status", "validation"):
                m[key] = old[key]
    m["port_report"] = "address-map.json"
    (out / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    report = {
        "source_module": "C9561ED1F9AFFED4",
        "target_module": USA_MODULE,
        "source_image_sha256": EU_SHA,
        "target_image_sha256": USA_SHA,
        "patch_sha256": m["patch_sha256"],
        "method": "Unique normalized PPC anchors; branch targets and constructed code pointers relocated; contiguous authored islands; checked empty shared caves. No uniform region delta or pdata-index pairing.",
        "changes": changes,
        "islands": [
            {"source": hex(a), "end": hex(b), "target": hex(c)} for a, b, c in islands
        ],
        "data_anchors": {
            hex(k): {**v, "target": hex(v["target"])}
            for k, v in sorted(mapper.data_cache.items())
        },
        "native_anchors": {
            hex(k): {**v, "target": hex(v["target"])}
            for k, v in sorted(mapper.cache.items())
        },
        "overlapping_writes": 0,
        "status": "Port generated; validation is separate.",
    }
    (out / "address-map.json").write_text(json.dumps(report, indent=2) + "\n")
    print(target, "native anchors", len(mapper.cache))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--europe-image", type=Path)
    parser.add_argument("--usa-image", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.source, args.europe_image, args.usa_image, args.output)
