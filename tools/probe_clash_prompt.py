"""Observe the native Super-mash widget using pad X and read-only UI traversal.

An optional LOCAL native tutorial-group selector can make the existing lesson
accessible. This driver never writes phases, Ki, HP, progress or UI state.
"""

import argparse, fcntl, json, struct, time
import battle_state as b
from coordinate_audit import request
from virtual_pad import VirtualPad

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("session")
p.add_argument("--capture", action="store_true")
p.add_argument("--seconds", type=float, default=120)
a = p.parse_args()
b.connect(a.session)
lock = open(b.input_lock_path(), "a")
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)


def named_part(scene, name):
    owner = b.word(scene + 0x14)
    count = b.word(owner + 0xC)
    table = b.word(owner + 8)
    assert count < 4096
    for i in range(count):
        part = b.word(table + i * 4)
        if part:
            ptr = b.word(part + 0xD4)
            if ptr and b.read(ptr, len(name) + 1) == name.encode() + b"\0":
                return part
    return 0


def panel():
    ui = b.word(b.word(0x82649298) + 0x64)
    widget = b.word(ui + 0x68)
    resource = b.word(widget + 0x34)
    scene = b.word(resource + 4)
    part = named_part(scene, "p_ico_dummy_000")
    root = named_part(scene, "i_pl_grp")
    groups = {}
    if root:
        node = b.word(root + 0xB8)
        count = int.from_bytes(b.read(node + 0xC, 2), "big")
        table = b.word(node + 8)
        assert count <= 64
        for i in range(count):
            child = b.word(table + i * 12 + 4)
            nameptr = b.word(child + 0xD4)
            name = b.read(nameptr, 80).split(b"\0")[0].decode()
            groups[name] = bool(b.word(child + 0xD0) & 1)
    loader = b.word(0x82649134)
    texture = b.word(b.word(loader + 0xDC) + 3 * 4)
    return {
        "widget": hex(widget),
        "vtable": hex(b.word(widget)),
        "active": b.word(widget + 0x48),
        "visibility_state": b.word(widget + 0x40),
        "progress": struct.unpack(">f", b.read(widget + 0x60, 4))[0],
        "dummy_part": hex(part),
        "dummy_texture": hex(b.word(part + 0x24)) if part else None,
        "X_texture": hex(texture),
        "groups": groups,
        "X_mapped": bool(part and b.word(part + 0x24) == texture),
    }


start = time.monotonic()
initial = b.word(0x8266E184)
rows = []
success = False
last = None
with VirtualPad(b.display_name()) as pad:
    request({"command": "resume"})
    try:
        while time.monotonic() - start < a.seconds:
            f = b.word(0x8266E184)
            pad.key("j", f % 6 < 3)
            row = panel()
            row["frame"] = f
            t = b.word(0x8264933C)
            row["lesson"] = b.word(t + 0x2C) if t else None
            signature = (
                row["visibility_state"],
                row["progress"],
                row["X_mapped"],
                row["lesson"],
            )
            if signature != last:
                rows.append(row)
                last = signature
            hidden = all(
                not row["groups"].get(n, True)
                for n in (
                    "a_pl_attack_anm_grp",
                    "i_pl_attack",
                    "a_pl_guard_anm_grp",
                    "i_pl_guard",
                )
            )
            if (
                row["active"]
                and row["visibility_state"] == 2
                and row["X_mapped"]
                and hidden
                and f - initial > 12
            ):
                request({"command": "pause"})
                if a.capture:
                    request({"command": "screenshot", "name": "clash-X"})
                success = True
                break
            time.sleep(0.1)
    finally:
        pad.key("j", False)
        request({"command": "pause"})
report = {
    "scope": __doc__,
    "passed": success,
    "session": a.session,
    "samples": rows,
    "final": panel(),
    "screenshot": "clash-X.png" if a.capture and success else None,
    "full_N18_vs_N17_match_reproduced": False,
}
(b.endpoint.parent / "clash-runtime.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(
    json.dumps(
        {
            "passed": success,
            "session": a.session,
            "rows": len(rows),
            "final": report["final"],
        }
    )
)
if not success:
    raise SystemExit(1)
