#pragma once

namespace ai
{
    struct ClassicRaidPlan;
    bool BuildWrathHorsemenPlan(PlayerbotAI* ai, const std::vector<Unit*>& horsemen,
        ObjectGuid& previousHorseman, ClassicRaidPlan& plan);
    Unit* WrathHorsemanReliefTarget(PlayerbotAI* ai);
}
