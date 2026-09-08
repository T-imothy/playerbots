#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetTarget()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->HasCharmer() ||
        bot->IsBeingTeleported()) return nullptr;
    uint32 bossEntry = 0, addEntry = 0, phaseAura = 0, summonerEntry = 0;
    uint32 alternateAddEntry = 0, secondAlternateAddEntry = 0;
    uint32 sourceBossEntry = 0, sourceAddEntry = 0, sourceAura = 0;
    uint32 rescueAura = 0;
    uint32 pursuedPlayerAura = 0, channelledPlayerAura = 0;
    uint32 bossOwnedAddAura = 0;
    bool engagedStaticAdd = false;
    switch (bot->GetMapId())
    {
        case 230: break; // Flamelash's native summoned spirits below.
        case 309: bossEntry = 14834; addEntry = 11357; engagedStaticAdd = true; break; // Son of Hakkar: already engaged by this group.
        case 509: bossEntry = 15369; addEntry = 15555; pursuedPlayerAura = 25725; break; // Ayamiss larva feeding on the paralyzed player.
        case 531: break; // Viscidus globs resolved as native summon objectives below.
        case 533: bossEntry = 15952; addEntry = 16486; rescueAura = 28622; break; // Maexxna Web Wrap.
#ifndef MANGOSBOT_ZERO
        case 548: case 568: break; // Karathress/Tidalvess and Halazzi totem objectives below.
        case 545:
            bossEntry = 17796; addEntry = 17951; // Steamrigger repair mechanics.
            sourceBossEntry = 17798; sourceAddEntry = 17954; sourceAura = 31543; // Kalithresh's active distiller.
            break;
        case 553: bossEntry = 17975; addEntry = 19953; phaseAura = 34551; break; // Freywinn Tree Form.
        case 555: bossEntry = 18732; addEntry = 19226; summonerEntry = 19427; break; // Vorpil's Void Travelers.
        case 556: bossEntry = 23035; addEntry = 23132; phaseAura = 42354; break; // Anzu banish.
        case 557: case 558: break; // Shaffar/Maladaar native summon objectives below.
        case 585: sourceBossEntry = 24723; sourceAddEntry = 24722; sourceAura = 44320; break; // Selin's active crystal.
#ifdef MANGOSBOT_TWO
        case 574: bossEntry = 23953; addEntry = 23965; rescueAura = 48400; break; // Keleseth's Frost Tomb channel.
        case 575: bossEntry = 26668; addEntry = 27281; channelledPlayerAura = 48278; break; // Svala's active ritual channelers.
        case 576: bossEntry = 26763; addEntry = 26918; phaseAura = 47748; break; // Anomalus Rift Shield.
        case 604:
            bossEntry = 29304; addEntry = 29742; // Slad'ran's player-summoned Snake Wrap.
            rescueAura = bot->GetMap()->IsRegularDifficulty() ? 55126 : 61476;
            break;
        case 619: sourceBossEntry = 29309; sourceAddEntry = 30176; sourceAura = 56153; break; // Nadox's shielding guardian.
        case 608: case 632: case 650: break; // Ichoron/Bronjahm/Paletress native summon objectives below.
        case 624:
            bossEntry = 33993; addEntry = 33998; alternateAddEntry = 34049;
            bossOwnedAddAura = 64218; // Emalon's actual Overcharge, before the minion's first self-stack.
            break;
        case 649:
            bossEntry = 34780; addEntry = 34813; alternateAddEntry = 34825;
            break; // Jaraxxus's attackable volcano/portal summons; native normal-mode immunity is preserved.
        case 631:
            bossEntry = 36612; addEntry = 36619; alternateAddEntry = 38711; secondAlternateAddEntry = 38712;
            rescueAura = 69065; // Marrowgar: all three native player-summoned Bone Spikes.
            break;
#endif
#endif
        default: return nullptr;
    }
    if (!bot->GetGroup() || ai->IsRealPlayer()) return nullptr;
    if (Unit* demon = InnerDemonAction::GetDemon(ai)) return demon;
    if (ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;
    auto valid = [this, rescueAura](Unit* unit)
    {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer() &&
            PossibleTargetsValue::IsValid(unit, bot, false) &&
            PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, rescueAura != 0) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            (rescueAura || !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot));
    };
    auto commanded = [this](Unit* unit)
    {
        // A marked shielded boss can be intentional (for example Chaos Theory).
        // Do not discard that command merely because damage is currently immune.
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer() &&
            !sServerFacade.IsFriendlyTo(unit, bot) && bot->GetDistance(unit) <= sPlayerbotAIConfig.sightDistance;
    };
    if (commanded(ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"))) || commanded(AI_VALUE(Unit*, "rti target"))) return nullptr;
    if (bot->GetMapId() == 309)
        if (Unit* trio = GetThekalTarget()) return trio;
    if (bot->GetMapId() == 533)
        if (Unit* chow = GetGluthTarget()) return chow;
    if (Unit* objective = GetSummonObjectiveTarget()) return objective;
    if (Unit* totem = GetRaidTotemTarget()) return totem;
    if (Unit* twin = GetTwinEmperorTarget()) return twin;
    if (Unit* icecrown = GetIcecrownAddTarget()) return icecrown;
    auto validBoss = [this](Unit* boss)
    {
        return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && bot->IsInMap(boss) &&
            !boss->HasCharmer() && boss->GetVictim() != bot;
    };
    auto groupPlayer = [this](Unit* unit) -> Player*
    {
        if (!unit || !unit->IsPlayer() || !unit->IsInWorld() || !unit->IsAlive() ||
            !bot->IsInMap(unit) || unit->HasCharmer()) return nullptr;
        Player* player = static_cast<Player*>(unit);
        return !player->IsBeingTeleported() && player->GetGroup() == bot->GetGroup() ? player : nullptr;
    };
    Unit* owner = nullptr;
    Unit* selected = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    const auto possibleTargets = AI_VALUE(std::list<ObjectGuid>, "possible targets");
    if (engagedStaticAdd)
    {
        bool needsPoison = !bot->HasAura(24321);
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref && !needsPoison; ref = ref->next())
            if (Player* member = groupPlayer(ref->getSource())) needsPoison = !member->HasAura(24321);
        if (!needsPoison) return nullptr;
    }
    for (const auto& guid : possibleTargets)
    {
        Unit* add = ai->GetUnit(guid);
        if (!add) continue;
        const bool auraSource = sourceAddEntry && add->GetEntry() == sourceAddEntry;
        const bool priorityAdd = add->GetEntry() == addEntry ||
            (alternateAddEntry && add->GetEntry() == alternateAddEntry) ||
            (secondAlternateAddEntry && add->GetEntry() == secondAlternateAddEntry);
        if ((!auraSource && (!addEntry || !priorityAdd)) || !valid(add)) continue;
        // Repair mechanics can be passive. Their live native summoner and its
        // encounter phase establish relevance without requiring an add victim.
        Unit* boss = nullptr;
        if (engagedStaticAdd)
        {
            // Sons are static dungeon creatures. Never treat a nearby idle
            // Son as permission to pull it or use a fake summoner relationship.
            if (!add->IsInCombat() || !groupPlayer(add->GetVictim())) continue;
            for (const auto& bossGuid : possibleTargets)
            {
                Unit* candidate = ai->GetUnit(bossGuid);
                if (!validBoss(candidate) || candidate->GetEntry() != bossEntry || add->GetDistance(candidate) > 60) continue;
                if (boss && boss != candidate) return nullptr;
                boss = candidate;
            }
        }
        else if (bossOwnedAddAura)
        {
            // Emalon's minions can be static spawns. The boss-owned aura,
            // rather than a fabricated summon relationship, identifies the task.
            for (const auto& bossGuid : possibleTargets)
            {
                Unit* candidate = ai->GetUnit(bossGuid);
                if (!validBoss(candidate) || candidate->GetEntry() != bossEntry ||
                    !add->GetSpellAuraHolder(bossOwnedAddAura, candidate->GetObjectGuid())) continue;
                if (boss && boss != candidate) return nullptr;
                boss = candidate;
            }
        }
        else if (rescueAura)
        {
            // The trapped player summons these rescue objects, not the boss.
            // Native immobilization must not make them look like protected CC.
            Unit* victim = ai->GetUnit(add->GetSpawnerGuid());
            if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
                !bot->IsInMap(victim) || victim->HasCharmer() || !victim->HasAura(rescueAura)) continue;
            Player* member = static_cast<Player*>(victim);
            if (member->IsBeingTeleported() || member->GetGroup() != bot->GetGroup()) continue;
            for (const auto& bossGuid : possibleTargets)
            {
                Unit* candidate = ai->GetUnit(bossGuid);
                if (!validBoss(candidate) || candidate->GetEntry() != bossEntry) continue;
                if (boss && boss != candidate) return nullptr;
                boss = candidate;
            }
        }
        else if (auraSource)
        {
            // Static crystals have no boss summoner. The boss aura's exact
            // caster identifies the active source, including Nadox's guardian.
            for (const auto& bossGuid : possibleTargets)
            {
                Unit* candidate = ai->GetUnit(bossGuid);
                if (!validBoss(candidate) || candidate->GetEntry() != sourceBossEntry ||
                    !candidate->GetSpellAuraHolder(sourceAura, add->GetObjectGuid())) continue;
                if (boss && boss != candidate) return nullptr;
                boss = candidate;
            }
        }
        else
            boss = ai->GetUnit(add->GetSpawnerGuid());
        if (!auraSource && summonerEntry)
        {
            // Vorpil's passive helper summons the travelers. Resolve exactly
            // that live native chain; never guess ownership from proximity.
            if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !bot->IsInMap(boss) ||
                boss->HasCharmer() || boss->GetEntry() != summonerEntry) continue;
            boss = ai->GetUnit(boss->GetSpawnerGuid());
        }
        if (!validBoss(boss) || boss->GetEntry() != (auraSource ? sourceBossEntry : bossEntry) ||
            (!auraSource && phaseAura && !boss->HasAura(phaseAura))) continue;
        if (pursuedPlayerAura)
        {
            Player* victim = groupPlayer(add->GetVictim());
            if (!victim || !victim->GetSpellAuraHolder(pursuedPlayerAura, boss->GetObjectGuid())) continue;
        }
        if (channelledPlayerAura)
        {
            bool rescuing = false;
            for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            {
                Player* member = groupPlayer(ref->getSource());
                if (member && member->GetSpellAuraHolder(channelledPlayerAura, add->GetObjectGuid()))
                {
                    rescuing = true;
                    break;
                }
            }
            if (!rescuing) continue;
        }
        if (owner && owner != boss) return nullptr;
        owner = boss;
        // Keep attacking the selected live add instead of oscillating as they move.
        if (!selected || add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))
            selected = add;
    }
    return selected;
}

bool DungeonAddTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != AI_VALUE(Unit*, "current target");
}
