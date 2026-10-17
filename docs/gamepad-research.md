# Early controller research — historical preview 1

See [development history](development-history.md) for corrections and the README for final controls. The early layout used hold/release Super Attacks and mapped A differently; it is not the released layout.

Ghidra 12.1.3 with XEXLoaderWV/GhidraXenon, `PowerPC:BE:64:Xenon`, replaced the generic PowerPC analysis that lost VMX128 details. Trampolines into checked alignment padding let Xenia's JIT execute new PPC without a complete game recompilation. Synthetic identity alone, neutral joints alone and a local profile alone did not fix presence; a camera-poll hook was not called. The post-logic hook at 82195550 finally retained presence data long enough for native menus.

The menu selector uses pad edges at 8211A720. Back must be processed before rejecting count=0 widgets. Tracking ID at Kinect context+2430 is not the player pad index; 27A4=4 means “back up” and prevented the initial punch. Position/presence fields had to be coherent before the starting X/Jab could load Goku/Raditz.

The virtual keyboard initially mapped K both to Y and right-thumb click; right-thumb moved to M. Checked internal masks: Y=10, A=40, X=80, B=20, D-pad Down=2 (hex). `virtual-player-11` isolated Y produced 300 damage, but the watcher name alone did not identify the visible move. The user later identified its uppercut animation.

Observed early data: X reduced Raditz 31,500→31,350→31,200; subsequent inputs reached a four-hit combo and 30,290. D-pad Down charged native Ki 0→100 through action 11 at 822241A0. Early ranged A reduced HP 31,500→31,380 in mode 6; it was not a universal ranged binding. Later contextual X replaced that design.

The first release-window implementation reversed `andis.` operands. After correction, a lower release used 50 Ki and reduced Raditz 31,500→26,709; an upper release used 100 Ki and reduced 26,709→19,509. Further upper attacks reached zero HP, but a following cinematic remained unresolved. HP zero and cinematic entry were not claimed as stage completion. Early B held entered state 80 and returned to 20; lateral D/E inputs moved the actor in opposite directions. Orientation and universal protection still needed visual checks.

The old 300-update release window supported multi-frame sequences; later single-impulse initiation and independent continuation superseded it. The full 67-action native metadata is in `research/action-mapping.json`; watcher names require verification against consumers. Actor+1130 is current state; +113C is pending state, and hexadecimal 72 means no pending transition. A readable checkpoint exported by the supervisor was not a restorable emulator savestate.

Runtime inspection was limited to owned Xenia children. New changes used a version-checked startup patch and fresh session. Intentional stops, Null-GPU expected draw failures, and experiments that did not reach a requested command are kept distinct from successful execution.
