#ifndef LIVING_ACTIVITY_NATIVE_CONTEXT_H
#define LIVING_ACTIVITY_NATIVE_CONTEXT_H
#include "LivingActivity.h"

namespace LivingActivity {
    // Reads the actor's native lifecycle and the group's atomic stamp only.
    // Never enumerates a roster or calls a manager's mutating 'const' session
    // getter on a map worker. Core patch 016 supplies the native group stamp.
    template<class NativePlayer>
    WorldContext ReadNativeContext(NativePlayer& player, uint64_t policy, const std::string& boot) {
        WorldContext value; value.actor = player.GetGUIDLow(); value.policyRevision = policy; value.boot = boot;
        const auto* ai = player.GetPlayerbotAI();
        if (!ai || !player.IsInWorld() || player.IsBeingTeleported()) return value; // Invalid epoch, fail closed.
        value.map = player.GetMapId(); value.instance = player.GetInstanceId();
        value.actorGeneration = ai->GetActivityActorEpoch(); value.mapGeneration = ai->GetActivityMapEpoch();
        if (const auto* group = player.GetGroup()) {
            if (!group->GetLivingActivityIdentity() || !group->GetLivingActivityRevision()) {
                value.mapGeneration = 0; return value; // Native counter exhaustion never revives authority.
            }
            value.session = "group:" + std::to_string(group->GetId()) + ':' +
                std::to_string(group->GetLivingActivityIdentity());
            value.sessionRevision = group->GetLivingActivityRevision();
        }
        return value;
    }
}
#endif
