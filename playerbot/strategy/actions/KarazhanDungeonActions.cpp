
#include "playerbot/playerbot.h"
#include "KarazhanDungeonActions.h"
#include "playerbot/strategy/Action.h"

using namespace ai;

bool NetherspitePositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetMapId() != 532 || !bot->IsInCombat()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("netherspite position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    Unit* portal = ai->GetUnit(plan.source);
    if (!boss || !portal || !boss->IsInWorld() || !portal->IsInWorld() ||
        boss->GetMap() != bot->GetMap() || portal->GetMap() != bot->GetMap() ||
        !boss->IsAlive() || !boss->IsInCombat() || !portal->IsAlive() || boss->HasAura(38542)) return false;
    const float oldZ = plan.destination.z;
    bot->UpdateAllowedPositionZ(plan.destination.x, plan.destination.y, plan.destination.z);
    return std::isfinite(plan.destination.z) && std::fabs(plan.destination.z - oldZ) < 6.0f;
}

bool NetherspitePositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f;
}

bool NetherspitePositionAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ai->CanMove()) return false;
    const WorldPosition here(bot);
    const WorldPosition destination(plan.map, plan.destination.x, plan.destination.y, plan.destination.z);
    if (!here.canPathTo(destination, bot)) return false;
    // Use ordinary pathfinding and the native portal SpellScript. No aura
    // grants, removals, boss weakening, teleportation or no-path movement.
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
