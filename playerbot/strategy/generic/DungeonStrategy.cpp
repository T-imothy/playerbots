
#include "playerbot/playerbot.h"
#include "DungeonStrategy.h"
#include "DungeonMultipliers.h"

using namespace ai;

void DungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("dungeon priority add",
        NextAction::array(0, new NextAction("dungeon priority add", 61.0f), NULL)));
    triggers.push_back(new TriggerNode("unsafe encounter offense",
        NextAction::array(0, new NextAction("stop unsafe encounter offense", ACTION_EMERGENCY + 3), NULL)));
    triggers.push_back(new TriggerNode("unsafe reflected cast",
        NextAction::array(0, new NextAction("stop unsafe reflected cast", ACTION_EMERGENCY + 1), NULL)));
    triggers.push_back(new TriggerNode("solarian burst position",
        NextAction::array(0, new NextAction("solarian burst position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("solarian priority target",
        NextAction::array(0, new NextAction("solarian priority target", 61.0f), NULL)));
    triggers.push_back(new TriggerNode("magtheridon cube",
        NextAction::array(0, new NextAction("magtheridon cube", 108.0f), NULL)));
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
    triggers.push_back(new TriggerNode("solarian burst position",
        NextAction::array(0, new NextAction("solarian burst position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("magtheridon cube",
        NextAction::array(0, new NextAction("magtheridon cube", 108.0f), NULL)));
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
    triggers.push_back(new TriggerNode("unsafe encounter offense",
        NextAction::array(0, new NextAction("stop unsafe encounter offense", ACTION_EMERGENCY + 3), NULL)));
    triggers.push_back(new TriggerNode("unsafe reflected cast",
        NextAction::array(0, new NextAction("stop unsafe reflected cast", ACTION_EMERGENCY + 1), NULL)));
    triggers.push_back(new TriggerNode("solarian burst position",
        NextAction::array(0, new NextAction("solarian burst position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("magtheridon cube",
        NextAction::array(0, new NextAction("magtheridon cube", 108.0f), NULL)));
    triggers.push_back(new TriggerNode("gruul shatter spread",
        NextAction::array(0, new NextAction("gruul shatter spread", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("boss cast safe position",
        NextAction::array(0, new NextAction("boss cast safe position", 105.0f), NULL)));
    triggers.push_back(new TriggerNode("hostile ground damage",
        NextAction::array(0, new NextAction("move away from hazard", 110.0f), NULL)));
}

void DungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveDungeonAddTargetMultiplier(ai));
    multipliers.push_back(new PreserveSolarianPositionMultiplier(ai));
    multipliers.push_back(new PreserveMagtheridonCubeMultiplier(ai));
    multipliers.push_back(new PreserveGruulSpreadMultiplier(ai));
    multipliers.push_back(new PreserveBossCastPositionMultiplier(ai));
}

void DungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSolarianPositionMultiplier(ai));
    multipliers.push_back(new PreserveMagtheridonCubeMultiplier(ai));
    multipliers.push_back(new PreserveGruulSpreadMultiplier(ai));
    multipliers.push_back(new PreserveBossCastPositionMultiplier(ai));
}

void DungeonStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSolarianPositionMultiplier(ai));
}
