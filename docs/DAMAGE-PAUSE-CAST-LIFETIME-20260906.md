# Encounter damage pauses and cast dispatch follow-up

This is an enhancement-branch source checkpoint. It follows the encounter route,
Keli'dan, Dalliah and Hellmaw corrections documented in
`ENCOUNTER-PATH-CONTINUATION-20260906.md`. Build revisions, regression results,
matching symbols and dev runtime receipts are recorded in the task output.

## Corrected behavior

* Wrath bots pause harmful spell dispatch and melee while an engaged King Ymiron
  in Utgarde Pinnacle has normal/heroic Bane (48294/59301), or an engaged Devourer
  of Souls in Forge of Souls has Mirrored Soul (69023). Matching entry, map,
  instance/phase, proximity, height and live combat state are required. Real
  players and charmed/teleporting bots are excluded.
* Combat and reaction engines stop already-running, interruptible harmful casts,
  channels, autorepeat and queued melee spells during these windows. Execution
  rechecks the current aura and spell, so a queued reaction cannot cancel a heal
  that replaced the original cast. Helpful spells remain available.
* Wrath's native PetAI rejects new attacks and harmful autocasts during the same
  pause and stops existing harmful casts/attacks. Explicit bot pet-spell packets
  pass through the same policy. Native reaction settings are preserved, allowing
  ordinary attack acquisition to resume when the aura expires. No temporary
  passive setting is stored in pet saves.
* Bot unit, gameobject and destination spell dispatch all check the policy before
  mutating movement state. Unit/gameobject execution also verifies current native
  map/instance/phase membership. Friendly/resurrection targets are not rejected
  merely because they are dead.
* A temporary Spell was leaked when casting was rejected before SpellStart, for
  example while jumping/falling or stopping to cast. Unit, gameobject and ground
  dispatch now retain ownership until SpellStart registers the native event.
  Early returns release the object and its cast-item usage flag. Native events
  retain ownership after SpellStart, including its failure path.
* Ground-targeted casting now returns false when native SpellStart rejects the
  attempt, without recording a successful cast or waiting for it.
* A clipped movement path ending within 0.05 yards of the mover's current position
  is rejected before issuing an empty native point move. The caller can stop or
  retry using its existing behavior.
* Administrative bot action dispatch now looks up progressively shorter action
  names while retaining the full remaining parameter text. Previously, a command
  such as `do <bot> debug position ground` kept looking up the entire argument
  string and failed. A failed dispatched action also disables its temporary
  message recording, preventing continued accumulation after an error.

## Evidence and bounds

`encounter_damage_pause_regression.py` executes the production policy helpers
under all three era macros and Wrath's actual PetAI attack/cast entry points.
It covers aura changes, wrong map/instance/phase, death, charm, real players,
friendly casts, all current spell slots, launched missiles and pet reacquisition.
The pet-command admission test additionally executes actual CastPetSpell.

`cast_dispatch_lifetime_regression.py` executes the actual unit/gameobject
preparation blocks, admission prefixes and complete coordinate overload. The
previous commit reproduces a leaked unregistered Spell. The native SpellStart
implementations in all three cores register their event before PreCastCheck;
the fixture tests success and failure ownership separately. Its scope excludes
native spell effects and target traversal.

`movement_dispatch_regression.py --before-empty-move` reproduces the zero-length
move; the current dispatch rejects it in all three era builds.

`bot_action_command_regression.py --before` reproduces the parameter lookup
failure in the actual handler. Current coverage includes longest matching action
names, multiword parameters, missing actions, explicit requester selection and
recording cleanup on both successful and failed actions.

Native Ymiron and Devourer scripts, Wrath UnitAuraProcHandler and local spell data
were inspected for the pause conditions. Mirrored Soul places 69023 on the boss,
cast by the linked player; 69051 alone on a player is not the boss-side condition.
Existing damage-over-time effects, missiles already launched, native aura procs
and custom guardian AIs are not undone by the pause. This is not a guarantee of
zero reflected damage or a complete strategy for either encounter.

These changes require no config additions or database migration. They do not
close the remaining encounter assignments or live normal/heroic/raid validation
listed in `RAID-DUNGEON-AUDIT-20260906.md`. Publication, production deployment and
ManTech baseline promotion remain deferred (area 6).
