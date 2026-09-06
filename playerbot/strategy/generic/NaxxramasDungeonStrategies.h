#pragma once
#include "playerbot/strategy/Strategy.h"

namespace ai
{
    class NaxxramasDungeonStrategy : public Strategy
    {
    public:
        NaxxramasDungeonStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "naxxramas"; }

    private:
        void InitCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitNonCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitReactionTriggers(std::list<TriggerNode*>& triggers) override;
        void InitCombatMultipliers(std::list<Multiplier*>& multipliers) override;
        void InitNonCombatMultipliers(std::list<Multiplier*>& multipliers) override;
    };

    class FourHorsemanFightStrategy : public Strategy
    {
    public:
        FourHorsemanFightStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "four horseman"; }

    private:
        void InitCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitNonCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitDeadTriggers(std::list<TriggerNode*>& triggers) override;
    };
}
