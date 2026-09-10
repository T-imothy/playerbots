#pragma once

#include <algorithm>
#include <cmath>
#include <vector>

namespace ai { namespace party_positioning {
struct Point
{
    float x, y, z;
};

inline float DistanceSquared(const Point& a, const Point& b)
{
    const float x = a.x - b.x, y = a.y - b.y, z = a.z - b.z;
    return x*x + y*y + z*z;
}

inline Point Between(const Point& a, const Point& b, float t)
{
    return {a.x + (b.x-a.x)*t, a.y + (b.y-a.y)*t, a.z + (b.z-a.z)*t};
}

// Sample segments, not just navmesh vertices. The extra half-yard covers the
// gap between samples; visibility is evaluated at each prospective position.
// Starting inside a boundary permits escape, but never moving deeper/re-entry.
template<class Visible>
bool CrossesBoundary(const std::vector<Point>& path, const Point& center,
    float radius, Visible visible)
{
    if (path.empty() || radius <= 0.0f)
        return false;
    radius += 0.5f;
    const float radiusSq = radius * radius;
    float previous = DistanceSquared(path.front(), center);
    bool escaping = previous < radiusSq && visible(path.front());
    for (size_t i = 1; i < path.size(); ++i)
    {
        const int steps = std::max(1, int(std::ceil(std::sqrt(DistanceSquared(path[i-1], path[i])))));
        for (int j = 1; j <= steps; ++j)
        {
            const Point p = Between(path[i-1], path[i], float(j) / steps);
            const float distance = DistanceSquared(p, center);
            const bool inside = distance < radiusSq && visible(p);
            if (inside && (!escaping || distance + 0.01f < previous))
                return true;
            if (!inside)
                escaping = false;
            previous = distance;
        }
    }
    return false;
}

struct Score
{
    unsigned extraPulls = 0;
    float preference = 0;

    bool BetterThan(const Score& other) const
    {
        return extraPulls < other.extraPulls ||
            (extraPulls == other.extraPulls && preference < other.preference);
    }
};

inline bool FitsRange(float distance, float minimum, float maximum,
    float current, bool retreat)
{
    return distance >= minimum && distance <= maximum + 0.5f &&
        (!retreat || distance >= current + 1.0f);
}

inline bool UsefulApproach(float distance, float minimum, float current)
{
    return distance >= minimum && distance <= current - 1.0f;
}
}}
