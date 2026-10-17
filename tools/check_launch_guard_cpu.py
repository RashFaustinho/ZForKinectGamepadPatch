"""Execute both native launch-choice dispatchers, including mixed pad inputs.

The actual original query order and patched input API run on PowerPC. Stop
before native UI dispatch: choosing a response is distinct from winning it.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_PC, UC_PPC_REG_LR

from patch_format import read

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--patch', type=Path, default=ROOT / 'experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml')
source = p.parse_args().patch
image = Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()


def machine(path):
    cpu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    cpu.mem_map(0x82000000, 0x700000)
    cpu.mem_map(0x100000, 0x100000)
    cpu.mem_write(0x82000000, image)
    patch = read(path)['patch'][0]
    for kind in ('be32', 'array'):
        for item in patch[kind]:
            raw = item['value'].to_bytes(4, 'big') if kind == 'be32' else bytes.fromhex(item['value'])
            cpu.mem_write(item['address'], raw)
    return cpu


def execute(path):
    c = machine(path)
    def put(a, v): c.mem_write(a, struct.pack('>I', v))
    def reg(n, v): c.reg_write(UC_PPC_REG_0 + n, v)
    def get(n): return c.reg_read(UC_PPC_REG_0 + n)
    for a, v in [(0x826490DC, 0x105000), (0x105098, 0x106000),
                 (0x826491D8, 0x109000), (0x82649298, 0x110000),
                 (0x110054, 0x111000), (0x111028, 0x112000)]:
        put(a, v)
    found = []
    def stop(uc, address, size, _):
        if address in (0x8229D178, 0x8220E9D0, 0x8221100C, 0x822110F8):
            found.append(get(3) if address == 0x8229D178 else get(29) if address == 0x8221100C else 0)
            uc.emu_stop()
    handle = c.hook_add(UC_HOOK_CODE, stop)
    priority = 'launch_guard_priority' in json.loads((path.parent / 'manifest.json').read_text())
    cases = []
    for mode in (5, 8):
        put(0x826492D8, mode)
        for held, rising, normal in [(0, 0, 0), (0x20, 0, 1), (0x20, 0x20, 1),
                                     (0x4000, 0, 3), (0x8000, 0x8000, 4), (0x10, 0x10, 2),
                                     (0x4020, 0x20, 3), (0x8020, 0x8020, 4),
                                     (0x30, 0x10, 1)]:
            put(0x106020, held)
            put(0x106028, rising)
            expected = 1 if priority and held & 0x20 else normal
            for start in (0x8220E77C, 0x82210F9C):
                reg(1, 0x1EF000)
                for n, v in [(30, 0x109000), (29, 0x109000), (25, 0x82650000),
                             (22, 0), (24, 2 if start == 0x8220E77C else 1),
                             (23, 3), (27, 1), (28, 0x82649E7C)]: reg(n, v)
                found.clear()
                c.emu_start(start, 0x1F0000, count=4000)
                assert found == [expected], (hex(start), mode, hex(held), found, expected)
                cases.append({'native_block': hex(start), 'mode': mode, 'held': hex(held),
                              'rising': hex(rising), 'native_choice': found[0]})
    c.hook_del(handle)
    # Unrelated callers retain the old lateral binding, even with B held.
    for action, mask in [(0x28, 0x4000), (0x29, 0x8000), (0xD, 0x4000), (0xE, 0x8000)]:
        for mode in (4, 5, 6, 8):
            put(0x826492D8, mode)
            put(0x106020, mask | 0x20)
            put(0x106028, mask)
            reg(4, action)
            reg(1, 0x1EF000)
            c.reg_write(UC_PPC_REG_LR, 0x1F0000)
            c.emu_start(0x82197118, 0x1F0000, count=1000)
            assert get(3) == 3
    if priority:
        writes = []
        c.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, address, size, value, user: writes.append((address, size)))
        for caller in (0x8220E788, 0x8220E81C, 0x82210FA8, 0x82210FC8):
            for held in (0x20, 0x4020, 0x8020, 0xC020):
                put(0x106020, held)
                reg(1, 0x1EF000)
                reg(4, 0x28 if caller in (0x8220E788, 0x82210FA8) else 0x29)
                reg(5, 3)
                for n in range(14, 32): reg(n, 0x55550000 + n)
                c.reg_write(UC_PPC_REG_LR, caller)
                writes.clear()
                c.emu_start(0x82197118, caller, count=1000)
                assert get(3) == 0 and get(1) == 0x1EF000 and get(5) == 3
                assert all(get(n) == 0x55550000 + n for n in range(14, 32))
                assert c.reg_read(UC_PPC_REG_LR) == caller and writes == []
    return cases


old = execute(ROOT / 'experiments/gamepad-feedback-v19/4E4D084E.gamepad-feedback.patch.toml')
new = execute(source)
regressions = [x for x in old if x['held'] in ('0x4020', '0x8020')]
assert len(regressions) == 8 and all(x['native_choice'] in (3, 4) for x in regressions)
report = {'scope': __doc__, 'patch_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'passed': True, 'native_choice_cases': new, 'revision19_B_stolen_by_stick': regressions,
          'unrelated_caller_cases': 16, 'adapter_ABI_and_no_write_cases': 16}
(source.parent / 'launch-guard-cpu.json').write_text(json.dumps(report, indent=2) + '\n')
print('36 native launch-choice cases and 16 unrelated-caller cases passed; 8 old failures reproduced')
