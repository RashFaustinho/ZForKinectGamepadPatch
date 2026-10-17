# Preview 2: revised controls, boss inputs and content work

Historical design notes; use the final README for the current layout.

Human feedback changed Supers from hold/release to one impulse when enough Ki was already available. Initiation and continuation masks were separated, rejected requests were not queued, and long Super cinematics preserved follow-up windows. X became contextual normal melee/Ki; A became rapid approach; aura stayed on D-pad Down. Additional native actions went to bumpers/triggers. Native hand coordinates were moved off the menu canvas.

The Great Ape fight required more than the public action APIs. Some boss consumers read discrete recognizer-state arrays directly. `ppc_boss_input.py` mirrors active pad bindings into type-1 recognizers only for battle kind 1. Clearing aliases first, then ORing active ones, prevents an inactive alias from erasing a valid gesture. Type-6 input required a separate adapter; it presents RT to the original accumulation path. The game's thresholds, increments and phase progression remain native.

A storage-selector adapter chooses Xenia HDD for a signed-in user and preserves its notification handle, replacing a Kinect-driven system selector. The content variant invokes native availability initialization and supplies decoded card fields through the original classifier. Score records are not fabricated. [Content and saves](content-unlock.md) explains the historical variants and how the final version preserves power-up removal.

Revisions after preview 2 addressed the in-game Kinect Tuner banner, sustained combo-escape input, non-finite projectile geometry, separate prompt catalogs, compact glyphs, UI layering, input priorities, authored first-person arms and Super-defense widgets. Do not install preview 2 together with the final patch.
