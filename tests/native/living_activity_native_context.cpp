#include "LivingActivityNativeContext.h"
#include "LivingActivityEpoch.h"
#include <cassert>
using namespace LivingActivity;
struct NativeGroup {
    NativeEpoch epoch;
    uint32_t GetId() const { return 7; }
    uint64_t GetLivingActivityIdentity() const { return epoch.Actor(); }
    uint64_t GetLivingActivityRevision() const { return epoch.Map(); }
};
struct NativeAI {
    NativeEpoch epoch;
    uint64_t GetActivityActorEpoch() const { return epoch.Actor(); }
    uint64_t GetActivityMapEpoch() const { return epoch.Map(); }
};
struct NativePlayer {
    NativeAI ai;
    NativeGroup* group = nullptr;
    bool inWorld = true, teleporting = false;
    uint32_t GetGUIDLow() const { return 497; }
    uint32_t GetMapId() const { return 1; }
    uint32_t GetInstanceId() const { return 0; }
    NativeAI* GetPlayerbotAI() { return &ai; }
    NativeGroup* GetGroup() { return group; }
    bool IsInWorld() const { return inWorld; }
    bool IsBeingTeleported() const { return teleporting; }
};
int main() {
    const std::string boot = "637bd562-36d2-5b01-bc01-e2d831c49f38";
    NativePlayer player; NativeGroup group;
    auto solo = ReadNativeContext(player, 1, boot);
    assert(solo.actor == 497 && solo.session.empty() && !solo.sessionRevision && solo.mapGeneration);
    player.group = &group; player.ai.epoch.Invalidate();
    const auto joined = ReadNativeContext(player, 1, boot);
    assert(!(joined == solo) && joined.sessionRevision && !joined.session.empty());
    group.epoch.Invalidate(); // Leader/member/permission-sensitive native roster update.
    assert(!(ReadNativeContext(player, 1, boot) == joined));
    const auto prior = ReadNativeContext(player, 1, boot);
    player.group = nullptr; player.ai.epoch.Invalidate();
    player.group = &group; player.ai.epoch.Invalidate();
    assert(!(ReadNativeContext(player, 1, boot) == prior)); // Unobserved leave/rejoin ABA.
    NativeGroup replacement; player.group = &replacement;
    assert(ReadNativeContext(player, 1, boot).session != prior.session); // Reused native numeric group ID.
    player.teleporting = true; assert(!ReadNativeContext(player, 1, boot).mapGeneration);
    player.teleporting = false; player.inWorld = false; assert(!ReadNativeContext(player, 1, boot).mapGeneration);
    player.inWorld = true;
    assert(!(ReadNativeContext(player, 2, boot) == ReadNativeContext(player, 1, boot)));
}
