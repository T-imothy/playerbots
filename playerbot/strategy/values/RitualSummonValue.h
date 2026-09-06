#pragma once
#include "playerbot/strategy/Value.h"

namespace ai
{
    struct RitualSummonRequest
    {
        ObjectGuid target, requester;
        uint32 map = 0, instance = 0;
        time_t expires = 0;
    };

    // Wrath creates a reusable portal before the selected-player ritual. This
    // bounded request preserves that second step, not a teleport destination.
    class RitualSummonRequestValue : public ManualSetValue<RitualSummonRequest>
    {
    public:
        RitualSummonRequestValue(PlayerbotAI* ai) : ManualSetValue(ai, RitualSummonRequest{}, "ritual summon request") {}
        void Reset() override { Set(RitualSummonRequest{}); }
    };
}
