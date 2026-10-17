# Original cloud research environment

Use the existing checkout; each managed task is already isolated. Do not create unnecessary worktrees or overwrite prior session names. Private inputs originally lived in `/workspace/artifacts/zforkinect`; local third-party tools in `/workspace/tools`. These paths are historical defaults, not files provided by a public clone.

`tools/setup_environment.py` verifies and restores retained archives in that snapshot. A new machine needs its own game copy and the tools listed in [building](building.md); the retained archives are not redistributed. Ghidra analysis uses `dbz-xenon.xex` with `PowerPC:BE:64:Xenon`, not the obsolete generic-PPC analysis.

```sh
python3 tools/debug_session.py serve my-new-session --seconds 1800 --patches experiments/gamepad-final-v1.0.0 --gpu vulkan --apu sdl --profile-source /path/to/isolated-local-profile/content --display :100
python3 tools/debug_session.py request my-new-session '{"command":"screenshot","name":"state"}'
python3 tools/debug_session.py request my-new-session '{"command":"pause"}'
python3 tools/debug_session.py request my-new-session '{"command":"resume"}'
python3 tools/debug_session.py request my-new-session '{"command":"stop"}'
```

The supervisor owns only its child and virtual display. One game per display; the display lock rejects collisions and input drivers use separate per-display locks. The timeout continues during pause. Null GPU verifies logic only and may log expected draw failures; it does not produce gameplay images. SDL audio can use a dummy driver for timing without sound output.

For precise input on slow Lavapipe use `probe_native_frames.py`: a short wall-clock key pulse may miss a native frame. `verify_runtime_patch.py` compares the actual chosen diagnostic/public startup image, excluding mutable counters. `verify_hd_runtime.py` verifies glyph allocations/data; screenshots are still required for visible placement. `coordinate_audit.py SESSION CAPTURE --pause` checks typed geometry without live writes.
