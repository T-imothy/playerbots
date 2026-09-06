# Tempest Keep native mechanic audit (partial)

2026-09-06. This records selected implemented mechanics, not complete TK support
or a raid clear. Classic cannot activate these TBC/Wrath behaviors.

## Solarian

- Both native `boss_astromancer.cpp` scripts apply 42783 in the normal ruleset.
  Their `WrathOfTheAstromancer::OnApply` expires into the next effect's simple
  value: dev spell 42783 effect 2 base points 42786 -> payload 42787. Its damage
  radius index 13 is 10 yards. 42784 is the application effect, not the explosion.
  The separate pre-nerf 33045 jumping mechanic is deliberately not treated as
  this bomb. No debuff is dispelled, removed, prevented or fabricated.
- Grouped bomb carriers separate from group members; non-carriers avoid nearby
  carriers, including humans. A live current boss tank does not drag Solarian
  across the raid. Actual aura lifetime governs release, even after combat/boss
  death. Map, instance, phase, charm, life, group and teleport guards apply.
- Reuses native-height/path validation, hazard checks and bounded escape geometry:
  at most eight candidate paths per one-second cached plan. Fresh group geometry
  is checked before movement. No path bypass, forced teleport or damage immunity.
  Safe positions stop existing chases without interrupting stationary casts;
  following/charge-like movement cannot immediately undo the safe position.
- DPS prioritizes admitted, engaged Solarium Priests (18806), then Agents (18925).
  Explicit player attack orders, raid targets, assigned/active CC, tank/healer
  roles and current targets within the same priority remain respected. Native
  wild summons record `m_trueCaster`, so the owner chain is add -> spotlight
  (18928) -> boss (18805), even though the original-caster callback notifies the
  boss. This is a bounded lookup, not a new world scan. Missing ownership falls
  back to normal target selection; it does not guess another nearby boss.

## Void Reaver

Native Pounding 34162 is a channel with periodic trigger 34164; the latter's
radius comes from native data. The existing curated boss-cast escape mechanism
now checks both generic and channeled spell slots. It does not flee arbitrary
damage spells. Pounding keeps the current tank planted while other bots can
leave the native radius, hold and resume normal combat when the channel ends.
Arcane Orb 34172/34190 is not treated as a caster-centered explosion. Orb landing
avoidance, knockback/tank coordination and complete Void Reaver remain open.

## Native core prerequisite found and corrected in TBC/Wrath testing branches

The Solarian split indexed three entries without verifying all three summons
succeeded. Both native callbacks now validate three distinct live spotlights
before use; failure invokes normal evade/reset, not a weakened partial phase.
Delayed split/transform callbacks now use the existing combat-only timer policy
so evade cancels them. Reset clears the spotlight list and restores combat state;
successful split completion restores melee disabled at split entry. No damage,
health, rewards, summon quantities, phase delays or normal valid split sequence
were lowered. The old unchecked access was reproduced in controlled actual-source
tests. This is not identified as a cause of any historical production crash.

## Verification and boundaries

`solarian_policy_regression.py` executes actual value, action, target and
multiplier source in all three expansion modes. It checks native payload lookup,
multi-carrier geometry, post-death lifetime, stale destination/ownership, map/phase,
roles, CC, explicit commands, native path rejection, casting and hold cleanup.
`boss_cast_position_regression.py` includes channeled Pounding, current tank,
completion, interruption, unrelated Orb and all earlier cast-registry cases.
Core `test_solarian_split.py` exercises actual callbacks, missing/despawned/wrong/
duplicate spotlights and valid normal split transitions, reproducing pre-fix
unchecked indexing with bounds-checking fixture storage.

Full native builds and actual in-client encounters remain distinct checks.
Solarian's pre-nerf jump handling, full void-phase tactics, Al'ar, Kael'thas,
weapons/advisors/interactions and the other remaining TK mechanics are still open.
No Playerbot SQL/config/logger/worker was added. Existing sampled diagnostics
can identify the new action names. The native core adds one error on an invalid
split before resetting, not per-bot/per-tick reporting.
