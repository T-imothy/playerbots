#pragma once
#include "playerbot/strategy/Action.h"
#include "playerbot/strategy/Trigger.h"
#include "EncounterSpellPolicy.h"

namespace ai
{
    class UnsafeReflectedCastTrigger : public Trigger
    {
    public:
        UnsafeReflectedCastTrigger(PlayerbotAI* ai) : Trigger(ai, "unsafe reflected cast", 1) {}
        bool IsActive() override { return HasUnsafeReflectedCast(bot); }
    };

    class StopUnsafeReflectedCastAction : public Action
    {
    public:
        StopUnsafeReflectedCastAction(PlayerbotAI* ai) : Action(ai, "stop unsafe reflected cast", 0) {}
        bool isUseful() override { return HasUnsafeReflectedCast(bot); }
        bool Execute(Event&) override { return InterruptUnsafeReflectedCast(bot); }
    };
}
