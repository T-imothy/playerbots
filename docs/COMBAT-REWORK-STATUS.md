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

- Righteous Defense now uses its native friendly group recipient in TBC/Wrath,
  including matching movement prerequisites and fresh dispatch admission.
  Existing tank taunts can respond to Ebonroc's boss-owned debuff in all eras;
  fresh dispatch checks prevent queued taunt-back after a successful swap.
- Heavy new encounter position values use the legacy interval value that
  actually caches for one second. Global combat-value timing is unchanged.
  See `TANK-TARGET-AND-PLANNER-AUDIT.md` for reproduced behavior and test limits.
- TBC/Wrath Magtheridon DPS coordinate native cube clicks/channels with stable
  assignment, occupied-human-cube and exhaustion guards, role preservation,
  normal paths and reset/group cleanup. Native phase-three Debris warnings
  feed the existing hostile-area avoidance before their delayed damage.
  See `MAGTHERIDON-NATIVE-MECHANIC-AUDIT.md`; live five-beam behavior remains
  untested and other Magtheridon mechanics remain under review.
- TBC/Wrath Spellsteal now checks the same positive, non-passive, stealable
  aura-holder conditions as the native effect, both before scheduling and
  immediately before casting. Skip no-op attempts on non-stealable buffs;
  retain real mana, cooldown, resistance, target and native stealing rules.
- TBC/Wrath Gruul spreading observes native Grasp/Stoned lifetime, native
  20-yard Shatter radius and combat reach. Bounded path-validated candidates
  prefer separation or reduced crowding, with fresh group-position checks and
  native movement/control restrictions. Classic is a no-op. This is partial
  Gruul support, not a complete raid; see `GRUUL-NATIVE-MECHANIC-AUDIT.md`.
- TBC/Wrath Karazhan DPS can prioritize Illhoof's actual boss-owned passive
  Demon Chains during a current sacrifice and Curator's four native flare
  variants. Preserve manual orders, marks, CC and tank/healer jobs; reuse normal
  combat and core destruction mechanics. See `KARAZHAN-TARGET-AUDIT.md`.
- Onyxia/Pathaleon add selection now preserves explicit attack orders as well as
  marks, and a stale invalid mark no longer blocks otherwise valid add handling.
- Pet spell feasibility now uses the actual pet caster and native cast checks,
  with ownership/lifecycle guards and native hostile spell-opener behavior
  preserved. Unsupported pet destination/gameobject commands are rejected.
- Wrath cleansing-totem actions and presence checks use the merged native spell;
  Classic/TBC keep separate disease/poison spells. Legacy strategy names remain.
- Coordinate spell sight checks use native linear-distance units; battleground
  squared-distance calls are unchanged. See `PET-AND-TOTEM-ADMISSION-AUDIT.md`.
- Vael destinations are rechecked against current group positions immediately
  before movement, including after native height/path adjustment; Naxx and BWL
  ignore members that no longer belong to the same group.
- BWL Burning Adrenaline uses the native aura-removal explosion and radius for
  separation, with active-tank protection, aura-lifetime cleanup, group/phase
  guards, bounded native paths and movement arbitration. All-three-expansion
  actual-value/action/multiplier tests pass. Existing Hunter Tranquilizing Shot
  routing and native Magmadar/Flamegor/Chromaggus frenzy metadata were confirmed;
  no duplicate boss-specific dispel or removable final-enrage rule was added.
- BWL Nefarian priest call follows native aura 23401 and direct-heal proc rules:
  avoid harmful automatic direct heals, interrupt only an eligible ongoing heal,
  preserve Renew/shields/damage, and handle Wrath's native Penance/channel split
  separately. Actual policy and complete casting-wrapper tests pass in all
  three expansion modes. See `BLACKWING-LAIR-MECHANIC-AUDIT.md`; this does not
  complete Nefarian or BWL.
- Shared named-spell feasibility forwards the requested effect mask. Three
  legacy boolean callers (generic cast trigger, pull and reach) explicitly use
  the unspecified mask, retaining their intent. Unspecified unit masks use
  native `GetCheckCastEffectMask`/`GetCheckCastSelfEffectMask`; immunity and
  damage prechecks inspect only selected effects. An AoE center is not every
  recipient, and an unrelated self effect cannot rescue an immune target effect.
  Native CheckCast and final targeting remain authoritative. Tests use the
  actual wrapper/filter and each core's native mask helpers.
- Spell allegiance prechecks now pass the real caster and target to native
  `IsPositiveSpell`, preserving neutral/dual-purpose targeting instead of
  misclassifying it as always positive. Strict friendly/enemy restrictions and
  existing explicit neutral exceptions remain. Actual gate tests use each
  expansion's native neutral-target classifier; this is not a new spell rule.
- Shared dispel eligibility skips a nearly-expired aura rather than stopping the
  scan and ignoring every other removable effect. Wrong dispel types cannot veto
  a valid later candidate; permanent negative-duration auras are not mistaken
  for nearly-expired effects. Existing friendliness, spell/effect positivity,
  name exclusions and duration configuration remain; native casting decides
  actual removal. World/map/phase guards reject invalid target contexts. The
  regression reproduced the old false negative before the fix.
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

- Naxxramas burst separation now observes native Grobbulus injection and
  Kel'Thuzad mana-detonation payload radii/lifetimes, with tank preservation,
  bounded paths and fresh destination/group checks. Automatic disease dispels
  cannot detonate injection; spell-aware party selection avoids repeatedly
  choosing unsafe Cleanse recipients. New periodic disease-cleansing/totem casts
  are withheld during Grobbulus. Existing pre-pull cleanses are not deleted.
  See `NAXXRAMAS-MECHANIC-AUDIT.md` for evidence and explicit remaining limits.
  These source-tested mechanics are partial Naxx coverage, not a full raid clear.

- Non-damage cast eligibility no longer overwrites a native immunity result
  with an unused trailing effect. It rejects a spell when all populated effects
  are immune, but preserves a spell with an actually usable partial effect.
  Native spell-level and per-effect immunity APIs, subsequent `CheckCast`,
  damage-spell handling and existing effect-mask forwarding are unchanged.
- Marked CC now honors native castability before committing to a target, while
  still letting the player's mark override automatic health/DoT/target heuristics.
  Normal reach-spell handling can close distance/LOS; it does not bypass the
  eventual cast check. Automatic tank-distance checks use native map/phase and
  lifecycle boundaries. Existing owned CC on a live eligible target still
  prevents another assignment; a stale/dead/off-map old target cannot block it.
- Actual-code tests reproduced the empty-effect immunity overwrite, marked-CC
  castability bypass and stale owned-CC veto. Corrected combinations pass in all
  three expansion modes, including partial immunity, explicit mark precedence,
  automatic exclusions, death, removal, instance/phase changes and teleportation.

- Shared interrupt selection now checks native immunity only for actual
  interrupt/stun/silence effects and accepts an effect that can work even when
  an unrelated secondary effect is immune. Existing native cast-interruptibility
  requirements and normal action/cooldown/range/cast checks remain. Target
  removal, death, map/phase changes and bot teleportation reject the read safely.
  The previous veto was reproduced with the actual helper; corrected cases pass
  in all three expansion fixtures. This is not a new raid interrupt coordinator.

- Shared threat history now records accepted changed samples instead of skipping
  them, seeds first/delta-only reads safely and rebaselines on target changes.
  Friendly target proxies are resolved to their current enemy before recording
  its GUID; missing, dead, removed or cross-instance targets are rejected through
  native world/map checks (including phase on TBC/Wrath). Tank membership reads
  also reject teleporting/removed/cross-phase members. This changes bot decisions,
  not native threat generation. Relative threat safely saturates at 255 instead
  of wrapping, with zero-denominator and nonfinite guards.
- The shared memory-value reset now initializes its next baseline; historical
  getters no longer dereference an empty log or malformed pair expression. The
  original configured sampling intervals and 10/30-entry limits remain. The
  position-history consumer refreshes its value and stops at the requested time
  window, so much older movement cannot mask current immobility. Existing stuck
  thresholds and real-player-group exclusions remain untouched. This warrants
  checking autonomous wandering/recovery as well as combat in dev.
- Actual-source deterministic tests reproduce the old history append inversion,
  threat percentage overflow and movement-window failure before their respective
  fixes. Corrected history, threat lifecycle/proxy switches, absent targets,
  first-use debug, clock rollback, count bounds and movement-window cases pass
  under all three expansion modes. Native full builds are separately required;
  these defects are not established causes of any reported production crash.

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

### Latest tested source follow-up (2026-09-06)

- Ragnaros DPS selects live engaged Sons of Flame even while the submerged boss
  is absent from the native attackers list. Ordinary target admission, player
  marks/commands, tank/healer roles, CC and ambiguous-pull fallback are preserved.
- Wrath-only Onyxian Lair Guards (native summon 68968 -> creature 36561) join
  eligible add selection. Classic/TBC do not acquire this Wrath encounter rule.
  This is target selection, not a claim of complete guard/boss mechanic support.
- Native reflectable spell decisions include the 50% boundary (Majordomo), still
  using the current school-specific reflection chance and core reflectability.
  This is pre-cast selection, not cancellation of an already launched spell.
- Netherspite now rechecks native phase/instance/lifecycle for boss, portals and
  beam participants, excludes charmed bots, and checks fresh hazards/path safety
  immediately before movement. Actual value/action tests cover human precedence,
  exhaustion without aura removal, phase switches, disappearance and path limits.
- Native map/phase guards are also applied to the reviewed Aran/Prince, Mechanar,
  Onyxia and boss-cast position paths. Onyxia/Pathaleon add priorities repeat
  normal native attack/assigned-CC eligibility instead of trusting an old list.
- Movement-effect spells cannot undo a current MC or Netherspite safe-position
  decision; normal stationary spells, attacks and hazard escape remain eligible.
- Removed the ineffective foreign-attacker cache lookup rather than enabling its
  unsafe shortcut. Existing owner/group/master aggregation and duel/pet sources
  remain. The unused undocumented `AiPlayerbot.ShareTargets` setting is retired;
  old configs containing it need no rewrite. No new shared cache was introduced.
- Battlemaster selection safely skips missing records/templates/factions, and
  creature-data diagnostic formatting handles null records and missing templates.
  These guards are not attributed to any production crash without a matching dump.

These are passing controlled actual-source tests, not completed raid clears.
The complete raid/dungeon/class checklist below remains open.

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
Threat and movement-history corrections reuse existing bounded functional value
logs, not output files. They add no diagnostic scan, counter, table or worker,
and do not alter general calculated-value cache cadence. Keep this functional
history when optional diagnostics are disabled; no runtime savings are claimed.
Per-effect interrupt candidate checks also add no diagnostic output or worker.
Non-damage immunity and CC eligibility corrections likewise add no diagnostic
output, background scan, SQL state or new persistent cache.

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
