# Molten Core native-mechanic audit — partial implementation, not raid completion

Scope: map 409 in all three ManTech testing cores. Native evidence comes from
`src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core/` in each core.
Lucifron, Gehennas, Garr, Golemagg, Sulfuron, Majordomo and Ragnaros script code
compared equal across Classic/TBC/Wrath after ignoring comments/whitespace.
That comparison does not establish identical player spells, gear or difficulty.

| Boss | Native rule / reviewed evidence | Implemented bot handling | Still open |
|---|---|---|---|
| Lucifron | Boss 12118; protector 12119; Doom 19702 and curse 19703 in `boss_lucifron.cpp` | Eligible DPS prioritizes engaged, non-CC protectors using normal attack admission | Verify class dispel/decurse reachability, mind-control response and actual encounter |
| Magmadar | Existing core and bot fight scripts; native lava objects and frenzy/fear | Existing lava avoidance/ranged separation/potion support retained | Verify learned Tranquilizing Shot timing, fear recovery, tank positioning and all remaining mechanics |
| Gehennas | Boss 12259; flamewaker 11661; curse 19716, Rain of Fire 19717 | Eligible DPS prioritizes engaged flamewakers | Verify Rain of Fire's native effect against generic ground-hazard handling; curse response |
| Garr | Boss 12057; firesworn 12099; death eruption 19497; separation trigger 23487/23492; mass eruption 20482/20483 | Ordinary native class combat retained; no invented banish/add assignments | CC assignment, explosion-aware DPS/AoE, native banish lifetime, tank/add separation |
| Baron Geddon | Native Inferno damage 19698, Living Bomb 20475, Armageddon 20478 | Native-radius combined hazard escape; bomb separation follows aura through boss death/combat exit | Ignite Mana dispel handling, actual raid play and recovery |
| Shazzrah | Native explosion 19712 plus remaining curse/counterspell/defensive effects | Ranged/healer spacing, excluding current boss victim | Validate all dispel/interrupt/curse interactions and teleport recovery |
| Golemagg | Boss 11988; rager 11672; ragers have death prevention and heal 17683 below 50%, die through boss-death event; boss quake at 10% | Eligible DPS targets Golemagg; all tank/off-tank roles unchanged | Native Magma Splash stack management, ranged fallback positioning, off-tank coordination and burn transition |
| Sulfuron | Boss 12098; priest 11662; native heal 19775, SW:P 19776 and Immolate 20294 | Eligible DPS prioritizes free, engaged healing priests | Interrupt coverage/coordination and dispel behavior; existing native casts still decide success |
| Majordomo | Boss 12018 cannot die normally; eight add deaths end encounter; healer 11663/elite 11664; reflection 20619/21075; later sheep immunity 21087 | DPS prioritizes free healers, then elites; never retargets tanks or breaks assigned CC | Reflection-aware action filtering, late-wave CC immunity behavior, tank assignments and native gossip/event progression |
| Ragnaros | Boss 11502; submerged aura 21859 and untargetable flag; sons 12143; normal threat loss on Wrath 20566; Magma Blast 20565 if not tanked | Existing normal target admission rejects untargetable boss; ordinary combat remains | Explicit phase/son assignment, native knockback recovery, mana-user spacing, tank return and wipe/reset checks |

## Target policy boundaries

The new MC action only handles the five explicitly mapped target policies above.
It uses existing attackers/possible-target values and `AttackAction`, not world
scans, fabricated threat, teleportation or core boss changes. Native attack
validation is repeated before selection. Tank/healer roles and the current boss
victim are excluded. A valid commanded target or configured raid mark defers to
the existing player-directed path. Breakable CC, hard CC and planned CC are
excluded even when the generic target list offers them as a fallback. Ties retain
the current target; generic DPS assist is suppressed only while this valid
encounter target exists, preventing an add/boss oscillation.

No new Garr or Ragnaros routine is claimed by that action. A CMaNGOS script using
an immunity/death-prevention flag is not permission to remove it. Donor AC MC
code was consulted for comparison only; no donor aura cheats or boss changes
were imported.

## Shared issues discovered during this review

- The common dispel scan returned false for every remaining aura after finding
  one nearly-expired effect, even an unrelated dispel type. Corrected to skip
  only that candidate, keep scanning and preserve native permanent durations.
  The old source reproduced the failure in a standalone actual-code test; the
  correction applies to all classes using this helper, not just an MC boss.
  Normal cast success, resistances and the existing dispel policy remain native.
- Mage cure strategies already provide a Remove Lesser Curse fallback in earlier
  expansions; hunters already schedule learned Tranquilizing Shot on an enrage
  trigger in all eras. Those are not missing action implementations. Actual raid
  timing/coordination and target selection still need encounter validation.
- AoE position used uninitialized bounds when the first selected GUID vanished
  before its second resolution. This is corrected and covered by actual-source
  tests for first/all GUID disappearance, lifecycle, instance/phase and count
  saturation. This does not by itself prove splash spells never break nearby CC.
- Geddon avoidance previously required a live boss/combat, despite a remaining
  bomb aura. It now follows native carrier lifetime with noncombat dispatch and
  movement arbitration; tests cover post-kill/despawn, nearby carriers, phase,
  interruption, native-radius inputs and the existing eight-path-query bound.
- Separate open audit lead: `AttackersValue.cpp` constructs the shared-value key
  with `"attackers" + !qualifier.empty() ? ...`, whose precedence does not build
  the intended key. Changing that enables a previously ineffective cache-sharing
  path; its owner/lifecycle/target-validity behavior needs review before enabling
  it. It is not silently included in the MC changes or claimed fixed.

No new database changes or diagnostics are required by these implementations.
Controlled regressions do not replace real pulls, player commands, CC assignments,
wipe/reset, dispel, knockback, tank/off-tank and after-kill Living Bomb tests.

## Follow-up native checks, 2026-09-06

- Read-only `spell_template` queries in all three dev worlds confirm Sulfuron's
  heal 19775 is a native heal effect. The shared interrupt helper previously
  rejected every interrupt when any unrelated spell effect was immune. It now
  checks actual interrupt/stun/silence candidates individually through native
  `IsImmuneToSpell` (effect mask) and `IsImmuneToSpellEffect`, preserving native
  `IsInterruptible` and subsequent cast checks. Actual-code fixtures reproduce
  the failure and cover the correction, including removed targets and map/phase
  boundaries. This is shared capability, not proof of coordinated raid kicks.
- Majordomo's native 20619 is a reflect aura with base points 49; core aura
  amounts and `GetReflectChance` support the 50% reflect mechanic. Existing
  `CastSpellAction::isUseful` only declines reflectable casts above 50%, so this
  does NOT provide a full Majordomo reflection policy. Native 21075 is a damage
  shield with base points 99; ordinary melee safety uses a 10%-of-bot-max-health
  threshold, not an unconditional stop on that boss's shield. Do not claim either
  existing generic check completely handles this encounter.
- Native 21087 carries mechanic-immunity misc value 17 in every dev world.
  Standard CC actions still go through native cast checks. Explicit CC target
  selection takes a marked target before checking its castability; that selection
  path and the general non-damage effect-immunity fold remain audit leads. No
  immunity or encounter aura has been removed or bypassed here.
- Threat/history corrections are shared, not a fabricated MC threat model:
  missing/changed targets safely reset history, percentage overflow is prevented,
  and live native threat tables are read unchanged. This does not substitute for
  actual tank/off-tank, knockback, wipe/reset and role tests.
