#pragma once

class Player;
class PlayerbotAI;
class Unit;
struct SpellEntry;

namespace ai
{
    // Decisions only: native spells, proc rules and aura lifetimes are unchanged.
    bool ShouldAvoidCorruptedHealing(Player* bot, const SpellEntry* spell, Unit* target);
    bool HasCorruptedHealingCast(Player* bot);
    bool InterruptCorruptedHealingCast(Player* bot);
    bool HasUnsafeReflectedCast(Player* bot);
    bool InterruptUnsafeReflectedCast(Player* bot);
    bool IsProtectedEncounterDispel(Unit* target, uint32 dispelType);
    bool ShouldAvoidEncounterDispel(PlayerbotAI* ai, const SpellEntry* spell, Unit* target);
    bool ShouldSwapEncounterTank(PlayerbotAI* ai, Unit* enemy);
    bool ShouldAvoidEncounterTaunt(PlayerbotAI* ai, const SpellEntry* spell, Unit* enemy);
}
