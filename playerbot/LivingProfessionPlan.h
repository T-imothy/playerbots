#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <utility>
#include <vector>

namespace LivingProfessions
{
constexpr std::array<unsigned,10> Skills = {{164,165,171,182,186,197,202,333,393,755}};
using Counts = std::array<unsigned,10>;
inline bool Primary(unsigned skill) { return std::find(Skills.begin(),Skills.end(),skill)!=Skills.end(); }
inline unsigned Faction(unsigned race) { return (race==1||race==3||race==4||race==7||race==11)?0:1; }
inline double Weight(unsigned skill) { return skill==186?1.6:(skill==182||skill==393)?1.1:1.0; }
inline void Add(Counts& counts,unsigned skill)
{
    auto at=std::find(Skills.begin(),Skills.end(),skill);
    if(at!=Skills.end()) ++counts[at-Skills.begin()];
}
inline std::uint64_t Mix(std::uint64_t x)
{
    x^=x>>30; x*=0xbf58476d1ce4e5b9ULL; x^=x>>27;
    x*=0x94d049bb133111ebULL; return x^(x>>31);
}
inline bool Complement(unsigned a,unsigned b)
{
    if(a>b) std::swap(a,b);
    return (a==171&&b==182)||(a==164&&b==186)||(a==186&&b==202)||
        (a==186&&b==755)||(a==165&&b==393)||(a==197&&b==333);
}
inline bool Affinity(unsigned cls,unsigned skill)
{
    switch(cls)
    {
        case 1:return skill==164||skill==202;
        case 2:return skill==164||skill==755;
        case 3:case 4:return skill==165||skill==202;
        case 5:case 8:case 9:return skill==197||skill==333;
        case 7:case 11:return skill==165||skill==171;
        default:return false;
    }
}
// New profiles only. Persist the result; never reshuffle existing careers.
inline std::pair<unsigned,unsigned> Choose(unsigned cls,std::uint64_t seed,
    const std::vector<unsigned>& learned,const Counts& counts,unsigned actors)
{
    double best=-std::numeric_limits<double>::infinity();
    std::pair<unsigned,unsigned> result={0,0};
    for(unsigned i=0;i<Skills.size();++i) for(unsigned j=i+1;j<Skills.size();++j)
    {
        unsigned a=Skills[i],b=Skills[j];
        if(std::any_of(learned.begin(),learned.end(),[&](unsigned s){return s!=a&&s!=b;})) continue;
        double score=Complement(a,b)?0.10:0;
        for(unsigned index:{i,j})
        {
            unsigned skill=Skills[index];
            if(std::find(learned.begin(),learned.end(),skill)!=learned.end())continue;
            double target=std::max(1.0,actors*2.0*Weight(skill)/10.8);
            score+=(target-counts[index])/target+(Affinity(cls,skill)?0.035:0);
        }
        score+=(Mix(seed^(std::uint64_t(a)<<32)^b)%10000)/10000.0*0.025;
        if(score>best){best=score;result={a,b};}
    }
    return result;
}
inline bool Allows(bool human,bool participant,unsigned revision,unsigned one,unsigned two,
    unsigned skill,bool known,unsigned learnedCount)
{
    if(human||!Primary(skill)||known) return true;
    if(!participant||revision==0) return true; // Preserve unreviewed/noncareer behavior.
    return learnedCount<2 && (skill==one||skill==two);
}
}
