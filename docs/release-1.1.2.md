# IMPORTANT DISCLAIMER: BUILT PRIMARILY WITH AI

Most reverse engineering, patch code, automation and documentation was produced
by OpenAI Codex under human direction and gameplay testing by RashFaustinho.
This is an unofficial fan project. AI-generated findings can contain mistakes;
the repository preserves source, research and scoped validation evidence.

# Gamepad conversion 1.1.2 — Europe and USA

Both regional packages include the gamepad patch, English installation and
Card Reader instructions, checksums, and an **optional content-complete save**.
The two save-only ZIPs are provided for users who already installed the patch.

## Downloads

- [European patch + optional save](https://raw.githubusercontent.com/RashFaustinho/ZForKinectGamepadPatch/v1.1.2/releases/v1.1.2/ZForKinectGamepadPatch-1.1.2-Europe.zip)
- [USA patch + optional save](https://raw.githubusercontent.com/RashFaustinho/ZForKinectGamepadPatch/v1.1.2/releases/v1.1.2/ZForKinectGamepadPatch-1.1.2-USA.zip)
- [European content-complete save only](https://raw.githubusercontent.com/RashFaustinho/ZForKinectGamepadPatch/v1.1.2/releases/v1.1.2/ZForKinectGamepadPatch-1.1.2-Content-Complete-Save-Europe.zip)
- [USA content-complete save only](https://raw.githubusercontent.com/RashFaustinho/ZForKinectGamepadPatch/v1.1.2/releases/v1.1.2/ZForKinectGamepadPatch-1.1.2-Content-Complete-Save-USA.zip)
- [SHA256SUMS](https://raw.githubusercontent.com/RashFaustinho/ZForKinectGamepadPatch/v1.1.2/releases/v1.1.2/SHA256SUMS)

These are direct downloads of the versioned files in the public repository.

| Download | Supported Xbox 360 executable |
| --- | --- |
| `ZForKinectGamepadPatch-1.1.2-Europe.zip` | EUROPEAN En/Fr/De/Es/It, module `C9561ED1F9AFFED4` |
| `ZForKinectGamepadPatch-1.1.2-USA.zip` | American (USA), module `8FDD4F4AB147612A` |

Both editions use Title ID `4E4D084E`. Use the patch matching your edition and
remove the older project TOML before installing. Other executable builds and
Title Updates remain unverified. No game files are included. Use your own copy;
no ISO editing or Python setup is required to use the patch.

## Changes since the original public release

- European and American executable support with separately verified mappings.
- Normal X punches and Ki Blasts alternate right and left, including follow-through.
- Working tucked B guard, retained from 1.1.1.
- Compact 256×256 A/B/X/Y using RGBA8 GPU pixels, removing BC3 color contamination
  on their outlines.
- X displayed by the separate Super-mash/clash widget, with Kinect pose groups
  hidden after native animations. Native OK/NG effects, progress and inputs remain.

RashFaustinho reported that 1.1.2 appeared to work very well and approved this
public release. This human feedback is recorded separately from automated tests;
it does not claim exhaustive campaign or matchup coverage.

## Optional saves

Each regional patch ZIP contains `optional-save/`, including its own English
guide and native-load evidence. The save-only ZIPs contain the same files.

- All identified content, 55 character groups and 67 valid variants are available.
- **No power-up is active**; Shield is not equipped by default.
- Scores remain zero and Xbox achievements are not fabricated.
- This is Xenia's extracted `DB_SAVE` format, not a signed physical-console STFS save.
- Back up your existing save. Replace only `DB_SAVE`, keeping your own local
  profile and `SystemData.header`. Both editions loaded the same validated data
  bytes and normally share a save path for the same local profile.

The patch already enables content availability, so installing the save is optional.

## Source, research and validation

Nineteen CPU suites pass per region, including 168 clash-prompt cases. Both exact
public startup payloads and thirteen texture resources were read back in Xenia.
The European native clash-panel rendering check is an explicitly isolated LOCAL
UI display fixture; the author-side tests did not replay the full N.18/N.17
encounter or claim an organically reached clash victory. USA graphics, physical
controllers, Windows/D3D12 and every campaign/matchup were not independently
verified here.

- [README and controls](https://github.com/RashFaustinho/ZForKinectGamepadPatch/blob/v1.1.2/README.md)
- [Latest findings and reproduction](https://github.com/RashFaustinho/ZForKinectGamepadPatch/blob/v1.1.2/docs/update-1.1.2.md)
- [Card Reader map](https://github.com/RashFaustinho/ZForKinectGamepadPatch/blob/v1.1.2/docs/card-reader-1.1.0.md)
- [Research index](https://github.com/RashFaustinho/ZForKinectGamepadPatch/blob/v1.1.2/docs/research-index.md)

`SHA256SUMS` identifies the four release ZIPs. The patch and save gameplay bytes
are unchanged from the tested artifacts; this publication adds the European save
to its patch package and provides both regional save-only downloads.
