# Isolated movement recovery review

Branch: `review/mantech-movement-recovery-20260910`.
Starting Playerbots baseline: `98648905df62e88842c629a870c9a4ea0669595d`.

## Included changes

Two independent fix commits are provided so either can be reverted without the other.

### Route selection and lock lifetime

`TravelNodeMap::getRoute` sorted its open list ascending and then used max-heap operations on that non-heap sequence. Open-node costs can also change after an edge is relaxed. Select the lowest current cost with `min_element` and remove that exact element. Edge eligibility, route costs, reopening and transport/spell conditions are unchanged.

`TravelNodeMap::getFullPath` returned when no route existed without releasing its shared map lock. A scoped shared lock now releases it on empty routes, successful returns and exceptions. The direct local-path shortcut remains before lock acquisition.

Adapted from Alex Boutros' Living Playerbots [patch 191](https://github.com/apb-hello-world/living-wow-playerbots/commit/17ac7774e1b6d20f777c5d64f397c765e38e3110). The queue correction is kept inline in the existing method; the broader Living framework is not required.

### Flee candidate distances

The candidate loop varied `dist` but calculated every candidate at `maxAllowedDistance`. Use `dist` for both coordinates so shorter escape positions are considered. Keep existing force-maximum-distance, edge, water, LOS and enemy-distance checks.

This is only the distance correction from Alex Boutros' [patch 205](https://github.com/apb-hello-world/living-wow-playerbots/commit/22f14bf67e8159a83a62da3f4cbffb1562241328), not the accompanying flee watchdog or outdoor death-avoidance policy.

## Validation and scope

`tests/travel_route_recovery_regression.py` compiles production selection code and the full production `getFullPath` method against controlled interfaces. It checks mutable costs, ties, exact removal, reopened nodes, direct paths and write-lock availability after empty, successful and exceptional route exits.

`tests/flee_distance_recovery_regression.py` compiles the production candidate loop. It checks blocked outer positions with usable shorter positions and preserves maximum-distance, edge, water and LOS restrictions.

Both tests passed with MSVC C++17 under `MANGOSBOT_ZERO`, `MANGOSBOT_ONE` and `MANGOSBOT_TWO`. These are focused compiled regression fixtures, not three full core builds or gameplay tests. The affected code is shared across all three expansions; core integration and live behavior remain unverified for this branch.

No core revision pins, baselines, production binaries, database records, configs or addons are changed by this review branch. No upstream PR is prepared. Merging or deploying this branch is a separate release step.

## Recovery follow-up assessment

| Candidate | Current local behavior and next validation |
|---|---|
| Unreachable loot, Living patch 230 | We already drop the loot target and apply per-bot path backoff when movement fails. The remaining candidate gap is movement accepted repeatedly with no progress. His watchdog measures decreasing straight-line distance, with a 10-second no-progress/30-second overall timeout and two-minute defer. A valid route around pillars or between floors can initially increase that distance. Validate path/waypoint progress, target identity, interruption by combat and long routes before adding it. |
| Flee watchdog, Living patch 205 | Actual displacement is better evidence than an installed chase generator, but legitimate roots/stuns, casts, holds and alternative defensive actions need explicit tests. Keep separate from the one-line geometry fix. |
| Activity rotation, Living patch 221 | Our rate still depends on the active percentage, which can stretch the rotation for throttled independent bots. However, activity checks are cached and priority brackets intentionally limit work. Test those together, timer wrap, representative populations and CPU cost before changing rotation speed. Preserve player-party/instance exemptions. |
| Safe party positioning, patches 233–234 | Requires a new positioning subsystem and overlaps our pull/LOS recovery. It excludes battlegrounds as written and is not a fix for independent WSG strategy. |
| Stale combat and strategy reconciliation | His versions depend on his rendezvous/build ownership systems. Preserve valid pet combat, player-selected roles, healer-DPS and pull settings before adapting any portion. |

The follow-up items above are assessed candidates, not fixes included in this branch. They do not require merging the chat, guild, economy or durable-task systems.

## Review and rollback

Review this branch against `mantech-playerbots`. Baseline and deployed behavior remain unchanged until an explicit integration release. If a fix is later merged, revert its individual commit and rebuild the core binaries against the resulting Playerbots revision; deleting the review branch alone does not undo a merge or deployed executable.
