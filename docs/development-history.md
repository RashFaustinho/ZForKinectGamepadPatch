# Development history: successful and rejected approaches

All work below targets the European En/Fr/De/Es/It executable. The final install is 1.0.0; historical revisions are retained as research source, not as patches to load together.

| Stage | Findings and resulting change |
| --- | --- |
| Original baseline | Linux Xenia rendered the title but required a raised hand. A connected pad alone did not establish Kinect presence. Static imports were only candidates, not evidence of executed camera calls. |
| Virtual player 01–04 | Synthetic identity, neutral skeleton and a local profile did not alone remove field-of-view errors. A camera-poll hook had a zero execution counter. |
| Virtual player 05–08 | Moving the hook after Kinect logic preserved synthesized presence. Pad menus reached Story/Raditz. Coherent distance/position fields allowed X to satisfy the initial punch gate and load Goku/Raditz. |
| Early controller bridge | Replaced integer/intensity queries with 67 bindings. A diagnostic K-key collision with right-thumb click was corrected by moving that click to M. Native pad masks were checked against `82351138`. |
| Early Super windows | An incorrect `andis.` source/destination order generated valid assembly with wrong semantics. Corrected release windows worked; a later human preference changed Supers to single impulses with sufficient Ki. |
| Preview 2 / content work | Contextual X, A approach, D-pad Down aura, extra shoulder/trigger actions, hidden menu hands, native storage selection, Great Ape QTE bridge, native content unlocks and pad-operated cards. |
| Revision 4 | Removed Kinect Tuner, changed gauge responses from edges to held input, and synchronized both derived joint buffers. This fixed non-finite player hand/projectile geometry. Added contextual texture paths. |
| Revisions 5–7 | Covered additional pose catalogs, context-dependent QTE requests and static prompts. Wrapper placement mattered: native callers could re-enable the old pose groups afterward. |
| Revisions 8–13 | Authored HD/compact glyphs; preserved 128×128 native BC3 allocation size. Fixed charged-arm side initialization, alternate extra-pose catalog flag 8000, boss type-6/7 prompts, and native menu text rendering. Glyph content reduced to 55% after human feedback. |
| Revisions 14–15 | Heavy ranged Ki moved to Y, guard arm pose improved, approach LT/RB and attack-meter X paths covered, and final UI cleanup ran after native pose setup. Prohibition signs were ordered above buttons. |
| Revision 16 | A priority gate interpreted rightward stick as defensive C before reaching the actual right step. B now supplies that gate in free combat, right step uses held input, and the ordinary attack no longer steals charge preparation. Fixed the separate action-history HUD UV mirror. |
| Revision 17 | Near Y hold/release, RT uppercut, authored first-person trajectories and visible idle hands. The release keeps preparation through a five-frame visual extension and emits one native punch. Meshes/hand poses/renderer remain native. |
| Revisions 18–19 | Opponent Super defense uses a separate widget loader: cover all eleven native selector variants, including RS up/down counter differences. Native two-gesture timing needed earliest-valid gating. A second scripted guard caller also needed B. Preserve native power-up reset instead of reactivating Shield at the main menu. |
| Final 1.0.0 | Consolidate one historical overlapping array with unchanged resulting bytes. Fix B losing to a lingering stick only in four exact launch-choice callers. Verify fifteen CPU suites, public startup memory and thirteen texture resources; package a frozen TOML. |

## Corrections worth preserving

The user correctly reported that Y's old visible attack was an uppercut rather than the “Kick” implied by a watcher label, that the jump symbol was rapid approach rather than aura charging, that pad punches/Ki did not display first-person arms, that only the player's Ki looked absent, that Super-defense icons had separate variants, and that a stale stick could take priority over B. These reports changed the implementation; earlier notes must not be treated as the final control specification.

Invisible Ki was not assumed to be a GPU bug simply because the opponent's shots rendered. The hand processor read context+1600 while the bridge initially filled only B80. Later, finite neutral joints still put hands at waist height, allowing native arm culling; visible deterministic trajectories solved a separate issue. A damage reduction alone had not proved visible shots or arms.

Repeated charge attempts could fail before arm-side selection. Held preparation actions 5/7 let the native charge consumer choose a side rather than leaving -1. Later Y release needed to retain preparation until the native punch, not simply stop holding the charge mask.

Finite coordinates, accepted gestures, HP zero, deallocated context, and chapter unlock are separate facts. Great Ape progression was tested on an isolated profile with the next chapter locked and the global unlock hook removed, then verified in native RAM and a valid saved DB_SAVE. A simple context disappearance was not called victory.

The final launch-guard test found pure B accepted in the requested Bardock/Frieza matchup. Isolated execution reproduced eight B-plus-stick failures and verified the scoped fix. The precise cause of the user's one-off event remains uncertain; unfavorable native choices still produce unfavorable results.
