#pragma once
#include "Common.h"
#include <array>
#include <string>
class PlayerbotAI;
namespace ai
{
enum class BotIncidentKind : uint8 { Dead, Movement, ActionLoop, Unreachable };
struct BotIncidentEpisode
{
    uint32 started = 0, last = 0, count = 0;
    bool active = false;
};
struct BotIncidentState
{
    std::array<BotIncidentEpisode, 4> episodes{};
    uint32 sampled = 0, map = 0, instance = 0, bot = 0;
    float x = 0, y = 0, z = 0;
    std::string failedAction;
    bool actionUnavailable = false;
    uint64 unreachableTarget = 0;
};
class BotIncidentHistory
{
public:
    static void Sample(PlayerbotAI* ai);
    static void ActionResult(PlayerbotAI* ai, const std::string& action, bool success, bool unavailable = false);
    static void Unreachable(PlayerbotAI* ai);
    static void Close(BotIncidentState& state);
    static void Flush();
};
}
