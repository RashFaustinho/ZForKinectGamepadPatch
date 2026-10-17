# Score Attack fixes: Tuner, gauges, geometry and prompts

Historical revisions 4–13; current controls are in the main README.

The user reported an always-visible Kinect Tuner banner, near-impossible hip escape accumulation, invisible player Ki shots, and unclear Kinect poses. The fixes were separate:

- Disable the dedicated in-game Tuner update/draw component; Vulkan confirmed no banner. Headless suppression of system dialogs alone had not solved it.
- Use **held** lateral/gauge inputs instead of one edge, so original per-frame increments continue. In an isolated native block with increment 0.05, an old one-edge input remained at 0.05 after 30 frames while each held response reached native cap 1.0; no coefficients or result flags were patched.
- Update both derived joint buffers before hand processing. Finite real projectile generation and later Vulkan visibility were verified separately from HP damage.
- Replace native prompt paths with authored pad glyphs, cover both extra catalogs, avoid mirrored lettering, and retain original player Super poses.

The early Vulkan banner/punch screenshot preceded the final joint correction; it is not evidence of the corrected projectile. A later corrected capture showed D-pad Down and no banner; a separate Goku/Raditz/Shield run showed flash and flight. The higher-resolution compact assets arrived in later revisions. Revision 13 completed the Great Ape with saved native progression without the global unlock hook.

See [coordinate audit](coordinate-audit.md), [follow-up checks](follow-up-validation.md), [compact prompts](controller-validation.md), and the associated historical JSON reports. Diagnostic variants add counters only to local research sessions; they are not installable alongside the release.
