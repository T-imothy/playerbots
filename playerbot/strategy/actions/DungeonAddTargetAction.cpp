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
    uint32 sourceBossEntry = 0, sourceAddEntry = 0, sourceAura = 0;
    uint32 rescueAura = 0;
    switch (bot->GetMapId())
    {
        case 533: bossEntry = 15952; addEntry = 16486; rescueAura = 28622; break; // Maexxna Web Wrap.
#ifndef MANGOSBOT_ZERO
        case 545:
            bossEntry = 17796; addEntry = 17951; // Steamrigger repair mechanics.
            sourceBossEntry = 17798; sourceAddEntry = 17954; sourceAura = 31543; // Kalithresh's active distiller.
            break;
        case 553: bossEntry = 17975; addEntry = 19953; phaseAura = 34551; break; // Freywinn Tree Form.
        case 555: bossEntry = 18732; addEntry = 19226; summonerEntry = 19427; break; // Vorpil's Void Travelers.
        case 556: bossEntry = 23035; addEntry = 23132; phaseAura = 42354; break; // Anzu banish.
        case 585: sourceBossEntry = 24723; sourceAddEntry = 24722; sourceAura = 44320; break; // Selin's active crystal.
#ifdef MANGOSBOT_TWO
        case 576: bossEntry = 26763; addEntry = 26918; phaseAura = 47748; break; // Anomalus Rift Shield.
        case 619: sourceBossEntry = 29309; sourceAddEntry = 30176; sourceAura = 56153; break; // Nadox's shielding guardian.
#endif
#endif
        default: return nullptr;
    }
    if (!bot->GetGroup() || ai->IsRealPlayer() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;
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
    auto validBoss = [this](Unit* boss)
    {
        return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && bot->IsInMap(boss) &&
            !boss->HasCharmer() && boss->GetVictim() != bot;
    };
    Unit* owner = nullptr;
    Unit* selected = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    const auto possibleTargets = AI_VALUE(std::list<ObjectGuid>, "possible targets");
    for (const auto& guid : possibleTargets)
    {
        Unit* add = ai->GetUnit(guid);
        if (!add) continue;
        const bool auraSource = sourceAddEntry && add->GetEntry() == sourceAddEntry;
        if ((!auraSource && (!addEntry || add->GetEntry() != addEntry)) || !valid(add)) continue;
        // Repair mechanics can be passive. Their live native summoner and its
        // encounter phase establish relevance without requiring an add victim.
        Unit* boss = nullptr;
        if (rescueAura)
        {
            // The wrapped player summons this rescue object, not the boss.
            // Its native self-stun must not make it look like protected CC.
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
