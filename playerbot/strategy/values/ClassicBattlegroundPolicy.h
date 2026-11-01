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
    inline bool GeneralReady(const std::array<Node, 4>& towers, Node finalGrave)
    {
        // An assault is not a destroyed tower: its marshal is still alive.
        for (Node state : towers) if (state != Node::Destroyed) return false;
        return finalGrave == Node::Ours;
    }
}
