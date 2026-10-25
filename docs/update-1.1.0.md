# Version 1.1.0: smoother glyphs, alternating X attacks and USA port

The README's prominent AI disclaimer applies to this work. This update keeps the frozen European 1.0.0 intact and builds separate European and American candidates from it. Runtime and package results are linked below; isolated CPU tests, native accepted input, visible motion and complete gameplay remain separate claims.

## Four face buttons

The original artwork is vector-based, but the loader set texture-fetch word 3 to `00000D10`: point minification and magnification. This can expose texel steps even with a 128-pixel source. The four round buttons now use `01280D10`: linear min/mag, base-map mip policy, unchanged RGBA swizzle. The native 128×128 BC3 allocation is still exactly 16 KiB; increasing its dimensions without allocating more storage would overrun it.

Only A/B/X/Y are rerendered at four times the target size, reduced with premultiplied-alpha Lanczos, and given four pixels of RGB extension beneath transparent edges before BC3 encoding. Their 55% drawing scale remains compact. All nine other textures retain their exact BC3 hashes. Packed source size changes from 15,600 to 17,797 bytes, fitting the checked 18,432-byte padding region. The new fetch policy is applied per texture index 2..5; it does not change every game texture or sampler globally. This improves edge sampling, not the underlying maximum texture resolution.

## Native and visible arm alternation

The legacy integer query returns both side bits (`3`). The game's setters prefer the left bit, so ordinary X consistently selected the left hand. Version 1.1.0 returns `2` for right and `1` for left only for normal X in modes 4/6. A request's side is stable across repeated queries; the next side advances only at the original accepted-action setters, once per native frame. A new actor starts on the right; the same sequence continues across close and ranged combat.

A first candidate fixed native side selection but revealed a separate visual error: the game clears `actor+2538` before the authored sixteen-frame trajectory ends. The old idle-tail code then defaulted to left. The corrected build retains the committed X side at private state `8266EC10` until the trajectory ends or another native action/context supersedes it. Charged Y, heavy Y, RT, guard and cinematic paths keep native selection. The three helpers use private state at `8266EC00..EC13`; they do not write actor, HP, energy, phase or result fields.

Executable helpers: pre-pose `825ED200`, integer result `825ED400`, glyph filtering `825ED600`, retained pose side `825ED680`. The new side fixture executes both real native setters, simulates the game's short attack state followed by native idle/action reset, and checks the selected hand keeps moving in all three joint buffers. This idle-tail case fails on the earlier candidate.

## USA executable identity and port method

- Title `4E4D084E`, Media `31D7559F`, module `8FDD4F4AB147612A`, entry `8237ED10`.
- Original XEX SHA-256 `c4d487f1be66b4484aedee63abd509a20138d283f4f91e074e367521afe24ace`.
- Decoded image SHA-256 `12ce5c89e9ee9b6903745bfd459222f628c88e804363895dd54e79d1094cd088`.
- Downloaded archive SHA-256 `09dff4a8a38b3fbee2b283847971487cb25e1c13db6fa0eb66d5a94f43e8f516`; ISO extraction CRC `3AE90026`.

No game download URL/token, executable, disc or extracted game assets are committed.

Although both images have 9,585 unwind entries, their indices do not identify matching functions. A uniform delta also fails: functions and UI routines have moved differently. `region_port.py` matches unique normalized PPC contexts, masking branch displacements and absolute-address operands only for identification. Leaf routines without unwind records use their bounded gap. Actual branches and constructed native pointers are then relocated; authored replacement islands stay contiguous and shared caves must remain empty. All final records must be disjoint.

| European logical address | American address | Normalized anchor bytes |
| --- | --- | --- |
| `82195550` | `821955C8` | 64 |
| `82197118` | `82197190` | 64 |
| `82197250` | `821972C8` | 64 |
| `822A4448` | `822A4350` | 64 |
| `822A465C` | `822A4564` | 64 |
| `823498A8` | `823497A0` | 64 |
| `822EE188` | `822E0480` | 64 |

The native UI name `p_ico_dummy_000` moves from `820F15F4` to `820F15FC`; its exact data/string anchor is checked. Omission would break otherwise valid Super/UI wrappers. A first relocation-loop attempt accidentally restored rewritten low halves of constructed pointers; the native-side test caught the unchanged caller comparisons. The corrected pass preserves those fixups. [Full address/anchor report](../experiments/gamepad-v1.1.0-usa/address-map.json).

## Reproduce and validate

```sh
python tools/make_hd_button_assets.py --size 128 --content-scale .55 --include-super-defense --face-supersample 4 --face-alpha-bleed --out assets/controller-smooth
python tools/build_update_patch.py
python tools/region_port.py
python tools/check_alternating_arms_cpu.py --patch experiments/gamepad-v1.1.0-europe/4E4D084E.gamepad.patch.toml
python tools/check_alternating_arms_cpu.py --patch experiments/gamepad-v1.1.0-usa/4E4D084E.gamepad.patch.toml
```

Use the pinned analysis environment and both private verified images. `analyze_code.py` now accepts both identified XEX hashes; `debug_session.py --game --image` selects a matching disc and read-only memory signature.

The fifteen existing regression fixtures run normally for Europe. `run_ported_cpu_suite.py` adapts native-address constants/imports, the pinned image path/digest and historical negative baselines for USA. It executes American original instructions plus the American patch, preserving behavioral assertions. The digest pin changes explicitly to the known USA image; European instructions are not substituted to make a USA test pass. Each adapted run records source/patch/image hashes and address changes.

For real menu navigation, `make_navigation_probe.py` adds only a LOCAL selector pointer/caller logger. It does not select items, change combat data or ship in the public patch. Runtime drivers use genuine frame-counted pad events; no phases, coordinates, animations, health, energy or wins are forced.

[European CPU suites](../experiments/gamepad-v1.1.0-europe/suite-results.json), [American CPU suites](../experiments/gamepad-v1.1.0-usa/suite-results.json), and [European](../experiments/gamepad-v1.1.0-europe/alternating-arms-cpu.json) / [American](../experiments/gamepad-v1.1.0-usa/alternating-arms-cpu.json) side-and-tail checks identify exact candidates. Final runtime summaries and packages must identify those same hashes. No exhaustive campaign, every-character, Windows or physical-controller claim is made.

## American content-complete save

The optional [USA save](../releases/v1.1.0/content-complete-save-USA/README.md) is byte-identical to the validated European game-data file. A dedicated American Null-GPU session reached the native root menu and loaded every byte with the automatic-unlock menu hook removed; the actual original main-menu instruction was read back to confirm that condition. Checksum is valid and no card is active. The [account-free report](../research/published-usa-save-runtime.json) records the exact digest. Both editions share Title ID 4E4D084E, so the same local profile normally shares a save path. No profile or account-bound header is distributed.

## Final runtime scope

Both regional artifacts passed all fifteen regression suites plus the native-setter/idle-tail suite. Both exact public payloads and all thirteen textures were read back without LOCAL probes. Four genuine nearby X requests and four ranged X requests alternated native sides in each edition, with damage observed. Vulkan melee captures at a 1280×720 virtual display confirm the selected hand remains forward after the native side record resets; all three joint buffers agree and the captured geometry is finite. The European ranged Null-GPU audit additionally checked 68 finite typed regions.

Final ranged input/state/damage checks use Null GPU and do not claim graphical projectile coverage for 1.1.0. A separate slow software-Vulkan ranged attempt timed out during the automated transition; it is not counted as passing. The recovery driver also lost one automated European battle before reaching range; the successful rerun used a native charged Y attack and normal pad choices to enter ranged combat. An unverified assumption about a three-item menu was removed from the navigator. These are probe outcomes, not forced wins or hidden skipped checks.

[European runtime report](../experiments/gamepad-v1.1.0-europe/runtime-checks.json), [American runtime report](../experiments/gamepad-v1.1.0-usa/runtime-checks.json), and [regression history](../research/update11-regressions.json). Both ZIPs are deterministic and include English installation/Card Reader guides; the USA ZIP includes the independently loaded account-free save.
