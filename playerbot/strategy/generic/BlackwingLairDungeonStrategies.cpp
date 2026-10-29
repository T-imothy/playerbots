#include "playerbot/playerbot.h"
#include "BlackwingLairDungeonStrategies.h"
#include "DungeonMultipliers.h"
#include "playerbot/strategy/actions/BlackwingLairDungeonActions.h"

using namespace ai;

namespace
{
    class PreserveSuppressionDutyMovementMultiplier : public Multiplier
    {
    public:
        PreserveSuppressionDutyMovementMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve suppression duty movement") {}
        float GetValue(ai::Action* action) override
        {
            if (!action || !SuppressionDutyOwnsMovement(ai)) return 1.0f;
            const std::string name = action->getName();
            // Do not suppress attacks, healing, defenses, casts or escapes.
            // Only idle regrouping must not replace an already checked duty path.
            return name == "follow" || name == "follow master" || name == "move random" ? 0.0f : 1.0f;
        }
    };
}

void BlackwingLairDungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_MOVE + 9), NULL)));
    triggers.push_back(new TriggerNode("suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_MOVE + 8), NULL)));
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
    triggers.push_back(new TriggerNode("blackwing unsafe movement",
        NextAction::array(0, new NextAction("blackwing stop unsafe movement", ACTION_EMERGENCY + 3), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair safe position",
        NextAction::array(0, new NextAction("blackwing lair safe position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode("corrupted healing cast",
        NextAction::array(0, new NextAction("stop corrupted healing", ACTION_EMERGENCY + 1), NULL)));
}

void BlackwingLairDungeonStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("razorgore orb",
        NextAction::array(0, new NextAction("razorgore orb", 100.0f), NULL)));
    triggers.push_back(new TriggerNode("use hourglass sand",
        NextAction::array(0, new NextAction("use hourglass sand", ACTION_DISPEL + 1), NULL)));
    triggers.push_back(new TriggerNode("blackwing lair safe position",
        NextAction::array(0, new NextAction("blackwing lair safe position", ACTION_EMERGENCY + 2), NULL)));
    triggers.push_back(new TriggerNode(
        "suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_MOVE + 9), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_MOVE + 8), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", ACTION_HIGH + 4), NULL)));
}

void BlackwingLairDungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveBlackwingLairPositionMultiplier(ai));
}

void BlackwingLairDungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSuppressionDutyMovementMultiplier(ai));
    multipliers.push_back(new PreserveBlackwingLairPositionMultiplier(ai));
}

void BlackwingLairDungeonStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSuppressionDutyMovementMultiplier(ai));
    multipliers.push_back(new PreserveBlackwingLairPositionMultiplier(ai));
}

void SuppressionRoomStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_MOVE + 9), NULL)));
    triggers.push_back(new TriggerNode(
        "suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_MOVE + 8), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", 90.0f), NULL)));
}

void SuppressionRoomStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "suppression device need stealth",
        NextAction::array(0, new NextAction("stealth for suppression device", ACTION_MOVE + 9), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device in sight",
        NextAction::array(0, new NextAction("move to suppression device", ACTION_MOVE + 8), NULL)));

    triggers.push_back(new TriggerNode(
        "suppression device close",
        NextAction::array(0, new NextAction("disarm suppression device", ACTION_MOVE + 2), NULL)));
}

void SuppressionRoomStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSuppressionDutyMovementMultiplier(ai));
    // Device priorities must not disable survival, combat or follow actions.
}

void SuppressionRoomStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveSuppressionDutyMovementMultiplier(ai));
    // Device priorities must not disable survival, combat or follow actions.
}

// Suppression-room priorities are temporary multipliers, not permission to
// delete the player's configured avoidance strategies in all three engines.
// Native reaction avoidance remains available, including after leaving BWL.
