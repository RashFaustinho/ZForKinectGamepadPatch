# Optional content-complete save — American (USA) edition

**Generated primarily with AI.** For Dragon Ball Z for Kinect, USA Xbox 360
edition in Xenia, Title ID `4E4D084E`, module `8FDD4F4AB147612A`.

[Download DB_SAVE](DB_SAVE). Size: **150,000 bytes**. SHA-256:
`08f6df33f0a4a79d1be117f210b7cf295cd189ea309b68cc7604d4ebad132ca9`.

## Contents and verification

All identified Story/Score Attack content, 55 character groups and 67 valid
variants are available. **No power-up is active.** Scores remain zero; this
file does not fabricate maximum ranks, leaderboards or Xbox achievements.
Card Reader can still apply bonuses and custom parts normally.

The American game loaded all 150,000 bytes identically and reached its native
main menu with the patch's automatic-content-unlock hook removed. The checksum
is valid and the active-card flag is clear. This is a native load/data check,
not a complete playthrough. [Report](../../../research/published-usa-save-runtime.json),
[manifest](manifest.json) and [checksums](SHA256SUMS).

The data format and file bytes are also compatible with the verified European
save. Both editions have the same Title ID and normally share a save directory
when you use the same Xenia profile. Use different local profiles if you want
separate progress for each edition.

## Installation

1. Launch your American copy once with your intended local Xenia profile,
   allow a normal save to be created, then close Xenia.
2. Find Xenia's Storage root in its log. Locate the existing file
   `content/<your-profile-XUID>/4E4D084E/00000001/SystemData/DB_SAVE`.
3. **Back up the whole existing `4E4D084E` folder**, including
   `Headers/00000001/SystemData.header`. Replacing DB_SAVE replaces current
   progress, scores and settings with this generated state.
4. Replace only the existing `SystemData/DB_SAVE` with the downloaded file.
   Keep your own local profile and existing `SystemData.header`.
5. Relaunch using that same local profile. Restore the backup with Xenia
   closed if you want your original progress back.

No account/profile or account-bound header is included. This is Xenia's
extracted folder format, **not a signed STFS save for a physical Xbox 360**.
If your Xenia build uses another layout, locate its actual SystemData save
before copying. The source generator can create a matching legacy header in
a new private output directory using your own local profile XUID:
[create_content_save.py](../../../tools/create_content_save.py).

The gamepad patch already enables content availability, so this save is
optional. To remove a card you equip later, use
**Options → Reset Power-Up Card → Yes**.
