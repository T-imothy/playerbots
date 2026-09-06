# Encounter and path continuation

This records additional reproduced corrections after the ae802751 audit
checkpoint. It does not replace the mechanic backlog in
`RAID-DUNGEON-AUDIT-20260906.md` or establish live encounter clears.

## Corrections

- Keli'dan (Blood Furnace, map 542, entry 17377): watch native Burning Nova
  warning aura 30940. The native action applies it instantly, then waits before
  Fire Nova; an active-cast-only watcher misses that interval. Resolve normal
  33775 versus heroic 37371 from the current map difficulty. Recheck warning,
  boss identity, instance, phase and geometry before movement. Expiry releases
  the hold. The heroic Vortex remains native behavior.
- Dalliah (Arcatraz, map 552, entry 20885): watch Whirlwind aura/cast 36142,
  using its native trigger 36175 for radius. Release the movement hold when
  Whirlwind ends, so the subsequent native heal can be interrupted normally.
- Hellmaw: in both TBC and Wrath cores, compare `eventType` with
  `AI_EVENT_CUSTOM_B`. Testing that enum constant by itself caused unrelated
  events to schedule an unbanish check. Channeler-completion event A and
  respawn event B retain their existing behavior.
- Shared short path handling: reject a failed native calculation and empty
  points before inspecting an incomplete result. Respect `forceNormalPath`
  during the underwater extension. After converting transport points back
  to world space, compare/extend against the world destination, rather than
  its transport-relative offset.
- Shared encounter destination validation: check every segment of one native
  normal path against the current ground-hazard snapshot. A safe endpoint
  does not prove its route is safe. Permit outward escape from a hazard;
  reject inward travel, crossings, incomplete paths, nonfinite points,
  mismatched maps and paths above 256 points. An already-reached safe point
  needs no new route. Candidate generation retains its existing bounds.

These changes introduce no configuration keys or database migration. Native
map data remains necessary; this is bounded local path validation, not a
replacement path planner or continuous moving-hazard prediction.

## Evidence

`boss_cast_position_regression.py` exercises the actual planning and execution
methods across all three compile-time eras, including aura expiry, difficulty
selection, healer-preserving holds and stale actions. The Classic fixture
deliberately lacks `Map::IsRegularDifficulty`, matching that core's API.
`hellmaw_event_regression.py` extracts both actual native event handlers.
`world_path_result_regression.py` and
`encounter_destination_path_regression.py` exercise the actual source methods
with controlled native results. Each new defect family has a failing prior-code
run and a passing corrected run in the task evidence directory.

The task's build records identify the exact revisions and verification results.
Fixture tests are not real map/raid simulations. Runtime validation and the
remaining encounter feature backlog are tracked separately; release area 6
and ManTech baseline promotion remain deferred.

## Database reference follow-up

The local TBC full database also contains empty list metadata for the three
heroic trash-list findings. In particular list 1861401 is named for Seductress,
while the local Shadowmoon Adept heroic template 18615 references it. TBC's
Hellmaw and Gothik lists have real spell rows; the queried Wrath lists do not.
Native Hellmaw does not separately cast Acid/Fear from its C++ action set.
These findings justify separate data repair investigation, not blindly copying
TBC lists into Wrath or attributing the missing rows to this bot change.
No production database has been inspected or changed in this follow-up.
