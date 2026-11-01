#pragma once

#include <algorithm>
#include <cmath>
#include "playerbot/strategy/values/HazardsValue.h"

namespace ai
{
    inline bool UsesClassicRaidEscapeAdmission(uint32 map)
    {
#ifdef MANGOSBOT_ZERO
        return map == 409 || map == 249 || map == 469 || map == 533 ||
            map == 309 || map == 509 || map == 531;
#else
        return false;
#endif
    }

    inline bool IsFiniteMovementPoint(const WorldPosition& point, uint32 map)
    {
        return point.getMapId() == map && std::isfinite(point.getX()) &&
            std::isfinite(point.getY()) && std::isfinite(point.getZ());
    }

    // Test entire segments, not just waypoints. A bot already inside a hazard
    // may move outward, but must not cut through its center or re-enter it.
    inline bool IsHazardSafeSegment(const WorldPosition& from, const WorldPosition& to,
        const std::list<HazardPosition>& hazards)
    {
        if (!IsFiniteMovementPoint(from, to.getMapId()) || !IsFiniteMovementPoint(to, from.getMapId()))
            return false;
        const double dx = double(to.getX()) - from.getX();
        const double dy = double(to.getY()) - from.getY();
        const double dz = double(to.getZ()) - from.getZ();
        const double lengthSquared = dx * dx + dy * dy + dz * dz;
        for (const auto& hazard : hazards)
        {
            if (hazard.first.getMapId() != from.getMapId() || hazard.second <= 0.0f)
                continue;
            if (!IsFiniteMovementPoint(hazard.first, from.getMapId()) || !std::isfinite(hazard.second))
                return false;
            const double x = double(from.getX()) - hazard.first.getX();
            const double y = double(from.getY()) - hazard.first.getY();
            const double z = double(from.getZ()) - hazard.first.getZ();
            const double radiusSquared = double(hazard.second) * hazard.second;
            const double startSquared = x * x + y * y + z * z;
            const double dot = x * dx + y * dy + z * dz;
            if (startSquared <= radiusSquared)
            {
                if (dot < -0.0001) // Moving farther into a hazard is not escape.
                    return false;
                continue;
            }
            const double t = lengthSquared > 0 ? std::clamp(-dot / lengthSquared, 0.0, 1.0) : 0.0;
            const double nearX = x + t * dx, nearY = y + t * dy, nearZ = z + t * dz;
            if (nearX * nearX + nearY * nearY + nearZ * nearZ <= radiusSquared)
                return false;
        }
        return true;
    }

    // A native ground-spell center can be slightly above the walking floor.
    // Directly below its center an outward uphill leg has a negative 3D dot
    // product despite leaving the fire horizontally. Permit at most 0.01yd
    // of radial convergence, only for a verified live MC ground object and
    // only while already inside it. Other hazards retain strict admission.
    inline bool IsMoltenCoreGroundEscapeSegment(const WorldPosition& from, const WorldPosition& to,
        const std::list<HazardPosition>& hazards, const std::list<HazardPosition>& nativeGround)
    {
        if (IsHazardSafeSegment(from, to, hazards)) return true;
#ifdef MANGOSBOT_ZERO
        if (from.getMapId() != 409 || !IsFiniteMovementPoint(from, 409) ||
            !IsFiniteMovementPoint(to, 409)) return false;
        const double dx = double(to.getX()) - from.getX(), dy = double(to.getY()) - from.getY();
        const double dz = double(to.getZ()) - from.getZ();
        const double lengthSquared = dx*dx + dy*dy + dz*dz;
        if (lengthSquared <= 0 || std::fabs(dz) > 2.0) return false;
        for (const auto& hazard : hazards)
        {
            if (IsHazardSafeSegment(from, to, std::list<HazardPosition>{hazard})) continue;
            if (!IsFiniteMovementPoint(hazard.first, 409) || !std::isfinite(hazard.second) ||
                hazard.second <= 0) return false;
            const bool native = std::any_of(nativeGround.begin(), nativeGround.end(), [&](const HazardPosition& ground) {
                // The generic hazard cache can also contain this same fire
                // at its unbuffered spell radius. A concentric footprint
                // wholly contained in the verified native ground footprint
                // cannot add danger; retain the native slope escape for both.
                // Never admit a larger or differently located hazard here.
                return ground.first.getMapId() == 409 && std::isfinite(ground.second) &&
                    hazard.second <= ground.second &&
                    std::fabs(ground.first.getX()-hazard.first.getX()) < 0.001f &&
                    std::fabs(ground.first.getY()-hazard.first.getY()) < 0.001f &&
                    std::fabs(ground.first.getZ()-hazard.first.getZ()) < 0.001f;
            });
            if (!native) return false;
            const double x = double(from.getX()) - hazard.first.getX(), y = double(from.getY()) - hazard.first.getY();
            const double z = double(from.getZ()) - hazard.first.getZ();
            const double startSquared = x*x + y*y + z*z;
            if (startSquared > double(hazard.second)*hazard.second || std::fabs(z) > 2.0 ||
                x*dx + y*dy < -0.0001 || dx*dx + dy*dy < 0.0001) return false;
            const double t = std::clamp(-(x*dx+y*dy+z*dz)/lengthSquared, 0.0, 1.0);
            const double nx=x+t*dx, ny=y+t*dy, nz=z+t*dz;
            if (std::sqrt(startSquared)-std::sqrt(nx*nx+ny*ny+nz*nz) > 0.01 ||
                (x+dx)*(x+dx)+(y+dy)*(y+dy)+(z+dz)*(z+dz) < startSquared) return false;
        }
        return true;
#else
        return false;
#endif
    }

    // A walking path can start by projecting the actor onto the navigation
    // floor at exactly the same XY. That correction is not an inward walk.
    // Use only for the first native waypoint of a ground-fire escape. The
    // remaining route and endpoint still require the ordinary hazard checks.
    inline bool IsHazardSafeGroundProjection(const WorldPosition& from, const WorldPosition& to,
        const std::list<HazardPosition>& hazards)
    {
        if (IsHazardSafeSegment(from, to, hazards)) return true;
        if (!IsFiniteMovementPoint(from, to.getMapId()) || !IsFiniteMovementPoint(to, from.getMapId()) ||
            std::hypot(to.getX() - from.getX(), to.getY() - from.getY()) > 0.001f ||
            std::fabs(to.getZ() - from.getZ()) > 2.0f) return false;
        for (const auto& hazard : hazards)
        {
            if (hazard.first.getMapId() != from.getMapId() || hazard.second <= 0) continue;
            if (!IsFiniteMovementPoint(hazard.first, from.getMapId()) || !std::isfinite(hazard.second)) return false;
            // Never project a safe actor into a new hazard, including on a
            // different floor. Only an already hazardous start gets this rule.
            const double x = double(from.getX()) - hazard.first.getX();
            const double y = double(from.getY()) - hazard.first.getY();
            const double z = double(from.getZ()) - hazard.first.getZ();
            if (x*x + y*y + z*z > double(hazard.second)*hazard.second &&
                !IsHazardSafeSegment(from, to, std::list<HazardPosition>{hazard})) return false;
        }
        return true;
    }
    // Deep Breath is one footprint made from overlapping native spell areas.
    // Escaping their union can approach a peripheral circle while still moving
    // out of the deepest danger. Requiring outward movement from every circle
    // independently can reject every usable escape. This admission is only for
    // Classic Onyxia's explicitly supplied breath footprint; other hazards must
    // still pass IsHazardSafeSegment separately.
    inline bool IsOnyxiaBreathSafeSegment(const WorldPosition& from, const WorldPosition& to,
        const std::list<HazardPosition>& breath, bool nativeFloorProjection = false)
    {
        if (from.getMapId() != 249 || !IsFiniteMovementPoint(from, 249) ||
            !IsFiniteMovementPoint(to, 249) || breath.empty()) return false;
        double clearance = 0;
        bool first = true;
        for (const auto& circle : breath)
        {
            if (!IsFiniteMovementPoint(circle.first, 249) ||
                !std::isfinite(circle.second) || circle.second <= 0) return false;
            const double x = double(from.getX()) - circle.first.getX();
            const double y = double(from.getY()) - circle.first.getY();
            const double z = double(from.getZ()) - circle.first.getZ();
            const double distance = std::sqrt(x*x + y*y + z*z) - circle.second;
            if (first || distance < clearance) clearance = distance;
            first = false;
        }
        if (clearance >= 0) return IsHazardSafeSegment(from, to, breath);
        if (nativeFloorProjection &&
            std::hypot(to.getX()-from.getX(), to.getY()-from.getY()) <= 0.001f &&
            std::fabs(to.getZ()-from.getZ()) <= 2.0f)
            return IsHazardSafeGroundProjection(from, to, breath);
        const double dx = double(to.getX()) - from.getX();
        const double dy = double(to.getY()) - from.getY();
        const double dz = double(to.getZ()) - from.getZ();
        const double lengthSquared = dx*dx + dy*dy + dz*dz;
        for (const auto& circle : breath)
        {
            const double x = double(from.getX()) - circle.first.getX();
            const double y = double(from.getY()) - circle.first.getY();
            const double z = double(from.getZ()) - circle.first.getZ();
            const double t = lengthSquared > 0 ? std::clamp(-(x*dx+y*dy+z*dz)/lengthSquared, 0.0, 1.0) : 0.0;
            const double nearX = x+t*dx, nearY = y+t*dy, nearZ = z+t*dz;
            if (std::sqrt(nearX*nearX+nearY*nearY+nearZ*nearZ) - circle.second < clearance - 0.0001)
                return false;
        }
        return true;
    }
}
