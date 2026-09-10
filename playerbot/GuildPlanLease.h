#ifndef LIVING_GUILD_PLAN_LEASE_H
#define LIVING_GUILD_PLAN_LEASE_H
#include <cstdint>
#include <map>
#include <string>
namespace livingguild {
// World-thread-only bindings for the actual candidates sent in one async brief.
// A provider cannot invent a reference or reuse one after policy/leader changes.
class GuildPlanLeases {
    struct Lease {uint32_t guild,revision,leader,expires;std::string kind;};
    std::map<std::string,Lease> leases_;
public:
    void Publish(const std::string& ref,uint32_t guild,const std::string& kind,
                 uint32_t revision,uint32_t leader,uint32_t now) {
        for(auto it=leases_.begin();it!=leases_.end();)
            if(it->second.expires<=now)it=leases_.erase(it);else ++it;
        if(leases_.size()<1024)leases_[ref]={guild,revision,leader,now+90,kind};
    }
    bool Consume(const std::string& ref,uint32_t guild,const std::string& kind,
                 uint32_t revision,uint32_t leader,uint32_t now) {
        auto it=leases_.find(ref);if(it==leases_.end())return false;
        const Lease lease=it->second;leases_.erase(it);
        return lease.expires>now&&lease.guild==guild&&lease.kind==kind&&
               lease.revision==revision&&lease.leader==leader;
    }
};
}
#endif
