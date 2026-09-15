#pragma once
#include <string>
class Player;
class PlayerbotAI;
namespace ai
{
class BotPartyCommands
{
public:
    static bool Queue(Player* owner, const std::string& text, unsigned type);
    // Called only under this bot's update lock, on its owning map.
    static bool Update(PlayerbotAI* ai);
};
}
