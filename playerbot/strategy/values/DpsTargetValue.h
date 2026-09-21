#pragma once
#include <set>
#include "playerbot/strategy/Value.h"
#include "RtiTargetValue.h"
#include "TargetValue.h"

namespace ai
{
    class DpsTargetValue : public RtiTargetValue
	{
	public:
        DpsTargetValue(PlayerbotAI* ai, std::string type = "rti", std::string name = "dps target") : RtiTargetValue(ai, type, name) {}

    public:
        ObjectGuid Calculate() override;
    private:
        // Only GUIDs still engaged in this fight survive the next calculation.
        std::set<ObjectGuid> observedHealers;
    };

    class DpsAoeTargetValue : public RtiTargetValue
    {
    public:
        DpsAoeTargetValue(PlayerbotAI* ai, std::string type = "rti", std::string name = "dps aoe target") : RtiTargetValue(ai, type, name) {}

    public:
        ObjectGuid Calculate() override;
    };
}
