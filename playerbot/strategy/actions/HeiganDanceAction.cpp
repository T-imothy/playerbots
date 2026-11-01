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
    if (wave != plan.spell || !HeiganCloudSafe(bot, boss, plan.destination) || !HeiganManaBurnSafe(ai,boss,plan.destination))
    {
        // A native wave transition invalidates the old safe band immediately.
        // Ordinary repeated checks still use the one-second planner cache.
        value->Reset();
        plan = value->Get();
        if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() ||
            plan.source != controller->GetObjectGuid() || plan.boss != boss->GetObjectGuid()) return false;
    }
    return plan.spell == HeiganUpcomingWave(boss, controller) && HeiganCloudSafe(bot, boss, plan.destination) &&
        HeiganManaBurnSafe(ai,boss,plan.destination);
}

bool HeiganDanceAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && EncounterMovementRequired(bot, plan.destination, 1.0f);
}

bool HeiganDanceAction::ShouldReactionInterruptCast() const
{
#ifdef MANGOSBOT_ZERO
    // Admit the fresh native escape before interrupting healing. Selecting a
    // reaction is not proof that the current wave still has a walkable exit.
    if (bot->GetMapId() == 533) return false;
#endif
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1;
}

bool HeiganDanceAction::ShouldReactionInterruptMovement() const
{
#ifdef MANGOSBOT_ZERO
    // Keep the existing spline until Execute can retain or replace it. The
    // native dispatcher reuses a matching admitted route across reactions.
    if (bot->GetMapId() == 533) return false;
#endif
    return MovementAction::ShouldReactionInterruptMovement();
}

bool HeiganDanceAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
    std::vector<encounter::Circle> threats;
    std::vector<encounter::Point> floor;
    if (!HeiganFloorThreats(ai, plan, threats, floor) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1)
    {
#ifdef MANGOSBOT_ZERO
        // This shared native dispatcher preserves a full PATHFIND_NORMAL
        // route and current hazards. Generic travel clipping must not replace
        // the endpoint just admitted for this wave or restart a matching walk.
        return MoveBlackwingPath(WorldPosition(plan.map, plan.destination.x, plan.destination.y, plan.destination.z));
#else
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
#endif
    }
    ai->StopMoving();
    SetDuration(100);
    return true;
}
