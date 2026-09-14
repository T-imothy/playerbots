#pragma once
#include "playerbot/strategy/Strategy.h"
namespace ai
{
    class TurtleClassStrategy : public Strategy
    {
    public:
        TurtleClassStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "turtle classes"; }
    private:
        void InitCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitNonCombatTriggers(std::list<TriggerNode*>& triggers) override;
    };
}
