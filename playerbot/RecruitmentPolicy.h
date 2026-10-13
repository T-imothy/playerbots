#pragma once

#include <cstdint>
#include <cmath>

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
        constexpr unsigned MaxPreparationReceipts = 8192;
        constexpr unsigned MaxPreparationReceiptsPerPlayer = 4096;
        constexpr unsigned DiagnosticEventsPerSecond = 32;
        constexpr unsigned DiagnosticEventsPerPlayerPerSecond = 8;
        constexpr float PreparationDistance = 10.0f;

        enum class ArrivalCondition
        {
            Ready, RequesterNotInWorld, BotNotInWorld, RequesterTransferring,
            BotTransferring, BotDead, DifferentMap, DifferentInstance, TooFar, NoLineOfSight
        };
        struct ArrivalResult
        {
            ArrivalCondition condition = ArrivalCondition::Ready;
            bool requesterLocationKnown = false, botLocationKnown = false;
            uint32_t requesterMap = 0, requesterInstance = 0, botMap = 0, botInstance = 0;
            bool distanceKnown = false;
            float distance = 0.0f, limit = PreparationDistance;
            bool Ready() const { return condition == ArrivalCondition::Ready; }
        };
        inline const char* ArrivalReason(ArrivalCondition condition)
        {
            switch (condition)
            {
                case ArrivalCondition::Ready: return "ok";
                case ArrivalCondition::RequesterNotInWorld: return "requester_not_in_world";
                case ArrivalCondition::BotNotInWorld: return "bot_not_in_world";
                case ArrivalCondition::RequesterTransferring: return "requester_transferring";
                case ArrivalCondition::BotTransferring: return "bot_transferring";
                case ArrivalCondition::BotDead: return "bot_dead";
                case ArrivalCondition::DifferentMap: return "different_map";
                case ArrivalCondition::DifferentInstance: return "different_instance";
                case ArrivalCondition::TooFar: return "too_far";
                case ArrivalCondition::NoLineOfSight: return "no_line_of_sight";
            }
            return "unknown";
        }

        inline bool Expired(uint64_t now, uint64_t expires) { return now >= expires; }
        inline bool ValidSize(unsigned size)
        {
            return size == 5 || size == 10 || size == 20 || size == 25 || size == 40;
        }
        inline bool HasVacancy(unsigned members, unsigned selected, bool raid)
        {
            return ValidSize(selected) && members < selected && members < (raid ? 40u : 5u);
        }
        inline bool Arrived(bool inWorld, bool transferring, bool alive,
            uint32_t map, uint32_t instance, uint32_t targetMap, uint32_t targetInstance,
            float distance, bool lineOfSight)
        {
            // Arrival describes location; combat readiness belongs to preparation.
            return inWorld && !transferring && alive && map == targetMap &&
                instance == targetInstance && distance <= PreparationDistance && lineOfSight;
        }
    }
}
