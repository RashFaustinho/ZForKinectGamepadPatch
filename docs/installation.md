# Installation — European edition only

Version 1.0.0 targets **Dragon Ball Z for Kinect, Europe (En/Fr/De/Es/It)**, Title ID `4E4D084E`, Xenia module hash `C9561ED1F9AFFED4`. Other editions and Title Updates are unverified. The original XEX digest is listed in the main README and [address reference](address-reference.md).

Download the final release, close Xenia, and find the **Storage root** in its log. In portable mode this may be the emulator folder; an explicit `--storage_root` overrides it. Copy `4E4D084E.gamepad.patch.toml` to `patches` under that root. Remove this project's older patch variants from the same folder. Enable `apply_patches = true` in `[General]`; the distributed patch already has `is_enabled = true`.

Use Xenia's normal controller input. Linux builds offer `hid = "sdl"`; Windows builds normally provide `any`/`xinput`. The keyboard driver used by the research probes is a virtual controller, not a requirement for playing. Select a local signed-in profile, launch your game copy, and confirm native save prompts. Back up existing saves first. The log must show `Gamepad conversion 1.0.0`; if it does not, check Storage root, patch loading, Title ID, and module hash.

The patch changes guest memory at startup. Do not replace `default.xex`, rebuild an ISO, or install Python to play. Python is needed only to rebuild or analyze the patch. The game and emulator are not included.

See the [README controls](../README.md#xbox-360-controls), [Card Reader map](powerup-cards.md), and [final review](final-review.md). The headless research environment verified Linux Xenia Canary `b735063`, Vulkan/Lavapipe and Null-GPU logic. It did not verify Windows/D3D12, a physical controller, every character, or a complete campaign playthrough.

A crossed-out choice can still register its button while producing an unfavorable native result. B has priority over a lingering lateral stick specifically in the launch-defense choice; normal guard and lateral movement remain separate. The apparent jump icon from the original Kinect UI meant rapid approach, not aura charging: aura stays on D-pad Down.
