# Molten Core playerbot combat audit — 2026-09-22

Scope: the shared playerbots source used by ManTech Classic, TBC and Wrath.
Compared against each core's native ScriptDevAI Molten Core implementation.
These are encounter actions, not changes to class damage rotations or warrior
rage priorities. Normal learned-spell, cooldown, cost, range and immunity checks
remain authoritative. The dungeon strategy activates in map 409.

## Coverage

| Boss | Existing behavior retained | Added in this revision |
|---|---|---|
| Lucifron | Protector-first DPS, ordinary tanking/healing | Off-tank allocation; prioritized Doom/curse removal; Dispel Magic selection for a mind-controlled raid member |
| Magmadar | Lava-bomb avoidance, ranged/healer spacing, generic enrage dispel | Explicit Frenzy response and learned Fear Ward on the current tank |
| Gehennas | Add-first DPS and generic harmful ground-effect avoidance | Off-tank allocation and prioritized curse removal |
| Garr | Deterministic warlock Banish assignment respecting CC | Uncontrolled Firesworn DPS priority, off-tank allocation, non-victim avoidance of low-health/casting Firesworn explosions |
| Baron Geddon | Inferno/Armageddon avoidance; Living Bomb separation even after boss death | Prioritized Ignite Mana removal; attack movement cannot undo a safe-position hold |
| Shazzrah | Ranged/healers outside Arcane Explosion | Curse removal and removal of the boss's magic buff |
| Sulfuron Harbinger | Priest-first DPS | Off-tank allocation and interruption of an active priest Heal, including a priest other than the current target |
| Golemagg | DPS stays on the boss instead of unkillable Core Ragers | Off-tanks acquire Core Ragers; melee DPS retreats at five Magma Splash stacks and holds outside until the aura expires |
| Majordomo Executus | Healer/elite targeting; generic spell-reflect and damage-shield policies | Off-tank allocation and deterministic mage Polymorph assignments; leave a healer available to kill; respect existing CC and native Polymorph immunity |
| Ragnaros | Sons targeting while Ragnaros is submerged; native phase recovery | Ranged/healer spacing and spreading; reactive Wrath avoidance for non-victims, preserving the current tank in melee |

## Safety and behavior boundaries

- Only live, engaged, same-map/instance/phase targets are admitted. No new pull
  automation or world-wide creature scanning was added. Boss-centred add scans
  are bounded to 100 yards. Ambiguous multi-boss selection falls back to normal AI.
- The established tank victim is retained when that victim has the tank role.
  Other tanks receive deterministic add slots, leaving CC targets in the slot
  ordering but never attacking them. With no assignment, ordinary tank logic
  resumes. Submerged Ragnaros uses existing ordinary tank handling of Sons;
  no dedicated wave-wide tank allocation is claimed.
- Direct attack commands remain authoritative for targeting. DPS respects raid
  target marks. Tank assignments intentionally do not all converge on the DPS
  mark. Automatic mage CC excludes the skull healer and preserves one killable
  healer when the skull is absent or marks something else.
- Support selection is rechecked at execution. It runs below urgent healing and
  danger movement. Classic/TBC use Earth Shock for interrupts; Wrath uses Wind
  Shear/Mind Freeze when learned. There are no free spells or bypassed immunities.
- Movement uses the existing native path/hazard validation and bounded candidate
  search. Five stacks for Golemagg and ten-percent Firesworn health are tactical
  thresholds to validate in raids, not promises of optimal DPS or survival.
- Interrupts are the implemented response to Sulfuron's priest healing. This
  revision does not coordinate pulling priests beyond their 60-yard heal range.
  It also does not add geometric separation of Core Ragers, scripted main-tank
  swaps, predictive instant-cast avoidance, or a complete automatic raid route.
- Existing reflect/shield policies remain generic and retain their normal
  thresholds. Boss scripts, immunities, DB content and class rotations are unchanged.

## Verification and deployment

Run the source contract check with:

`python tests/molten_core_source_contract.py --cores-dir <directory-containing-classic-tbc-wotlk>`

The existing C++ regression fixtures were extended for Garr selection, Golemagg
stack thresholds, Ragnaros spacing/tank exemption, Firesworn hazards and attack
movement hold. These fixtures require a compiler; they were not executed during
this source-only task. Tank allocation and support selection have source-contract
checks, not a claim of runtime simulation coverage.

Build and deploy **Classic, TBC and Wrath** to use this shared revision, then
restart each rebuilt realm. **No SQL or client patch is required.** No binaries
were built or deployed as part of this task.

Live raid validation remains required: tank/add ownership under deaths and threat
resets; CC renewal and four-add immunity transition; interrupted priest heals;
raid debuff recovery; Geddon bomb paths; Golemagg retreat/re-engagement; Ragnaros
spacing on lava terrain, knockbacks, and both submerged/emerged transitions.
Appropriate tank/healer roles, learned abilities, gear and raid composition are
still necessary. This audit does not certify an unattended Molten Core clear.
