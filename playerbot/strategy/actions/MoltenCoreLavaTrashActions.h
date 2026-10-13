#pragma once
#include "playerbot/strategy/values/EncounterPositionValue.h"

namespace ai
{
    bool LavaTrashCombatActive(PlayerbotAI* ai);
    bool MoltenCoreGroupEnemy(PlayerbotAI* ai, Unit* target);
    bool MoltenCoreRecoveryTrash(uint32 entry);
    Unit* MoltenCoreTrashAggroTarget(PlayerbotAI* ai);
    Unit* LavaTrashBanishTarget(PlayerbotAI* ai);
    Unit* LavaTrashFocusTarget(PlayerbotAI* ai);
    bool LavaTrashReservedTarget(PlayerbotAI* ai, Unit* target);
    bool LavaTrashSpellAllowed(PlayerbotAI* ai, const std::string& name, Unit* target, const SpellEntry* spell);
    bool PlanLavaTrashCarrier(PlayerbotAI* ai, EncounterPosition& plan);
    bool PlanLavaTrashBanish(PlayerbotAI* ai, EncounterPosition& plan);
    bool LavaTrashRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path);
}
