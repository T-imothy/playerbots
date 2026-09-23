#pragma once
#include "DungeonTriggers.h"
#include "GenericTriggers.h"
#include "playerbot/strategy/actions/EncounterSpellPolicy.h"
#include "playerbot/strategy/actions/BlackwingLairDungeonActions.h"

namespace ai
{
    class BlackwingLairFlankTrigger : public Trigger
    {
    public:
        BlackwingLairFlankTrigger(PlayerbotAI* ai) : Trigger(ai, "blackwing lair flank", 1) {}
        bool IsActive() override
        {
            Unit* target = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
            float angle = 0.0f;
            return BlackwingMeleeFlankAngle(ai, target, angle) && bot->GetDistance(target, false) <= 15.0f &&
                std::fabs(std::remainder(target->GetAngle(bot) - angle, float(2 * M_PI))) > 0.25f;
        }
    };

    class BlackwingLairSupportTrigger : public Trigger
    {
    public:
        BlackwingLairSupportTrigger(PlayerbotAI* ai) : Trigger(ai, "blackwing lair support", 1) {}
        bool IsActive() override { BlackwingLairSupportAction action(ai); return action.isUseful(); }
    };
    class BlackwingLairPriorityTargetTrigger : public Trigger
    {
    public:
        BlackwingLairPriorityTargetTrigger(PlayerbotAI* ai) : Trigger(ai, "blackwing lair priority target", 1) {}
        bool IsActive() override { BlackwingLairPriorityTargetAction action(ai); return action.isUseful(); }
    };
    class HourglassSandTrigger : public Trigger
    {
    public:
        HourglassSandTrigger(PlayerbotAI* ai) : Trigger(ai, "use hourglass sand", 1) {}
        bool IsActive() override { HourglassSandAction action(ai); return action.isUseful(); }
    };

    class BlackwingLairPositionTrigger : public Trigger
    {
    public:
        BlackwingLairPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "blackwing lair safe position", 1) {}
        bool IsActive() override { BlackwingLairPositionAction action(ai); return action.isUseful(); }
    };

    class CorruptedHealingCastTrigger : public Trigger
    {
    public:
        CorruptedHealingCastTrigger(PlayerbotAI* ai) : Trigger(ai, "corrupted healing cast", 1) {}
        bool IsActive() override { return HasCorruptedHealingCast(bot); }
    };

    class BlackwingLairEnterDungeonTrigger : public EnterDungeonTrigger
    {
    public:
        BlackwingLairEnterDungeonTrigger(PlayerbotAI* ai) : EnterDungeonTrigger(ai, "enter blackwing lair", "blackwing lair", 469) {}
    };

    class BlackwingLairLeaveDungeonTrigger : public LeaveDungeonTrigger
    {
    public:
        BlackwingLairLeaveDungeonTrigger(PlayerbotAI* ai) : LeaveDungeonTrigger(ai, "leave blackwing lair", "blackwing lair", 469) {}
    };

    class SuppressionDeviceNeedStealthTrigger : public Trigger
    {
    public:
        SuppressionDeviceNeedStealthTrigger(PlayerbotAI* ai) : Trigger(ai, "suppression device need stealth", 1) {}

        bool IsActive() override
        {
            if (bot->getClass() != CLASS_ROGUE)
                return false;

            if (ai->HasAura("stealth", bot))
                return false;

            std::list<GuidPosition> gos = AI_VALUE(std::list<GuidPosition>, "go usable filter::go trapped filter::entry filter::{gos in sight,suppression devices}");
            return !gos.empty();
        }
    };

    class SuppressionDeviceInSightTrigger : public Trigger
    {
    public:
        SuppressionDeviceInSightTrigger(PlayerbotAI* ai) : Trigger(ai, "suppression device in sight", 1) {}

        bool IsActive() override
        {
            if (bot->getClass() != CLASS_ROGUE)
                return false;

            std::list<GuidPosition> gosInSight = AI_VALUE(std::list<GuidPosition>, "go usable filter::go trapped filter::entry filter::{gos in sight,suppression devices}");
            std::list<GuidPosition> gosClose = AI_VALUE(std::list<GuidPosition>, "entry filter::{gos close,suppression devices}");
            
            return !gosInSight.empty() && gosClose.empty();
        }
    };

    class SuppressionDeviceCloseTrigger : public Trigger
    {
    public:
        SuppressionDeviceCloseTrigger(PlayerbotAI* ai) : Trigger(ai, "suppression device close", 1) {}

        bool IsActive() override
        {
            if (bot->getClass() != CLASS_ROGUE)
                return false;

            std::list<GuidPosition> gos = AI_VALUE(std::list<GuidPosition>, "go usable filter::go trapped filter::entry filter::{gos close,suppression devices}");
            return !gos.empty();
        }
    };
}
