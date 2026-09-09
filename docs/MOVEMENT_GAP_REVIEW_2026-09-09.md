# Movement review reconciliation — 2026-09-09

This is a targeted comparison of previous movement audits with baseline
`d07d9dbefee38d3d927f2ba12d71c6743410df9b`, followed by inspection of remaining
destination, reach/chase, and direct-flight gaps. It is not a new certification
of all movement. No native core or encounter mechanics are changed.

## Previously covered and still present

| Area | Existing protection checked in current source |
| --- | --- |
| Hazard navigation | Active MoveTo2 dispatch preserves validated paths; failed hazard detours cannot fall through to unchecked native chase. |
| Chase spacing | Destination is target-relative, with the requested stand-off clamped to the target distance. |
| Movement ownership | Wrath vehicle movement checks the controlling seat and selected mover. |
| Failed-path retries | Per-bot retry identity includes map, instance, transition generation and X/Y/Z destination cells. |
| Transport route recovery | Dock/exit availability is checked before use, including after trimming a resumed route. |
| Empty movement | Dispatch rejects a destination effectively equal to the mover's current position. |
| Pull and reach scheduling | Pull engagement/deadline handling and the short enemy-approach wait are retained; friendly healing targets do not use the enemy-wait branch. |
| Movement state | LastMovement copying retains flee and retry state. |

Prior records: `GENERIC-PATHING-AUDIT-20260906.md`,
`EXISTING-ENCOUNTERS-PATHING-20260906.md`,
`ENCOUNTER-PATH-CONTINUATION-20260906.md`,
`DAMAGE-PAUSE-CAST-LIFETIME-20260906.md`,
`WARRIOR-AND-PULL-AUDIT-20260908.md`, and
`ALLOWED-HEIGHT-MAP-AUDIT-20260906.md`.
Historical core/encounter entries in those documents do not establish that such
changes remain deployed; later encounter reversions are outside this review.

## Confirmed corrections

Both corrections are inside `MovementAction::FlyDirect`, which returns false
immediately in Classic. They affect the TBC/Wrath direct-flight branch called
from active MoveTo2, not only the unreachable legacy MoveTo body.

1. **Flight wait distance used a malformed position.** The old four-argument
   WorldPosition expression passed destination X as the map ID, Y as X, Z as Y,
   and zero as Z. Distance calculation could consequently use a cross-map travel
   lookup instead of the actual flight segment. Missing transfers return
   FLT_MAX, which causes WaitForReach to select the configured maximum wait.
   The correction measures from the supplied starting position to the chosen
   destination, retaining the existing wait cap and delay policy.
2. **Flight destination was assigned to an area-trigger integer.** WorldPosition's
   implicit bool conversion reduced the coordinates to 0/1. The destination now
   goes into the position-valued lastMoveShort field. The separately registered
   `last area trigger` value is untouched. This is a state bookkeeping correction;
   no portal failure is claimed from the old write.

The malformed distance expression is present in historical commit `9f2776f82`
dated 2026-07-26. The incorrect integer assignment also exists in its parent.
These defects predate the recent class and scheduler audits.

## Remaining / unverified

- Live walls, stairs, doors, different floors and unreachable destinations;
  particularly the previously reported Uldaman pull location.
- Moving hazards and targets, chase/follow oscillation, kiting and recovery when
  targets die, teleport or change instances during a movement action.
- Swimming, takeoff/landing, taxi, boat/zeppelin docking, vehicles and pet
  traversal. The direct-flight corrections do not certify these systems.
- Per-bot failure backoff exists; an additional target-selection blacklist for
  unreachable enemies remains deferred pending evidence and expiry/recovery
  design. Different-floor and temporary-LOS cases must not be rejected blindly.
- Reach actions cache qualified spell range. Whether live rank/talent changes
  leave a stale reach distance remains unverified; derived actions have their
  own range overrides, so no blanket refresh was introduced.
- Navigation cost and behavior at production bot counts require runtime/load
  measurements. Source review does not establish a performance gain.

## Validation and release scope

Reviewed the WorldPosition constructor and conversion, distance/MapTransDistance,
WaitForReach, the active FlyDirect caller, LastMovement fields, and independent
area-trigger value registration. Checked expansion preprocessing and the final
diff. These are source checks, not compiled or in-game tests.

The earlier movement regression scripts compile C++ harnesses, so they were not
rerun under the current build hold. No binaries, core submodule pins, production
files, configuration or databases are changed. Compilation and live traversal
remain pending for the next authorized build/test cycle.
