# Encounter counter initialization

Development-only continuation of the dungeon and raid audit. No database or
configuration changes are required, and no production binaries are replaced.

| Encounter | Correction | Scope |
| --- | --- | --- |
| Ouro | Initialize the melee-range check counter to the same `-1` state used after a valid melee target. A first pull without a reachable tank no longer increments uninitialized memory. | All three cores |
| Skeram | Initialize the corresponding Earth Shock range-check counter on reset. | All three cores |
| Kael'thas, The Eye | Initialize the Pyroblast counter and reset it for every phase-four Shock Barrier, preserving the native three-cast sequence each time. Discard an obsolete queued sequence after leaving phase four. | TBC and Wrath |
| Gruul | Initialize the look-around callback flag and set it before dispatching Ground Slam. Both immediate and delayed spell-hit callbacks consume it once. | TBC and Wrath |
| Auriaya's Feral Defender | Initialize the maximum Feral Rush count instead of mistakenly assigning the difficulty-dependent limit to the current count. Preserve the native six/ten rush limits and 400-ms/12-second intervals. | Wrath |
| Halion | Initialize physical-realm Flame Breath to 15 seconds, consistent with the paired shadow-realm initial timer and the existing 15–20-second repeat window. | Wrath |

The actual native reset/action/callback code is exercised by
`encounter_counter_initialization_regression.py`. Coverage includes initial
out-of-melee pulls, melee recovery, rejected casts, repeated three-Pyroblast and
six/ten-rush sequences, stale phase actions, immediate/delayed Gruul callbacks,
and Flame Breath timer boundaries. This is source behavior verification, not a
claim of exact retail pull timings or a successful live raid clear.

The initialization scan is a candidate finder. Fields initialized by a reset
helper, a phase-entry handler, a derived constructor, or `JustRespawned()` must
not be reported as uninitialized merely because they are absent from `Reset()`.
Native `Creature::AIM_Initialize()` invokes `JustRespawned()` before normal AI
updates; this matters for Archimonde, XT-002 and summoned helper state.

The previous four-encounter checkpoint passed all three builds and the full
156-runner suite. This follow-up reuses the build directories and verifies the
affected native encounters without rerunning unrelated bot regression runners.
Its build results and source/binary hashes are tracked separately in the task.
