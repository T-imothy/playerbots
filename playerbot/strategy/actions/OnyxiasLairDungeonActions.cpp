#include "playerbot/playerbot.h"
#include "OnyxiasLairDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool OnyxiaPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetMapId() != 249 || !bot->IsInCombat()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("onyxia position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    if (!boss || !boss->IsInWorld() || boss->GetMap() != bot->GetMap() || !boss->IsAlive() || !boss->IsInCombat()) return false;
    // An off-tank assigned to adds must be allowed to chase them, not get
    // dragged back to the boss's flank. A breath escape still takes precedence.
    Unit* current = ai->GetAiObjectContext()->GetValue<Unit*>("current target")->Get();
    if (!plan.exclusive && current && current != boss) return false;
    const float oldZ = plan.destination.z;
    bot->UpdateAllowedPositionZ(plan.destination.x, plan.destination.y, plan.destination.z);
    return std::isfinite(plan.destination.z) && std::fabs(plan.destination.z - oldZ) < 8;
}

bool OnyxiaPositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool OnyxiaPositionAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ai->CanMove()) return false;
    const WorldPosition here(bot);
    const WorldPosition destination(plan.map, plan.destination.x, plan.destination.y, plan.destination.z);
    if (!here.canPathTo(destination, bot)) return false;
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}

Unit* OnyxiaAddsAction::GetTarget()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 249 || !bot->IsInCombat() || ai->IsHeal(bot)) return nullptr;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && unit->GetMap() == bot->GetMap() && unit->GetEntry() == 10184 && unit->IsAlive())
        { boss = unit; break; }
    }
    if (!boss || boss->GetVictim() == bot) return nullptr;
    const bool airborne = boss->IsLevitating() || boss->GetPositionZ() - bot->GetPositionZ() > 10;
    if (!airborne && !ai->IsTank(bot)) return nullptr;
    Unit* nearest = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || unit->GetMap() != bot->GetMap() || !unit->IsAlive() || !unit->IsInCombat()) continue;
        // This list already applies the shared crowd-control/attackability rules.
        if (unit->GetEntry() != 11262) continue;
        if (!nearest || bot->GetDistance(unit) < bot->GetDistance(nearest)) nearest = unit;
    }
    return nearest;
}

bool OnyxiaAddsAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != AI_VALUE(Unit*, "current target");
}
