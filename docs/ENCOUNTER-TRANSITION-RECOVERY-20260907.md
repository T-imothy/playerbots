# Native encounter transition audit

This continuation repairs seven native encounter scripts used by the Playerbots
development builds. It changes neither the production realms nor baseline
branches. No SQL or configuration changes are required by this batch. Prepared
migrations from earlier audit batches remain separate release requirements.

## Confirmed defects repaired

| Encounter | Failure and repair | Cores |
| --- | --- | --- |
| C'Thun | Failed emerge, carapace or vulnerability casts previously had no recovery. Transitions now retry without repeating already-applied phase auras. Failed flesh-tentacle slots retry individually; only the actual current wave's two GUIDs count toward vulnerability. Entering vulnerability also cancels delayed giant-tentacle summons. | Classic, TBC, Wrath |
| Headless Horseman | The head checked health before the incoming hit, delaying the phase transition until another hit. Incoming damage now triggers the phase boundary immediately and is limited to that boundary. Late projectiles cannot advance the next phase while the head is attached. Native final-stage death prevention remains responsible for completion. | TBC, Wrath |
| Felmyst | A rejected Demonic Vapor cast consumed one of the two vapor slots. Failed attempts now retry after one second; successful attempts retain the original eleven-second interval. | TBC, Wrath |
| Freya | Failed wave casts advanced the sequence; extra wave callbacks could index past its three-entry table. Failed waves now retain their slot and retry, successful waves stop at six, and reshuffling avoids a repeated boundary wave with one bounded swap. | Wrath |
| Nethekurse | Peon deaths during the dialogue cooldown were discarded, so simultaneous kills could fail to start the fight. Death counting now runs independently of dialogue. Reset clears the dialogue flag, and a dead reinforcement no longer aborts notification of remaining living reinforcements. | TBC, Wrath |
| Keli'dan | Every setup appended the channelers again, growing the list across retries and wipes. Setup now rebuilds the list and uses its full size for iteration. Existing respawn and evade-retry behavior is preserved. | TBC, Wrath |
| Illidan | Lift-off dereferenced a missing lower trigger, indexed absent glaive targets, and advanced after failed throws. Missing targets and rejected casts now retry the same stage; equipment and flight-phase changes follow an accepted throw. | TBC, Wrath |

These are source-confirmed failure paths. No claim is made that any of them
caused a reported production crash or originated in the enhancement branch.
An accepted summon spell is not a guarantee that every downstream summon effect
completed; the repairs above state exactly which boundary they protect.

## Verification

One combined incremental build pass succeeded for Classic, TBC and Wrath,
sequentially, reusing the existing build directories. Logs are named
`build-{classic,tbc,wotlk}-transition-batch.log` in the task evidence directory.
No additional full binary package was created.

Five focused regression runners passed against extracted native methods:

- `cthun_transition_recovery_regression.py`: all three cores; partial summons,
  failed phase casts, old/duplicate deaths, reset and delayed-summon cancellation.
- `horseman_head_threshold_regression.py`: TBC/Wrath; crossing hits, overkill,
  one-health boundary, late projectiles and final-stage delegation.
- `freya_felmyst_wave_recovery_regression.py`: Felmyst in TBC/Wrath and Freya
  in Wrath; rejected casts, wave timing/caps, lifecycle and 100 shuffle seeds.
- `hellfire_reset_progression_regression.py`: TBC/Wrath; simultaneous peon
  deaths during dialogue, reset, 100 channeler setups and evade retries.
- `illidan_flight_transition_regression.py`: TBC/Wrath; missing lower triggers,
  empty/one-entry/unloaded glaive targets and failed first/second throws.

The preceding combined hazards/beam checkpoint passed the complete 135-runner
suite. The five newer runners were tested separately, bringing the available
runner inventory to 140; this is **not** a claim that a fresh complete
140-runner suite ran. Native builds verified the actual core interfaces.
No current-build live encounter clear or server-load benchmark was performed.

## Remaining boundaries

This continuation does not implement C'Thun stomach assignments, automatic
Illidan flame tanking/cage roles, Felmyst fog lanes, Freya raid assignments,
or automatic dungeon escort/event progression. Those are distinct bot features.
Illidan's downstream blade-to-flame summon effects and full flight/landing cycle
still need live failure testing. Horseman body/head spell exchanges also need a
complete event test, beyond the damage-boundary regression.

The main raid/dungeon register remains the full-encounter backlog. Its older
rows include mechanisms subsequently implemented in continuation documents;
they must not be read as a list of entirely untouched encounters. Compilation
and targeted method tests do not establish autonomous clears of every listed
raid or dungeon.
