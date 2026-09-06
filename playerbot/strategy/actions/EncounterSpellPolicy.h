#pragma once

class Player;
class Unit;
struct SpellEntry;

namespace ai
{
    // Decisions only: native spells, proc rules and aura lifetimes are unchanged.
    bool ShouldAvoidCorruptedHealing(Player* bot, const SpellEntry* spell, Unit* target);
    bool HasCorruptedHealingCast(Player* bot);
    bool InterruptCorruptedHealingCast(Player* bot);
}
