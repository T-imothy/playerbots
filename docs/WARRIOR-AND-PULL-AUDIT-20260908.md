# Warrior combat and shared pull repairs — 8 September 2026

This release follows the production log repair release. It contains the completed warrior source review and confirmed shared pull repairs. The separate dungeon/raid encounter audit remains paused and is excluded.

## All three expansions

- End the pull-only waiting state immediately when the selected enemy attacks another party member, allowing the tank to engage instead of waiting ten seconds.
- Track pull request, accepted shot and engagement separately. Returning to the pull position waits for the shot to finish. Failed or interrupted attempts can retry within the original 15-second deadline.
- Let melee pullers close a ranged weapon's minimum-range gap and attack normally when already within melee reach.
- Preserve and restore pet reaction settings after successful pulls, retries and cancellation. Report an expired pull to the requesting player.
- Prevent routine elixir/food-buff selection during a pull, active AI combat or nearby party combat. Recheck this before using the item. Emergency potion actions retain their existing behavior.
- Prepare the stance required by the actual expansion's spell data. Check learned abilities, reactive state, rage and stance availability before planning the change; native cast validation still decides whether an ability can fire.
- Remove a Sweeping Strikes stance veto that used an expansion-dependent spell ID and blocked unrelated actions.
- Add missing Arms interrupt routes and fix the misspelled distance trigger used by Intercept.
- Allow Mortal Strike to be selected while its healing-reduction debuff is already present, subject to native readiness.
- Prevent Sunder Armor/Devastate from waiting for a preferred attack that cannot currently be cast.
- Restore shared capability and encounter checks in warrior Taunt, Disarm, Sunder Armor and Devastate overrides.
- Allow native validation of warrior fear responses and their stance preparation through the AI's preliminary control-state filter.
- Use Shield Wall as the unavailable-Last-Stand fallback instead of an unexpected area fear.

## Expansion adaptations

| Area | Classic | TBC | Wrath |
| --- | --- | --- | --- |
| Shared pull lifecycle and consumable guard | Included | Included | Included |
| Warrior casting, triggers and safety checks | Native Classic spell rules | Native TBC spell rules | Native Wrath spell rules |
| Sweeping Strikes form rules | Battle only; native ID 12292 | Battle/Berserker; native ID 12328 | Battle/Berserker; native ID 12328 |
| Berserker Rage | Native Berserker requirement | Native Berserker requirement; add missing general fear trigger | No forced stance change where native data has no stance requirement |
| Arms preferred combat stance | Existing preference retained | Existing preference retained | Battle stance |
| Fury AoE scheduling | Existing combat placement retained | Existing combat placement retained | Move misplaced Whirlwind/Bloodthirst triggers into combat |
| Protection lost-aggro response | Existing Taunt route retained | Existing Taunt route retained | Select Taunt directly before a non-taunting Heroic Throw |

## Audit coverage and origin

Reviewed warrior strategy registration, Arms/Fury/Protection combat and noncombat routes, PvE/PvP/raid variants, triggers, action overrides, proc identity, stance prerequisites, rage/readiness checks, interrupts, taunts, defensive fallbacks, Vigilance and the shared pull/movement/consumable handoff. Checked native spell definitions from each realm's world database and the corresponding core validation code.

Git history places the hardcoded Sweeping Strikes multiplier in January 2025, disabled general stance prerequisites in June 2023, Mortal Strike's debuff trigger in July 2021, and cooldown-only Sunder selection in February 2026. Several custom action overrides predate the newer shared safety checks and consequently bypassed those checks. The ten-second pull wait also existed before the recent ranged-weapon correction. These findings do not establish that every reported symptom originated in the latest overhaul.

## Validation and limits

Focused tests execute production method bodies for pull transitions, ally rescue, retries, deadlines, pet restoration, native stance planning and consumable guards. Additional checks cover proc identity, Vigilance, encounter taunting, explicit-command retries, related-action dispatch and per-expansion warrior routing. Release receipts record the three native builds and deployed file hashes.

The exact Uldaman stair/line-of-sight incident was not reproduced live. Native line-of-sight, pathfinding, cast outcomes and threat calculations remain authoritative. This review does not certify every talent/gear combination or complete every encounter; live pull timing and combat behavior still need observation after restart. No artificial threat or guaranteed successful attack was added.

## Installation

Only `mangosd.exe` and its matching `mangosd.pdb` change. No database migration or configuration edit is required. Existing files are backed up on each realm share; running realms continue using their current process until restarted.
