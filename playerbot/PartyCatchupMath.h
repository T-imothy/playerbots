#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

namespace ai
{
    inline double PartyCatchupMultiplier(double gap, double baseRate, double remainingSeconds, double cap)
    {
        if (!(gap > 0) || !(baseRate > 0)) return 1.0;
        return std::min(std::max(1.0, cap), 1.0 + gap / (baseRate * std::max(60.0, remainingSeconds)));
    }
    // Bonus stops at the leader's level threshold. Ordinary XP is never removed.
    inline uint32_t PartyCatchupBonus(uint64_t normalXP, uint64_t gap, double multiplier)
    {
        if (!normalXP || normalXP >= gap || !std::isfinite(multiplier) || multiplier <= 1.0) return 0;
        double extra = std::floor(double(normalXP) * (multiplier - 1.0));
        return uint32_t(std::min<double>(std::min<uint64_t>(gap - normalXP,
            std::numeric_limits<uint32_t>::max()), extra));
    }
}
