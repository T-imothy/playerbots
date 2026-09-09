# Target selection and switching â€” 9 September 2026

Item 2 of the shared-system audit. Applies to the shared Playerbots source for Classic, TBC and Wrath, after scheduler commit `fc631a6991a473c678a127b856394d6525697521`. No native boss mechanics, spell data, databases, configurations or server files were changed.

## Corrections

| Area | Defect or missing behavior | Change |
|---|---|---|
| Cached eligibility | Several selection/validation paths relied on cached GUID membership to admit a target that could since have died, changed faction, become unattackable or started evading. Map-ID equality alone also did not distinguish instances. | Revalidate basic eligibility before scoring/dispatch, compare the actual map/instance, and reject evading creatures. Cached attacker fallback must still pass current attack eligibility. |
| CC protection | DPS/tank target scoring could keep picking damage-breakable CC that the newer class actions refused to damage. Generic attack dispatch could start auto-attacks or send the pet anyway. | Apply the existing class CC policy to automatic damage selection, current-target invalidation and generic attack dispatch. Preserve separate CC assignment selection, so a marked target can still be chosen for its control spell. |
| Tank rescue | Unmarked tank targets were ranked only by absolute threat; an enemy attacking another tank could beat one attacking a non-tank group member. | Prefer enemies currently attacking a living non-tank member of the same group; use existing threat comparison within each category. Explicit raid-target marks still take priority. |
| Repeated DPS assist | The assist trigger returned true every check while already fighting, even when bot and pet both had the intended target. | Reissue only for a changed target or missing bot/pet attack order, retaining the opening wait, stealth and passive phase-shifted imp exceptions. |
| PvE/PvP contention | PvE assist triggers noticed an enemy-player target but queued an action that selects a different PvE target value. | Let enemy-player actions own that switch instead of repeatedly queuing mismatched PvE assists. WSG objective scoring/routes are unchanged. |
| Target recovery | Recovery consulted non-combat assist settings, preferred DPS over tank when both were enabled, and reported failure despite completing target/pet cleanup. Cached ranked choices could immediately select the abandoned target again. | Use combat settings, prefer tank assist, reset ranked target values, and report actual cleanup success even if no replacement is available. An already-empty selection does not consume a successful action every tick ahead of healing. |
| Cast recovery | The broad interruption helper could cancel a positive spell while abandoning an enemy, but excluded channels. | Preserve positive spells; stop interruptible hostile auto-attacks and casts/channels targeting the previous selection. Copy the spell ID before interruption and use existing interruption-delay handling. |
| Enemy-player scoring | The first cached enemy was accepted without fresh validation and used as the initial health/distance baseline. | Validate every candidate before scoring. Reuse the existing arena-aware friendship predicate. |

The CC changes align automatic targeting with the class combat guards already in the baseline. This intentionally means that a damage-protected target is not selected merely because it is the only enemy left. No new universal CC classification or expansion spell list was introduced.

## Reviewed and retained

- GUID-backed current/old/pull target resolution and the existing owner/group/pet attacker aggregation.
- Native attackability, PvP-prohibited zones, tag/loot checks, attack range policy, raid marks and dedicated WSG target selection.
- Existing low-health DPS ranking, threat comparison within a tank-rescue category, taunt and interrupt strategies. This does not add universal peel actions, automatic taunt swaps or an optimized DPS focus-fire policy.
- An enemy behind an obstacle is not permanently blacklisted merely for temporary LOS loss. Selection still allows movement to regain LOS. Evade rejection is included; path failure history and repeated unreachable-target abandonment belong to the next movement/pathing audit.

## Verification and remaining limits

`tests/target_selection_source_checks.py` checks the changed source control flow and can inspect the native interface declarations in all three local core checkouts with `--core-root`. These checks do not execute C++ or demonstrate live combat behavior.

**No C++ compilation, native harness execution, dev realm startup, gameplay test, build or deployment was performed under the build hold.** No measured healing, response-time or server-performance claim is made. Runtime acceptance should cover: target death/despawn/charm/evade; newly applied CC while bot/pet attacks; two-tank fights with an add on a healer; a target behind stairs/LOS; post-pull pet recovery; positive healing during enemy-target cleanup; and PvP mixed with nearby NPC enemies.

Pending independent audits: movement/pathing/positioning, full group/pull coordination, and general recovery. Native collision/path reachability and every encounter-specific target selector have not been exhaustively runtime-tested by this shared selection pass.
