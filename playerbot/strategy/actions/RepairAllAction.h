#pragma once
#include "GenericActions.h"

namespace ai
{
    class RepairAllAction : public ChatCommandAction
    {
    public:
        RepairAllAction(PlayerbotAI* ai) : ChatCommandAction(ai, "repair") {}
        LivingActivity::Effects GetActivityEffects() const override {
            using namespace LivingActivity;
            return {Mask(Effect::Inventory) | Mask(Effect::Money) | Mask(Effect::Social), Lane::Managed, true};
        }
        virtual bool Execute(Event& event) override;
    };
}
