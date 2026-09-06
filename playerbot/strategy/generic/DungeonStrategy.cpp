
#include "playerbot/playerbot.h"
#include "DungeonStrategy.h"
#include "DungeonMultipliers.h"

using namespace ai;

void DungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("gruul shatter spread",
        NextAction::array(0, new NextAction("gruul shatter spread", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("boss cast safe position",
        NextAction::array(0, new NextAction("boss cast safe position", 105.0f), NULL)));
    triggers.push_back(new TriggerNode("hostile ground damage",
        NextAction::array(0, new NextAction("move away from hazard", 110.0f), NULL)));
    triggers.push_back(new TriggerNode(
        "enter naxxramas",
        NextAction::array(0, new NextAction("enable naxxramas strategy", 100.0f), NULL)));
    // Add this combat triggers in case the bot gets summoned into the dungeon and goes straight into combat
    triggers.push_back(new TriggerNode(
        "enter onyxia's lair",
        NextAction::array(0, new NextAction("enable onyxia's lair strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter molten core",
        NextAction::array(0, new NextAction("enable molten core strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter blackwing lair",
        NextAction::array(0, new NextAction("enable blackwing lair strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter karazhan",
        NextAction::array(0, new NextAction("enable karazhan strategy", 100.0f), NULL)));
    
    triggers.push_back(new TriggerNode(
        "enter mechanar",
        NextAction::array(0, new NextAction("enable mechanar strategy", 100.0f), NULL)));
}

void DungeonStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "enter naxxramas",
        NextAction::array(0, new NextAction("enable naxxramas strategy", 100.0f), NULL)));
    triggers.push_back(new TriggerNode(
        "leave naxxramas",
        NextAction::array(0, new NextAction("disable naxxramas strategy", 100.0f), NULL)));
    triggers.push_back(new TriggerNode(
        "enter onyxia's lair",
        NextAction::array(0, new NextAction("enable onyxia's lair strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "leave onyxia's lair",
        NextAction::array(0, new NextAction("disable onyxia's lair strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter molten core",
        NextAction::array(0, new NextAction("enable molten core strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "leave molten core",
        NextAction::array(0, new NextAction("disable molten core strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter blackwing lair",
        NextAction::array(0, new NextAction("enable blackwing lair strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "leave blackwing lair",
        NextAction::array(0, new NextAction("disable blackwing lair strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter karazhan",
        NextAction::array(0, new NextAction("enable karazhan strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "leave karazhan",
        NextAction::array(0, new NextAction("disable karazhan strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enter mechanar",
        NextAction::array(0, new NextAction("enable mechanar strategy", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "leave mechanar",
        NextAction::array(0, new NextAction("disable mechanar strategy", 100.0f), NULL)));
}

void DungeonStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("gruul shatter spread",
        NextAction::array(0, new NextAction("gruul shatter spread", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("boss cast safe position",
        NextAction::array(0, new NextAction("boss cast safe position", 105.0f), NULL)));
    triggers.push_back(new TriggerNode("hostile ground damage",
        NextAction::array(0, new NextAction("move away from hazard", 110.0f), NULL)));
}

void DungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveGruulSpreadMultiplier(ai));
    multipliers.push_back(new PreserveBossCastPositionMultiplier(ai));
}

void DungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveGruulSpreadMultiplier(ai));
    multipliers.push_back(new PreserveBossCastPositionMultiplier(ai));
}
