#pragma once
#include <map>
#include "playerbot/strategy/Value.h"

namespace ai
{
    // Per-bot state only; inspect peers' leases but never mutate their AI state.
    struct SuppressionDuty
    {
        ObjectGuid device, anchor;
        uint32 instance = 0, generation = 0, progressAt = 0;
        float distance = 0;
        std::map<ObjectGuid, uint32> rejected;
    };
    class SuppressionDutyValue : public ManualSetValue<SuppressionDuty>
    {
    public:
        SuppressionDutyValue(PlayerbotAI* ai) : ManualSetValue<SuppressionDuty>(ai, SuppressionDuty(), "suppression duty") {}
    };
}
