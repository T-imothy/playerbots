# Raid and dungeon selection / rescue audit

This pass reviews shared bot encounter decisions and native target/container
selection in the enhancement branches. It does not certify complete raid tactics
or a successful full-instance run. The mechanic register in
[RAID-DUNGEON-AUDIT-20260906.md](RAID-DUNGEON-AUDIT-20260906.md) remains applicable;
the fixes below close individual defects and two rescue-behavior gaps.

## Changes

| Encounter | Cores | Finding and resulting behavior |
| --- | --- | --- |
| Shade of Aran | TBC, Wrath | Primary spell selection used a position in a filtered list as the original spell index. It now chooses the corresponding eligible spell, including when earlier schools are unavailable. |
| Prince Malchezaar | TBC, Wrath | Stored relay GUIDs were dereferenced without resolving them successfully. Resolve each relay, discard stale references, clear selections for each pull, and use the native evade path when both required relays are unavailable. |
| Lady Vashj | TBC, Wrath | Wave callbacks could index an empty trigger vector while the phase-two move was still pending. Retry those callbacks in one second until initialization. Rebuild the spatial references each pull; missing required quadrants after arrival cause the native encounter reset instead of dropping required waves. Normal populated-wave intervals remain unchanged. |
| Warbringer Omrogg | TBC, Wrath | Beatdown generated a random index but reset threat and attacked every processed target. Only the selected target now performs that switch. Empty target lists do not generate an invalid random range. |
| Grand Champions | Wrath | The remount callback dereferenced its former mount before the fallback check. A missing mount now enters the existing replacement search; no replacement retains the native logged failure. |
| Assembly of Iron | Wrath | Static Disruption checked stored GUID count but not resolved unit count before using the first shuffled unit. An entirely stale target list now returns safely. The farthest-two/farthest-three selection remains unchanged. |
| Keleseth | Wrath | DPS bots can prioritize their group's active Frost Tomb rescue object. Native spell 42714 is cast by the trapped player, summons entry 23965, and its EventAI channels aura 48400 on the summoner. Applies to normal and heroic. |
| Slad'ran | Wrath | DPS bots can prioritize their group's active Snake Wrap. Native death handling removes the summoner's 55126/61476 aura. Select the correct normal/heroic aura; entry 29742 belongs to the trapped player. |

The rescue additions reuse the existing Maexxna policy: same live map/instance/
phase and group, valid native ownership, an engaged boss, current aura, permitted
attack target, and no conflicting manual target or marked crowd control. Healers
and tanks keep their assignments. Current live rescue targets remain stable as
actors move. Dead/despawned objects and expired rescue auras release the priority.
No additional world scan or path search was introduced by these two map cases.

The priest emergency-heal ranking idea discussed separately is not implemented
by this change.

## Review method and evidence

The local scan covers 546 native encounter-context source files (86 Classic,
187 TBC, 273 Wrath), producing 169 selection sites in 117 grouped contexts.
These are file/site counts, not unique bosses or percentages. It strips comments
and records actual `Name` assignments instead of treating header metadata as a
registration. It can include outdoor registered bosses and companion scripts.

Selection triage checks nearby null guards, filtered-list indices, depletion,
container initialization and retained GUID resolution. Full surrounding context
was inspected for the confirmed defects and nonlocal guards such as Kargath's
count bound, Anub'arak's fixed-size sphere vector, Noth's fresh per-wave vectors,
Algalon's empty-list restart and Putricide's resolved-stalker guard. A regex scan
does not prove every pointer lifetime safe or every boss mechanic implemented.

Shared bot review covered add ownership and phase/role gates, explicit target
precedence, harmful dispels, damage/cast holds, taunt swaps, strategy activation
and movement arbitration. Existing executable regressions exercise the detailed
policies described in the linked prior mechanic reports.

Local read-only dev evidence confirms Prince's two relay spawns at different
heights, Vashj's outer-ring spawns in all four quadrants, Keleseth's native spell
chain and Frost Tomb EventAI. Slad'ran's native aura and death hooks establish
normal/heroic rescue ownership. These reads do not diagnose production data.
The affected native files at the pre-fix enhancement heads match their ManTech
baseline versions. These six native defects were already present in the baseline;
this audit did not establish them as Playerbots enhancement regressions.

## Validation

`encounter_selection_completion_regression.py` compiles the actual Aran primary
selection, Prince aggro, remount callback, Static Disruption and Beatdown blocks.
Pre-fix runs reproduce the filtered-spell assertion, stale-reference failures
and invalid empty Beatdown range. Post-fix cases exercise every spell-availability
mask, reversed/missing relays, missing/occupied/replaced mounts, empty resolved
targets, difficulty selection and each Beatdown target position.

`vashj_wave_initialization_regression.py` reproduces the empty wave-vector failure,
then tests retry, unchanged populated timers, one-shot tainted-elemental handling
and all missing/present quadrant combinations using the source validation block.
The expanded `dungeon_add_priority_regression.py` fails before the rescue cases
are added and tests both difficulties with the existing lifecycle/role/command
matrix. Native builds and the complete regression-run result are recorded in the
task artifact; they are not live boss-fight tests.
The complete cross-core regression suite passed all 92 runners for this source
checkpoint, including the two new runners and expanded rescue matrix.

## Release and remaining work

These changes require rebuilt `mangosd` binaries and matching symbols. They add
no configuration options, SQL migration or persistent state. Production files
and ManTech baseline branches are not modified by this audit pass.

The full mechanics in the earlier raid/dungeon register remain open wherever
there is no reachable bot behavior and encounter-level validation. Examples are
Razorgore eggs/orb, complete Opera/Chess, Heigan dance and Horsemen assignments,
Kael'thas items/phase roles, Vashj core delivery, Wrath vehicle encounters and
scripted dungeon escort/objective interactions. Native placeholders such as the
Vault scripts must not be presented as implemented encounters. Earlier dev-only
missing spell-list references require separate data attribution; no speculative
database replacement is included here.

Live checks for this batch are Aran interrupt locks, Prince pulls/reset with the
actual relays, Vashj phase-two arrival/waves and wipe/re-pull, Omrogg target changes,
Champion remount races, Steelbreaker's difficulty variants, and Frost Tomb/Snake
Wrap rescue in normal and heroic groups. Generic combat and passing fixtures do
not establish full dungeon or raid completion.
