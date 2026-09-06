# Generic movement and audit continuation — 2026-09-06

Area 7 is now part of the enhancement audit. This pass fixes reproduced source
defects and records the movement controls and remaining validation. It does not
establish that every map or encounter is navigable. Release area 6 remains deferred.

## What controls bot pathing

| Layer | Source | Responsibility |
| --- | --- | --- |
| Destination and role | `ReachTargetActions.h`, encounter actions, follow/flee/RPG actions | Choose the target, distance, formation or escape point. |
| Shared movement | `MovementActions.cpp`, active `MoveTo2` path | Reuse/resolve travel paths, handle transitions, clip the next movement, dispatch it. The older `MoveTo` implementation below its immediate `return MoveTo2(...)` is unreachable. |
| Long travel | `TravelMgr`, `TravelNode`, `TravelPath`, `WorldPosition` | Choose routes and special links, including taxi/transport/portal transitions. |
| Local navigation | Each core's `MotionGenerators/PathFinder.cpp`, mmap data | Resolve connected walkable polygons and native path status. Missing tiles can produce a native shortcut rather than a validated navmesh path. |
| Collision and height | Native map/vmap terrain APIs | LOS, ground height, water and collision checks; these depend on extracted data and core configuration. |
| Actual motion | Native `MotionMaster`, point/path/chase/follow/taxi generators | Execute movement and splines. Supplying only an endpoint does not preserve an edited waypoint route. |
| Hazards | `HazardsValue`, encounter hazard producers, `MovementPathSafety.h` | Supply positions/radii and validate detours. Hazard values have a one-second calculation interval. |
| Failure recovery | `LastMovementValue`, `StuckValues`, `StuckTriggers`, `UnstuckAction` | Retry backoff and longer-term position/combat recovery. Stuck recovery deliberately differs for human-led bots. |
| Pets and vehicles | Native pet session handler/AI; Wrath transport seat metadata | Pets retain native movement/cast openers. A vehicle passenger cannot issue driving movement without a controlling seat. |

Existing controls include `AiPlayerbot.PathFailureRetryMs` (template default
3000 ms), sight/react/follow/flee distances, activity/detail settings, and core
`mmap.enabled`, vmap LOS/height and `DataDir`. None is a universal "better
pathing" switch. This pass adds no configuration keys, database migration or
replacement map data.

## Reproduced corrections

1. **Discarded hazard edits:** `GeneratePathAvoidingHazards` changed a local
   waypoint but did not write it back. Save the edited point; reject empty and
   one/two-point inputs before reading `front()` or subtracting unsigned size.
2. **Detours discarded at dispatch:** preserve the selected route with native
   `MovePath`. Resolve each leg through native `PathFinder` first, require a
   successful calculation and normal path status, and check complete segments
   against hazards. Raw edited waypoint joins can cross walls and are not used.
3. **Unsafe fallback chase:** failed, unchanged-but-unsafe or invalid hazard
   routes stop instead of falling through to native target chase. Safe unchanged
   paths are checked too. Native ordinary chase remains available without hazards.
4. **Chase distance geometry:** measure the stand-off point back from the target,
   not forward from the bot; clamp the geometric offset to zero/current distance.
5. **Mover selection:** dispatch through the selected mover's motion controller;
   validate missing vehicle/seat metadata and reject non-controlling Wrath seats.
   The short navigation start/source uses the selected mover.
6. **Movement history:** copy the flee timestamp along with the existing retry
   history. Start failed-path backoff after calculation fails, so expensive work
   does not consume the retry interval before it is recorded.
7. **False taxi warning:** all three native taxi generators intentionally start
   with an empty path; `Resume` loads their flight path. Exclude that initialization
   from the empty-fixed-path warning. Preserve actual invalid waypoint diagnostics
   and the native stop/clear behavior; no taxi routing behavior is changed.
8. **Queued overheal cancellation:** re-evaluate the live heal trigger at action
   execution. A patient injured after queueing, or a replacement damage cast,
   must not be canceled by that old event. Limit automatic cancellation to the
   generic heal slot; capture the spell ID before native cancellation callbacks.

## Verification

New executable regressions extract actual production methods/branches and compile
them against controlled native interfaces. Native builds separately verify the
real APIs. These are not live-world or client simulations.

- `generic_hazard_path_regression.py`: original waypoint-retention failure,
  alternate side, blocked detours and empty/short inputs.
- `movement_dispatch_regression.py`: native route dispatch, finite/map validation,
  navigation rejection (including calculate=false), incomplete/empty routes,
  whole-segment crossings, vertical separation, outward escape and mover selection.
- `chase_hazard_dispatch_regression.py`: safe and unsafe adjusted/unchanged routes,
  invalid destinations and preservation of the no-hazard native fallback.
- `chase_spacing_regression.py`: target offset, diagonal, in-range, negative/zero
  requested offset and coincident positions.
- `movement_state_regression.py`: actual history copy/reset and Wrath seat admission.
- `taxi_empty_path_regression.py`: actual native initialization branch, legitimate
  taxi emptiness, invalid fixed-path warning and rate limiting in all three cores.
- `heal_interrupt_recheck_regression.py`: actual live trigger/action behavior after
  health/cast changes, manual cancellation scope and callback-safe spell ID.

Full suite/build exit codes, exact local revisions and evidence are recorded in
the task's continuation report. The previous checkpoint remains installed in dev;
new movement binaries have not been installed or tested in a running world.

## Remaining limits and required live checks

- This is a local detour correction, not a global hazard-aware route planner.
  Short paths and tightly overlapping hazards can be rejected with no alternate
  route. Route validation allows at most 64 input waypoints and refuses missing
  navmesh/shortcut results and transport-relative detours. Measure extra path
  queries and rejected-route frequency before deployment at 10,000 bots per realm.
- Hazard snapshots can age while moving. The source checks do not prove continuous
  avoidance of moving/appearing hazards, full boss mechanics or recovery under load.
- Explicit non-navmesh motion, swimming/flying, legacy distant activity teleports,
  transport transitions, native follow/flee and pet movement are distinct paths.
  The validated ground dispatch does not certify all of them. No new teleport or
  geometry bypass was introduced.
- Exercise walls/stairs/doorways and different floors; unreachable targets;
  moving targets and moving hazards; kiting and group follow; swimming/landing;
  taxi/boat boarding and disembark; vehicle control/passenger seats; pet LOS/range
  casting; death/charm/teleport and same-map different-instance transitions.
- Verify extracted maps/vmaps/mmaps against each era. File presence and successful
  startup alone cannot establish mesh correctness or a completed encounter.
