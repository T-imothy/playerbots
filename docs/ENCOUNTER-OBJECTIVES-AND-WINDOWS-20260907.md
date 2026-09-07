# Encounter objectives, movement and healing windows

This is implementation and verification evidence for the continuing raid/dungeon
audit. It does not certify complete encounter strategies or completed raid runs.
All work remains on the enhancement branches; this continuation has not changed
production files, permanent database tables, or ManTech baseline branches.

## Native objectives and rescue

- Hakkar: native Son of Hakkar death casts 24319, creating Poison Cloud 14989.
  Its EventAI event 11 casts 24320 once on spawn; that spell applies 24321.
  Bots therefore gather before an already engaged Son dies. A ten-second cap
  limits the offense hold below 40% Son health. The main Hakkar tank stays
  anchored, actual poison ends movement, and healing remains available.
  A lingering visual cloud is not treated as a repeatable poison source.
- Ossirian: one eligible DPS uses the native crystal interaction as the native
  weakness expires. The tank's approach remains stable when the boss crosses
  the crystal. Native trigger position, spell range, LOS, interaction range and
  the selected user's continued eligibility are checked before clicking.
- Naj'entus: a valid spine is a live 185584 summoned by 39929, with its actual
  spawner still suffering boss-owned Impaling Spine 39837. A DPS is preferred
  for rescue; a healer is a fallback. Tanks, impaled players, full inventories,
  manual players and bots unable to move are excluded. The normal gameobject
  handler creates item 32408 and triggers the linked 185601 rescue trap/39977.
  Shield breaking uses an actually owned spine through the normal item path.
  Exactly one ready, in-range bot is selected. The automated throw waits while
  an exposed living group member has at most the raw native 39878 burst damage
  (8,500 in the inspected data). This conservative check does not estimate
  absorption or resistance; manual item use remains available.

## Movement and items

- Akil'zon: use the actual 44007 dynamic object's ground position, rather than
  the lifted player's altitude. Require the native 43648 caster relationship,
  correct group/phase, and a live storm. Spell 43657 excludes 44007 recipients.
  Recheck terrain-adjusted destinations against the live shelter radius.
- Keristrasza/Hodir: use the existing in-place jump at two cold stacks. At four
  stacks, reaction handling may interrupt a cast. Toasty Fire, Flash Freeze and
  invalid movement/lifecycle states suppress this action. Native Hodir reads
  IsMoving (including FALLING); the fixture proves the policy and normal jump
  delegation, not the resulting live periodic-tick timing.
- Mother Shahraz: separate actual Fatal Attraction 41001 carriers beyond its
  40870 link radius, while also avoiding 40871 splash on other group members.
  Those radii are 25 and 15 yards in both inspected cores. Linked players get
  evenly spaced GUID-ranked escape directions from their shared teleport point.
- Omor/Murmur: separate normal/heroic Treacherous Aura/Bane (30695/37566,
  payloads 30697/39298) and Murmur's Touch (33711/38794, payload 33686).
  Their inspected damage radii are 15 and 20 yards respectively. Add a two-yard
  movement margin. Native aura ownership and current positions are rechecked.
- Archimonde: use an actually owned Tears of the Goddess in the final 1.5
  seconds of the existing bot landing deadline. The bot knockback simulation
  holds its apex, so changing altitude cannot reliably establish descent.
  Existing feather fall, item cooldown and encounter/lifecycle checks remain.
  The action does not manufacture an item or change native fall information.
- Garr: banish slots exclude warlocks whose `cc` strategy is disabled, as well
  as dead, absent, unlearned, manual or otherwise ineligible participants.

The separation planner requests up to 40-yard candidates to clear the actual
25-yard Fatal Attraction link. Other callers retain the existing 24-yard
default. Path attempts remain capped at eight. Ordinary offense, stationary
healing and designated emergency escapes retain their movement exceptions.

## Wrath Loatheb healing

Both native raid spell lists apply Necrotic Aura 55593 every 20 seconds. Bots
may select injured targets in its final three seconds and begin a direct heal
whose native haste-adjusted cast time finishes at least 100 ms after expiry,
within the next 2.8 seconds. Instant heals, channels and spells without a direct
healing effect do not receive that exception. Another complete healing blocker
also prevents it. Single-target and AOE actions recheck before dispatch, so a
new aura application cannot reuse an earlier opening. Classic/TBC healing
retains the ordinary complete-healing-block check.

## Verification and remaining validation

### Heigan's floor waves

The live controller's 29351/30114 aura tick count identifies the next native
wave in the six-step sequence. Spell-target rows and their effect masks identify
which live fissures will erupt; safe-band fissure positions provide candidate
destinations. The platform cloud starts the move to the floor before the first
fast wave. Wave changes invalidate the cached destination immediately. Reached
safe positions stop an old chase without canceling a stationary heal.

Development data contains 115 floor fissures in each era. A static clearance
check found 16–23 candidate centers per wave; this is not proof of a traversable
native path or successful live dance. The present radius margins are conservative.
Native spell targeting differs by era and target mode; a blanket claim that
all area spells add both units' combat reach would be incorrect.

### Healing objectives and Wrath adds

Native full-health wound removal now remains a healing objective above the
normal almost-full threshold. Target selection includes those patients, the
existing medium-heal trigger remains available, and overheal cancellation
preserves the finishing cast. The exact native wound IDs are 43093, 31956,
38801, 35321, 38363, 39215 and 48920 in TBC/Wrath.

Wrath's positive native healing-absorb amounts also count as healing work,
including at full health. The native amount is added to the selection deficit;
critically injured patients precede absorption objectives. Healing casts are
not canceled solely for full health while absorption remains. This covers
Incinerate Flesh's native 301 aura in all four data variants without changing
health, removing auras directly, or inventing healing credit.

Emalon's boss-owned Overcharge 64218 selects the affected Tempest Minion even
before its first self-applied stack. Lightning Nova 64216 uses the shared
native-radius escape. The inspected 25-player spell 65279 has a 100-yard radius,
outside that planner's escape bound, and no native spell script binding was
found. Its encounter behavior remains unresolved; the bot does not invent a
25-yard safe point. Jaraxxus's real volcano and portal summons receive DPS
priority only when native target validation allows attacking them. Manual
targets, CC protection, healer/tank roles and lifecycle checks remain in force.

Actual-method regression fixtures cover these rules, native ownership, stale
objects/auras, path failures, role changes, inventory/cooldown failures and map/
phase transitions. The 109-runner suite and all three native builds passed
through Heigan, Naj'entus and Loatheb. Healing-objective and Emalon/Jaraxxus
targeted tests, all three subsequent native builds and the 110-runner full
suite passed. The radius-data follow-up corrected test inputs for Emalon's
25-player Nova and both Keli'dan Novas; those are tracked separately.

These checks have not run every mechanic inside its real room with a live
group. Complete raid phases, routes, vehicles, event progression and the other
entries in the main gap register remain required. No encounter-clear percentage
or production readiness follows from compilation or these fixtures.
