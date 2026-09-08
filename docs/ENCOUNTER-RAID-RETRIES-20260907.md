# Raid and dungeon transition retry review

This development batch follows the six-encounter resurrection/hazard batch.
It has not been deployed or promoted to baseline branches.

| Encounter | Confirmed source fix | Cores |
| --- | --- | --- |
| Chromaggus | A rejected low-health enrage no longer consumes the one-shot action or emits a success emote. | Classic, TBC, Wrath |
| Thekal, Lor'Khan and Zath | Rejected resurrections retry after 500 ms. Accepted two-second casts arm a three-second recovery timer, canceled by native Revive/Reset on success. Interrupted casts therefore remain recoverable. Existing coordinated-death rules remain. Rejected Tiger Form cannot release the final phase. | Classic, TBC, Wrath |
| Ragnaros | Track actual current-wave Son GUIDs instead of decrementing an assumed eight. Old/duplicate deaths cannot shorten the new wave; early clears during the three-second animation retain the short emerge timer. Rejected summon, submerge and emerge casts preserve the pending phase. The normal 90-second fallback remains for surviving Sons. | Classic, TBC, Wrath |
| Netherspite | A rejected banish cast cannot reset threat while the boss remains in beam phase. Successful phase changes retain one threat reset each. | TBC, Wrath |
| Illhoof | Custom portal, Kil'rek and berserk timers rearm after a rejected cast instead of being permanently consumed. | TBC, Wrath |
| Shade of Aran | Record the four accepted elemental summon slots so a partial failure retries missing slots without duplicating successful ones. Rejected Dragon's Breath cannot consume the action or delay the next special. | TBC, Wrath |
| Muselek | Rejected threshold traps do not consume the action, mark the target or start the follow-up retreat. | TBC, Wrath |
| Kargath | A rejected post-dance charge remains ready. Existing blade-dance target selection and timing remain. | TBC, Wrath |
| Drakkari Colossus | Failed emerge/merge and Mortal Strikes casts retain their actions. Emerge reports acceptance to its caller before the one-shot transition is disabled. | Wrath |
| Black Knight | Initialize the next phase; reject stale/foreign resurrection callbacks and null spell targets; block all damage during fake death. A missing native feign aura retries through its existing five-second resurrection trigger. Failed full healing cannot release the next phase at zero health. An absent victim is not passed to MoveChase. A rejected Army of the Dead retries without repeating an accepted cast. | Wrath |

## Evidence and testing

Native 21108 dispatches eight instantaneous Son summon spells, 21110–21117.
Native 24173 takes two seconds; its script calls Revive, whose reset cancels the
recovery timer. Black Knight aura 67691 lasts five seconds and triggers bound
spell 67693 on its five-second tick. The recovery timer allows an additional
second before checking; an aura still present is allowed to finish.

Focused fixtures execute the edited methods/callbacks. They exercise failed and
successful casts, partial waves, old/duplicate deaths, early clears, interrupted
resurrection, native reset cleanup, absent targets, delayed callbacks, and
normal/heroic spell choices. Netherspite/Illhoof fixtures also cover both sides
of the PRENERF_2_0_3 flag. Full-suite/build results are recorded after completion
in the task worklog and source/binary checkpoint.

## Review dispositions and boundaries

The unchecked-cast scan is a candidate finder, not a bug count. Some matches
cross function boundaries or precede unrelated switch cases. Examples include
Horsemen death summons, Grobbulus melee checks, Loatheb's repeatedly ready
berserk, Sartharion's explicit retry timer and Reliquary's spawn visual.

Tharon'ja's main transformations already gate phase advancement on accepted
casts. Venoxis's phase change is gated on Snake Form; the scan caught secondary
poison casts inside that accepted transition. Netherspite's empowerment action
likewise already checks its primary cast. These observations are not complete
encounter certifications or evidence that downstream summons can never fail.

Colossus Emerge/Merge have native cast times of three/two seconds and prevention
type NONE. This fix covers rejected casts; it does not alter interrupt immunity
or certify downstream spawn allocation. Triggered companion casts and visual
effects are not automatically rewritten as phase blockers.

This batch requires no SQL or configuration changes. Full live encounter clears,
vehicle controls, escort orchestration and complete raid role assignments remain
separate from these source-level recovery fixes.
