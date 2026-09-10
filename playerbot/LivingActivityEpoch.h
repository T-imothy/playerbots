#ifndef LIVING_ACTIVITY_EPOCH_H
#define LIVING_ACTIVITY_EPOCH_H
#include <atomic>
#include <cstdint>
#include <limits>

namespace LivingActivity {
    // Per-native-actor stamp. Core world entry/exit/teleport hooks invalidate
    // it, including a roundtrip to the same map. No Player pointer is retained.
    // Atomics let the world thread publish grants while native map workers only
    // read/revoke their own actor's stamp. They never mutate the lease book.
    class NativeEpoch {
    public:
        NativeEpoch() : actor(NextActor()) {}
        uint64_t Actor() const { return actor; }
        uint64_t Map() const { return map.load(std::memory_order_acquire); }
        void Invalidate() {
            uint64_t old = map.load(std::memory_order_relaxed);
            while (old && !map.compare_exchange_weak(old,
                old == std::numeric_limits<uint64_t>::max() ? 0 : old + 1,
                std::memory_order_release, std::memory_order_relaxed)) {}
            // Exhaustion is permanently invalid; never wrap to a reusable stamp.
        }
    private:
        static uint64_t NextActor() {
            static std::atomic<uint64_t> counter{0};
            uint64_t old = counter.load(std::memory_order_relaxed);
            while (old != std::numeric_limits<uint64_t>::max()) {
                if (counter.compare_exchange_weak(old, old + 1, std::memory_order_relaxed)) return old + 1;
            }
            return 0;
        }
        const uint64_t actor;
        std::atomic<uint64_t> map{1};
    };

    struct NativeWorldStamp { uint32_t map, instance; uint64_t actorEpoch, mapEpoch; };
    template<class NativePlayer>
    bool SameNativeWorld(NativePlayer& player, const NativeWorldStamp& stamp) {
        // GetMap/GetTerrain assert outside world membership in pinned CMaNGOS.
        // Never call either just to test whether a map pointer is available.
        // Pinned CMaNGOS exposes GetPlayerbotAI() only on non-const Player.
        const auto* ai = player.GetPlayerbotAI();
        return player.IsInWorld() && !player.IsBeingTeleported() && ai &&
            stamp.actorEpoch && stamp.mapEpoch && player.GetMapId() == stamp.map &&
            player.GetInstanceId() == stamp.instance &&
            ai->GetActivityActorEpoch() == stamp.actorEpoch && ai->GetActivityMapEpoch() == stamp.mapEpoch;
    }
}
#endif
