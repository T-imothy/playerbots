#pragma once
#include "playerbot/strategy/Value.h"
#include "playerbot/strategy/GarrCombatPolicy.h"

namespace ai
{
    struct GarrControl
    {
        ObjectGuid boss;
        GarrAllocation allocation;
        float laneAngle = 0;
    };
    class GarrControlValue : public ManualSetValue<GarrControl>
    {
    public:
        GarrControlValue(PlayerbotAI* ai) : ManualSetValue<GarrControl>(ai, GarrControl(), "garr control") {}
    };
}
