# Revisions 14–15: context UI layers, guard and heavy Ki

Historical patch: [revision 15](../experiments/gamepad-feedback-v15/4E4D084E.gamepad-feedback.patch.toml). Revision 16 later corrected right-step priority; revision 17 replaced nearby RT+X charge with Y hold/release.

B updated guard joints instead of leaving neutral hands. Two cinematic response recognizers were disabled in free combat, where their old activation started an unrelated sequence. Y at distance used heavy Ki; close RT supplied preparation, then X punched. The separate two-choice approach loader needed LT/RB; its attack meter needed X instead of four alternating Kinect punch drawings.

Native callers re-enabled pose groups after a generic UI update. Four complete-function wrappers run the final cleanup **after** those writes. The native prohibition node retains native visibility and is ordered after the button by swapping entire 12-byte child records. Player Super artwork keeps its original path. Native renderer 8211E590 was executed to confirm button-before-seal traversal, with only ABI helpers/leaf draw callbacks fixture-bound.

CPU coverage included 384 contextual input combinations, four post-native wrappers, missing resources, idempotence and bounded writes. Prior suites included 804 numeric cases, 2,103 catalog/QTE cases and 36 charge-side cases. Inputs/poses in revision 15 matched revision 14.

The ranged heavy shot entered native state32, created type-1 projectiles and later reduced HP 43,790→37,190; held RT at range stayed in state20 without damage. A guard comparison in the same Goku/Raditz/Shield setup observed old B losing 1,000 HP while the corrected attempt retained 50,000 HP during enemy attacks. This was not universal guard invulnerability.

Vulkan captured raised arms, an open hand/heavy projectile/Y icon, and an A-approach choice with LT/RB and the prohibition **above RB**. The prohibited RB was deliberately selected to verify native reading, not to claim it was the winning option. Texture slots7/9, hidden pose groups, final node order and the native RB latch were read back. A shot capture had 60 finite typed regions, including projectiles.

Revision-14 input regression completed the Great Ape and saved next-chapter availability without global unlock; 1,792 geometry samples were finite. [Approach screenshot](../experiments/gamepad-feedback-v15/previews/approach-choices.png), [heavy shot](../experiments/gamepad-feedback-v15/previews/heavy-y.png), [guard](../experiments/gamepad-feedback-v15/previews/guard-b.png), and [report](../experiments/gamepad-feedback-v15/runtime-checks.json).
