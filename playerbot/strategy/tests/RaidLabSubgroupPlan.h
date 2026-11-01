#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <set>
#include <tuple>
#include <vector>

namespace ai
{
    struct RaidLabMemberRole
    {
        uint64_t guid;
        bool tank, healer, provider;
    };
    // Local fixture only: balanced five-player parties, preserving every
    // native class/spec. Totems/auras and group heals retain native scope.
    inline std::vector<uint8_t> RaidLabSubgroups(const std::vector<RaidLabMemberRole>& members)
    {
        if (members.size()!=20 && members.size()!=40) return {};
        std::set<uint64_t> ids;
        for (const auto& m:members)
            if (!m.guid || !ids.insert(m.guid).second || (m.tank && m.healer)) return {};
        const size_t groups=members.size()/5;
        std::vector<size_t> order(members.size());
        for (size_t i=0;i<order.size();++i) order[i]=i;
        const auto priority=[](const RaidLabMemberRole& m) {return m.provider?0:m.healer?1:m.tank?2:3;};
        std::sort(order.begin(),order.end(),[&](size_t a,size_t b) {
            return std::make_tuple(priority(members[a]),members[a].guid)<
                   std::make_tuple(priority(members[b]),members[b].guid);
        });
        std::array<unsigned,8> counts{},healers{},tanks{},providers{};
        std::vector<uint8_t> result(members.size(),255);
        for (size_t i:order)
        {
            const auto& m=members[i];size_t chosen=groups;
            const auto score=[&](size_t g) {
                return std::make_tuple(m.provider?providers[g]:m.healer?healers[g]:m.tank?tanks[g]:0u,
                    m.tank?unsigned(providers[g]==0):0u,counts[g],g);
            };
            for (size_t g=0;g<groups;++g)
                if (counts[g]<5 && (chosen==groups || score(g)<score(chosen))) chosen=g;
            if (chosen==groups) return {};
            result[i]=uint8_t(chosen);++counts[chosen];
            healers[chosen]+=m.healer;tanks[chosen]+=m.tank;providers[chosen]+=m.provider;
        }
        return result;
    }
}
