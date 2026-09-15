#pragma once

#include <array>
#include <cmath>
#include <cstdint>

namespace ai
{
// No world pointers or allocations. Times are monotonic milliseconds and
// subtraction deliberately handles the core's 32-bit timer rollover.
class PursuitProgress
{
public:
    bool Observe(uint64_t target, uint32_t map, uint32_t instance, uint32_t now,
        float distance, float x, float y, float z, bool eligible)
    {
        if (!eligible || !std::isfinite(distance) || !std::isfinite(x) ||
            !std::isfinite(y) || !std::isfinite(z))
        { Reset(); return false; }
        const float dx = x - px, dy = y - py, dz = z - pz;
        if (guid != target || mapId != map || instanceId != instance ||
            uint32_t(now - last) > 5000 || distance < best - 2.0f ||
            dx * dx + dy * dy + dz * dz > 64.0f)
        {
            guid = target; mapId = map; instanceId = instance; since = now;
            best = distance; px = x; py = y; pz = z;
        }
        last = now;
        return guid && uint32_t(now - since) >= 15000;
    }
    void Reset() { guid = 0; }
private:
    uint64_t guid = 0;
    uint32_t mapId = 0, instanceId = 0, since = 0, last = 0;
    float best = 0, px = 0, py = 0, pz = 0;
};

class UnreachableTargets
{
public:
    void Add(uint64_t guid, uint32_t map, uint32_t instance, uint32_t now)
    {
        for (auto& entry : entries)
            if (entry.guid == guid && entry.map == map && entry.instance == instance)
            { entry.since = now; return; }
        entries[next++ % entries.size()] = {guid, map, instance, now};
    }
    bool Contains(uint64_t guid, uint32_t map, uint32_t instance, uint32_t now)
    {
        for (auto& entry : entries)
        {
            if (uint32_t(now - entry.since) >= 30000) entry.guid = 0;
            if (guid && entry.guid == guid && entry.map == map && entry.instance == instance) return true;
        }
        return false;
    }
private:
    struct Entry { uint64_t guid = 0; uint32_t map = 0, instance = 0, since = 0; };
    std::array<Entry, 8> entries{};
    uint32_t next = 0;
};
}
