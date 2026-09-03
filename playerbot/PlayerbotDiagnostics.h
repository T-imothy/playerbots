#pragma once

#include "Common.h"

#include <atomic>
#include <mutex>
#include <string>
#include <unordered_map>

namespace ai
{
    enum class PlayerbotDiagnosticOutcome : uint8
    {
        Ok,
        Failed,
        Impossible,
        Useless,
        Unknown,
        SuppressedFailed,
        SuppressedImpossible
    };

    struct PlayerbotEngineSample
    {
        uint64 durationUs = 0;
        uint32 evaluations = 0;
        uint32 queueStart = 0;
        uint32 queueEnd = 0;
        uint32 ok = 0;
        uint32 failed = 0;
        uint32 impossible = 0;
        uint32 useless = 0;
        uint32 unknown = 0;
        uint32 suppressedFailed = 0;
        uint32 suppressedImpossible = 0;
        bool minimal = false;
        bool actionExecuted = false;
    };

    struct PlayerbotManagerSnapshot
    {
        uint32 botsOnline = 0;
        uint32 botsTarget = 0;
        uint32 botsAvailable = 0;
        uint32 botsActive = 0;
        uint32 realPlayers = 0;
        uint32 activityPercent = 0;
        uint32 worldDiff = 0;
        uint32 worldAverageDiff = 0;
        uint32 worldMaxDiff = 0;
        uint32 characterDbDelay = 0;
        uint32 pendingDbResults = 0;
        uint32 pendingDbOperations = 0;
        uint32 loadedEventBots = 0;
        uint32 cachedEvents = 0;
        uint32 trackedMaps = 0;
        uint64 privateBytes = 0;
        uint64 cachedValues = 0;
        uint64 cachedActions = 0;
        uint64 cachedTriggers = 0;
        uint64 cachedStrategies = 0;
        uint64 expiredValuesReleased = 0;
        uint64 actionFailureCacheEntries = 0;
        uint64 actionFailureCachePeakEntries = 0;
        uint64 expiredActionFailureEntries = 0;
        uint64 evictedActionFailureEntries = 0;
    };

    class PlayerbotDiagnostics
    {
    public:
        static PlayerbotDiagnostics& instance();

        bool IsEnabled() const;
        bool ShouldSampleEngineTick();
        bool IsFlushDue() const;

        void RecordEngineSample(const PlayerbotEngineSample& sample);
        void RecordFailure(const std::string& action, const std::string& source, PlayerbotDiagnosticOutcome outcome);
        void RecordManagerPass(uint64 durationUs, uint32 processScans, uint32 processCalls,
            uint32 loginScans, uint32 loginRequests, bool loginBackpressure);
        void RecordEventCacheLoad(uint32 rows, uint64 durationUs);
        void RecordEventMutation(bool removed);
        void RecordDatabasePing();
        void RecordTeleportFailure();
        void Flush(const PlayerbotManagerSnapshot& snapshot);

    private:
        PlayerbotDiagnostics() = default;
        PlayerbotDiagnostics(const PlayerbotDiagnostics&) = delete;
        PlayerbotDiagnostics& operator=(const PlayerbotDiagnostics&) = delete;

        struct FailureBucket
        {
            std::string action;
            std::string source;
            PlayerbotDiagnosticOutcome outcome = PlayerbotDiagnosticOutcome::Failed;
            uint64 count = 0;
        };

        static void UpdateMax(std::atomic<uint64>& target, uint64 value);
        static const char* OutcomeName(PlayerbotDiagnosticOutcome outcome);
        static std::string Sanitize(const std::string& value);
        void EnsureSessionHeader();

        std::atomic<uint64> engineSamples{0};
        std::atomic<uint64> engineDurationUs{0};
        std::atomic<uint64> engineMaxDurationUs{0};
        std::atomic<uint64> engineEvaluations{0};
        std::atomic<uint64> engineMaxEvaluations{0};
        std::atomic<uint64> engineQueueStart{0};
        std::atomic<uint64> engineQueueEnd{0};
        std::atomic<uint64> engineMaxQueue{0};
        std::atomic<uint64> engineNoAction{0};
        std::atomic<uint64> engineMinimal{0};
        std::atomic<uint64> outcomeOk{0};
        std::atomic<uint64> outcomeFailed{0};
        std::atomic<uint64> outcomeImpossible{0};
        std::atomic<uint64> outcomeUseless{0};
        std::atomic<uint64> outcomeUnknown{0};
        std::atomic<uint64> suppressedFailed{0};
        std::atomic<uint64> suppressedImpossible{0};
        std::atomic<uint64> exactFailed{0};
        std::atomic<uint64> exactImpossible{0};

        std::atomic<uint64> managerPasses{0};
        std::atomic<uint64> managerDurationUs{0};
        std::atomic<uint64> managerMaxDurationUs{0};
        std::atomic<uint64> processScans{0};
        std::atomic<uint64> processCalls{0};
        std::atomic<uint64> loginScans{0};
        std::atomic<uint64> loginRequests{0};
        std::atomic<uint64> loginBackpressurePasses{0};
        std::atomic<uint64> eventCacheLoads{0};
        std::atomic<uint64> eventCacheRows{0};
        std::atomic<uint64> eventCacheLoadUs{0};
        std::atomic<uint64> eventCacheMaxLoadUs{0};
        std::atomic<uint64> eventUpserts{0};
        std::atomic<uint64> eventDeletes{0};
        std::atomic<uint64> databasePings{0};
        std::atomic<uint64> teleportFailures{0};
        std::atomic<uint64> failureKeyOverflow{0};

        mutable std::mutex failureMutex;
        std::unordered_map<std::string, FailureBucket> failures;
        uint64 lastFlushMs = 0;
        bool sessionHeaderWritten = false;
    };
}

#define sPlayerbotDiagnostics ai::PlayerbotDiagnostics::instance()
