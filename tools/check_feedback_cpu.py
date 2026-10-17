"""Exercise the emitted feedback adapters on a PowerPC CPU, without Xenia."""
import hashlib
import argparse
import json
import struct
import tomllib
from pathlib import Path
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_PC, UC_PPC_REG_LR, UC_PPC_REG_MSR, UC_PPC_REG_FPR31

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--patch',type=Path,default=ROOT/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml')
args=parser.parse_args();source=args.patch;OUT=source.parent
data = tomllib.loads(source.read_text())['patch'][0]
cpu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
cpu.mem_map(0x82000000, 0x700000); cpu.mem_map(0x100000, 0x20000)
cpu.mem_write(0x82000000, Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for item in data['array']: cpu.mem_write(item['address'], bytes.fromhex(item['value']))
for item in data['be32']: cpu.mem_write(item['address'], struct.pack('>I', item['value']))
def put(a, v): cpu.mem_write(a, struct.pack('>I', v))
def get(a): return struct.unpack('>I', cpu.mem_read(a,4))[0]
def reg(n, v): cpu.reg_write(UC_PPC_REG_0+n, v)
calls = []
def native_texture(uc, address, size, _):
    if address == 0x823498A8:
        values = [uc.reg_read(UC_PPC_REG_0+n) for n in (3,4,5)]
        calls.append(values)
        reg(3, 0xF0000000+values[1]); uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
cpu.hook_add(UC_HOOK_CODE, native_texture)
put(0x82649134, 0x111000)
manifest = json.loads((OUT/'manifest.json').read_text())
checks = []
for action, icon in enumerate(manifest['button_texture_by_action']):
    calls.clear(); reg(3,0x112000); reg(4,action); reg(1,0x11F000)
    cpu.reg_write(UC_PPC_REG_LR,0x110000)
    end = 0x822DE724 if icon == 255 else 0x110000
    cpu.emu_start(0x822DE720,end,count=100)
    assert cpu.reg_read(UC_PPC_REG_PC) == end
    if icon == 255:
        assert not calls and cpu.reg_read(UC_PPC_REG_0+3) == 0x112000
        assert cpu.reg_read(UC_PPC_REG_0+4) == action
    else:
        assert calls == [[0x111000,icon,0x54583244]], (action,calls)
        assert cpu.reg_read(UC_PPC_REG_0+3) == 0xF0000000+icon
checks.append('All 67 action icon paths: mapped controls use native Xbox textures; super gestures fall back to the original renderer')
for icon in range(17):
    calls.clear(); reg(3,0x112000); reg(4,icon)
    cpu.reg_write(UC_PPC_REG_LR,0x110000)
    cpu.emu_start(0x822DAE40,0x110000,count=100)
    assert len(calls) == 1 and calls[0][0] == 0x111000
    assert 0 <= calls[0][1] < 34 and calls[0][2] == 0x54583244
checks.append('All 17 common gesture icons select valid Xbox texture indices')
for hook,loop_reg,loop_values,indices in (
        (0x822E4218,30,[0,1,2,3],[6,9,7,10]),
        (0x822E3AF8,28,[4,3,2,1],[2,4,15,14]),
        (0x822E0EEC,31,[0,1,2],[7,15,14])):
    for loop_value,icon in zip(loop_values,indices):
        calls.clear();reg(3,0x112000);reg(4,0);reg(5,0x54583244)
        reg(loop_reg,loop_value if loop_reg != 31 else 0x114000)
        if loop_reg == 31: put(0x114078,loop_value)
        cpu.emu_start(hook,hook+4,count=100)
        assert cpu.reg_read(UC_PPC_REG_PC) == hook+4
        assert calls == [[0x111000,icon,0x54583244]],(hex(hook),loop_value,calls)
checks.append('Native contextual call sites select LB/RB/LT/RT, guard/uppercut responses, and LT/LS-left/LS-right for the defender gauge')
put(0x114020,5);reg(8,0x114020)
cpu.emu_start(0x822E4240,0x822E4244,count=50)
assert get(0x114020) == 1 and cpu.reg_read(UC_PPC_REG_0+3) == 0
checks.append('Contextual button lettering clears the native pose mirror flag')
for slot,icon in enumerate(manifest['extra_pose_texture_indices']):
    calls.clear();reg(3,0x112000);put(0x112024,slot);put(0x112010,0)
    cpu.reg_write(UC_PPC_REG_LR,0x110000)
    end=0x822EBBBC if icon==255 else 0x110000
    cpu.emu_start(0x822EBBB8,end,count=100)
    assert cpu.reg_read(UC_PPC_REG_PC) == end
    assert calls == ([] if icon==255 else [[0x111000,icon,0x54583244]])
checks.append('All 21 extra pose widgets follow the manifest: mapped Xbox textures or explicit original fallback')
put(0x82649134,0);put(0x11207C,0x113000)
reg(3,0x112000);reg(4,3)
cpu.emu_start(0x822DAE40,0x822DAE44,count=100)
assert cpu.reg_read(UC_PPC_REG_0+11) == 0x113000
checks.append('Missing pad resources replay the original common-icon load instruction')
for hook in (0x821DB5D0,0x821DB888):
    reg(3,0x112000);cpu.reg_write(UC_PPC_REG_LR,0x110000)
    old=bytes(cpu.mem_read(0x112000,256))
    cpu.emu_start(hook,0x110000,count=5)
    assert bytes(cpu.mem_read(0x112000,256)) == old
checks.append('Kinect Tuner update and drawing return without touching their object')
put(0x826490DC,0x105000);put(0x105098,0x106000)
for action,mask in ((0x42,0x4000),(0xC,0x8000),(0xD,0x4000),(0xE,0x8000)):
    for held,expected in ((mask,3),(mask,3),(0,0)):
        put(0x106020,held);put(0x106028,0)
        reg(3,0x100000);reg(4,action);reg(5,3)
        cpu.reg_write(UC_PPC_REG_LR,0x110000)
        cpu.emu_start(0x82197118,0x110000,count=150)
        assert cpu.reg_read(UC_PPC_REG_0+3) == expected
checks.append('Lateral inputs remain active on consecutive held frames, then clear on release')
main_payload=bytes.fromhex(next(x['value'] for x in data['array'] if x['address']==0x825EB100))
copy_start=0x825EB100+main_payload.index(bytes.fromhex('38ea0b80396a00d0'))
joints=b''.join(struct.pack('>4f',i*.01,i*.02,2.5,1.0) for i in range(20))
cpu.mem_write(0x1000D0,joints)
cpu.mem_write(0x100B7C,b'BEFR'+b'\x00'*320+b'AFTR')
cpu.mem_write(0x1015FC,b'BEFR'+b'\x00'*320+b'AFTR')
reg(10,0x100000);cpu.reg_write(UC_PPC_REG_LR,0x110000)
cpu.emu_start(copy_start,copy_start+36,count=800)
assert bytes(cpu.mem_read(0x100B80,320)) == joints
assert bytes(cpu.mem_read(0x101600,320)) == joints
assert bytes(cpu.mem_read(0x100B7C,4))==b'BEFR' and bytes(cpu.mem_read(0x100CC0,4))==b'AFTR'
assert bytes(cpu.mem_read(0x1015FC,4))==b'BEFR' and bytes(cpu.mem_read(0x101740,4))==b'AFTR'
assert cpu.reg_read(UC_PPC_REG_LR)==0x110000
checks.append('The emitted copy loop fills both 20-joint buffers, preserves LR, and leaves surrounding memory intact')
# The unchanged native close-range dispatcher queries 28 before it prepares
# the front-sway D. Check that LS-left can reach this gate, preserving LT.
put(0x826491D8,0x109000);put(0x826492A0,0)
for held in (0x4000,0x400):
    put(0x106020,held);put(0x106028,0);reg(24,0);reg(31,0x109000)
    cpu.emu_start(0x822A2E0C,0x822A3290,count=250)
    assert cpu.reg_read(UC_PPC_REG_0+24)==1
checks.append('The original close-range sway gate accepts held LS-left as well as LT')
# Execute the original defender-combo gauge block, including its real input
# calls and floating-point increment/clamp. Only the selector and UI object
# are fixtures; no native instruction in this block is replaced.
cpu.reg_write(UC_PPC_REG_MSR, 0x2000)
cpu.reg_write(UC_PPC_REG_FPR31, 0x3FF0000000000000)
put(0x107044, 0x108000)
gauge_results = []
for choice, action, mask in ((0,0x26,0x400),(1,0xD,0x4000),(2,0xE,0x8000)):
    table_source = 0x825EBB00+action*8+4
    values = []
    for source_offset in (0x28,0x20):
        put(table_source,source_offset);put(0x108064,0)
        cpu.mem_write(0x108080,struct.pack('>f',.05))
        for frame in range(30):
            put(0x106020,mask);put(0x106028,mask if frame == 0 else 0)
            reg(27,0x109000);reg(28,1);reg(29,choice);reg(30,0x107000)
            cpu.emu_start(0x822174F4,0x8221756C,count=300)
            assert cpu.reg_read(UC_PPC_REG_PC) == 0x8221756C
        values.append(struct.unpack('>f',cpu.mem_read(0x108064,4))[0])
    assert .049 < values[0] < .051 and values[1] == 1.0, (choice,values)
    gauge_results.append({'choice':choice,'action':hex(action),
                          'edge_only_after_30_frames':values[0],
                          'held_after_30_frames':values[1]})
checks.append('Original native defender gauge: all three responses reach 1.0 with held input; edge-only input stalls at 0.05 in the same fixture')
report = {'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'checks':checks,'passed':len(checks),'native_gauge_fixture':gauge_results,'scope':'isolated emitted PowerPC; native texture factory stubbed; no gameplay claim'}
(OUT/'cpu-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
