# Coordinate audit and the player projectile fix

The early bridge populated context+B80, while native getter 821B7090 read context+1600 for the tracked player. Derived hand positions were NaN and affected player projectile creation. Revision 4 synchronizes both buffers, plus the tracked skeleton, before native processing. The final authored arm trajectories retain that coherence.

The audit covered skeleton getters, shoulder/pelvis frames, derived hand position/direction, limb directions, arm angles and first-person matrices. It checked finite values **and nondegenerate bases**. In normal-battle captures axis lengths were about 0.99982–1.00014 and determinants 1.00006–1.00039; limb directions were near unit length. The initial 51 typed regions became 52 with the camera transform, plus projectile regions when present. Unknown data was not reclassified as coordinates; boss layouts were handled separately.

Revision-4 evidence includes 804 CPU checks of 67 actions (integer/float, active/inactive and side selections), 1,660 samples across 15 input groups, and 2,302 boss samples with active type-5/6/7 QTE requests. All geometry in those samples was finite with nondegenerate bases; full snapshots preserved joint equality. Some initial Y/left/upper-Super samples had no accepted native command and were not counted as successful action execution. Upper Super was subsequently requested with actual 100 Ki.

A close left-step gate queried action 28 before preparing D. The bridge added held LS-left there while retaining LT as an alternative. This was found by following the consumer rather than trusting the action table alone.

A ranged X projectile against Raditz had origin approximately (-8.29,21.35,71.31), direction (0.374,-0.049,-0.926), and direction length about 0.9999994. All 54 sampled descriptors had finite origin, direction, speed and dimensions. First object observation was about 0.123 s after input; 120 damage was observed around 0.703 s. These sampled Null-GPU times demonstrate a flight interval, not exact universal timing. A separate Vulkan test later showed the flash and projectile with Goku and Shield.

The first boss audit observed 25 phase indices, not necessarily consecutive because native branches differ. Context deallocation was not itself claimed as victory; later locked-next-chapter tests verified saved progression separately. Revision 13 added 1,893 finite boss geometry samples, and revision 14 recorded 1,792. These are per-session counts, not interchangeable evidence for all revisions.

Sources: `tools/coordinate_audit.py`, `probe_action_coordinates.py`, `probe_projectiles.py`, `check_action_values_cpu.py`, `check_feedback_cpu.py`, and [the revision-4 summary](../experiments/gamepad-feedback-v4/coordinate-audit-summary.json). A finite virtual baseline alone did not solve arm visibility; [revision 17](animated-combat-v17.md) addressed the distinct culling/trajectory issue.
