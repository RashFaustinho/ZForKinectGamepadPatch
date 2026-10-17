# European executable: address and structure reference

**Europe (En/Fr/De/Es/It), Title ID `4E4D084E`, module `C9561ED1F9AFFED4`.**

Original XEX SHA-256: `d09d3c36857d930279f2657188f0b135c27d22a39306178743d4e9becd42d438`.
Decoded image SHA-256: `72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b`.
Image base `82000000`; original entry `8237ED60`; Media ID `320B3C10`; XDK static NUI/NUIHNDL libraries `2.0.21076.0`.

All addresses below are **guest virtual addresses**. They are not encrypted-XEX file offsets. Heap object pointers must be reread after each launch.

## Globals and native entry points

| Address | Observed role |
| --- | --- |
| `826491D8` | NUI manager pointer; `+1C` Kinect context, `+460` current Super gesture processor |
| `826490DC` | Pad manager pointer; `+98` pad state; held `+20`, rising `+28`, falling `+2C` |
| `82649298` | Battle owner pointer; `+54` battle context, `+64` UI owner |
| `826492D8` | Native mode: 4 close combat, 6 ranged, 5/8 contextual/cinematic paths, 10 Super; do not infer all subphases from this alone |
| `8264933C` | Tutorial manager/permission information |
| `8264920C` | Save manager; dereference to the native save buffer |
| `82649344` | Stage selection; saga `+8`, stage `+C` |
| `82195550` | Post-Kinect-logic per-frame hook |
| `8211A720` | Native slide selector replaced with pad edges |
| `8211AC48` | Menu presence/distance gate |
| `821DC5B0` | Menu hand-coordinate getter |
| `82197118` / `82197250` | Discrete and intensity action-query APIs |
| `821B7090` | Tracked-player joint getter reading context+1600 |
| `82192DC4`, `82358468` | Static calls to the game's XInput wrapper |
| `8237DBB8` | Wrapper calling XamInputGetState |
| `821983A0/B4/C8` | gesture.dat / watcher.dat / blast.dat references |
| `8248D520` | Static PsCamDeviceRequest call site; not proof that it ran in the baseline |
| `821DB5D0`, `821DB888` | Disabled Kinect Tuner update/draw bodies; checked space also hosts adapters |
| `8229CEA0` | Four contextual attack choices: native results 1/2/3/4, actions 1E/1F/20/21 |
| `8229D178` | Native four-choice selection/UI dispatch |
| `8220E77C`, `82210F9C` | Two original launch-choice input blocks executed by the final regression test |
| `8220E788`, `8220E81C`, `82210FA8`, `82210FC8` | Four LR values scoped by the final B-priority helper |
| `822A25A8` | Free-combat dispatcher/gates; defensive C was checked before lateral movement |
| `822A4138` | Native charged-arm selection/preparation consumer |
| `822241A0` | Aura charging through native action 11 |
| `8211E590` | Original child traversal used to verify button-before-prohibition drawing |
| `822DF944` | Separate action-history HUD UV-side comparison |
| `82194E30`, `82194FD8` | Original two-gesture Super recognizer |
| `82252E18`, `822533B8` | Normal Super defense and scoped guard query |
| `8225C008`, `8225C098` | Scripted/tutorial guard path and second scoped guard query |
| `82253A80`, `82253B68` | Super evade and counter consumers |
| `822EF2B0`, `822EF728` | Super defense texture update and visibility initialization |
| `822DF858` | Dedicated player Super pose-art loader, preserved |
| `821BEFC0` | Original content-availability initializer |
| `822FF238` | Original decoded-QR classifier |
| `82302220`, `82302508`, `822FC450` | Replacement reader, unlock adapter, main-menu hook |
| `82203BF0`, `822F8770`, `822E6D70` | Active-bonus check and native score/result handling |
| `823038E0` | Native Options reset path |

## Allocations and authored payloads

| Address / range | Use |
| --- | --- |
| `825EB100` | Main bridge, skeleton data and action-binding table; table at +A00 |
| `8266E180` | PAD1 signature and core input diagnostics |
| `8266E600`, `8266E800` | Dynamic authored pose and its local state |
| `825EC000`, `825EC800`, `825ECE00`, `8266E900` | Arm adapter, trajectory frames, charge pose, charged extension frames |
| `825EE100` | Bounded shared final UI pass |
| `825EF800`, `825EFC00` | Opponent Super texture/visibility wrappers |
| `825EFD00` | Native-timed synthesized Super follow-up input |
| `825EFE00` | Final, four-caller-only B-priority helper (128 bytes) |
| `825ED840` | Thirteen HD texture records plus sentinel |
| `826BB800` | Packed controller data, 15,600 bytes, below `826C0000` |
| `8210EC00` | Native decoded-card pair catalog used by the replacement reader |
| `8266E1C0` | Reader cursor/state, separate from saved active card |

Diagnostic variants may occupy `825EB780`, `825ECE80`, `825ED200..D800`, `825EF700`, and writable data padding `8266E1D0..E3EC`. **Those local counters and the lesson-entry fixture are excluded from the final patch.** Do not assume executable zero padding is writable at runtime; Xenia protects code pages.

## Native object fields

| Object | Fields |
| --- | --- |
| Kinect context | tracking ID `2430`; menu events `2780/2784`; distance/position `2788/278C`; presence `2790`; position error `27A4`; absence counter `27AC`; source/derived joint buffers as documented in architecture |
| Normal battle context | actor pointers `2FC0/2FC4`; attack phase `307C`; two-choice phase `30F8`; combo phase `3134`; native helper `82206E20` returns context+3000, `82205138` returns context+307C |
| Normal actor | character ID `34`; current/pending state `1130/113C`; control pointer `2580`; last action `2530`; side `2538`; action progress `253C` |
| First-person control | enabled `80`; control flags `84`; charge flags `88`; input suppression `264`; native draw delay byte `21A`; arm-cull flags `220` |
| Super processor | state `0`; frame `10`; result `14`; earliest valid `3C/40`; expiry `44/48`; prepare/shoot quality `4C/50` |
| Super defense widget | kind `34` (0 counter / 1 evade / 2 guard), evade type `38`, counter type `3C`, UI object `40`, technique variant `4C`, visibility state `50`, active `58` |
| UI owner | Super widgets `5C/60/64`; native launch-choice UI `90` |
| UI parts | root child-list pointer `B8`; name pointer `D4`; node flags `D0`; dummy texture `24`, flags `20`; child records are 12 bytes |
| Save buffer | card flags `2EEC`; custom-fighter triple `2EF4/2EF8/2EFC`; six selected-item slots `2F00..2F14` |

For the Super sequence base `q = context+1150`: attacker `+370`, defender `+D10`, normal phase `+1CBC`, scripted phase `+1D04`, counter type `+1CF4`, result `+16D4`. Results observed: 5 counter, 6 evade, 7 guard. The D10 address also begins the second actor record: respect the context and do not treat every overlapping field as an independent layout.

The final reported matchup used native character IDs **37 (Super Saiyan Bardock)** and **52 (Full Power Frieza)**, saga 1 / stage 5, and custom triple `[98,416,416]`. These observations identify the test; they are not new universal offsets for another executable.
