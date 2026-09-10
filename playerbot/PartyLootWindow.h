#pragma once
#include <cstdint>

namespace ai
{
// Bounded ownership of one selected loot target, using monotonic milliseconds.
struct PartyLootWindow
{
    uint64_t target = 0, blockedTarget = 0;
    int64_t started = 0, progressed = 0, retryAfter = 0;
    float bestDistance = 0;
    bool Observe(uint64_t guid, float distance, int64_t now)
    {
        if (!guid) { target = 0; return false; }
        if (guid == blockedTarget && now < retryAfter) return false;
        if (target != guid)
        {
            target = guid; started = progressed = now; bestDistance = distance;
        }
        if (distance + 1.0f < bestDistance)
        {
            bestDistance = distance; progressed = now;
        }
        if (now - started >= 30000 || now - progressed >= 10000)
        {
            blockedTarget = guid; retryAfter = now + 30000; target = 0;
            return false;
        }
        return true;
    }
};
}
