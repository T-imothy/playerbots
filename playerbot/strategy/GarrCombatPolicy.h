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
            // Keep ownership after Garr dies. Only the selected cleanup add
            // stops receiving renewals; all other locks retain their targets.
            for (auto it = banishes.begin(); it != banishes.end();)
                if (std::find(locks.begin(), locks.end(), it->first) == locks.end() ||
                    std::find(adds.begin(), adds.end(), it->second) == adds.end()) it = banishes.erase(it);
                else ++it;
            std::set<uint32_t> held;
            for (const auto& [add, owner] : nativeBanishes)
            {
                held.insert(add);
                if (std::find(locks.begin(), locks.end(), owner) != locks.end()) banishes[owner] = add;
            }
            for (const auto& [owner, add] : banishes) held.insert(add);
            if (bossAlive)
            {
                for (uint32_t lock : locks)
                {
                    if (banishes.count(lock)) continue;
                    // Leave at least one unreserved add to kill when starting.
                    if (held.size() + 1 >= adds.size()) break;
                    for (auto it = adds.rbegin(); it != adds.rend(); ++it)
                        if (!held.count(*it))
                        { banishes[lock] = *it; held.insert(*it); break; }
                }
            }
            const auto reserved = [&](uint32_t add) {
                if (nativeBanishes.count(add)) return true;
                for (const auto& [owner, target] : banishes) if (target == add) return true;
                return false;
            };
            if (std::find(adds.begin(), adds.end(), focus) == adds.end() || (bossAlive && reserved(focus))) focus = 0;
            const auto focusAura = nativeBanishes.find(focus);
            if (!bossAlive && focusAura != nativeBanishes.end() &&
                std::find(locks.begin(), locks.end(), focusAura->second) == locks.end()) focus = 0;
            if (!focus) for (uint32_t add : adds) if (!reserved(add)) { focus = add; break; }
            if (!bossAlive && !focus)
                for (const auto& [owner, add] : banishes)
                {
                    const auto native = nativeBanishes.find(add);
                    // Human-controlled CC is never selected for auto-release.
                    if (native != nativeBanishes.end() &&
                        std::find(locks.begin(), locks.end(), native->second) == locks.end()) continue;
                    focus = add;
                    break;
                }
        }
    };
}
