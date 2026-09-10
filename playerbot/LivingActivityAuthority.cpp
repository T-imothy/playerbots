#include "LivingActivityAuthority.h"
#include <algorithm>
#include <limits>

namespace LivingActivity {
    const char* Name(AuthorityCode code) {
        switch (code) {
#define CASE(value, text) case AuthorityCode::value: return text
        CASE(Granted, "granted"); CASE(Renewed, "renewed"); CASE(Preempted, "preempted");
        CASE(Released, "released"); CASE(NoOwner, "no_owner"); CASE(Allowed, "allowed");
        CASE(InvalidRequest, "invalid_request"); CASE(StaleContext, "stale_context");
        CASE(StaleLease, "stale_lease"); CASE(StaleRevision, "stale_revision");
        CASE(SafetyPaused, "safety_paused"); CASE(AtomicPending, "atomic_pending");
        CASE(PriorityDenied, "priority_denied"); CASE(EffectsDenied, "effects_denied");
        CASE(UnknownAction, "unknown_action"); CASE(ReconciliationRequired, "reconciliation_required");
        CASE(Capacity, "actor_capacity"); CASE(GenerationExhausted, "generation_exhausted");
#undef CASE
        }
        return "invalid_authority_code";
    }
    bool AuthorityResult::Granted() const {
        return code == AuthorityCode::Granted || code == AuthorityCode::Renewed || code == AuthorityCode::Preempted;
    }
    bool ExecutionAuthority::ContextValid(const WorldContext& c) {
        return c.actor && c.actorGeneration && c.mapGeneration && c.policyRevision && IsUuid(c.boot) &&
            c.session.size() <= 120 && (c.session.empty() == (c.sessionRevision == 0));
    }
    bool ExecutionAuthority::Executable(const Task& t) {
        return t.mode == Mode::Active && (t.phase == Phase::Preparing || t.phase == Phase::Traveling ||
            t.phase == Phase::Executing);
    }
    bool ExecutionAuthority::Matches(const ActivityLease& a, const ActivityLease& b) {
        return a.actor && a.generation && a.actor == b.actor && a.rootTask == b.rootTask &&
            a.generation == b.generation && a.context == b.context;
    }
    AuthorityResult ExecutionAuthority::Drop(Actor& a, AuthorityCode code) {
        AuthorityResult result; result.code = code; result.displaced = a.lease;
        a.lease = {}; a.root = {}; a.expires = 0; a.effects = 0; a.operation.clear(); a.invalidated = false;
        return result;
    }
    AuthorityResult ExecutionAuthority::Observe(const WorldContext& current, uint32_t safety) {
        if (!ContextValid(current) || (safety & ~uint32_t(127))) return {AuthorityCode::InvalidRequest, {}, {}};
        auto found = actors.find(current.actor);
        if (found == actors.end()) {
            if (actors.size() >= limit) return {AuthorityCode::Capacity, {}, {}};
            found = actors.emplace(current.actor, Actor{}).first;
        }
        auto& a = found->second;
        const bool changed = !(a.current == current);
        a.current = current; a.safety = safety;
        if (changed && a.lease.actor) {
            if (!a.operation.empty()) {
                // Native effect may already have happened. Keep its identity for
                // the receipt; it grants NO permission in the new world context.
                a.invalidated = true;
                return {AuthorityCode::ReconciliationRequired, a.lease, {}};
            }
            return Drop(a, AuthorityCode::Released);
        }
        return {safety ? AuthorityCode::SafetyPaused : AuthorityCode::Allowed, a.lease, {}};
    }
    AuthorityResult ExecutionAuthority::Acquire(const Task& root, uint32_t effects, uint64_t now, uint64_t duration) {
        std::string error;
        if (!Validate(root, error) || !Executable(root) || !root.parent.empty() || root.root != root.id ||
            !effects || (effects & ~AllEffects) || !duration || duration > 600000 ||
            duration > std::numeric_limits<uint64_t>::max() - now)
            return {AuthorityCode::InvalidRequest, {}, {}};
        auto found = actors.find(root.actor);
        if (found == actors.end() || !(root.context == found->second.current))
            return {AuthorityCode::StaleContext, {}, {}};
        auto& a = found->second;
        if (a.safety) return {AuthorityCode::SafetyPaused, a.lease, {}};
        if (a.invalidated) return {AuthorityCode::ReconciliationRequired, a.lease, {}};
        const bool held = a.lease.actor != 0;
        if (held && root.id == a.root.id && root.revision < a.root.revision)
            return {AuthorityCode::StaleRevision, a.lease, {}};
        if (held && root.id == a.root.id && root.revision == a.root.revision) {
            // An existing revision cannot silently change its authority/priority.
            if (effects != a.effects || root.priority != a.root.priority || root.accepted != a.root.accepted ||
                root.dueAtMs != a.root.dueAtMs || root.createdAtMs != a.root.createdAtMs || root.phase != a.root.phase)
                return {AuthorityCode::StaleRevision, a.lease, {}};
            if (now < a.expires) {
                a.expires = now + duration;
                return {AuthorityCode::Renewed, a.lease, {}};
            }
        }
        if (!a.operation.empty()) return {AuthorityCode::AtomicPending, a.lease, {}};
        if (held && now < a.expires && root.id != a.root.id && !Before(root, a.root))
            return {AuthorityCode::PriorityDenied, a.lease, {}};
        generation = std::max(generation, root.ownerGeneration);
        if (generation == std::numeric_limits<uint64_t>::max())
            return {AuthorityCode::GenerationExhausted, a.lease, {}};
        AuthorityResult result; result.displaced = a.lease;
        a.root = root; a.effects = effects; a.expires = now + duration;
        a.lease = {root.actor, root.id, ++generation, root.context};
        result.lease = a.lease; result.code = held ? AuthorityCode::Preempted : AuthorityCode::Granted;
        return result;
    }
    AuthorityResult ExecutionAuthority::Release(const ActivityLease& lease) {
        const auto found = actors.find(lease.actor);
        if (found == actors.end() || !Matches(found->second.lease, lease))
            return {AuthorityCode::StaleLease, {}, {}};
        if (!found->second.operation.empty()) return {AuthorityCode::AtomicPending, found->second.lease, {}};
        return Drop(found->second, AuthorityCode::Released);
    }
    AuthorityResult ExecutionAuthority::Forget(uint32_t actor) {
        const auto found = actors.find(actor);
        if (found == actors.end()) return {AuthorityCode::NoOwner, {}, {}};
        if (!found->second.operation.empty()) {
            found->second.invalidated = true;
            return {AuthorityCode::ReconciliationRequired, found->second.lease, {}};
        }
        auto result = Drop(found->second, AuthorityCode::Released);
        actors.erase(found);
        return result;
    }
    AuthorityResult ExecutionAuthority::Inspect(uint32_t actor, uint64_t now) const {
        const auto found = actors.find(actor);
        if (found == actors.end() || !found->second.lease.actor) return {AuthorityCode::NoOwner, {}, {}};
        const auto& a = found->second;
        if (a.invalidated) return {AuthorityCode::ReconciliationRequired, a.lease, {}};
        if (a.safety) return {AuthorityCode::SafetyPaused, a.lease, {}};
        if (now >= a.expires) return {a.operation.empty() ? AuthorityCode::StaleLease : AuthorityCode::AtomicPending, a.lease, {}};
        return {AuthorityCode::Allowed, a.lease, {}};
    }
    AuthorityResult ExecutionAuthority::BeginAtomic(const ActivityLease& lease, const std::string& operation, uint64_t now) {
        const auto found = actors.find(lease.actor);
        if (!IsUuid(operation) || found == actors.end() || !Matches(found->second.lease, lease))
            return {AuthorityCode::StaleLease, {}, {}};
        auto& a = found->second;
        if (a.invalidated || !(a.current == lease.context)) return {AuthorityCode::StaleContext, a.lease, {}};
        if (a.safety) return {AuthorityCode::SafetyPaused, a.lease, {}};
        if (now >= a.expires) return {AuthorityCode::StaleLease, a.lease, {}};
        if (!a.operation.empty()) return {AuthorityCode::AtomicPending, a.lease, {}};
        a.operation = operation; return {AuthorityCode::Allowed, a.lease, {}};
    }
    AuthorityResult ExecutionAuthority::FinishAtomic(const ActivityLease& lease, const std::string& operation) {
        const auto found = actors.find(lease.actor);
        if (found == actors.end() || !Matches(found->second.lease, lease) ||
            operation.empty() || found->second.operation != operation)
            return {AuthorityCode::StaleLease, {}, {}};
        auto& a = found->second;
        a.operation.clear();
        // This ends only the atomic execution boundary. It is NOT proof that
        // the operation succeeded or the task completed; the journal owns that.
        if (a.invalidated) return Drop(a, AuthorityCode::ReconciliationRequired);
        return {AuthorityCode::Allowed, a.lease, {}};
    }
    uint32_t ExecutionAuthority::LaneEffects(Lane lane) {
        switch (lane) {
        case Lane::Inspection: return 0;
        case Lane::Combat: case Lane::Healing: return Mask(Effect::Movement) | Mask(Effect::Spell) | Mask(Effect::Inventory);
        case Lane::Loot: return Mask(Effect::Movement) | Mask(Effect::Inventory) | Mask(Effect::Money);
        case Lane::Roll: return Mask(Effect::Inventory) | Mask(Effect::Social);
        case Lane::LocalQuest: return Mask(Effect::Inventory) | Mask(Effect::Spell) | Mask(Effect::Money);
        case Lane::Safety: return Mask(Effect::Movement) | Mask(Effect::Spell);
        case Lane::Social: return Mask(Effect::Social);
        default: return 0;
        }
    }
    AuthorityCode ExecutionAuthority::Authorize(const Effects& effects, const WorldContext& current, uint64_t now,
        const Task* task, const ActionContext* action, const NativePermit* permit) const {
        const auto found = actors.find(current.actor);
        if (found == actors.end()) return AuthorityCode::StaleContext;
        return Check(found->second, effects, current, now, task, action, permit);
    }
    AuthoritySnapshot ExecutionAuthority::Read(uint32_t actor) const {
        const auto found = actors.find(actor);
        return found == actors.end() ? AuthoritySnapshot{} : found->second;
    }
    AuthorityCode ExecutionAuthority::Check(const AuthoritySnapshot& a, const Effects& effects,
        const WorldContext& current, uint64_t now, const Task* task,
        const ActionContext* action, const NativePermit* permit) {
        if (!ContextValid(current) || !(a.current == current)) return AuthorityCode::StaleContext;
        if (!effects.classified) return AuthorityCode::UnknownAction;
        if (effects.mask & ~AllEffects) return AuthorityCode::EffectsDenied;
        if (effects.lane == Lane::Inspection)
            return effects.mask ? AuthorityCode::EffectsDenied : AuthorityCode::Allowed;
        if (effects.lane != Lane::Managed) {
            // The native adapter must validate the actual target and operation.
            // A combat/reaction flag or a model-supplied action name is no proof.
            if (!permit || !permit->validated || permit->lane != effects.lane || !(permit->world == current) ||
                (effects.mask & ~permit->effects) || (effects.mask & ~LaneEffects(effects.lane)))
                return AuthorityCode::EffectsDenied;
            if (a.safety & ~permit->allowedSafety) return AuthorityCode::SafetyPaused;
            if (!a.operation.empty() && (effects.mask & (Mask(Effect::Inventory) | Mask(Effect::Money))))
                return AuthorityCode::AtomicPending;
            return AuthorityCode::Allowed;
        }
        if (a.invalidated) return AuthorityCode::ReconciliationRequired;
        if (a.safety) return AuthorityCode::SafetyPaused;
        if (!a.operation.empty()) return AuthorityCode::AtomicPending;
        if (!task || !action || !Executable(*task) || !Fresh(*task, *action, current) ||
            !Matches(a.lease, {task->actor, task->root, action->ownerGeneration, current}) || now >= a.expires)
            return AuthorityCode::StaleLease;
        if (!IsToken(action->origin, 64) || (action->permittedEffects & ~a.effects) ||
            (effects.mask & ~action->permittedEffects)) return AuthorityCode::EffectsDenied;
        if (task->id != task->root && task->parent.empty()) return AuthorityCode::InvalidRequest;
        if (task->id == a.root.id && task->revision != a.root.revision) return AuthorityCode::StaleRevision;
        return AuthorityCode::Allowed;
    }
}
