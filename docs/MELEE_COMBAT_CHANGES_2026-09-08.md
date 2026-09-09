# Melee combat corrections — 8 September 2026

This source change addresses the 16 spell-coverage finding groups and eight follow-up sequence finding groups. Native CMaNGOS spell, talent, resource and encounter rules remain authoritative. No boss scripts or database content changed.

## Behavior changes

- **Warrior:** TBC Fury schedules learned Sweeping Strikes. Fury promotes Whirlwind for two-target AoE, with native eight-yard action eligibility; nearby melee counts are distinct from ranged clusters. Stance-dependent continuations outrank routine stance restoration while remaining below interrupts/emergencies. Planning accounts for the native retained rage after changing stance. Wrath Heroic Fury has root-break/Intercept-reset use. Area damage receives area-threat classification.
- **Rogue:** Combat boosts run in combat in all expansions. Wrath Fan of Knives has a registered AoE action. TBC/Wrath Shiv uses off-hand utility poison opportunities; Deadly Throw requires points on the selected out-of-melee target. Wrath Shadow Dance requires a melee opportunity and energy, and its opener decision uses native eligibility while the aura is active. CC and boost strategy switches remain relevant.
- **Feral:** Wrath cat/bear can use learned Berserk under their boost strategy, with form/resource/opportunity checks. TBC/Wrath Maim uses combo points for an actual cast interruption. Optional Classic/TBC powershifting requires Furor; the obsolete energy-grant powershift is disabled in Wrath, whose Furor preserves energy instead.
- **Enhancement:** TBC/Wrath Shamanistic Rage has combat mana-recovery use. Wrath Lava Lash is independently scheduled; Maelstrom Lightning Bolt requires five stacks of native proc 53817 and rechecks before execution. Earth Shock damage no longer requires other shocks to disappear. Classic/TBC use Fire Nova Totem; Wrath uses Fire Nova from its existing fire totem. Pending Nova, manual fire-totem selection and important fire buffs/summons are protected from automatic replacement.
- **Retribution/Paladin:** Wrath damaging judgements can repeat after debuffs are present, while covering a missing Light debuff. Freedom resolves to the native expansion name. Corruption is recognized and serves as the learned faction alternative to Vengeance. Automatic low-mana seal recovery remembers its replaced seal and returns after mana reaches 60%; manual changes/recasts cancel that ownership.
- **Death Knight:** Empower Rune Weapon resolves the registered action. Useful Pestilence spreading outranks individual off-target applications and checks protected CC. Native eligible Gargoyle, Dancing Rune Weapon, Deathchill and Unbreakable Armor have spec routes. Hysteria is conservatively self-only, healthy, non-tank boost use; Lichborne addresses fear/charm/confusion, including controlled action eligibility.
- **Shared decisions:** melee target counting uses a self-centred 3D/LOS check and preserves group CC marks and breakable CC. Ranged cluster selection is unchanged. Spell failure entries can release their retry delay when readiness changes; the bounded cache and explicit-player-command exemption remain. Optional threat restraint does not suppress a tank's area threat generation.

## Validation and release state

`python -B tests/melee_source_wiring.py` passes all three expansion branches. This verifies routes, registration links, expansion guards and the presence of decision safeguards. It is **source inspection**, not runtime combat testing.

Existing retained-rage and explicit-command retry fixtures were updated, but their C++ binaries have **not** been compiled or run for this change. An initial native syntax-check setup could not find the configured Boost include path; it did not establish successful compilation. The subsequent instruction placed all builds on hold. No full realm build, server start, database write or deployment was performed.

Before release, compile against all three native cores and run focused cases for stance transitions with/without retained rage; repeated attacks after range/resource recovery; one/two/three/five targets and protected CC; unavailable talents/off-hand weapons/ammunition; Maelstrom proc acquisition/loss; Shadow Dance facing/weapon/energy changes; Fire Nova placement/detonation/replacement; manual and automatic seal changes; and disease spreading with missing/owned auras and rune pressure.

## Deliberate limits

- These are functional policies, not a promise of optimal DPS or perfect cooldown alignment.
- Maim is an interrupt policy, not a general damage finisher. Shiv does not indiscriminately replace damage builders. Shadow Dance does not invent a lasting stealth state.
- Hysteria is not automatically applied to another player. Lichborne self-healing combinations are not introduced here.
- Chain Lightning spending of Maelstrom, optional bleed-refresh/ownership tuning, Tiger's Fury energy optimization, DK Rime policy and every terrain/navigation edge case remain outside confirmed corrections in this change.
- No runtime claim is made for every dungeon, raid or PvP encounter. Hunter, ranged and caster coverage is a separate review.
