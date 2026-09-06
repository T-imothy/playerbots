#pragma once
#include "DungeonTriggers.h"
#include "GenericTriggers.h"
#include "playerbot/strategy/actions/NaxxramasDungeonActions.h"

namespace ai
{
    class NaxxramasPositionTrigger : public Trigger
    {
    public:
        NaxxramasPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "naxxramas safe position", 1) {}
        bool IsActive() override { NaxxramasPositionAction action(ai); return action.isUseful(); }
    };

    class NaxxramasEnterDungeonTrigger : public EnterDungeonTrigger
    {
    public:
        NaxxramasEnterDungeonTrigger(PlayerbotAI* ai) : EnterDungeonTrigger(ai, "enter naxxramas", "naxxramas", 533) {}
    };

    class NaxxramasLeaveDungeonTrigger : public LeaveDungeonTrigger
    {
    public:
        NaxxramasLeaveDungeonTrigger(PlayerbotAI* ai) : LeaveDungeonTrigger(ai, "leave naxxramas", "naxxramas", 533) {}
    };

    class FourHorsemanStartFightTrigger : public StartBossFightTrigger
    {
    public:
        // Thane Korth'azz exists in both encounter versions; Mograine (16062)
        // is replaced by Rivendare in Wrath.
        FourHorsemanStartFightTrigger(PlayerbotAI* ai) : StartBossFightTrigger(ai, "start four horseman fight", "four horseman", 16064) {}
    };

    class FourHorsemanEndFightTrigger : public EndBossFightTrigger
    {
    public:
        FourHorsemanEndFightTrigger(PlayerbotAI* ai) : EndBossFightTrigger(ai, "end four horseman fight", "four horseman", 16064) {}
    };
}
