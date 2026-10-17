# IMPORTANT DISCLAIMER: BUILT PRIMARILY WITH AI

Most research, implementation, automation and documentation was produced by
OpenAI Codex under human direction. AI-generated work can contain mistakes.
Human direction and gameplay feedback: RashFaustinho. This is an unofficial
fan project; original project work is MIT-licensed in the source repository.

# Dragon Ball Z for Kinect — Gamepad Patch 1.0.0

**EUROPEAN Xbox 360 edition only — English, French, German, Spanish, Italian.**
Title ID: `4E4D084E`. Executable module hash: `C9561ED1F9AFFED4`.
Other regions, Title Updates and modified executables are unverified.
Tested with Xenia Canary b735063 on Linux. Windows/D3D12 and physical USB
controllers were not tested in this environment.

## Installation

1. Close Xenia. Find its Storage root in the startup log.
2. Copy `patches/4E4D084E.gamepad.patch.toml` into that root's `patches` folder.
3. Remove older versions of this project's patch; load only one version.
4. Set `apply_patches = true` under `[General]` in Xenia's configuration.
5. Select a local profile, configure your controller normally, and launch
   your own European copy of the game. Back up your save first.

The log should show `Gamepad conversion 1.0.0`. No Python installation,
ISO changes or replacement executable is required for playing.

The patch is 64,441 bytes (62.93 KiB), SHA-256:
`bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50`.

## Xbox 360 controls


| Context | Input | Action |
| --- | --- | --- |
| Menus | Left stick / A / B | Select / confirm / back |
| Battle start | X | Perform the required starting punch |
| Close range | X | Normal punches |
| Long range | X | Normal Ki Blasts |
| Close range | Hold Y, then release | Charge and throw a charged punch |
| Long range | Y | Heavy Ki Blast |
| Close range | RT | Uppercut |
| Battle | Hold B | Guard |
| Battle | Left stick left / right | Lateral steps |
| Battle | A | Request a rapid approach |
| Battle | Hold D-pad Down | Charge Ki |
| Battle | Right-stick Down impulse | Lower Super, with at least 50 Ki |
| Battle | Right-stick Up impulse | Upper Super, with 100 Ki |
| Contextual choices | Displayed LB/RB/LT/RT or other button | Select the corresponding action |
| Opponent Super | B / left stick left / indicated right-stick direction | Guard / evade / counter |
| Great Ape Vegeta QTEs | Hold RT when requested | Supply the special boss gesture/pose input |

A Super request below the required Ki threshold is ignored, rather than queued. Super Attacks use a single stick impulse, without hold-to-charge or release-to-fire. Player Super preparation artwork remains original. The first-person arms use authored generic trajectories with the game's original meshes; they are not extracted CPU attack clips.

The native prohibition sign marks an unfavorable option. Recognizing its button does not guarantee a successful defense. In the launch-defense choice, B now takes priority over a left stick that remains tilted.

## Card Reader and evidence

Read [CARD_READER.md](CARD_READER.md) for the full power-up button map,
including the read → B → save → re-enter sequence for each counted press.
An unwanted Shield effect can be removed with
**Options → Reset Power-Up Card → Yes**.

[VERIFICATION.md](VERIFICATION.md) explains the final review and limits.
The archive's `validation.json`, `manifest.json` and `SHA256SUMS` identify
its exact patch and recorded checks. These checks are not an exhaustive
playthrough of every character, matchup or campaign event.

Full source, original controller artwork, probes, tests, historical
experiments and English research:
https://github.com/RashFaustinho/ZForKinectGamepadPatch

No original game files, profiles or generated saves are included.
