#pragma once
#include <string>

class PlayerbotAI;
class Unit;
namespace ai
{
    bool HasEquivalentGroupBuff(PlayerbotAI* ai, const std::string& spell, Unit* target);
    // Automatic, long-duration shared buffs only. Native spell admission still
    // owns range, LOS, reagents, resources and the global cooldown.
    bool AutomaticGroupBuffAllowed(PlayerbotAI* ai, const std::string& spell, Unit* target);
}
