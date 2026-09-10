#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotPartyCombatCoordinator.h"
#include "LivingPartyCombatStrategy.h"

using namespace ai;

float LivingPartyCombatMultiplier::GetValue(Action* action)
{
    return sPlayerbotPartyCombatCoordinator.ActionMultiplier(ai->GetBot(), action);
}

void LivingPartyCombatStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new LivingPartyCombatMultiplier(ai));
}
