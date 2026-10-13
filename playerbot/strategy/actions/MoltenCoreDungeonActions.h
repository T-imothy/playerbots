#pragma once
#include "DungeonActions.h"
#include "ChangeStrategyAction.h"
#include "UseItemAction.h"
#include "AttackAction.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    // Native spell checks remain authoritative for learned ranks, range, mana,
    // cooldowns, immunities and crowd control. No leader command is required.
    class MoltenCoreSupportAction : public Action
    {
    public:
        MoltenCoreSupportAction(PlayerbotAI* ai) : Action(ai, "molten core support") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    private:
        bool Select(std::string& spell, Unit*& target);
    };

    Unit* MoltenCoreAssignedTankTarget(PlayerbotAI* ai);
    std::vector<Unit*> MoltenCoreGroupTrash(PlayerbotAI* ai);
    bool PlanMoltenCoreGiants(PlayerbotAI* ai, EncounterPosition& plan);
    Unit* MoltenCorePackTankTarget(PlayerbotAI* ai);
    bool MoltenCorePackStackRequired(PlayerbotAI* ai);
    bool PlanGeddonFormation(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan);
    bool PlanMajordomoFormation(PlayerbotAI* ai, EncounterPosition& plan);
    bool PlanGolemaggFormation(PlayerbotAI* ai, EncounterPosition& plan);
    Unit* MoltenCoreRagnaros(PlayerbotAI* ai);
    bool RagnarosSameCluster(PlayerbotAI* ai, Player* member);
    bool PlanRagnarosFormation(PlayerbotAI* ai, EncounterPosition& plan);
    bool PlanMoltenCorePack(PlayerbotAI* ai, EncounterPosition& plan);

    class MoltenCorePriorityTargetAction : public AttackAction
    {
    public:
        MoltenCorePriorityTargetAction(PlayerbotAI* ai) : AttackAction(ai, "molten core priority target") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };

    class MoltenCorePositionAction : public MovementAction
    {
    public:
        MoltenCorePositionAction(PlayerbotAI* ai) : MovementAction(ai, "molten core safe position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class MoltenCoreEnableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        MoltenCoreEnableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable molten core strategy", "+molten core") {}
    };

    class MoltenCoreDisableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        MoltenCoreDisableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable molten core strategy", "-molten core") {}
    };

    class MagmadarEnableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        MagmadarEnableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable magmadar fight strategy", "+magmadar") {}
    };

    class MagmadarDisableFightStrategyAction : public ChangeAllStrategyAction
    {
    public:
        MagmadarDisableFightStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable magmadar fight strategy", "-magmadar") {}
    };

    class MagmadarMoveAwayFromLavaBombAction : public MoveAwayFromHazard
    {
    public:
        MagmadarMoveAwayFromLavaBombAction(PlayerbotAI* ai) : MoveAwayFromHazard(ai, "move away from magmadar lava bomb") {}
    };

    class MagmadarMoveAwayAction : public MoveAwayFromCreature
    {
    public:
        MagmadarMoveAwayAction(PlayerbotAI* ai) : MoveAwayFromCreature(ai, "move away from magmadar", 11982, 31.0f) {}
    };

    bool MoltenCoreDouseItemAvailable(PlayerbotAI* ai, uint32 itemId = 0);
    GameObject* MoltenCoreRuneTarget(PlayerbotAI* ai, bool close);

    class MoveToMCRuneAction : public MovementAction
    {
    public:
        MoveToMCRuneAction(PlayerbotAI* ai) : MovementAction(ai, "move to mc rune") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    };

    class DouseMCRuneAction : public UseItemIdAction
    {
    public:
        DouseMCRuneAction(PlayerbotAI* ai, const char* name, uint32 item) : UseItemIdAction(ai, name), itemId(item) { Qualify(int32(item)); }
        bool isPossible() override;
        bool isUseful() override;
        bool Execute(Event& event) override;
    protected:
        uint32 GetItemId() override { return itemId; }
    private:
        uint32 itemId;
    };

    class DouseMCRuneActionAqual : public DouseMCRuneAction
    {
    public:
        DouseMCRuneActionAqual(PlayerbotAI* ai) : DouseMCRuneAction(ai, "douse mc rune aqual", 17333) {}
    };

    class DouseMCRuneActionEternal : public DouseMCRuneAction
    {
    public:
        DouseMCRuneActionEternal(PlayerbotAI* ai) : DouseMCRuneAction(ai, "douse mc rune eternal", 22754) {}
    };
}
