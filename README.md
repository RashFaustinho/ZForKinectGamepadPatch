# ⚠️ IMPORTANT DISCLAIMER: THIS PROJECT WAS BUILT PRIMARILY WITH AI

> [!WARNING]
> **Most of the reverse engineering, patch code, test automation, and documentation in this project was produced by OpenAI Codex under human direction.** The human contributor defined the controls, tested gameplay, reported problems, and guided revisions.
>
> **AI-generated work can contain mistakes.** Read the evidence and limitations before relying on a technical claim. Passing a CPU fixture, accepting an input, rendering an animation, and completing a battle are different results. This repository documents them separately. “Final 1.0.0” identifies the released revision; it is not a guarantee that every character, event, or emulator backend is bug-free.

# Dragon Ball Z for Kinect — Gamepad Patch 1.1.2

**Supports the EUROPEAN edition (En/Fr/De/Es/It) and the American (USA) edition.** Use the patch for your exact executable module. Other builds and Title Updates are unverified.

Play through Xenia with a normal controller: menus, combat, Ki charge, Super Attacks, QTEs and the Card Reader. The patch applies to emulated memory at startup; no ISO edits or executable replacement are needed.

| Supported Xbox 360 build | Europe | USA |
| --- | --- | --- |
| Title ID | `4E4D084E` | `4E4D084E` |
| Xenia module hash | `C9561ED1F9AFFED4` | `8FDD4F4AB147612A` |
| Media ID | `320B3C10` | `31D7559F` |
| Original `default.xex` SHA-256 | `d09d3c36857d930279f2657188f0b135c27d22a39306178743d4e9becd42d438` | `c4d487f1be66b4484aedee63abd509a20138d283f4f91e074e367521afe24ace` |

Tested emulator: **Xenia Canary b735063, Linux**. Runtime checks use a virtual controller, Vulkan/Lavapipe and, where specified, the Null backend. Physical USB controllers and Windows/D3D12 were not tested in this environment.

## What changed in 1.1.2

- **Clean A/B/X/Y contours:** the remaining red outline artifacts came from BC3 color blocks. The four compact 256×256 faces now use uncompressed RGBA8 GPU pixels. A measured annulus on B changes from 285 reddish texels to zero; loaded GPU bytes match the authored PNG exactly.
- **X on the Super-mash/clash widget:** the previously unpatched second punch-picture selector is covered, along with cleanup after native animations. OK/NG effects, progress and input timing retain their native behavior.
- **Working guard and alternating attacks preserved:** the user confirmed the 1.1.1 guard works; its pose/input and normal X code and trajectories are byte-identical here. Both regions pass nineteen CPU suites. The author-side clash rendering check uses an explicitly LOCAL native UI display fixture; the complete N.18 versus N.17 encounter was not replayed. RashFaustinho subsequently reported that 1.1.2 appeared to work very well and approved public publication ([recorded feedback](research/user-feedback-1.1.2.json)).

[1.1.2 findings, source and validation](docs/update-1.1.2.md), [1.1.1 guard and allocation research](docs/update-1.1.1.md), [1.1.0 arm alternation and USA port](docs/update-1.1.0.md).

## Download and install

[Latest public release: v1.1.2](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/tag/v1.1.2) · [Release notes](docs/release-1.1.2.md)

Choose **one** package for your edition:

- [Europe 1.1.2 ZIP — patch + optional save](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/download/v1.1.2/ZForKinectGamepadPatch-1.1.2-Europe.zip) — En/Fr/De/Es/It, module `C9561ED1F9AFFED4`.
- [USA 1.1.2 ZIP — patch + optional save](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/download/v1.1.2/ZForKinectGamepadPatch-1.1.2-USA.zip) — module `8FDD4F4AB147612A`.
- [Standalone European TOML](experiments/gamepad-v1.1.2-europe/4E4D084E.gamepad.patch.toml) / [American TOML](experiments/gamepad-v1.1.2-usa/4E4D084E.gamepad.patch.toml).
- [Original European 1.0.0 release](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/tag/v1.0.0) and its [frozen patch](experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml).

1. Close Xenia and back up your save. Locate its **Storage root** in the startup log.
2. Remove older versions of this project's patch from that root's `patches` folder.
3. Copy the TOML from your chosen regional ZIP's `patches` folder into it.
4. Set `apply_patches = true` under `[General]` in Xenia's configuration.
5. Select your local profile and launch your own copy of the matching edition. Use Xenia's normal controller driver.

The log should identify `Gamepad conversion 1.1.2 (Europe)` or `(USA)`. No Python installation is required to play. Each package includes English instructions, the Card Reader map, a verification summary and SHA-256 checksums.

The original European 1.0.0 remains **64,441 bytes (62.93 KiB)**, SHA-256 `bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50`; it has not been replaced or modified. The 1.1.2 artifacts have their own hashes and validation reports.

## Optional content-complete save

[European save and guide](releases/v1.0.0/content-complete-save/README.md) / [American save and guide](releases/v1.1.0/content-complete-save-USA/README.md). It enables identified chapters and all 55 character groups / 67 variants, with **no active power-up**. Scores and Xbox achievements are not fabricated, and no account profile is included. Both editions loaded the same generated game-data bytes with the automatic unlock hook disabled. Both regional packages include their optional save; both editions normally share a save folder for the same local profile. The patch already enables content availability, so this save is optional.

Save-only downloads: [Europe](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/download/v1.1.2/ZForKinectGamepadPatch-1.1.2-Content-Complete-Save-Europe.zip) / [USA](https://github.com/RashFaustinho/ZForKinectGamepadPatch/releases/download/v1.1.2/ZForKinectGamepadPatch-1.1.2-Content-Complete-Save-USA.zip). They contain the same independently loaded game-data bytes, with regional guides and verification.

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

Each 1.1.2 region has nineteen recorded CPU suites, exact public startup/resource readback and scoped European UI rendering evidence. See [the current report](docs/update-1.1.2.md). Version 1.1.0 had fifteen PPC regression suites plus its native-setter/arm-tail suite. Runtime evidence and its exact scope are documented in [the 1.1.0 report](docs/update-1.1.0.md). The original European 1.0.0 startup and thirteen controller textures were separately verified. The research also records native Great Ape completion and saved progression without the global unlock hook, Super-defense responses, and all twelve power-up reads. **These are scoped results, not an exhaustive playthrough of every matchup or the whole campaign.**

Original game binaries, disc images, extracted game assets, full proprietary decompilations, account profiles, and raw process-memory dumps are not distributed. The inspection/decoding tools and documented addresses allow researchers to reproduce the work with their own game copy. Some historical scripts retain the original cloud workspace paths; [building](docs/building.md) explains the prerequisites and portable final-build path.

## License and credits

Original project code, documentation, and newly created controller artwork are provided under the [MIT License](LICENSE). Game content, screenshots of the game, Xbox/Dragon Ball trademarks, and third-party tools remain the property of their respective owners. This is an unofficial fan project.

Human direction and gameplay feedback: **RashFaustinho**. Primary AI implementation and research: **OpenAI Codex**. Research tools include [Xenia Canary](https://github.com/xenia-canary/xenia-canary), [Ghidra](https://github.com/NationalSecurityAgency/ghidra), [XEXLoaderWV](https://github.com/zeroKilo/XEXLoaderWV), [GhidraXenon](https://github.com/emoose/GhidraXenon), Unicorn, and Capstone.
