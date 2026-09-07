#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool LinkedBurstAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || !bot->GetGroup() ||
        bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer() || !ai->CanMove()) return false;
    if (bot->GetMapId() != 543 && bot->GetMapId() != 555 && bot->GetMapId() != 564) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("linked burst position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    EncounterPosition current;
    std::vector<encounter::Circle> threats;
    return LinkedBurstThreats(ai, current, threats) && current.boss == plan.boss &&
        current.spell == plan.spell && current.source == plan.source &&
        encounter::OutsideCircles(plan.destination, threats);
}

bool LinkedBurstAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1 ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool LinkedBurstAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1;
}

bool LinkedBurstAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan) ||
        !LinkedBurstThreats(ai, current, threats) || current.boss != plan.boss ||
        current.spell != plan.spell || current.source != plan.source || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1)
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    ai->StopMoving();
    SetDuration(100);
    return true;
}
