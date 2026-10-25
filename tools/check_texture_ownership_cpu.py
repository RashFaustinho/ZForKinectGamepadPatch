"""Execute the native texture destructor's physical-buffer ownership branch.

The allocator/free implementation is an external recording stub; the original
flag test, back-pointer lookup, pool selection and cleared data field execute
from the selected regional image. This does not simulate GPU synchronization.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_PC, UC_PPC_REG_LR
from region_port import NativeMap

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--patch", type=Path, required=True)
source = parser.parse_args().patch
manifest = json.loads((source.parent / "manifest.json").read_text())
eu = Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin").read_bytes()
image = eu
mapping = lambda x: x
if manifest["region"] == "USA":
    image = Path(
        "/workspace/artifacts/zforkinect/usa/analysis/Dbkn.image.bin"
    ).read_bytes()
    mapping = NativeMap(eu, image)
c = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
c.mem_map(0x82000000, 0x700000)
c.mem_map(0x100000, 0x10000)
c.mem_write(0x82000000, image)


def put(a, x):
    c.mem_write(a, struct.pack(">I", x))


def get(a):
    return int.from_bytes(c.mem_read(a, 4), "big")


def reg(n, x):
    c.reg_write(UC_PPC_REG_0 + n, x)


calls = []


def free(uc, address, size, user):
    if address == mapping(0x823794B8):
        calls.append([uc.reg_read(UC_PPC_REG_0 + 3), uc.reg_read(UC_PPC_REG_0 + 4)])
        uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))


c.hook_add(UC_HOOK_CODE, free)
rows = []
for flags in (0xA2, 0xAA):
    calls.clear()
    put(0x100034, 0x101000)
    put(0x101000, flags)
    put(0x101004, 0x104000)
    put(0x103FFC, 0x102000)
    put(0x102000, 0x105000)
    for repeat in range(2):
        reg(3, 0x100000)
        reg(30, 0)
        c.emu_start(mapping(0x82358AB0), mapping(0x82358B04), count=100)
        assert c.reg_read(UC_PPC_REG_PC) == mapping(0x82358B04)
        assert get(0x101000) == flags
        assert get(0x101004) == (0 if flags == 0xAA else 0x104000)
    assert calls == ([[0x105000, 0x102000]] if flags == 0xAA else [])
    rows.append(
        {
            "metadata_flags": hex(flags),
            "free_calls": calls.copy(),
            "repeat_does_not_free_twice": True,
        }
    )
report = {
    "scope": __doc__,
    "patch_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "region": manifest["region"],
    "passed": True,
    "cases": rows,
}
(source.parent / "texture-ownership-cpu.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(
    "Passed native texture ownership and repeated-destruction checks:",
    manifest["region"],
)
