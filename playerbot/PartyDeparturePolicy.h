#pragma once
#include <cstdint>
#include <map>
#include <set>

namespace living_party_departure
{
// The electorate is the persistent human roster, including offline humans.
inline unsigned Required(const std::set<uint32_t>& humans, uint32_t leader)
{
    return humans.count(leader) ? 1u : unsigned(humans.size() / 2 + 1);
}
inline bool MayVote(const std::set<uint32_t>& humans, uint32_t leader, uint32_t voter)
{
    return humans.count(voter) && (!humans.count(leader) || leader == voter);
}
inline bool Approved(const std::set<uint32_t>& humans, uint32_t leader,
    const std::map<uint32_t, bool>& votes)
{
    unsigned yes = 0;
    for (const auto& vote : votes)
        if (vote.second && MayVote(humans, leader, vote.first)) ++yes;
    return !humans.empty() && yes >= Required(humans, leader);
}
}
