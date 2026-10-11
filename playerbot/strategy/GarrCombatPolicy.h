#pragma once
#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <vector>

namespace ai
{
    // Encounter-local ownership. Removing a killed DPS add must not reshuffle
    // the remaining warlocks' banishes. Native auras remain authoritative.
    struct GarrAllocation
    {
        std::map<uint32_t, uint32_t> banishes; // warlock -> Firesworn
        uint32_t focus = 0;

        void Reconcile(const std::vector<uint32_t>& locks, const std::vector<uint32_t>& adds,
            const std::map<uint32_t, uint32_t>& nativeBanishes, bool bossAlive)
        {
            if (!bossAlive) { banishes.clear(); }
            else
            {
                for (auto it = banishes.begin(); it != banishes.end();)
                    if (std::find(locks.begin(), locks.end(), it->first) == locks.end() ||
                        std::find(adds.begin(), adds.end(), it->second) == adds.end()) it = banishes.erase(it);
                    else ++it;
                std::set<uint32_t> reserved;
                for (const auto& [add, owner] : nativeBanishes)
                {
                    reserved.insert(add); // Respect human banishes too.
                    if (std::find(locks.begin(), locks.end(), owner) != locks.end()) banishes[owner] = add;
                }
                for (const auto& [owner, add] : banishes) reserved.insert(add);
                for (uint32_t lock : locks)
                {
                    if (banishes.count(lock)) continue;
                    // Leave at least one unreserved add to kill when starting.
                    if (reserved.size() + 1 >= adds.size()) break;
                    for (auto it = adds.rbegin(); it != adds.rend(); ++it)
                        if (!reserved.count(*it))
                        { banishes[lock] = *it; reserved.insert(*it); break; }
                }
            }
            const auto reserved = [&](uint32_t add) {
                if (nativeBanishes.count(add)) return true;
                for (const auto& [owner, target] : banishes) if (target == add) return true;
                return false;
            };
            if (std::find(adds.begin(), adds.end(), focus) == adds.end() || reserved(focus)) focus = 0;
            if (!focus) for (uint32_t add : adds) if (!reserved(add)) { focus = add; break; }
        }
    };
}
