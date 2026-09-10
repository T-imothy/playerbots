#pragma once
#include <cstdint>

// Preserve the legacy 0..100 slot distribution. A full rotation takes 20m12s,
// with no dependency on changing load, so idle bots cannot retain the same
// inactive slot for hours. Priority bypasses and the active cutoff remain owned
// by AllowActive; this helper does not enable extra bots or choose destinations.
inline uint32_t LivingActivitySlot(uint32_t fixedSlot, uint64_t elapsedSeconds)
{
    return uint32_t((fixedSlot + elapsedSeconds / 12) % 101);
}
