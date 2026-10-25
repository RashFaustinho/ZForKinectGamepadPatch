"""Check the actual emitted guard skeleton after both accepted X arm sides.

This checks the PPC pose-selection/copy chain, native B query and geometry,
not rendered character meshes. The separate native/Vulkan report covers that.
"""

import hashlib
import json
import math
import struct
from pathlib import Path

fixture = Path(__file__).with_name("check_alternating_arms_cpu.py")
scope = {"__file__": str(fixture), "__name__": "guard_fixture"}
exec(compile(fixture.read_text().split("checks = []")[0], str(fixture), "exec"), scope)
c, frame, query, setter = (scope[k] for k in ("c", "frame", "query", "setter"))
put, get, source = (scope[k] for k in ("put", "get", "source"))
rows = []


def guard(mode, state, history):
    for held_frame in range(20):
        frame(mode=mode, state=state, held=0x20, edge=0x20 if held_frame == 0 else 0)
        assert query(0xC) == 3
        raw = bytes(c.mem_read(0x1010D0, 320))
        assert (
            raw == bytes(c.mem_read(0x101B80, 320)) == bytes(c.mem_read(0x102600, 320))
        )
        vectors = list(struct.iter_unpack(">4f", raw))
        assert all(math.isfinite(x) for v in vectors for x in v)
        for elbow, wrist, hand, shoulder in ((5, 6, 7, 4), (9, 10, 11, 8)):
            assert vectors[elbow][1] < vectors[shoulder][1] < vectors[hand][1]
            assert (
                vectors[hand][2] > 2.30
            )  # A short guard reach, distinct from a strike.
            assert vectors[wrist][2] > 2.34
            first = [x - y for x, y in zip(vectors[shoulder][:3], vectors[elbow][:3])]
            second = [x - y for x, y in zip(vectors[wrist][:3], vectors[elbow][:3])]
            dot = sum(x * y for x, y in zip(first, second))
            cosine = dot / math.sqrt(
                sum(x * x for x in first) * sum(x * x for x in second)
            )
            assert cosine > 0.8, "Guard elbow is not tightly bent"
        for l, r in ((5, 9), (6, 10), (7, 11)):
            assert vectors[l][0] == -vectors[r][0] and vectors[l][1:] == vectors[r][1:]
        assert get(0x8266E80C) == 0 and get(0x8266E810) == 0
    rows.append(
        {
            "mode": mode,
            "native_state": state,
            "history": history,
            "held_frames": 20,
            "hands": [vectors[7], vectors[11]],
            "native_B_result": 3,
        }
    )
    frame(mode=mode, state=1 if mode == 4 else 20)
    assert query(0xC) == 0
    assert bytes(c.mem_read(0x1010D0, 320)) != raw


for mode in (4, 6):
    guard(mode, 1 if mode == 4 else 20, "idle")
    for side in range(2):
        frame(mode=mode, state=1 if mode == 4 else 20, held=0x80, edge=0x80)
        setter(mode)
        for _ in range(5):
            frame(mode=mode, state=10 if mode == 4 else 29)
        guard(mode, 77, "accepted X side " + str(side))
    frame(mode=mode, state=13 if mode == 4 else 32, held=0x10)
    guard(mode, 13 if mode == 4 else 32, "Y preparation")
    frame(mode=mode, held=0x8000)
    assert query(0xC) == 0 and query(0x29) == 3

report = {
    "scope": __doc__,
    "patch_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "passed": True,
    "cases": rows,
    "guard_held_frames": sum(x["held_frames"] for x in rows),
}
(source.parent / "guard-pose-cpu.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    "Passed", len(rows), "guard histories;", report["guard_held_frames"], "held frames"
)
