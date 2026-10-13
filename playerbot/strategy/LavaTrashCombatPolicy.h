#pragma once
#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <vector>

namespace ai
{
    // Separate from Garr: trash can initially hold every elemental. A released
    // GUID is never assigned again during this pull, even if another pack joins.
    struct LavaTrashAllocation
    {
        std::map<uint32_t, uint32_t> banishes;
        std::set<uint32_t> released;
        uint32_t focus = 0;

        bool Reserved(uint32_t target) const
        {
            if (released.count(target)) return false;
            for (const auto& assignment : banishes)
                if (assignment.second == target) return true;
            return false;
        }

        void Reconcile(const std::vector<uint32_t>& locks, const std::vector<uint32_t>& elementals,
            const std::map<uint32_t, uint32_t>& nativeBanishes, bool priorityAlive)
        {
            const auto alive = [&](uint32_t id) { return std::find(elementals.begin(), elementals.end(), id) != elementals.end(); };
            const auto available = [&](uint32_t id) { return std::find(locks.begin(), locks.end(), id) != locks.end(); };
            for (auto it = banishes.begin(); it != banishes.end();)
                if (!available(it->first) || !alive(it->second) || released.count(it->second)) it = banishes.erase(it);
                else ++it;
            std::set<uint32_t> held;
            for (const auto& aura : nativeBanishes)
            {
                if (!alive(aura.first)) continue;
                held.insert(aura.first);
                if (available(aura.second) && !released.count(aura.first))
                {
                    // Native ownership wins over a pending assignment. Remove
                    // an old duplicate rather than give two locks the same mob.
                    for (auto it = banishes.begin(); it != banishes.end();)
                        if (it->second == aura.first && it->first != aura.second) it = banishes.erase(it);
                        else ++it;
                    banishes[aura.second] = aura.first;
                }
            }
            for (const auto& assignment : banishes) held.insert(assignment.second);
            if (priorityAlive)
                for (uint32_t owner : locks)
                {
                    if (banishes.count(owner)) continue;
                    for (uint32_t target : elementals)
                        if (!held.count(target) && !released.count(target))
                        { banishes[owner] = target; held.insert(target); break; }
                }
            if (!alive(focus)) focus = 0;
            if (priorityAlive) return; // Renew retained CC, including both pulled packs.
            const auto humanHeld = [&](uint32_t target) {
                auto aura = nativeBanishes.find(target);
                return aura != nativeBanishes.end() && !available(aura->second);
            };
            if (focus && humanHeld(focus)) focus = 0;
            if (!focus)
            {
                for (uint32_t target : elementals)
                    if (!humanHeld(target) && !Reserved(target)) { focus = target; break; }
                if (!focus)
                    for (uint32_t target : elementals)
                        if (!humanHeld(target)) { focus = target; break; }
            }
            if (focus)
            {
                released.insert(focus);
                for (auto it = banishes.begin(); it != banishes.end();)
                    if (it->second == focus) it = banishes.erase(it);
                    else ++it;
            }
        }
    };
}
