#include "playerbot/playerbot.h"
#include "TestStrategy.h"
#include "TestAction.h"
#include "TestTriggers.h"

using namespace ai;

#ifdef MANTECH_RAID_LAB
namespace {
bool MobileRaidLeaderAction(const std::string& scenario, uint32 map, const std::string& action) {
    // Explicit companion to the stationary-leader diagnostic. It exercises
    // ordinary production avoidance, without DPS, healing, forced movement,
    // immunities or encounter-state changes by the synthetic human leader.
    if (map==533 && scenario=="raidlab_533_15936_leader_mobile_cleared_room")
        return action=="heigan dance" || action=="move away from hazard" || action=="boss cast safe position";
    if(map!=409 || (scenario!="raidlab_409_11982_leader_mobile_cleared_room" &&
        scenario!="raidlab_409_11982_leader_mobile_post_lucifron_cleared_room"))return false;
    return action=="enable molten core strategy" || action=="molten core safe position" ||
        action=="move away from hazard" || action=="boss cast safe position";
}
class PassiveRaidObserver : public Multiplier {
public:
    PassiveRaidObserver(PlayerbotAI* ai, const std::string& scenario) : Multiplier(ai, "local raid observer"), scenario(scenario) {}
    float GetValue(Action* action) override {
        Player* bot=ai->GetBot();
        if(!RaidLab::Controlled(bot) || !action || action->getName()=="test")return 1.0f;
        return bot->IsInCombat() && !bot->IsGameMaster() &&
            MobileRaidLeaderAction(scenario,bot->GetMapId(),action->getName()) ? 1.0f : 0.0f;
    }
private:
    std::string scenario;
};
}
void TestStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers) {
    multipliers.push_back(new PassiveRaidObserver(ai,qualifier));
}
#endif

void TestStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "test ready",
        NextAction::array(0, new NextAction("test", 100.0f), NULL)));
}

void TestStrategy::OnStrategyRemoved(BotState state)
{
    AiObjectContext* context = ai->GetAiObjectContext();
    Action* action = context->GetAction("test");

    if (action)
    {
        action->Reset();
    };
}
