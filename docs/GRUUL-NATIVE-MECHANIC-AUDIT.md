# Gruul's Lair: native review and implemented limits

2026-09-06. Partial encounter support, not a completed raid.

## Gruul Shatter

Reviewed both CMaNGOS TBC and Wrath `boss_gruul.cpp`, the corresponding
`SpellEffects.cpp` handlers and local dev spell records. These agree:

- Map 565, boss 19044. Ground Slam 33525 applies native knockback; 39187
  periodically applies Gronn Lord's Grasp 33572. At five stacks the native
  aura script casts Stoned 33652. Shatter 33654 triggers player burst 33671
  and removes Grasp/Stoned in the core.
- Burst 33671 uses radius index 9 (20 yards). Native damage falls with distance
  after the bursting player's combat reach is subtracted. A donor tactic's
  fixed ten-yard spread mitigates damage; it does not completely avoid it.
- Bots observe actual Grasp/Stoned on themselves/group members. No estimated
  encounter timer, aura removal, fake immunity or boss modification is used.
- A live same-instance/phase Gruul and live group are required. Dead, charmed,
  teleporting, wrong-map/group or out-of-world members are excluded. Reset,
  boss death, group departure and removal of the real auras end the policy.
- Existing `CanMove`, height/hazard/path checks and ordinary `MoveTo` remain
  authoritative. Falling/knockback and Stoned do not get bypassed.
- At most 81 geometric candidates and eight non-current destination checks
  are considered per one-second value calculation. Scores are computed once
  per candidate, not in every sort comparison. The current point is checked
  separately without a new path when already at that point.
- Prefer full separation when reachable; otherwise reduce total overlapping
  burst radii. This is mitigation in a crowded room, not a survival guarantee.
  Proposals are at most 24 yards away. A one-yard overlap-improvement threshold
  limits tiny direction changes; GUID-seeded directions reduce identical moves.
- Recheck the point against current group positions before moving. A short
  phase hold cancels an old chase at the current point without stopping a valid
  stationary heal. Hazard escape and ordinary attacks/casts remain available;
  generic following/chasing and movement spells cannot immediately undo spread.
- Classic compiles the entry as a no-op. No TBC spells/behavior activate there.
  Nothing is written to world/character data; no new logging is added.

`tests/gruul_spread_regression.py` compiles the actual value, action, movement
arbitration and geometry in all three eras. It covers lifecycle, native-control
admission, crowded mitigation, bounded work, fresh destinations and wiring.
Native APIs/pathfinding are mocked: native builds and a real group pull remain
separate validation requirements.

## Council review: not implemented yet

Native scripts and dev records were inspected for Maulgar 18831, Krosh 18832,
Olm 18834, Kiggler 18835 and Blindeye 18836. Blindeye's shield 33147 is
non-dispellable and protects Prayer of Healing 33152. Krosh's Spell Shield
33054 is magic and native Spellsteal remains relevant. Maulgar's Whirlwind
33238 is a persistent periodic-trigger aura, not merely a generic cast to avoid.
Mage-tank/support assignment, shield/interrupt timing, Kiggler/Olm handling
and coordinated target selection remain open.

The council review uncovered a general Spellsteal selection mismatch. The mage
trigger previously reused ordinary dispel selection, without the native
`SPELL_ATTR_EX4_CANNOT_BE_STOLEN`, holder positivity or passive-holder checks.
The native cast check does not reject an empty stealing pool, so this could
waste mana/GCD. `CastSpellstealAction` now mirrors the native effect's candidate
predicate using the actual spell's effect dispel mask. It rechecks before
execution and retains native casting, resistance, random candidate selection
and duration/stack transfer. Ordinary dispel policy is unchanged. Classic is a
no-op; `tests/spellsteal_regression.py` tests all three era configurations and
the native TBC/Wrath effect contracts. This does not assign a Krosh mage tank.

The donor `mod-playerbots` Gruul source at b949b50bfcdd4fab937781bac2d7765e39330e4b
was reviewed for coverage, not copied wholesale. Its fixed world positions,
raid-mark rewriting and API assumptions are not imported. Native Hurtful Strike
selects the second threat player in melee; this patch neither fabricates threat
nor claims an off-tank assignment system.

## Test in dev

Use a TBC/Wrath raid group: verify spreading after Ground Slam landing, no
movement while Stoned, no repeated melee chase during spreading, and resumption
after Shatter. Test walls/Cave In, tightly packed players, members dying/leaving
and wipe/reset. Check healing and off-tank melee position outside the Shatter
window. This does not validate a full Gruul kill or the council encounter.
