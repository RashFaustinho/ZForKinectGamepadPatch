"""Drive normal X attacks and observe native arm choices in an owned session.

Uses frame-counted pad pulses and read-only native/bridge fields. No HP, Ki,
phases, distance, animation or battle outcome is written. Contextual recovery
uses ordinary buttons; partial runs are reported as incomplete, not success.
"""

import argparse, fcntl, json, struct, time
from pathlib import Path
import battle_state as b
from coordinate_audit import request, snapshot
from virtual_pad import VirtualPad

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("session")
p.add_argument("name")
p.add_argument("--kind", choices=("near", "far"), required=True)
p.add_argument("--attacks", type=int, default=4)
p.add_argument("--seconds", type=float, default=300)
p.add_argument("--warmup-frames", type=int, default=0)
p.add_argument("--capture", action="store_true")
p.add_argument("--ranged-entry", choices=("normal", "charged"), default="normal")
a = p.parse_args()
b.connect(a.session)
target = b.endpoint.parent / (a.name + ".json")
if target.exists() or not a.name.replace("-", "").isalnum():
    p.error("Choose a new simple report name")
lock = open(b.input_lock_path(), "a")
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
rows = []
accepted = []
images = []
audits = []
capture_context = []
pad = VirtualPad(b.display_name())
held = None
release_at = 0
next_pulse = 0
last_frame = -1
last_stamp = 0xFFFFFFFF
capture_pending = None
recovery = 0
start = time.monotonic()
initial_frame = b.word(0x8266E184)
request({"command": "resume"})


def pulse(key, frame, duration=3):
    global held, release_at, next_pulse
    pad.key(key, True)
    held = key
    release_at = frame + duration
    next_pulse = frame + max(22, duration + 10)


try:
    while time.monotonic() - start < a.seconds:
        frame = b.word(0x8266E184)
        if frame == last_frame:
            time.sleep(0.03)
            continue
        last_frame = frame
        if held and frame >= release_at:
            pad.key(held, False)
            held = None
        s = b.sample()
        actor = s["players"][0]
        stamp = b.word(0x8266EC08)
        mode = s["mode"]
        mask = b.word(0x8266EC04)
        row = {
            "frame": frame,
            "mode": mode,
            "state": actor.get("state"),
            "action": actor["last_action"],
            "side": actor["last_action_side"],
            "input": s["bridge"]["held"],
            "opponent_hp": s["players"][1]["hp"],
            "accepted_stamp": stamp,
            "latched_side_mask": mask,
            "committed_side_mask": b.word(0x8266EC10),
        }
        rows.append(row)
        if stamp != 0xFFFFFFFF and stamp != last_stamp:
            last_stamp = stamp
            if mode == (4 if a.kind == "near" else 6):
                event = {
                    **row,
                    "sequence_index": len(accepted),
                    "side_verified_in_native_actor": actor["last_action"] == 0
                    and actor["last_action_side"] == (1 if mask == 2 else 0),
                }
                accepted.append(event)
                print(json.dumps(event), flush=True)
                if a.capture and len(images) < 2:
                    capture_pending = (stamp, mask, len(accepted))
        if capture_pending and frame - capture_pending[0] >= 4:
            stamp, mask, index = capture_pending
            request({"command": "pause"})
            name = f"{a.name}-{index}-" + ("right" if mask == 2 else "left")
            images.append(request({"command": "screenshot", "name": name}))
            audit = snapshot()
            audits.append(audit)
            joints = next(
                x["values"] for x in audit["regions"] if x["name"] == "raw_joints"
            )
            left = joints[7 * 4 : 7 * 4 + 3]
            right = joints[11 * 4 : 11 * 4 + 3]
            capture_context.append(
                {
                    "expected_mask": mask,
                    "committed_mask": b.word(0x8266EC10),
                    "phase": b.word(0x8266E810),
                    "left_hand": left,
                    "right_hand": right,
                    "selected_hand_further_forward": (
                        right[2] < left[2] - 0.03
                        if mask == 2
                        else left[2] < right[2] - 0.03
                    ),
                }
            )
            request({"command": "resume"})
            capture_pending = None
        if len(accepted) >= a.attacks and not held and capture_pending is None:
            break
        if held or frame < next_pulse or frame - initial_frame < a.warmup_frames:
            continue
        idle = mode in (4, 6) and actor.get("state") in (0, 1, 20)
        if idle:
            if mode == 6 and a.kind == "near":
                pulse("space", frame)
            elif mode == 4 and a.kind == "far" and a.ranged_entry == "charged":
                pulse("k", frame, 45)
            else:
                pulse("j", frame)
        elif mode in (5, 8) and actor.get("state") not in (70, 71, 110):
            key = ("1", "e", "q", "3", "b", "a", "d", "j")[recovery % 8]
            pulse(key, frame, 24 if key in ("a", "d") else 3)
            recovery += 1
        elif mode == 0 and actor.get("state") in (70, 71):
            pulse("j", frame)
finally:
    if held:
        pad.key(held, False)
    pad.close()
    request({"command": "pause"})
    result = {
        "scope": __doc__,
        "session": a.session,
        "kind": a.kind,
        "complete": len(accepted) >= a.attacks,
        "requested_attacks": a.attacks,
        "accepted": accepted,
        "samples": rows,
        "screenshots": images,
        "geometry_audits": audits,
        "capture_context": capture_context,
        "elapsed_seconds": round(time.monotonic() - start, 2),
    }
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(target, flush=True)
if not result["complete"]:
    raise SystemExit(1)
