#ifndef LIVING_GUILD_EVENT_POLICY_H
#define LIVING_GUILD_EVENT_POLICY_H
#include "GuildGovernancePolicy.h"
namespace livingguild {
struct EventDefinition {
    std::string id,kind,title,details;
    uint32_t revision=0,starts=0,ends=0,target=0;
};
inline bool TerminalEvent(const std::string& state) {
    return state=="completed"||state=="cancelled"||state=="failed";
}
inline uint32_t WeeklyEventLimit(uint32_t members) { return members<=20?1:members<=45?2:3; }
inline uint32_t UtcWeekStart(uint32_t epoch) {
    // UTC Monday, independent of the realm host's locale and DST.
    const uint64_t shifted=uint64_t(epoch)+3*86400;
    const uint64_t rounded=(shifted/604800)*604800;
    return rounded>=3*86400?uint32_t(rounded-3*86400):0;
}
inline std::string ValidateEvent(const EventDefinition& e,uint32_t now) {
    if(!Id(e.id)||e.title.empty()||e.title.find_first_not_of(' ')==std::string::npos||e.title.size()>48||e.details.size()>72)
        return "invalid_event_text";
    for(const auto* text:{&e.title,&e.details})
        for(unsigned char c:*text) if(c<32||c=='|') return "invalid_event_text";
    if(e.kind!="social"&&e.kind!="quest"&&e.kind!="dungeon"&&e.kind!="supply"&&e.kind!="leveling")
        return "unsupported_event_type";
    if(uint64_t(e.starts)+3600<now||uint64_t(e.starts)>uint64_t(now)+370*86400||
        uint64_t(e.ends)<uint64_t(e.starts)+1800||uint64_t(e.ends)>uint64_t(e.starts)+7*86400)
        return "invalid_event_time";
    if((e.kind=="quest"||e.kind=="dungeon"||e.kind=="supply")&&!e.target)
        return "concrete_objective_required";
    if((e.kind=="social"||e.kind=="leveling")&&e.target) return "unexpected_event_target";
    return "";
}
inline bool NeedsRenewedAcceptance(const EventDefinition& before,const EventDefinition& after) {
    return before.starts!=after.starts||before.ends!=after.ends||before.kind!=after.kind||before.target!=after.target;
}
}
#endif
