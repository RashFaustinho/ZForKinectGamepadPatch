# Final 1.0.0 review and the launch-defense B fix

The [final European patch](../experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml) retains revision19's controls, authored arms, compact glyphs, content availability and native power-up reset. Its only functional change from that baseline is B priority in the identified launch-choice callers.

## Super Saiyan Bardock versus Full Power Frieza

Real pad navigation selected Score Attack saga1/stage5 and the native roster entry for Super Saiyan Bardock. Runtime IDs were37/52 and the custom triple[98,416,416]. The game accepted pure B as action2A at caller8220E8B8, frame10698, and latched guard choice0. Acceptance is not a claim that every B option is favorable or avoids damage.

The two original dispatchers query lateral movement before B. Executing their actual PPC instructions reproduced B losing to a left stick that remained tilted. The final helper suppresses only the four lateral query callers while B is held; the original next query chooses guard. It preserves normal guard, steps, escape gauges and unrelated QTE consumers. It does not alter deadzones or force phase/result fields.

The targeted test executes36 native choice cases,16 unrelated-caller cases and16 helper ABI/no-write cases. Eight negative cases reproduce the old B-plus-stick behavior. The original one-off human incident cannot be identified with certainty from the report; this is a reproducible cause that has been corrected.

## Source review

- Consolidated a historical overlapping array into the main block. Before the B change, every resulting byte remained identical; the release contains no overlapping writes.
- Pinned the original image and reviewed revision19 digest independently of editable reports; verified native call signatures, free-space bounds, alignment and relative branches.
- Scoped the new128-byte helper by four exact caller LR values. It preserves nonvolatile registers, stack and LR and performs no guest-data writes on its suppression path.
- Preserved every baseline byte except the integer input entry redirect and the newly added helper.
- Shared X11 input handling across recent diagnostic drivers, ensuring held synthetic keys are released on errors. Protected Card Reader reports against accidental overwrite.
- Replaced historical preview packaging with a deterministic final allowlist, checksums and exact byte comparisons. Local diagnostic patches, private profiles, saves and original game data are excluded.

All historical experiments remain available as research, including failed attempts. They are not loaded by the release. The final source supports a user-supplied private decoded image via `build_final_patch.py --image`.

## Evidence

[Fifteen final CPU suites](../experiments/gamepad-final-v1.0.0/suite-results.json) pass on SHA-256 `bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50`. The exact public startup payload/hook bytes were read back from Xenia, with thirteen native128×128 glyph resources checked byte-for-byte. The virtual pad's held state returned to zero after cleanup.

UI/arm/card payloads are byte-identical to revision19. Its native Super results7/6/5, separate Piccolo Vulkan sample, twelve card scans/valid saves, and persistent reset remain relevant within their documented scope. CPU coverage of eleven Super selectors is not graphical coverage of every character. [Final validation report](../experiments/gamepad-final-v1.0.0/runtime-checks.json).

The final TOML remains64,441 bytes. A later size-only experiment could omit about1.4KB of redundant original-equal padding, but it was not adopted. English publication changes guides/package names, not the released gameplay bytes. The complete campaign, every matchup, Windows/D3D12 and physical controller remain unverified exhaustively.
