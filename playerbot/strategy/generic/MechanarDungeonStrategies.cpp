
#include "playerbot/playerbot.h"
#include "MechanarDungeonStrategies.h"
#include "DungeonMultipliers.h"

using namespace ai;

void MechanarDungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("pathaleon attack adds",
        NextAction::array(0, new NextAction("pathaleon attack adds", 65.0f), NULL)));
    triggers.push_back(new TriggerNode("mechanar safe position",
        NextAction::array(0, new NextAction("mechanar safe position", 105.0f), NULL)));
	triggers.push_back(new TriggerNode(
		"start nethermancer sepethrea fight",
		NextAction::array(0, new NextAction("enable nethermancer sepethrea fight strategy", 100.0f), NULL)));
}

void MechanarDungeonStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("mechanar safe position",
        NextAction::array(0, new NextAction("mechanar safe position", 105.0f), NULL)));
}

void MechanarDungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveMechanarPositionMultiplier(ai));
}

void MechanarDungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveMechanarPositionMultiplier(ai));
}

void NethermancerSepethreaFightStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    // The dungeon strategy owns one combined, path-checked hazard decision.
    // Running a second fixed-distance flee action fights its safe-position hold.
}

void NethermancerSepethreaFightStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"end nethermancer sepethrea fight",
		NextAction::array(0, new NextAction("disable nethermancer sepethrea fight strategy", 100.0f), NULL)));
}

void NethermancerSepethreaFightStrategy::InitDeadTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"end nethermancer sepethrea fight",
		NextAction::array(0, new NextAction("disable nethermancer sepethrea fight strategy", 100.0f), NULL)));
}
