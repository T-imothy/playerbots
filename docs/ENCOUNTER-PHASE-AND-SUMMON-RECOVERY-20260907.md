# Encounter phase and summon recovery

Development continuation of the dungeon and raid audit. These changes are not
installed on the production shares or promoted to baseline branches. They require
no SQL or configuration changes. Earlier pending production SQL remains separate.

| Encounter | Native correction | Cores | Focused verification |
| --- | --- | --- | --- |
| Sindragosa | A successful 30% transition takes precedence over an expiring takeoff timer. Takeoff enters its movement phase immediately, preventing further ground attacks during departure. Arrival callbacks require the expected phase; patrol/dead/stale callbacks cannot reset the final phase. Departure for landing stops the air update before another Frost Bomb can be scheduled. | Wrath | Actual update, reset and movement callbacks: simultaneous deadlines, normal flight and landing, initial pull, stale and dead callbacks. |
| Kael'thas, The Eye | The three-second weapon-phase opening advances on its spell-hit callback. Rejected or interrupted casts remain recoverable. Seven triggered weapon casts are tracked independently so rejected payloads can retry without recasting accepted ones. Duplicate completion callbacks and obsolete phase timers cannot restart the phase timer. | TBC, Wrath | Actual opening, spell-hit and summon methods; interrupted opening, each partial payload failure, stale/dead/out-of-combat callbacks, normal/early-nerf/fast test timing. |
| Majordomo Executus | Rejected retreat teleport retains the current event step. A missing steam object or failed Ragnaros allocation keeps the summon step pending; an existing Ragnaros is not summoned again. A missing Ragnaros or rejected execution cast retains the final event step. | Classic, TBC, Wrath | Actual outro method with rejected casts, missing instance/object/creature, failed summon, duplicate summon protection and successful progression. |
| Kil'jaeden | Shield-orb counts increment in the actual summon callback. Failed allocations retry only the missing part of the wave. Death callbacks decrement only a tracked GUID once. Slot storage and position access are bounded to the three native orb positions. | TBC, Wrath | Actual summon/death callbacks and combat action; partial allocation, old/duplicate deaths, slot reuse, full capacity and oversized requested count. |

The Kael'thas payload mask records accepted spell casts, not a guarantee that
every downstream allocation succeeded. Majordomo's accepted casts retain their
native completion behavior; this change does not introduce a watchdog for every
visual or triggered effect. Full live encounter validation remains required.

## Evidence and uncovered mechanic gap

Local native spell data confirms Kael'thas spell 36976 casts for 3 seconds and
36958–36964 are instant payloads. Majordomo 19484 casts for 1 second and invokes
the native gossip/teleport handler; 19774 is the 10-second summoning presentation,
while the actual Ragnaros creature allocation occurs in outro step 13. Spell
19773 is the 0.5-second execution cast. Native timings remain unchanged on success.

Sindragosa's dummy spells 69712 (area selection) and 69675 (single hostile target)
have no `spell_scripts` or `dbscripts_on_spell` bindings in the queried local Wrath
world database. The checked native source registers the boss, two dragons and
Frost Bomb actor, but no Ice Tomb spell handler; no matching numeric dummy handler
was found in the core spell implementation. The phase-three code also selects a
target using 69675 but casts 69712. These are separate unresolved native mechanic
findings, not proof that bot positioning or a binary-only change implements Ice
Tombs. No speculative spell binding or substitute tomb behavior was added.

## Verification record

Focused runners: `sindragosa_phase_order_regression.py`,
`kael_weapon_phase_regression.py`, `majordomo_event_recovery_regression.py`, and
`kiljaeden_orb_lifecycle_regression.py` all passed. The combined native builds and
156-runner suite are tracked in the task's verification logs and checkpoint.
This document does not certify a raid clear, live route, or server-load result.
