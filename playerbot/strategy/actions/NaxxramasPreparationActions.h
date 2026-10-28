#pragma once
#include "MovementActions.h"
#include "playerbot/strategy/Trigger.h"
#include "playerbot/strategy/Multiplier.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    bool NaxxramasGothikPullReady(PlayerbotAI* ai);
    bool NaxxramasGothikPreparationPlan(PlayerbotAI* ai, EncounterPosition& plan, bool& groupReady);
    class NaxxramasGothikPrepareAction : public MovementAction
    {
    public:
        NaxxramasGothikPrepareAction(PlayerbotAI* ai) : MovementAction(ai, "prepare gothik sides") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override { return false; }
    };
    class NaxxramasGothikPrepareTrigger : public Trigger
    {
    public:
        NaxxramasGothikPrepareTrigger(PlayerbotAI* ai) : Trigger(ai, "prepare gothik sides", 1) {}
        bool IsActive() override { NaxxramasGothikPrepareAction action(ai); return action.isUseful(); }
    };
    class PreserveNaxxramasPreparation : public Multiplier
    {
    public:
        PreserveNaxxramasPreparation(PlayerbotAI* ai) : Multiplier(ai, "preserve naxxramas preparation") {}
        float GetValue(Action* action) override;
    };
}
