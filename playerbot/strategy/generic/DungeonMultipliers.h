#pragma once

#include "playerbot/strategy/Multiplier.h"

class Action;

namespace ai
{
    class PreserveBossCastPositionMultiplier : public Multiplier
    {
    public:
        PreserveBossCastPositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve boss cast position") {}
        float GetValue(Action* action) override;
    };

    class PreserveAranFlameWreathMultiplier : public Multiplier
    {
    public:
        PreserveAranFlameWreathMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve aran flame wreath") {}
        float GetValue(Action* action) override;
    };
    class PreserveMechanarPositionMultiplier : public Multiplier
    {
    public:
        PreserveMechanarPositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve mechanar safe position") {}
        float GetValue(Action* action) override;
    };
    class PreserveMoltenCorePositionMultiplier : public Multiplier
    {
    public:
        PreserveMoltenCorePositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve molten core safe position") {}
        float GetValue(Action* action) override;
    };

    class PreserveOnyxiaPositionMultiplier : public Multiplier
    {
    public:
        PreserveOnyxiaPositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve onyxia safe position") {}
        float GetValue(Action* action) override;
    };

    class PreserveNetherspitePositionMultiplier : public Multiplier
    {
    public:
        PreserveNetherspitePositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve netherspite beam position") {}
        float GetValue(Action* action) override;
    };

    class PreventMoveAwayFromCreatureOnReachToCastMultiplier : public Multiplier
    {
    public:
        PreventMoveAwayFromCreatureOnReachToCastMultiplier(PlayerbotAI* ai) : Multiplier(ai, "cast spell after reach") {}

    public:
        virtual float GetValue(Action* action) override;
    };
}
