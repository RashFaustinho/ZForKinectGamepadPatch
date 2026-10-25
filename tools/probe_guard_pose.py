"""Send genuine held B/X pad events and capture read-only guard geometry.

Owns one session's input lock. No live memory writes or forced native states.
Screenshots require a real rendering backend; Null GPU only checks data flow.
"""

import argparse
import fcntl
import json
import time
import battle_state as b
from coordinate_audit import request, snapshot
from virtual_pad import VirtualPad

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("session")
parser.add_argument("--capture", action="store_true")
parser.add_argument("--after-x", action="store_true")
args = parser.parse_args()
b.connect(args.session)
lock = open(b.input_lock_path(), "a")
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
rows = []


def advance(frames):
    start = b.word(0x8266E184)
    deadline = time.monotonic() + 120
    request({"command": "resume"})
    while b.word(0x8266E184) - start < frames:
        if time.monotonic() > deadline:
            raise TimeoutError("Native frames did not advance")
        time.sleep(0.05)
    request({"command": "pause"})


with VirtualPad(b.display_name()) as pad:
    try:
        for history in ["idle", "after_X_1", "after_X_2"] if args.after_x else ["idle"]:
            if history != "idle":
                pad.key("j", True)
                advance(3)
                pad.key("j", False)
                advance(3)
            pad.key("b", True)
            advance(100 if history == "idle" else 30)
            geometry = snapshot()
            state = geometry["state"]
            assert state["mode"] in (4, 6), state
            assert int(state["bridge"]["held"], 16) & 0x20
            assert state["players"][0]["control_flags"] & 2, state
            raw = next(r for r in geometry["regions"] if r["name"] == "raw_joints")[
                "values"
            ]
            assert raw[7 * 4 + 1] > 0.83 and raw[11 * 4 + 1] > 0.83
            assert raw[7 * 4 + 2] > 2.30 and raw[11 * 4 + 2] > 2.30
            assert geometry["all_finite"] and geometry["joint_buffers_equal"]
            name = "guard-" + history.lower()
            if args.capture:
                request({"command": "screenshot", "name": name})
            output = b.endpoint.parent / (name + "-geometry.json")
            output.write_text(json.dumps(geometry, indent=2) + "\n")
            rows.append(
                {
                    "history": history,
                    "native_frame": state["bridge"]["frame"],
                    "mode": state["mode"],
                    "native_action": state["players"][0]["last_action"],
                    "native_state": state["players"][0]["state"],
                    "guard_flag": True,
                    "hands": [raw[28:32], raw[44:48]],
                    "finite": True,
                    "joint_buffers_equal": True,
                    "screenshot": name + ".png" if args.capture else None,
                }
            )
            pad.key("b", False)
            advance(3)
    finally:
        request({"command": "pause"})
report = {
    "scope": __doc__,
    "session": args.session,
    "passed": True,
    "cases": rows,
    "note": "After-X rows identify input history; this driver does not certify an accepted X attack. Actual setters are covered by the CPU regression.",
}
(b.endpoint.parent / "guard-runtime.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps({"passed": True, "session": args.session, "cases": len(rows)}))
