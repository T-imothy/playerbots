#include "playerbot/playerbot.h"
#include "PlayerbotDiagnostics.h"

#include "PlayerbotAIConfig.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <vector>

using namespace ai;

namespace
{
    uint64 SteadyMilliseconds()
    {
        return static_cast<uint64>(std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
    }

    uint64 Take(std::atomic<uint64>& value)
    {
        return value.exchange(0, std::memory_order_relaxed);
    }
}

PlayerbotDiagnostics& PlayerbotDiagnostics::instance()
{
    static PlayerbotDiagnostics diagnostics;
    return diagnostics;
}

bool PlayerbotDiagnostics::IsEnabled() const
{
    return sPlayerbotAIConfig.diagnosticsEnabled;
}

bool PlayerbotDiagnostics::ShouldSampleEngineTick()
{
    if (!IsEnabled())
        return false;

    thread_local uint32 sampleCounter = 0;
    const uint32 sampleRate = std::max<uint32>(1, sPlayerbotAIConfig.diagnosticsEngineSampleRate);
    return (++sampleCounter % sampleRate) == 0;
}

bool PlayerbotDiagnostics::IsFlushDue() const
{
    if (!IsEnabled())
        return false;

    const uint64 now = SteadyMilliseconds();
    const uint64 interval = std::max<uint32>(1000, sPlayerbotAIConfig.diagnosticsInterval);
    return !lastFlushMs || now - lastFlushMs >= interval;
}

void PlayerbotDiagnostics::UpdateMax(std::atomic<uint64>& target, uint64 value)
{
    uint64 current = target.load(std::memory_order_relaxed);
    while (current < value && !target.compare_exchange_weak(current, value, std::memory_order_relaxed))
    {
    }
}

void PlayerbotDiagnostics::RecordEngineSample(const PlayerbotEngineSample& sample)
{
    if (!IsEnabled())
        return;

    engineSamples.fetch_add(1, std::memory_order_relaxed);
    engineDurationUs.fetch_add(sample.durationUs, std::memory_order_relaxed);
    engineEvaluations.fetch_add(sample.evaluations, std::memory_order_relaxed);
    engineQueueStart.fetch_add(sample.queueStart, std::memory_order_relaxed);
    engineQueueEnd.fetch_add(sample.queueEnd, std::memory_order_relaxed);
    if (!sample.actionExecuted)
        engineNoAction.fetch_add(1, std::memory_order_relaxed);
    if (sample.minimal)
        engineMinimal.fetch_add(1, std::memory_order_relaxed);

    outcomeOk.fetch_add(sample.ok, std::memory_order_relaxed);
    outcomeFailed.fetch_add(sample.failed, std::memory_order_relaxed);
    outcomeImpossible.fetch_add(sample.impossible, std::memory_order_relaxed);
    outcomeUseless.fetch_add(sample.useless, std::memory_order_relaxed);
    outcomeUnknown.fetch_add(sample.unknown, std::memory_order_relaxed);
    suppressedFailed.fetch_add(sample.suppressedFailed, std::memory_order_relaxed);
    suppressedImpossible.fetch_add(sample.suppressedImpossible, std::memory_order_relaxed);

    UpdateMax(engineMaxDurationUs, sample.durationUs);
    UpdateMax(engineMaxEvaluations, sample.evaluations);
    UpdateMax(engineMaxQueue, std::max(sample.queueStart, sample.queueEnd));
}

void PlayerbotDiagnostics::RecordFailure(const std::string& action, const std::string& source, PlayerbotDiagnosticOutcome outcome)
{
    if (!IsEnabled())
        return;

    const std::string key = std::to_string(static_cast<uint32>(outcome)) + "\x1f" + action + "\x1f" + source;
    std::lock_guard<std::mutex> guard(failureMutex);
    auto existing = failures.find(key);
    if (existing != failures.end())
    {
        ++existing->second.count;
        return;
    }

    if (failures.size() >= std::max<uint32>(1, sPlayerbotAIConfig.diagnosticsMaxFailureKeys))
    {
        failureKeyOverflow.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    FailureBucket bucket;
    bucket.action = action;
    bucket.source = source;
    bucket.outcome = outcome;
    bucket.count = 1;
    failures.emplace(key, std::move(bucket));
}

void PlayerbotDiagnostics::RecordManagerPass(uint64 durationUs, uint32 processScanCount, uint32 processCallCount,
    uint32 loginScanCount, uint32 loginRequestCount, bool loginBackpressure)
{
    if (!IsEnabled())
        return;

    managerPasses.fetch_add(1, std::memory_order_relaxed);
    managerDurationUs.fetch_add(durationUs, std::memory_order_relaxed);
    processScans.fetch_add(processScanCount, std::memory_order_relaxed);
    processCalls.fetch_add(processCallCount, std::memory_order_relaxed);
    loginScans.fetch_add(loginScanCount, std::memory_order_relaxed);
    loginRequests.fetch_add(loginRequestCount, std::memory_order_relaxed);
    if (loginBackpressure)
        loginBackpressurePasses.fetch_add(1, std::memory_order_relaxed);
    UpdateMax(managerMaxDurationUs, durationUs);
}

void PlayerbotDiagnostics::RecordEventCacheLoad(uint32 rows, uint64 durationUs)
{
    if (!IsEnabled())
        return;
    eventCacheLoads.fetch_add(1, std::memory_order_relaxed);
    eventCacheRows.fetch_add(rows, std::memory_order_relaxed);
    eventCacheLoadUs.fetch_add(durationUs, std::memory_order_relaxed);
    UpdateMax(eventCacheMaxLoadUs, durationUs);
}

void PlayerbotDiagnostics::RecordEventMutation(bool removed)
{
    if (!IsEnabled())
        return;
    if (removed)
        eventDeletes.fetch_add(1, std::memory_order_relaxed);
    else
        eventUpserts.fetch_add(1, std::memory_order_relaxed);
}

void PlayerbotDiagnostics::RecordDatabasePing()
{
    if (IsEnabled())
        databasePings.fetch_add(1, std::memory_order_relaxed);
}

void PlayerbotDiagnostics::RecordTeleportFailure()
{
    if (IsEnabled())
        teleportFailures.fetch_add(1, std::memory_order_relaxed);
}

const char* PlayerbotDiagnostics::OutcomeName(PlayerbotDiagnosticOutcome outcome)
{
    switch (outcome)
    {
        case PlayerbotDiagnosticOutcome::Ok: return "ok";
        case PlayerbotDiagnosticOutcome::Failed: return "failed";
        case PlayerbotDiagnosticOutcome::Impossible: return "impossible";
        case PlayerbotDiagnosticOutcome::Useless: return "useless";
        case PlayerbotDiagnosticOutcome::Unknown: return "unknown";
        case PlayerbotDiagnosticOutcome::SuppressedFailed: return "suppressed_failed";
        case PlayerbotDiagnosticOutcome::SuppressedImpossible: return "suppressed_impossible";
    }
    return "unknown";
}

std::string PlayerbotDiagnostics::Sanitize(const std::string& value)
{
    std::string sanitized = value;
    for (char& c : sanitized)
    {
        if (c == '\r' || c == '\n' || c == '\t')
            c = ' ';
        else if (c == '"')
            c = '\'';
    }
    return sanitized;
}

void PlayerbotDiagnostics::EnsureSessionHeader()
{
    if (sessionHeaderWritten)
        return;

    if (!sPlayerbotAIConfig.openLog(sPlayerbotAIConfig.diagnosticsLogFile, "a", true))
        return;

    sessionHeaderWritten = true;
    sPlayerbotAIConfig.log(sPlayerbotAIConfig.diagnosticsLogFile,
        "%s PB_DIAG_SESSION interval_ms=%u engine_sample_rate=%u top_failures=%u max_failure_keys=%u",
        sPlayerbotAIConfig.GetTimestampStr().c_str(), sPlayerbotAIConfig.diagnosticsInterval,
        sPlayerbotAIConfig.diagnosticsEngineSampleRate, sPlayerbotAIConfig.diagnosticsTopFailures,
        sPlayerbotAIConfig.diagnosticsMaxFailureKeys);
}

void PlayerbotDiagnostics::Flush(const PlayerbotManagerSnapshot& snapshot)
{
    if (!IsEnabled() || !IsFlushDue())
        return;

    EnsureSessionHeader();
    if (!sessionHeaderWritten)
        return;

    const uint64 now = SteadyMilliseconds();
    const uint64 intervalMs = lastFlushMs ? now - lastFlushMs : 0;
    lastFlushMs = now;

    const uint64 samples = Take(engineSamples);
    const uint64 engineUs = Take(engineDurationUs);
    const uint64 maxEngineUs = Take(engineMaxDurationUs);
    const uint64 evaluations = Take(engineEvaluations);
    const uint64 maxEvaluations = Take(engineMaxEvaluations);
    const uint64 queueStart = Take(engineQueueStart);
    const uint64 queueEnd = Take(engineQueueEnd);
    const uint64 maxQueue = Take(engineMaxQueue);
    const uint64 noAction = Take(engineNoAction);
    const uint64 minimal = Take(engineMinimal);

    const uint64 managerCount = Take(managerPasses);
    const uint64 managerUs = Take(managerDurationUs);
    const uint64 maxManagerUs = Take(managerMaxDurationUs);

    const std::string timestamp = sPlayerbotAIConfig.GetTimestampStr();
    sPlayerbotAIConfig.log(sPlayerbotAIConfig.diagnosticsLogFile,
        "%s PB_DIAG_STATE interval_ms=%llu bots_online=%u bots_target=%u bots_available=%u bots_active=%u real_players=%u activity_pct=%u private_mb=%.2f world_diff_ms=%u world_avg_ms=%u world_max_ms=%u maps=%u",
        timestamp.c_str(), static_cast<unsigned long long>(intervalMs), snapshot.botsOnline, snapshot.botsTarget,
        snapshot.botsAvailable, snapshot.botsActive, snapshot.realPlayers, snapshot.activityPercent,
        static_cast<double>(snapshot.privateBytes) / (1024.0 * 1024.0), snapshot.worldDiff,
        snapshot.worldAverageDiff, snapshot.worldMaxDiff, snapshot.trackedMaps);

    sPlayerbotAIConfig.log(sPlayerbotAIConfig.diagnosticsLogFile,
        "%s PB_DIAG_ENGINE samples=%llu avg_us=%.2f max_us=%llu avg_evaluations=%.2f max_evaluations=%llu avg_queue_start=%.2f avg_queue_end=%.2f max_queue=%llu no_action=%llu minimal=%llu ok=%llu failed=%llu impossible=%llu useless=%llu unknown=%llu suppressed_failed=%llu suppressed_impossible=%llu",
        timestamp.c_str(), static_cast<unsigned long long>(samples), samples ? static_cast<double>(engineUs) / samples : 0.0,
        static_cast<unsigned long long>(maxEngineUs), samples ? static_cast<double>(evaluations) / samples : 0.0,
        static_cast<unsigned long long>(maxEvaluations), samples ? static_cast<double>(queueStart) / samples : 0.0,
        samples ? static_cast<double>(queueEnd) / samples : 0.0, static_cast<unsigned long long>(maxQueue),
        static_cast<unsigned long long>(noAction), static_cast<unsigned long long>(minimal),
        static_cast<unsigned long long>(Take(outcomeOk)), static_cast<unsigned long long>(Take(outcomeFailed)),
        static_cast<unsigned long long>(Take(outcomeImpossible)), static_cast<unsigned long long>(Take(outcomeUseless)),
        static_cast<unsigned long long>(Take(outcomeUnknown)), static_cast<unsigned long long>(Take(suppressedFailed)),
        static_cast<unsigned long long>(Take(suppressedImpossible)));

    sPlayerbotAIConfig.log(sPlayerbotAIConfig.diagnosticsLogFile,
        "%s PB_DIAG_MANAGER passes=%llu avg_us=%.2f max_us=%llu process_scans=%llu process_calls=%llu login_scans=%llu login_requests=%llu login_backpressure_passes=%llu db_delay_ms=%u db_pending_results=%u db_pending_ops=%u db_pings=%llu",
        timestamp.c_str(), static_cast<unsigned long long>(managerCount), managerCount ? static_cast<double>(managerUs) / managerCount : 0.0,
        static_cast<unsigned long long>(maxManagerUs), static_cast<unsigned long long>(Take(processScans)),
        static_cast<unsigned long long>(Take(processCalls)), static_cast<unsigned long long>(Take(loginScans)),
        static_cast<unsigned long long>(Take(loginRequests)), static_cast<unsigned long long>(Take(loginBackpressurePasses)),
        snapshot.characterDbDelay, snapshot.pendingDbResults, snapshot.pendingDbOperations,
        static_cast<unsigned long long>(Take(databasePings)));

    const uint64 cacheLoads = Take(eventCacheLoads);
    const uint64 cacheLoadUs = Take(eventCacheLoadUs);
    const uint64 cacheMaxLoadUs = Take(eventCacheMaxLoadUs);
    sPlayerbotAIConfig.log(sPlayerbotAIConfig.diagnosticsLogFile,
        "%s PB_DIAG_CACHE event_bots=%u event_entries=%u event_loads=%llu event_rows_loaded=%llu event_load_avg_us=%.2f event_load_max_us=%llu event_upserts=%llu event_deletes=%llu values=%llu actions=%llu triggers=%llu strategies=%llu expired_values_released_total=%llu teleport_failures=%llu failure_key_overflow=%llu",
        timestamp.c_str(), snapshot.loadedEventBots, snapshot.cachedEvents,
        static_cast<unsigned long long>(cacheLoads), static_cast<unsigned long long>(Take(eventCacheRows)),
        cacheLoads ? static_cast<double>(cacheLoadUs) / cacheLoads : 0.0, static_cast<unsigned long long>(cacheMaxLoadUs),
        static_cast<unsigned long long>(Take(eventUpserts)), static_cast<unsigned long long>(Take(eventDeletes)),
        static_cast<unsigned long long>(snapshot.cachedValues), static_cast<unsigned long long>(snapshot.cachedActions),
        static_cast<unsigned long long>(snapshot.cachedTriggers), static_cast<unsigned long long>(snapshot.cachedStrategies),
        static_cast<unsigned long long>(snapshot.expiredValuesReleased), static_cast<unsigned long long>(Take(teleportFailures)),
        static_cast<unsigned long long>(Take(failureKeyOverflow)));

    std::vector<FailureBucket> topFailures;
    {
        std::lock_guard<std::mutex> guard(failureMutex);
        topFailures.reserve(failures.size());
        for (const auto& entry : failures)
            topFailures.push_back(entry.second);
        failures.clear();
    }

    std::sort(topFailures.begin(), topFailures.end(), [](const FailureBucket& left, const FailureBucket& right)
    {
        return left.count > right.count;
    });

    const size_t topCount = std::min<size_t>(topFailures.size(), sPlayerbotAIConfig.diagnosticsTopFailures);
    for (size_t index = 0; index < topCount; ++index)
    {
        const FailureBucket& failure = topFailures[index];
        sPlayerbotAIConfig.log(sPlayerbotAIConfig.diagnosticsLogFile,
            "%s PB_DIAG_FAILURE rank=%u outcome=%s count=%llu action=\"%s\" source=\"%s\"",
            timestamp.c_str(), static_cast<uint32>(index + 1), OutcomeName(failure.outcome),
            static_cast<unsigned long long>(failure.count), Sanitize(failure.action).c_str(),
            Sanitize(failure.source).c_str());
    }
}
