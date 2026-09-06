#pragma once
#include "DungeonTriggers.h"
#include "playerbot/strategy/actions/OnyxiasLairDungeonActions.h"

namespace ai
{
    class OnyxiaPositionTrigger : public Trigger
    {
    public:
        OnyxiaPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "onyxia safe position", 1) {}
        bool IsActive() override { OnyxiaPositionAction action(ai); return action.isUseful(); }
    };

    class OnyxiaAddsTrigger : public Trigger
    {
    public:
        OnyxiaAddsTrigger(PlayerbotAI* ai) : Trigger(ai, "onyxia attack adds", 1) {}
        bool IsActive() override { OnyxiaAddsAction action(ai); return action.isUseful(); }
    };

    class OnyxiasLairEnterDungeonTrigger : public EnterDungeonTrigger
    {
    public:
        OnyxiasLairEnterDungeonTrigger(PlayerbotAI* ai) : EnterDungeonTrigger(ai, "enter onyxia's lair", "onyxia's lair", 249) {}
    };

    class OnyxiasLairLeaveDungeonTrigger : public LeaveDungeonTrigger
    {
    public:
        OnyxiasLairLeaveDungeonTrigger(PlayerbotAI* ai) : LeaveDungeonTrigger(ai, "leave onyxia's lair", "onyxia's lair", 249) {}
    };

    class OnyxiaStartFightTrigger : public StartBossFightTrigger
    {
    public:
        OnyxiaStartFightTrigger(PlayerbotAI* ai) : StartBossFightTrigger(ai, "start onyxia fight", "onyxia", 10184) {}
    };

    class OnyxiaEndFightTrigger : public EndBossFightTrigger
    {
    public:
        OnyxiaEndFightTrigger(PlayerbotAI* ai) : EndBossFightTrigger(ai, "end onyxia fight", "onyxia", 10184) {}
    };
}
