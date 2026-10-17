# All 67 native action entries and final input bindings

For the verified European image only. Native names, recognizer types, indices
and side masks come from [action-mapping.json](../research/action-mapping.json).
The bindings below are read directly from the released patch's table at
`825EBB00` (main block `825EB100 + A00`), rather than copied from an obsolete
preview. These masks belong to the bridge, not to the Xbox XInput ABI.

## Context overrides: read these before using the table

The table is a fallback, not a complete description of a move. The native
consumer, mode and caller can change its meaning. The adaptor at `825EE600`
and the final helper at `825EFE00` preserve these distinctions.

- Close range, mode 4: X punches; Y prepares a charged punch and release
  fires it after the authored visual lead. Action 02 is RT uppercut, 03 is
  disabled; 05/06 use charge-preparation state and 00 uses the release-punch
  state when armed. Normal guard is action 0C on B held. Action 29 uses LS
  right held. Actions 2A/2C are disabled as free-fight guards.
- Long range, mode 6: X makes normal Ki Blasts. Y drives the heavy-shot
  preparation/held consumers 03/06/07/08/0A; action 02 is disabled. Guard
  and right step use B and LS right respectively. The final arm provider
  supplies finite authored positions instead of an absent Kinect skeleton.
- Launch choice: while B is held, the four lateral queries with LR
  `8220E788`, `8220E81C`, `82210FA8`, `82210FC8` return zero. The original
  dispatcher then reaches action 2A. Other callers retain their behavior.
- Opponent Super, mode 10: two identified guard sites query 2C on B held.
  Evade consumers use LS left. Counter 30 uses RS down; 34/38/39/3C/3F use
  RS up. The pending-initiation and follow-up windows enforce the Ki gates.
- Cinematic action 0C retains LS right outside normal free-fight guard.
  A global B remap here previously broke contextual movement choices.
- Great Ape includes direct recognizer types as well as these action IDs.
  The type-1 route at `825EBE40` and type-6/7 adaptor supply RT-held input.
  It cannot be implemented correctly by changing this table alone.

`pressed` and `released` refer to bridge transitions. A zero-mask placeholder
has no fallback binding even if a contextual route handles it. Native names
are historical labels; for example, the name Kick alone does not prove that
the currently selected animation is a kick.

| Action (hex) | Type / index / side mask | Native watcher name | Fallback input | Source |
| --- | --- | --- | --- | --- |
| `00` | 1 / 0 / `3` | `WAT_0_FP_00_Jab` | X | pressed |
| `01` | 1 / 2 / `3` | `WAT_0_FP_02_Upper` | LB | pressed |
| `02` | 1 / 3 / `3` | `WAT_0_FP_03_Kick` | Y | pressed |
| `03` | 1 / 4 / `3` | `WAT_0_FP_04_OnChargeAtk` | RT | held |
| `04` | 1 / 17 / `3` | `WAT_1_HATK_00_Elbow` | RB | pressed |
| `05` | 1 / 5 / `3` | `WAT_0_FP_05_NormalShot` | RT | held |
| `06` | 2 / 0 / `3` | `WAT_0_FP_04_OnChargeAtk` | RT | held |
| `07` | 1 / 6 / `3` | `WAT_0_FP_06_SideShot` | RT | held |
| `08` | 1 / 7 / `3` | `WAT_0_FP_07_OnChargeShot` | RT | held |
| `09` | 1 / 8 / `3` | `WAT_0_FP_08_Repel` | B | pressed |
| `0A` | 2 / 1 / `3` | `WAT_0_FP_07_OnChargeShot` | RT | held |
| `0B` | 1 / 9 / `3` | `WAT_0_FP_09_Guard` | B | held |
| `0C` | 1 / 11 / `3` | `WAT_0_FP_11_SwayRight` | LS right | held |
| `0D` | 1 / 12 / `1` | `WAT_0_FP_12_SwayFront` | LS left | held |
| `0E` | 1 / 13 / `1` | `WAT_0_FP_13_SwayBack` | LS right | held |
| `0F` | 1 / 14 / `3` | `WAT_0_FP_14_OnChargeEn` | RT | held |
| `10` | 1 / 15 / `3` | `WAT_0_FP_15_KickSide` | Y | pressed |
| `11` | 1 / 16 / `3` | `WAT_0_FP_16_Jump` | D-pad Down | held |
| `12` | 1 / 18 / `3` | `WAT_1_HATK_01_FrontKick` | A | pressed |
| `13` | 1 / 1 / `3` | `WAT_0_FP_01_Hook` | X | pressed |
| `14` | 1 / 64 / `3` | `WAT_1_HATK_49_Boss_04_Guard` | B | held |
| `15` | 1 / 65 / `3` | `WAT_1_HATK_50_Boss_05_Sun` | LB | pressed |
| `16` | 1 / 66 / `3` | `WAT_1_HATK_51_Boss_06_SpiritPose` | RT | held |
| `17` | 1 / 67 / `3` | `WAT_1_HATK_52_Boss_07_OneHandShot` | X | pressed |
| `18` | 1 / 68 / `3` | `WAT_1_HATK_53_Boss_08_SwayLeft` | LS left | held |
| `19` | 1 / 69 / `3` | `WAT_1_HATK_54_Boss_09_SwayRight` | D-pad Down | held |
| `1A` | 1 / 70 / `3` | `WAT_1_HATK_55_Boss_Run` | A | held |
| `1B` | 1 / 71 / `1` | `WAT_2_BLST_00_path_KameKoshi` | LS left | pressed |
| `1C` | 1 / 72 / `1` | `WAT_2_BLST_00_end_KameKoshi` | LS right | pressed |
| `1D` | 1 / 73 / `1` | `WAT_2_BLST_00_charge_KameKoshi` | RT | held |
| `1E` | 1 / 23 / `2` | `WAT_1_HATK_07_HeadButt` | LB | pressed |
| `1F` | 1 / 29 / `FFFFFFFF` | `WAT_1_HATK_13_Backhand` | RB | pressed |
| `20` | 1 / 27 / `2` | `WAT_1_HATK_11_Straight` | LT | pressed |
| `21` | 1 / 21 / `1` | `WAT_1_HATK_05_BackSpinKick` | RT | pressed |
| `22` | 1 / 49 / `FFFFFFFF` | `WAT_1_HATK_34_BackCharge` | RT | held |
| `23` | 1 / 27 / `2` | `WAT_1_HATK_11_Straight` | LT | pressed |
| `24` | 1 / 59 / `FFFFFFFF` | `WAT_1_HATK_44_GuardVert` | RB | held |
| `25` | 1 / 61 / `FFFFFFFF` | `WAT_1_HATK_46_Boss_01_SwayBack` | LS right | pressed |
| `26` | 1 / 62 / `FFFFFFFF` | `WAT_1_HATK_47_Boss_02_SwayFront` | 0x4400 | held |
| `27` | 1 / 63 / `FFFFFFFF` | `WAT_1_HATK_48_Boss_03_Jump` | A | pressed |
| `28` | 1 / 57 / `1` | `WAT_1_HATK_42_SwayBack` | 0x4400 | held |
| `29` | 1 / 58 / `1` | `WAT_1_HATK_43_NormalShot` | LS right | pressed |
| `2A` | 1 / 59 / `FFFFFFFF` | `WAT_1_HATK_44_GuardVert` | B | held |
| `2B` | 1 / 60 / `FFFFFFFF` | `WAT_1_HATK_45_GuardLimb` | Y | pressed |
| `2C` | 1 / 59 / `FFFFFFFF` | `WAT_1_HATK_44_GuardVert` | B | held |
| `2D` | 2 / 10 / `FFFFFFFF` | `WAT_2_BLST_05_charge_CrouchStart` | RS down | pending Super initiation |
| `2E` | 0 / 0 / `0` | `(none)` | RS down | Super follow-up window |
| `2F` | 1 / 93 / `FFFFFFFF` | `WAT_2_BLST_04_path_Jump` | RS down | Super follow-up window |
| `30` | 2 / 11 / `FFFFFFFF` | `WAT_2_BLST_05_int_charge_CrouchStart` | RS down | Super follow-up window |
| `31` | 2 / 3 / `FFFFFFFF` | `WAT_2_BLST_00_charge_KameKoshi` | RS up | pending Super initiation |
| `32` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `33` | 1 / 80 / `FFFFFFFF` | `WAT_2_BLST_01_start_Kame2HandShot` | RS up | Super follow-up window |
| `34` | 2 / 4 / `FFFFFFFF` | `WAT_2_BLST_00_int_charge_KameKoshi` | RS up | Super follow-up window |
| `35` | 2 / 12 / `FFFFFFFF` | `WAT_2_BLST_06_charge_SpiritPose` | RS up | pending Super initiation |
| `36` | 1 / 104 / `FFFFFFFF` | `WAT_2_BLST_06_start_SpiritPose` | RS up | Super follow-up window |
| `37` | 1 / 126 / `FFFFFFFF` | `WAT_2_BLST_11_end_OneHandShoulderCharge` | RS up | Super follow-up window |
| `38` | 2 / 13 / `FFFFFFFF` | `WAT_2_BLST_06_int_charge_SpiritPose` | RS up | Super follow-up window |
| `39` | 2 / 19 / `FFFFFFFF` | `WAT_2_BLST_11_int_charge_OneHandShoulderCharge` | RS up | Super follow-up window |
| `3A` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `3B` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `3C` | 2 / 9 / `FFFFFFFF` | `WAT_2_BLST_03_int_charge_ShoulderPose` | RS up | Super follow-up window |
| `3D` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `3E` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `3F` | 2 / 9 / `FFFFFFFF` | `WAT_2_BLST_03_int_charge_ShoulderPose` | RS up | Super follow-up window |
| `40` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `41` | 0 / 0 / `0` | `(none)` | RS up | Super follow-up window |
| `42` | 1 / 10 / `3` | `WAT_0_FP_10_SwayLeft` | LS left | held |

See [architecture](architecture.md), [address reference](address-reference.md),
[coordinate audit](coordinate-audit.md) and [validation](validation.md) before
changing a consumer. CPU coverage of a route is distinct from a rendered
sample and from completing its native gameplay sequence.
