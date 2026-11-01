#pragma once
#include <cstdint>

namespace ai
{
    // Player-observable timing, not access to the boss AI's future timer.
    // Native Classic Panic: first 6-10sec, then 30-35sec after each cast.
    struct MagmadarPanicClock
    {
        uint64_t boss = 0;
        uint32_t instance = 0, firstSeen = 0, observedStart = 0;
        int64_t combat = 0;
        bool initialized = false, observed = false;

        bool Update(uint32_t now, uint64_t bossGuid, uint32_t instanceId,
                    int64_t combatStart, int32_t observedAuraAge, uint32_t observedCombatAge = 0)
        {
            if (!initialized || boss != bossGuid || instance != instanceId || combat != combatStart)
            {
                boss = bossGuid; instance = instanceId; combat = combatStart;
                // Encounter strategy installation may occur after engagement.
                // Use the bot's observed elapsed combat, not installation time.
                // Cap stale timestamps well beyond the first preparation band.
                firstSeen = now - (observedCombatAge > 60000 ? 60000 : observedCombatAge);
                initialized = true; observed = false;
            }
            if (observedAuraAge >= 0 && observedAuraAge <= 8000)
            {
                const uint32_t start = now - uint32_t(observedAuraAge);
                // The same aura is sampled repeatedly. Its expiry must not
                // keep moving the next preparation window later.
                if (!observed || int32_t(start - observedStart) > 1000)
                { observedStart = start; observed = true; }
            }
            const uint32_t anchor = observed ? observedStart : firstSeen;
            const int32_t elapsed = int32_t(now - anchor);
            // Two seconds for a native stance/GCD transition. Berserker Rage
            // lasts ten seconds, covering the complete known five-second band.
            return observed ? elapsed >= 28000 && elapsed <= 35000 :
                              elapsed >= 4000 && elapsed <= 10000;
        }
    };
}
