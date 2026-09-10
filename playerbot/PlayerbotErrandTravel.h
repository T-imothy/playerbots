#ifndef LIVING_WOW_ERRAND_TRAVEL_H
#define LIVING_WOW_ERRAND_TRAVEL_H

#include <chrono>
#include <cstdint>

// Travel has no total duration limit. Five idle minutes accommodate transport
// schedules and route preparation before the manager retries a stalled route.
// Observe physical movement: a valid route may initially head away from its
// destination to reach a road, flight master, boat, or zeppelin.
class LivingWowErrandTravel
{
public:
    using Clock = std::chrono::steady_clock;
    using Time = Clock::time_point;

    void Reset(Time now, std::uint32_t map, float x, float y, float z)
    {
        lastMap = map; lastX = x; lastY = y; lastZ = z;
        deadline = now + std::chrono::minutes(5);
    }

    void Observe(Time now, std::uint32_t map, float x, float y, float z, bool taxi)
    {
        float dx = x - lastX, dy = y - lastY, dz = z - lastZ;
        if (taxi || map != lastMap || dx * dx + dy * dy + dz * dz >= 9.0f)
            Reset(now, map, x, y, z);
    }

    bool Expired(Time now) const { return now >= deadline; }

private:
    std::uint32_t lastMap = 0;
    float lastX = 0, lastY = 0, lastZ = 0;
    Time deadline;
};

#endif
