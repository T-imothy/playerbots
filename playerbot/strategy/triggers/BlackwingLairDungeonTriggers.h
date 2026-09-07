#pragma once
#include "DungeonTriggers.h"
#include "GenericTriggers.h"
#include "playerbot/strategy/actions/EncounterSpellPolicy.h"
#include "playerbot/strategy/actions/BlackwingLairDungeonActions.h"

namespace ai
{
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
