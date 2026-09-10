#pragma once
#include "GenericActions.h"

namespace ai
{
    class TradeAction : public ChatCommandAction
    {
    public:
        TradeAction(PlayerbotAI* ai) : ChatCommandAction(ai, "trade") {}
        LivingActivity::Effects GetActivityEffects() const override {
            using namespace LivingActivity;
            return {Mask(Effect::Inventory) | Mask(Effect::Money) | Mask(Effect::Social), Lane::Managed, true};
        }
        virtual bool Execute(Event& event) override;

    private:
        bool TradeItem(const Item& item, int8 slot);

    private:
        static std::map<std::string, uint32> slots;
    };
}
