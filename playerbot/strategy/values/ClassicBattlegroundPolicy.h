#pragma once
#include <array>
#include <vector>
#include <cstdint>

namespace ai::ClassicBattlegroundPolicy
{
    // Relative to our team. Never infer team from GUID or from node number.
    enum class Node { Neutral, Ours, OurAssault, Theirs, EnemyAssault, Destroyed };
    inline unsigned Arathi(unsigned slot, unsigned count, bool alliance,
        unsigned elapsedMs, const std::array<Node, 5>& nodes)
    {
        const unsigned home = alliance ? 0 : 2;
        // Seed all four useful opening objectives even with a small roster.
        static const unsigned opening[] = {0, 1, 3, 4, 1, 3, 4, 1, 0, 3, 4, 1, 3, 4, 1};
        if (elapsedMs < 90000)
            return opening[slot % 15] == 0 ? home : opening[slot % 15];

        std::vector<unsigned> owned, threatened, attack;
        for (unsigned node = 0; node < 5; ++node)
        {
            if (nodes[node] == Node::Ours || nodes[node] == Node::OurAssault) owned.push_back(node);
            else if (nodes[node] == Node::EnemyAssault) threatened.push_back(node);
            else attack.push_back(node);
        }
        // A small guard at each owned/assaulted flag; remaining squads retake
        // threatened flags and attack. A lost home node is a real objective.
        if (!owned.empty() && slot < owned.size() && count > owned.size()) return owned[slot];
        unsigned mobile = slot >= owned.size() ? slot - unsigned(owned.size()) : slot;
        if (!threatened.empty() && (attack.empty() || mobile % 3 != 2))
            return threatened[mobile % threatened.size()];
        if (!attack.empty()) return attack[mobile % attack.size()];
        if (!threatened.empty()) return threatened[mobile % threatened.size()];
        return owned.empty() ? home : owned[slot % owned.size()];
    }

    inline unsigned TowerSquadSize(unsigned count)
    {
        return count >= 30 ? 6 : (count >= 12 ? 3 : (count >= 5 ? 1 : 0));
    }
    struct ApproachPoint { float x, y, z; };
    inline bool WarsongOpening(bool alliance, unsigned lane, unsigned& step,
        float x, float y, float z, ApproachPoint& next)
    {
        // Existing WSG path-graph points: tunnel vs side door/ramp. No forced
        // graveyard jump, teleport or coordinate shortcut through the walls.
        static const ApproachPoint routes[2][2][3] = {
            {{{965.049f,1459.15f,338.076f},{1030.1f,1459.58f,330.204f},{1124.37f,1462.28f,315.853f}},
             {{1029.14f,1387.49f,340.836f},{1057.67f,1487.55f,342.537f},{1068.15f,1548.1f,321.446f}}},
            {{{1502.27f,1457.52f,347.589f},{1442.5f,1459.7f,342.024f},{1348.02f,1461.06f,323.167f}},
             {{1443.55f,1533.4f,343.148f},{1405.34f,1432.33f,345.792f},{1354.17f,1411.56f,324.327f}}}
        };
        // Never turn a bot that already reached the field back toward base.
        if ((alliance ? x < 1350.0f : x > 1120.0f) || z < 328.0f) { step=3; return false; }
        while (step < 3)
        {
            next=routes[alliance ? 1 : 0][lane % 2][step];
            const float dx=x-next.x,dy=y-next.y,dz=z-next.z;
            if (dx*dx+dy*dy+dz*dz > 36.0f) return true;
            ++step;
        }
        return false;
    }
    inline bool AlteracApproach(bool alliance, unsigned instance, unsigned& observedInstance,
        unsigned& step, float x, float y, float z, float goalX, ApproachPoint& next)
    {
        // Waypoints already present in the AV path graph. Separate the two
        // offensive approaches instead of routing both armies into one scrum.
        // Native pathfinding and the normal engagement checks still apply.
        if (instance != observedInstance || (alliance ? x > 0.0f : x < -600.0f))
        { observedInstance = instance; step = 0; }
        if (alliance ? goalX >= -500.0f : goalX <= -170.0f) return false;
        if (alliance ? x < -450.0f : x > 0.0f) { step = 2; return false; }
        if (alliance ? x < -200.0f : x > -220.0f) step = step < 1 ? 1 : step;
        const ApproachPoint routeA[] = {{-147.596f,-253.494f,6.78363f},{-432.235f,-273.793f,20.6022f}};
        const ApproachPoint routeH[] = {{-244.184f,-433.898f,20.024f},{-104.292f,-455.243f,22.3564f}};
        const ApproachPoint* route = alliance ? routeA : routeH;
        while (step < 2)
        {
            next = route[step];
            const float dx=x-next.x,dy=y-next.y,dz=z-next.z;
            if (dx*dx+dy*dy+dz*dz > 144.0f) return true;
            ++step;
        }
        return false;
    }
    inline bool GeneralReady(const std::array<Node, 4>& towers, Node finalGrave)
    {
        // An assault is not a destroyed tower: its marshal is still alive.
        for (Node state : towers) if (state != Node::Destroyed) return false;
        return finalGrave == Node::Ours;
    }
}
