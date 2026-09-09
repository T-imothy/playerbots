# Hunter combat corrections — 8 September 2026

This batch implements the thirteen source-audit finding groups for Classic, TBC and Wrath. Changes are to Playerbots decisions and shared helpers scoped to hunters. Native boss, spell, item and encounter mechanics are unchanged. No database migration or configuration addition is required.

| Audit group | Implemented behavior |
|---|---|
| H01: pet recovery | A callable dismissed pet now activates Call Pet. Automatic recovery no longer attempts to tame the combat target. Saved-pet death detection checks health and native summonable slots, excludes stable-only pets, and caches the database fallback for five seconds. A present pet's death is checked directly. Existing policy-controlled pet initialization remains. |
| H02: ammunition | Selected projectile, weapon subclass, stock and native usability agree across combat decisions. Spare usable ammo can be equipped in combat; exhausted ammo permits melee fallback and a throttled warning. Item cheats and native no-ammo exceptions remain. |
| H03: missing Arcane Shot | Arcane Shot has its own route in every expansion. Wrath avoids spending Explosive Shot's shared cooldown/Lock and Load charges. Signature shots retain priority over the filler. |
| H04: range/transitions | Minimum/maximum shot range comes from the native target-aware calculation. Melee/ranged switching has a margin, and hunter spacing handles the actual minimum range. Aimed Shot uses the learned rank/native readiness; Classic/TBC retain long-cast caution while Wrath removes that old restriction. Native validation replaces the caster-only ranged eligibility estimate for hunters. |
| H05: Scatter Shot target | Defensive Scatter Shot uses the dedicated pursuer target. Successful Scatter/Wyvern control stops the hunter's attack on that target and recalls a pet attacking it. Hunter damaging spell decisions reject damage-breakable CC. |
| H06: Viper mana recovery | TBC enters Viper below 30% mana and leaves at 70%; Wrath enters below 20% and leaves at 60%. Different thresholds and hysteresis reflect the different native behavior. Explicit manual aspect strategies take precedence; Classic gets no Viper route. |
| H07: stings | Raid sting strategies inherit Serpent coverage. Default PvE uses Serpent rather than draining every mana-bearing monster. PvP/manual Viper uses a percent-mana check. Own-sting checks allow preparation for the caster's Chimera interaction; native stacking still decides which effects may coexist. |
| H08: unused learned actions | Mongoose Bite is scheduled with native eligibility. Wyvern Sting receives CC routes in combat and noncombat, with native expansion restrictions. TBC Steady Shot is a filler below Arcane Shot; slow Aimed Shot is a lower-priority fallback. |
| H09: missing utilities | Classic/TBC Disengage uses enemy threat reduction. Wrath Disengage checks native jump parameters, landing/path, distance gained, hazards and nearby unengaged enemies, and respects stay/guard. It requires enabled knockback handling and a nearby player. TBC/Wrath gain a local defensive Snake Trap; Wrath gains group/root-snare Master's Call and Freezing Arrow at explicit CC-target coordinates. These use the existing CC strategy switch. |
| H10: area safety | Multi-Shot and Volley report AoE threat and inspect their planned area for protected/unengaged targets. Damaging traps report damage threat and respect tank-opening waits. Multi-Shot remains eligible against one target if its splash is safe. |
| H11: trap movement | Automatic traps are placed locally rather than walking into melee to plant them. Offensive traps check nearby safety and shared Wrath Black Arrow opportunity, allowing a local AoE trap for multiple enemies. Classic keeps Feign Death until its trap cast starts. |
| H12: Black Arrow | Removed the Wrath snare-target route and its action/trigger registration. Black Arrow remains a damage ability. |
| H13: Dragonhawk | Existing Hawk no longer prevents a learned Dragonhawk upgrade. Automatic mana recovery still takes precedence. |

Additional corrections: Frost/Explosive Trap readiness resolves the current spell rank instead of retaining a constructor-time ID. Rapid Fire/Readiness require a usable shooting opportunity. Wrath Tranquilizing Shot gains a magic-dispel reaction alongside the enrage reaction. Kill Shot, Chimera and Explosive Shot have priority over ordinary fillers.

## Validation and limits

`python -B tests/hunter_source_wiring.py` passed. These source-only checks also run the preceding melee wiring checks, expand all three compile-time branches, and check the new trigger/action registrations, missing-pet routing, ammo repair, CC mapping, raid sting inheritance, area classification, local trap prerequisites and expansion exclusions. Native core signatures and DBC evidence were reviewed. Whitespace checks passed.

**C++ compilation and in-game tests have not been run.** Builds and deployment are intentionally held for the next audit batch. This commit is source-ready for later validation, not a claim of production-tested behavior. Runtime validation must include pet state transitions, gear/ammo changes during combat, all three range models, manual strategies, mana thresholds, CC/pet interaction, Classic trap chains, Wrath leap landings and shared shot/trap cooldowns.

The audit's explicitly unverified or discretionary items are not invented fixes: every pet family/DB autocast rule, Growl/Cower group policy, ongoing Volley interruption, cast timing under load, terrain edge cases and all talent/glyph combinations still require runtime evidence. Pet happiness convenience, optional tracking/scouting/stable utilities and native boss behavior are unchanged. No measured performance or DPS percentage is claimed.
