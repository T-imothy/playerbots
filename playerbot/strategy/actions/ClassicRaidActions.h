#pragma once
#include "DungeonActions.h"
#include "playerbot/strategy/ClassicRaidPolicy.h"
#include "playerbot/strategy/Trigger.h"
#include "playerbot/strategy/Multiplier.h"

namespace ai
{
    bool ClassicRaidDamageSpell(const SpellEntry* spell);
    bool ClassicRaidOffenseAllowed(PlayerbotAI* ai, const SpellEntry* spell, Unit* target);
    bool BlackwingSuppressionChaseAllowed(PlayerbotAI* ai, Unit* target);
    struct ClassicRaidPlan
    {
        ObjectGuid boss, target;
        EncounterPosition position;
        bool emergency = false;
        bool holdDamage = false;
    };
    class ClassicRaidPlanValue : public CalculatedValue<ClassicRaidPlan>
    {
    public:
        ClassicRaidPlanValue(PlayerbotAI* ai) : CalculatedValue(ai, "classic raid plan", 2) {}
        ClassicRaidPlan Calculate() override;
        void Reset() override { CalculatedValue::Reset(); previousHorseman.Clear(); }
    private:
        ObjectGuid previousHorseman;
    };
    class ClassicRaidPositionAction : public MovementAction
    {
    public:
        ClassicRaidPositionAction(PlayerbotAI* ai) : MovementAction(ai, "classic raid position") {}
        static bool GetPlan(PlayerbotAI* ai, ClassicRaidPlan& plan);
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
    };
    class ClassicRaidTargetAction : public AttackAction
    {
    public:
        ClassicRaidTargetAction(PlayerbotAI* ai) : AttackAction(ai, "classic raid target") {}
        Unit* GetTarget() override;
        bool isUseful() override;
    };
    class ClassicRaidSupportAction : public Action
    {
    public:
        ClassicRaidSupportAction(PlayerbotAI* ai) : Action(ai, "classic raid support") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    private:
        bool Select(std::string& spell, Unit*& target);
    };
    class ClassicRaidControlAction : public MovementAction
    {
    public:
        ClassicRaidControlAction(PlayerbotAI* ai) : MovementAction(ai, "classic raid control") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool UpdateControl();
    private:
        Unit* SelectUnderstudy();
        uint32 nextControl = 0;
        ObjectGuid configuredCharm;
    };
    class ClassicRaidCloakAction : public Action
    {
    public:
        ClassicRaidCloakAction(PlayerbotAI* ai) : Action(ai, "classic raid cloak") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    };
    class ClassicRaidPauseAction : public Action
    {
    public:
        ClassicRaidPauseAction(PlayerbotAI* ai) : Action(ai, "classic raid pause", 0) {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    };
    class ClassicRaidTrigger : public Trigger
    {
    public:
        ClassicRaidTrigger(PlayerbotAI* ai, const std::string& name) : Trigger(ai, name, 1) {}
        bool IsActive() override;
    };
    class PreserveClassicRaidPlan : public Multiplier
    {
    public:
        PreserveClassicRaidPlan(PlayerbotAI* ai) : Multiplier(ai, "preserve classic raid plan") {}
        float GetValue(Action* action) override;
    };
}
