#pragma once
#include "playerbot/strategy/Trigger.h"
#include "playerbot/strategy/actions/RitualSummonAction.h"

namespace ai
{
    class HoldSummoningRitualTrigger : public Trigger
    {
    public:
        HoldSummoningRitualTrigger(PlayerbotAI* ai) : Trigger(ai, "hold summoning ritual", 1) {}
        bool IsActive() override { return HasActiveSummoningRitual(bot); }
    };

    class AssistSummoningRitualTrigger : public Trigger
    {
    public:
        AssistSummoningRitualTrigger(PlayerbotAI* ai) : Trigger(ai, "assist summoning ritual", 2) {}
        bool IsActive() override { AssistSummoningRitualAction action(ai); return action.isUseful(); }
    };

    class ContinueRitualSummonTrigger : public Trigger
    {
    public:
        ContinueRitualSummonTrigger(PlayerbotAI* ai) : Trigger(ai, "continue ritual summon", 2) {}
        bool IsActive() override { ContinueRitualSummonAction action(ai); return action.isUseful(); }
    };
}
