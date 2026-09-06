# Combat and summon rework — work in progress

Requested scope: all three ManTech testing cores, class-rotation review and the
full dungeon/raid coverage inventory. Production and ManTech master branches are
not deployment targets. This document is an implementation ledger, **not a
claim that every encounter has been implemented or played successfully**.

## Implemented source changes

### Shared Classic, TBC and Wrath

- Inn summons no longer require a hearthstone or its readiness, apply its
  cooldown, or clear an existing genuine hearth cooldown. Meeting stones retain
  their existing no-hearth behavior. Inn/stone location restrictions remain.
- Bare convenience summons only move the bot, never a real player. Reject
  logout/teleport transitions, combat, charm, taxi and transport contexts rather
  than attaching passengers with incompatible coordinates.
- Check core map admission and the return value of `Player::TeleportTo`.
  Same-map movement does not misuse `Map::CanEnter`, which rejects a player
  already in that map. Same-number/different-instance movement is rejected;
  this does not bypass instance bindings or normal entrance handling.
- Do not clear movement or rewrite stay/guard anchors after a rejected move.
  Acceptance is not completion: a far transfer still needs its normal ACK.
- Existing safe dead-bot revival is deferred until ACK at the intended
  destination. Rejection, fallback location, expiry and duplicate completion
  cannot grant a resurrection. One bounded pending record per AI, not a queue.
- Suppress the misleading missing-stone announcement before trying an inn.
- Explicit warlock summons no longer fail map admission merely because the
  target is already on the warlock's map. Ritual fidelity/reagents remain a
  separate open review item; no new claim of complete native ritual simulation.
- Wire Naxxramas entry in combat/noncombat and exit in noncombat. Correct the
  Horsemen cleanup lookup and use Korth'azz, present in both eras, rather than
  the Classic-only Mograine identifier. This is not a complete Naxx strategy.

### TBC and Wrath

- Assassination Envenom candidate uses the existing combo threshold, learned
  spell/cast rules and the core's own Deadly Poison ownership/family selector.
  Require enough owned doses for the combo points; preserve Eviscerate fallback.

### Wrath only

| Class | New scheduling/behavior |
|---|---|
| Warrior | Register existing Enraged Regeneration action; consider it at low health, retaining native enrage/cooldown requirements. |
| Paladin | Divine Plea at low mana for non-healing roles; Protection Shield of Righteousness through melee/core equipment checks. |
| Hunter | Kill Shot through native target-health, learned-spell, range and cooldown validation. |
| Rogue | Hunger for Blood only with a bleeding target and a learned/ready spell. |
| Priest | Discipline Penance on an injured party member; healing-role Divine Hymn for critical group damage. Channels use the existing casting path. |
| Shaman | Elemental owned Flame Shock and Lava Burst sequence; Enhancement Feral Spirit follows the existing boost policy. |
| Warlock | Destruction Chaos Bolt, owned Haunt for Affliction, Metamorphosis under the existing Demonology boost policy. Remove obsolete Wrath raid Demonic Sacrifice scheduling and restore raid pet maintenance, preferring a learned Felguard. Classic/TBC sacrifice policy is unchanged. |
| Druid | Cat-form/combo-gated Savage Roar; Nourish prefers an owned periodic heal using the same test as our core spell script; Wild Growth for group injury. Restoration form prerequisites and existing heal fallbacks remain. |

### Additional encounter and class corrections

- Native hazardous ground-area detection inside combat in dungeons/raids:
  hostile periodic damage only; reject friendly heals, farsight, expired objects,
  excessive radii, other maps and native attack-ineligible targets. No outdoor
  scan is introduced. Object hazards expire with their actual object; hazard
  movement retries are not suppressed simply because the last action moved.
- Onyxia: deep-breath avoidance uses the core's spell-target positions; ground
  flank positioning avoids front/tail while excluding the active tank; targeted
  fireball spreading holds separation; eligible roles target engaged whelps.
  Native height/path checks reject invalid destinations. This is not a claim
  of complete egg, lair-guard or every heroic/raid-size mechanic coverage.
- Netherspite (TBC/Wrath): replace aura grants/removals with actual beam
  positioning. Stable role assignments respect human blockers, exhaustion,
  stack limits, banish and portal lifetime. No boss weakening or teleportation.
- Molten Core: Geddon Living Bomb separation and Inferno/Armageddon radius
  avoidance, plus Shazzrah ranged/healer separation, use native spell radii.
  Escape candidates must clear the combined danger areas and native path/height
  checks. At most eight path candidates per cached decision; no manufactured
  safe location when none is reachable. Other MC mechanics remain under review.
- Shared spell actions reject passive talents/procs instead of casting them;
  target-map validation uses the actual map instance, not just the map number.
- Wrath DK: apply owned Blood Plague/Frost Fever, use the secondary target for
  secondary disease actions, spread diseases only where missing (or refresh
  under the native glyph rule), register Killing Machine, and gate Empower Rune
  Weapon on depleted rune cooldowns/runic power/native castability.
- Wrath Arcane Blast builds up to four stacks rather than stopping after one,
  with the existing low-mana boundary. Older expansion behavior is unchanged.
- TBC/Wrath Misdirection and Wrath Tricks automatic combat support uses a live
  group tank, preferring the current enemy's tank victim. It rejects self,
  controlled/dead/other-map/non-group targets and already-active caster auras.
  Existing hunter pull preparation remains available out of combat; explicit
  manual cast commands keep their own targeting path.

These are source implementations with controlled tests, not demonstrated raid
clears or optimal DPS. Further proc/channel/encounter review remains open. No DK
combat scheduling or Wrath-only ability scheduling is added to Classic/TBC.

## Validation completed so far

- Intermediate native x64 RelWithDebInfo builds succeeded for Classic, TBC and
  Wrath. Later edits require a final build of the exact committed revisions.
- Actual-source controlled C++ tests passed for convenience summon rejection,
  admission, owned bot direction, post-ACK revival and duplicate/expired/fallback
  cases; explicit warlock summon eligibility; placement retry/crowd behavior.
- Actual-source predicate tests passed for Envenom dose/ownership, Nourish HoT
  ownership and Lava Burst's owned Flame Shock/core-castability requirement.
- Existing class and combat diagnostics regression suites passed, including the
  Classic/TBC/Wrath diagnostics probes. Static Naxx registration checks passed.
- No new encounter play tests have been performed. No damage/healing gain or
  performance improvement percentage is established by these tests.

## Remaining before the full requested scope is complete

- Boss-by-boss, mechanic-by-mechanic review against each CMaNGOS expansion's
  actual scripts; the earlier inventory is not that complete semantic audit.
- Finish remaining MC, Karazhan and Mechanar mechanics; review new Onyxia and
  Netherspite behavior in actual encounter play. Do not treat a partial boss
  strategy or generic hazard detector as complete raid support.
- Review/implement the other missing raid/dungeon libraries from the complete
  coverage matrix. Preserve normal/heroic, raid-size, expansion, threat, CC,
  movement, admission and spell rules; reject donor boss weakening/aura cheats.
- Resolve remaining class comparison leads (Vigilance/assigned support,
  proc and channel clipping, further rune/disease policy, etc.) against
  native APIs and actual reachable behavior; do not treat name differences as bugs.
- Final exact-revision builds, matching EXE/PDB checks, dev installation and
  GitHub verification. Keep runtime files stopped/unchanged until installation is
  actually performed and reported. Do not present a partial snapshot as full completion.
- User encounter testing is still required after implementation/build validation.

## Diagnostics and database impact

No new log file, per-bot scan thread or SQL migration is introduced by the changes
listed here. Existing sampled combat diagnostics already observe the new action
names/outcomes. Pending summon revival is functional state, not removable
diagnostic instrumentation. Existing diagnostic caps/lifecycle policy remain.

The 10,000-bot Classic soak was stopped through the normal console signal; the
server logged `Halting process...` at 19:16:48 local on 2026-09-05. Shutdown also
reported existing hunter-trap owner-reference warnings. Those are separate
investigation leads, not proof that the newly edited code caused a crash (it was
not running in that process).

## Additional baseline regression found during this work

Classic/TBC dev builds and the current production crash/summon package omitted
the module framework, dual spec and training dummies. This is a build-feature
omission, not deletion of this NPC's individual gossip options. The core testing
branches now require those baseline modules by default and reject cached OFF
settings. Restored-module native builds pass; production was not deployed.
The four existing dual-spec tables were inspected read-only, not rebuilt/deleted.

New test programs: `encounter_geometry_test.cpp`, `encounter_runtime_regression.py`,
`combat_policy_regression.py`, and `threat_transfer_regression.py`. Geometry,
actual hazard predicates, all-three-expansion resource/disease predicates and
actual threat-transfer selection tests pass. Existing summon/class/placement/
diagnostic suites also pass. These do not replace client encounter testing.
