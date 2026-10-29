#pragma once
#include <map>
#include "DungeonActions.h"
#include "AttackAction.h"
#include "ChangeStrategyAction.h"
#include "MovementActions.h"
#include "UseItemAction.h"
#include "EncounterSpellPolicy.h"
#include "BlackwingMovementSafety.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"
#include "playerbot/strategy/values/GuidPositionValues.h"

namespace ai
{
    // One action instance owns retry state for its bot; no shared mutable raid state.
    class BlackwingStopUnsafeMovementAction : public Action
    {
    public:
        BlackwingStopUnsafeMovementAction(PlayerbotAI* ai) : Action(ai, "blackwing stop unsafe movement", 0) {}
        bool isUseful() override { return BlackwingActiveMovementUnsafe(ai); }
        bool Execute(Event& event) override { return StopUnsafeBlackwingMovement(ai); }
        bool ShouldReactionInterruptCast() const override { return false; }
        bool ShouldReactionInterruptMovement() const override { return false; }
    };

    class RazorgoreOrbAction : public MovementAction
    {
    public:
        RazorgoreOrbAction(PlayerbotAI* ai) : MovementAction(ai, "razorgore orb") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool UpdateControl();
    private:
        GameObject* SelectOrb();
        uint32 lastControlUpdate = 0;
        ObjectGuid controlledGuid;
        ObjectGuid movingToEgg;
        uint32 eggMoveStarted = 0;
        ObjectGuid castEgg;
        unsigned castAttempts = 0;
        std::map<ObjectGuid, uint32> failedEggs;
    };

    class BlackwingLairSupportAction : public Action
    {
    public:
        BlackwingLairSupportAction(PlayerbotAI* ai) : Action(ai, "blackwing lair support") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    private:
        bool Select(std::string& spell, Unit*& target);
    };

    class BlackwingLairPriorityTargetAction : public AttackAction
    {
    public:
        BlackwingLairPriorityTargetAction(PlayerbotAI* ai) : AttackAction(ai, "blackwing lair priority target") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };

    const uint32 SPELL_DISARM_TRAP = 1842;

    class HourglassSandAction : public UseItemIdAction
    {
    public:
        HourglassSandAction(PlayerbotAI* ai) : UseItemIdAction(ai, "use hourglass sand") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override { return false; }
    protected:
        uint32 GetItemId() override { return 19183; }
        Unit* GetTarget() override { return bot; }
    };

    class BlackwingLairPositionAction : public MovementAction
    {
    public:
        BlackwingLairPositionAction(PlayerbotAI* ai) : MovementAction(ai, "blackwing lair safe position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class StopCorruptedHealingAction : public Action
    {
    public:
        StopCorruptedHealingAction(PlayerbotAI* ai) : Action(ai, "stop corrupted healing", 0) {}
        bool isUseful() override { return HasCorruptedHealingCast(bot); }
        bool Execute(Event& event) override { return InterruptCorruptedHealingCast(bot); }
        // Action's default reaction flags are false: only Execute may cancel
        // a freshly checked harmful cast, not movement or an unrelated spell.
    };

    class BlackwingLairEnableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        BlackwingLairEnableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "enable blackwing lair strategy", "+blackwing lair") {}
    };

    class BlackwingLairDisableDungeonStrategyAction : public ChangeAllStrategyAction
    {
    public:
        BlackwingLairDisableDungeonStrategyAction(PlayerbotAI* ai) : ChangeAllStrategyAction(ai, "disable blackwing lair strategy", "-blackwing lair") {}
    };

    // Shared assignment: triggers and execution must agree on the same active device.
    GameObject* AssignedSuppressionDevice(PlayerbotAI* ai);
    bool SuppressionDutyOwnsMovement(PlayerbotAI* ai);
    bool SuppressionDeviceInCastRange(PlayerbotAI* ai, GameObject* device);

    class MoveToSuppressionDeviceAction : public MovementAction
    {
    public:
        MoveToSuppressionDeviceAction(PlayerbotAI* ai) : MovementAction(ai, "move to suppression device") {}
        bool ShouldReactionInterruptCast() const override { return false; }
        bool ShouldReactionInterruptMovement() const override { return false; }
        bool Execute(Event& event) override;
        bool isPossible() override { return ai->CanMove(); }
        bool isUseful() override;
    };

    class StealthForSuppressionDeviceAction : public Action
    {
    public:
        StealthForSuppressionDeviceAction(PlayerbotAI* ai) : Action(ai, "stealth for suppression device") {}
        bool Execute(Event& event) override;
        bool isPossible() override { return bot->getClass() == CLASS_ROGUE; }
        bool isUseful() override;
    };

    class DisarmSuppressionDeviceAction : public Action
    {
    public:
        DisarmSuppressionDeviceAction(PlayerbotAI* ai) : Action(ai, "disarm suppression device") {}
        bool Execute(Event& event) override;
        bool isPossible() override { return bot->getClass() == CLASS_ROGUE && bot->HasSpell(SPELL_DISARM_TRAP); }
        bool isUseful() override;
    };

    // Preserve the legacy action name, but use the learned native spell too.
    class DeactivateSuppressionDeviceAction : public DisarmSuppressionDeviceAction
    {
    public:
        DeactivateSuppressionDeviceAction(PlayerbotAI* ai) : DisarmSuppressionDeviceAction(ai) {}
    };
}
