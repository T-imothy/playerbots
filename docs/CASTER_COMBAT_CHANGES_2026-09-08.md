# Caster combat changes — 8 September 2026

Source changes for Classic, TBC and Wrath. **Not compiled, deployed or gameplay-tested.** The build hold remains in effect. Native spell mechanics and boss scripts are unchanged.

## Shared corrections

- Personal damage-over-time triggers and secondary-target selection recognize the bot's own copy instead of suppressing it because another caster applied the spell. Shared debuffs, curses and existing expansion debuff limits retain separate handling.
- Legal filler fallbacks cover unavailable talent/level spells and unusable normal fillers. Destruction has an explicit Incinerate → Shadow Bolt alternative; shadow has a Mind Flay → wand alternative, with additional learned filler selection.
- Caster area attacks use AoE threat classification and check the selected destination or affected neighborhood for protected CC and ineligible enemies. Chain Lightning checks potential bounce neighborhoods. Cone checks deliberately use a conservative surrounding radius. Self-centered bursts use native spell range instead of melee weapon reach.
- Caster damage actions avoid marked or damage-breakable CC. Dragon's Breath/Blast Wave no longer force a Flamestrike follow-up. New Hex/Cyclone control checks diminishing-return immunity and stops the bot/pet's attacks on the controlled target.
- Shadow Word: Death has a conservative owner-health guard. Health Funnel/Hellfire require healthy, unpressured owners, with reaction actions to stop unsafe channels.

## Mage

- Cold Snap resolves learned frost cooldowns by name, fixing Classic's mismatched later-expansion IDs.
- Wrath Arcane Power/Presence of Mind automation belongs to boost settings rather than ordinary buffs. Later expansions have a Presence of Mind consumption route using a legal learned cast-time spell.
- TBC/Wrath Slow supports PvP pursuit control. Wrath Arcane Barrage handles movement and missing/unavailable Arcane Blast, while Focus Magic selects an eligible nearby ally outside combat and preserves an existing partner.
- Real mana gems are selected strongest first. Existing armor and Brain Freeze spell alternatives remain.

## Warlock

- Wrath Conflagrate recognizes its non-consuming glyph. Affliction Drain Soul execute use is independent of shard count, bag space and item cheats; Classic/TBC retain shard-farming behavior.
- Dark Pact precedes Life Tap when the owner needs mana and a living pet has a reserve to transfer. Empty-pet casts cannot continually outrank Life Tap.
- Pet strategy adds guarded Health Funnel, Fel Domination and accelerated recovery of a missing/dead demon. Existing manual pet selections take precedence.
- Wrath demonology reacts to active Molten Core/Decimation proc IDs with Incinerate/Soul Fire, supports Demonic Empowerment, and uses appropriate Metamorphosis abilities under combat/AoE/PvP gates.
- Hellfire requires a safe nearby pack and high owner health. Wrath Shadowflame stays local. Demonic Circle placement/escape is PvP-only, uses the actual owned circle, checks destination separation/safety and excludes flag carriers. Demon Charge is restricted to nearby PvP pursuit rather than dungeon charges.

## Shadow priest

- Wrath Mind Sear has an AoE route once learned; Psychic Horror provides guarded PvP defense once talented.
- Personal DoTs and missing-Mind-Flay filler behavior receive the shared corrections. Existing emergency healing and Shadowfiend/Dispersion support remain.

## Balance druid

- TBC/Wrath Force of Nature is a boost ability with destination checks; Cyclone supports designated CC and defensive PvP use. Wrath Typhoon is defensive PvP-only to preserve dungeon positioning.
- Personal DoTs, safe caster fillers and Starfall/Hurricane area handling receive shared corrections. Eclipse behavior and Classic raid DoT exclusions remain.

## Elemental shaman

- Elemental Mastery is used when learned and boost is enabled. Later expansions prefer Wrath of Air while preserving explicit air-totem choices; Classic still uses its available alternatives.
- Wrath Thunderstorm uses a self target for mana/defense. It avoids PvE knockback near enemies unless the no-knockback glyph is present. Hex supports designated CC and guarded PvP defense.
- TBC/Wrath elemental summons are conservative: Fire Elemental requires a safe nearby pack and an empty fire slot; Earth Elemental is restricted to solo emergencies with an empty earth slot. Existing totems and explicit fire choices are preserved.

## Retained restrictions and validation limits

- Blizzard's existing ten-second delay, movement settling before independent-bot casts, Classic raid debuff restrictions, and commented-out Firestone/Spellstone automation were deliberately retained. General portals/rituals/remote vision and Mind Control are outside these combat changes.
- The checks verify expansion exclusions, trigger/action wiring, existing regression expectations and key source invariants. They do not establish C++ compile success, actual talent/gear setup, measured performance, PvP balance or live combat correctness.
- AoE checks examine cached nearby units at decision/cast time. They cannot guarantee the future position of enemies when a delayed explosion lands. Conservative cone/chain checks may decline casts near protected targets.
- No database migration or configuration line is introduced. No core submodule pointers, production files or running processes were changed during this source-only release.

Validation: `tests/caster_source_wiring.py`, existing melee/hunter source checks, and `git diff --check`. Compilation and runtime scenarios must accompany the later binary release.
