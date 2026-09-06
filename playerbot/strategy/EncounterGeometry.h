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
