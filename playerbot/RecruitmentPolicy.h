#pragma once

#include <cstdint>

namespace ai
{
    // Shared bounds for legacy commands and the optional versioned protocol.
    namespace RecruitmentPolicy
    {
        constexpr unsigned MaxIncoming = 256;
        constexpr unsigned MaxIncomingPerPlayer = 16;
        constexpr unsigned MaxPending = 256;
        constexpr unsigned MaxPendingPerPlayer = 40;
        constexpr unsigned MaxReceipts = 8192;
        constexpr unsigned MaxReceiptsPerPlayer = 512;
        constexpr unsigned CommandsPerTick = 8;
        constexpr unsigned TickMilliseconds = 250;
        constexpr unsigned ScanPerRequest = 128;
        constexpr unsigned ResultsPerRequest = 8;
        constexpr unsigned InviteSeconds = 15;
        constexpr unsigned SummonSeconds = 40;
        constexpr unsigned ReserveSeconds = 15;
        constexpr unsigned ReceiptSeconds = 600;
        constexpr unsigned LegacyPreparationSeconds = 60;

        inline bool Expired(uint64_t now, uint64_t expires) { return now >= expires; }
        inline bool ValidSize(unsigned size)
        {
            return size == 5 || size == 10 || size == 20 || size == 25 || size == 40;
        }
        inline bool HasVacancy(unsigned members, unsigned selected, bool raid)
        {
            return ValidSize(selected) && members < selected && members < (raid ? 40u : 5u);
        }
        inline bool Arrived(bool inWorld, bool transferring, bool alive, bool combat,
            uint32_t map, uint32_t instance, uint32_t targetMap, uint32_t targetInstance,
            float distance, bool lineOfSight)
        {
            return inWorld && !transferring && alive && !combat && map == targetMap &&
                instance == targetInstance && distance <= 10.0f && lineOfSight;
        }
    }
}
