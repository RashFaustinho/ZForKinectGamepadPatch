# Rebuilding and extending the European patch

The final gameplay TOML is frozen at SHA-256 `bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50`. English documentation and release packaging do not change those bytes. The final builder pins its revision-19 input independently of editable reports and verifies the original image before checking its four native launch-choice call sites.

## Rebuild the final artifact from your own executable

Python 3.11+ handles TOML. Inspection/analysis dependencies are pinned in `tools/analysis-requirements.txt`; only Cryptodome/Capstone are needed for the initial decoder, and Unicorn is needed for CPU execution tests. The final generator itself uses the Python standard library plus the project's integer emitter.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/analysis-requirements.txt
python3 tools/inspect_disc.py /path/to/your-european-game.iso --output /path/to/private/analysis
.venv/bin/python tools/analyze_code.py --artifacts /path/to/private --xenia-source /path/to/xenia-canary-b735063
python3 tools/build_final_patch.py --image /path/to/private/analysis/Dbkn.image.bin --output /tmp/dbzk-final-build
```

`inspect_disc.py` creates the private `default.xex` and filesystem metadata. `analyze_code.py` reconstructs the basic-compressed image using the XEX format implemented by Xenia and checks the supported European original digest. It reads Xenia's public format constants from the supplied source checkout; no account key or credential is needed or embedded. An optional `--baseline-log` adds import-thunk call analysis. The rebuilt image must match `72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b`.

The final builder consumes the committed revision-19 TOML, consolidates an old overlapping array, and adds the scoped B-priority adapter. It refuses a changed predecessor, unexpected original instructions, occupied cave, out-of-range branch, unrelated byte change, or different existing output. Rebuilding identical output preserves existing validation metadata. Rebuilding a candidate does not by itself validate it for release.

## Full historical regeneration

The repository retains the layered research generators and hash-checked intermediate TOMLs. Start with `build_virtual_player.py --pose --postlogic --selector --combat --revised-layout`, then `build_content_unlock.py`, the feedback/catalog/HD/compact/context/final-panel/step-guard/animated-combat builders, and finally `build_super_defense_patch.py`, `build_powerup_selection_patch.py`, and `build_final_patch.py`. Read each builder's pinned predecessor before running it; revision numbers are research snapshots, not a single generic option.

The historical pipeline expects the original cloud layout:

- `/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin` and associated private metadata;
- `/workspace/artifacts/zforkinect/analysis/ui-boot-decoded/7.bin` for verifying original SPR slot names and allocations;
- `/workspace/tools` for the tested emulator, Ghidra/Xenon, JDK and Python environment.

`extract_ui_research.py` reads AFS/STPZ/SCD0/SCL0 resources from your own disc. It never edits the disc or publishes extracted assets. `make_hd_button_assets.py --size 128 --content-scale .55 --include-super-defense` builds the authored final glyphs. The historical `setup_environment.py` restores retained local archives using checksums from `tool-artifacts.json`; those third-party archives are not included and it is **not a fresh-machine installer**. Adapt the documented paths or recreate the workspace layout when reproducing the full historical pipeline.

## Tests

The fifteen final suite names and exact patch digest are in [suite-results.json](../experiments/gamepad-final-v1.0.0/suite-results.json). Each test accepts `--patch`. For example:

```sh
.venv/bin/python tools/check_bridge_cpu.py --patch experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml --report-name bridge-regression-cpu.json
.venv/bin/python tools/check_launch_guard_cpu.py --patch experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml
```

CPU tests require the private verified image at their documented workspace path. They do not run without the game inputs. Publication CI performs source/metadata/documentation checks and explicitly does not claim to rerun game-dependent CPU or emulator tests.

To use runtime probes, start one owned `debug_session.py serve` per display, with a new session name and isolated profile copy. Probe scripts send pad events and read only their session's guest memory. Do not attach to an unrelated emulator or combine input drivers on one display. Pause, capture, resume and stop affect only the supervisor's child. [Cloud-session examples](cloud-start.md).

## English release packaging

Run `python3 tools/validate_publication.py`, then `python3 tools/package_patch.py`. Packaging requires the final hash, all fifteen recorded suites, and the public startup readback to agree. It uses a fixed file allowlist, deterministic ZIP metadata, byte comparisons, and SHA-256 checksums. No game, private profile, diagnostic patch or generated save is bundled. Only release documentation/package names changed to English; gameplay bytes remain the tested 1.0.0.
