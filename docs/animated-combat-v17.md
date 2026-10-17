# Revision 17: Y charge/release and authored first-person arms

Historical [patch](../experiments/gamepad-feedback-v17/4E4D084E.gamepad-feedback.patch.toml) and [report](../experiments/gamepad-feedback-v17/runtime-checks.json). These arm/control payloads remain in the final release.

Near Y holds native preparation and release throws one charged punch. The same actor must have accepted the close charge. Release supplies five native frames of visible extension while preparation remains valid, then one punch; changing actor, leaving close combat or being interrupted cancels the pending input. X punches nearby/Ki-blasts at distance, ranged Y is heavy Ki, close RT is the old uppercut, B guards and D/E remain lateral steps.

Finite neutral joints had left hands at waist height, so native arm visibility/culling could hide them during an otherwise accepted action. The patch retains original per-character first-person meshes, hand-pose clip and renderer, but supplies **authored generic** windup/extension/recoil/idle trajectories for accepted states10/13/29/32. The side follows native selection. Shot movement continues through idle because its native state can end before the visible arm motion. The idle-ready pose does not activate guard. These are not extracted CPU action clips or a demonstrated reuse of third-person CPU arm anchoring.

All three relevant joint buffers stay coherent. Guard and contextual QTEs retain their prior paths; player Supers and external-camera sequences use original animations. Y/RT prompts follow the new near/far context.

Eleven CPU suites passed for revision17, including release cancellation, side selection, repeated attacks, all buffer copies, register contracts and prompts. Native/Vulkan Goku–Raditz examples: nearby X44,400→44,250; Y held then released44,250→43,030 with no damage while held; ranged X43,030→42,910 with open hand and visible projectile; ranged Y sequence42,910→41,110. Thirty-five geometry captures were finite and consistent; final shots additionally had60 Vulkan and64 Null typed regions finite.

[Normal punch](../experiments/gamepad-feedback-v17/previews/punch-x.png), [charge](../experiments/gamepad-feedback-v17/previews/charge-y.png), [release extension](../experiments/gamepad-feedback-v17/previews/release-y.png), [normal Ki](../experiments/gamepad-feedback-v17/previews/ki-x.png), [heavy Ki](../experiments/gamepad-feedback-v17/previews/ki-y.png).

The session requested internal640×360 while window captures were1280×720; do not call those different quantities the same resolution. Glyph data remained128×128. These tests did not cover every character, chapter, physical controller or Windows backend.
