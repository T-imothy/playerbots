#include "playerbot/playerbot.h"
#include "TestStrategy.h"
#include "TestAction.h"
#include "TestTriggers.h"

using namespace ai;

#ifdef MANTECH_RAID_LAB
namespace {
class PassiveRaidObserver : public Multiplier {
public:
    explicit PassiveRaidObserver(PlayerbotAI* ai) : Multiplier(ai, "local raid observer") {}
    float GetValue(Action* action) override {
        return RaidLab::Controlled(ai->GetBot()) && action && action->getName() != "test" ? 0.0f : 1.0f;
    }
};
}
void TestStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers) {
    multipliers.push_back(new PassiveRaidObserver(ai));
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
