# Optional content-complete save — European edition

**Generated primarily with AI.** For Dragon Ball Z for Kinect, European
Xbox 360 edition (En/Fr/De/Es/It), Title ID `4E4D084E`, using Xenia.

[Download DB_SAVE](DB_SAVE). The file is **150,000 bytes**.
SHA-256: `08f6df33f0a4a79d1be117f210b7cf295cd189ea309b68cc7604d4ebad132ca9`.

## What “complete” means

All identified Story/Score Attack content and 55 character groups with 67
valid variants are available. Scores remain zero; this does not fabricate
maximum ranks, leaderboard records or Xbox achievements. The Card Reader
can still apply QR power-ups and custom parts through the native system.
**No power-up is active**, so Shield is not equipped by default.

This is a generated native game-data file, with no account/profile included.
It is Xenia's extracted folder format, **not a signed STFS save for a physical
Xbox 360**. A fresh Xenia Null-GPU session loaded all 150,000 bytes identically with
the gamepad/storage patch and no automatic unlock hook. The native-format
checksum is valid and the loaded active-card flag is clear. This confirms
loading/data integrity, not a complete gameplay test.
[Runtime evidence](../../../research/published-save-runtime.json) and the
[manifest](manifest.json) document verification precisely;
[SHA256SUMS](SHA256SUMS) identifies the files. Generator source:
[create_content_save.py](../../../tools/create_content_save.py).

## Install into your own local profile

1. Launch the European game once with your intended local Xenia profile.
   Let it create a normal save, then close Xenia.
2. Find Xenia's Storage root in its startup log. Locate the existing file
   `content/<your-profile-XUID>/4E4D084E/00000001/SystemData/DB_SAVE`.
   Use the profile you actually play with; do not create a new profile ID.
3. **Back up the entire existing `4E4D084E` directory**, including
   `Headers/00000001/SystemData.header`. Replacing DB_SAVE replaces your
   current progress, scores and game settings with this generated state.
4. Replace only the existing `SystemData/DB_SAVE` with this downloaded file.
   Keep your own profile and existing `SystemData.header`.
5. Relaunch using the same local profile and verify the available chapters
   and roster. To revert, close Xenia and restore your backup.

If your Xenia version uses a different save layout, locate its actual
SystemData save first. Do not copy it into an unrelated account directory.
Alternatively, use the source generator with your local profile XUID to
create the matching legacy Xenia content header in a new output directory.

The final gamepad patch already enables content availability; this save is
optional. It does not replace the controller patch. Reading a power-up card
later equips that card; use **Options → Reset Power-Up Card → Yes** to remove
it. [Research and native save-format findings](../../../docs/content-unlock.md).
