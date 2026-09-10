#pragma once
#include <cstdint>
#include <map>

namespace ai
{
// Per bot and spawn: walking successfully is not evidence that loot is reachable.
class LootApproachMemory
{
    struct Attempt
    {
        int64_t started, progressed, touched, retryAfter;
        float bestDistance;
    };
    std::map<uint64_t, Attempt> attempts;
    void Prune(int64_t now)
    {
        for (auto i = attempts.begin(); i != attempts.end();)
            if (now - i->second.touched >= 180000 && now >= i->second.retryAfter)
                i = attempts.erase(i);
            else
                ++i;
    }
public:
    bool IsBlocked(uint64_t guid, int64_t now)
    {
        Prune(now);
        auto i = attempts.find(guid);
        return i != attempts.end() && now < i->second.retryAfter;
    }
    bool Observe(uint64_t guid, float distance, int64_t now)
    {
        Prune(now);
        auto i = attempts.find(guid);
        if (i == attempts.end())
            i = attempts.emplace(guid, Attempt{now, now, now, 0, distance}).first;
        Attempt& attempt = i->second;
        if (now < attempt.retryAfter)
            return false;
        if (attempt.retryAfter)
            attempt = Attempt{now, now, now, 0, distance};
        attempt.touched = now;
        if (distance + 1.0f < attempt.bestDistance)
        {
            attempt.bestDistance = distance;
            attempt.progressed = now;
        }
        if (now - attempt.started >= 30000 || now - attempt.progressed >= 10000)
        {
            attempt.retryAfter = now + 120000;
            return false;
        }
        return true;
    }
    void Complete(uint64_t guid) { attempts.erase(guid); }
};
}
