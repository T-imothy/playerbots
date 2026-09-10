#pragma once
#include <cstdint>
namespace ai
{
struct OutdoorRecoveryMemory
{
    uint32_t map = 0, deaths = 0;
    float x = 0, y = 0;
    int64_t lastDeath = 0, avoidUntil = 0;
    void RecordDeath(uint32_t deathMap, float deathX, float deathY, int64_t now)
    {
        float dx = deathX - x, dy = deathY - y;
        bool repeated = deaths && deathMap == map && now - lastDeath <= 600 &&
            dx * dx + dy * dy <= 10000.0f;
        deaths = repeated ? deaths + 1 : 1;
        map = deathMap; x = deathX; y = deathY; lastDeath = now;
        avoidUntil = deaths >= 2 ? now + 900 : 0;
    }
    bool Avoid(uint32_t targetMap, float targetX, float targetY, int64_t now) const
    {
        float dx = targetX - x, dy = targetY - y;
        return now < avoidUntil && map == targetMap && dx * dx + dy * dy <= 22500.0f;
    }
};
}
