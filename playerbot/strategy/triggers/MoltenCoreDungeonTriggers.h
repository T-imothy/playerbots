#pragma once
#include "DungeonTriggers.h"
#include "GenericTriggers.h"
#include "playerbot/strategy/actions/MoltenCoreDungeonActions.h"

namespace ai
{
    class MoltenCoreMageAoeTrigger : public Trigger
    {
    public:
        MoltenCoreMageAoeTrigger(PlayerbotAI* ai) : Trigger(ai, "molten core mage aoe", 1) {}
        bool IsActive() override { return ai->CanDoSpecificAction("molten core mage aoe", true, false); }
    };
    class MoltenCoreImpTrigger : public Trigger
    {
    public:
        MoltenCoreImpTrigger(PlayerbotAI* ai) : Trigger(ai, "molten core imp pack", 1) {}
        bool IsActive() override { return MoltenCoreImpPack(ai); }
    };

    class MoltenCoreSupportTrigger : public Trigger
    {
    public:
        MoltenCoreSupportTrigger(PlayerbotAI* ai) : Trigger(ai, "molten core support", 1) {}
        bool IsActive() override { MoltenCoreSupportAction action(ai); return action.isUseful(); }
    };

    class MoltenCorePriorityTargetTrigger : public Trigger
    {
    public:
        MoltenCorePriorityTargetTrigger(PlayerbotAI* ai) : Trigger(ai, "molten core priority target", 1) {}
        bool IsActive() override { MoltenCorePriorityTargetAction action(ai); return action.isUseful(); }
    };

    class MoltenCorePositionTrigger : public Trigger
    {
    public:
        MoltenCorePositionTrigger(PlayerbotAI* ai) : Trigger(ai, "molten core safe position", 1) {}
        bool IsActive() override { MoltenCorePositionAction action(ai); return action.isUseful(); }
    };

    class MoltenCoreEnterDungeonTrigger : public EnterDungeonTrigger
    {
    public:
        MoltenCoreEnterDungeonTrigger(PlayerbotAI* ai) : EnterDungeonTrigger(ai, "enter molten core", "molten core", 409) {}
    };

    class MoltenCoreLeaveDungeonTrigger : public LeaveDungeonTrigger
    {
    public:
        MoltenCoreLeaveDungeonTrigger(PlayerbotAI* ai) : LeaveDungeonTrigger(ai, "leave molten core", "molten core", 409) {}
    };

    class MagmadarStartFightTrigger : public StartBossFightTrigger
    {
    public:
        MagmadarStartFightTrigger(PlayerbotAI* ai) : StartBossFightTrigger(ai, "start magmadar fight", "magmadar", 11982) {}
    };

    class MagmadarEndFightTrigger : public EndBossFightTrigger
    {
    public:
        MagmadarEndFightTrigger(PlayerbotAI* ai) : EndBossFightTrigger(ai, "end magmadar fight", "magmadar", 11982) {}
    };

    class MagmadarLavaBombTrigger : public CloseToGameObjectHazardTrigger
    {
    public:
        MagmadarLavaBombTrigger(PlayerbotAI* ai) : CloseToGameObjectHazardTrigger(ai, "magmadar lava bomb", 177704, 5.0f, 60) {}
    };

    class MagmadarTooCloseTrigger : public CloseToCreatureTrigger
    {
    public:
        MagmadarTooCloseTrigger(PlayerbotAI* ai) : CloseToCreatureTrigger(ai, "magmadar too close", 11982, 30.0f) {}
    };

    class FireProtectionPotionReadyTrigger : public ItemBuffReadyTrigger
    {
    public:
        FireProtectionPotionReadyTrigger(PlayerbotAI* ai) : ItemBuffReadyTrigger(ai, "fire protection potion ready", 13457, 17543) {}
    };

    class MCRuneInSightTrigger : public Trigger
    {
    public:
        MCRuneInSightTrigger(PlayerbotAI* ai) : Trigger(ai, "mc rune in sight", 1) {}
        bool IsActive() override { MoveToMCRuneAction action(ai); return action.isUseful(); }
    };

    class MCRuneCloseTrigger : public Trigger
    {
    public:
        MCRuneCloseTrigger(PlayerbotAI* ai) : Trigger(ai, "mc rune close", 1) {}
        bool IsActive() override { return MoltenCoreRuneTarget(ai, true) != nullptr; }
    };
}
