#pragma once

#include <algorithm>
#include <cmath>
#include "playerbot/strategy/values/HazardsValue.h"

namespace ai
{
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
}
