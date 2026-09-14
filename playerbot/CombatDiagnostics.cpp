#include "playerbot/playerbot.h"
#include "CombatDiagnostics.h"
#include "CombatOutcomeCounters.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotAI.h"
#include "TravelMgr.h"
#include "strategy/AiObjectContext.h"
#include "Movement/spline/MoveSpline.h"
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
    ai::diagnostics::OutcomeCounters outcomeCounters;
    std::vector<std::string> traces;
    std::vector<std::string> progress;
    uint64 droppedKeys = 0, droppedTraces = 0, sequence = 0;
    thread_local const std::string* currentAction = nullptr;
    thread_local const std::string* currentSpellName = nullptr;
    std::string Clean(std::string value)
    {
        value.resize(std::min<size_t>(value.size(), 96));
        for (char& c : value)
            if (c == '"' || c == '\r' || c == '\n' || c == '\t') c = '_';
        return value;
    }
    uint64 DiagnosticMilliseconds()
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

CombatSpellNameContext::CombatSpellNameContext(const std::string& name)
    : previous(currentSpellName), enabled(sPlayerbotAIConfig.combatDiagnosticsEnabled)
{ if (enabled) currentSpellName = &name; }
CombatSpellNameContext::~CombatSpellNameContext()
{ if (enabled) currentSpellName = previous; }
std::string CombatSpellNameContext::Current()
{ return currentSpellName ? *currentSpellName : ""; }

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
    if (std::string_view(stage) == "spell_check")
        key << " requested_spell=\"" << Clean(CombatSpellNameContext::Current()) << '\"';
    const uint32 guid = bot->GetGUIDLow();
    // A deterministic small cohort provides examples, not population-wide sequences.
    const bool trace = sPlayerbotAIConfig.combatDiagnosticsTraceBot ?
        guid == sPlayerbotAIConfig.combatDiagnosticsTraceBot : guid % 256 == 0;
    std::string detail;
    if (trace)
    {
        std::ostringstream out;
        out << " time_ms=" << DiagnosticMilliseconds() << " bot=" << guid << " map=" << bot->GetMapId()
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
    outcomeCounters.Add(bot->getClass(), stage, result);
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

void CombatDiagnostics::RecordProgress(PlayerbotAI* ai)
{
    if (!sPlayerbotAIConfig.combatDiagnosticsEnabled || !sPlayerbotAIConfig.diagnosticsEnabled || !ai)
        return;
    Player* bot = ai->GetBot();
    if (!bot || !bot->IsInWorld() || ai->IsRealPlayer()) return;
    const uint32 guid = bot->GetGUIDLow();
    if (sPlayerbotAIConfig.combatDiagnosticsTraceBot ?
        guid != sPlayerbotAIConfig.combatDiagnosticsTraceBot : guid % 256 != 0) return;
    std::ostringstream out;
    out << "time_ms=" << DiagnosticMilliseconds() << " bot=" << guid
        << " generation=" << bot->GetMapWorkGeneration() << " map=" << bot->GetMapId()
        << " instance=" << bot->GetInstanceId() << " zone=" << bot->GetZoneId()
        << " x=" << bot->GetPositionX() << " y=" << bot->GetPositionY() << " z=" << bot->GetPositionZ()
        << " level=" << uint32(bot->GetLevel()) << " xp=" << bot->GetUInt32Value(PLAYER_XP)
        << " alive=" << bot->IsAlive() << " combat=" << bot->IsInCombat()
        << " moving=" << bot->IsMoving() << " spline=" << (bot->movespline && !bot->movespline->Finalized())
        << " casting=" << bot->IsNonMeleeSpellCasted(true) << " mail=" << bot->GetMailSize()
        << " action_delay_ms=" << ai->GetAIInternalUpdateDelay()
        << " minimal_delay_ms=" << ai->GetBackgroundMinimalDelay();
    auto* context = ai->GetAiObjectContext();
    if (context && context->HasValue("travel target"))
        if (auto* value = context->GetValue<TravelTarget*>("travel target"))
            if (auto* target = value->LazyGet())
                out << " travel_status=" << uint32(target->GetStatus()) << " travel_entry=" << target->GetEntry();
    if (context && context->HasValue("next rpg action"))
        if (auto* value = context->GetValue<std::string>("next rpg action"))
            out << " rpg=\"" << Clean(value->LazyGet()) << '"';
    std::lock_guard<std::mutex> guard(combatMutex);
    if (progress.size() < 128) progress.push_back(out.str());
}

void CombatDiagnostics::Flush()
{
    if (!sPlayerbotAIConfig.combatDiagnosticsEnabled) return;
    std::map<std::string, uint64> batch;
    ai::diagnostics::OutcomeCounters totals;
    std::vector<std::string> detail, progressBatch;
    uint64 keyDrops, traceDrops;
    {
        std::lock_guard<std::mutex> guard(combatMutex);
        batch.swap(buckets);
        totals.values.swap(outcomeCounters.values);
        detail.swap(traces);
        progressBatch.swap(progress);
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
    // Compact totals use their own bounded two-file history so verbose examples
    // cannot evict the only evidence for a multi-hour run.
    const std::string totalsPath = directory + "PlayerbotCombatTotals.log";
    FILE* totalsFile = fopen(totalsPath.c_str(), "ab+");
    if (totalsFile)
    {
        fseek(totalsFile, 0, SEEK_END);
        if (ftell(totalsFile) >= static_cast<long>(limit))
        {
            fclose(totalsFile); totalsFile = nullptr;
            const std::string oldTotals = totalsPath + ".1";
            if ((std::remove(oldTotals.c_str()) == 0 || errno == ENOENT) &&
                std::rename(totalsPath.c_str(), oldTotals.c_str()) == 0)
                totalsFile = fopen(totalsPath.c_str(), "ab+");
        }
    }
    totals.Each([&](size_t cls, std::string_view stage, int result, uint64_t count)
    {
        std::string line = timestamp + " PB_COMBAT_TOTAL class=" + std::to_string(cls) +
            " stage=" + std::string(stage) + " result=" + std::to_string(result) +
            " count=" + std::to_string(count) + " sample_rate=" +
            std::to_string(sPlayerbotAIConfig.combatDiagnosticsSampleRate);
        if(stage == "spell_check" && result >= 0)
            line += " reason=\"" + Clean(GetSpellCastResultString(static_cast<SpellCastResult>(result))) + "\"";
        if(stage == "travel_result" && result >= 0 && size_t(result) < ai::diagnostics::TravelReasons.size())
            line += " reason=\"" + std::string(ai::diagnostics::TravelReasons[result]) + "\"";
        if(totalsFile && (fwrite(line.data(), 1, line.size(), totalsFile) != line.size() || fputc('\n', totalsFile) == EOF))
        { fclose(totalsFile); totalsFile = nullptr; }
    });
    if(totalsFile) fclose(totalsFile);
    for (const auto& entry : batch)
        write(timestamp + " PB_COMBAT_COUNT count=" + std::to_string(entry.second) + " " + entry.first);
    for (const auto& entry : detail) write(timestamp + " PB_COMBAT_TRACE " + entry);
    for (const auto& entry : progressBatch) write(timestamp + " PB_BOT_PROGRESS " + entry);
    if (file) fclose(file);
}
