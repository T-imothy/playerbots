#pragma once
#include "DungeonActions.h"
#include "ChangeStrategyAction.h"
#include "UseItemAction.h"
#include "AttackAction.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    class KarazhanPriorityTargetAction : public AttackAction
    {
    public:
        KarazhanPriorityTargetAction(PlayerbotAI* ai) : AttackAction(ai, "karazhan priority target") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };

    class AranFlameWreathHoldAction : public Action
    {
    public:
        AranFlameWreathHoldAction(PlayerbotAI* ai) : Action(ai, "aran hold position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptMovement() const override { return true; }
        static bool IsHolding(PlayerbotAI* ai);
    };

    class KarazhanEnableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        KarazhanEnableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable karazhan strategy", "+karazhan") {}
    };

    class KarazhanDisableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        KarazhanDisableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable karazhan strategy", "-karazhan") {}
    };

    class NetherspiteEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        NetherspiteEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable netherspite fight strategy", "+netherspite") {}
    };

    class NetherspiteDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        NetherspiteDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable netherspite fight strategy", "-netherspite") {}
    };

    class VoidZoneMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        VoidZoneMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from void zone", 16697, 6.0f) {}
    };

    class NetherspitePositionAction : public MovementAction
    {
    public:
        NetherspitePositionAction(PlayerbotAI* ai) : MovementAction(ai, "netherspite beam position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class PrinceMalchezaarEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        PrinceMalchezaarEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable prince malchezaar fight strategy", "+prince malchezaar") {}
    };

    class PrinceMalchezaarDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        PrinceMalchezaarDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable prince malchezaar fight strategy", "-prince malchezaar") {}
    };

    class NetherspiteInfernalMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        NetherspiteInfernalMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from netherspite infernal", 17646, 22.0f, false, true) {}
    };

    class PrinceMalchezaarMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        PrinceMalchezaarMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from prince malchezaar", 15690, 32.0f, false, true) {}
    };
    
}
