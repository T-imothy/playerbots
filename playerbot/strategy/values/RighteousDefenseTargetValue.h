#pragma once
#include "playerbot/strategy/Value.h"

namespace ai
{
    class RighteousDefenseTargetValue : public UnitCalculatedValue
    {
    public:
        // Zero explicitly requests fresh calculation, not a saved victim pointer.
        RighteousDefenseTargetValue(PlayerbotAI* ai) : UnitCalculatedValue(ai, "righteous defense target", 0) {}
        Unit* Calculate() override;
    };
}
