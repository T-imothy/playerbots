#pragma once
#include "playerbot/strategy/values/EncounterPositionValue.h"
namespace ai
{
    bool GarrEncounterActive(PlayerbotAI* ai);
    Unit* GarrBanishTarget(PlayerbotAI* ai);
    Unit* GarrFocusTarget(PlayerbotAI* ai);
    Unit* GarrTankTarget(PlayerbotAI* ai);
    bool GarrTankHandoff(PlayerbotAI* ai, Unit* target);
    bool PlanGarrPosition(PlayerbotAI* ai, EncounterPosition& plan);
    bool GarrSpellAllowed(PlayerbotAI* ai, const std::string& name, Unit* target, const SpellEntry* spell);
}
