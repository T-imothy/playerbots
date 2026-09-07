#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool HakkarPoisonAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 309 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        bot->HasAura(24321) || !ai->CanMove()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("hakkar poison position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() || plan.spell != 24321) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    Unit* cloud = ai->GetUnit(plan.source);
    const float radius = NativeEncounterSpellRadius(24320);
    return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && !boss->HasCharmer() &&
        boss->GetEntry() == 14834 && bot->IsInMap(boss) && IsHakkarPoisonSource(bot, cloud) &&
        std::isfinite(radius) && radius > 2 && radius <= 20 &&
        cloud->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= radius - 1 &&
        (boss->GetVictim() != bot || bot->GetDistance(cloud) <= radius - 2);
}

bool HakkarPoisonAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool HakkarPoisonAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f)
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    ai->StopMoving();
    SetDuration(100);
    // Wait near the engaged Son. Native on-death/on-spawn spells apply the
    // poison; a lingering cloud is never treated as an active poison source.
    return true;
}
