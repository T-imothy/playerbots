#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "Entities/DynamicObject.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool AkilzonStormAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 568 ||
        bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("akilzon storm position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() || plan.spell != 44007) return false;
    DynamicObject* eye = bot->GetMap()->GetDynamicObject(plan.source);
    Unit* boss = AkilzonStormBoss(bot, eye);
    return boss && boss->GetObjectGuid() == plan.boss &&
        eye->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= eye->GetRadius() - 1;
#else
    return false;
#endif
}

bool AkilzonStormAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1 ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool AkilzonStormAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1;
}

bool AkilzonStormAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
#ifndef MANGOSBOT_ZERO
    // Validation can adjust terrain height. Recheck the adjusted point against
    // the live eye rather than replacing it with the cached destination.
    DynamicObject* eye = bot->GetMap()->GetDynamicObject(plan.source);
    Unit* boss = AkilzonStormBoss(bot, eye);
    if (!boss || boss->GetObjectGuid() != plan.boss ||
        eye->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > eye->GetRadius() - 1) return false;
#endif
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1)
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    ai->StopMoving();
    SetDuration(100);
    return true;
}
