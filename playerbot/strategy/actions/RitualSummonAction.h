#pragma once
#include "MovementActions.h"
#include "playerbot/strategy/values/RitualSummonValue.h"

namespace ai
{
    bool IsNativeSummoningRitual(uint32 spell);
    bool CanParticipateInRitual(Player* player);
    bool HasActiveSummoningRitual(Player* player);
    GameObject* FindOwnedSummoningPortal(Player* player);

    class HoldSummoningRitualAction : public Action
    {
    public:
        HoldSummoningRitualAction(PlayerbotAI* ai) : Action(ai, "hold summoning ritual") {}
        bool isUseful() override { return HasActiveSummoningRitual(bot); }
        bool Execute(Event&) override
        {
            if (!isUseful()) return false;
            SetDuration(500);
            return true;
        }
    };

    class AssistSummoningRitualAction : public MovementAction
    {
    public:
        AssistSummoningRitualAction(PlayerbotAI* ai) : MovementAction(ai, "assist summoning ritual") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool isPossible() override;
        GameObject* GetRitual();
        bool UseRitual(GameObject* ritual);
    };

    class ContinueRitualSummonAction : public MovementAction
    {
    public:
        ContinueRitualSummonAction(PlayerbotAI* ai) : MovementAction(ai, "continue ritual summon") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        static uint32 RequiredHelpers(Player* bot);
        static bool Start(PlayerbotAI* ai, Player* requester, Player* target);
    };
}
