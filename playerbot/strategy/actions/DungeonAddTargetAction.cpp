#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetTarget()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->HasCharmer() ||
        bot->IsBeingTeleported()) return nullptr;
    uint32 bossEntry = 0, addEntry = 0, phaseAura = 0;
    switch (bot->GetMapId())
    {
        case 545: bossEntry = 17796; addEntry = 17951; break; // Steamrigger mechanics repair him.
        case 553: bossEntry = 17975; addEntry = 19953; phaseAura = 34551; break; // Freywinn Tree Form.
        case 556: bossEntry = 23035; addEntry = 23132; phaseAura = 42354; break; // Anzu banish.
#ifdef MANGOSBOT_TWO
        case 576: bossEntry = 26763; addEntry = 26918; phaseAura = 47748; break; // Anomalus Rift Shield.
#endif
        default: return nullptr;
    }
    if (!bot->GetGroup() || ai->IsRealPlayer() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;
    auto valid = [this](Unit* unit)
    {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer() &&
            PossibleTargetsValue::IsValid(unit, bot, false) &&
            PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, false) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) && !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    auto commanded = [this](Unit* unit)
    {
        // A marked shielded boss can be intentional (for example Chaos Theory).
        // Do not discard that command merely because damage is currently immune.
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer() &&
            !sServerFacade.IsFriendlyTo(unit, bot) && bot->GetDistance(unit) <= sPlayerbotAIConfig.sightDistance;
    };
    if (commanded(ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"))) || commanded(AI_VALUE(Unit*, "rti target"))) return nullptr;
    Unit* owner = nullptr;
    Unit* selected = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible targets"))
    {
        Unit* add = ai->GetUnit(guid);
        if (!add || add->GetEntry() != addEntry || !valid(add)) continue;
        // Repair mechanics can be passive. Their live native summoner and its
        // encounter phase establish relevance without requiring an add victim.
        Unit* boss = ai->GetUnit(add->GetSpawnerGuid());
        if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || !bot->IsInMap(boss) ||
            boss->HasCharmer() || boss->GetEntry() != bossEntry || boss->GetVictim() == bot ||
            (phaseAura && !boss->HasAura(phaseAura))) continue;
        if (owner && owner != boss) return nullptr;
        owner = boss;
        // Keep attacking the selected live add instead of oscillating as they move.
        if (!selected || add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))
            selected = add;
    }
    return selected;
#else
    return nullptr;
#endif
}

bool DungeonAddTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != AI_VALUE(Unit*, "current target");
}
