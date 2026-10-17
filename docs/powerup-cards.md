# Card Reader, power-ups, and persistent reset

For the **European edition (En/Fr/De/Es/It)**. The [final patch](../experiments/gamepad-final-v1.0.0/4E4D084E.gamepad.patch.toml) preserves **Options → Reset Power-Up Card → Yes** across menu returns. This removes the active effect without replacing the save or losing progress.

The older generated all-content save equipped **Shield**, bonus index 0. Earlier unlock code also forced the active-card flag back on whenever the main menu was constructed. Revision 19 changed the initializer from `ori r9,r8,5` to `ori r9,r8,1` at `823025B4`, preserving the native active/inactive bit at save offset `2EEC`. The final patch retains that change. Native reset clears bit 4 and saves. The six selected-item slots `2F00..2F14` are preserved; an old stored index need not be erased when its active bit is clear.

An active card affects gameplay and removes the normal Score Attack win multiplier. The original result screen shows **Power Up Card Usage** and **×1**. The patch does not hide scoring text, force scores, or claim that this label alone indicates corruption. The native check is `82203BF0`; result handling includes `822F8770` and `822E6D70`. The reset path is `823038E0`.

## Reading cards

| Input | Native result |
| --- | --- |
| A | Read the current catalog entry again |
| LB / RB | Read the previous / next entry across the full catalog |
| LT / RT | Read the previous / next power-up |
| B | Close the result and return after native saving |

After each result, press B, wait for saving and the main menu, then re-enter **Card Reader**. Rapid repeated trigger presses on a result screen do not read multiple entries. The cursor persists within the emulator session; it is not the equipped card index saved on disk.

**Every row below starts from Shield.** On a fresh emulator launch, first RT from the character catalog selects Shield. Otherwise cycle until its native result name is Shield. Each counted press requires its own read → B → save → re-enter cycle.

| Power-up on the promotional sheet | Input from Shield | Native bonus index |
| --- | --- | --- |
| Double Ki Blast | LT ×4 | 8 |
| Supreme Kai | RT ×5 | 5 |
| Guided Ki Blast | LT ×2 | 10 |
| High-Speed Ki Blast | LT ×3 | 9 |
| Unleash Ki | RT ×6 | 6 |
| Super Smash | LT ×1 | 11 |
| Shield | A | 0 |
| Kaioken ×20 | RT ×4 | 4 |
| Eternal Youth | LT ×5 | 7 |

RT cycles through **Shield, Kaioken, Kaioken ×3, Kaioken ×10, Kaioken ×20, Supreme Kai, Unleash Ki, Eternal Youth, Double Ki Blast, High-Speed Ki Blast, Guided Ki Blast, Super Smash**, then Shield again. From any non-power-up entry, first RT chooses Shield and first LT chooses Super Smash.

The native catalog has 85 accepted pairs: 67 character variants, 12 power-up entries, three appearance parts, and three style parts. The six parts are paired to support complementary scans. This is the classifier's accepted catalog, not a claim that every pair appeared on a promotional QR sheet. A current scan replaces the active bonus; scanning all entries does not stack their effects or create a permanent card inventory.

All twelve power-ups were actually read through Xenia menus with virtual-pad input; each produced the expected native name and a saved `DB_SAVE` with a valid checksum. Shield removal was confirmed in RAM and in the file after a main-menu return. [Native catalog results](../experiments/gamepad-feedback-v19/powerup-catalog-runtime.json) and [final validation](../experiments/gamepad-final-v1.0.0/runtime-checks.json) preserve the scope. Individual combat effects of all twelve cards were not measured separately.
