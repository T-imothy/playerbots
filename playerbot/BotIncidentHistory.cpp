#include "playerbot/playerbot.h"
#include "BotIncidentHistory.h"
#include "strategy/values/BotReliabilityValue.h"
#include <mutex>
#include <vector>
#include <cstdio>
#include <cerrno>

using namespace ai;
namespace
{
struct Record
{
    uint32 bot, map, instance, duration, count;
    BotIncidentKind kind;
    const char* state;
    int64 timestamp;
};
std::mutex historyMutex;
std::vector<Record> pending;
uint64 dropped = 0;
const char* Name(BotIncidentKind kind)
{
    switch (kind)
    {
        case BotIncidentKind::Dead: return "dead_long";
        case BotIncidentKind::Movement: return "movement_no_progress";
        case BotIncidentKind::ActionLoop: return "repeated_action_failure";
        default: return "unreachable_target";
    }
}
void Emit(BotIncidentState& state, BotIncidentKind kind, const char* status, uint32 now)
{
    auto& episode = state.episodes[size_t(kind)];
    std::lock_guard<std::mutex> lock(historyMutex);
    if (pending.size() >= 4096) { ++dropped; return; }
    pending.push_back({state.bot, state.map, state.instance, uint32(now - episode.started),
        episode.count, kind, status, int64(time(nullptr))});
}
void Observe(BotIncidentState& state, BotIncidentKind kind, bool condition, uint32 threshold, uint32 now)
{
    auto& episode = state.episodes[size_t(kind)];
    if (!condition)
    {
        if (episode.active) Emit(state, kind, "resolved", now);
        episode = {}; return;
    }
    if (!episode.count) episode.started = now;
    episode.last = now; ++episode.count;
    if (!episode.active && uint32(now - episode.started) >= threshold)
    { episode.active = true; Emit(state, kind, "opened", now); }
}
BotIncidentState& State(PlayerbotAI* ai)
{
    return ai->GetAiObjectContext()->GetValue<BotReliabilityState&>("bot reliability")->Get().incidents;
}
}

void BotIncidentHistory::Sample(PlayerbotAI* ai)
{
    if (!sPlayerbotAIConfig.incidentHistory) return;
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || bot->IsBeingTeleported()) return;
    auto& state = State(ai);
    const uint32 now = WorldTimer::getMSTime();
    if (state.bot && uint32(now - state.sampled) < 1000) return;
    if (state.bot && (state.map != bot->GetMapId() || state.instance != bot->GetInstanceId() ||
        uint32(now - state.sampled) > 10000)) Close(state);
    state.bot = bot->GetGUIDLow(); state.map = bot->GetMapId(); state.instance = bot->GetInstanceId();
    const float dx = bot->GetPositionX() - state.x, dy = bot->GetPositionY() - state.y,
        dz = bot->GetPositionZ() - state.z;
    const bool progressed = dx * dx + dy * dy + dz * dz > 4.0f;
    // An observation, not a stuck verdict: ignore intentional idle, casting,
    // incapacitation and melee contact. No movement changes are made here.
    const bool movementExpected = bot->IsAlive() && !bot->IsStopped() &&
        !bot->IsNonMeleeSpellCasted(true) && bot->CanFreeMove() &&
        (!bot->GetVictim() || !bot->CanReachWithMeleeAttack(bot->GetVictim()));
    Observe(state, BotIncidentKind::Dead, !bot->IsAlive(), 300000, now);
    Observe(state, BotIncidentKind::Movement, movementExpected && !progressed, 30000, now);
    if (progressed || !movementExpected)
    { state.x = bot->GetPositionX(); state.y = bot->GetPositionY(); state.z = bot->GetPositionZ(); }
    for (auto kind : {BotIncidentKind::ActionLoop, BotIncidentKind::Unreachable})
        if (state.episodes[size_t(kind)].count && uint32(now - state.episodes[size_t(kind)].last) > 30000)
            Observe(state, kind, false, 0, now);
    state.sampled = now;
}

void BotIncidentHistory::ActionResult(PlayerbotAI* ai, const std::string& action, bool success)
{
    if (!sPlayerbotAIConfig.incidentHistory) return;
    auto& state = State(ai);
    const uint32 now = WorldTimer::getMSTime();
    if (success)
    {
        if (state.failedAction == action) { Observe(state, BotIncidentKind::ActionLoop, false, 0, now); state.failedAction.clear(); }
        return;
    }
    if (state.failedAction != action)
    { Observe(state, BotIncidentKind::ActionLoop, false, 0, now); state.failedAction = action.substr(0, 96); }
    Observe(state, BotIncidentKind::ActionLoop, true, 15000, now);
}

void BotIncidentHistory::Unreachable(PlayerbotAI* ai)
{
    if (!sPlayerbotAIConfig.incidentHistory) return;
    Sample(ai);
    Observe(State(ai), BotIncidentKind::Unreachable, true, 0, WorldTimer::getMSTime());
}

void BotIncidentHistory::Close(BotIncidentState& state)
{
    const uint32 now = WorldTimer::getMSTime();
    for (size_t i = 0; i < state.episodes.size(); ++i)
        if (state.episodes[i].active) Emit(state, BotIncidentKind(i), "observation_ended", now);
    state.episodes = {}; state.failedAction.clear();
}

void BotIncidentHistory::Flush()
{
    if (!sPlayerbotAIConfig.incidentHistory) return;
    static uint32 last = 0;
    const uint32 now = WorldTimer::getMSTime();
    if (uint32(now - last) < 10000) return;
    last = now;
    std::vector<Record> batch;
    uint64 lost;
    { std::lock_guard<std::mutex> lock(historyMutex); batch.swap(pending); lost = dropped; dropped = 0; }
    if (batch.empty() && !lost) return;
    std::string directory = sConfig.GetStringDefault("LogsDir");
    if (!directory.empty() && directory.back() != '/' && directory.back() != '\\') directory += '/';
    const std::string path = directory + "PlayerbotIncidents.jsonl";
    FILE* file = fopen(path.c_str(), "ab+");
    if (!file) { std::lock_guard<std::mutex> lock(historyMutex); dropped += batch.size() + lost; return; }
    fseek(file, 0, SEEK_END);
    const long size = ftell(file);
    if (size < 0) { fclose(file); return; }
    if (size > 16 * 1024 * 1024)
    {
        fclose(file);
        const std::string old = path + ".1";
        if ((std::remove(old.c_str()) != 0 && errno != ENOENT) || std::rename(path.c_str(), old.c_str()) != 0) return;
        file = fopen(path.c_str(), "ab");
        if (!file) return;
    }
    // Bounded event records, no player chat/account data. I/O runs on the
    // existing manager update, never inside individual map-worker samples.
    for (const auto& record : batch)
        fprintf(file, "{\"time\":%lld,\"bot\":%u,\"map\":%u,\"instance\":%u,\"kind\":\"%s\",\"state\":\"%s\",\"duration_ms\":%u,\"observations\":%u}\n",
            static_cast<long long>(record.timestamp), record.bot, record.map, record.instance,
            Name(record.kind), record.state, record.duration, record.count);
    if (lost) fprintf(file, "{\"time\":%lld,\"dropped_records\":%llu}\n", static_cast<long long>(time(nullptr)), static_cast<unsigned long long>(lost));
    fclose(file);
}
