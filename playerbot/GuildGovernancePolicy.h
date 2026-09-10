#ifndef LIVING_GUILD_GOVERNANCE_POLICY_H
#define LIVING_GUILD_GOVERNANCE_POLICY_H
#include <cstdint>
#include <string>
#include <vector>
namespace livingguild {
enum Permission : uint32_t { Recruit=1, Promote=2, Demote=4, Configure=8, Delegate=16 };
struct Policy {
    uint32_t leader=0, revision=1;
    bool recruitment=false, events=false, supplies=false, promotions=false;
    uint32_t memberHours=24, veteranDays=7, memberCredits=1, veteranCredits=3;
    uint32_t cooldownHours=72, dailyLimit=3;
};
inline bool Id(const std::string& value) {
    if (value.empty() || value.size()>64) return false;
    for (unsigned char c:value) if (!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
        (c>='0'&&c<='9')||c=='-'||c=='_'||c==':')) return false;
    return true;
}
inline bool Number(const std::string& value,uint32_t& result,uint32_t maximum=0xffffffffu) {
    if(value.empty()||value.size()>10) return false;
    uint64_t number=0;
    for(char c:value) { if(c<'0'||c>'9') return false; number=number*10+(c-'0'); if(number>maximum) return false; }
    result=uint32_t(number); return true;
}
inline std::vector<std::string> Split(const std::string& input) {
    std::vector<std::string> fields; size_t start=0;
    do { size_t end=input.find('\t',start); fields.push_back(input.substr(start,end==std::string::npos?end:end-start));
        if(end==std::string::npos) break;
        start=end+1;
    } while(fields.size()<20);
    return fields;
}
inline bool Delegated(const Policy& p,const std::string& duty) {
    return duty=="recruitment"?p.recruitment:duty=="events"?p.events:
        duty=="supplies"?p.supplies:duty=="promotions"?p.promotions:false;
}
inline std::string PromotionBlocker(const Policy& p,uint32_t now,uint32_t joined,uint32_t last,
    uint32_t credits,uint32_t creditedDays,bool veteran,uint32_t dailyCount) {
    if(!joined || now<joined) return "unknown_tenure";
    if(uint64_t(now-joined)<(veteran?uint64_t(p.veteranDays)*86400:uint64_t(p.memberHours)*3600)) return "membership_time";
    const uint32_t required=veteran?p.veteranCredits:p.memberCredits;
    if(credits<required || (veteran&&creditedDays<required)) return "verified_participation";
    if(last&&(now<last||uint64_t(now-last)<uint64_t(p.cooldownHours)*3600)) return "promotion_cooldown";
    if(dailyCount>=p.dailyLimit) return "guild_daily_limit";
    return "eligible";
}
}
#endif
