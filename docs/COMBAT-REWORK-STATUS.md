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
  target is already on the warlock's map. They now start the learned native
  ritual with ordinary reagent/cast checks instead of manually sending a summon
  packet or teleporting a bot. Shared default-strategy assistance clicks the
  native ritual, preserves its cast/channel, and lets the core count helpers
  and issue the normal accept/decline request. Wrath's separate portal step has
  bounded, expiring GUID-only state. See `NATIVE-SUMMON-RITUAL.md`; real-client
  validation of all three native chains remains required.
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

- Shared AoE target selection revalidates world/life/map/phase membership. AoE
  position bounds initialize from the first still-resolved target, not the first
  cached GUID; when every target disappears, return no position. Target counts
  saturate at 255 instead of wrapping 256 targets to zero. No altered spell radius
  or invented coordinates are used. Actual-source lifecycle tests cover all eras.
- MC DPS priority now uses normal attack admission for Lucifron/Gehennas adds,
  Sulfuron's healing priests and Majordomo's remaining adds (free healers first).
  Golemagg remains the DPS target rather than his death-prevented Core Ragers.
  Tank/healer assignments, current boss victim, explicit attack commands, valid
  raid marks, crowd-controlled/planned-CC targets and ambiguous multi-boss pulls
  are left to existing policy. Same-priority targets remain stable. Native script
  code for these bosses was compared across all three cores. This is not the
  complete MC encounter implementation; see `MOLTEN-CORE-MECHANIC-AUDIT.md`.
- Living Bomb separation now survives Geddon's death/despawn and combat exit,
  ending with the carrier's actual aura. Friendly carriers, map/phase, death,
  transition and bounded path checks remain enforced. Combat and noncombat
  movement arbitration prevents ordinary following from undoing separation.
  No aura is granted, removed or extended.
- Wrath-only learned Vigilance maintenance selects a native-castable grouped DPS
  recipient while the warrior is a tank and out of combat. Preserve an existing
  own assignment, do not overwrite another warrior's aura, and select stably
  rather than rotating recipients. The native threat direction is toward the
  warrior, not the outgoing Misdirection/Tricks direction. Not optimal-DPS tuning.
- BWL's optional suppression-room mode no longer permanently deletes `avoid aoe`
  and `avoid mobs` from three AI engines. Its existing passive multiplier is
  scoped to a live rogue inside BWL; native reaction avoidance stays available.
  Leaving the map does not leave that multiplier suppressing ordinary combat.

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
- Mechanar (TBC/Wrath): Capacitus opposite-polarity separation and native Nether
  Charge avoidance use actual spell radii and live, timer-bearing summons.
  Combined danger areas, safe-position holding, same-map/height/lifetime checks
  and eight-path-query limits apply. Classic returns an inactive decision.
  This does not implement same-charge stacking bonuses or every Mechanar boss.
- Mechanar positioning also observes Sepethrea's actual Raging Flames aura and
  current fixation target, with a running buffer for the chased bot. It combines
  nearby flame danger areas and replaces the competing fixed-distance flee
  trigger. Pathaleon ranged/healer positioning uses native silence/explosion
  radii and normal/heroic difficulty, without pulling the boss tank/melee away.
- Pathaleon add priority selects engaged Nether Wraiths, leaving the boss tank
  and healing roles alone. Both it and Onyxia add priority explicitly reject
  crowd-controlled targets (the shared list can reintroduce them as a fallback),
  honor configured raid-target marks, retain a valid current add, and reject
  charm, teleport, death and different-instance targets. Normal AttackAction is
  used; this is not direct damage, fabricated threat or forced CC removal.
- Aran (TBC/Wrath): stop normal motion while his native Flame Wreath cast or
  a living same-instance group member's ring aura is present. Keep stationary
  attacks/heals available; suppress chase/jump/flee and native movement-effect
  spell actions such as Charge/Blink/Disengage. Combat and reaction scheduling
  use the same cached decision. No aura removal, false root or boss-script edit.
- Prince retreat checks now require the actual live engaged Prince, not an
  arbitrary current/tank target. Only same-instance living group members count
  for Enfeeble; an unrelated master target is no longer treated as that debuff.
- Native cast escape/hold for Aran Arcane Explosion and Murmur Sonic Boom in
  TBC/Wrath, plus Wrath Loken Lightning Nova, Leviathan Mk II Shock Blast and Ick
  Poison Nova. Runtime damage-spell radii, actual cast lifetime, bounded native
  paths, same-instance guards and normal movement/reaction APIs are used. No
  matching cast means ordinary combat resumes; Flame Wreath holding wins an
  overlap. See `NATIVE-BOSS-CAST-POLICY.md` for native-source mappings and limits.
- Shared creature avoidance honors its requested creature ID (the configurable
  list previously searched for its base class's zero entry), rejects dead,
  other-instance and controlled/transition cases, and matches the trigger's
  victim policy. Safe-healer shortcuts now validate against the closest hazard
  too and try other nearby healers within an eight-candidate bound. Existing
  native LOS/path checks and radial fallback are retained.
- Configured multi-creature avoidance now uses the existing native multi-entry
  query and validates a destination against the combined entries, including
  neighbors beyond the initial danger radius. One escape cannot deliberately
  select a point inside another collected hazard merely due to entry-list order.
  Single-entry actions also include nearby same-entry destination hazards. This
  is on-demand movement work, not a new persistent/background scanner.
- Shared spell actions reject passive talents/procs instead of casting them;
  target-map validation uses the actual map instance, not just the map number.
- Wrath DK: apply owned Blood Plague/Frost Fever, use the secondary target for
  secondary disease actions, spread diseases only where missing (or refresh
  under the native glyph rule), register Killing Machine, and gate Empower Rune
  Weapon on depleted rune cooldowns/runic power/native castability.
- Wrath Arcane Blast builds up to four stacks rather than stopping after one,
  with the existing low-mana boundary. Older expansion behavior is unchanged.
- Wrath Sword and Board, Sudden Death, Taste for Blood, Fingers of Frost and
  Killing Machine check the native temporary proc IDs, not identically named
  passive talents. These proc checks return false in earlier expansions.
- Wrath Explosive Shot does not overwrite its own still-ticking effect during
  Lock and Load. Another hunter's effect does not block it. The secondary-target
  Black Arrow trigger now invokes its matching target-specific action.
- Wrath Shadow priests can use learned/ready Dispersion for low mana or low
  health through normal buff/cast/channel handling. No earlier-expansion action
  is registered. Existing mana-potion fallback remains available.
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
- Actual-source Mechanar decisions passed all three expansion fixtures for
  polarity, charge lifetime, flame fixation, caster-only normal/heroic radii,
  map/control/life guards and the eight-path-query bound. Add-target tests passed
  for CC fallback exclusion, marked/current target precedence, role assignment,
  instance/transition/life guards and Classic exclusion of Pathaleon behavior.
- Actual-source Karazhan tests passed in all three expansion builds, including
  Classic's inactive Aran detector, cast/aura lifetime and map guards, permitted
  stationary actions, native movement-effect suppression and Prince scope.
  Shared avoidance tests exercise the actual search and destination-validation
  code, including the configured entry ID and unsafe-nearest-healer regressions.
- Actual-source native cast escape/hold tests pass for all three expansion gates,
  including dummy-to-damage dispatch, difficulty variants, interrupted/completed
  casts, reset/transition/map guards, movement arbitration and eight-query limits.
  The shared avoidance tests also cover combined entries and single-query use.
- Actual-source MC tests cover DPS target priorities, manual/raid-mark overrides,
  tank/healer roles, CC and planned CC, native attack eligibility, current-target
  stability, instance/phase/lifecycle guards and ambiguous pulls. Position tests
  cover native Living Bomb after combat/boss death, other carriers, Inferno cast
  lifetime, Shazzrah roles and the eight-path bound. AoE tests cover disappearing
  first/all targets and saturated counts. These controlled cases are not raid play.

## Remaining before the full requested scope is complete

- Boss-by-boss, mechanic-by-mechanic review against each CMaNGOS expansion's
  actual scripts; the earlier inventory is not that complete semantic audit.
- Finish remaining MC, Karazhan and Mechanar mechanics; review new Onyxia and
  Netherspite behavior in actual encounter play. Do not treat a partial boss
  strategy or generic hazard detector as complete raid support.
- Review/implement the other missing raid/dungeon libraries from the complete
  coverage matrix. Preserve normal/heroic, raid-size, expansion, threat, CC,
  movement, admission and spell rules; reject donor boss weakening/aura cheats.
- Resolve remaining class comparison leads (further assigned support,
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
The one-second Aran decision is functional combat state, not a diagnostic cache.
The one-second native boss-cast position is also functional state, not optional
logging instrumentation. These changes introduce no additional diagnostic output.
MC target priority, post-combat bomb handling and AoE lifetime checks likewise add
no logs, counters, worker or SQL table. They are gameplay decisions, not diagnostics.

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
Production reports of training dummies chasing/attacking match this same missing
module. Controlled tests verify the restored passive/no-combat-movement setup,
the core's passive attack-start guard and ten-second inactivity combat reset.
The native module save hook also consumed action-button dirty states before the
normal core saver ran, contradicting its default-table-mirroring comment. The
Classic/TBC correction explicitly mirrors the active bar in the existing save
transaction. An operator-only, once-receipted repair script preserves current
single-spec bars when reactivating a previously omitted module; it is not an
automatic world update and has not been applied to production.

New test programs: `encounter_geometry_test.cpp`, `encounter_runtime_regression.py`,
`combat_policy_regression.py`, and `threat_transfer_regression.py`. Geometry,
actual hazard predicates, all-three-expansion resource/disease predicates and
actual threat-transfer selection tests pass. Existing summon/class/placement/
diagnostic suites also pass. These do not replace client encounter testing.
