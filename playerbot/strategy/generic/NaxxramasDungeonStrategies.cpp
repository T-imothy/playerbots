
#include "playerbot/playerbot.h"
#include "NaxxramasDungeonStrategies.h"
#include "DungeonMultipliers.h"

using namespace ai;

void NaxxramasDungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("naxxramas safe position",
        NextAction::array(0, new NextAction("naxxramas safe position", ACTION_EMERGENCY + 2), NULL)));
	triggers.push_back(new TriggerNode(
		"start four horseman fight",
		NextAction::array(0, new NextAction("enable four horseman fight strategy", 100.0f), NULL)));
}

void NaxxramasDungeonStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("naxxramas safe position",
        NextAction::array(0, new NextAction("naxxramas safe position", ACTION_EMERGENCY + 2), NULL)));
}

void NaxxramasDungeonStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("naxxramas safe position",
        NextAction::array(0, new NextAction("naxxramas safe position", ACTION_EMERGENCY + 2), NULL)));
}

void NaxxramasDungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveNaxxramasPositionMultiplier(ai));
}

void NaxxramasDungeonStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveNaxxramasPositionMultiplier(ai));
}

void FourHorsemanFightStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"void zone too close",
		NextAction::array(0, new NextAction("move away from void zone", 100.0f), NULL)));
}

void FourHorsemanFightStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
        "end four horseman fight",
		NextAction::array(0, new NextAction("disable four horseman fight strategy", 100.0f), NULL)));
}

void FourHorsemanFightStrategy::InitDeadTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
        "end four horseman fight",
		NextAction::array(0, new NextAction("disable four horseman fight strategy", 100.0f), NULL)));
}
