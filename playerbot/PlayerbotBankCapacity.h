#pragma once
#include <cstdint>

namespace ai { namespace PlayerbotBankCapacity
{
    // Evaluate the inventory AFTER a proposed acquisition. Keeping existing
    // gear at the limit and acquiring beyond it must be different decisions.
    inline bool Fits(uint32_t capacity, uint32_t used, uint32_t offItems,
        uint32_t minimumFree, uint32_t maximumPercent, uint32_t limit, bool acquiring)
    {
        const uint64_t projectedUsed = uint64_t(used) + (acquiring ? 1 : 0);
        const uint64_t projectedOffItems = uint64_t(offItems) + (acquiring ? 1 : 0);
        return capacity && projectedUsed <= capacity && capacity - projectedUsed >= minimumFree &&
            projectedUsed * 100 / capacity < maximumPercent && projectedOffItems <= limit;
    }
}}
