#pragma once

#include <string>

class PlayerbotAI;
class Unit;

namespace ai
{
// Local, grounded combat movement for bots following a human party master.
class PartyCombatPositioning
{
public:
    static bool Enabled(PlayerbotAI* ai);
    static bool SpellRanges(PlayerbotAI* ai, Unit* target, const std::string& spell,
        float& minimum, float& maximum);
    static bool Move(PlayerbotAI* ai, Unit* target, float minRange,
        float maxRange, bool retreat = false);
};
}
