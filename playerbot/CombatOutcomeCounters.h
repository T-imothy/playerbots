#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>
namespace ai::diagnostics
{
inline constexpr std::array<std::string_view, 10> Stages = {
    "spell_check", "cast_wrapper_result", "action_execute", "action_impossible",
    "action_useless", "action_unknown", "suppressed_impossible", "suppressed_failed",
    "travel_result", "other"};
inline constexpr std::array<std::string_view, 6> TravelReasons = {
    "not_preparing", "invalid_future", "search_pending", "search_exception", "no_destination", "selected"};
// Fixed dimensions preserve every selected outcome even when detailed keys fill.
// Result slot 256 is unknown/out of range; this does not extrapolate sampling.
struct OutcomeCounters
{
    static constexpr size_t Classes=12, Results=257;
    std::array<uint64_t, Classes*Stages.size()*Results> values{};
    void Add(uint32_t cls, std::string_view stage, int32_t result)
    {
        size_t s=Stages.size()-1;
        for(size_t i=0;i<Stages.size();++i) if(Stages[i]==stage){s=i;break;}
        size_t c=cls<Classes?cls:0;
        size_t v=result>=0&&result<256?size_t(result):256;
        ++values[(c*Stages.size()+s)*Results+v];
    }
    template<class F> void Each(F&& f) const
    {
        for(size_t c=0;c<Classes;++c)for(size_t s=0;s<Stages.size();++s)for(size_t v=0;v<Results;++v)
            if(auto n=values[(c*Stages.size()+s)*Results+v])f(c,Stages[s],v==256?-1:int(v),n);
    }
};
}
