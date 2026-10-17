# Revision 16: separate right step, B guard, charge and HUD UVs

Historical [patch](../experiments/gamepad-feedback-v16/4E4D084E.gamepad-feedback.patch.toml) and [runtime report](../experiments/gamepad-feedback-v16/runtime-checks.json).

Original dispatcher 8220A250 checks case7 of 822A25A8 (gesture C) before lateral gates9/A. Case7 sets first-person flag2 and defensive state27. C=LS-right therefore stole rightward requests before gate29/E. In free modes4/6, C now reads held B; actual right step gate29 uses held input. Other cinematic contexts retain their original mappings. Action-C/common-slot9 icons show B in that free context; E/right-step continues showing right stick movement.

Close gesture3, bound to RT, had also entered an ordinary-strike branch before sustained charge gesture6. Suppressing that close discrete branch let the native preparation select its arm through5 and later accept X. No charge percentage, animation state or timing was forced. Historical controls were hold RT, then punch X while retaining RT; revision17 replaces that interface with Y hold/release.

Action-history HUD lettering used explicit UV endpoints independently of the clash panels. Hook822DF944 preserves the original CR6 side comparison for original art; loaded native pad resources take the unmirrored branch. Missing loader, wrong count and missing table fall back safely. CPU coverage included seven UV cases and native gate/charge dispatchers; the old revision15 negative control reproduced the right-stick defensive conflict.

In native Goku/Raditz tests, right recorded E/state9 and actual movement, left D/state8, and B followed defense without activating steps. Dodging did not guarantee invulnerability. Charged preparation reached state13, selected side and progress1.0; X reduced HP44,850→43,630 before an LB/choice1 follow-up at8229CF5C. Final Vulkan with corrected UVs again observed full charge and HP45,000→43,780, readable RT, LB/RB/LT/RT choices and the prohibition over LT. Eleven compact textures matched byte-for-byte and52 geometry regions were finite.

Screenshots: [right step](../experiments/gamepad-feedback-v16/previews/right-step.png), [B guard](../experiments/gamepad-feedback-v16/previews/b-guard.png), [charge](../experiments/gamepad-feedback-v16/previews/charged-rt.png), [follow-up](../experiments/gamepad-feedback-v16/previews/charged-followup.png). The first two precede only the later UV change; their controls/poses were unchanged.
