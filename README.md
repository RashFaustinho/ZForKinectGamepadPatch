# ⚠️ IMPORTANT DISCLAIMER: THIS PROJECT WAS BUILT PRIMARILY WITH AI

> [!WARNING]
> **Most of the reverse engineering, patch code, test automation, and documentation in this project was produced by OpenAI Codex under human direction.** The human contributor defined the controls, tested gameplay, reported problems, and guided revisions.
>
> **AI-generated work can contain mistakes.** Read the evidence and limitations before relying on a technical claim. Passing a CPU fixture, accepting an input, rendering an animation, and completing a battle are different results. This repository documents them separately. “Final 1.0.0” identifies the released revision; it is not a guarantee that every character, event, or emulator backend is bug-free.

# Dragon Ball Z for Kinect — Gamepad Patch 1.0.0

**For the EUROPEAN Xbox 360 edition only: En/Fr/De/Es/It.**

Play the game through Xenia using a normal controller: navigate menus, fight, charge Ki, use Super Attacks, answer QTEs, and use the Card Reader without a Kinect. The patch changes the emulated game's memory at startup; it does not modify the ISO or replace `default.xex`.

| Supported build | Value |
| --- | --- |
| Region / languages | **Europe — English, French, German, Spanish, Italian** |
| Title ID | `4E4D084E` |
| Xenia executable module hash | `C9561ED1F9AFFED4` |
| Original `default.xex` SHA-256 | `d09d3c36857d930279f2657188f0b135c27d22a39306178743d4e9becd42d438` |
| Tested emulator | Xenia Canary `b735063`, Linux |

**Other regions, modified executables, and Title Updates have not been verified.** Windows/D3D12 and a physical USB controller were not tested in this environment; the automated runtime tests used Xenia's virtual controller and Linux Vulkan/Lavapipe or the Null GPU backend.

## Download and install

- **[Download version 1.0.0](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/tag/v1.0.0)** — patch, English guides, validation summary, and checksums.
- [English ZIP package](releases/v1.0.0/ZForKinectGamepadPatch-1.0.0.zip) and [archive checksum](releases/v1.0.0/ZForKinectGamepadPatch-1.0.0.zip.sha256) are also kept in the repository.
- [View the standalone TOML](experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml).

1. Close Xenia. Find its **Storage root**, shown in the startup log.
2. Copy `4E4D084E.gamepad.patch.toml` into the Storage root's `patches` folder.
3. Remove older versions of this project's patch from that folder. **Load one version only.**
4. Enable `apply_patches = true` under `[General]` in Xenia's configuration.
5. Select a local profile and launch your own European copy of the game. Use Xenia's normal controller driver.

The log should show **`Gamepad conversion 1.0.0`** being applied. No Python installation or game recompilation is needed to play. Back up your save before installing. Full instructions: [installation](docs/installation.md).

The TOML is **64,441 bytes (62.93 KiB)**. Its SHA-256 is `bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50`. The released gameplay bytes are unchanged from the final version tested with the user.

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

## Card Reader: power-up button map

The patch replaces QR-camera reading with a controller-operated catalog. **Reading a card applies it.** Cards replace the active power-up; their effects are not accumulated by scanning the whole list.

- **A:** read the current entry again.
- **LB / RB:** read the previous / next entry in the entire catalog.
- **LT / RT:** read the previous / next power-up.
- **B:** leave the result; wait for the native save and return to the main menu, then enter **Card Reader** again before the next read.

**Start each row of this table from Shield.** On a fresh Xenia launch, the first RT from the character portion of the catalog selects Shield. If you have already used the reader, cycle until the result says Shield. The reader cursor is session-local and is separate from the card equipped in your save.

| Promotional power-up | From Shield |
| --- | --- |
| Double Ki Blast | LT ×4 |
| Supreme Kai | RT ×5 |
| Guided Ki Blast | LT ×2 |
| High-Speed Ki Blast | LT ×3 |
| Unleash Ki | RT ×6 |
| Super Smash | LT ×1 |
| Shield | A |
| Kaioken ×20 | RT ×4 |
| Eternal Youth | LT ×5 |

**Each counted press means: read → B → wait for saving → re-enter Card Reader.** Repeated trigger presses on one result screen do not advance through multiple cards.

The complete RT cycle is **Shield → Kaioken → Kaioken ×3 → Kaioken ×10 → Kaioken ×20 → Supreme Kai → Unleash Ki → Eternal Youth → Double Ki Blast → High-Speed Ki Blast → Guided Ki Blast → Super Smash → Shield**.

To remove a card, use **Options → Reset Power-Up Card → Yes**. The reset persists and preserves progress. Old project-generated saves could have Shield active. An active card invokes the game's own **Power Up Card Usage** scoring rule and ×1 win multiplier in Score Attack. [Card Reader findings and save format](docs/powerup-cards.md).

## Source and research: start here

This repository includes the patch generators, PowerPC assembler, generated patches, original controller artwork, CPU tests, runtime probes, Ghidra scripts, catalogs, evidence summaries, and unsuccessful experiments. **Only the final TOML is for installation.** The `experiments/diagnostic-*` variants add local research instrumentation and must not be installed alongside it.

| For | Start with |
| --- | --- |
| Players | [Installation](docs/installation.md), [Card Reader](docs/powerup-cards.md) |
| Another developer or AI | **[Research index and handover](docs/research-index.md)** |
| How the conversion works | [Architecture](docs/architecture.md), [address reference](docs/address-reference.md), [all 67 actions](docs/action-reference.md) |
| What was tried and why | [Development history](docs/development-history.md), [initial analysis](docs/first-analysis.md) |
| What was actually verified | [Final review](docs/final-review.md), [validation methods](docs/validation.md), [final reports](experiments/gamepad-final-v1.0.0) |
| Rebuilding / extending | [Build instructions](docs/building.md), [tool and evidence provenance](docs/provenance.md) |

Fifteen PowerPC suites pass on the final patch. The exact public startup payload was read back from Xenia; thirteen native 128×128 controller textures were checked byte-for-byte. The research also records native Great Ape completion and saved progression without the global unlock hook, Super-defense responses, and all twelve power-up reads. **These are scoped results, not an exhaustive playthrough of every matchup or the whole campaign.**

Original game binaries, disc images, extracted game assets, full proprietary decompilations, account profiles, and raw process-memory dumps are not distributed. The inspection/decoding tools and documented addresses allow researchers to reproduce the work with their own game copy. Some historical scripts retain the original cloud workspace paths; [building](docs/building.md) explains the prerequisites and portable final-build path.

## License and credits

Original project code, documentation, and newly created controller artwork are provided under the [MIT License](LICENSE). Game content, screenshots of the game, Xbox/Dragon Ball trademarks, and third-party tools remain the property of their respective owners. This is an unofficial fan project.

Human direction and gameplay feedback: **RashFaustinho**. Primary AI implementation and research: **OpenAI Codex**. Research tools include [Xenia Canary](https://github.com/xenia-canary/xenia-canary), [Ghidra](https://github.com/NationalSecurityAgency/ghidra), [XEXLoaderWV](https://github.com/zeroKilo/XEXLoaderWV), [GhidraXenon](https://github.com/emoose/GhidraXenon), Unicorn, and Capstone.
