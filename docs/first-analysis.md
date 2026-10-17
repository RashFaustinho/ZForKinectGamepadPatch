# Initial original-game analysis — historical baseline

On 2026-10-15, Xenia Canary b735063 on Linux x86-64 with Xvfb/Lavapipe rendered the original Bandai logo, save notice and title screen. The local archive was 7,394,712,958 bytes; the ISO was 8,738,846,720 bytes with extraction CRC `603CEC00`. No game download links, disc images or original binaries are distributed here.

The title requested “Raise your hand in the sensor's field of view to start.” A second test connected a keyboard-driven controller (slot 0) and sent A/Start through XTest, but remained at the title. Individual guest reads of those events were not traced, so that was not proof that the game ignored every pad input. `headless=true` also suppresses system dialogs, including Kinect Tuner; it did not establish that the in-game banner was fixed. Audio was disabled (`apu=nop`).

A restart test recreated the virtual display and reached the title again. The supervisor intentionally stopped each run after 90 seconds; exit -15 indicated deliberate termination, not a crash. No battle, physical controller, real GPU performance or save functionality was confirmed by this baseline.

The original executable is `Dbkn.exe` inside `default.xex`, image base `82000000`, entry `8237ED60`, European Title ID `4E4D084E`, Media ID `320B3C10`. The [address reference](address-reference.md) records exact hashes and static call candidates. The game statically links XDK NUI/NUIHNDL 2.0.21076.0. A PsCamDeviceRequest export was unimplemented in the tested Xenia source and marked in the import log; a static call to it was not proof that it ran during the baseline.

The initial strategy was to trace the hand-raise transition, establish identity/presence/calibration, follow gesture recognition into native actions, and supply a skeleton only where continuous joint coordinates were necessary. Later findings required both an action bridge and coherent joints. [Development history](development-history.md) records that transition.

The original disc/XEX inspection and decoded-image reconstruction source is now in `tools/inspect_disc.py` and `tools/analyze_code.py`. XEX addresses are guest addresses, not offsets into an encrypted/compressed container. The original ISO/XEX were not patched on disk.
