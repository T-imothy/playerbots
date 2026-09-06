#pragma once
#include "DungeonActions.h"
#include "ChangeStrategyAction.h"
#include "AttackAction.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    class OnyxiaPositionAction : public MovementAction
    {
    public:
        OnyxiaPositionAction(PlayerbotAI* ai) : MovementAction(ai, "onyxia safe position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class OnyxiaAddsAction : public AttackAction
    {
    public:
        OnyxiaAddsAction(PlayerbotAI* ai) : AttackAction(ai, "onyxia attack adds") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };

    class OnyxiasLairEnableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        OnyxiasLairEnableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable onyxia's lair strategy", "+onyxia's lair") {}
    };

    class OnyxiasLairDisableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        OnyxiasLairDisableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable onyxia's lair strategy", "-onyxia's lair") {}
    };

    class OnyxiaEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        OnyxiaEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable onyxia fight strategy", "+onyxia") {}
    };

    class OnyxiaDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        OnyxiaDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable onyxia fight strategy", "-onyxia") {}
    };
}
