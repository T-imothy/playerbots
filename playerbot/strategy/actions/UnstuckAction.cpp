#include "playerbot/playerbot.h"
#include "UnstuckAction.h"
#include "Maps/PathFinder.h"
#include "Maps/MoveMap.h"
#include <cmath>

bool UnstuckAction::Execute(Event& event)
{
    std::string source = event.getSource();
    Player* bot = ai->GetBot();
    Player* master = ai->GetMaster();

    // A decision reset cannot repair a persisted position below the floor.
    // Keep this in the existing stuck action, not in every AI/map update.
    if (source.find("stuck") != std::string::npos && bot->IsAlive() &&
        bot->IsInWorld() && !bot->IsBeingTeleported() && !bot->IsTaxiFlying() &&
        !bot->GetTransport() && !bot->IsInWater() && !bot->IsMoving() &&
        !bot->HasMovementFlag(MOVEFLAG_JUMPING) && !bot->HasMovementFlag(MOVEFLAG_FALLINGFAR) && ai->CanMove())
    {
        const float x = bot->GetPositionX(), y = bot->GetPositionY(), z = bot->GetPositionZ();
        // Query from the actual position so a valid lower floor in a cave or
        // building wins over terrain/roofs above it. Use native player rules
        // for the correction (including liquids), then require a walkable poly.
        const float ground = bot->GetMap()->GetHeight(x, y, z, true);
        float correctedZ = z;
        bot->UpdateAllowedPositionZ(x, y, correctedZ);
        if (ground > INVALID_HEIGHT && ground > z + 3.0f &&
            correctedZ > z + 3.0f && correctedZ <= z + 10.0f &&
            std::fabs(correctedZ - ground) < 0.5f)
        {
            WorldPosition corrected(bot->GetMapId(), x, y, correctedZ + 0.05f, bot->GetOrientation());
            if (corrected.loadMapAndVMap(bot->GetInstanceId()))
            {
                auto const* query = MMAP::MMapFactory::createOrGetMMapManager()->GetNavMeshQuery(bot->GetMapId());
                if (query)
                {
                    float point[3] = {y, corrected.getZ(), x}, nearest[3];
                    dtQueryFilter filter;
                    filter.setIncludeFlags(NAV_GROUND);
                    filter.setExcludeFlags(NAV_WATER | NAV_MAGMA | NAV_SLIME | NAV_STEEP_SLOPES);
                    if (PathInfo::FindWalkPoly(query, point, filter, nearest) &&
                        std::fabs(nearest[1] - corrected.getZ()) < 1.0f &&
                        bot->TeleportTo(bot->GetMapId(), x, y, corrected.getZ(), bot->GetOrientation(), TELE_TO_NOT_LEAVE_COMBAT))
                    {
                        sLog.outString("GROUND_RECOVERY bot=%s guid=%u map=%u z=%.3f corrected_z=%.3f source=%s",
                            bot->GetName(), bot->GetGUIDLow(), bot->GetMapId(), z, corrected.getZ(), source.c_str());
                        ai->Reset(true);
                        return true;
                    }
                }
            }
        }
    }

    // Default action if no specific source is matched
    if (source.empty())
    {
        ai->TellDebug(master, "Unstuck: No specific source, resetting.", "debug unstuck");
        return ai->DoSpecificAction("reset", event, true);
    }

    // Handle move stuck scenarios
    if (source.find("move stuck") != std::string::npos)
    {
        ai->TellDebug(master, "Unstuck: Move stuck detected, resetting.", "debug unstuck");
        return ai->DoSpecificAction("reset", event, true);
    }

    // Handle long move stuck scenarios
    if (source.find("move long stuck") != std::string::npos)
    {
        ai->TellDebug(master, "Unstuck: Long move stuck detected, attempting hearthstone or repop.", "debug unstuck");
        if (AI_VALUE2(bool, "action useful", "hearthstone") && bot->IsAlive())
        {
            return ai->DoSpecificAction("hearthstone", event, true);
        }
        else
        {
            return ai->DoSpecificAction("repop", event, true);
        }
    }

    // Handle combat stuck scenarios
    if (source.find("combat stuck") != std::string::npos)
    {
        ai->TellDebug(master, "Unstuck: Combat stuck detected, resetting position.", "debug unstuck");
        return ai->DoSpecificAction("reset", event, true);
    }

    // Handle long combat stuck scenarios
    if (source.find("combat long stuck") != std::string::npos)
    {
        ai->TellDebug(master, "Unstuck: Long combat stuck detected, attempting hearthstone or repop.", "debug unstuck");
        if (AI_VALUE2(bool, "action useful", "hearthstone") && bot->IsAlive())
        {
            return ai->DoSpecificAction("hearthstone", event, true);
        }
        else
        {
            return ai->DoSpecificAction("repop", event, true);
        }
    }

    // Fallback to reset if no specific condition is met
    ai->TellDebug(master, "Unstuck: Fallback to reset action.", "debug unstuck");
    return ai->DoSpecificAction("reset", event, true);
}
