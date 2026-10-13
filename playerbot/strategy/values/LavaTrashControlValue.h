#pragma once
#include "playerbot/strategy/Value.h"
#include "playerbot/strategy/LavaTrashCombatPolicy.h"

namespace ai
{
    struct LavaTrashControl
    {
        LavaTrashAllocation allocation;
        // Native owning-map group state. Mirrored to eligible member contexts
        // so losing a controller cannot erase the release ledger mid-pull.
        uint32 groupId = 0, map = 0, instance = 0;
        uint32 observedAt = 0;
        std::vector<ObjectGuid> observedElementals, observedPriorities;
    };
    class LavaTrashControlValue : public ManualSetValue<LavaTrashControl>
    {
    public:
        LavaTrashControlValue(PlayerbotAI* ai) : ManualSetValue<LavaTrashControl>(ai, LavaTrashControl(), "lava trash control") {}
        void Reset() override {} // The encounter adapter clears it when the group leaves combat.
    };
}
