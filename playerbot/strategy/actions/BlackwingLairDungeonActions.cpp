#include "playerbot/playerbot.h"
#include "BlackwingLairDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool BlackwingLairPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 469 || !bot->GetGroup()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("blackwing lair position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() ||
        (plan.spell != 18173 && plan.spell != 23620)) return false;
    if (Unit* boss = ai->GetUnit(plan.boss))
        if (boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() &&
            boss->IsInCombat() && boss->GetEntry() == 13020 && boss->GetVictim() == bot) return false;
    Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
    if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !carrier->IsAlive() ||
        !bot->IsInMap(carrier) || !carrier->HasAura(plan.spell) || carrier->HasCharmer()) return false;
    Player* player = static_cast<Player*>(carrier);
    return !player->IsBeingTeleported() && player->GetGroup() == bot->GetGroup();
}

bool BlackwingLairPositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool BlackwingLairPositionAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool BlackwingLairPositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !BlackwingLairBurstThreats(ai, current, threats) ||
        !ValidateEncounterDestination(ai, plan) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1.5f)
    {
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
