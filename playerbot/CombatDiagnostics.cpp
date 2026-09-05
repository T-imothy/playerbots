#include "playerbot/playerbot.h"
#include "CombatDiagnostics.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotAI.h"
#include "Config/Config.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cerrno>
#include <map>
#include <mutex>
#include <sstream>
#include <vector>

using namespace ai;
namespace
{
    std::mutex combatMutex;
    std::map<std::string, uint64> buckets;
    std::vector<std::string> traces;
    uint64 droppedKeys = 0, droppedTraces = 0, sequence = 0;
    thread_local const std::string* currentAction = nullptr;
    std::string Clean(std::string value)
    {
        value.resize(std::min<size_t>(value.size(), 96));
        for (char& c : value)
            if (c == '"' || c == '\r' || c == '\n' || c == '\t') c = '_';
        return value;
    }
    uint64 Milliseconds()
    {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    }
    const char* Expansion()
    {
#ifdef MANGOSBOT_ZERO
        return "classic";
#elif defined(MANGOSBOT_ONE)
        return "tbc";
#else
        return "wotlk";
#endif
    }
}

CombatActionContext::CombatActionContext(const std::string& name)
    : previous(currentAction), enabled(sPlayerbotAIConfig.combatDiagnosticsEnabled)
{
    if (enabled) currentAction = &name;
}
CombatActionContext::~CombatActionContext()
{
    if (enabled) currentAction = previous;
}
std::string CombatActionContext::Current()
{
    return currentAction ? *currentAction : "outside_engine_action";
}

bool CombatDiagnostics::Select(PlayerbotAI* ai)
{
    if (!sPlayerbotAIConfig.combatDiagnosticsEnabled || !sPlayerbotAIConfig.diagnosticsEnabled || !ai)
        return false;
    Player* bot = ai->GetBot();
    if (!bot || !bot->IsInWorld() || ai->IsRealPlayer()) return false;
    if (!(sPlayerbotAIConfig.combatDiagnosticsClassMask & (uint32(1) << bot->getClass()))) return false;
    // Explicit bot trace includes every observed event until the interval cap.
    if (sPlayerbotAIConfig.combatDiagnosticsTraceBot == bot->GetGUIDLow()) return true;
    thread_local uint32 counter = 0;
    return (++counter % sPlayerbotAIConfig.combatDiagnosticsSampleRate) == 0;
}

void CombatDiagnostics::Record(PlayerbotAI* ai, const std::string& action, const std::string& source,
    const char* stage, int32 result, uint32 spell, Unit* target)
{
    // Select must run before collecting context; disabled mode never resolves targets.
    Player* bot = ai->GetBot();
    const char* role = PlayerbotAI::IsTank(bot) ? "tank" : (PlayerbotAI::IsHeal(bot) ? "healer" : (ai->IsRanged(bot) ? "ranged" : "melee"));
    std::ostringstream key;
    key << "class=" << uint32(bot->getClass()) << " level=" << uint32(bot->GetLevel())
        << " role=" << role << " combat=" << bot->IsInCombat() << " stage=" << stage
        << " result=" << result << " spell=" << spell << " action=\"" << Clean(action)
        << "\" source=\"" << Clean(source) << '"';
    if (std::string(stage) == "spell_check" && result >= 0)
        key << " reason=\"" << Clean(GetSpellCastResultString(static_cast<SpellCastResult>(result))) << '"';
    const uint32 guid = bot->GetGUIDLow();
    // A deterministic small cohort provides examples, not population-wide sequences.
    const bool trace = sPlayerbotAIConfig.combatDiagnosticsTraceBot ?
        guid == sPlayerbotAIConfig.combatDiagnosticsTraceBot : guid % 256 == 0;
    std::string detail;
    if (trace)
    {
        std::ostringstream out;
        out << " time_ms=" << Milliseconds() << " bot=" << guid << " map=" << bot->GetMapId()
            << " instance=" << bot->GetInstanceId() << " target_kind=";
        if (!target) out << "none_or_unobserved";
        else if (target == bot) out << "self";
        else if (target == bot->GetPet()) out << "pet";
        else out << "other_unit";
        out << " target=" << (target ? target->GetObjectGuid().GetRawValue() : 0);
        if (target) out << " reaction=" << int32(static_cast<Unit*>(bot)->GetReactionTo(target));
        if (target && bot->GetMap() == target->GetMap()) out << " distance=" << bot->GetDistance(target);
        out << ' ' << key.str();
        detail = out.str();
    }
    std::lock_guard<std::mutex> guard(combatMutex);
    const std::string name = key.str();
    auto found = buckets.find(name);
    if (found != buckets.end()) ++found->second;
    else if (buckets.size() < sPlayerbotAIConfig.combatDiagnosticsMaxKeys) buckets.emplace(name, 1);
    else ++droppedKeys;
    if (trace)
    {
        if (traces.size() < sPlayerbotAIConfig.combatDiagnosticsMaxTraces)
            traces.push_back("seq=" + std::to_string(++sequence) + detail);
        else ++droppedTraces;
    }
}

void CombatDiagnostics::Flush()
{
    if (!sPlayerbotAIConfig.combatDiagnosticsEnabled) return;
    std::map<std::string, uint64> batch;
    std::vector<std::string> detail;
    uint64 keyDrops, traceDrops;
    {
        std::lock_guard<std::mutex> guard(combatMutex);
        batch.swap(buckets);
        detail.swap(traces);
        keyDrops = droppedKeys; traceDrops = droppedTraces;
        droppedKeys = droppedTraces = 0;
    }
    // Only the existing manager flush thread performs file I/O, never AI workers.
    std::string directory = sConfig.GetStringDefault("LogsDir");
    if (!directory.empty() && directory.back() != '/' && directory.back() != '\\') directory += '/';
    const std::string path = directory + "PlayerbotCombat.log";
    const std::string previous = path + ".1";
    FILE* file = fopen(path.c_str(), "ab+");
    if (!file) return;
    fseek(file, 0, SEEK_END);
    long offset = ftell(file);
    if (offset < 0) { fclose(file); return; }
    uint64 size = offset;
    const uint64 limit = uint64(sPlayerbotAIConfig.combatDiagnosticsMaxFileMB) * 1024 * 1024;
    auto write = [&](const std::string& line)
    {
        if (!file) return;
        if (size + line.size() + 1 > limit)
        {
            fclose(file); file = nullptr;
            // One bounded previous generation. Do not truncate if rotation fails.
            if (std::remove(previous.c_str()) != 0 && errno != ENOENT) return;
            if (std::rename(path.c_str(), previous.c_str()) != 0) return;
            file = fopen(path.c_str(), "ab+"); size = 0;
            if (!file) return;
        }
        if (fwrite(line.data(), 1, line.size(), file) != line.size() || fputc('\n', file) == EOF)
        { fclose(file); file = nullptr; return; }
        size += line.size() + 1;
    };
    const std::string timestamp = sPlayerbotAIConfig.GetTimestampStr();
    write(timestamp + " PB_COMBAT_WINDOW expansion=" + Expansion() + " sample_rate=" +
        std::to_string(sPlayerbotAIConfig.combatDiagnosticsSampleRate) + " trace_bot=" +
        std::to_string(sPlayerbotAIConfig.combatDiagnosticsTraceBot) + " key_drops=" +
        std::to_string(keyDrops) + " trace_drops=" + std::to_string(traceDrops) +
        " completion_observed=0");
    for (const auto& entry : batch)
        write(timestamp + " PB_COMBAT_COUNT count=" + std::to_string(entry.second) + " " + entry.first);
    for (const auto& entry : detail) write(timestamp + " PB_COMBAT_TRACE " + entry);
    if (file) fclose(file);
}
