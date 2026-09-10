#ifndef LIVING_GUILD_SUPPLY_POLICY_H
#define LIVING_GUILD_SUPPLY_POLICY_H
#include <algorithm>
#include <cstdint>
#include <string>
namespace livingguild {
inline uint32_t SupplyOutstanding(uint32_t target,uint32_t bank,uint32_t reserved,uint32_t transit) {
    const uint64_t available=bank>reserved?bank-reserved:0;
    const uint64_t committed=available+transit;
    return committed>=target?0:target-uint32_t(committed);
}
inline bool SupplyTerminal(const std::string& phase) {
    return phase=="completed"||phase=="cancelled"||phase=="failed";
}
inline bool SupplyClaimable(bool spare,bool tradeable,bool reserved,uint32_t count,uint32_t outstanding) {
    return spare&&tradeable&&!reserved&&count&&outstanding;
}
inline bool SupplyCity(uint32_t zone,bool alliance) {
    return alliance?(zone==1519||zone==1537||zone==1657||zone==3557):
        (zone==1637||zone==1638||zone==1497||zone==3487);
}
}
#endif
