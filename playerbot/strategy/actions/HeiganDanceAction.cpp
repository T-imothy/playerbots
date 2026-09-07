#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool HeiganDanceAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 533 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return false;
    Value<EncounterPosition>* value = ai->GetAiObjectContext()->GetValue<EncounterPosition>("heigan dance position");
    plan = value->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    Unit* controller = ai->GetUnit(plan.source);
    if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || boss->HasCharmer() ||
        boss->GetEntry() != 15936 || !bot->IsInMap(boss) || !controller || !bot->IsInMap(controller)) return false;
    const uint32 wave = HeiganUpcomingWave(boss, controller);
    if (!wave) return false;
    if (wave != plan.spell || !HeiganCloudSafe(bot, boss, plan.destination))
    {
        // A native wave transition invalidates the old safe band immediately.
        // Ordinary repeated checks still use the one-second planner cache.
        value->Reset();
        plan = value->Get();
        if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() ||
            plan.source != controller->GetObjectGuid() || plan.boss != boss->GetObjectGuid()) return false;
    }
    return plan.spell == HeiganUpcomingWave(boss, controller) && HeiganCloudSafe(bot, boss, plan.destination);
}

bool HeiganDanceAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1 ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool HeiganDanceAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1;
}

bool HeiganDanceAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
    std::vector<encounter::Circle> threats;
    std::vector<encounter::Point> floor;
    if (!HeiganFloorThreats(ai, plan, threats, floor) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1)
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    ai->StopMoving();
    SetDuration(100);
    return true;
}
