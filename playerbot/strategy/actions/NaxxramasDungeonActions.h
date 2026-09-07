#pragma once
#include "DungeonActions.h"
#include "ChangeStrategyAction.h"
#include "UseItemAction.h"
#include "MovementActions.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    class NaxxramasPositionAction : public MovementAction
    {
    public:
        NaxxramasPositionAction(PlayerbotAI* ai) : MovementAction(ai, "naxxramas safe position") {}
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptMovement() const override { return true; }
    };

    class NaxxramasEnableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        NaxxramasEnableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable naxxramas strategy", "+naxxramas") {}
    };

    class NaxxramasDisableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        NaxxramasDisableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable naxxramas strategy", "-naxxramas") {}
    };

    class FourHorsemanEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        FourHorsemanEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable four horseman fight strategy", "+four horseman") {}
    };

    class FourHorsemanDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        FourHorsemanDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable four horseman fight strategy", "-four horseman") {}
    };
}
