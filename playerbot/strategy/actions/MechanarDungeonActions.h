#pragma once
#include "DungeonActions.h"
#include "ChangeStrategyAction.h"
#include "UseItemAction.h"
#include "AttackAction.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    class PathaleonAddsAction : public AttackAction
    {
    public:
        PathaleonAddsAction(PlayerbotAI* ai) : AttackAction(ai, "pathaleon attack adds") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };

    class MechanarPositionAction : public MovementAction
    {
    public:
        MechanarPositionAction(PlayerbotAI* ai) : MovementAction(ai, "mechanar safe position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class MechanarEnableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        MechanarEnableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable mechanar strategy", "+mechanar") {}
    };

    class MechanarDisableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        MechanarDisableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable mechanar strategy", "-mechanar") {}
    };

    class NethermancerSepethreaEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        NethermancerSepethreaEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable nethermancer sepethrea fight strategy", "+nethermancer sepethrea") {}
    };

    class NethermancerSepethreaDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        NethermancerSepethreaDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable nethermancer sepethrea fight strategy", "-nethermancer sepethrea") {}
    };

    class RagingFlamesMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        RagingFlamesMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from raging flames", 20481, 20.0f) {}
    };
}
