#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

namespace ai { namespace encounter {
    struct Point { float x = 0, y = 0, z = 0; };

    inline float Distance2d(Point a, Point b)
    {
        return std::hypot(a.x - b.x, a.y - b.y);
    }

    // A finite segment, not its infinite extension. Portals and the boss can
    // move between phases; callers supply their current native coordinates.
    inline bool InBeam(Point player, Point portal, Point boss, float width = 2.0f)
    {
        const float dx = boss.x - portal.x, dy = boss.y - portal.y;
        const float length2 = dx * dx + dy * dy;
        if (length2 < 1.0f) return false;
        const float t = ((player.x - portal.x) * dx + (player.y - portal.y) * dy) / length2;
        if (t <= 0 || t >= 1) return false;
        const float z = portal.z + t * (boss.z - portal.z);
        return std::fabs(player.z - z) < 5.0f &&
            std::fabs((player.x - portal.x) * dy - (player.y - portal.y) * dx) <= width * std::sqrt(length2);
    }

    inline Point BeamPoint(Point portal, Point boss, float distanceFromBoss, float side = 0)
    {
        const float length = Distance2d(portal, boss);
        if (length < 1.0f) return boss;
        const float distance = std::max(0.5f, std::min(distanceFromBoss, length - 0.5f));
        const float dx = (portal.x - boss.x) / length, dy = (portal.y - boss.y) / length;
        return {boss.x + distance * dx - side * dy,
            boss.y + distance * dy + side * dx, boss.z + (portal.z - boss.z) * distance / length};
    }

    inline float LineDistance(Point position, Point origin, float orientation)
    {
        return std::fabs((position.x - origin.x) * std::sin(orientation) -
            (position.y - origin.y) * std::cos(orientation));
    }

    inline Point OutsideLine(Point position, Point origin, float orientation, float clearance, int side)
    {
        const float dx = std::cos(orientation), dy = std::sin(orientation);
        const float along = (position.x - origin.x) * dx + (position.y - origin.y) * dy;
        return {origin.x + along * dx - side * clearance * dy,
            origin.y + along * dy + side * clearance * dx, position.z};
    }

    struct Circle { Point center; float radius; };

    inline bool OutsideCircles(Point point, const std::vector<Circle>& circles)
    {
        for (const auto& circle : circles)
            if (Distance2d(point, circle.center) < circle.radius) return false;
        return true;
    }

    // Geometry only: the caller must validate native height and pathfinding.
    inline std::vector<Point> EscapeCircles(Point here, const std::vector<Circle>& circles)
    {
        if (OutsideCircles(here, circles)) return {here};
        std::vector<Point> candidates;
        for (float distance : {8.0f, 16.0f, 24.0f, 32.0f, 40.0f})
            for (unsigned step = 0; step < 16; ++step)
            {
                const float angle = step * 6.28318530717958647692f / 16;
                Point point{here.x + distance * std::cos(angle), here.y + distance * std::sin(angle), here.z};
                if (OutsideCircles(point, circles)) candidates.push_back(point);
            }
        std::stable_sort(candidates.begin(), candidates.end(), [here](Point a, Point b) {
            return Distance2d(here, a) < Distance2d(here, b);
        });
        return candidates;
    }

    // Magmadar's overlapping fires can leave a narrow exit between the coarse
    // 8/16-yard escape rings. Propose the first clear point on outward rays;
    // these are geometry candidates, never permission to skip native routes.
    inline std::vector<Point> MagmadarFireEscapeCandidates(Point here, const std::vector<Circle>& circles)
    {
        std::vector<Point> candidates;
        if (!std::isfinite(here.x) || !std::isfinite(here.y) || !std::isfinite(here.z) ||
            circles.empty() || OutsideCircles(here, circles)) return candidates;
        for (const auto& circle : circles)
            if (!std::isfinite(circle.center.x) || !std::isfinite(circle.center.y) ||
                !std::isfinite(circle.radius) || circle.radius <= 0) return candidates;
        for (unsigned step = 0; step < 64; ++step)
        {
            const double angle = step * 6.28318530717958647692 / 64;
            const double ux = std::cos(angle), uy = std::sin(angle);
            double distance = 0.5;
            bool safe = true;
            for (const auto& circle : circles)
            {
                const double x = double(here.x) - circle.center.x, y = double(here.y) - circle.center.y;
                const double radius2 = double(circle.radius) * circle.radius;
                if (x*x + y*y >= radius2) continue;
                const double dot = x*ux + y*uy;
                if (dot < 0) { safe = false; break; }
                distance = std::max(distance, -dot + std::sqrt(std::max(0.0, dot*dot + radius2 - x*x - y*y)) + 0.5);
            }
            if (!safe || distance > 40) continue;
            for (const auto& circle : circles)
            {
                const double x = double(here.x) - circle.center.x, y = double(here.y) - circle.center.y;
                const double radius2 = double(circle.radius) * circle.radius;
                if (x*x + y*y < radius2) continue;
                const double t = std::clamp(-(x*ux + y*uy), 0.0, distance);
                if ((x+t*ux)*(x+t*ux) + (y+t*uy)*(y+t*uy) < radius2)
                { safe = false; break; }
            }
            const Point point{here.x + float(ux*distance), here.y + float(uy*distance), here.z};
            if (safe && OutsideCircles(point, circles)) candidates.push_back(point);
        }
        std::stable_sort(candidates.begin(), candidates.end(), [here](Point a, Point b) {
            return Distance2d(here, a) < Distance2d(here, b);
        });
        return candidates;
    }

    // Residual overlap, not a promise that a crowded room has a fully safe
    // point. Used for distance-scaled bursts: fewer/less-deep overlaps are
    // preferable to remaining stacked when complete separation is impossible.
    inline float SpreadOverlap(Point point, const std::vector<Circle>& circles)
    {
        float overlap = 0;
        for (const auto& circle : circles)
            overlap += std::max(0.0f, circle.radius - Distance2d(point, circle.center));
        return overlap;
    }

    inline std::vector<Point> SpreadCandidates(Point here, const std::vector<Circle>& circles, uint64_t seed, float maxDistance = 24.0f)
    {
        struct Candidate { Point point; float overlap, distance; };
        std::vector<Candidate> ranked{{here, SpreadOverlap(here, circles), 0}};
        const float start = (seed % 997) * 6.28318530717958647692f / 997;
        for (float distance : {4.0f, 8.0f, 12.0f, 16.0f, 24.0f, 32.0f, 40.0f})
        {
            if (distance > maxDistance) break;
            for (unsigned step = 0; step < 16; ++step)
            {
                const float angle = start + step * 6.28318530717958647692f / 16;
                const Point point{here.x + distance * std::cos(angle),
                    here.y + distance * std::sin(angle), here.z};
                ranked.push_back({point, SpreadOverlap(point, circles), distance});
            }
        }
        std::stable_sort(ranked.begin(), ranked.end(), [](const Candidate& a, const Candidate& b) {
            return a.overlap == b.overlap ? a.distance < b.distance : a.overlap < b.overlap;
        });
        std::vector<Point> candidates;
        candidates.reserve(ranked.size());
        for (const auto& candidate : ranked) candidates.push_back(candidate.point);
        return candidates;
    }

    struct BeamMember
    {
        uint64_t guid = 0;
        bool human = false, tank = false, healer = false, caster = false, noMana = false;
        std::array<bool, 3> exhausted{{false, false, false}};
        std::array<unsigned, 3> stacks{{0, 0, 0}};
        std::array<bool, 3> inside{{false, false, false}};
    };

    inline unsigned StackLimit(const BeamMember& member, unsigned color)
    {
        // Red health loss and blue damage vulnerability require relief. Green
        // reduces maximum mana; a non-mana user does not need a mana-stack swap.
        return color == 0 ? 30 : color == 2 && member.noMana ? 100 : 25;
    }

    // Red, blue, green. Stable GUID tie breaks and a single reservation set
    // prevent each bot picking itself or one player being assigned two beams.
    inline std::array<uint64_t, 3> AssignBeams(std::vector<BeamMember> members,
        const std::array<bool, 3>& portals)
    {
        std::sort(members.begin(), members.end(), [](const BeamMember& a, const BeamMember& b) { return a.guid < b.guid; });
        std::array<uint64_t, 3> assigned{{0, 0, 0}};
        // Human decisions are observed, never controlled or replaced.
        for (unsigned color = 0; color < 3; ++color)
            if (portals[color])
                for (const auto& member : members)
                    if (member.human && member.inside[color] && !member.exhausted[color] &&
                        std::find(assigned.begin(), assigned.end(), member.guid) == assigned.end())
                    { assigned[color] = member.guid; break; }
        for (unsigned color = 0; color < 3; ++color)
        {
            if (!portals[color] || assigned[color]) continue;
            int best = -1;
            for (const auto& member : members)
            {
                if (member.human || member.exhausted[color] || member.stacks[color] >= StackLimit(member, color) ||
                    std::find(assigned.begin(), assigned.end(), member.guid) != assigned.end()) continue;
                const bool role = color == 0 ? member.tank : color == 1 ? member.caster : member.healer || member.noMana;
                if (!role) continue;
                // Retain a suitable current blocker instead of swapping on each tick.
                const int score = member.inside[color] && member.stacks[color] ? 10 :
                    color == 2 && member.noMana ? 2 : 1;
                if (score > best) { assigned[color] = member.guid; best = score; }
            }
        }
        return assigned;
    }
} }
