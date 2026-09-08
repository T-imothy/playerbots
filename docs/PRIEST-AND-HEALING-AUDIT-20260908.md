# Priest and cross-class healing review — 8 September 2026

This release follows the warrior/pull repair release. It includes confirmed priest defects and a healing integration review for priests, druids, shamans and paladins. The separate dungeon/raid encounter audit remains paused and excluded.

## Changes

| Fix | Classic | TBC | Wrath |
| --- | --- | --- | --- |
| Prioritize critically injured and low-health patients before ordinary missing-HP totals | Yes | Yes | Yes |
| Distribute multiple healers within the most urgent health band, rather than assigning a healer to a healthier tank while an urgent patient waits | Yes | Yes | Yes |
| Keep critically injured players eligible even when another healing cast is in progress | Yes | Yes | Yes |
| Keep urgent heals available under optional Low Threat behavior | Yes | Yes | Yes |
| Allow an urgent Regrowth direct heal despite an existing Regrowth HoT | Yes | Yes | Yes |
| Allow an urgent Riptide direct heal despite an existing Riptide HoT | Not available | Not available | Yes |
| Prefer an available Swiftmend over a Regrowth cast for a critical patient, retaining Regrowth/Healing Touch fallbacks | Yes | Yes | Yes |
| Put Lifebloom through shared healing restrictions while retaining stack/expiry-based refreshes | Not available | Yes | Yes |
| Route the paladin's low-health Holy Shock to itself, retaining the separate offensive action | Yes | Yes | Yes |
| Aim Tranquility at the caster, matching its native area/channel targeting | Yes | Yes | Yes |
| Exclude offline, dead, teleporting, other-map/instance/phase, hostile and fully healing-blocked patients from the group-heal count | Yes | Yes | Yes, preserving valid precast windows |
| Require actual priest threat before using Fade; restore shared buff/capability checks | Yes | Yes | Yes |
| Restore shared spell checks in Mana Burn and Starshards overrides | Yes | Yes | Yes, if the spell is actually learned/available |
| Aim Shadowfiend at the enemy used by the native summon attack script | Not available | Yes | Yes |
| Fix the spell name for secondary-target Vampiric Touch | Not available | Yes | Yes |
| Treat Vampiric Embrace as a self buff | Retain enemy debuff | Retain enemy debuff | Yes |
| Use healing action checks for Prayer of Healing | Native caster-group target | Native caster-group target | Injured party target, following native subgroup targeting |
| Complete missing Shadowform-removal prerequisites for Holy healing abilities | Prayer of Healing and existing Holy fallback routes | Also Binding Heal, Prayer of Mending, Circle of Healing and Lightwell | Same, plus Divine Hymn |

Shared healing-selection and urgent-heal threat handling also benefit other healer classes. Native cast times, mana, cooldowns, range, line of sight, threat amounts and encounter restrictions remain in force. Healing need still includes encounter healing absorbs and pre-heal forecasts; urgency comes first.

## What caused the reported behavior

Verollo's saved combat strategies contain `offdps` and `offdps raid`; his saved noncombat strategies do not. The installed addon computes its card state by requiring every requested context to be enabled. A single bot with combat enabled and noncombat disabled therefore appears OFF. That can explain Holy Fire and Shadow Word: Pain despite the displayed state. The user is handling the addon; this release does not edit it or silently change Verollo's saved strategies.

Fade is scheduled by the priest raid strategy independently of the optional Low Threat strategy. The relative-threat value deliberately reports high threat when an enemy is in combat and the tank has none yet. That is useful for holding damage back, but the old Fade action accepted it without requiring the priest to have any actual threat. The fix removes that false opening-pull opportunity. Fade remains available for real threat; it is not globally disabled.

The healing selector ranked ordinary patients by raw missing HP, and assigned healers by index across the entire candidate list. A larger, healthier tank could win that ranking, or the second healer could receive a much less urgent candidate. The updated selection applies health urgency before missing-HP ranking and distributes healers within that urgency band.

The Shadowfiend target and Fade override date to 2021; the secondary Vampiric Touch name dates to 2024. The index-based healer assignment also predates the recent audit. Recent healing-objective changes preserved the missing-HP behavior; they did not fully address low-health prioritization. These findings do not establish the exact cause of every observed pause.

The paladin's enemy-targeted Holy Shock wrapper dates to April 2022 and its self-health trigger to August 2023. The generic existing-aura suppression dates to December 2022; Lifebloom's separate spell action dates to October 2023. These specific defects predate the recent enhancement audit. The group-heal count's latest distance edit was in July 2026; that edit is not evidence that it introduced the missing lifecycle checks.

The earlier healing tests checked invalid targets, incoming casts, pets, encounter healing windows and healing objectives, but did not adequately test urgency across unequal health pools or each class's trigger-to-spell targeting. One regression test explicitly preserved distribution away from the only critical patient. That was a coverage failure; the new tests correct that expectation and exercise these missed cases.

## Coverage and verification

Reviewed all priest strategy/action/trigger/context files: Holy, Discipline and Shadow; combat/noncombat and PvE/PvP/raid variants; optional DPS/off-healing, buffs, cures, crowd control, protective spells, mana tools, spell identity, target selection, Shadowform prerequisites and shared healing/threat policy. Compared the relevant native spell definitions in all three world databases and the native summon script.

Expanded the review through Restoration druid, Restoration shaman and Holy paladin combat/noncombat healing triggers, action registration, self/party targeting, fallback routes and class restrictions. Druid Regrowth, Rejuvenation, Swiftmend, Healing Touch, Tranquility, Lifebloom and Wrath Nourish/Wild Growth were checked; shaman Healing Wave, Lesser Healing Wave, Chain Heal and Riptide; paladin Holy Light, Flash of Light, Holy Shock, Lay on Hands and protective/mana actions. Native databases confirmed the relevant effect and target differences. Existing shaman cast-time priorities were not retuned without gameplay evidence. The unused automated-healing alias `divine protection on party` is not referenced by healer strategies and is outside these automatic healing routes; Divine Protection itself remains a self-only native spell.

Focused regression tests exercise actual production selection, Fade and threat methods, including low-health cloth wearer versus higher-health tank, multiple healers, another pending heal, zero-threat Fade, and urgent healing under Low Threat. Existing healing-window, full-health-wound, heal-interrupt, corrupted-healing, proc-identity and related-action-dispatch tests also pass. Native build/deployment verification is recorded in the release receipts.

The cross-healer fixture compiles actual shared admission/counting methods and class action definitions in all three expansion modes. It checks direct-heal-plus-HoT rescue, redundant pure-HoT suppression, base safety failures, healing immunities, Lifebloom refresh admission, Holy Shock/Tranquility targeting and group lifecycle/range filters. Native cooldowns, mana costs and cast success remain enforced by the core. Group-heal counting remains a nearby-patient heuristic, not a complete spell-specific clustering optimizer; this review does not claim optimal target geometry for every group spell.

The live console endpoint timed out, so no live Verollo action trace was obtained. The saved settings are confirmed; exact runtime pauses and post-restart behavior still require observation. This completes the stated priest and cross-class healing source review, not every encounter audit or live timing scenario. No percentage improvement or guarantee of bug-free play is asserted.

## Deployment

Only `mangosd.exe` and its matching `mangosd.pdb` change on each realm share, with rollback backups. No database migration, configuration change, addon modification or automatic realm restart is included. Previous warrior/pull and production-log fixes are retained.
