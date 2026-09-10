#ifndef LIVING_ACTIVITY_AUTHORITY_H
#define LIVING_ACTIVITY_AUTHORITY_H
#include "LivingActivity.h"
#include "LivingActivityEffects.h"
#include <map>

namespace LivingActivity {
    enum class AuthorityCode {
        Granted, Renewed, Preempted, Released, NoOwner, Allowed,
        InvalidRequest, StaleContext, StaleLease, StaleRevision, SafetyPaused,
        AtomicPending, PriorityDenied, EffectsDenied, UnknownAction,
        ReconciliationRequired, Capacity, GenerationExhausted
    };
    const char* Name(AuthorityCode code);
    struct AuthorityResult {
        AuthorityCode code = AuthorityCode::InvalidRequest;
        ActivityLease lease, displaced;
        bool Granted() const;
    };

    // A world-thread-owned lease book, NOT a second scheduler or task store.
    // The coordinator owns the durable queue. Producers supply already validated
    // root tasks; child steps inherit that root rather than competing with it.
    // Every displacement is returned exactly once for the coordinator's handoff.
    class ExecutionAuthority {
    public:
        explicit ExecutionAuthority(size_t actorLimit = 20000) : limit(actorLimit) {}
        AuthorityResult Observe(const WorldContext& current, uint32_t safety);
        AuthorityResult Acquire(const Task& root, uint32_t effects, uint64_t now, uint64_t duration);
        AuthorityResult Release(const ActivityLease& lease);
        AuthorityResult Forget(uint32_t actor);
        AuthorityResult BeginAtomic(const ActivityLease& lease, const std::string& operation, uint64_t now);
        AuthorityResult FinishAtomic(const ActivityLease& lease, const std::string& operation);
        AuthorityResult Inspect(uint32_t actor, uint64_t now) const;
        AuthorityCode Authorize(const Effects& effects, const WorldContext& current, uint64_t now,
            const Task* task = nullptr, const ActionContext* action = nullptr,
            const NativePermit* permit = nullptr) const;
        size_t Size() const { return actors.size(); }
    private:
        struct Actor {
            WorldContext current;
            uint32_t safety = 0, effects = 0;
            Task root;
            ActivityLease lease;
            uint64_t expires = 0;
            std::string operation;
            bool invalidated = false;
        };
        static bool ContextValid(const WorldContext& context);
        static bool Matches(const ActivityLease& left, const ActivityLease& right);
        static bool Executable(const Task& task);
        static uint32_t LaneEffects(Lane lane);
        static AuthorityResult Drop(Actor& actor, AuthorityCode code);
        std::map<uint32_t, Actor> actors;
        size_t limit;
        uint64_t generation = 0;
    };
}
#endif
