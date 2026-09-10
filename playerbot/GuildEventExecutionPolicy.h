#ifndef LIVING_GUILD_EVENT_EXECUTION_POLICY_H
#define LIVING_GUILD_EVENT_EXECUTION_POLICY_H
#include "GuildEventPolicy.h"
namespace livingguild {
inline bool EventCommitmentDue(uint32_t starts,uint32_t ends,uint32_t now) {
    return uint64_t(starts)<=uint64_t(now)+900 && ends>now;
}
inline bool EventFormationExpired(uint32_t starts,uint32_t now) {
    // Not created_at: an event can have been on the calendar for months.
    return uint64_t(now)>uint64_t(starts)+300;
}
inline bool EventCommitmentsOverlap(uint32_t aStart,uint32_t aEnd,uint32_t bStart,uint32_t bEnd) {
    return uint64_t(aStart)<uint64_t(bEnd)+900 && uint64_t(bStart)<uint64_t(aEnd)+900;
}
inline bool MayMutateEventMovement(bool bot,bool committed,bool safe,bool unrelatedHumanParty) {
    return bot && committed && safe && !unrelatedHumanParty;
}
}
#endif
