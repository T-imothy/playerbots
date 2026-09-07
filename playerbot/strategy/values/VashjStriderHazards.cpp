#include "playerbot/playerbot.h"
#include "HazardsValue.h"
#include "VashjCoreValue.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

void ai::AppendVashjStriderHazards(PlayerbotAI* ai, std::list<HazardPosition>& hazards)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 548) return;
    Unit* boss = FindVashjCorePhase(ai);
    if (!boss) return;
    const float radius = NativeEncounterSpellRadius(38258);
    if (!std::isfinite(radius) || radius <= 0 || radius > 35) return;
    std::list<Unit*> striders;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, 22056, 100.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(striders, check);
    Cell::VisitAllObjects(bot, searcher, 100.0f);
    for (Unit* strider : striders)
    {
        if (!strider->IsInWorld() || !strider->IsAlive() || !strider->IsInCombat() ||
            !bot->IsInMap(strider) || strider->HasCharmer() || strider->GetSpawnerGuid() != boss->GetObjectGuid() ||
            !strider->GetSpellAuraHolder(38257, strider->GetObjectGuid()) ||
            std::fabs(strider->GetPositionZ() - bot->GetPositionZ()) > 8) continue;
        // Rebuild from live positions, so death, phase changes and movement do
        // not leave stored circles behind. The pursued player gets extra lead.
        // Shared chase/path/escape checks also protect core relay destinations.
        hazards.emplace_back(WorldPosition(strider), radius + (strider->GetVictim() == bot ? 8.0f : 4.0f));
    }
#endif
}
