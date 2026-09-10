#pragma once

#include "playerbot/strategy/Multiplier.h"
#include "playerbot/strategy/Strategy.h"

namespace ai
{
    class LivingPartyCombatMultiplier : public Multiplier
    {
    public:
        LivingPartyCombatMultiplier(PlayerbotAI* ai) : Multiplier(ai, "living party combat") {}
        float GetValue(Action* action) override;
    };

    class LivingPartyCombatStrategy : public Strategy
    {
    public:
        LivingPartyCombatStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "living party combat"; }
    private:
        void InitCombatMultipliers(std::list<Multiplier*>& multipliers) override;
    };

    class LivingPartyHealerOffDpsStrategy : public Strategy
    {
    public:
        LivingPartyHealerOffDpsStrategy(PlayerbotAI* ai) : Strategy(ai) {}
        std::string getName() override { return "living party healer offdps"; }
        NextAction** GetDefaultCombatActions() override;
    };
}
