# Research index and handover for developers and AI

Start by reading the prominent AI disclaimer in the [README](../README.md). This is research for the **European En/Fr/De/Es/It executable only**. Absolute guest addresses are not raw encrypted-XEX file offsets. Do not apply them to another edition or a Title Update.

## Suggested reading order

1. [Architecture](architecture.md): per-frame bridge, native action APIs, synthetic skeleton, rendering and UI.
2. [Address reference](address-reference.md) and [67-action reference](action-reference.md): identities, pointers, offsets, binding sources, and contextual overrides.
3. [Development history](development-history.md): failed approaches, why each revision exists, and superseded assumptions.
4. [Validation](validation.md): the distinction between isolated CPU execution, accepted native input, rendering, and saved progression.
5. [Final review](final-review.md): the B-plus-stick conflict, final-byte audit, and release boundaries.
6. [Building](building.md) and [provenance](provenance.md): reconstruct inputs from your own game, rebuild, test, and understand missing private artifacts.

Topic notes retain the technical sequence: [initial analysis](first-analysis.md), [early gamepad work](gamepad-research.md), [preview-2 changes](preview-2.md), [coordinate audit](coordinate-audit.md), [follow-up runtime checks](follow-up-validation.md), [compact prompts](controller-validation.md), [UI layers and guard](combat-feedback-v15.md), [right-step priority](step-guard-v16.md), [first-person arms](animated-combat-v17.md), [Super defense](super-defense-v19.md), [content unlocks](content-unlock.md), and [Card Reader](powerup-cards.md).

## Repository layout

| Path | Contents and intended use |
| --- | --- |
| `tools/build_*.py`, `tools/ppc_*.py` | Original patch generators and PowerPC emitters |
| `tools/check_*_cpu.py` | Tests that execute emitted/native PPC instructions on Unicorn |
| `tools/debug_session.py`, `tools/probe_*.py` | Owned Xenia sessions, pad events, and read-only observations |
| `tools/make_*_probe.py` | LOCAL diagnostic variants; never install alongside the release |
| `tools/ghidra` | Scripts for pdata correction and focused function/reference export |
| `tools/inspect_disc.py`, `tools/analyze_code.py` | Disc/XEX inspection and decoded-image reconstruction from a user-owned copy |
| `assets/controller*` | Authored controller glyphs and their raster/compression outputs |
| `experiments/gamepad-final-v1.0.0` | Final TOML, manifest, fifteen-suite results, and scoped validation |
| Other `experiments/*` | Historical code, reports, screenshots, and unsuccessful research variants |
| `experiments/content-unlock/catalog.json` | Factual native character/card identifiers and relationships |
| `research/action-mapping.json` | All 67 native action/recognizer identifiers and watcher names |
| `research/native-input-evidence.json` | Exported, account-free structured observations of the final investigation |

Earlier experimental TOMLs are retained because generators build on hash-checked predecessors and failed experiments explain later fixes. They are not alternative recommended installs. `gamepad-final` is an intermediate normalization candidate; **`gamepad-final-v1.0.0` is the released artifact**.

## Rules that prevented misleading conclusions

- Follow an action to its native consumer. Watcher labels such as “Kick” did not reliably describe the visible attack.
- Distinguish an input queried by a tutorial detector from a response latched by the actual battle choice widget.
- Native guard, lateral steps, escape gauges, launch choices, and Super defense can query different action IDs.
- A finite matrix can still be degenerate. Check axis lengths/determinants and both derived joint buffers.
- A Null-GPU run has no visual evidence. An allocation/readback check does not establish that the expected icon was drawn.
- A game HP reduction is not by itself evidence of a visible projectile, correct arms, victory, or saved progression.
- Scope ABI fixtures precisely: Unicorn PPC32 needs Xenon 64-bit spill/restore helpers emulated; those fixtures are not the complete Xbox execution environment.
- The graphical Super-defense shortcut selects an existing tutorial lesson. It is excluded from the public patch and is not counted as a full-course completion test.
- New runtime changes use a startup TOML and a fresh session. The supervisor never writes live guest memory or forces HP, Ki, timers, battle phases, animations, or wins.

Do not treat the old session paths in JSON reports as public download links. They identify the original private evidence; public summaries, relevant screenshots, source, and numeric reports are included. Raw memory and original game code/assets are not redistributed. [Provenance](provenance.md) states the exact boundary.
