#ifndef LIVING_ACTIVITY_COORDINATOR_H
#define LIVING_ACTIVITY_COORDINATOR_H
#include <memory>
#include <string>
#include <cstdint>
#include "LivingActivityEffects.h"

class LivingActivityCoordinator {
public:
    static LivingActivityCoordinator& instance();
    // Called by the existing world update. Persistence uses the existing
    // CharacterDatabase delay/result queues, not a worker/timer per bot.
    void Update();
    std::string StatusJson() const;
    std::string ActorJson(uint32_t guid) const;
    // Map-worker entry point: bounded immutable diagnostics only. Does not read
    // the coordinator's task/lease maps and never authorizes a native effect.
    void ObserveAction(uint32_t guid, uint64_t actorEpoch, uint64_t mapEpoch,
        const LivingActivity::Effects& effects, const std::string& action);
private:
    LivingActivityCoordinator();
    ~LivingActivityCoordinator();
    struct State;
    std::unique_ptr<State> state;
};
#define sLivingActivityCoordinator LivingActivityCoordinator::instance()
#endif
