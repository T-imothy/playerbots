#pragma once

#include "playerbot/strategy/Multiplier.h"

class Action;

namespace ai
{
    class PreserveRotatingBeamMultiplier : public Multiplier
    {
    public:
        PreserveRotatingBeamMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve rotating beam position") {}
        float GetValue(Action* action) override;
    };
    class PreserveVashjCoreMultiplier : public Multiplier
    {
    public:
        PreserveVashjCoreMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve vashj core relay") {}
        float GetValue(Action* action) override;
    };
    class PreserveHeiganDanceMultiplier : public Multiplier
    {
    public:
        PreserveHeiganDanceMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve heigan dance") {}
        float GetValue(Action* action) override;
    };
    class PreserveNajentusSpineMultiplier : public Multiplier
    {
    public:
        PreserveNajentusSpineMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve najentus rescue") {}
        float GetValue(Action* action) override;
    };
    class PreserveLinkedBurstMultiplier : public Multiplier
    {
    public:
        PreserveLinkedBurstMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve linked burst separation") {}
        float GetValue(Action* action) override;
    };
    class PreserveAkilzonStormMultiplier : public Multiplier
    {
    public:
        PreserveAkilzonStormMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve akilzon shelter") {}
        float GetValue(Action* action) override;
    };
    class PreserveHakkarPoisonMultiplier : public Multiplier
    {
    public:
        PreserveHakkarPoisonMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve hakkar poison position") {}
        float GetValue(Action* action) override;
    };
    class PreserveOssirianCrystalMultiplier : public Multiplier
    {
    public:
        PreserveOssirianCrystalMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve ossirian crystal") {}
        float GetValue(Action* action) override;
    };
    class PreserveBossCoverMultiplier : public Multiplier
    {
    public:
        PreserveBossCoverMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve boss cover") {}
        float GetValue(Action* action) override;
    };

    class PreserveDungeonAddTargetMultiplier : public Multiplier
    {
    public:
        PreserveDungeonAddTargetMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve dungeon priority add") {}
        float GetValue(Action* action) override;
    };

    class PreserveSolarianPositionMultiplier : public Multiplier
    {
    public:
        PreserveSolarianPositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve solarian burst position") {}
        float GetValue(Action* action) override;
    };

    class PreserveMagtheridonCubeMultiplier : public Multiplier
    {
    public:
        PreserveMagtheridonCubeMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve magtheridon cube") {}
        float GetValue(Action* action) override;
    };

    class PreserveGruulSpreadMultiplier : public Multiplier
    {
    public:
        PreserveGruulSpreadMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve gruul spread") {}
        float GetValue(Action* action) override;
    };

    class PreserveKarazhanTargetMultiplier : public Multiplier
    {
    public:
        PreserveKarazhanTargetMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve karazhan target") {}
        float GetValue(Action* action) override;
    };

    class PreserveNaxxramasPositionMultiplier : public Multiplier
    {
    public:
        PreserveNaxxramasPositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve naxxramas position") {}
        float GetValue(Action* action) override;
    };

    class PreserveBlackwingLairPositionMultiplier : public Multiplier
    {
    public:
        PreserveBlackwingLairPositionMultiplier(PlayerbotAI* ai) : Multiplier(ai, "preserve blackwing lair position") {}
        float GetValue(Action* action) override;
    };

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
