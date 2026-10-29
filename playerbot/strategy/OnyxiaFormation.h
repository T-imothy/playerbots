#pragma once
#include "EncounterGeometry.h"

namespace ai { namespace onyxia {
    // Search the lair floor, never the entrance passage or egg tunnels. Native
    // floor, hazard, LOS and walking-path validation still decides admissibility.
    inline bool InRoom(encounter::Point p)
    {
        const float x = (p.x + 25.0f) / 52.0f, y = (p.y + 215.0f) / 44.0f;
        return x * x + y * y <= 1.0f;
    }

    inline encounter::Point Station(unsigned slot, float z)
    {
        // A shared GUID-sorted roster gives different preferred destinations
        // even when all forty players start at exactly the same position.
        const float radius = 6.5f * std::sqrt(float(slot % 40) + 0.5f);
        const float angle = float(slot % 40) * 2.39996323f;
        return {-25.0f + radius * std::cos(angle), -215.0f + radius * std::sin(angle), z};
    }

    inline bool YieldSpacing(encounter::Point here, unsigned slot, const std::vector<encounter::Point>& members, float spacing)
    {
        // Only the later GUID yields in an overlapping pair. Without this,
        // two bots can repeatedly swap the same two otherwise empty spots.
        for (unsigned i = 0; i < std::min(slot, unsigned(members.size())); ++i)
            if (encounter::Distance2d(here, members[i]) < spacing - 1.0f) return true;
        return false;
    }

    inline std::vector<encounter::Point> Candidates(encounter::Point here, unsigned slot,
        const std::vector<encounter::Circle>& neighbors, const std::vector<encounter::Circle>& danger)
    {
        const auto preferred = Station(slot, here.z);
        std::vector<encounter::Point> candidates{here, preferred};
        for (unsigned i = 0; i < 40; ++i) candidates.push_back(Station(i, here.z));
        for (float distance : {2.0f, 4.0f, 6.0f, 8.0f, 16.0f, 24.0f, 32.0f, 40.0f})
            for (unsigned step = 0; step < 24; ++step)
            {
                const float angle = float(step) * 6.283185307f / 24 + float(slot) * 2.39996323f;
                candidates.push_back({here.x + distance * std::cos(angle), here.y + distance * std::sin(angle), here.z});
            }
        candidates.erase(std::remove_if(candidates.begin(), candidates.end(), [&](encounter::Point point) {
            return !InRoom(point) || !encounter::OutsideCircles(point, danger);
        }), candidates.end());
        // Breath safety is mandatory. Spacing is best effort in the smaller
        // safe sector: never reject a breath escape because forty people cannot
        // all fit there ten yards apart. Stable preference breaks symmetric ties.
        const auto score = [&](encounter::Point point) {
            return encounter::SpreadOverlap(point, neighbors) * 20.0f +
                encounter::Distance2d(point, preferred) * 0.3f + encounter::Distance2d(point, here) * 0.1f;
        };
        std::stable_sort(candidates.begin(), candidates.end(), [&](encounter::Point a, encounter::Point b) {
            return score(a) < score(b);
        });
        return candidates;
    }
} }
