
#include "playerbot/playerbot.h"
#include "MechanarDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool MechanarPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 554 || !bot->IsInCombat()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("mechanar position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    return boss && boss->GetEntry() == 19219 && boss->IsInWorld() && boss->GetMap() == bot->GetMap() &&
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
