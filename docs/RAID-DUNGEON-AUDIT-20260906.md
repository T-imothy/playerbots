# Raid and dungeon audit: verified fixes and mechanic backlog

This continues audit areas 3–5 on `playerbot-behavior-enhancements`. The source
fixes below have targeted regression coverage. The accompanying task report
records final native builds and exact commits. No encounter clears, success
percentage, complete raid strategy, or production deployment are established by
these tests. Areas 3–5 remain open at the full mechanic-by-mechanic level.

## Fixed behavior

Subsequent continuation fixes add [Mandokir threat and Anzu casting holds](ENCOUNTER-CAST-HOLDS-20260906.md)
and [boss-owned add priorities](DUNGEON-ADD-PRIORITY-20260906.md) for Steamrigger,
Freywinn, Anzu and Anomalus. Keli'dan/Dalliah warning handling, Ymiron/Devourer
damage pauses and cast lifetime safeguards are recorded in
[the combat continuation](DAMAGE-PAUSE-CAST-LIFETIME-20260906.md).
The register below describes full encounters; these specific fixes do not close
their remaining group assignments or live gameplay validation.

[The Anzu/Vorpil continuation](ANZU-VORPIL-AUDIT-20260906.md) corrects native
Anzu brood thresholds and bird pulse initialization in TBC/Wrath, and adds DPS
priority for Vorpil's travelers using their exact two-level summon ownership.

| Finding | Change | Expansion scope | Regression |
| --- | --- | --- | --- |
| A cast already underway could complete after its target gained a reflect shield | Dungeon combat/reaction hooks recheck the current generic spell and cancel only a native-reflectable hostile cast facing at least 50% school-specific reflection. Execution rechecks the shield and cast; launched spells, channels, friendly casts and uninterruptible casts are preserved. | All three | `reflected_cast_reaction_regression.py` |
| Ordinary cleansing could remove Hakkar's required Poisonous Blood | While a live Hakkar is engaged in map 309, automatic poison cleansing preserves aura 24321. New continuing poison-cleansing effects/totems are withheld during the fight. Direct cleansing of unaffected players and non-poison cleanses remain available. | All three, with era-specific totem IDs | `encounter_dispel_regression.py` |
| Sepethrea's flame avoidance used the trail radius during Inferno | Active native Inferno auras 35268/39346 also use damage spell 35283's larger radius. The chased bot retains its additional running buffer. | TBC and Wrath | `mechanar_policy_regression.py` |
| A Mechanar destination could be stale by execution | Recollect current hazards and reject a destination inside their current radii or belonging to a different active boss; keep bounded path checks. Pathaleon's actual victim is excluded from the ranged/healer retreat rule. | TBC and Wrath | `mechanar_policy_regression.py` |
| Encounter holds were missing from reaction multipliers; movement spells bypassed two holds | Register existing MC/BWL/Naxx/Mechanar/Onyxia movement constraints in the reaction engine. Mechanar and exclusive Onyxia holds also reject movement-producing spell actions. Attacks, stationary spells and emergency ground-hazard escape retain their existing exceptions. | All three; existing encounter gates apply | `encounter_movement_arbitration_regression.py` |
| An already-safe bot could continue an old chase; stopping it could cancel a heal | Mechanar and exclusive Onyxia positioning stop an old movement generator at a safe destination. They interrupt a cast only if actual relocation is needed. Nonexclusive Onyxia flank guidance does not force a stationary hold. | All three action bodies; Mechanar activates only in TBC/Wrath | `encounter_safe_hold_regression.py` |
| Thorngrin's Hellfire lacked an explicit escape/hold | Match map 553, entry 17978 and channels 34659/39131; take radii from native damage ticks 34660/39132. | TBC and Wrath | `boss_cast_position_regression.py` |
| Slad'ran's Poison Nova lacked an explicit escape/hold | Match map 604, entry 29304 and casts 55081/59842. Use the native radius; release the hold on cast completion, interruption, reset, phase/map mismatch or invalid path. | Wrath | `boss_cast_position_regression.py` |

The reflection helper supplements the existing pre-cast guard in
`GenericSpellActions.cpp`; it does not change native reflection. Hakkar's native
`BloodSiphon::OnEffectExecute` selects spell 24323 instead of 24322 only if the
player still has aura 24321. This safeguard does not acquire the poison for the
group, route Sons of Hakkar, remove pre-existing cleansing totems, or take over
manual player casts. Native `SpellAuras.cpp` dispatches Sepethrea's Inferno damage
35283 separately from the flame-trail payload chain, which explains the previous
underestimate. Thorngrin and Slad'ran's normal/heroic spell-list assignments were
checked against the local development databases as well as their C++ scripts.

## Area 3: existing partial encounters

The following are remaining mechanic assignments or validation requirements,
not promises made by the new fixes. A named strategy is not a complete fight.

| Encounter group | Current support inspected | Work still required |
| --- | --- | --- |
| Molten Core | Named strategy; add priorities/CC protection; selected tank rules and positional hazards; native reflect guard now also covers an ongoing cast | Full Garr/add assignments, Majordomo shield/CC transitions, Ragnaros submerge/Son recovery, all role/phase combinations and actual raid runs |
| Onyxia | Native breath spell/target-position selection, fireball separation, add targeting, flank guidance; improved hold arbitration | Breath-chain timing and route validation in the real room; tank/knockback recovery and Wrath guards across raid difficulties |
| Blackwing Lair | Selected tank rules, Burning Adrenaline separation, Nefarian corrupted-healing/taunt guards; reaction holds | Razorgore orb/egg roles, suppression-room progression, Firemaw LOS/stack resets, all Chromaggus breath combinations and class-call assignments |
| Karazhan | Selected chain/flare/beam handling, Aran cast escape and Flame Wreath precedence | All Opera variants, Chess interaction, beam rotation/exhaustion and full Maiden/Nightbane/Prince role/phase coverage |
| Mechanar | Polarity, native charges/flames, Pathaleon adds/caster spacing; Inferno and stale-move fixes above | Live normal/heroic route, polarity grouping, threat transitions, chained bridge pulls and recovery |
| Gruul / Maulgar | Shatter spread and existing generic priority/interrupt/taunt behavior | Maulgar council assignments, Krosh shield acquisition, Kiggler/Olm roles, Gruul Hurtful Strike positioning and live Shatter coordination |
| Magtheridon | Cube/channel lifecycle and selected Debris hazards | Five-player cube coordination under fear/Quake, channeler assignments, exhausted-player replacement and phase-three overlap runs |
| Tempest Keep | Solarian bomb/priority handling and Void Reaver Pounding escape | Al'ar platforms/rebirth/Embers, full Kael'thas advisor/weapon/item/phase mechanics, Orb trajectories and native phase spell-list variants |
| Naxxramas | Selected burst separation, Thaddius charge separation, Grobbulus cleansing protection and lifecycle gates | Wing-specific assignments: Four Horsemen rotations, Heigan dance, Loatheb healing windows, Sapphiron ice-block LOS, Kel'Thuzad phases, Thaddius platforms/jumps/grouping; Classic versus Wrath difficulty runs |

## Area 4: wider raid requirements

Native source and spell-data evidence identifies the following mechanics to
implement or validate. These rows are a prioritized gap register, not a claim
that every listed native mechanism was executed in a running server. Generic
healing, interrupts, valid-target selection and dynamic-ground avoidance are
shared services; they do not substitute for group assignments or special items.

| Raid | Concrete mechanics requiring dedicated coverage |
| --- | --- |
| Zul'Gurub | Hakkar poison acquisition/Siphon and aspect handling; Mandokir's native threat-increase check during Threatening Gaze; Thekal/zealot synchronized resurrection; Jeklik healing, Marli spiders, Arlokk marking/vanish and Venoxis poison. The new Hakkar cleanse guard addresses one of these only. |
| AQ20 | Buru eggs/kiting, Ossirian crystal use, Moam resource/add control, Ayamiss airborne/larva phases, Kurinnaxx traps/wounds and Rajaxx wave/event progression |
| AQ40 | Twin Emperors tank roles/teleports/immunities, Viscidus frost/melee/glob phases, C'Thun sweep/stomach/tentacles, Huhuran soaks, Ouro submerge, Bug Trio order and Fankriss/Sartura assignments |
| SSC | Hydross boundary/threat resets; Lurker rotating Spout/submerge; Leotheras individual demons and tank changes; Karathress council/totems; Morogrim graves/murlocs; Vashj cores/generators/strider kiting |
| Hyjal | Event waves and friendly NPC protection; Winterchill Death and Decay, Anetheron infernals/healing reduction, Kaz'rogal mana mark, Azgalor Doom replacement, Archimonde fear/doomfire/Air Burst item handling |
| Black Temple | Naj'entus spine item/shield, Supremus fixation, Akama event, Teron ghosts, Bloodboil assignment, Reliquary phase-specific behavior, Mother attraction, Council shared health and Illidan flight/flames/demon/cage roles |
| Zul'Aman | Akil'zon storm stacking, Nalorakk tank phases, Jan'alai eggs/bombs, Halazzi splits/totems, Malacrass stolen abilities, Zul'jin phase-specific movement/casting rules |
| Sunwell | Kalecgos dual realms, Brutallus Slash/Burn assignments, Felmyst flight/fog, Twins, M'uru/Entropius, Kil'jaeden orb/drake/shield phases |
| Obsidian Sanctum | Tsunami lanes, fissures, drake portals/realm assignment and drake-count variants |
| Eye of Eternity | Sparks, discs, protected ground phase and red-drake abilities/energy in phase three |
| Vault of Archavon | Trace EventAI spell/target rules for Archavon, Emalon, Koralon and Toravon; dedicated add/overcharge/orb/meteor roles. The four empty C++ AddSC files are not evidence that the live bosses have no AI. |
| Ulduar | Leviathan vehicles/overloads; Ignis construct heating/water; Razorscale harpoons; XT heart/bombs; Assembly order/runes; Kologarn arms/eyes; Auriaya stacking; Hodir cold/snow; Thorim arena/gauntlet; Freya waves; Mimiron all phases; Vezax resource restrictions; Yogg sanity/portals; Algalon portals/Big Bang. Existing Mimiron Shock Blast escape covers only one cast. |
| Trial of the Crusader | Beasts tank/bile/toxin/charge mechanics; Jaraxxus portals/Incinerate; Champions CC/target assignments; Twins essence/shield switches; Anub'arak permafrost, pursued target and phase-three healing priorities |
| Icecrown Citadel | Bone spikes/Storm, Deathwhisper adds/phase switch, Gunship vehicles, Saurfang beast control, Festergut spores/tank swaps, Rotface ooze routing, Putricide abomination/oozes, Princes invocation/nuclei/bombs, Blood Queen bite/pact, Valithria healing/portals, Sindragosa tombs/LOS/stack limits, Lich King plague/Defile/Val'kyr/realm transitions |
| Ruby Sanctum | Halion realms/corporeality, cutter geometry, meteor fire and positioned dispels; Baltharus clones, Saviana conflag and Zarithrian adds |
| World bosses | Dedicated behavior not established for Azuregos/Kazzak, the four green dragons, Doom Lord Kazzak or Doomwalker. Need actual native spell/phase analysis, group entry/evade rules and world-space movement validation. |

## Area 5: dungeon review register

The data scan includes every populated dungeon/raid map in each dev Map.dbc and
its static spawn templates, their difficulty links, spell lists and EventAI rows.
Unspawned summons and event-created actors are additionally represented where
the native-script inventory maps their template. This is not an exhaustive
runtime actor inventory. A map-specific behavior can be absent even when every
spell reference resolves. The next table records required encounter work; it
does not mark an entire dungeon cleared because a shared rule applies there.

| Era / dungeon | Audit disposition and remaining cases |
| --- | --- |
| Classic: Ragefire Chasm | DB-driven combat, interrupts, caster pulls and reset/wipe tests |
| Classic: Deadmines | Smite weapon transitions, ship pulls, adds and event progression |
| Classic: Wailing Caverns | DB-driven boss abilities and Disciple escort/event recovery |
| Classic: Shadowfang Keep | Arugal teleport/curse and scripted door/event progression |
| Classic: Blackfathom Deeps | DB-driven boss abilities, altar/wave interactions and water routes |
| Classic: Stockade | DB-driven combat, room pulls and evades |
| Classic: Gnomeregan | Bomb/add priorities, event waves and multi-level routes |
| Classic: Razorfen Kraul | DB-driven abilities, escort/add control and elevation |
| Classic: Scarlet Monastery | Whitemane resurrection, event state and each wing's pulls |
| Classic: Razorfen Downs | DB-driven bosses and gong/event progression |
| Classic: Uldaman | Archaedas activation/guardian waves and doors |
| Classic: Zul'Farrak | Pyramid waves, Gahz'rilla interaction and boss mechanics |
| Classic: Maraudon | Princess movement/knockback, adds and route/height cases |
| Classic: Sunken Temple | DB-driven abilities, shield/event dependencies and platform routes |
| Classic: Blackrock Depths | Arena/seven/bar/doors, Emperor/Moira priorities, Flamelash adds and noncombat objectives |
| Classic: Blackrock Spire | Upper/lower routes, Emberseer activation, Rend/Gyth transitions and add/tank assignments |
| Classic: Dire Maul | Separate East/West/North events, pylons, possession and tribute constraints; DB-only evidence must not be omitted |
| Classic: Scholomance | Gandling room teleports, summoned adds and room/event dependencies |
| Classic: Stratholme | Possession, courtyard/gauntlet waves and event recovery |
| TBC: Ramparts | Gargolmar healers, Omor separation, Nazan/Vazruden fire/flight transitions |
| TBC: Blood Furnace | Broggok event/poison and Keli'dan Burning Nova aura/Vortex; his warning is triggered, so an instant-spell-only cast watcher would be insufficient |
| TBC: Shattered Halls | Nethekurse fissures, Omrogg threat switches, Kargath dance/add waves and timed event |
| TBC: Slave Pens | DB-driven bosses/poisons/totems; Ahune event and frozen-core transition |
| TBC: Underbog | Hungarfen mushrooms, Ghaz'an, Muselek/bear and Black Stalker levitation/charge |
| TBC: Steamvault | Thespia clouds, Steamrigger repair adds, Kalithresh distiller/Rage. Generic reflect handling does not destroy distillers. |
| TBC: Mana-Tombs | Pandemonius Dark Shell now benefits from mid-cast reflection checks; Tavarok/Shaffar/beacons/Yor and difficulty variants still need live coverage |
| TBC: Auchenai Crypts | Shirrak focus fire/casting inhibition and Maladaar souls/avatar |
| TBC: Sethekk Halls | Syth elementals, Ikiss blink/LOS and Anzu spirits/Spell Bomb. Blanket radial escape is not an LOS strategy. |
| TBC: Shadow Labyrinth | Hellmaw, Blackheart charm transitions, Vorpil voidwalkers, Murmur Touch and heroic storm/return positioning; Sonic Boom already has a selected escape |
| TBC: Old Hillsbrad | Thrall escort phases, waves and wipe/restart handling |
| TBC: Black Morass | Portal/Medivh protection, Temporus wounds/reflection and Aeonus tank pressure |
| TBC: Mechanar | New fixes above; complete normal/heroic run remains open |
| TBC: Botanica | Thorngrin Hellfire escape added; Freywinn adds/tree, Laj forms, Warp Splinter saplings and Sarannis remain encounter work |
| TBC: Arcatraz | Zereketh hazards, Dalliah heal/whirlwind, Soccothrates charge and Skyriss/event waves |
| TBC: Magisters' Terrace | Selin crystals, Vexallus add/feedback allocation, Delrissa roles and Kael phoenix/Gravity Lapse |
| Wrath: Utgarde Keep | Frost tomb rescue, duo assignments and Ingvar fake-death/resurrection/roar phases |
| Wrath: Nexus | Telestra clones, Anomalus rifts, Ormorok spikes/reflection, Keristrasza cold/root movement |
| Wrath: Azjol-Nerub | Krik'thir watches/swarm, Hadronox event and Anub'arak submerge/impale |
| Wrath: Ahn'kahet | Nadox guardian, Taldaram rescue/spheres, Jedoga volunteer, Volazj insanity phases and heroic Amanitar mushrooms |
| Wrath: Drak'Tharon Keep | DB/native boss abilities including adds, crystals, flight and transformed-player controls |
| Wrath: Violet Hold | Random boss/event routing, Ichoron globules, Xevozz spheres, and alternate-boss abilities |
| Wrath: Gundrak | Slad'ran normal/heroic Nova escape added; snake-wrap rescue, Colossus phases, Moorabi, Gal'darah and heroic Eck remain |
| Wrath: Halls of Stone | Krystallus/Sjonnir abilities and Tribunal escort/waves; investigate LOS/floor geometry in the live map |
| Wrath: Halls of Lightning | Bjarngrim stances, Volkhan brittle golems, Ionar sparks; Loken Nova escape exists but subsequent Shockwave positioning needs a complete fight test |
| Wrath: Oculus | Drakos/Varos/Urom event progression and Eregos drake abilities/energy; ordinary on-foot path checks do not certify vehicles |
| Wrath: Utgarde Pinnacle | Svala sacrifice, Gortok activation, Skadi harpoons/gauntlet and Ymiron Bane/spirits |
| Wrath: Culling of Stratholme | Escort/timed event, waves and boss-specific DB/native abilities |
| Wrath: Trial of the Champion | Joust controls, champions, Eadric facing/hammer, Paletress memory and Black Knight phases |
| Wrath: Forge of Souls | Bronjahm fragments/Soulstorm, Devourer Mirrored Soul and Wailing Souls |
| Wrath: Pit of Saron | Garfrost LOS/stacks, Ick pursuit/barrage and Tyrannus/Rimefang. Ick Nova escape already exists. Tyrannus' native header flags incomplete Brand logic; inspect payload/proc data before prescribing behavior. |
| Wrath: Halls of Reflection | Falric/Marwyn waves, escort/walls and Lich King pursuit; static-spawn counts alone miss event-created actors |

Later cores also contain earlier-expansion instances. Their mechanics/difficulty
templates must be tested in that core, not inferred from Classic/TBC alone.

## Data findings and evidence limits

No nonempty template ScriptName in the collected static instance creatures was
unresolved by the native name-registration scan. That check does not prove the
native file was compiled, loaded, or selected at runtime.

Nonzero template spell lists with no rows were found in the local dev data:

| Core | Template | SpellList |
| --- | --- | --- |
| TBC and Wrath | Shadowmoon Adept heroic 18615 | 1861401 |
| TBC and Wrath | Coilfang Technician heroic 19891 | 1989101 |
| TBC and Wrath | Ethereal Priest heroic 20257 | 2025701 |
| Wrath | Gothik 16060 | 1606001 |
| Wrath | Hellmaw 18731 | 1873101 |

These are reference findings, not proof that the creature has no abilities:
native C++/EventAI may also cast spells or change the list by phase. No source
attribution to the Playerbots enhancements or production-data diagnosis follows
from a dev-only query. Resolve them against the database repository and native
AI selection before preparing a migration. This pass changes no database rows.

The earlier 101/235/359 inventory counts included declared script names from
source metadata, not exclusively live C++ registrations. In particular Wrath's
four Vault placeholder files must not be called four implemented scripts. The
new `native-registrations.json` distinguishes parsed Name assignments from empty
AddSC functions. File-level constants can belong to multiple bosses or actors;
phase spell-list IDs are not spell IDs; candidate name/ID matches in bot code
are not proof of reachable behavior.

## Required validation before broader completion

Run the targeted mechanics in real normal/heroic and applicable raid difficulties,
including caster/healer/melee/tank roles; zero/multiple bots; death/evade;
teleport/map/phase transitions; incomplete paths and overlapping hazards.
Test Hakkar poison acquisition as well as preservation, and remove/replace
pre-existing cleansing effects manually as appropriate during the test setup.
Test reflection arriving during an active cast and disappearing before a queued
reaction executes. Test Mechanar flames moving into a queued destination and
both safe-point holds while an old chase is active.

The remaining raid assignments are substantial feature work. They are explicitly
open above and cannot be closed by successful compilation or by generic combat
improvements. Release/promotion area 6 stays deferred; ManTech baseline branches
remain unchanged. Training dummies and dual spec are outside this enhancement
audit.
