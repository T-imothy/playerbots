# Encounter resurrection, summon recovery and hazards

Development continuation after Playerbots commit 6005d6ce. These changes are not
part of the already delivered realm patch notes or deployed binaries.

| Encounter | Change | Cores |
| --- | --- | --- |
| Flamelash | Damage bots prioritize his own living Burning Spirits, choosing the spirit closest to him. Native attackability, crowd control, range, manual targets and healer/tank assignments still apply. | Classic, TBC, Wrath |
| Whitemane | Missing Mograine or rejected Deep Sleep preserves the ready transition. Rejected Scarlet Resurrection retries after one second. Combat resumes only after Mograine's native SpellHit records SPECIAL; an interrupted cast retries instead of releasing the phase early. Dead, out-of-combat and stale encounter callbacks are ignored. | Classic, TBC, Wrath |
| Skyriss | Rejected 66%/33% illusion casts leave the action ready. Accepted summons retain their one-shot behavior even if the cosmetic blink fails. | TBC, Wrath |
| Dungeon Kael'thas | Gravity Lapse preserves partial sphere-summon progress across 500 ms retries, capped at three accepted summons per cycle. A rejected channel retries without releasing the phase. Rejected normal/heroic Power Feedback remains ready. The five-element teleport table rejects out-of-range indices. | TBC, Wrath |
| Ingvar | A rejected banshee summon cannot commit fake death. Annhylde retries missing boss references and rejected channel/visual/heal casts without advancing her phase. Ingvar retries his transformation independently after the helper departs. AI events require his own summon and the appropriate phase. | Wrath |
| Devourer of Souls | Wailing Souls uses the existing rotating-beam route planner. Owned Well of Souls actors enter the native hazard collector. The native wipe callback reports the encounter type rather than the creature entry. | Wrath |

## Native evidence

Flamelash is entry 9156 on map 230 in each development database. His script
directly summons Burning Spirit 9178. On arrival, 13489 kills the spirit and
its dummy effect applies 14744 to the boss. The priority excludes unrelated
summons and preserves the current target when two spirits are equally close.

Scarlet Resurrection 9232 has a two-second native cast and a scripted target
of Mograine 3976 in all three inspected databases. Existing 3400/5700 ms
salute/combat timers remain unchanged on success. Rejected casts schedule only
the retry; normal encounter completion is not inferred from a timer alone.

Devourer's native 68875/68876 aura ticks every 500 ms and rotates by 0.09 radians.
The normal/heroic beam has a five-degree cone and 100-yard radius. Well of Souls
36536 carries self aura 68854; normal 68863 and heroic 70323 have a four-yard
radius. The hazard adds one yard of clearance. Existing ownership, lifecycle,
height and bounded route checks apply. Classic/TBC beam calculations reject
this Wrath-only encounter.

## Verification and limits

Focused fixtures execute the edited production methods. They cover failure and
retry ordering, interrupted resurrection, stale callbacks, summon ownership,
100 partial-summon cycles, wrong encounter keys, 100 Devourer wipes, map/era
guards, route budgets, manual targets, crowd control and role preservation.
Full-suite and native-build results are recorded in the task worklog after
completion. No new SQL or configuration changes are required for this batch.

An accepted summon cast is not proof that every downstream native allocation
succeeded. These fixes do not certify live dungeon clears, three-dimensional
Gravity Lapse movement, complete vehicle controls or coordinated raid roles.
Mr. Smite's point callback was reviewed; no naturally occurring invalid callback
sequence was reproduced, so no speculative callback rewrite was made.
