
#include "playerbot/playerbot.h"
#include "DungeonStrategy.h"
#include "DungeonMultipliers.h"

using namespace ai;

void DungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("fight own inner demon",
        NextAction::array(0, new NextAction("fight own inner demon", 63.0f), NULL)));
    triggers.push_back(new TriggerNode("avoid rotating beam",
        NextAction::array(0, new NextAction("avoid rotating beam", 108.0f), NULL)));
    triggers.push_back(new TriggerNode("vashj core relay",
        NextAction::array(0, new NextAction("vashj core relay", 104.0f), NULL)));
    triggers.push_back(new TriggerNode("eadric face away",
        NextAction::array(0, new NextAction("eadric face away", 109.0f), NULL)));
    triggers.push_back(new TriggerNode("moam mana control",
        NextAction::array(0, new NextAction("moam mana control", 54.0f), NULL)));
    triggers.push_back(new TriggerNode("viscidus frost",
        NextAction::array(0, new NextAction("viscidus frost", 55.0f), NULL)));
    triggers.push_back(new TriggerNode("heigan dance",
        NextAction::array(0, new NextAction("heigan dance", 108.0f), NULL)));
    triggers.push_back(new TriggerNode("najentus spine rescue",
        NextAction::array(0, new NextAction("najentus spine rescue", 106.0f), NULL)));
    triggers.push_back(new TriggerNode("najentus break shield",
        NextAction::array(0, new NextAction("najentus break shield", 105.0f), NULL)));
    triggers.push_back(new TriggerNode("archimonde tears",
        NextAction::array(0, new NextAction("archimonde tears", 112.0f), NULL)));
    triggers.push_back(new TriggerNode("separate linked burst",
        NextAction::array(0, new NextAction("separate linked burst", 104.0f), NULL)));
    triggers.push_back(new TriggerNode("akilzon storm shelter",
        NextAction::array(0, new NextAction("akilzon storm shelter", 107.0f), NULL)));
    triggers.push_back(new TriggerNode("move against cold",
        NextAction::array(0, new NextAction("move against cold", 103.0f), NULL)));
    triggers.push_back(new TriggerNode("hakkar acquire poison",
        NextAction::array(0, new NextAction("hakkar acquire poison", 69.0f), NULL)));
    triggers.push_back(new TriggerNode("ossirian crystal",
        NextAction::array(0, new NextAction("ossirian crystal", 104.0f), NULL)));
    triggers.push_back(new TriggerNode("boss seek cover",
        NextAction::array(0, new NextAction("boss seek cover", 106.0f), NULL)));
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
    triggers.push_back(new TriggerNode("avoid rotating beam",
        NextAction::array(0, new NextAction("avoid rotating beam", 108.0f), NULL)));
    triggers.push_back(new TriggerNode("vashj core relay",
        NextAction::array(0, new NextAction("vashj core relay", 104.0f), NULL)));
    triggers.push_back(new TriggerNode("eadric face away",
        NextAction::array(0, new NextAction("eadric face away", 109.0f), NULL)));
    triggers.push_back(new TriggerNode("heigan dance",
        NextAction::array(0, new NextAction("heigan dance", 108.0f), NULL)));
    triggers.push_back(new TriggerNode("najentus spine rescue",
        NextAction::array(0, new NextAction("najentus spine rescue", 106.0f), NULL)));
    triggers.push_back(new TriggerNode("najentus break shield",
        NextAction::array(0, new NextAction("najentus break shield", 105.0f), NULL)));
    triggers.push_back(new TriggerNode("archimonde tears",
        NextAction::array(0, new NextAction("archimonde tears", 112.0f), NULL)));
    triggers.push_back(new TriggerNode("separate linked burst",
        NextAction::array(0, new NextAction("separate linked burst", 104.0f), NULL)));
    triggers.push_back(new TriggerNode("akilzon storm shelter",
        NextAction::array(0, new NextAction("akilzon storm shelter", 107.0f), NULL)));
    triggers.push_back(new TriggerNode("move against cold",
        NextAction::array(0, new NextAction("move against cold", 103.0f), NULL)));
    triggers.push_back(new TriggerNode("ossirian crystal",
        NextAction::array(0, new NextAction("ossirian crystal", 104.0f), NULL)));
    triggers.push_back(new TriggerNode("boss seek cover",
        NextAction::array(0, new NextAction("boss seek cover", 106.0f), NULL)));
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
    multipliers.push_back(new PreserveRotatingBeamMultiplier(ai));
    multipliers.push_back(new PreserveVashjCoreMultiplier(ai));
    multipliers.push_back(new PreserveEadricFacingMultiplier(ai));
    multipliers.push_back(new PreserveHeiganDanceMultiplier(ai));
    multipliers.push_back(new PreserveNajentusSpineMultiplier(ai));
    multipliers.push_back(new PreserveLinkedBurstMultiplier(ai));
    multipliers.push_back(new PreserveAkilzonStormMultiplier(ai));
    multipliers.push_back(new PreserveHakkarPoisonMultiplier(ai));
    multipliers.push_back(new PreserveOssirianCrystalMultiplier(ai));
    multipliers.push_back(new PreserveBossCoverMultiplier(ai));
    multipliers.push_back(new PreserveDungeonAddTargetMultiplier(ai));
    multipliers.push_back(new PreserveSolarianPositionMultiplier(ai));
    multipliers.push_back(new PreserveMagtheridonCubeMultiplier(ai));
    multipliers.push_back(new PreserveGruulSpreadMultiplier(ai));
    multipliers.push_back(new PreserveBossCastPositionMultiplier(ai));
}

void DungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveRotatingBeamMultiplier(ai));
    multipliers.push_back(new PreserveVashjCoreMultiplier(ai));
    multipliers.push_back(new PreserveEadricFacingMultiplier(ai));
    multipliers.push_back(new PreserveHeiganDanceMultiplier(ai));
    multipliers.push_back(new PreserveNajentusSpineMultiplier(ai));
    multipliers.push_back(new PreserveLinkedBurstMultiplier(ai));
    multipliers.push_back(new PreserveAkilzonStormMultiplier(ai));
    multipliers.push_back(new PreserveOssirianCrystalMultiplier(ai));
    multipliers.push_back(new PreserveBossCoverMultiplier(ai));
    multipliers.push_back(new PreserveSolarianPositionMultiplier(ai));
    multipliers.push_back(new PreserveMagtheridonCubeMultiplier(ai));
    multipliers.push_back(new PreserveGruulSpreadMultiplier(ai));
    multipliers.push_back(new PreserveBossCastPositionMultiplier(ai));
}

void DungeonStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSolarianPositionMultiplier(ai));
}
