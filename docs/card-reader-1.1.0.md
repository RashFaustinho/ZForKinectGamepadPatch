# Card Reader — Europe and USA 1.1.0

The reader works with pad input instead of the Kinect QR camera. A card is applied when read. Power-ups replace the active bonus; reading all entries does not stack them.

| Button | Operation |
| --- | --- |
| A | Read the current entry again |
| LB / RB | Previous / next entry in the entire catalog |
| LT / RT | Previous / next power-up |
| B | Leave the result, wait for saving and return to the main menu |

Start **each row below from Shield**. On a fresh emulator launch, first RT from the character catalog chooses Shield. Otherwise cycle until the result says Shield. The session cursor is separate from the power-up equipped in your save.

| Promotional power-up | From Shield |
| --- | --- |
| Double Ki Blast | LT ×4 |
| Supreme Kai | RT ×5 |
| Guided Ki Blast | LT ×2 |
| High-Speed Ki Blast | LT ×3 |
| Unleash Ki | RT ×6 |
| Super Smash | LT ×1 |
| Shield | A |
| Kaioken ×20 | RT ×4 |
| Eternal Youth | LT ×5 |

**Each counted press requires its own read → B → save → re-enter Card Reader cycle.** Rapid presses on a result screen do not read several cards.

RT cycles through Shield → Kaioken → Kaioken ×3 → Kaioken ×10 → Kaioken ×20 → Supreme Kai → Unleash Ki → Eternal Youth → Double Ki Blast → High-Speed Ki Blast → Guided Ki Blast → Super Smash → Shield.

To remove an active bonus: **Options → Reset Power-Up Card → Yes**. This preserves progress. Shield and the Score Attack “Power Up Card Usage” / ×1 rule come from an active power-up; the patch retains the native reset. Some older project saves had Shield active.

The native classifier accepts 85 pairs: 67 character variants, 12 power-ups, three appearance and three style parts. This is not a claim that every pair appeared on a printed promotional QR. The European native reader/save/reset checks are documented in the research; the USA classifier and adapter are independently exercised on its original PPC instructions. Individual combat effects of every bonus have not been separately measured for each region.
