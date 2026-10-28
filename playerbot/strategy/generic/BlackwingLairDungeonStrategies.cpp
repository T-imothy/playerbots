#include "playerbot/playerbot.h"
#include "BlackwingLairDungeonStrategies.h"
#include "DungeonMultipliers.h"
#include "playerbot/strategy/actions/ClassicRaidActions.h"

using namespace ai;

void BlackwingLairDungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
#ifndef MANGOSBOT_ZERO
    triggers.push_back(new TriggerNode("classic raid position", NextAction::array(0, new NextAction("classic raid position", ACTION_MOVE + 5), NULL)));
    triggers.push_back(new TriggerNode("classic raid support", NextAction::array(0, new NextAction("classic raid support", ACTION_DISPEL + 4), NULL)));
#endif
    triggers.push_back(new TriggerNode("suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_HIGH + 9), NULL)));
    triggers.push_back(new TriggerNode("suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_HIGH + 8), NULL)));
    triggers.push_back(new TriggerNode("razorgore orb",
        NextAction::array(0, new NextAction("razorgore orb", 100.0f), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair flank",
        NextAction::array(0, new NextAction("set behind", 80.0f), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair support",
        NextAction::array(0, new NextAction("blackwing lair support", ACTION_DISPEL + 5), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair priority target",
        NextAction::array(0, new NextAction("blackwing lair priority target", 90.0f), NULL)));
    triggers.push_back(new TriggerNode("use hourglass sand",
        NextAction::array(0, new NextAction("use hourglass sand", ACTION_DISPEL + 1), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair safe position",
        NextAction::array(0, new NextAction("blackwing lair safe position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("corrupted healing cast",
        NextAction::array(0, new NextAction("stop corrupted healing", ACTION_EMERGENCY + 1), NULL)));
    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", 80.0f), NULL)));
}

void BlackwingLairDungeonStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
#ifndef MANGOSBOT_ZERO
    triggers.push_back(new TriggerNode("classic raid emergency", NextAction::array(0, new NextAction("classic raid position", ACTION_EMERGENCY + 2), NULL)));
#endif
    triggers.push_back(new TriggerNode("blackwing lair safe position",
        NextAction::array(0, new NextAction("blackwing lair safe position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("corrupted healing cast",
        NextAction::array(0, new NextAction("stop corrupted healing", ACTION_EMERGENCY + 1), NULL)));
}

void BlackwingLairDungeonStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
#ifndef MANGOSBOT_ZERO
    triggers.push_back(new TriggerNode("classic raid cloak", NextAction::array(0, new NextAction("classic raid cloak", ACTION_HIGH), NULL)));
#endif
    triggers.push_back(new TriggerNode("razorgore orb",
        NextAction::array(0, new NextAction("razorgore orb", 100.0f), NULL)));
    triggers.push_back(new TriggerNode("use hourglass sand",
        NextAction::array(0, new NextAction("use hourglass sand", ACTION_DISPEL + 1), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair safe position",
        NextAction::array(0, new NextAction("blackwing lair safe position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode(
        "suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_HIGH + 3), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_HIGH + 2), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", ACTION_HIGH + 4), NULL)));
}

void BlackwingLairDungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
#ifndef MANGOSBOT_ZERO
    multipliers.push_back(new PreserveClassicRaidPlan(ai));
#endif
    multipliers.push_back(new PreserveBlackwingLairPositionMultiplier(ai));
}

void BlackwingLairDungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
#ifndef MANGOSBOT_ZERO
    multipliers.push_back(new PreserveClassicRaidPlan(ai));
#endif
    multipliers.push_back(new PreserveBlackwingLairPositionMultiplier(ai));
}

void BlackwingLairDungeonStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveBlackwingLairPositionMultiplier(ai));
}

void SuppressionRoomStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_HIGH + 9), NULL)));
    triggers.push_back(new TriggerNode(
        "suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_HIGH + 8), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", 90.0f), NULL)));
}

void SuppressionRoomStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_MOVE), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_HIGH + 8), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", ACTION_MOVE + 2), NULL)));
}

void SuppressionRoomStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    // Device priorities must not disable survival, combat or follow actions.
}

void SuppressionRoomStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    // Device priorities must not disable survival, combat or follow actions.
}

// Suppression-room priorities are temporary multipliers, not permission to
// delete the player's configured avoidance strategies in all three engines.
// Native reaction avoidance remains available, including after leaving BWL.
