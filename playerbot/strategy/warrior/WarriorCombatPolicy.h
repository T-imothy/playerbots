#pragma once
#include <string>
class PlayerbotAI;
class Unit;
struct SpellEntry;
namespace ai
{
    std::string WarriorStancePrerequisite(PlayerbotAI* ai, const SpellEntry* spell);
    bool CanPlanWarriorSpell(PlayerbotAI* ai, const std::string& name, Unit* target);
}
