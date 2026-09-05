# Playerbot behavior enhancements — September 5, 2026

Branch: `playerbot-behavior-enhancements`, based on ManTech Playerbots `811d6f1e`. Supported by matching Classic, TBC and WotLK core branches. This is a behavior-correction test release, not another architecture/RAM optimization release.

## Changes mapped to the audit

| Audit | Correction |
| --- | --- |
| B01 | `AiPlayerbot.AutonomousTravel = 1` enables the existing travel system for autonomous bots independently of `AutoDoQuests`. General destinations load without quest destinations when automatic quests are disabled. Idle level-20+ random bots in non-capital areas with area level 1–10 receive a placement recheck while away from humans, groups and combat. Existing activity limits remain in force. |
| B02 | NPC occupancy is counted once per target-selection pass, including inactive occupants. The cap no longer disappears at 200 nearby players/bots. Player-owned companion targeting retains its exemption. |
| B03 | Random relocation reports success/failure. Failed attempts get a 60-second timer rather than normal 2–48-hour residency scheduling; actual retry also depends on manager update cadence and eligibility. Failed RPG relocation no longer refreshes the bot or installs a ten-minute travel cooldown. Initial placement failure schedules another attempt. |
| B04 | Random group relocation validates each member and rejects mixed/player-owned groups, offline/transitioning members, combat, transports and battleground situations. Homebind changes follow successful relocation. |
| B05 | Recovery/admin relocation evaluates candidate locations using FleeManager's existing start-position parameter. It no longer moves the real bot while calculating candidates; it actually uses the selected candidate list. |
| B06 | Eligible unsolicited human mail returns all attachments and money, including when the sender is offline. Missing attachments, unsupported/system/returned/requested mail and text-only mail are preserved. All three cores can atomically replace the original mail with its return. No schema migration. |
| B07 | Warlock summon commands use the same helper checks for named and selected targets. Helpers must be alive, in the same map/instance, nearby, visible and available. Invalid/ineligible targets, missing ritual knowledge and rejected teleports do not report success. Rejected summon commands no longer fall through into ordinary spell casting. Human summon acceptance and existing no-shard bot convenience remain; no player hearth cooldown is charged. |
| B08 | Ranged-spacing triggers cannot drive warrior/rogue/DK or melee/tank strategy retreat loops. Emergency fleeing remains separate. Hybrid roles still require gameplay verification. |
| B09 | Wildcard quest acceptance returns its actual result. Recording loot rolls reports successful handling. Broader action-result redesign was not needed for these confirmed cases. |
| B10 | Choosing a new travel destination clears the matching ignored NPC entries without comparing unrelated target-object addresses or invalidating the iterator. |

Also corrected an inverted nearest-inn distance comparison encountered in relocation.

## Validation

Native harnesses compile actual changed C++ bodies with controlled interfaces, rather than reimplementing their decision logic:

- `tests/behavior_regression.py --core <core>`: money, multiple attachments, missing attachment, offline sender metadata, unsupported/requested/returned/future mail, sender eligibility, transactional source deletion, and repeat-safe travel ignore cleanup. Run with `--wrath` for WotLK.
- `tests/summon_regression.py`: 16 target/helper/direction cases, including wrong-map helpers at identical coordinates, dead helpers, blocked sight, bot targets, rejected teleports and pet-command fallthrough.
- `tests/placement_regression.py`: failed versus successful relocation side effects, normal versus short scheduling, and occupancy at 199/200/300 nearby bots.

Full x64 RelWithDebInfo builds are required for each matching core. Native tests and builds do not establish that every dungeon, class or production population behaves correctly.

## In-game acceptance checklist

1. Observe existing high-level starter-area residents over time and test a small fresh mixed-level pool. Compare local NPC crowd size, appropriate low-level population, and movement out of unsuitable areas. No human-controlled companion should be relocated by the population manager.
2. Test a failed placement followed by restored destination availability. Verify the next eligible retry succeeds and does not award repeated refresh effects while failing.
3. Test warrior melee combat, a tank, caster DPS, and healer/hybrid roles. Confirm no repeated flee/reach-melee oscillation and verify legitimate emergency retreat.
4. In party and raid, use bare `summon` near an inn/stone; verify bots come to the requester. Whisper a warlock `cast summon Charactername`; verify helper requirements, summon prompt, destination and unchanged human hearth cooldown. Repeat with a dead helper and with a helper on a different map.
5. Enter/exit SM, Deadmines and Wailing Caverns with following bots, including a bot drinking or channeling. Exercise a raid entrance, transport and BG entry/exit. These are regression tests for the retained baseline transition fixes.
6. Mail a free autonomous bot one item, money, and (TBC/WotLK) multiple attachments. Test while sender is offline. Verify returned contents and no duplicates after relog/restart. Do not use valuable items for first gameplay verification.
7. Try wildcard quest acceptance and multiple loot rolls; confirm successful actions do not report failure or retry unnecessarily.
8. Verify protected portable mailbox/repair items, their initial mail, group loot and existing convenience features still work.

Autonomous travel can load more world content and increase background activity compared with stationary bots. The unchanged 4,000-bot/thread/activity settings do not guarantee identical RAM or tick times. Measure this behavior tradeoff during acceptance; `AutonomousTravel = 0` restores the prior quest-coupled travel admission and disables the new low-level-area placement recheck, while retaining the correctness fixes.

Production replacement requires the matching core binary and shared Playerbots build together because of the new mail API. Keep matching PDBs beside mangosd.exe. No SQL update, new database, bot-pool deletion, character rewrite or database backup is required for this release.
