#pragma once
#include "DungeonActions.h"
#include "AttackAction.h"

namespace ai
{
    class SolarianPositionAction : public MovementAction
    {
    public:
        SolarianPositionAction(PlayerbotAI* ai) : MovementAction(ai, "solarian burst position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class SolarianPriorityTargetAction : public AttackAction
    {
    public:
        SolarianPriorityTargetAction(PlayerbotAI* ai) : AttackAction(ai, "solarian priority target") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };
}
