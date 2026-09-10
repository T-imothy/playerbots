#pragma once
#include <cstdint>
#include <string>
class Player;

namespace ai
{
    struct PartyCatchupStatus
    {
        double multiplier = 1.0;
        uint32_t leaderLevel = 0;
        std::string leader;
        std::string reason = "not_grouped";
    };
    // Called only by marked kill/quest/exploration awards, never a model or GM command.
    uint32_t AwardPartyCatchupBonus(Player* bot, uint64_t normalXP);
    PartyCatchupStatus GetPartyCatchupStatus(Player* bot);
    void ClearPartyCatchup(Player* bot);
}
