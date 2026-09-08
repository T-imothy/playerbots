# Healer strategy route appendix

Generated from the reviewed, expansion-preprocessed source on 2026-09-08. Entries are reached by the named spec/mode and optional strategy suite. PvE includes ordinary dungeon use; encounter overlays and live overrides are additional. Priorities are source expressions. This is code scheduling evidence, not observed casts.

## Classic

### HolyPriest

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | circle of healing | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | inner focus | inner focus | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | power infusion | power infusion | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | target of attacker | elune's grace | ACTION_HIGH + 3 | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | psychic scream | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | shackle undead | shackle undead | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | desperate prayer | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | PriestStrategy.cpp |
| Combat | Spec | Raid | medium threat | fade | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pvp | random | free action potion | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | power word: shield | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | circle of healing | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit | divine spirit | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit on party | divine spirit on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | inner fire | inner fire | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude | power word: fortitude | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude on party | power word: fortitude on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of fortitude on party | prayer of fortitude on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of shadow protection on party | prayer of shadow protection on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of spirit on party | prayer of spirit on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection | shadow protection | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection on party | shadow protection on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadowguard | shadowguard | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | swimming | levitate | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | touch of weakness | touch of weakness | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | renew | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | resurrection | ACTION_EMERGENCY | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### DisciplinePriest

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of healing | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | inner focus | inner focus | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | power infusion | power infusion | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | target of attacker | elune's grace | ACTION_HIGH + 3 | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | psychic scream | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | shackle undead | shackle undead | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | desperate prayer | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | PriestStrategy.cpp |
| Combat | Spec | Raid | medium threat | fade | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pvp | random | free action potion | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | power word: shield | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of healing | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit | divine spirit | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit on party | divine spirit on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | inner fire | inner fire | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude | power word: fortitude | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude on party | power word: fortitude on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of fortitude on party | prayer of fortitude on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of shadow protection on party | prayer of shadow protection on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of spirit on party | prayer of spirit on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection | shadow protection | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection on party | shadow protection on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadowguard | shadowguard | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | swimming | levitate | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | touch of weakness | touch of weakness | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | renew | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | resurrection | ACTION_EMERGENCY | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### HolyPaladin

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | divine favor | divine favor | ACTION_HIGH | HolyPaladinStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice interrupt | hammer of justice | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice on enemy healer | hammer of justice on enemy healer | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice on snare target | hammer of justice on snare target | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | turn undead | turn undead | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure disease | cleanse disease | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure magic | cleanse magic | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure poison | cleanse poison | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure disease | cleanse disease on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure magic | cleanse magic on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure poison | cleanse poison on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member rooted | blessing of freedom on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | rooted | blessing of freedom | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | flash of light | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | divine shield | ACTION_EMERGENCY + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | holy light | ACTION_EMERGENCY | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | lay on hands | ACTION_EMERGENCY + 2 | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | enemy is close | judgement | ACTION_NORMAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy shock on self | ACTION_MEDIUM_HEAL + 2 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | flash of light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | flash of light on party | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | lay on hands on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL + 4 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy shock on party | ACTION_MEDIUM_HEAL + 5 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | flash of light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | protect party member | blessing of protection on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pvp | random | free action potion | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | seal | seal of light | ACTION_NORMAL + 2 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aura | Pve, Pvp, Raid | no paladin aura | concentration aura | ACTION_NORMAL + 1 | HolyPaladinStrategy.cpp |
| NonCombat | Aura | Pve, Pvp, Raid | no paladin aura | paladin aura | ACTION_NORMAL | PaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | HolyPaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply stone | ACTION_NORMAL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure disease | cleanse disease | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure magic | cleanse magic | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure poison | cleanse poison | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure disease | cleanse disease on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure magic | cleanse magic on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure poison | cleanse poison on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member rooted | blessing of freedom on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | rooted | blessing of freedom | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | flash of light | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | holy light | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | flash of light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | flash of light on party | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | holy light on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | redemption | ACTION_EMERGENCY | PaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | flash of light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### RestorationShaman

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp | shaman weapon | flametongue weapon | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | wind shear | wind shear | ACTION_INTERRUPT | ShamanStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | wind shear on enemy healer | wind shear on enemy healer | ACTION_INTERRUPT | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | cure disease | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure poison | cure poison | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | cure disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure poison | cure poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | lesser healing wave | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | healing wave | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | lesser healing wave | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | healing wave | ACTION_MEDIUM_HEAL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | lesser healing wave | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low mana | mana tide totem | ACTION_EMERGENCY | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | chain heal | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | healing wave | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | lesser healing wave on party | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | healing wave on party | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | lesser healing wave on party | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | lesser healing wave on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | healing wave on party | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pvp | player has flag | ghost wolf | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | purge | purge | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Spec | Pvp | random | free action potion | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | air totem | windfury totem | ACTION_HIGH + 1 | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | air totem | wrath of air totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | earth totem | strength of earth totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | fire totem | searing totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | water totem | healing stream totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Raid | often | apply oil | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp | shaman weapon | flametongue weapon | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water breathing | water breathing | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water breathing on party | water breathing on party | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water walking | water walking | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water walking on party | water walking on party | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | cure disease | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure poison | cure poison | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | cure disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure poison | cure poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | lesser healing wave | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | healing wave | ACTION_MOVE | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | lesser healing wave | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | healing wave | ACTION_MEDIUM_HEAL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | lesser healing wave | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | chain heal | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | healing wave | ACTION_HIGH | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | lesser healing wave on party | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | healing wave on party | ACTION_MOVE | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | lesser healing wave on party | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | ancestral spirit | ACTION_EMERGENCY | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | lesser healing wave on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | healing wave on party | ACTION_HIGH | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pvp | player has flag | ghost wolf | ACTION_EMERGENCY | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### RestorationDruid

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | nature's swiftness | nature's swiftness | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | innervate | innervate | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | nature's grasp | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | entangling roots | entangling roots on cc | ACTION_INTERRUPT | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | entangling roots kite | entangling roots | ACTION_INTERRUPT | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hibernate | hibernate on cc | ACTION_INTERRUPT | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure poison | abolish poison | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure poison | abolish poison on party | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member remove curse | remove curse on party | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | remove curse | remove curse | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | rooted | caster form | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | rejuvenation | ACTION_LIGHT_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | regrowth | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | swiftmend | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | regrowth | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | tranquility | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | regrowth | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | rejuvenation on party | ACTION_LIGHT_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | regrowth on party | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | swiftmend on party | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pvp | player has flag | travel form | ACTION_HIGH | DruidStrategy.cpp |
| Combat | Spec | Pvp | random | free action potion | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | rebirth | rebirth | ACTION_EMERGENCY | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | barkskin | ACTION_CRITICAL_HEAL + 3 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | gift of the wild on party | gift of the wild on party | ACTION_NORMAL + 5 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | mark of the wild | mark of the wild | ACTION_NORMAL + 1 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | mark of the wild on party | mark of the wild on party | ACTION_NORMAL + 3 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | thorns | thorns | ACTION_NORMAL + 1 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | thorns on party | thorns on party | ACTION_NORMAL + 2 | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure poison | abolish poison | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure poison | abolish poison on party | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member remove curse | remove curse on party | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | remove curse | remove curse | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | rejuvenation | ACTION_LIGHT_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | regrowth | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | swiftmend | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | regrowth | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | tranquility | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | regrowth | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | rejuvenation on party | ACTION_LIGHT_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | regrowth on party | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | swiftmend on party | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pvp | player has flag | travel form | ACTION_EMERGENCY | DruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### Native healing-tree talent inventory

Includes passive talents and native spell-learning talents; a listed talent is not automatically an AI cast. Tree IDs: Priest Discipline 201/Holy 202; Shaman restoration 262; Druid restoration 282; Paladin Holy 382. See the main audit for active-spell support and deliberate limits.

| Tree | Minimum talent level | First-rank ID | Native name |
|---|---|---|---|
| 201 | 10 | 14522 | unbreakable will |
| 201 | 10 | 14524 | wand specialization |
| 201 | 15 | 14523 | silent resolve |
| 201 | 15 | 14749 | improved power word: fortitude |
| 201 | 15 | 14748 | improved power word: shield |
| 201 | 15 | 14531 | martyrdom |
| 201 | 20 | 14751 | inner focus |
| 201 | 20 | 14521 | meditation |
| 201 | 25 | 14747 | improved inner fire |
| 201 | 25 | 14520 | mental agility |
| 201 | 25 | 14750 | improved mana burn |
| 201 | 30 | 18551 | mental strength |
| 201 | 30 | 14752 | divine spirit |
| 201 | 35 | 18544 | force of will |
| 201 | 40 | 10060 | power infusion |
| 202 | 10 | 14913 | healing focus |
| 202 | 10 | 14908 | improved renew |
| 202 | 10 | 14889 | holy specialization |
| 202 | 15 | 27900 | spell warding |
| 202 | 15 | 18530 | divine fury |
| 202 | 20 | 15237 | holy nova |
| 202 | 20 | 27811 | blessed recovery |
| 202 | 20 | 14892 | inspiration |
| 202 | 25 | 27789 | holy reach |
| 202 | 25 | 14912 | improved healing |
| 202 | 25 | 14909 | searing light |
| 202 | 30 | 14911 | improved prayer of healing |
| 202 | 30 | 20711 | spirit of redemption |
| 202 | 30 | 14901 | spiritual guidance |
| 202 | 35 | 14898 | spiritual healing |
| 202 | 40 | 724 | lightwell |
| 262 | 10 | 16182 | improved healing wave |
| 262 | 10 | 16179 | tidal focus |
| 262 | 15 | 16184 | improved reincarnation |
| 262 | 15 | 16176 | ancestral healing |
| 262 | 15 | 16173 | totemic focus |
| 262 | 20 | 16180 | nature's guidance |
| 262 | 20 | 16181 | healing focus |
| 262 | 20 | 16189 | totemic mastery |
| 262 | 20 | 29187 | healing grace |
| 262 | 25 | 16187 | restorative totems |
| 262 | 25 | 16194 | tidal mastery |
| 262 | 30 | 29206 | healing way |
| 262 | 30 | 16188 | nature's swiftness |
| 262 | 35 | 16178 | purification |
| 262 | 40 | 16190 | mana tide totem |
| 282 | 10 | 17050 | improved mark of the wild |
| 282 | 10 | 17056 | furor |
| 282 | 15 | 17069 | improved healing touch |
| 282 | 15 | 17063 | nature's focus |
| 282 | 15 | 17079 | improved enrage |
| 282 | 20 | 17106 | reflection |
| 282 | 20 | 5570 | insect swarm |
| 282 | 20 | 17118 | subtlety |
| 282 | 25 | 24968 | tranquil spirit |
| 282 | 25 | 17111 | improved rejuvenation |
| 282 | 30 | 17116 | nature's swiftness |
| 282 | 30 | 17104 | gift of nature |
| 282 | 30 | 17123 | improved tranquility |
| 282 | 35 | 17074 | improved regrowth |
| 282 | 40 | 18562 | swiftmend |
| 382 | 10 | 20262 | divine strength |
| 382 | 10 | 20257 | divine intellect |
| 382 | 15 | 20205 | spiritual focus |
| 382 | 15 | 20224 | improved seal of righteousness |
| 382 | 20 | 20237 | healing light |
| 382 | 20 | 26573 | consecration |
| 382 | 20 | 20234 | improved lay on hands |
| 382 | 20 | 9453 | unyielding faith |
| 382 | 25 | 20210 | illumination |
| 382 | 25 | 20244 | improved blessing of wisdom |
| 382 | 30 | 20216 | divine favor |
| 382 | 30 | 20359 | lasting judgement |
| 382 | 35 | 5923 | holy power |
| 382 | 40 | 20473 | holy shock |

## Tbc

### HolyPriest

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | circle of healing | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | inner focus | inner focus | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | power infusion | power infusion | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | low mana | shadowfiend | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | medium mana | symbol of hope | ACTION_HIGH + 1 | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_HIGH | HolyPriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | target of attacker | elune's grace | ACTION_HIGH + 2 | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | chastise | chastise | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | psychic scream | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | shackle undead | shackle undead | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | binding heal | binding heal | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | desperate prayer | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | PriestStrategy.cpp |
| Combat | Spec | Raid | medium threat | fade | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | power word: shield | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | circle of healing | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit | divine spirit | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit on party | divine spirit on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | inner fire | inner fire | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_NORMAL | HolyPriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude | power word: fortitude | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude on party | power word: fortitude on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of fortitude on party | prayer of fortitude on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of shadow protection on party | prayer of shadow protection on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of spirit on party | prayer of spirit on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection | shadow protection | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection on party | shadow protection on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadowguard | shadowguard | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | swimming | levitate | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | touch of weakness | touch of weakness | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | renew | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | resurrection | ACTION_EMERGENCY | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### DisciplinePriest

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of healing | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | inner focus | inner focus | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | power infusion | power infusion | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | low mana | shadowfiend | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | medium mana | symbol of hope | ACTION_HIGH + 1 | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_HIGH | DisciplinePriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | target of attacker | elune's grace | ACTION_HIGH + 2 | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | chastise | chastise | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | psychic scream | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | shackle undead | shackle undead | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | binding heal | binding heal | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | desperate prayer | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | pain suppression | ACTION_CRITICAL_HEAL + 3 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | PriestStrategy.cpp |
| Combat | Spec | Raid | medium threat | fade | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | protect party member | pain suppression on party | ACTION_EMERGENCY | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | power word: shield | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of healing | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit | divine spirit | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit on party | divine spirit on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | inner fire | inner fire | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_NORMAL | DisciplinePriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude | power word: fortitude | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude on party | power word: fortitude on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of fortitude on party | prayer of fortitude on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of shadow protection on party | prayer of shadow protection on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of spirit on party | prayer of spirit on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection | shadow protection | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection on party | shadow protection on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadowguard | shadowguard | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | swimming | levitate | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | touch of weakness | touch of weakness | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | renew | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | resurrection | ACTION_EMERGENCY | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### HolyPaladin

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | divine favor | divine favor | ACTION_HIGH | HolyPaladinStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | divine illumination | divine illumination | ACTION_HIGH + 1 | HolyPaladinStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | avenging wrath | ACTION_HIGH + 1 | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice interrupt | hammer of justice | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice on enemy healer | hammer of justice on enemy healer | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice on snare target | hammer of justice on snare target | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | turn undead | turn undead | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure disease | cleanse disease | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure magic | cleanse magic | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure poison | cleanse poison | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure disease | cleanse disease on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure magic | cleanse magic on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure poison | cleanse poison on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member rooted | blessing of freedom on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | rooted | blessing of freedom | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | flash of light | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | divine shield | ACTION_EMERGENCY + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | holy light | ACTION_EMERGENCY | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | lay on hands | ACTION_EMERGENCY + 2 | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | enemy is close | judgement | ACTION_NORMAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | divine favor | ACTION_MEDIUM_HEAL + 3 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy shock on self | ACTION_MEDIUM_HEAL + 2 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | flash of light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | flash of light on party | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | lay on hands on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | divine favor | ACTION_MEDIUM_HEAL + 6 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL + 4 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy shock on party | ACTION_MEDIUM_HEAL + 5 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | flash of light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | protect party member | blessing of protection on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | seal | seal of light | ACTION_NORMAL + 2 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aura | Pve, Pvp, Raid | no paladin aura | concentration aura | ACTION_NORMAL + 1 | HolyPaladinStrategy.cpp |
| NonCombat | Aura | Pve, Pvp, Raid | no paladin aura | paladin aura | ACTION_NORMAL | PaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | HolyPaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure disease | cleanse disease | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure magic | cleanse magic | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure poison | cleanse poison | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure disease | cleanse disease on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure magic | cleanse magic on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure poison | cleanse poison on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member rooted | blessing of freedom on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | rooted | blessing of freedom | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | flash of light | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | holy light | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | flash of light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | flash of light on party | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | holy light on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | redemption | ACTION_EMERGENCY | PaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | flash of light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### RestorationShaman

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | bloodlust | bloodlust | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | heroism | heroism | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | earth shield on party tank | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Buff | Pve, Pvp | shaman weapon | flametongue weapon | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | water shield | water shield | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | wind shear | wind shear | ACTION_INTERRUPT | ShamanStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | wind shear on enemy healer | wind shear on enemy healer | ACTION_INTERRUPT | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | cure disease | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure poison | cure poison | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | cure disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure poison | cure poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | lesser healing wave | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | healing wave | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | lesser healing wave | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | healing wave | ACTION_MEDIUM_HEAL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | lesser healing wave | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low mana | mana tide totem | ACTION_EMERGENCY | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | chain heal | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | healing wave | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | lesser healing wave on party | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | healing wave on party | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | lesser healing wave on party | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | healing wave on party | ACTION_LIGHT_HEAL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | lesser healing wave on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | healing wave on party | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pvp | player has flag | ghost wolf | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | purge | purge | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | air totem | windfury totem | ACTION_HIGH + 1 | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | air totem | wrath of air totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | earth totem | strength of earth totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | fire totem | flametongue totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | water totem | healing stream totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Raid | often | apply oil | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | earth shield on party tank | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp | shaman weapon | flametongue weapon | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | totemic recall | totemic recall | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water breathing | water breathing | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water breathing on party | water breathing on party | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water shield | water shield | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water walking | water walking | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water walking on party | water walking on party | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | cure disease | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure poison | cure poison | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | cure disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure poison | cure poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | lesser healing wave | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | healing wave | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | lesser healing wave | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | healing wave | ACTION_MEDIUM_HEAL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | lesser healing wave | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | chain heal | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | healing wave | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | lesser healing wave on party | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | healing wave on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | lesser healing wave on party | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | ancestral spirit | ACTION_EMERGENCY | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | healing wave on party | ACTION_LIGHT_HEAL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | lesser healing wave on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | healing wave on party | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pvp | player has flag | ghost wolf | ACTION_EMERGENCY | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### RestorationDruid

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | nature's swiftness | nature's swiftness | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | innervate | innervate | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | tree form | tree form | ACTION_MOVE | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | nature's grasp | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | entangling roots | entangling roots on cc | ACTION_INTERRUPT | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | entangling roots kite | entangling roots | ACTION_INTERRUPT | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hibernate | hibernate on cc | ACTION_INTERRUPT | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure poison | abolish poison | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure poison | abolish poison on party | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member remove curse | remove curse on party | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | remove curse | remove curse | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | rejuvenation | ACTION_LIGHT_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | regrowth | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | swiftmend | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | lifebloom | lifebloom | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | regrowth | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | tranquility | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | regrowth | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | rejuvenation on party | ACTION_LIGHT_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | regrowth on party | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | swiftmend on party | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pvp | player has flag | travel form | ACTION_HIGH | DruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | rebirth | rebirth | ACTION_EMERGENCY | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | barkskin | ACTION_CRITICAL_HEAL + 3 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | gift of the wild on party | gift of the wild on party | ACTION_NORMAL + 5 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | mark of the wild | mark of the wild | ACTION_NORMAL + 1 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | mark of the wild on party | mark of the wild on party | ACTION_NORMAL + 3 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | thorns | thorns | ACTION_NORMAL + 1 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | thorns on party | thorns on party | ACTION_NORMAL + 2 | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure poison | abolish poison | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure poison | abolish poison on party | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member remove curse | remove curse on party | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | remove curse | remove curse | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | rejuvenation | ACTION_LIGHT_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | regrowth | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | swiftmend | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | lifebloom | lifebloom | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | regrowth | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | tranquility | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | regrowth | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | rejuvenation on party | ACTION_LIGHT_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | regrowth on party | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | swiftmend on party | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pvp | player has flag | travel form | ACTION_EMERGENCY | DruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### Native healing-tree talent inventory

Includes passive talents and native spell-learning talents; a listed talent is not automatically an AI cast. Tree IDs: Priest Discipline 201/Holy 202; Shaman restoration 262; Druid restoration 282; Paladin Holy 382. See the main audit for active-spell support and deliberate limits.

| Tree | Minimum talent level | First-rank ID | Native name |
|---|---|---|---|
| 201 | 10 | 14522 | unbreakable will |
| 201 | 10 | 14524 | wand specialization |
| 201 | 15 | 14523 | silent resolve |
| 201 | 15 | 14749 | improved power word: fortitude |
| 201 | 15 | 14748 | improved power word: shield |
| 201 | 15 | 14531 | martyrdom |
| 201 | 20 | 33167 | absolution |
| 201 | 20 | 14751 | inner focus |
| 201 | 20 | 14521 | meditation |
| 201 | 25 | 14747 | improved inner fire |
| 201 | 25 | 14520 | mental agility |
| 201 | 25 | 14750 | improved mana burn |
| 201 | 30 | 18551 | mental strength |
| 201 | 30 | 14752 | divine spirit |
| 201 | 30 | 33174 | improved divine spirit |
| 201 | 35 | 33186 | focused power |
| 201 | 35 | 18544 | force of will |
| 201 | 40 | 45234 | focused will |
| 201 | 40 | 10060 | power infusion |
| 201 | 40 | 33201 | reflective shield |
| 201 | 45 | 34908 | enlightenment |
| 201 | 50 | 33206 | pain suppression |
| 202 | 10 | 14913 | healing focus |
| 202 | 10 | 14908 | improved renew |
| 202 | 10 | 14889 | holy specialization |
| 202 | 15 | 27900 | spell warding |
| 202 | 15 | 18530 | divine fury |
| 202 | 20 | 15237 | holy nova |
| 202 | 20 | 27811 | blessed recovery |
| 202 | 20 | 14892 | inspiration |
| 202 | 25 | 27789 | holy reach |
| 202 | 25 | 14912 | improved healing |
| 202 | 25 | 14909 | searing light |
| 202 | 30 | 14911 | healing prayers |
| 202 | 30 | 20711 | spirit of redemption |
| 202 | 30 | 14901 | spiritual guidance |
| 202 | 35 | 33150 | surge of light |
| 202 | 35 | 14898 | spiritual healing |
| 202 | 40 | 34753 | holy concentration |
| 202 | 40 | 724 | lightwell |
| 202 | 40 | 33142 | blessed resilience |
| 202 | 45 | 33158 | empowered healing |
| 202 | 50 | 34861 | circle of healing |
| 262 | 10 | 16182 | improved healing wave |
| 262 | 10 | 16179 | tidal focus |
| 262 | 15 | 16184 | improved reincarnation |
| 262 | 15 | 16176 | ancestral healing |
| 262 | 15 | 16173 | totemic focus |
| 262 | 20 | 16180 | nature's guidance |
| 262 | 20 | 16181 | healing focus |
| 262 | 20 | 16189 | totemic mastery |
| 262 | 20 | 29187 | healing grace |
| 262 | 25 | 16187 | restorative totems |
| 262 | 25 | 16194 | tidal mastery |
| 262 | 30 | 29206 | healing way |
| 262 | 30 | 16188 | nature's swiftness |
| 262 | 30 | 30864 | focused mind |
| 262 | 35 | 16178 | purification |
| 262 | 40 | 16190 | mana tide totem |
| 262 | 40 | 30881 | nature's guardian |
| 262 | 45 | 30867 | nature's blessing |
| 262 | 45 | 30872 | improved chain heal |
| 262 | 50 | 974 | earth shield |
| 282 | 10 | 17050 | improved mark of the wild |
| 282 | 10 | 17056 | furor |
| 282 | 15 | 17069 | naturalist |
| 282 | 15 | 17063 | nature's focus |
| 282 | 15 | 16833 | natural shapeshifter |
| 282 | 20 | 17106 | intensity |
| 282 | 20 | 17118 | subtlety |
| 282 | 20 | 16864 | omen of clarity |
| 282 | 25 | 24968 | tranquil spirit |
| 282 | 25 | 17111 | improved rejuvenation |
| 282 | 30 | 17116 | nature's swiftness |
| 282 | 30 | 17104 | gift of nature |
| 282 | 30 | 17123 | improved tranquility |
| 282 | 35 | 33879 | empowered touch |
| 282 | 35 | 17074 | improved regrowth |
| 282 | 40 | 34151 | living spirit |
| 282 | 40 | 18562 | swiftmend |
| 282 | 40 | 33881 | natural perfection |
| 282 | 45 | 33886 | empowered rejuvenation |
| 282 | 50 | 33891 | tree of life |
| 382 | 10 | 20262 | divine strength |
| 382 | 10 | 20257 | divine intellect |
| 382 | 15 | 20205 | spiritual focus |
| 382 | 15 | 20224 | improved seal of righteousness |
| 382 | 20 | 20237 | healing light |
| 382 | 20 | 31821 | aura mastery |
| 382 | 20 | 20234 | improved lay on hands |
| 382 | 20 | 9453 | unyielding faith |
| 382 | 25 | 20210 | illumination |
| 382 | 25 | 20244 | improved blessing of wisdom |
| 382 | 30 | 31822 | pure of heart |
| 382 | 30 | 20216 | divine favor |
| 382 | 30 | 20359 | sanctified light |
| 382 | 35 | 31825 | purifying power |
| 382 | 35 | 5923 | holy power |
| 382 | 40 | 31833 | light's grace |
| 382 | 40 | 20473 | holy shock |
| 382 | 40 | 31828 | blessed life |
| 382 | 45 | 31837 | holy guidance |
| 382 | 50 | 31842 | divine illumination |

## Wotlk

### HolyPriest

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | circle of healing | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | inner focus | inner focus | ACTION_HIGH + 1 | PriestStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | power infusion | power infusion | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | low mana | hymn of hope | ACTION_HIGH - 1 | HolyPriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | low mana | shadowfiend | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_HIGH | HolyPriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | target of attacker | elune's grace | ACTION_HIGH + 1 | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | psychic scream | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | shackle undead | shackle undead | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | binding heal | binding heal | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical aoe heal | divine hymn | ACTION_CRITICAL_HEAL + 3 | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | desperate prayer | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | guardian spirit | ACTION_CRITICAL_HEAL + 3 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | PriestStrategy.cpp |
| Combat | Spec | Raid | medium threat | fade | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | guardian spirit on party | ACTION_CRITICAL_HEAL + 3 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | tricks of the trade | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | power word: shield | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | circle of healing | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit | divine spirit | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit on party | divine spirit on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | inner fire | inner fire | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_NORMAL | HolyPriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude | power word: fortitude | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude on party | power word: fortitude on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of fortitude on party | prayer of fortitude on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of shadow protection on party | prayer of shadow protection on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of spirit on party | prayer of spirit on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection | shadow protection | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection on party | shadow protection on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadowguard | shadowguard | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | swimming | levitate | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | touch of weakness | touch of weakness | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | renew | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | resurrection | ACTION_EMERGENCY | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | HolyPriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | critical health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | low health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | party member critical health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | party member low health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | target of attacker | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |

### DisciplinePriest

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of healing | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | inner focus | inner focus | ACTION_HIGH + 1 | PriestStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | power infusion | power infusion | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | low mana | hymn of hope | ACTION_HIGH - 1 | DisciplinePriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | low mana | shadowfiend | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_HIGH | DisciplinePriestStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | target of attacker | elune's grace | ACTION_HIGH + 1 | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | psychic scream | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | shackle undead | shackle undead | ACTION_INTERRUPT | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | binding heal | binding heal | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical aoe heal | divine hymn | ACTION_CRITICAL_HEAL + 3 | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | desperate prayer | ACTION_EMERGENCY | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | pain suppression | ACTION_CRITICAL_HEAL + 3 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | penance | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | penance | ACTION_MEDIUM_HEAL + 3 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Raid | medium threat | fade | ACTION_DISPEL | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | penance on party | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | penance on party | ACTION_MEDIUM_HEAL + 3 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | protect party member | pain suppression on party | ACTION_EMERGENCY | DisciplinePriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | tricks of the trade | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | power word: shield | ACTION_HIGH | PriestStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of healing | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Aoe | Pve, Pvp, Raid | medium aoe heal | prayer of mending | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit | divine spirit | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | divine spirit on party | divine spirit on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | fear ward | fear ward | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | inner fire | inner fire | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | prayer of mending | ACTION_NORMAL | DisciplinePriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude | power word: fortitude | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | power word: fortitude on party | power word: fortitude on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of fortitude on party | prayer of fortitude on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of shadow protection on party | prayer of shadow protection on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | prayer of spirit on party | prayer of spirit on party | ACTION_NORMAL + 5 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection | shadow protection | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadow protection on party | shadow protection on party | ACTION_NORMAL + 3 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shadowguard | shadowguard | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | swimming | levitate | ACTION_NORMAL | PriestStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | touch of weakness | touch of weakness | ACTION_NORMAL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | abolish disease | ACTION_DISPEL + 1 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic | dispel magic | ACTION_DISPEL + 3 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | dispel magic on party | dispel magic on party | ACTION_DISPEL + 2 | PriestStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | abolish disease on party | ACTION_DISPEL | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | flash heal | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | penance | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | greater heal | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | penance | ACTION_MEDIUM_HEAL + 3 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | renew | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | renew on party | ACTION_LIGHT_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | binding heal | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | flash heal on party | ACTION_CRITICAL_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | penance on party | ACTION_CRITICAL_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | power word: shield on party | ACTION_CRITICAL_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | resurrection | ACTION_EMERGENCY | PriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | binding heal | ACTION_MEDIUM_HEAL + 4 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | greater heal on party | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | penance on party | ACTION_MEDIUM_HEAL + 3 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | power word: shield on party | ACTION_MEDIUM_HEAL + 2 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | binding heal | ACTION_MEDIUM_HEAL + 1 | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | greater heal on party | ACTION_MEDIUM_HEAL | DisciplinePriestStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | critical health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | low health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | party member critical health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | party member low health | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | target of attacker | stop hymn of hope | ACTION_EMERGENCY | PriestStrategy.cpp |

### HolyPaladin

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | divine favor | divine favor | ACTION_HIGH | HolyPaladinStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | divine illumination | divine illumination | ACTION_HIGH + 1 | HolyPaladinStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | aura mastery | ACTION_CRITICAL_HEAL + 1 | HolyPaladinStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | avenging wrath | ACTION_HIGH + 1 | PaladinStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | beacon of light | ACTION_HIGH | HolyPaladinStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | sacred shield | ACTION_HIGH - 1 | HolyPaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice interrupt | hammer of justice | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice on enemy healer | hammer of justice on enemy healer | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hammer of justice on snare target | hammer of justice on snare target | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | turn undead | turn undead | ACTION_INTERRUPT | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure disease | cleanse disease | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure magic | cleanse magic | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse cure poison | cleanse poison | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure disease | cleanse disease on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure magic | cleanse magic on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse party member cure poison | cleanse poison on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member rooted | blessing of freedom on party | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | rooted | blessing of freedom | ACTION_DISPEL | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | flash of light | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | divine shield | ACTION_EMERGENCY + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | holy light | ACTION_EMERGENCY | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | lay on hands | ACTION_EMERGENCY + 2 | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | enemy is close | judgement of light | ACTION_NORMAL + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | hand of sacrifice | hand of sacrifice | ACTION_MEDIUM_HEAL + 8 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | divine favor | ACTION_MEDIUM_HEAL + 3 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL + 1 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | holy shock on self | ACTION_MEDIUM_HEAL + 2 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low mana | divine plea | ACTION_HIGH + 3 | PaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | flash of light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | flash of light on party | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | lay on hands on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | divine favor | ACTION_MEDIUM_HEAL + 6 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL + 4 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | holy shock on party | ACTION_MEDIUM_HEAL + 5 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | flash of light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | protect party member | blessing of protection on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | seal | seal of light | ACTION_NORMAL + 2 | HolyPaladinStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | tricks of the trade | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Aura | Pve, Pvp, Raid | no paladin aura | concentration aura | ACTION_NORMAL + 1 | HolyPaladinStrategy.cpp |
| NonCombat | Aura | Pve, Pvp, Raid | no paladin aura | paladin aura | ACTION_NORMAL | PaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | HolyPaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply stone | ACTION_NORMAL | PaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | beacon of light | ACTION_NORMAL | HolyPaladinStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | sacred shield | ACTION_NORMAL - 1 | HolyPaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure disease | cleanse disease | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure magic | cleanse magic | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse cure poison | cleanse poison | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure disease | cleanse disease on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure magic | cleanse magic on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse party member cure poison | cleanse poison on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member rooted | blessing of freedom on party | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | rooted | blessing of freedom | ACTION_DISPEL | PaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | flash of light | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | holy light | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | holy light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | flash of light | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | flash of light on party | ACTION_LIGHT_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | holy light on party | ACTION_CRITICAL_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | redemption | ACTION_EMERGENCY | PaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | holy light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | flash of light on party | ACTION_MEDIUM_HEAL | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | set glyph::Blessing of Wisdom | set glyph::Blessing of Wisdom | ACTION_NORMAL + 1 | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | set glyph::Divinity | set glyph::Divinity | ACTION_NORMAL + 1 | HolyPaladinStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### RestorationShaman

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | bloodlust | bloodlust | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | heroism | heroism | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | tidal force | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | often | earth shield on party tank | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | shaman weapon | earthliving weapon | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | water shield | water shield | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | wind shear | wind shear | ACTION_INTERRUPT | ShamanStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | wind shear on enemy healer | wind shear on enemy healer | ACTION_INTERRUPT | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse spirit curse | cleanse spirit | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse spirit disease | cleanse spirit | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cleanse spirit poison | cleanse spirit | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure disease | cure disease | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure poison | cure poison | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cleanse spirit curse | cleanse spirit curse on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cleanse spirit disease | cleanse spirit disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cleanse spirit poison | cleanse spirit poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure disease | cure disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure poison | cure poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | lesser healing wave | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | healing wave | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | lesser healing wave | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | riptide | ACTION_CRITICAL_HEAL + 3 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | levelup | set totembars on levelup | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | healing wave | ACTION_MEDIUM_HEAL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | riptide | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low mana | mana tide totem | ACTION_EMERGENCY | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | chain heal | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | healing wave | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | riptide | ACTION_MEDIUM_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | lesser healing wave on party | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | healing wave on party | ACTION_CRITICAL_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | lesser healing wave on party | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | riptide on party | ACTION_CRITICAL_HEAL + 3 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | healing wave on party | ACTION_LIGHT_HEAL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | riptide on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | healing wave on party | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | riptide on party | ACTION_MEDIUM_HEAL + 1 | RestorationShamanStrategy.cpp |
| Combat | Spec | Pvp | player has flag | ghost wolf | ACTION_HIGH | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | purge | purge | ACTION_DISPEL | ShamanStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | tricks of the trade | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | air totem | windfury totem | ACTION_HIGH + 1 | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | air totem | wrath of air totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | earth totem | strength of earth totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | fire totem | flametongue totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| Combat | Totems | Pve, Pvp, Raid | water totem | healing stream totem | ACTION_HIGH | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | earth shield on party tank | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | shaman weapon | earthliving weapon | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water breathing | water breathing | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water breathing on party | water breathing on party | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water shield | water shield | ACTION_NORMAL | RestorationShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water walking | water walking | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | water walking on party | water walking on party | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse spirit curse | cleanse spirit | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse spirit disease | cleanse spirit | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cleanse spirit poison | cleanse spirit | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure disease | cure disease | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure poison | cure poison | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cleanse spirit curse | cleanse spirit curse on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cleanse spirit disease | cleanse spirit disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cleanse spirit poison | cleanse spirit poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure disease | cure disease on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure poison | cure poison on party | ACTION_DISPEL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | lesser healing wave | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | healing wave | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | lesser healing wave | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | riptide | ACTION_CRITICAL_HEAL + 3 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | levelup | set totembars on levelup | ACTION_HIGH | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | healing wave | ACTION_MEDIUM_HEAL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | riptide | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | chain heal | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | healing wave | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | riptide | ACTION_MEDIUM_HEAL + 1 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | lesser healing wave on party | ACTION_LIGHT_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | healing wave on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | lesser healing wave on party | ACTION_CRITICAL_HEAL + 2 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | riptide on party | ACTION_CRITICAL_HEAL + 3 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member dead | ancestral spirit | ACTION_EMERGENCY | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | healing wave on party | ACTION_LIGHT_HEAL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | riptide on party | ACTION_CRITICAL_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | healing wave on party | ACTION_MEDIUM_HEAL | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | riptide on party | ACTION_MEDIUM_HEAL + 1 | RestorationShamanStrategy.cpp |
| NonCombat | Spec | Pvp | player has flag | ghost wolf | ACTION_EMERGENCY | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | totemic recall | totemic recall | ACTION_NORMAL | ShamanStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### RestorationDruid

| State | Suite | Modes | Trigger | Action | Priority | Source |
|---|---|---|---|---|---|---|
| Combat | Aoe | Pve, Pvp, Raid | melee very high aoe | goblin sapper | ACTION_HIGH + 1 | ClassStrategy.cpp |
| Combat | Aoe | Pve, Pvp, Raid | ranged high aoe | throw grenade | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | nature's swiftness | nature's swiftness | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Boost | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | innervate | innervate | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Buff | Pve, Pvp, Raid | tree form | tree form | ACTION_MOVE | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | enemy five yards | nature's grasp | ACTION_HIGH | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | entangling roots | entangling roots on cc | ACTION_INTERRUPT | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | entangling roots kite | entangling roots | ACTION_INTERRUPT | RestorationDruidStrategy.cpp |
| Combat | Cc | Pve, Pvp, Raid | hibernate | hibernate on cc | ACTION_INTERRUPT | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | cure poison | abolish poison | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member cure poison | abolish poison on party | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | party member remove curse | remove curse on party | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Cure | Pve, Pvp, Raid | remove curse | remove curse | ACTION_DISPEL | DruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | almost full health | rejuvenation | ACTION_LIGHT_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat long stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | combat stuck | unstuck | static_cast<float>(ACTION_IDLE | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | regrowth | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | critical health | swiftmend | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | invalid target | select new target | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | lifebloom | lifebloom | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | nourish | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | low health | regrowth | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | tranquility | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium aoe heal | wild growth on party | ACTION_MEDIUM_HEAL + 3 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | medium health | regrowth | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | mounted | check mount state | ACTION_EMERGENCY | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | often | use trinket | ACTION_HIGH | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member almost full health | rejuvenation on party | ACTION_LIGHT_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | regrowth on party | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member critical health | swiftmend on party | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | nourish on party | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member low health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | party member medium health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| Combat | Spec | Pvp | player has flag | travel form | ACTION_HIGH | DruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | rebirth | rebirth | ACTION_EMERGENCY | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | misdirection on party tank | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | tank threat transfer | tricks of the trade | ACTION_HIGH + 2 | ClassStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | target of attacker | barkskin | ACTION_CRITICAL_HEAL + 3 | RestorationDruidStrategy.cpp |
| Combat | Spec | Pve, Pvp, Raid | very often | use lightwell | ACTION_LIGHT_HEAL | ClassStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | gift of the wild on party | gift of the wild on party | ACTION_NORMAL + 5 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | mark of the wild | mark of the wild | ACTION_NORMAL + 1 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | mark of the wild on party | mark of the wild on party | ACTION_NORMAL + 3 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | often | apply oil | ACTION_NORMAL | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | party member dead | revive | ACTION_HIGH | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | thorns | thorns | ACTION_NORMAL + 1 | DruidStrategy.cpp |
| NonCombat | Buff | Pve, Pvp, Raid | thorns on party | thorns on party | ACTION_NORMAL + 2 | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | cure poison | abolish poison | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member cure poison | abolish poison on party | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | party member remove curse | remove curse on party | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Cure | Pve, Pvp, Raid | remove curse | remove curse | ACTION_DISPEL | DruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | almost full health | rejuvenation | ACTION_LIGHT_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal azeroth | use dark portal azeroth | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | at dark portal outland | move from dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | nature's swiftness heal | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | regrowth | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | critical health | swiftmend | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | lifebloom | lifebloom | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | nourish | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | low health | regrowth | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | tranquility | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium aoe heal | wild growth on party | ACTION_MEDIUM_HEAL + 3 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | medium health | regrowth | ACTION_MEDIUM_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | near dark portal | move to dark portal | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member almost full health | rejuvenation on party | ACTION_LIGHT_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | nature's swiftness heal on party | ACTION_CRITICAL_HEAL + 4 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | regrowth on party | ACTION_CRITICAL_HEAL + 1 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member critical health | swiftmend on party | ACTION_CRITICAL_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | nourish on party | ACTION_MEDIUM_HEAL + 2 | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member low health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | party member medium health | regrowth on party | ACTION_MEDIUM_HEAL | RestorationDruidStrategy.cpp |
| NonCombat | Spec | Pvp | player has flag | travel form | ACTION_EMERGENCY | DruidStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | vehicle near | enter vehicle | 10.0f | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check mount state | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | check values | ACTION_IDLE | ClassStrategy.cpp |
| NonCombat | Spec | Pve, Pvp, Raid | very often | use lightwell | 80.0f | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat end | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | combat start | set combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | death | set dead state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |
| Reaction | Spec | Pve, Pvp, Raid | resurrect | set non combat state | ACTION_PASSTROUGH + 10 | ClassStrategy.cpp |

### Native healing-tree talent inventory

Includes passive talents and native spell-learning talents; a listed talent is not automatically an AI cast. Tree IDs: Priest Discipline 201/Holy 202; Shaman restoration 262; Druid restoration 282; Paladin Holy 382. See the main audit for active-spell support and deliberate limits.

| Tree | Minimum talent level | First-rank ID | Native name |
|---|---|---|---|
| 201 | 10 | 14522 | unbreakable will |
| 201 | 10 | 47586 | twin disciplines |
| 201 | 15 | 14523 | silent resolve |
| 201 | 15 | 14747 | improved inner fire |
| 201 | 15 | 14749 | improved power word: fortitude |
| 201 | 15 | 14531 | martyrdom |
| 201 | 20 | 14521 | meditation |
| 201 | 20 | 14751 | inner focus |
| 201 | 20 | 14748 | improved power word: shield |
| 201 | 25 | 33167 | absolution |
| 201 | 25 | 14520 | mental agility |
| 201 | 25 | 14750 | improved mana burn |
| 201 | 30 | 33201 | reflective shield |
| 201 | 30 | 18551 | mental strength |
| 201 | 30 | 63574 | soul warding |
| 201 | 35 | 33186 | focused power |
| 201 | 35 | 34908 | enlightenment |
| 201 | 40 | 45234 | focused will |
| 201 | 40 | 10060 | power infusion |
| 201 | 40 | 63504 | improved flash heal |
| 201 | 45 | 57470 | renewed hope |
| 201 | 45 | 47535 | rapture |
| 201 | 45 | 47507 | aspiration |
| 201 | 50 | 47509 | divine aegis |
| 201 | 50 | 33206 | pain suppression |
| 201 | 50 | 47516 | grace |
| 201 | 55 | 52795 | borrowed time |
| 201 | 60 | 47540 | penance |
| 202 | 10 | 14913 | healing focus |
| 202 | 10 | 14908 | improved renew |
| 202 | 10 | 14889 | holy specialization |
| 202 | 15 | 27900 | spell warding |
| 202 | 15 | 18530 | divine fury |
| 202 | 20 | 19236 | desperate prayer |
| 202 | 20 | 27811 | blessed recovery |
| 202 | 20 | 14892 | inspiration |
| 202 | 25 | 27789 | holy reach |
| 202 | 25 | 14912 | improved healing |
| 202 | 25 | 14909 | searing light |
| 202 | 30 | 14911 | healing prayers |
| 202 | 30 | 20711 | spirit of redemption |
| 202 | 30 | 14901 | spiritual guidance |
| 202 | 35 | 33150 | surge of light |
| 202 | 35 | 14898 | spiritual healing |
| 202 | 40 | 34753 | holy concentration |
| 202 | 40 | 724 | lightwell |
| 202 | 40 | 33142 | blessed resilience |
| 202 | 45 | 64127 | body and soul |
| 202 | 45 | 33158 | empowered healing |
| 202 | 45 | 63730 | serendipity |
| 202 | 50 | 63534 | empowered renew |
| 202 | 50 | 34861 | circle of healing |
| 202 | 50 | 47558 | test of faith |
| 202 | 55 | 47562 | divine providence |
| 202 | 60 | 47788 | guardian spirit |
| 262 | 10 | 16182 | improved healing wave |
| 262 | 10 | 16173 | totemic focus |
| 262 | 15 | 16184 | improved reincarnation |
| 262 | 15 | 29187 | healing grace |
| 262 | 15 | 16179 | tidal focus |
| 262 | 20 | 16180 | improved water shield |
| 262 | 20 | 16181 | healing focus |
| 262 | 20 | 55198 | tidal force |
| 262 | 20 | 16176 | ancestral healing |
| 262 | 25 | 16187 | restorative totems |
| 262 | 25 | 16194 | tidal mastery |
| 262 | 30 | 29206 | healing way |
| 262 | 30 | 16188 | nature's swiftness |
| 262 | 30 | 30864 | focused mind |
| 262 | 35 | 16178 | purification |
| 262 | 40 | 30881 | nature's guardian |
| 262 | 40 | 16190 | mana tide totem |
| 262 | 40 | 51886 | cleanse spirit |
| 262 | 45 | 51554 | blessing of the eternals |
| 262 | 45 | 30872 | improved chain heal |
| 262 | 45 | 30867 | nature's blessing |
| 262 | 50 | 51556 | ancestral awakening |
| 262 | 50 | 974 | earth shield |
| 262 | 50 | 51560 | improved earth shield |
| 262 | 55 | 51562 | tidal waves |
| 262 | 60 | 61295 | riptide |
| 282 | 10 | 17050 | improved mark of the wild |
| 282 | 10 | 17063 | nature's focus |
| 282 | 10 | 17056 | furor |
| 282 | 15 | 17069 | naturalist |
| 282 | 15 | 17118 | subtlety |
| 282 | 15 | 16833 | natural shapeshifter |
| 282 | 20 | 17106 | intensity |
| 282 | 20 | 16864 | omen of clarity |
| 282 | 20 | 48411 | master shapeshifter |
| 282 | 25 | 24968 | tranquil spirit |
| 282 | 25 | 17111 | improved rejuvenation |
| 282 | 30 | 17116 | nature's swiftness |
| 282 | 30 | 17104 | gift of nature |
| 282 | 30 | 17123 | improved tranquility |
| 282 | 35 | 33879 | empowered touch |
| 282 | 35 | 17074 | nature's bounty |
| 282 | 40 | 34151 | living spirit |
| 282 | 40 | 18562 | swiftmend |
| 282 | 40 | 33881 | natural perfection |
| 282 | 45 | 33886 | empowered rejuvenation |
| 282 | 45 | 48496 | living seed |
| 282 | 50 | 48539 | revitalize |
| 282 | 50 | 65139 | tree of life |
| 282 | 50 | 48535 | improved tree of life |
| 282 | 55 | 63410 | improved barkskin |
| 282 | 55 | 51179 | gift of the earthmother |
| 282 | 60 | 48438 | wild growth |
| 382 | 10 | 20205 | spiritual focus |
| 382 | 10 | 20224 | seals of the pure |
| 382 | 15 | 20237 | healing light |
| 382 | 15 | 20257 | divine intellect |
| 382 | 15 | 9453 | unyielding faith |
| 382 | 20 | 31821 | aura mastery |
| 382 | 20 | 20210 | illumination |
| 382 | 20 | 20234 | improved lay on hands |
| 382 | 25 | 20254 | improved concentration aura |
| 382 | 25 | 20244 | improved blessing of wisdom |
| 382 | 25 | 53660 | blessed hands |
| 382 | 30 | 31822 | pure of heart |
| 382 | 30 | 20216 | divine favor |
| 382 | 30 | 20359 | sanctified light |
| 382 | 35 | 31825 | purifying power |
| 382 | 35 | 5923 | holy power |
| 382 | 40 | 31833 | light's grace |
| 382 | 40 | 20473 | holy shock |
| 382 | 40 | 31828 | blessed life |
| 382 | 45 | 53551 | sacred cleansing |
| 382 | 45 | 31837 | holy guidance |
| 382 | 50 | 31842 | divine illumination |
| 382 | 50 | 53671 | judgements of the pure |
| 382 | 55 | 53569 | infusion of light |
| 382 | 55 | 53556 | enlightened judgements |
| 382 | 60 | 53563 | beacon of light |

