# Magtheridon: native cube coordination and delayed debris

Implemented for TBC and Wrath; Classic cannot activate this code. This is not a
claim of a live raid clear or complete tuning of all Magtheridon roles.

## Native evidence and repaired prerequisites

Both cores' `boss_magtheridon.cpp` uses player channel 30410 on cube trigger
17376. Each trigger supplies a separate 30166 beam to boss 17257. Five native
beam holders cause Shadow Cage 30168 and interrupt Blast Nova 30616. Ending
the player channel applies Mind Exhaustion 44032 through the native aura script.
No bot code casts the cage, removes these auras or resets exhaustion.

The native cube AI had an unused owner setter. The testing core branches now
record an admitted channel's owner and reject duplicate/busy cube users. This
is necessary because gameobject auto-close is shorter than the channel.
Both core repositories test their actual GO-use handler separately.

Wrath dev incorrectly targeted 30410 directly at Magtheridon, bypassing the
five distinct trigger casters. World migration 5874 on the Wrath DB testing
branch restores target 17376, preserving 30166's boss target. The migration was
tested twice in a temporary-table fixture and applied only to local Wrath dev.
Production has not received these core/data corrections.

## Bot behavior

- A one-second, instance-scoped value observes live boss/cube/trigger objects.
  It stores GUIDs and one destination, not persistent pointers or queues.
- Only eligible automated group DPS with the dungeon strategy participate.
  Humans, tanks, healers, the current boss victim, exhausted users, current
  channelers and stale/dead/teleporting/charmed/logout players are excluded.
- Stable ranged-first/GUID ordering assigns one eligible bot per free cube.
  A trigger already channelled by a human also occupies its cube. Native GO
  ownership still arbitrates a stale assignment at click time.
- Ranged volunteers preposition on the boss-facing side of actual cubes and
  keep casting normally. Melee relief only moves during a real Blast Nova;
  there is no invented encounter timer. An insufficient eligible group is
  not supplemented by forcing human, tank or healer participation.
- Destinations use native interaction distance, height and reachable paths,
  with fresh admission/occupancy checks before use. A submitted click uses
  `HandleGameObjectUseOpcode`, not a remote use or direct spell injection.
- Nova can interrupt an ordinary bot cast. A real cube channel is preserved
  until Nova ends or encounter/group context becomes invalid, then ended
  through native channel cancellation. Hazard escapes remain allowed.
- Failed clicks are bounded to the action's one-second retry interval.
  Submission is not proof that all five beam effects landed.

## Debris warning

Native area 30632 is a dummy warning. Its `OnPersistentAreaAuraEnd` script
casts damage 30631 from the area's position. TBC and Wrath dev data use the
same eight-yard radius for both spells. The shared hostile-area detector now
recognizes this verified boss/map/spell combination before damage lands,
using the damage spell's native attack admission. Arbitrary friendly/dummy
areas are not hazards. Lifetime still ends with the native object; no phantom
post-despawn obstacle is created. Non-finite hazard radii are rejected.

## Validation and remaining tests

`tests/magtheridon_cube_regression.py` compiles actual source for all three
eras: distinct assignments, roles, exhaustion, short GO flags, occupied human
cubes, missing/duplicate triggers, stale maps, paths, native click submission,
channel preservation/cancellation and cleanup. The hazard runtime suite checks
actual debris admission and Classic exclusion. Native compilation and live
testing are separate gates, recorded in the external build manifest.

In-client tests must include a complete five-cube Nova, mixed human/bot users,
second Nova with previous users exhausted, blocked cubes, knockback,
channel disruption, group loss, wipe/reset and phase-three debris. Test low
ranged counts: melee relief may be too far away to complete all five channels
in time. The routine does not promise success for an insufficient or badly
positioned raid. Channeler CC/interrupt priorities, tank positioning, Blaze
placement and optimal phase timing remain additional encounter review items.

No new configuration, diagnostic logger, worker, global cache or bot SQL is
introduced. The assignment value and guard checks are functional behavior,
not optional diagnostic instrumentation to remove after testing.
