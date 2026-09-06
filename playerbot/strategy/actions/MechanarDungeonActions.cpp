
#include "playerbot/playerbot.h"
#include "MechanarDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* PathaleonAddsAction::GetTarget()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 554 || !bot->IsInCombat() || ai->IsHeal(bot)) return nullptr;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->GetEntry() == 19220 && unit->IsInWorld() && unit->GetMap() == bot->GetMap() &&
            unit->IsAlive() && unit->IsInCombat()) { boss = unit; break; }
    }
    // Keep the current boss tank on the boss. Respect the configured raid mark.
    if (!boss || boss->GetVictim() == bot) return nullptr;
    Unit* marked = AI_VALUE(Unit*, "rti target");
    if (marked && marked->GetEntry() != 21062) return nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    Unit* nearest = nullptr;
    Unit* retained = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        // The shared list can reintroduce CC targets as a last resort. Encounter
        // priority must never turn that fallback into an instruction to break CC.
        if (!unit || unit->GetEntry() != 21062 || !unit->IsInWorld() || unit->GetMap() != bot->GetMap() ||
            !unit->IsAlive() || !unit->IsInCombat() || PossibleAttackTargetsValue::HasBreakableCC(unit, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot)) continue;
        if (unit == marked) return unit;
        if (unit == current) retained = unit;
        if (!nearest || bot->GetDistance(unit) < bot->GetDistance(nearest)) nearest = unit;
    }
    return retained ? retained : nearest;
#else
    return nullptr;
#endif
}

bool PathaleonAddsAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != AI_VALUE(Unit*, "current target");
}

bool MechanarPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 554 || !bot->IsInCombat()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("mechanar position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    return boss && (boss->GetEntry() == 19219 || boss->GetEntry() == 19221 || boss->GetEntry() == 19220) &&
        boss->IsInWorld() && boss->GetMap() == bot->GetMap() &&
        boss->IsAlive() && boss->IsInCombat();
}

bool MechanarPositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool MechanarPositionAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !ValidateEncounterDestination(ai, plan)) return false;
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
