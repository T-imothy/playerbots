#pragma once

#include <vector>
#include "playerbot/WorldPosition.h"
#include "playerbot/strategy/EncounterGeometry.h"

class PlayerbotAI;
class Unit;
namespace ai
{
    struct EncounterPosition;
    bool BlackwingPatrolThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);
    // Local movement admission only. Fresh packs must never become global
    // damage hazards, which would make the raid flee from unpulled creatures.
    bool BlackwingSuppressionMovementActive(PlayerbotAI* ai);
    bool BlackwingMovementSafetyActive(PlayerbotAI* ai);
    bool RaidUnpulledPackMovementActive(PlayerbotAI* ai);
    bool BlackwingMovementRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path);
    bool RaidUnpulledPackRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path);
    bool MadnessFormationRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path, Unit* boss);
    bool MajordomoFormationRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path, Unit* boss);
    bool MoltenCoreTrashChargeSafe(PlayerbotAI* ai);
    bool BuildBlackwingMovementPath(PlayerbotAI* ai, const WorldPosition& destination,
        std::vector<WorldPosition>& path);
    bool StopUnsafeBlackwingMovement(PlayerbotAI* ai);
    bool BlackwingActiveMovementUnsafe(PlayerbotAI* ai);
}
