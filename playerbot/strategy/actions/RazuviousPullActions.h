#pragma once
#include "MovementActions.h"
#include "playerbot/strategy/Trigger.h"

namespace ai
{
    // Only an authenticated explicit PullStrategy request may activate these
    // helpers. The original command target/deadline remains authoritative.
    bool IsRazuviousCrystalPull(PlayerbotAI* ai, Unit* target);
    bool RazuviousCrystalPullReady(PlayerbotAI* ai);
    bool ExecuteRazuviousCrystalPull(PlayerbotAI* ai);
    float RazuviousPreparationMultiplier(PlayerbotAI* ai, Action* action);

    class RazuviousPreparationAction : public MovementAction
    {
    public:
        RazuviousPreparationAction(PlayerbotAI* ai) : MovementAction(ai, "razuvious preparation") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    private:
        uint32 nextAttempt = 0;
    };
    class RazuviousPreparationTrigger : public Trigger
    {
    public:
        RazuviousPreparationTrigger(PlayerbotAI* ai) : Trigger(ai, "razuvious preparation", 1) {}
        bool IsActive() override { RazuviousPreparationAction action(ai); return action.isUseful(); }
    };
}
