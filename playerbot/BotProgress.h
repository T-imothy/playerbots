#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cmath>
#include <string>
#include <vector>

namespace ai {
// Map-owner state only. IDs, never retained native object pointers.
class UnreachableTargetMemory {
    struct Exclusion { uint64_t target; uint32_t until; };
    std::vector<Exclusion> excluded;
    uint64_t tracking = 0;
    uint32_t since = 0, map = 0, instance = 0;
    float x = 0, y = 0, bestDistance = 0;
public:
    static constexpr size_t Capacity = 32;
    static bool Future(uint32_t deadline, uint32_t now) { return int32_t(deadline - now) > 0; }
    void ResetProgress() { tracking = 0; }
    void Reset() { tracking = 0; excluded.clear(); }
    void SetDomain(uint32_t newMap, uint32_t newInstance) {
        if (map != newMap || instance != newInstance) { Reset(); map = newMap; instance = newInstance; }
    }
    void Prune(uint32_t now) {
        excluded.erase(std::remove_if(excluded.begin(), excluded.end(), [now](Exclusion const& e) {
            return !Future(e.until, now);
        }), excluded.end());
    }
    bool Contains(uint64_t target, uint32_t now) {
        Prune(now);
        return std::any_of(excluded.begin(), excluded.end(), [target](Exclusion const& e) { return e.target == target; });
    }
    size_t Size() const { return excluded.size(); }
    bool Observe(uint64_t target, uint32_t now, float px, float py, float distance,
                 bool mayAbandon, uint32_t timeout, uint32_t exclusionMs) {
        if (!target || !mayAbandon || !timeout || !exclusionMs ||
            !std::isfinite(px) || !std::isfinite(py) || !std::isfinite(distance)) { ResetProgress(); return false; }
        if (Contains(target, now)) return true;
        float dx = px - x, dy = py - y;
        if (tracking != target || distance < bestDistance - 2.0f || dx*dx + dy*dy >= 64.0f) {
            tracking = target; since = now; x = px; y = py; bestDistance = distance;
            return false;
        }
        if (uint32_t(now - since) < timeout) return false;
        if (excluded.size() == Capacity) excluded.erase(excluded.begin());
        excluded.push_back({target, now + exclusionMs});
        ResetProgress();
        return true;
    }
};

enum class BotIncidentKind : uint8_t { Stuck, DeadLong, ActionLoop, Unreachable, Count };
inline char const* BotIncidentName(BotIncidentKind kind) {
    static char const* names[] = {"STUCK", "DEAD_LONG", "ACTION_LOOP", "UNREACHABLE_TARGET"};
    return names[static_cast<size_t>(kind)];
}
// One small tracker per AI; output only on transitions or a 30-second heartbeat.
class BotIncidentTracker {
    struct Condition { bool observing=false, open=false; uint32_t since=0, lastPublish=0; uint64_t target=0; };
    std::array<Condition, static_cast<size_t>(BotIncidentKind::Count)> conditions{};
public:
    template<class Emit> void Observe(BotIncidentKind kind, bool condition, uint64_t target,
                                      uint32_t now, uint32_t threshold, Emit emit) {
        auto& c = conditions[static_cast<size_t>(kind)];
        if (c.observing && (!condition || c.target != target)) {
            if (c.open) emit(kind, false, c.target, uint32_t(now-c.since));
            c = {};
        }
        if (!condition) return;
        if (!c.observing) { c.observing=true; c.since=now; c.target=target; }
        uint32_t age = now-c.since;
        if (age >= threshold && (!c.open || uint32_t(now-c.lastPublish) >= 30000)) {
            c.open=true; c.lastPublish=now; emit(kind,true,target,age);
        }
    }
    template<class Emit> void Reset(uint32_t now, Emit emit) {
        for (size_t i=0;i<conditions.size();++i) Observe(static_cast<BotIncidentKind>(i),false,0,now,0,emit);
    }
};
}
