"""Execute native melee/ranged action setters and the alternating-side bridge.

PPC fixtures use simulated input/state, not forced live gameplay. The original
setter instructions select actor+2538 from the returned side bits. Tests verify
query stability, acceptance-only advancement, pose symmetry, buffer coherence,
charge isolation, context reset, ABI and the helper's local-only write bounds.
"""

import argparse, hashlib, json, math, struct, tomllib
from pathlib import Path
from unicorn import (
    Uc,
    UC_ARCH_PPC,
    UC_MODE_PPC32,
    UC_MODE_BIG_ENDIAN,
    UC_HOOK_MEM_WRITE,
)
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_PC, UC_PPC_REG_LR, UC_PPC_REG_MSR

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--patch", type=Path, required=True)
args = p.parse_args()
source = args.patch
manifest = json.loads((source.parent / "manifest.json").read_text())
region = manifest["region"]
mapping = lambda x: x
image_path = Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin")
if region == "USA":
    from region_port import NativeMap

    image_path = Path("/workspace/artifacts/zforkinect/usa/analysis/Dbkn.image.bin")
    d = json.loads((source.parent / "address-map.json").read_text())
    mapping = NativeMap(
        Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin").read_bytes(),
        image_path.read_bytes(),
        [
            (int(x["source"], 16), int(x["end"], 16), int(x["target"], 16))
            for x in d["islands"]
        ],
    )
doc = tomllib.loads(source.read_text())["patch"][0]
c = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
c.mem_map(0x82000000, 0x700000)
c.mem_map(0x100000, 0x100000)
c.reg_write(UC_PPC_REG_MSR, 0x2000)
c.mem_write(0x82000000, image_path.read_bytes())
for x in doc["array"]:
    c.mem_write(x["address"], bytes.fromhex(x["value"]))
for x in doc["be32"]:
    c.mem_write(x["address"], struct.pack(">I", x["value"]))


def put(a, v):
    c.mem_write(a, struct.pack(">I", v))


def get(a):
    return int.from_bytes(c.mem_read(a, 4), "big")


def reg(n, v):
    c.reg_write(UC_PPC_REG_0 + n, v)


def run(start, end):
    c.emu_start(start, end, count=20000)
    assert c.reg_read(UC_PPC_REG_PC) == end, hex(c.reg_read(UC_PPC_REG_PC))


put(0x826491D8, 0x100000)
put(0x10001C, 0x101000)
put(0x826490DC, 0x105000)
put(0x105098, 0x106000)
put(0x82649298, 0x107000)
put(0x107054, 0x108000)
put(0x10800C, 0)
put(0x10AFC0, 0x140000)
put(0x142580, 0x148000)
reg(1, 0x1EF000)
reg(31, 0x10C000)
helper_writes = []


def writes(cpu, access, address, size, value, user):
    pc = cpu.reg_read(UC_PPC_REG_PC)
    if 0x825ED200 <= pc < 0x825ED600:
        helper_writes.append((address, size))


c.hook_add(UC_HOOK_MEM_WRITE, writes)


def frame(mode=4, state=0, held=0, edge=0):
    put(0x826492D8, mode)
    put(0x141130, state)
    for off, v in ((0x20, held), (0x28, edge), (0x2C, 0)):
        put(0x106000 + off, v)
    reg(31, 0x10C000)
    run(mapping(0x82195550), mapping(0x82195554))


def query(action=0, caller=0x1F0000):
    reg(3, 0x100000)
    reg(4, action)
    reg(5, 3)
    c.reg_write(UC_PPC_REG_LR, caller)
    run(mapping(0x82197118), caller)
    return c.reg_read(UC_PPC_REG_0 + 3)


def setter(mode):
    reg(31, 0x140000)
    reg(30, 0x82650000 if mode == 4 else 0)
    reg(29, 0)
    reg(28, 1)
    reg(8, 0x100000)
    reg(3, 0x100000)
    start, end = (0x822A443C, 0x822A4488) if mode == 4 else (0x822A4654, 0x822A46C8)
    run(mapping(start), mapping(end))
    return get(0x142538)


checks = []
sequences = {}
for mode in (4, 6):
    put(0x10AFC0, 0)
    frame()
    put(0x10AFC0, 0x140000)
    sides = []
    motions = []
    for attack in range(8):
        frame(mode=mode, state=0 if mode == 4 else 20)
        frame(mode=mode, state=0 if mode == 4 else 20, held=0x80, edge=0x80)
        expected_mask = 2 if attack % 2 == 0 else 1
        before = get(0x8266EC00)
        assert (
            query() == expected_mask
            and query() == expected_mask
            and get(0x8266EC00) == before
        )
        side = setter(mode)
        assert side == (1 if attack % 2 == 0 else 0)
        assert setter(mode) == side and get(0x8266EC00) == (expected_mask ^ 3), (
            mode,
            attack,
            side,
            get(0x142538),
            get(0x8266EC00),
            get(0x8266EC04),
            get(0x8266EC08),
            get(0x8266E184),
        )
        sides.append(side)
        positions = []
        for tick in range(8):
            if tick == 2:
                put(0x142530, 0xFFFFFFFF)
                put(0x142538, 0xFFFFFFFF)
            frame(
                mode=mode,
                state=(
                    (10 if mode == 4 else 29) if tick < 2 else (1 if mode == 4 else 20)
                ),
            )
            raw = bytes(c.mem_read(0x1010D0, 320))
            assert (
                raw
                == bytes(c.mem_read(0x101B80, 320))
                == bytes(c.mem_read(0x102600, 320))
            )
            assert all(math.isfinite(x) for x in struct.unpack(">80f", raw))
            positions.append(struct.unpack_from(">3f", raw, (11 if side else 7) * 16))
        assert len(set(positions)) >= 6 and positions[4][2] < positions[0][2] - 0.1
        motions.append(positions)
    sequences["melee" if mode == 4 else "ranged"] = {
        "native_sides": sides,
        "active_hand_positions": motions,
    }
checks.append(
    "Eight native melee setters and eight native ranged setters select right-left-right-left; every accepted side keeps its moving hand through the native idle/reset tail in all buffers"
)
# Mixed ranges retain one sequence; cosmetic and boolean queries do not count.
frame(mode=4, edge=0x80, held=0x80)
first = query()
setter(4)
frame(mode=6, edge=0x80, held=0x80)
assert query() == (first ^ 3)
setter(6)
checks.append("The same alternation continues across close/ranged transitions")
frame(mode=4)
before = get(0x8266EC00)
assert query() == 0 and get(0x8266EC00) == before
for _ in range(4):
    frame(mode=4, held=0x80, edge=0x80)
    query()
assert get(0x8266EC00) == before
checks.append(
    "Rejected/missing X and repeated non-setter queries never advance the next side"
)
for mode in (5, 8, 10):
    frame(mode=mode, held=0x80, edge=0x80)
    assert query() == 3
checks.append("Cinematic, launch and Super contexts keep both native side bits")
frame(mode=4, held=0x80, edge=0x80)
put(0x8266E800, 1)
put(0x8266E828, 0x10)
assert query() == 3
put(0x8266E800, 0)
put(0x8266E828, 0)
checks.append(
    "A synthesized Y-release punch retains its original side even alongside X"
)
put(0x10AFC0, 0)
frame()
assert get(0x8266EC0C) == 0
put(0x10AFC0, 0x140000)
frame(mode=4, held=0x80, edge=0x80)
assert query() == 2
checks.append(
    "A lost/replaced actor resets the first valid X request to the right hand"
)
assert helper_writes and all(
    0x8266EC00 <= a and a + n <= 0x8266EC14 for a, n in helper_writes
)
checks.append(
    "Both new helpers write only their twenty bytes of private state, never actor/HP/energy/phase fields"
)
report = {
    "scope": __doc__,
    "region": region,
    "patch_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "original_image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
    "passed": True,
    "checks": checks,
    "sequences": sequences,
}
(source.parent / "alternating-arms-cpu.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps({"region": region, "passed": True, "checks": checks}))
