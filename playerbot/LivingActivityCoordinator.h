#ifndef LIVING_ACTIVITY_COORDINATOR_H
#define LIVING_ACTIVITY_COORDINATOR_H
#include <memory>
#include <string>
#include <cstdint>

class LivingActivityCoordinator {
public:
    static LivingActivityCoordinator& instance();
    // Called by the existing world update. Persistence uses the existing
    // CharacterDatabase delay/result queues, not a worker/timer per bot.
    void Update();
    std::string StatusJson() const;
    std::string ActorJson(uint32_t guid) const;
private:
    LivingActivityCoordinator();
    ~LivingActivityCoordinator();
    struct State;
    std::unique_ptr<State> state;
};
#define sLivingActivityCoordinator LivingActivityCoordinator::instance()
#endif
