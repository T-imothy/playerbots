#pragma once
class PlayerbotAI;
namespace ai
{
    bool NaxxramasControlAllowed(PlayerbotAI* ai);
    void ProcessNaxxramasControlCommands(PlayerbotAI* ai, bool commandsPending);
}
