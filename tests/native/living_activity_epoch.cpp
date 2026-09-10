#include "LivingActivityEpoch.h"
#include <cassert>
#include <set>
#include <thread>
#include <vector>
#include <mutex>

using namespace LivingActivity;
struct Actor {
    NativeEpoch epoch;
    uint64_t GetActivityActorEpoch() const { return epoch.Actor(); }
    uint64_t GetActivityMapEpoch() const { return epoch.Map(); }
};
struct Player {
    Actor ai;
    bool inWorld = true, teleporting = false;
    uint32_t map = 0, instance = 0;
    const Actor* GetPlayerbotAI() const { return &ai; }
    bool IsInWorld() const { return inWorld; }
    bool IsBeingTeleported() const { return teleporting; }
    uint32_t GetMapId() const { return map; }
    uint32_t GetInstanceId() const { return instance; }
};
int main() {
    Player p;
    NativeWorldStamp stamp{p.map, p.instance, p.ai.epoch.Actor(), p.ai.epoch.Map()};
    assert(SameNativeWorld(p, stamp));
    p.inWorld = false; assert(!SameNativeWorld(p, stamp));
    p.inWorld = true; p.teleporting = true; assert(!SameNativeWorld(p, stamp));
    p.teleporting = false; p.ai.epoch.Invalidate(); assert(!SameNativeWorld(p, stamp));
    stamp.mapEpoch = p.ai.epoch.Map(); assert(SameNativeWorld(p, stamp));
    ++p.map; assert(!SameNativeWorld(p, stamp));
    --p.map; ++p.instance; assert(!SameNativeWorld(p, stamp));
    Player relogged; assert(!SameNativeWorld(relogged, stamp));
    std::mutex lock; std::set<uint64_t> identities;
    std::vector<std::thread> workers;
    for (int i = 0; i < 4; ++i) workers.emplace_back([&] {
        for (int n = 0; n < 1000; ++n) {
            Actor actor;
            p.ai.epoch.Invalidate();
            std::lock_guard<std::mutex> hold(lock);
            assert(identities.insert(actor.epoch.Actor()).second);
        }
    });
    for (auto& worker : workers) worker.join();
    assert(identities.size() == 4000 && p.ai.epoch.Map() == 4002);
    stamp.actorEpoch = 0; assert(!SameNativeWorld(p, stamp));
}
