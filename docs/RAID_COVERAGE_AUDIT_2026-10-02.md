# Raid playerbot audit — 2026-10-02

This is a source/behavior audit and a tested correction batch, **not a claim that all raids can be cleared autonomously**. The all-boss/all-mechanic implementation remains open. Many later encounters still have only shared combat services and need dedicated role/phase controllers. No raid scripts, creature/spell data, class DPS rotations, or live servers were changed by this batch.

## Scope and evidence

The native inventory covers 316 encounter source records: 58 in Classic (7 raid directories), 108 in TBC (16), and 150 in Wrath (23). These are source-file counts, not boss counts: a file can contain a council, Opera variants or helpers. The roster below additionally names database-driven/optional encounters. The Classic/TBC Naxxramas and Onyxia versions are distinct from Wrath's versions.

Live read-only template checks supplemented native scripts. Jin'do and Rajaxx use EventAI; the four Vault bosses also use EventAI despite empty C++ AddSC functions. An empty C++ file therefore does not establish missing server AI. Numeric spell/NPC matches were used to find candidates, never as proof of implemented bot behavior. Source comments such as `SD%Complete` are not playerbot coverage or live validation.

Baseline inputs: playerbots `148dfac7e431ef046b1b556810b72c32136e2524`, Classic `626904b6950ca15375328f9e0afa8e21aff8502c`, TBC `2ad5f290e0bccee9a0690c1b1c6fa5f3bb1c7ae9`, Wrath `c416407060e445d01229ed8cbd971eaf69322c7e`.

## Corrections in this batch

| Scope | Defect and correction | Verification |
|---|---|---|
| All three | Off-target interrupt selection previously considered only positive spells. In raid maps, reachable interruptible harmful casts/channels now qualify after positive casts. Native cast admission prevents selecting an unavailable/out-of-range interrupt. Execution rechecks the cast, including warlock pet Spell Lock. | Actual selector/action bodies compiled and exercised in ZERO/ONE/TWO; per-effect immunity and pet-admission regressions |
| All three, Zul'Gurub | Jin'do's Brain Wash Totem 15112 now outranks Powerful Healing Ward 14987. Exact native owner 11380 and group victim are required. Preserve Delusions 24306 from automatic curse dispels, both at selection and queued execution. | Totem dispatch, owner/role/command/lifecycle rejection tests; real native dispel masks; live summon spell/template checks |
| All three, Naxxramas | Anub'Rekhan Locust Swarm 28785 remains an escape requirement after its cast finishes. Wrath additionally handles 54021. | Native radius/payload and aura checks, expiry/reset and failed-path regression |
| TBC/Wrath, Karazhan | Enfeeble 30843 now warns before Prince's short Shadow Nova 30852 cast. Non-victims also escape Nova itself; the current tank is exempt from Nova alone. | Native cast/aura-owner tests, tank exemption, lifecycle/path gates |
| TBC/Wrath, Black Temple | Prioritize Illidan's native Shadow Demon 23375 while its own Paralysis 41083 affects a living same-group player. Do not require a threat victim: native demon AI stores its own target GUID. | Actual dispatcher tests plus both native Illidan scripts |
| Wrath, Icecrown | Valithria: Skeletons 36791, then Suppressers 37863, then Archmages 37868. Lich King: rescue Val'kyr 36609 actually transporting a same-group player, and ranged target Ice Spheres 36633. | Native summoner/transport checks, ranged/role/phase/expiry tests and live NPC script bindings |

These are normal bot actions. They retain native costs, cooldowns, range, immunity and path checks. No effects or items are fabricated. Explicit player attack/raid-mark commands retain existing targeting precedence. Tanks/healers retain their existing assignments. The Anub escape is radial/path-validated, not a new complete room-specific tank kite route.

## Reading the roster

### Continued mechanic review and implementation

The continuation starts from playerbots `2db61fcbb3e5481e2163d443998fd49daf74db90`. The following are additional implemented decisions, not certification of the entire raids. They were traced against the native encounter scripts in the applicable eras and the live world spell lists were queried read-only. Native raid scripts and databases remain unchanged.

| Encounter | Native evidence and implemented decision | Still requires work / live verification |
|---|---|---|
| Jeklik, all three | `boss_jeklik.cpp` summons Bloodseeker Bats 14965 and unattackable bombers 14750. DPS now prioritize the actual boss-owned bats, preserving normal attackability/CC; bombers are excluded. Shared interrupts cover Great Heal 23954 and Mind Flay 23953 when native spell admission permits. | Flying/rooted bat movement and fire placement in the real room; see data defect below |
| Mar'li, all three | Native entry is **14510**, not Venoxis 14507. Spider eggs are gameobjects, so spider 15041 selection requires an engaged same-group victim near active Mar'li rather than a fabricated boss summoner. Shared harmful-channel interrupts cover Drain Life 24300. | Tank/web/charge recovery; native phase-list defect below prevents claiming normal phase behavior |
| Arlokk, all three | `boss_arlokk.cpp` activates panther triggers 15091. Target their engaged Prowlers 15101, prioritizing the group member with **Arlokk-owned** Mark 24210. Continue during native vanish when the boss has no victim. | Tank positioning, full vanish return and Whirlwind geometry |
| Jin'do, all three | `zulgurubScripts.cpp` casts summon 24308 from Jin'do and applies shade invisibility 24307. A bot with Delusions 24306 targets native-owned shade 14986 only while actually visible. Shared attack admission also rejects a cached shade after the curse expires. Existing control/healing totems retain precedence. | Live shade/teleport recovery and role coverage when cursed players are healers/tanks |
| Hazza'rah, all three | Spell list 1508301 uses 24728; native `SummonNightmareIllusion` additionally casts 24681/24729 from the boss. Prioritize boss-owned Nightmare Illusions 15163. | Sleep removal and live illusion pursuit |
| Gri'lek, all three | Live EventAI uses Avatar 24646 and clears threat. Only the current pursued player retreats during Avatar. The melee-clearance margin uses native combat reach; bounded native paths may exit but cannot cross inward through the pursuer. | Real-room kiting and root-removal timing |
| Big Bad Wolf, TBC/Wrath | Native `RedRidingHoodFixate` uses **30753**, separate from selection 30769 and appearance 30768. Only the actual boss-victim with the boss-owned fixation aura kites. Expiry, target change, reset and failed paths release the movement rule. | Stage walls and fear overlaps; this is local path-based kiting, not a certified perimeter route |
| Romulo / Julianne, TBC/Wrath | `bosses_opera.cpp`: Julianne 17534 summons Romulo 17533; fake death leaves actors alive but unattackable, with a ten-second deadline. DPS balance the active pair, finish Julianne first below 10%, attack the remaining valid actor and recover after native resurrection. Role/command/CC rules remain in force. | Real damage/DoT/pet timing against the deadline; this does not guarantee simultaneous kills at every gear level |
| Valithria, Wrath | Native `HealedBy` completes only on an actual heal to full health; `StartEncounter` marks the friendly boss in combat. Eligible bot healers now select her automatically during an active attempt. One available bot healer is reserved for the raid; native Dream-stack counts favor buffed healers for the boss. Low-health/forecast-danger party members override the objective. Medium-heal triggers continue through 99%, overheal cancellation preserves the finishing heal, and queued heals are rejected after reset/completion. | Dedicated portal/cloud navigation, 10/25 and heroic throughput, and actual full encounter completion |
| Kologarn, Wrath | Native `boss_kologarn.cpp` summons right arm 32934 from boss 32930. Live Stone Grip 62056/63985 target that arm with vehicle control; bot DPS now rescue only while a living group member is actually boarded on that exact arm. Release/despawn/reset immediately removes the target override. | Eyebeam/arm geometry and native release damage threshold in 10/25; tank handoffs and rubble control |
| Hodir, Wrath | `npc_flash_freezeAI` casts 61969/61990 from ice block 32926/32938 onto its own summoner. DPS now break blocks with that exact living prisoner/aura relationship during active group combat. Player rescue precedes friendly NPC rescue. Initial NPC blocks cannot authorize pulling Hodir. | Flash Freeze snowdrift routes, helper buffs and Biting Cold movement; real 10/25 rescue timing |
| Freya, Wrath | Native boss 32906 summons Eonar's Gift 33228, whose AI attempts Lifebinder's Gift every ten seconds. DPS now prioritize the actual boss-owned tree, without requiring a threat victim on the passive summon. | Full wave/cohort logic, Conservator mushrooms, roots and bomb positions; this is not a complete Freya controller |

Shared escape actions also no longer interrupt a cast for a move that native `CanMove()` rejects (roots, fear, stun, etc.). Release of that movement hold permits ordinary class recovery actions. No native speeds, auras, threat, health, damage, resurrection timers or spell costs are changed.

**Separate native encounter defects discovered, not modified:** In all three cores, Mar'li's C++ phase lists are `1450701/1450702`, while the live world databases identify those as Venoxis's lists and Mar'li's as `1451001/1451002`. After transformation/reset she therefore selects the wrong lists. In all three live databases Jeklik's phase-one row labelled “Swoop” uses **24210 (Mark of Arlokk)**, while her native Swoop constant is **23919**. These are raid-script/data changes outside the requested playerbot-only scope; bot code must not pretend they are corrected.

Additional native review: Buru's egg AI casts 19593 and performs the boss-health reduction itself; a safe bot implementation still needs egg preparation, lure geometry and damage holds together. Freya's native three-add check uses **12 seconds** and retains one current GUID per add entry; a generic all-add health-balancing rule is insufficient for overlapping waves. Neither encounter is marked complete by this continuation.

XT-002's `ReceiveAIEvent(AI_EVENT_CUSTOM_B)` enables hard mode when the heart dies. Automatically selecting the exposed heart without a hard-mode policy can therefore make an unintended difficulty choice. This continuation does not add an unconditional heart override. Native vehicle/control and hard-mode policies remain explicit follow-up work.

Every row remains **partial or unverified as a full encounter**. “Shared” means ordinary class targeting, healing, native interrupt admission and recognized ground hazards, not a dedicated strategy or proof that every named mechanic is handled. The right column is open implementation or live verification work; it must not be treated as completed by the correction batch. Shared interrupts are reactive; no raid-wide preassigned interrupt rotation was added. Untargetable/immune boss abilities must be handled by mechanics rather than forced interrupts.

## Molten Core (409; Classic, TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Lucifron | Protector targeting, off-tanks, curse/Doom removal and friendly mind-control dispel | Live add/tank reassignment and dispel load |
| Magmadar | Frenzy removal, Fear Ward, lava-bomb avoidance and ranged spacing | Fear/knockback recovery in actual terrain |
| Gehennas | Add targeting/off-tanks and curse removal; generic ground avoidance | Overlapping Rain of Fire and tank positioning |
| Garr | Banish allocation, free-add targeting and explosion separation | Renewal, simultaneous explosions and tank losses |
| Baron Geddon | Inferno/Armageddon escape, Living Bomb separation and Ignite Mana removal | Bomb paths and overlap with other hazards |
| Shazzrah | Ranged spacing, curse and boss-buff removal | Blink recovery and melee placement |
| Sulfuron | Priest targets, off-tanks and explicit priest-heal interrupts | Priest separation and interrupt fallback after role deaths |
| Golemagg | Boss DPS, Core Rager off-tanks and Magma Splash retreat | Rager separation and tank recovery |
| Majordomo | Healer/elite priorities, polymorph allocation, native reflect checks | Four-add CC-immunity transition and recovery |
| Ragnaros | Submerge/Sons targeting, spacing and Wrath avoidance | Wave-wide tank distribution, knockback/lava paths and re-emerge recovery |

## Onyxia's Lair (249; Classic/TBC level 60, Wrath level 80)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Onyxia | Breath positions, fireball separation, adds and flank guidance | Complete phase transitions, tank knockback recovery and Wrath 10/25 guards |

## Blackwing Lair (469; all three)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Razorgore | Orb-controller election, native possession/egg use, protected boss and defender priorities | Split-room add kiting, controller death/human takeover and full phase transition |
| Vaelastrasz | Burning Adrenaline separation and rear-side melee placement | Tank succession and overlap with movement/casts |
| Broodlord | Blast Wave spacing and rogue suppression support | Room progression and knockback/threat recovery |
| Firemaw | Five-stack LOS reset, healer LOS and elected clean-tank swap | Real pillar geometry, Wing Buffet overlaps and failed-taunt recovery |
| Ebonroc | Shadow of Ebonroc elected tank swap | Live handoff under misses/deaths |
| Flamegor | Explicit Frenzy tranquilizing response | Wing Buffet tank succession and range recovery |
| Chromaggus | Both breath variants, Hourglass Sand and ranked affliction cleansing | Time Lapse backup tank and all breath/affliction combinations |
| Nefarian / Victor Nefarius | Phase immunity, add priorities, Veil cleansing, priest-call safeguards and flank placement | Hunter weapon swaps, remaining class calls and cloak equipment preparation |

## Zul'Gurub (309; all three)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Jeklik | Shared interrupts and native-owned bloodseeker-bat priority | Phase/tank positioning and live flight/fire recovery; native Swoop data issue above |
| Venoxis | Shared native target/ground services | Poison phase positioning and add assignments |
| Marli | Engaged egg-spider priority and shared interrupts | Tank changes, web recovery and native phase-list defect above |
| Thekal / Lor'Khan / Zath | Explicit balanced trio targeting | Live feign/resurrection timing and healer interruption |
| Arlokk | Trigger-owned panther priority and marked-player rescue during vanish | Return positioning and Whirlwind recovery |
| Mandokir | Threatening Gaze threat-generating action pause | Raptor order, charge spacing and tank recovery |
| Jin'do | Control/healing-totem priority, Delusions preservation and visible-shade targeting with expiry rejection | Live shade/teleport recovery |
| Hakkar | Poison acquisition, engaged Son targeting and poison-cleansing suppression | Poison timing for the whole raid and priest-aspect variants |
| Gahz'ranka | Shared native combat services | Summon/event start, knockback and tank recovery |
| Gri'lek | Avatar pursuit escape with native combat-reach/path checks | Live kiting and root removal |
| Hazza'rah | Native-owned Nightmare Illusion priority | Sleep response and live pursuit |
| Renataki | Shared native combat services | Vanish/ambush recovery |
| Wushoolay | Shared native combat services | Lightning positioning and event-specific response |

## Ruins of Ahn'Qiraj (509; all three)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Kurinnaxx | Mortal Wound tank swap and shared ground avoidance | Sand-trap timing and real-room spacing |
| General Rajaxx | Shared native combat/interrupt services; live boss uses EventAI | Wave start/order, commander priorities and friendly-NPC protection |
| Moam | Mana-control action and native-owned fiend priority | Resource timing, banish allocation and split-phase recovery |
| Buru | Shared native combat services | Egg selection, pursuit routing and transition placement |
| Ayamiss | Larva rescue tied to the paralyzed group member | Air-phase ranged assignment and ground-phase tank transition |
| Ossirian | Elected crystal interaction and native crystal positioning | Crystal sequence, tank routing and failed-use recovery |

## Temple of Ahn'Qiraj (531; all three)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Skeram | Shared interrupts and native targeting | Clone assignments, mind control and teleport recovery |
| Bug Trio | Shared combat/dispel services | Chosen kill order, Yauj fear/heal and death-effect handling |
| Sartura | Whirlwind escape using native radius | Add assignments and chase/threat resets |
| Fankriss | Mortal Wound swaps and enraging-spawn targeting | Tunnel/add assignments and tank-death recovery |
| Viscidus | Frost-hit actions, native shatter admission and glob targets | Whole-raid frost/melee transitions and glob distribution |
| Huhuran | Shared dispels/combat services | Poison Volley soaking positions and berserk coordination |
| Twin Emperors | Physical/caster target split and native immunities | Caster-tank assignment, teleport swaps and separation |
| Ouro | Shared native combat/ground services | Burrow routing, emergence tanking and sandblast placement |
| C'Thun | Rotating Dark Glare escape | Opening spacing, tentacle priority, stomach exit/kill assignments and phase-two coordination |

## Naxxramas (533; Classic/TBC original, Wrath 10/25)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Anub'Rekhan | NEW cast warning and sustained Locust Swarm escape, including Wrath 25 spell | Tank kite route, crypt-guard assignments and overlaps |
| Faerlina | Shared interrupts/dispels/ground avoidance | Worshipper control/sacrifice and era-specific frenzy removal |
| Maexxna | Group-member Web Wrap rescue | Spider pickup, Web Spray healing preparation and tank cooldowns |
| Noth | Shared interrupts/dispels/targets | Curse deadline, balcony waves and skeleton assignments |
| Heigan | Native-wave safe-position planner and hold | Real eruption timing, melee approach and dance recovery |
| Loatheb | Wrath healing-window admission/precast | Classic healing rotation, spore allocation and Wrath coordinated healing |
| Razuvious | Shared native combat services | Classic priest mind control versus Wrath crystal/understudy control |
| Gothik | Shared native combat/interrupt services | Living/dead-side roster and wave transitions |
| Four Horsemen | Void-zone avoidance | Four-corner roles, mark rotations and Classic/Wrath boss differences |
| Patchwerk | Shared tank/healing services | Hateful Strike off-tank positioning and health priorities |
| Grobbulus | Injection separation and suppression of unsafe disease cleansing | Tank route, poison-cloud placement and slime pickup |
| Gluth | Low-health chow finishing targets and era-specific tank swap | Dedicated kiting/slow roles before Decimate |
| Thaddius | Opposite-charge separation using native charges | Feugen/Stalagg assignments, platform jumps and fixed charge-group positions |
| Sapphiron | Air warning and native Ice Block LOS cover | Icebolt spacing, breath geometry and curse/heal coordination |
| Kel'Thuzad | Detonate Mana separation and shared interrupts | Phase-one add lanes, Frost Blast spacing, mind-control CC and guardian tanks |

## Karazhan (532; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Attumen / Midnight | Shared native combat services | Horse/rider tank split, merge transition and curse removal |
| Moroes | Shared native combat/CC services | Guest-specific CC/kill order, Garrote management and vanish recovery |
| Maiden of Virtue | Shared native combat/dispel services | Repentance recovery and Holy Fire dispel priority |
| Opera: Oz | Shared native combat services | Roar fear, Strawman fire response, Tito order and Crone cyclone positioning |
| Opera: Big Bad Wolf | Native-fixation pursuit escape | Live stage-wall route and fear overlaps |
| Opera: Romulo and Julianne | Native-pair health balancing and fake-death target changes | Live synchronized finish and damage-over-time/pet overlaps |
| Curator | Native-owned Astral Flare priorities | Evocation timing and raid spacing |
| Shade of Aran | Flame Wreath movement hold and Arcane Explosion escape | Blizzard route, elemental control and planned interrupt schools |
| Terestian Illhoof | Sacrifice-linked Demon Chains rescue | Imp AoE/tank assignments and Kil'rek timing |
| Netherspite | Role-based beam positioning with buff/exhaustion gates | Full beam rotation, replacement after deaths and banish recovery |
| Prince Malchezaar | Infernal avoidance; NEW Enfeeble warning and Shadow Nova escape | Tank kiting against blocked infernal paths and axe phase |
| Nightbane | Shared native combat/ground services | Fear management, landing/air assignments and skeleton pickup |
| Chess | No complete playerbot chess controller found | Native piece control, move/ability selection and event completion |

## Gruul's Lair (565; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| High King Maulgar and council | Shared interrupts and native combat services | Krosh shield/spellsteal, Kiggler ranged tank, Olm pet handling, Blindeye focus and council assignments |
| Gruul | Native Ground Slam/Shatter separation | Hurtful Strike off-tank geometry, cave-in overlaps and late-growth recovery |

## Magtheridon's Lair (544; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Magtheridon and channelers | Cube election/channel lifecycle and debris hazards; shared interrupts | Live five-cube timing, fear/Quake recovery, exhausted replacements and channeler tank distribution |

## Serpentshrine Cavern (548; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Hydross | Shared combat/ground/interrupt services | Boundary-crossing ownership, resistance tank swaps and add assignments |
| The Lurker Below | Rotating Spout escape | Platform/submerge assignments and water/path recovery |
| Leotheras | Bot fights its own Inner Demon | Demon/normal tank roles, whirlwind route and final split |
| Fathom-Lord Karathress | Tidalvess/Karathress Spitfire Totem priority | Council assignments and focused Caribdis interruption |
| Morogrim | Shared native combat services | Murloc tanks, grave rescue/healing and globule route |
| Lady Vashj | Shield-phase add priorities, native core relay and Strider hazards | Live core looting/relay reliability, generator assignments and kiter recovery |

## Tempest Keep (550; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Al'ar | Shared native combat/ground services | Platform tanks, Quills evacuation, Ember control and rebirth transitions |
| Void Reaver | Pounding escape with tank exemption | Arcane Orb predictive movement and knockback tank succession |
| Solarian | Wrath-bomb separation and priest/add priority | Pre-nerf spell-list variant and complete split/void transitions |
| Kael'thas and advisors | Shared native interrupts/ground/target services | Advisor assignments, weapon pickup/equip/use, phoenix/egg priority, shield/Pyroblast and Gravity Lapse |

## Hyjal Summit (534; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Rage Winterchill | Shared interrupts/ground avoidance | Icebolt healing/dispel response, Death and Decay escape validation and wave NPC protection |
| Anetheron | Shared combat/ground services | Infernal separation/tank and Carrion Swarm healing assignments |
| Kaz'rogal | Shared combat services | Low-mana Mark evacuation and mana management |
| Azgalor | Shared combat/ground services | Doom evacuation, replacement tank/healer and Doomguard pickup |
| Archimonde | Doomfire actor hazard and native Tears item action | Air Burst acquisition/landing, fear response and overlapping movement |

## Black Temple (564; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Naj'entus | Spine rescue, actual item use and shield break | Multiple-spine election, item failure and raid-health timing |
| Supremus | Native volcano and molten-flame hazards | Fixation kiting and Hateful Strike role placement |
| Shade of Akama | Shared interrupts/targets | Channeler/sorcerer priority, wave pickup and Akama protection |
| Teron Gorefiend | Shared dispel/combat services | Shadow-of-Death exit positioning and ghost/construct ability controller |
| Gurtogg Bloodboil | Shared native combat services | Bloodboil soaking groups, tank swaps and Fel Rage healing/positioning |
| Reliquary of Souls | Shared interrupts, reflect and healing admission | Phase-specific interrupt/shield rules, Suffering tank rotation and Anger resource/threat handling |
| Mother Shahraz | Fatal Attraction separation | Saber Lash soaking and beam/healing assignments |
| Illidari Council | Shared interrupts, reflection and ground services | Separate council tanks, shield-sensitive heal interrupts and shared-health coordination |
| Illidan | NEW Shadow Demon rescue tied to its actual paralyzed group member | Flame tanks, demon tank, parasitic adds, flight/eye beams and Maiev cage coordination |

## Zul'Aman (568; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Akil'zon | Storm shelter at the native storm target | Lightning separation and shelter recovery under deaths |
| Nalorakk | Bear-phase Mangle-aware tank swap | Surge positioning and clean-tank availability |
| Jan'alai | Native armed fire-bomb avoidance | Hatcher/egg allocation, hatchling AoE and safe bomb pathing |
| Halazzi | Lightning Totem priority | Split-phase lynx tank and regrouping |
| Hex Lord Malacrass | Shared interrupts, dispels and CC | Add-specific assignments and stolen-class ability responses |
| Zul'jin | Vortex and column-of-fire actor hazards | Phase-specific casting stops, Grievous Throw healing and phase-transition positioning |

## Sunwell Plateau (580; TBC, Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Kalecgos / Sathrovarr | Shared native combat services | Two-realm roster/portal rotation and synchronized finish |
| Brutallus | Shared native combat services | Meteor Slash groups, tank swap and Burn isolation |
| Felmyst | Shared native ground/dispels | Encapsulate separation, skeleton pickup and fog/flight lanes |
| Eredar Twins | Shared native combat/dispels | Conflagration exit, tank assignments and touch reset |
| M'uru / Entropius | Shared native targets/interrupts | Portal waves, fiend dispels, tank assignments and phase-two avoidance |
| Kil'jaeden | Shared native targets/healing | Orb/drake control, shields, Darkness timing and reflection assignments |

## Obsidian Sanctum (615; Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Sartharion | Shared native combat/ground services | Flame Tsunami lanes, tank breath positioning and drake-count strategy |
| Tenebron / Shadron / Vesperon | Shared native combat/ground services | Portal rosters, egg/acolyte objectives and realm return |

## Eye of Eternity (616; Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Malygos | Shared native combat services | Spark control, discs, protective bubbles and phase-three drake abilities/energy |

## Vault of Archavon (624; Wrath; EventAI)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Archavon | Shared native combat services | Grab recovery and cloud/rock positioning |
| Emalon | Actual boss-owned Overcharge target and Lightning Nova escape | Tank/add separation and live 10/25 timing |
| Koralon | Shared native ground services | Meteor Fists soaking/tank placement |
| Toravon | Shared native combat services | Frozen Orb priority and Frostbite tank swaps |

## Ulduar (603; Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Flame Leviathan | No complete vehicle-role controller found | Vehicle seat roles, pursuit, pyrite, passenger overload and tower variants |
| Ignis | Shared native combat/ground services | Construct heating/water/shatter, tank route and Slag Pot healing |
| Razorscale | Devouring Flame actor avoidance | Harpoon election, add roles and final-phase tank swaps |
| XT-002 | Shared native combat services | Bomb separation, scrapbot priorities, heart timing and explicit hard-mode choice |
| Assembly of Iron | Shared interrupts/ground services | Chosen kill order, rune positioning and phase-dependent tank/interrupt rules |
| Kologarn | Eye-beam avoidance, difficulty-specific tank swap and actual boarded-player right-arm rescue | Live grip threshold/arm geometry, rubble tank roles and tank recovery |
| Auriaya | Shared native combat services | Sonic Screech stack, pull/tank assignments and defender voids |
| Hodir | Biting Cold movement, Flash Freeze jump suppression and actual ice-prison targeting for players/friendly NPCs | Snowdrift positioning, buff sharing and live rescue timing |
| Thorim | Unbalancing Strike tank swap | Arena/gauntlet groups, traps and Lightning Charge positioning |
| Freya and elders | Shared native combat/interrupt services plus native-owned Eonar's Gift target priority | Trio synchronized deaths, mushroom shelter, roots/bombs and wave-specific roles |
| Mimiron | Leviathan Mk II Shock Blast escape | Mines/rockets/Laser Barrage, magnetic cores and synchronized final parts |
| General Vezax | Shared native interrupts/healing services | Searing Flames rotation, Surge kiting, mana restrictions and Animus choice |
| Yogg-Saron | Shared native targets/interrupts | Sanity, facing, portals/brain group, tentacle priorities and phase transitions |
| Algalon | Phase Punch tank swap | Star/constellation handling, black-hole entry and Big Bang role assignments |

## Trial of the Crusader (649; Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Gormok | Difficulty-aware Impale tank swap | Snobold rescue, fire avoidance and tank recovery |
| Acidmaw / Dreadscale | Shared native dispels/combat | Bile/toxin pairing, worm roles and burrow transitions |
| Icehowl | Shared native combat services | Massive Crash recovery and charge escape |
| Jaraxxus | Attackable portal/volcano priority and shared healing-absorb support | Legion Flame route, Nether Power removal, Incinerate timing and add tanks |
| Faction Champions | Shared PvP-like class combat/interrupts | Coordinated CC and healer focus that accounts for diminishing returns |
| Twin Val'kyr | Shared native targets/interrupts | Essence/orb handling, shield target swaps and vortex responses |
| Anub'arak | Shared native combat/healing services | Permafrost placement, pursuing-spike route, burrower control and Leeching Swarm healing policy |

## Icecrown Citadel (631; Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Marrowgar | Bone Spike rescue and native Coldflame hazards | Saber Lash stack, Bonestorm spacing and tank regrouping |
| Deathwhisper | School-aware cultist priorities | Mana barrier transition, mind-control CC and phase-two tank swaps |
| Gunship | No complete native vehicle/boarding controller found | Cannon heat, mage targeting, boarding roles and faction variants |
| Saurfang | Ranged Blood Beast priority and Rune of Blood swaps | Beast slows/kiting, Blood Nova spacing and Mark healing |
| Festergut | Eight-stack Gastric Bloat tank swap | Spore groups, blight/inhale positions and heroic overlaps |
| Rotface | Shared native combat/ground/dispels | Small/Big Ooze routing, safe Infection dispel and explosion destinations |
| Putricide | Shared native combat/ground services | Abomination control, ooze/gas target roles and Mutated Plague tank rotation |
| Blood Prince Council | Shared native combat services | Invocation targets, kinetic-bomb juggling, nuclei tank and Empowered Vortex |
| Blood Queen | Swarming Shadows actor hazard | Vampire bite election/chains, Pact stack and air-phase spacing |
| Valithria | Skeleton/Suppresser/Archmage priorities plus friendly-boss healing assignment, raid-healer reservation and full-health finish | Portal/cloud controller, remaining add roles and live throughput |
| Sindragosa | Blistering Cold escape, Chilled weapon hold and grounded-tomb targeting | Ice Beacon spread, Unchained Magic, Mystic Buffet rotations and functional native ice-block LOS; cover-map remnants do not establish an active cover handler |
| Lich King | NEW carried-player Val'kyr rescue and ranged Ice Sphere priority | Necrotic Plague positioning/dispel, Defile, transition roles, Soul Reaper, Vile Spirits and Frostmourne room |
| Sister Svalna event | Shared native combat services | Impaling spear rescue and captain/event progression |

## Ruby Sanctum (724; Wrath)

| Encounter | Implemented source behavior | Open mechanics / validation |
|---|---|---|
| Baltharus | Shared native combat services | Clone targets, Enervating Brand spread and knockback recovery |
| Saviana | Shared native dispel/combat services | Conflagration separation and Enrage response |
| Zarithrian | Shared native combat/interrupt services | Roar recovery, add pickups and tank swaps |
| Halion | Shared native combat/ground services | Realm split, corporeality balancing, cutter geometry, meteor fire and positioned dispels |

## Cross-cutting blockers and next implementation order

1. Native client-control encounters need dedicated ability/seat/possession controllers, not ordinary melee movement: Razuvious, Teron, Chess, Malygos, Leviathan and Gunship.
2. Group assignment state needs deterministic ownership and re-election after deaths/disconnects: Horsemen, Kalecgos, Yogg, Halion, councils, soaking groups and healing rotations.
3. A target override alone is insufficient for pickup/use objectives and portal progression: Kael weapons, Valithria's Dream portals, Putricide abomination and Kil'jaeden drakes. Valithria now has ordinary friendly-boss healing; that does not implement portal/cloud navigation.
4. Spell/actor terrain safety requires actual room and collision tests. In particular Sindragosa's cover eligibility is currently inactive; residual map/GO constants are not coverage. Validate native Ice Block collision/LOS before enabling a bot cover claim. No native encounter repair was attempted here.
5. Bot composition, learned abilities, role assignments, gear, hard-mode choices and explicit player marks affect outcomes. Live tests must use non-GM bots/players, native raid sizes/difficulties and actual phase transitions.

The above also means the experience is not yet a complete unattended “taxi” through every raid. World bosses (Azuregos, Kazzak, the green dragons, Doom Lord Kazzak and Doomwalker) have no certified dedicated group strategy in this audit; the new harmful off-target interrupt expansion is intentionally restricted to raid maps.

## Source entry points

- `playerbot/strategy/generic/DungeonStrategy.cpp`: common combat/reaction registration and movement holds.
- `playerbot/strategy/values/EnemyHealerTargetValue.cpp`: shared off-target interrupt selector; class strategies register era-appropriate interrupt actions.
- `playerbot/strategy/actions/DungeonAddTargetAction.cpp`: role/command/lifecycle gates and add dispatch.
- `playerbot/strategy/actions/{RaidTotemTargetAction,IcecrownAddTargetAction,SummonObjectiveTargetAction,ThekalTargetAction,GluthTargetAction,TwinEmperorTargetAction,ZulGurubTargetAction,OperaDuoTargetAction,UlduarObjectiveTargetAction}.cpp`: focused target policies.
- `playerbot/strategy/actions/RaidHealingObjective.cpp`: friendly-boss healing admission and raid-healer reservation.
- `playerbot/strategy/actions/{MoltenCoreDungeonActions,BlackwingLairDungeonActions,KarazhanDungeonActions}.cpp`: raid-specific actions.
- `playerbot/strategy/actions/Encounter{Damage,Dispel,Healing,Taunt,Spell}Policy.cpp`: shared action-admission rules.
- `playerbot/strategy/values/*PositionValue.cpp` and `NativeEncounterActorHazards.cpp`: movement, cover, aura and actor hazards.
- Native evidence: each era's `src/game/AI/ScriptDevAI/scripts` raid directories and read-only live world template/spell records. Current source, not old audit commentary, determines what is implemented.

## Validation and rollout

| Check | Result |
|---|---|
| Original nine executable regression runners, ZERO/ONE/TWO each | 27/27 configurations passed again during the continuation |
| Continuation behavior runners, including actual dispatcher and Ulduar targets | 25/25 configurations passed; overlaps two original runners, so these totals are not additive |
| Final MSVC `/Zs`, fourteen translation units per core with actual project definitions/includes | Classic, TBC and Wrath passed: 42 translation-unit checks, including all new C++ files and action contexts |
| Live NPC script bindings, ZG phase/summon lists, Hodir prison auras and Kologarn vehicle targets | Read-only verification passed for applicable eras |
| Full server link/build, deployment and live raid clears | Not performed |

The nine runners are `raid_interrupt_regression.py`, `interrupt_effect_regression.py`, `pet_cast_admission_regression.py`, `encounter_dispel_regression.py`, `dungeon_add_priority_regression.py`, `icecrown_add_priority_regression.py`, `boss_cast_position_regression.py`, `encounter_movement_arbitration_regression.py`, and `encounter_safe_hold_regression.py`, under `tests/`. Run them with Python from an x64 MSVC developer environment, with the Classic/TBC/Wrath source checkouts next to the playerbots checkout. Existing fixture paths/GUID target types were brought up to date where necessary; their assertions were retained.

Continuation runners: `dungeon_add_priority_regression.py`, `boss_cast_position_regression.py`, `encounter_destination_path_regression.py`, `zul_gurub_visibility_regression.py`, `healing_selection_regression.py`, `full_health_wound_regression.py`, `raid_healing_objective_regression.py`, `heal_interrupt_recheck_regression.py`, and `healing_window_regression.py`. All run ZERO/ONE/TWO except the shared route-geometry fixture, which runs once. The actual dispatcher fixture covers role and manual-target arbitration for ZG, Opera and Ulduar; the healing fixtures cover selection, urgent triage, final-heal cancellation and queued-action reset rejection.

Validation results and exact commands are recorded in the accompanying local `raid-audit-20261002` work directory. Regression fixtures exercise actual function bodies with controlled native state; they do not simulate a live raid or prove a full clear. Native MSVC syntax checks use each real core's headers/configuration and do not link a server binary.

To activate this batch, **build Classic, TBC and Wrath**, deploy their resulting binaries and restart those realms. **No SQL, client patch, installer change or game reinstall is required.** No new server binary was built, deployed or restarted in this audit. Source/test success does not replace the required live encounter checks.
