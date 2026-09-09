#pragma once

#include "Common.h"
#include <functional>
#include <string>

class Player;

namespace ai
{
    class BotRecruitment
    {
    public:
        // Queue only GUIDs. Update is called on the world thread, outside map workers.
        static bool Queue(Player* requester, Player* bot, const std::string& operation);
        static bool HandleCommand(Player* requester, const std::string& command);
        static bool CanInvite(Player* requester, Player* bot);
        static void OnInvite(Player* requester, Player* bot);
        static bool HasPendingInvite(Player* bot);
        static void Update(uint32 diff);
        static std::string Eligibility(Player* requester, Player* bot);
        static std::string PreparationReason(Player* requester, Player* bot);
        static bool IsPreparation(const std::string& command);
        static std::string Prepare(Player* requester, Player* bot, const std::string& command,
            const std::string& parameter, const std::function<std::string()>& apply);
    };
}
