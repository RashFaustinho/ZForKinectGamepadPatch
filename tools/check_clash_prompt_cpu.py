"""Check real mash-texture selection and post-animation widget cleanup.

Native 822EE188 executes with simulated Kinect catalogs (including missing or
unready catalogs). Other widget bodies model their late pose/texture resets;
their gameplay logic is not simulated. Texture and part factories are fixtures,
while the original named-child traversal and emitted wrappers execute on PPC.
"""

import hashlib, json, struct
from pathlib import Path
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_PC, UC_PPC_REG_LR

fixture = Path(__file__).with_name("check_alternating_arms_cpu.py")
s = {"__file__": str(fixture), "__name__": "clash_fixture"}
exec(compile(fixture.read_text().split("checks = []")[0], str(fixture), "exec"), s)
c, put, get, reg, mapping, source = (
    s[k] for k in ("c", "put", "get", "reg", "mapping", "source")
)
c.mem_map(0x200000, 0x100000)
m = s["manifest"]
new = "clash_prompt" in m
wrappers = m.get("clash_prompt", {}).get(
    "wrappers",
    [{"native": hex(mapping(0x822F1608)), "wrapper": hex(mapping(0x822F1608))}],
)
names = [
    "i_pl_seal_anm_grp",
    "a_pl_attack_anm_grp",
    "i_pl_attack",
    "a_pl_guard_anm_grp",
    "i_pl_guard",
    "i_ico_dummy_grp",
    "a_ok_s_tx_JP_ef",
]
lookup = {}
calls = []
native_visits = []
writes = []
scenario = "normal"


def g(n):
    return c.reg_read(UC_PPC_REG_0 + n)


def ret():
    c.reg_write(UC_PPC_REG_PC, c.reg_read(UC_PPC_REG_LR))


native = mapping(0x822EE188)
selectors = (native, mapping(0x822F1608))
others = {
    int(x["native"], 16) + 4 for x in wrappers if int(x["native"], 16) not in selectors
}


def hook(uc, address, size, user):
    if address in others:
        native_visits.append(address - 4)
        # A late native animation reset must be followed by the wrapper.
        for i in range(len(names)):
            put(0x1240D0 + i * 0x100, 1)
        put(0x121020, 5)
        put(0x121024, 0x195000)
        uc.reg_write(UC_PPC_REG_PC, g(12))
        return
    if any(n + 4 <= address < n + 0xE8 for n in selectors):
        w = get(address)
        op = w >> 26
        if op in (58, 62) and w & 3 == 0:
            r = (w >> 21) & 31
            ra = (w >> 16) & 31
            off = (w & 0xFFFC) - (0x10000 if w & 0x8000 else 0)
            a = (g(ra) if ra else 0) + off
            if op == 62:
                c.mem_write(a, struct.pack(">Q", g(r)))
            else:
                reg(r, int.from_bytes(c.mem_read(a + 4, 4), "big"))
            uc.reg_write(UC_PPC_REG_PC, address + 4)
            return
    if address == mapping(0x82115458):
        name = bytes(uc.mem_read(g(4), 80)).split(b"\0")[0].decode()
        reg(3, lookup.get(name, 0))
        ret()
    elif address == mapping(0x823498A8):
        calls.append((g(3), g(4), g(5)))
        reg(
            3,
            (
                0
                if scenario == "missing_texture" and g(3) == 0x180000
                else 0x190000 + g(4) * 0x100 if g(3) == 0x180000 else 0x195000
            ),
        )
        ret()


c.hook_add(UC_HOOK_CODE, hook)
c.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, a, n, v, user: writes.append((a, n)))
rows = []
for wrapper in wrappers:
    for count, ready in ((0, 0), (3, 0), (4, 0), (4, 1)):
        for scenario in (
            "normal",
            "missing_pad",
            "wrong_pad_count",
            "missing_table",
            "missing_texture",
            "missing_part",
        ):
            c.mem_write(0x100000, bytes(0x200000))
            lookup.clear()
            calls.clear()
            writes.clear()
            native_visits.clear()
            lookup.update(
                {
                    "p_ico_dummy_000": 0 if scenario == "missing_part" else 0x121000,
                    "i_pl_grp": 0x120000,
                }
            )
            put(0x110034, 0x111000)
            put(0x111004, 0x112000)
            put(0x110064, 0x3F000000)
            put(0x11006C, 0x12345678)  # Native progress/result sentinels.
            put(0x1200B8, 0x122000)
            put(0x122008, 0x123000)
            c.mem_write(0x12200C, struct.pack(">H", len(names)))
            put(0x121020, 5)
            put(0x121024, 0x195000)
            for i, name in enumerate(names):
                obj = 0x124000 + i * 0x100
                string = 0x130000 + i * 0x80
                c.mem_write(string, name.encode() + b"\0")
                put(obj + 0xD4, string)
                put(obj + 0xD0, 1)
                for off, value in ((0, 77 + i), (4, obj), (8, 0xAA000000 + i)):
                    put(0x123000 + i * 12 + off, value)
            put(0x8264910C, 0x160000)
            put(0x160314, count)
            put(0x1602A4, 0x170000)
            put(0x170088, ready)
            put(0x82649134, 0 if scenario == "missing_pad" else 0x180000)
            put(0x1800D8, 33 if scenario == "wrong_pad_count" else 34)
            put(0x1800DC, 0 if scenario == "missing_table" else 0x181000)
            for i in range(34):
                put(0x181000 + i * 4, 0x190000 + i * 0x100)
            reg(1, 0x2EF000)
            reg(3, 0x110000)
            for r in range(14, 32):
                reg(r, 0x55550000 + r)
            c.reg_write(UC_PPC_REG_LR, 0x2F0000)
            c.emu_start(int(wrapper["native"], 16), 0x2F0000, count=20000)
            assert c.reg_read(UC_PPC_REG_PC) == 0x2F0000
            assert g(1) == 0x2EF000 and all(
                g(r) == 0x55550000 + r for r in range(14, 32)
            )
            if scenario == "normal":
                assert get(0x121024) == 0x190300, (wrapper, count, ready, "no X glyph")
                assert get(0x121020) == 1
                for i in range(1, 5):
                    assert get(0x1240D0 + i * 0x100) == 0
                order = [get(0x123000 + i * 12 + 4) for i in range(len(names))]
                assert order.index(0x124000) > order.index(0x124500)
            else:
                assert all(get(0x1240D0 + i * 0x100) == 1 for i in range(len(names)))
            assert get(0x1246D0) == 1  # The native OK group remains visible.
            assert get(0x110064) == 0x3F000000 and get(0x11006C) == 0x12345678
            allowed = (
                set(range(0x2EED00, 0x2EF000))
                | set(range(0x121020, 0x121028))
                | set(range(0x123000, 0x123000 + len(names) * 12))
                | set(range(0x110058, 0x110064))
            )
            for i in range(len(names)):
                allowed.update(range(0x1240D0 + i * 0x100, 0x1240D4 + i * 0x100))
            assert all(all(a + k in allowed for k in range(n)) for a, n in writes)
            rows.append(
                {
                    "native": wrapper["native"],
                    "Kinect_catalog_count": count,
                    "Kinect_ready": ready,
                    "case": scenario,
                    "mapped": scenario == "normal",
                    "OK_and_progress_preserved": True,
                }
            )
report = {
    "scope": __doc__,
    "patch_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "passed": True,
    "cases": rows,
    "native_mash_selectors_executed": [hex(x) for x in selectors],
    "outer_native_bodies": "late-reset ordering fixtures; not full gameplay",
}
(source.parent / "clash-prompt-cpu.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print("Passed", len(rows), "clash prompt/catalog/fallback cases")
