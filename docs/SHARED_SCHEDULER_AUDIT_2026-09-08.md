# Shared action priorities and delays — 8 September 2026

Scope: shared scheduling for all classes in Classic, TBC and Wrath, following the melee, hunter and caster source audits. This is item 1 of the proposed shared-system audit. It does not claim completion of the separate targeting, pathing, group coordination or recovery audits.

## Confirmed corrections

| Finding | Effect | Correction |
|---|---|---|
| Equal-priority queue order reversed by `34a09916` | The multimap implementation selected the most recently inserted equal-priority action. Repeatedly requeued work could starve older work. The earlier list implementation selected the oldest equal-priority action. | Keep the indexed queue and select highest priority with insertion order for ties. |
| Zero-priority strategy veto still entered prerequisite planning | An action blocked by pull, threat, CC or another multiplier could enqueue a prerequisite at `0.02`, or a reaction fallback at `0.03`. This could initiate unwanted movement or consume scheduling iterations. | Stop vetoed decisions before prerequisites/alternatives in both engines. Negative ordinary default priorities remain valid. |
| Reordering marked prerequisites complete | A multiplier-reduced action was pushed back with `skipPrerequisites=true` even though its prerequisites had not run. | Preserve the original prerequisite flag when merely reordering; retain the existing skip after actual prerequisite scheduling. |
| Expiration occurred only after processing | An old plan could be selected, or absorb a fresh trigger with the same action name, before expiration cleanup. | Expire old entries before fresh trigger processing in both engines, retaining end-of-tick cleanup. |
| Explicit execution queued continuers after failure | A failed directly requested or nested action could enqueue follow-up work as though it succeeded. | Queue continuers only after a successful result. |
| Enemy approach wait accepted friendly targets | A reach action toward a moving friendly player could choose to wait under the enemy-approach setting. This applies to healing/support reach as well as other friendly reach. | Restrict that branch to hostile targets. |
| Approach wait reused previous movement duration | Cached reach actions could return success while waiting, retaining the duration from an earlier movement. | Give this deliberate short wait the normal configured reaction delay. |

All corrections are in shared Playerbots code; there are no expansion-specific spell IDs or boss/core mechanic changes in this patch.

## Other paths reviewed

- Existing routine-consumable guards reject combat, active pulls and nearby group combat. The combat trigger remains harmless behind those guards. Emergency potions retain their separate paths.
- The wait-for-tank multiplier already exempts urgent direct healing and pull commands; this patch makes a zero veto apply to prerequisite scheduling too.
- Failed spell retry entries already include target identity and a readiness signature covering resources, position, form and native possibility; explicit real-player chat commands bypass suppression. The configured retry backoff remains unchanged.
- Native cast duration, global cooldown, interrupted-spell handling, combat wake-up, reaction scheduling and movement waits were inspected. No global reduction in delays was applied. A movement wait can still reach the configured maximum, and a running reaction can still delay ordinary combat decisions.
- Pull start's existing pre-action wait, negative default-action priorities, mana-conservation policy and class spell priorities remain unchanged. These are behavior policies, not proven defects solely because they introduce a delay.

## Validation and limits

Source-ordering and control-flow checks cover queue selection, prerequisite flags, vetoes, expiration, success-only continuers and friendly reach. `tests/shared_scheduler_regression.py` defaults to source checks. Its optional `--compile` mode exercises the actual Queue methods against controlled interfaces for equal-priority fairness, emergency ordering, prerequisite offsets, promotion/deduplication, explicit removal, expiration and node cleanup.

**No compilation, native harness execution, dev realm startup, gameplay testing or deployment was performed under the build hold.** Source checks are not proof of runtime correctness or a measured healing/performance improvement. Focused gameplay testing should include simultaneous healing needs, pull with queued buffs, a moving friendly heal target, a blocked spell with a reach prerequisite, and repeated failed explicit commands.

Remaining independent audits: target selection/switching; pathing and positioning beyond the approach-wait correction; complete pull/group coordination; recovery after failed paths, resources or death. Scheduler behavior with real combat load and every encounter multiplier remains unverified at runtime.
