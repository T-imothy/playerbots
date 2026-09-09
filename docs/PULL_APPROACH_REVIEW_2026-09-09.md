# Commanded pull approach review

Reported on Classic: Jados, grouped with Tim, approaches a selected enemy in
Uldaman, sometimes shouts and returns without shooting. Other pulls, including
farther targets and stairs, succeed. Moving the leader a few feet can change the
result. These observations do not establish a general pathfinding failure.

## Confirmed source defects

- PullAction stopped movement based on range alone. Its possibility check
  intentionally ignores range and LOS so movement prerequisites can run.
  Inside range but behind an obstruction, this let Execute cancel a running
  approach before Shoot's stricter LOS check rejected the shot.
- PullStart cleared its pending flag, and only a successful shot or particular
  movement branches armed another attempt. A failed cast or lost queued action
  could therefore leave the request waiting until its 15-second deadline.
- ReachPull inherited the generic wait-for-an-approaching-enemy branch. That
  branch tests enemy movement/facing rather than whether it is actually coming
  to fight, so a commanded pull could wait on a patrolling enemy.

## Changes

Keep movement until range and Shoot's LOS check both pass. Schedule an unissued
shot from its own trigger after preparation, without replaying preparation or
extending the existing deadline. Do not use the generic wait-for-enemy policy
for commanded pull movement. Existing shot retry, pull-back, melee fallback,
pet restoration and native spell/equipment restrictions remain in effect.

The changes are in shared playerbot code for Classic, TBC and Wrath. Each keeps
its expansion-specific pull spell and native spell range. No map, collision,
boss script, spell data, database or configuration changes are included.

## Validation and limits

Extracted production-method tests cover the blocked-LOS approach, stopping and
shooting with clear LOS, retry after a transient cast failure, accepted-shot
suppression, original timeout, invalid targets and melee fallback in all three
expansion builds. Existing warrior/pull lifecycle tests cover stance planning,
pet restoration, ally rescue, pull-back and shot retry. These tests simulate
native movement and spell outcomes; they are not live Uldaman pathfinding tests.

Live SOAP diagnostics timed out. The screenshots alone cannot prove every
reported failure followed these paths. Exact collision/path failures, actual
shot timing, and end-to-end behavior at the reported positions remain runtime
verification items. Do not describe this as a complete movement audit.
