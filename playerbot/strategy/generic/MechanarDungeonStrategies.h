#pragma once
#include "playerbot/strategy/Strategy.h"

namespace ai
{
    class MechanarDungeonStrategy : public Strategy
    {
    public:
        MechanarDungeonStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "mechanar"; }

    private:
        void InitCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitReactionTriggers(std::list<TriggerNode*>& triggers) override;
        void InitCombatMultipliers(std::list<Multiplier*>& multipliers) override;
    };

    class NethermancerSepethreaFightStrategy : public Strategy
    {
    public:
        NethermancerSepethreaFightStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "nethermancer sepethrea"; }

    private:
        void InitCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitNonCombatTriggers(std::list<TriggerNode*>& triggers) override;
        void InitDeadTriggers(std::list<TriggerNode*>& triggers) override;
    };
}
