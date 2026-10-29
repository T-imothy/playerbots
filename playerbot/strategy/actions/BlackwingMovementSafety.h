#pragma once

#include <vector>
#include "playerbot/WorldPosition.h"

class PlayerbotAI;
namespace ai
{
    // Local movement admission only. Fresh packs must never become global
    // damage hazards, which would make the raid flee from unpulled creatures.
    bool BlackwingSuppressionMovementActive(PlayerbotAI* ai);
    bool BlackwingMovementRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path);
    bool BuildBlackwingMovementPath(PlayerbotAI* ai, const WorldPosition& destination,
        std::vector<WorldPosition>& path);
    bool StopUnsafeBlackwingMovement(PlayerbotAI* ai);
    bool BlackwingActiveMovementUnsafe(PlayerbotAI* ai);
}
