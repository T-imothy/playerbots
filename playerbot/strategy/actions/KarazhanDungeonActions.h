#pragma once
#include "DungeonActions.h"
#include "playerbot/strategy/generic/KarazhanDungeonStrategies.h"
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

    class ShadeOfAranEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        ShadeOfAranEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable shade of aran fight strategy", "+shade of aran") {}
    };

    class ShadeOfAranDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        ShadeOfAranDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable shade of aran fight strategy", "-shade of aran") {}
    };

    class ShadeOfAranMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        ShadeOfAranMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from shade of aran", 16524, 22.0f, false, false) {}
    };

    class ShadeOfAranFirePhaseStartedAction : public Action
    {
    public:
        ShadeOfAranFirePhaseStartedAction(PlayerbotAI* ai) : Action(ai, "start aran fire phase") {}
        bool Execute(Event& event) override;
    };

    class ShadeOfAranFrostPhaseStartedAction : public Action
    {
    public:
        ShadeOfAranFrostPhaseStartedAction(PlayerbotAI* ai) : Action(ai, "start aran frost phase") {}
        bool Execute(Event& event) override;
    };

    class ShadeOfAranArcanePhaseStartedAction : public Action
    {
    public:
        ShadeOfAranArcanePhaseStartedAction(PlayerbotAI* ai) : Action(ai, "start aran arcane phase") {}
        bool Execute(Event& event) override;
    };

    class ShadeOfAranArcanePhaseEndedAction : public Action
    {
    public:
        ShadeOfAranArcanePhaseEndedAction(PlayerbotAI* ai) : Action(ai, "end aran arcane phase") {}
        bool Execute(Event& event) override;
    };

    class ShadeOfAranElementalsAction : public Action
    {
    public:
        ShadeOfAranElementalsAction(PlayerbotAI* ai) : Action(ai, "start aran elementals") {}
        bool Execute(Event& event) override;
    };

    class BigBadWolfEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        BigBadWolfEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable big bad wolf fight strategy", "+big bad wolf") {}
    };

    class BigBadWolfDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        BigBadWolfDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable big bad wolf fight strategy", "-big bad wolf") {}
    };

    class BigBadWolfMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        BigBadWolfMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from big bad wolf", 17521, 28.0f, true) {}
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

        bool Execute(Event& event) override;
    };

    class PrinceMalchezaarMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        PrinceMalchezaarMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from prince malchezaar", 15690, 32.0f, false, true) {}
    };
    


}
