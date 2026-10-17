# Revision 13: compact controller prompts

Historical patch: [revision 13](../experiments/gamepad-feedback-v13/4E4D084E.gamepad-feedback.patch.toml), hash `2b959569f24df88dd11d7e41ad579835754913ba7ebab308de2125972fd5a663`. It is not the final install. [Runtime report](../experiments/gamepad-feedback-v13/runtime-checks.json).

Eleven authored vector glyphs were rasterized to 128×128 and centered with transparent space at **55% of the first HD footprint**. The original 32×32 pad resources already had 16 KiB allocations, equal to a 128×128 BC3 texture. Native dimensions/descriptors/data were read back; CPU tests checked allocation guards, bounded writes, fallback and idempotence. The final version adds two actual right-stick slots for thirteen resources.

Coverage includes 67 action getters, 17 common symbols, four attack/four response choices, three gauge responses, **both 21-entry extra-pose catalogs**, static approach, and boss type-6/7 pose/camera QTEs. Native resource flag 8000 selects the alternate extra catalog: its slot 14 needs A while the ordinary slot 14 needs RT. Static tutorial preview illustrations are distinct from the interactive panels covered by these tests.

Charged preparation could start without setting its arm side, leaving -1 and preventing the punch. Held preparation actions 5/7 corrected native initialization, even if the button was already held when the phase opened. Historical revision-13 controls used RT preparation then X; final Y hold/release supersedes that interface.

Four native Knockback Combo selections were observed: LB/action1E/choice1, RB/1F/2, LT/20/3, RT/21/4. Revision-11 inputs were byte-identical to revision 13 for these checks; revision 13 additionally showed LB with compact Vulkan prompts. A new Score Attack two-choice window accepted RB/action24 at caller 822C79E8, choice1 with native latch, frame14091. An isolated ready-state RB also caused 640 damage; exact elbow/forearm animation naming remained visually unconfirmed.

Great Ape completion unlocked the next chapter in RAM and DB_SAVE with the global unlock hook disabled and checksum valid. The boss's 1,893 geometry samples and a normal 52-region capture were finite. CPU records include 804 numeric-action checks, 2,103 catalog/QTE cases and 24 charge-initialization cases. The front escape that reached only about 0.564 is not counted as complete. All-character, full-campaign, Windows and physical-controller coverage remains limited.
