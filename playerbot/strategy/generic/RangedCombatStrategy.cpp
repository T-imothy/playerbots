
#include "playerbot/playerbot.h"
#include "RangedCombatStrategy.h"

using namespace ai;

void RangedCombatStrategy::InitCombatTriggers(std::list<TriggerNode*> &triggers)
{
    // Approach is independent of spell affordability and tank-opening threat
    // wait. Native movement, stay, CC and encounter-position policies apply.
    triggers.push_back(new TriggerNode(
        "enemy out of spell",
        NextAction::array(0, new NextAction("reach spell", ACTION_MOVE), NULL)));

    triggers.push_back(new TriggerNode(
        "enemy too close for spell",
        NextAction::array(0, new NextAction("flee", ACTION_MOVE), NULL)));
}
