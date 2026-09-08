# Healing coverage audit — Classic, TBC and Wrath

Date: 2026-09-08. Scope: Priest Holy/Discipline, restoration Shaman, restoration Druid and Holy Paladin. Reviewed existing actions and missing scheduling, learned/talent availability, targeting, prerequisites, shared healing selection, mana recovery, movement, support buffs, and healer-DPS controls. This is a source audit with controlled C++ regressions and native builds, **not a live-combat certification**.

## What changed

- **All three:** Shaman and Druid Nature's Swiftness now have critical-health healing actions with the cooldown/form prerequisites attached. Ordinary heals remain available when the talent is absent or on cooldown. A healthy party no longer causes the Druid action to waste the buff. Restoration Druids gain a scheduled Barkskin defense; Classic requires critical self-health because its version penalizes cast time.
- **All three:** restoration Shaman Chain Heal and Priest group heals gain recovery scheduling outside combat. Holy Priest and older Holy Paladin recovery priorities now use healing priorities instead of ordinary movement/buff priorities. Holy/Discipline priests explicitly heal themselves between fights.
- **TBC and Wrath:** Earth Shield maintenance moves from raid-only scheduling into shared restoration buffs, covering PvE, dungeons, raids and PvP. It prefers a tank, then an attacked ally, then the master, then another eligible group member. A missing formal tank role therefore no longer prevents every assignment.
- **TBC and Wrath:** Prayer of Mending becomes a maintained Holy/Discipline support buff. Binding Heal is scheduled when both the priest and another patient are injured. The already-implemented Power Infusion action is scheduled in later-expansion boost strategies. Discipline receives a self-targeted emergency Pain Suppression route.
- **Wrath:** Riptide gains critical-health and medium-health routes instead of only the low-health band. Tidal Force gains a learned/cooldown-gated boost route for noncritical healing pressure. Native Tidal Waves, Earthliving and Riptide/Chain Heal effects are left to the core.
- **Wrath:** restoration Lifebloom uses its existing stack/expiry-aware trigger instead of requiring Clearcasting. Nourish and Wild Growth also work during recovery outside combat.
- **Wrath:** Guardian Spirit gains Holy emergency routes; Discipline Penance gains self-healing and outside-combat routes. Hymn of Hope gains a guarded low-mana route, with a reaction that interrupts that exact mana channel if healing pressure or incoming attacks develop. It does not cancel Divine Hymn or ordinary healing channels.
- **Wrath:** Holy Paladin maintains Beacon of Light and Sacred Shield, and can use learned Aura Mastery with Concentration Aura while attacked during noncritical healing pressure.
- Maintained shields/buffs preserve the caster's existing assignment, including a jumped Prayer of Mending. They avoid repeatedly moving the buff around the group or alternating Earth Shield and Water Shield on the healer. Another caster's buff on one person does not suppress all other eligible recipients.
- Protection-target selection rejects strangers, dead/offline/teleporting/hostile/dueling members and, in Wrath, incompatible phases before choosing a threatened group member.
- Classic/TBC restoration schedules no longer request Wrath-only Riptide or Earthliving Weapon. The shared Earthliving-to-Flametongue fallback remains intact for Wrath characters that have not learned Earthliving yet.

## Expansion, level and mode rules

Learned spells are the authority, not the selected preset name or character level alone. Each cast resolves the current learned rank and still uses the native core's mana, cooldown, range, line-of-sight, target, form, reagent and casting restrictions. Changing a preset does not grant an unspent talent or an untrained spell.

Native Talent.dbc places restoration Shaman Nature's Swiftness at a minimum talent level of 30, Mana Tide at 40, Earth Shield at 50 in TBC/Wrath, and Riptide at 60 in Wrath. These are minimum tree-investment levels, not automatic grants. A level-42 shaman cannot have normally acquired Earth Shield or Riptide through those talent trees. Wrath Tidal Force is a different, earlier talent. Trainer spell levels/ranks remain native.

The engine has PvE, raid and PvP class strategies; there is no fourth independent class rotation named “dungeon.” Dungeon bots inherit their active class strategy plus dungeon/encounter overlays. The new shared healing and buff routes are reached through all three mode implementations. The compiled routing test exercises five healing specializations × three modes × two states × three expansions (90 combinations), with each mode's buff/boost/AoE/cure inheritance. Individual encounter overlays and player overrides can still affect execution.

The generated [route appendix](HEALER-COVERAGE-ROUTES.md) lists actual action, trigger and priority entries inherited by every reviewed spec/mode/state. It is scheduling evidence, not proof that a particular live bot has the required strategies enabled or that every cast will succeed.

## Spell coverage and targeting

“Shared checks” below means learned/native cast eligibility plus current target, health, aura, healing-policy and strategy gates. Direct heals with an accompanying HoT retain their existing emergency direct-heal exception; pure HoTs avoid redundant application. AoE healing additionally requires the configured injured-group threshold and eligible nearby recipients. The engine's existing incoming-heal distribution, healing-absorb and full-health-wound handling remain active.

| Class / spell family | Availability | Trigger / target and principal constraints |
|---|---|---|
| Priest Lesser Heal, Heal, Greater Heal, Flash Heal | All | Self or selected injured group member; health bands. Earlier learned heals remain alternatives when the requested higher spell is unavailable. Native mana/cast time and shared checks apply. |
| Priest Renew | All | Self/group recovery bands. Existing HoT suppresses redundant refresh; emergency direct heals remain separate. |
| Power Word: Shield | All | Emergency patient and attacked self; native Weakened Soul/aura restrictions still apply. |
| Prayer of Healing | All | Injured-group AoE route; Classic/TBC use their self/group version, Wrath its targeted AoE action. Now also scheduled during recovery. |
| Circle of Healing | TBC/Wrath talent | Holy injured-group route; learned spell and AoE eligibility. Existing Prayer of Healing fallback remains. |
| Prayer of Mending | TBC/Wrath | Holy/Discipline buff maintenance plus existing AoE routes; tank/attacked ally preferred, existing caster assignment preserved. Requires another eligible group member. |
| Binding Heal | TBC/Wrath | Holy/Discipline critical/low/medium patient routes; another patient and priest below medium health, then ordinary healing checks. |
| Penance | Wrath talent | Discipline low/critical self and group patient, both states. Native friendly-target Penance effect chooses the healing channel. |
| Desperate Prayer | Learned racial/talent by era | Critical self-health; native availability/cooldown. Wrath talent is not granted to every priest. |
| Guardian Spirit | Wrath talent | Holy critical self or selected group patient in combat; native cooldown and aura checks. |
| Pain Suppression | TBC/Wrath talent | Threatened eligible group member; added Discipline critical self route. Native cooldown and buff validity. |
| Divine Hymn | Wrath | Existing healer-only critical-group route. Native channel and cooldown remain. No new mechanics or channel timing introduced. |
| Inner Focus / Power Infusion | Learned talent by era | Boost strategy; native ready/learned trigger. Power Infusion honors boost-target selection, with the existing self-target fallback. |
| Shadowfiend | TBC/Wrath | Low mana, valid enemy target; retains corrected enemy targeting. It is mana recovery even though the summoned pet deals damage. |
| Hymn of Hope | Wrath | Low self mana, stationary, not personally attacked, no patient below medium health or heal-removable wound/absorb. Rechecked at execution. Exact channel canceled when attacked or low/critical healing pressure develops. In-combat route; ordinary drinking handles recovery out of combat. |
| Priest Fortitude/Spirit/Shadow Protection, group prayers, Inner Fire, Fear Ward, racial buffs, Levitate | By learned era/race | Existing buff-target, aura, reagent and environmental gates. Group prayers retain single-target alternatives. |
| Priest Dispel Magic / Cure or Abolish Disease | All as learned | Cure strategy, eligible self/group dispel targets; existing protected-aura and native dispel restrictions. Offensive dispel/CC are separate utilities. |
| Priest Resurrection | All | Dead group member outside combat, corpse/range/cast eligibility. |
| Shaman Healing Wave / Lesser Healing Wave | All | Self/group health bands. Critical LHW and HW alternatives remain independently available; earlier learned HW is a fallback. |
| Shaman Chain Heal | All | Injured-group target/threshold, combat and recovery. Native jump range and party/raid effect rules remain. |
| Shaman Nature's Swiftness | All, talent | Critical self/group HW action with learned/ready NS prerequisite. No deliberate idle cast when nobody needs healing. |
| Earth Shield | TBC/Wrath talent | Shared restoration buff strategy, maintained eligible group assignment; does not require an existing formal tank role. Native charges and elemental-shield rules. |
| Riptide | Wrath talent | Critical, low and medium self/group bands. Emergency direct healing can remain useful with its HoT present; medium-health maintenance avoids redundant aura application. |
| Tidal Force | Wrath talent | Restoration boost while someone is low but nobody selected/self is critical; native cooldown and aura. Emergency direct healing wins. |
| Mana Tide Totem | All, talent | Existing low-mana restoration route; native totem/cooldown/placement. Existing mana-potion fallback retained. |
| Water Shield / Earthliving Weapon | TBC+ / Wrath | Existing restoration buff/enchant maintenance. Older eras use their available imbues. Native Earthliving proc handles its healing. |
| Healing Stream / Mana Spring and other support totems | By era | Totem strategy, existing slot, party and learned-spell choices/fallbacks. Manual totem overrides remain authoritative. Native ranges and effects unchanged. |
| Shaman poison/disease cures and cleansing totems | By era | Existing cure/totem routes; learned spell, dispel type, target and native era availability. |
| Cleanse Spirit | Wrath talent | Existing poison/disease/curse self/group triggers; learned native talent required. |
| Bloodlust / Heroism | TBC/Wrath | Existing boost routes and native faction, exhaustion/sated, mana and cooldown restrictions. |
| Ancestral Spirit / Reincarnation | By learned availability | Group resurrection / existing dead-state handling and native cooldown/reagents. This audit does not promise a new strategic wipe-recovery planner. |
| Druid Healing Touch / Regrowth / Rejuvenation | All | Self/group health bands; restoration caster-form prerequisite, existing direct-heal fallbacks and HoT rules. |
| Swiftmend | All, talent | Critical self/group rescue; learned/ready spell and appropriate existing HoT/native target conditions. Regrowth/Healing Touch alternatives remain. |
| Druid Nature's Swiftness | All, talent | Critical self/group Regrowth action; caster form before NS prerequisite. Normal spells remain eligible with NS unavailable. |
| Tranquility | All | Existing injured-group channel, combat/recovery, shared AoE eligibility. Native channel and group limits unchanged. |
| Lifebloom | TBC/Wrath | Existing tank/under-attack selector with stack/expiration checks; Wrath no longer requires Clearcasting to enter the action. It is not a universal multi-target HoT distribution planner. |
| Nourish / Wild Growth | Wrath / Wrath talent | Low-health self/group direct heal / injured-group AoE; both combat and recovery. Native HoT bonuses and target caps retained. |
| Innervate | All | Existing low-mana eligible boost-target/self selection; zero-mana-power classes excluded, native cooldown/learned checks. |
| Barkskin | All | Restoration healer under attack. Classic requires critical self-health due to its native casting penalty; TBC/Wrath permit the normal defense. |
| Tree of Life / caster forms | TBC/Wrath talent | Existing form actions respect each expansion's casting restrictions. New NS healing requests caster form first. |
| Mark/Gift of the Wild, Thorns, poison/curse removal | By era | Existing buff/cure targets, reagents, aura and native dispel checks; optional strategy required. |
| Rebirth / Revive | All / Wrath | Existing combat resurrection / outside-combat resurrection; native cooldown/reagents, dead eligible recipient. |
| Paladin Holy Light / Flash of Light | All | Self/group health bands with emergency healing and native cast checks. Recovery priorities normalized. |
| Holy Shock | All, talent | Existing explicit self/group healing routes, native cooldown and friendly target. Ordinary Holy Light remains available. |
| Lay on Hands / Divine Shield | All | Existing emergency self/group and self protection; Holy Light alternatives retained. Native cooldown/Forbearance/era rules remain. |
| Blessing/Hand of Protection, Freedom, Sacrifice | By era | Existing threatened-member, roots and damage-transfer policies. Protection selection now rejects ineligible group victims earlier. Native physical immunity and damage transfer are not modified. |
| Beacon of Light / Sacred Shield | Wrath | Holy buff strategy maintains one caster assignment each, prefers tank/attacked ally, avoids stealing another caster's aura on that recipient. Native healing transfer, proc/HoT and limits remain. |
| Divine Favor / Divine Illumination | All talent / TBC+ talent | Existing Holy boost and low-health preparation routes; native mana cost/crit effects and cooldowns. |
| Aura Mastery | Wrath talent | Holy boost with Concentration Aura, self attacked, noncritical low-health pressure. Other aura-specific proactive cooldown planning is not added. |
| Paladin auras, blessings, seals and healing/mana judgements | By era | Existing aura/blessing configuration and spell variants. Support judgements remain separate from the offdps attack/assist toggle. |
| Cleanse / Purify / Redemption | By learned era | Existing dispel-type and resurrection routes with native eligibility/fallbacks. |
| Potions / runes / drinking / racials | Shared, by item/spell | Prior mana-potion eligibility/fallback fixes retained; current mana recheck, real level/item availability, health cost, cooldown, combat/arena and strategy gates. Drinking remains outside combat; no consumable or GCD cheats added. |

## Deliberate limits and remaining unsupported behavior

- **Lightwell:** action/prerequisite exists, but reliable autonomous placement and party interaction policy remain unsupported. No automatic placement/click system is introduced by this patch.
- **Mass Dispel:** existing direct action remains; this patch does not add a general friendly/offensive AoE placement and protected-aura planner. Ordinary cure/dispel routes remain in use.
- **Divine Sacrifice:** no new automatic raid-wide damage-redirection policy. Safe recipient pressure, cancellation and healer survival need a dedicated design; blindly adding an “often” cast is inappropriate.
- **Divine Plea:** the existing healer-role exclusion remains deliberate because the native spell penalizes healing. A safe downtime/cancel policy is not implemented. Other mana recovery stays available.
- **Holy Nova:** remains associated with offensive/AoE utility, not a newly enabled default healing spam spell. Its damage component matters for CC and healer-DPS expectations.
- **Aura Mastery:** the new automatic policy is specifically Concentration Aura under healing pressure. Optimized resistance-aura cooldown planning is not added.
- **Passive talents and glyph effects:** native core procs are not extra AI buttons. Tidal Waves, Ancestral Awakening, Earthliving, Divine Aegis, Grace, Serendipity, Beacon transfer, Sacred Shield interaction, Living Seed, haste/mana modifiers and applicable glyph effects continue to use native spell handling. This audit does not rewrite or independently certify those core mechanics.
- **Spell-combination optimization:** native Riptide/Chain Heal consumption, Nourish/HoT bonuses, Swiftmend requirements and similar interactions are respected. Optimal Chain Heal primary-target selection, raid-wide HoT allocation, mana forecasting and every glyph-dependent sequence are not fully modeled. No claim of an optimal player rotation is made.
- **Pet, subgroup, map and encounter behavior:** native range, subgroup caps and spell targeting still decide the actual effect. The audit does not certify every dungeon/raid/PvP encounter or every possible party composition. Boss scripts, boss data and encounter mechanics are unchanged.

## Settings, delays and observations

`offdps` is the bot strategy key behind healer damage behavior. Attack/assist actions already honor healer role plus `offdps`; Priest and Druid have specific off-DPS spell strategies. It is not a universal ban on every ability with a damage component: mana-recovery pets, Purge/interrupts, support judgements, reactive buffs and explicitly configured totems have separate purposes. An addon display is not proof of the live strategy list. A mismatched noncombat spec can also change maintenance behavior between fights.

The generic combat command to remove healer DPS is `co -offdps`; `co ?` and `nc ?` query their respective active lists. No character strategy, talent allocation or addon setting is changed by this release. Presets must resolve to the intended healing spec in the relevant state, and buff/boost/AoE/cure/potions settings must be enabled for those optional suites.

Source review followed cast prerequisites and movement-to-patient actions, native cast duration/GCD, unavailable-action alternatives, healing priority versus ordinary buffs/consumables, target safety, incoming-heal selection and interruption rechecks. Range, line of sight, silence/stun, mana shortage, cooldowns, disabled strategies or an absent learned spell can still legitimately delay a cast. Source checks cannot measure actual reaction latency on a loaded live realm.

## Validation and attribution

- Controlled regressions compile the new support-action implementation for all three expansion defines and exercise assignment preservation, invalid recipients, learned/talent/cooldown gates, emergency prerequisite order, Binding Heal's two-patient condition and mana-channel safety.
- A separate C++ test compiles the actual strategy initialization/inheritance paths in all 90 combinations described above and checks expansion registration, new routing and the weapon fallback.
- Related regressions cover shared healing/HoT safety, heal selection and incoming casts, interruption rechecks, wound/absorb handling, Fade, consumable recovery/timing, rank refresh and action alternatives. The heal-selection fixture was stale after the earlier PvP change that restored the full heal range; its expected 25-yard rejection was replaced with explicit accepted 25/40-yard and rejected 41-yard boundaries.
- Native class/talent definitions were read from each expansion's own Spell.dbc/Talent.dbc and matching core DBC structures. Wrath Penance's friendly healing channel was checked in the CMaNGOS SpellEffects implementation. No Trinity/AzerothCore encounter mechanics were imported.
- Missing routes were present in the pre-patch source. This audit does not attribute every historical omission to a particular upstream author or previous local audit. It does not establish that every reported live hesitation shares the same cause.
- Native compilation/linking and packaged EXE/PDB revision checks are release requirements. **No new dev-world startup test or live healer-combat test is claimed**; dev startup was explicitly omitted for this release. Actual casts, movement under load, native proc/glyph behavior and real group outcomes remain runtime-unverified.
- No database or configuration migration. Core changes only advance the shared playerbots source revision. Deploy world executable plus matching symbols; restart world servers to load the new code.
