# Playerbot class behavior audit — 5 September 2026

This is the second development candidate on `playerbot-behavior-enhancements`, built on the first behavior release. Production and ManTech master branches are not deployment targets for this candidate. No database migration or new configuration setting is required for these class fixes.

## Approach and limits

Reviewed class action names/registrations, selected strategy prerequisites and triggers, direct cast paths, shared spell capability checks, and each expansion's local Spell.dbc. All ten class directories were included in the literal spell/action inventory; death knights are relevant only to Wrath. Missing literal names are leads, not automatically defects: aliases, synthetic actions, and expansion-specific spells are legitimate.

Fixes reuse existing Playerbot spell actions and core validation. No dungeon-name exceptions, forced success results, new movement/teleport system, or global suppression of spell errors were added. This is not proof that every rotation, encounter, talent combination or command is correct; those need runtime testing.

## Confirmed corrections

| Area | Before | Now / existing mechanism used | Versions |
|---|---|---|---|
| Learned spell IDs | An action retained its construction-time spell ID, including zero, after its cached resolver could discover a learned or changed rank. | Re-read the existing timed `spell id` value during evaluation/execution; preserve alternate contexts such as vehicle spells. This is not a new cache or immediate cache invalidation. | All |
| Cooldown boost triggers | Could repeatedly nominate an unavailable racial/class boost. | Require a resolved, known spell and the core's `IsSpellReady`, preserving existing combat/balance policy. | All |
| Expansion racials | Mana Tap was registered in Wrath; active Perception was registered there despite the expansion change. | Mana Tap trigger only in TBC; active Perception only in Classic/TBC. Arcane Torrent retained. | Expansion-specific |
| Mana Tap | Mana-bearing target alone could activate it while the cast was invalid. | Existing `CanCastSpell` checks eligibility before nomination. | TBC |
| Will of the Forsaken | Consecutive returns made only the fear check reachable; the dead checks also included overly broad effects. | Read the expansion spell's immunity effects and use core aura mechanic masks, plus learned/cooldown checks. Handles applicable fear/charm/sleep, not every stun. | All |
| Hunter ammunition | Skipped backpack ammo, could choose unusable ammo, and directly changed the ammo field. | Scan backpack and equipped bags; match arrow/bullet to weapon, filter with `CanUseAmmo`, apply with `SetAmmo`. Unsupported ranged weapon types rejected. | All |
| Mage mana gems | Guessed spell IDs from level across expansion boundaries; ID could remain uninitialized. | Resolve actually learned gem spells, with Classic/TBC names and Wrath's shared rank name; validate even on direct execution. | All |
| Rogue Shadowstep | Forced triggered cast bypassed ordinary checks and interpreted a result enum as a boolean. | Standard `CastSpellAction` validation and execution. No Shadowstep introduced into Classic. | TBC/Wrath |
| Rogue Stealth | Reported success even when the cast failed. | Report failure; change stealth strategies only after the existing cast succeeds. | All |
| Druid Barkskin | Action tried to resolve `barskin`. | Resolve `barkskin`; retain the old command alias for compatibility. | All |
| Paladin emergency fallback | Registered `repentance of shield`, while strategies requested `repentance or shield`. | Correct the ActionNode key so the existing fallback can be found. No new emergency rotation. | All |
| DK spell names | Misspellings/noncanonical names prevented resolution of several actions. | Correct Scourge Strike, Death Coil, Anti-Magic Shell/Zone and Dancing Rune Weapon; correct Heart Strike action reference and add canonical Unholy Presence alias. | Wrath |
| DK targets | Taunt/offensive summons used a self-buff action; Ghoul Frenzy targeted self; magic defenses used a melee target. | Existing enemy, self-buff and pet-target action mechanisms, checked against Wrath spell targets. Dark Command doesn't force Blood Presence and avoids taunting a victim already attacking the bot. | Wrath |
| DK passive | Improved Icy Talons was scheduled as an active buff cast. | Remove the active trigger; the core still handles the passive/proc. | Wrath |
| DK runeforging | Invalid link/unlearned or unresolved spell could report an error and continue. | Return failure before casting; require an equipped main-hand weapon. | Wrath |
| DK build boundary | DK source files were compiled in older builds even though factory creation was guarded. | Exclude DK implementation compilation outside the Wrath CMake project. This does not mean Classic/TBC previously spawned DKs. | All builds |

## Classes without new class-specific patches

Warrior, priest, shaman and warlock were included in the inventory and selected trigger/action review. No additional confirmed class-specific fix is claimed for those four in this candidate. They receive relevant shared spell/trigger corrections. The prior behavior release's melee-spacing fix remains included; this candidate does not rewrite their rotations.

## Log evidence and unresolved items

The local development logs inspected were from 4 September, before this candidate. Their diagnostics report top failure buckets per interval, not a complete census of every attempt. Examples included TBC Mana Tap (471,796 reported failures), Blood Fury (333,855), and Berserking (314,923); Wrath Mana Tap (60,931), Bone Shield (51,002), and Dark Command (33,005). These counts identify audit priorities; ordinary cooldown/resource/target failures can also be expected and are not all bugs.

The sampled production Wrath Server.log tail contained repeated `CastSpell: unknown spell id 0` records for Verice. A read-only character lookup identified a level-67 warlock. The diagnostic lacks the originating call stack/action. The checked direct quest-source casts already guard zero and trainer casts already validate the spell entry. **The source of this specific error remains unresolved; none of the above fixes is asserted to solve it.** Preserve this error reporting for subsequent attribution.

A historical TBC message referencing spell 19465 and missing target coordinates also remains unattributed. Do not turn these messages off or delete spell data to make the log clean.

## Verification and runtime test checklist

`tests/class_behavior_regression.py` compiles extracted production decision bodies with controlled core interfaces. Covers usable ammo/backpack/bags, core setter rejection, all three mana-gem variants, changed learned ranks, alternate spell resolver contexts, racial mechanic/cooldown gates, boost gates and rogue Stealth success/failure. Source contracts cover corrected class names/targets. These tests complement, not replace, the full realm builds or gameplay tests.

`tests/class_spell_inventory.py` performs the repeatable read-only literal-name scan against each development realm's DBC. It deliberately reports aliases and out-of-expansion literals for review, not automatic removal.

Test each expansion separately:

1. Invite melee and caster bots; confirm attacking/following, ordinary cooldowns and role changes remain functional.
2. Hunter: arrows versus bullets, ammo in backpack and bags, and an unusable higher-level stack alongside usable ammo.
3. Mage: no learned gem spell, first learned gem and upgraded rank. Classic must not attempt emerald/Wrath gems; TBC must not attempt Wrath ranks.
4. Rogue: Stealth success/failure and Shadowstep with valid/invalid target, range and cooldown in TBC/Wrath.
5. Druid: Barkskin when available; paladin: existing emergency fallback under an appropriate low-health test.
6. Blood elf in TBC: Mana Tap only when castable. Wrath: no Mana Tap nomination. Undead: eligible fear/charm/sleep and cooldown; unrelated stun must not cause this racial attempt.
7. Wrath DK: enemy taunt, ghoul buff, offensive summons, defensive shell/zone, valid and invalid runeforge requests. Test learned talents only; no new talents granted.
8. Train/respec a bot without rebuilding its AI object; confirm the existing resolver's refresh allows the learned action and rejects removed capabilities.
9. Recheck diagnostics under gameplay. Record spell ID, bot class/level, action and target when possible. A lower log count alone is not a gameplay correctness test.

Do not infer an overall CPU/RAM percentage improvement from compilation or these tests. Reduced impossible-action work is the expected benefit; quantify it only with comparable runtime samples.
