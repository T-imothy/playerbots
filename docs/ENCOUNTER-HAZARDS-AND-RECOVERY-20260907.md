# Native hazards and transition recovery

This continuation belongs to the existing development enhancement audit. It
does not certify full encounters, routes, raid clears or production deployment.

## Rotating beams

C'Thun's Eye and the Lurker Below use their actual self-owned rotation auras,
native cone table and periodic rotation direction. Position selection considers
the upcoming sweep and the bot's movement speed, rather than treating either
beam as a circular explosion. The complete candidate route is checked against
that sweep, including whether an initially safe route crosses into it. Four
candidate distances limit native route queries to eight per calculation.

Combat and reaction engines both receive the escape action and movement hold.
An already safe bot stops an old chase without canceling a stationary heal.
Ground hazard escape remains available. Queued actions recheck the boss, aura,
map, instance and destination. The Lurker's exemption requires both native
`IsInWater` and `IsInHighLiquid`; mere contact with water is insufficient.
Automatic diving or a proven route through either actual room is not claimed.

## Actor hazards

The shared hazard collector now recognizes these specific native effects:

| Encounter | Actor/effect | Scope |
| --- | --- | --- |
| Archimonde | Moving Doomfire source and its native trail radius | TBC/Wrath |
| Hungarfen | Player-summoned mushrooms, using their upcoming Spore Cloud radius | TBC/Wrath |
| Jan'alai | Armed Fire Bombs until the native explosion removes their aura | TBC/Wrath |
| Zul'jin | Feather Vortexes and Columns of Fire | TBC/Wrath |
| Supremus | Active volcanoes and moving Molten Flame sources | TBC/Wrath |
| Razorscale | Normal and heroic Devouring Flame | Wrath |
| Kologarn | Both normal/heroic player-summoned Focused Eyebeam actors | Wrath |
| Marrowgar | Moving Coldflame source | Wrath |
| Blood Queen | Player-dropped Swarming Shadows | Wrath |

Passive actors need not enter combat. Admission requires a live engaged native
boss, the actor's own actual warning/damage aura, same instance and suitable
height, and a finite radius obtained from native spell data. Player-owned actors
also require the precise summon spell and a group-member summoner GUID. Such
an effect may remain dangerous after its player dies. These rules produce fresh
positions through the existing hazard service; they do not create persistent
obstacles or change native spells. Classic has no actors from this table.

Blood Queen's actual chain includes summon spell 71266. Creature EventAI row
3816301 applies aura 71267 on spawn; the absence of a creature addon is not a
missing aura. Hungarfen's warning aura is 31690 and the native Spore Cloud is
34168. Kologarn's two summon spells are 63343 and 63701, not nearby vehicle IDs.

## Native recovery

Ionar previously waited for exactly five movement notifications and advanced a
health threshold even when Disperse failed to cast. Wrath now tracks the GUIDs
of actual returning sparks, ignores duplicate/foreign callbacks, tolerates
missing/dead sparks, and retries failed or interrupted Disperse at the same
threshold. A failed merge cast leaves the split eligible for retry. Repeated
Disperse effect callbacks cannot create another full wave while already split.

Reliquary of Souls in TBC/Wrath now retries failed essence casts without
consuming the transition. Soul waves count successful casts up to the native
total. The summon timer stops when the next essence starts. Reset initializes
the intermission state and tolerates missing instance data. Delayed or unrelated
movement callbacks cannot restart an intermission after its phase has changed.

Delrissa in TBC/Wrath accepts completion notifications only for the four selected,
boss-owned companions. Each GUID counts once, and the death-line array index
cannot exceed its four entries. This is callback hardening; a production crash
from that path has not been reproduced.

## Verification status

The new actual-method regressions passed: actor hazards and beams in all three
era builds, Ionar's native failure paths in Wrath, and Reliquary/Delrissa in
TBC/Wrath. They exercise failed casts, partial waves, duplicate callbacks, reset,
phase changes, ownership, route crossings, rotation direction and water state.

All three native builds passed, and the combined suite passed 135 of 135
regression runners. The task checkpoint-hazards-beams.json records the source
and binary hashes for this checkpoint; later transition edits require separate
verification. No new SQL or configuration is required by this
continuation. Earlier prepared audit migrations remain separate requirements.
Production files, databases and baseline branches have not been changed.

The wider audit remains open. This batch does not add Zul'jin healer casting
suppression, Ionar spark kiting assignments, Blood Queen bite/pact assignments,
or native vehicle/event strategies. Those cannot be inferred from a working
ground-hazard collector.


