# Content availability, QR replacement, and generated saves

The final patch includes native content availability and the controller Card Reader for the European game. Historical `gamepad-layout-v2` did not automatically unlock content; `gamepad-unlocked` added that option. Do not load them together or alongside the final release.

The bridge calls native initializer821BEFC0 to enable story/Score Attack chapters and55 character groups with67 valid variants. It preserves the selected custom fighter and current bonus. An empty custom fighter uses a Goku-based default. Earlier code also equipped Shield by default; revision19/final preserve the inactive-card choice instead. Scores, maximum ranks, Xbox achievements and leaderboard records are not fabricated.

The replacement reader supplies original decoded QR fields to classifier822FF238. Its85 accepted pairs comprise67 character variants,12 bonuses, three appearance parts and three style parts. Some custom combinations need complementary scans, as in the original. The catalog is not evidence that every accepted pair appeared on a printed promotional QR card. [Full factual catalog](../experiments/content-unlock/catalog.json).

The native format stores one selected custom fighter/bonus configuration, not a permanent inventory of every scanned QR. Card reading uses the game's own result screen, application and save path. LB/RB cycle all entries, LT/RT cycle bonuses, A rereads, and B exits after saving. [Exact power-up map](powerup-cards.md).

A fresh-profile Vulkan test confirmed55 groups/67 variants, applied another Goku variant with RB, and wrote a valid native save after B. Bonus11 showed Super Smash and was saved. Later all twelve bonus names/indices were read and saved natively. An active power-up changes the normal win-bonus multiplier; removing it is a real native setting, not a hidden-text patch.

`tools/create_content_save.py` creates a150,000-byte `SystemData/DB_SAVE` and the corresponding legacy Xenia folder header. Its checksum matches the game's validator. A load test with only the gamepad patch, without automatic unlock, loaded the same150,000 bytes and received native validation state1. “100%” here means **content available**, not maximum scores/ranks or all Xbox achievements. It is a Xenia folder-format save, not a signed STFS package for a physical console.

```sh
python3 tools/create_content_save.py /tmp/new-dbzk-save --xuid B13EBABEBABEBABE
```

That XUID is a synthetic research example; use the appropriate local profile for installation. The generator refuses an existing output directory. Default bonus is now inactive; explicit `--powerup 0..11` equips one. Back up your own SystemData/header before copying a generated save under `content/<local-profile-XUID>/4E4D084E/`. The optional [published content-complete save](../releases/v1.0.0/content-complete-save/README.md) includes only generated DB_SAVE data, English installation instructions, a manifest and checksums. No account/profile is distributed. It has no active power-up and is optional with the final patch.

[Classifier/save-load evidence](../experiments/content-unlock/save-load-checks.json), [historical unlocked variant](../experiments/gamepad-unlocked), and [final card validation](../experiments/gamepad-final-v1.0.0/runtime-checks.json). Every bonus's individual combat effect was not measured.

The exact optional published save was additionally loaded in `publication-save-null-01` using the gamepad/storage patch without automatic unlocks. All 150,000 loaded bytes match its SHA-256, its native-format checksum is valid, and no power-up is active. [Account-free load/data report](../research/published-save-runtime.json).
