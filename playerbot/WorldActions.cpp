#include "playerbot/playerbot.h"
#include "WorldActions.h"
#include "BotSlots.h"
#include "PlayerbotAI.h"
#include "ObjectAccessor.h"
#include <chrono>
#include <map>

namespace ai {
thread_local bool WorldActions::mapExecution = false;
thread_local bool WorldActions::continuationExecution = false;
WorldActions& WorldActions::Instance() { static WorldActions actions; return actions; }
bool WorldActions::Enqueue(Player* bot, std::string const& action, Event const& event, Continuation continuation)
{
    if (!bot || action.empty() || !bot->IsInWorld() || bot->IsBeingTeleported() ||
        !bot->GetSession() || !bot->GetSession()->IsHeadless()) return false;
    PlayerbotAI* ai = GetBotAI(bot);
    if (!ai) return false;
    std::lock_guard<std::mutex> lock(mutex);
    auto found = perBot.find(bot->GetGUIDLow());
    if (pending.size() >= 1024 || (found != perBot.end() && found->second >= 8)) { ++rejected; return false; }
    Request request{bot->GetObjectGuid(), bot->GetSession()->GetAccountId(), ai->GetChatLifetime(),
        {bot->GetMapId(), bot->GetInstanceId(), bot->GetMapWorkGeneration()}, action, event, std::move(continuation)};
    auto count = perBot.try_emplace(bot->GetGUIDLow(), 0);
    try { pending.push_back(std::move(request)); }
    catch (...) { if (count.second) perBot.erase(count.first); throw; }
    ++count.first->second;
    ++accepted;
    return true;
}
void WorldActions::Drain(uint32_t diff)
{
    // Called only from the post-map WorldScript hook. Core retains sessions
    // through each callback, including a callback requesting its own logout.
    const uint32_t budgetMs = DrainBudgetMs(diff);
    lastBudgetMs.store(budgetMs, std::memory_order_relaxed);
    auto start = std::chrono::steady_clock::now();
    uint32_t drained = 0;
    for (unsigned n = 0; n < 256; ++n)
    {
        if (n && std::chrono::steady_clock::now()-start >= std::chrono::milliseconds(budgetMs)) break;
        std::unique_ptr<Request> request;
        {
            std::lock_guard<std::mutex> lock(mutex);
            if (pending.empty()) break;
            request = std::make_unique<Request>(std::move(pending.front())); pending.pop_front();
            auto count = perBot.find(request->guid.GetCounter());
            if (!--count->second) perBot.erase(count);
        }
        ++drained;
        auto lifetime = request->lifetime.lock();
        if (!lifetime || !request->event.IsOwnerAvailable()) { ++cancelled; continue; }
        Player* bot = sObjectAccessor.FindPlayer(request->guid);
        auto* session = bot ? bot->GetSession() : nullptr;
        PlayerbotAI* ai = bot ? GetBotAI(bot) : nullptr;
        if (!session || !session->IsHeadless() || session->isLogingOut() ||
            session->GetAccountId() != request->account || !ai || ai->GetChatLifetime().lock() != lifetime ||
            bot->IsBeingTeleported() || !request->stamp.Matches(bot->GetMapId(), bot->GetInstanceId(),
                bot->GetMapWorkGeneration(), bot->IsInWorld())) { ++cancelled; continue; }
        struct StopScope {
            StopScope() { sWorld.BeginHeadlessStopDeferral(); }
            ~StopScope() { sWorld.EndHeadlessStopDeferral(); }
        } scope;
        ++executed;
        try {
            if (request->continuation)
            {
                struct ContinuationScope {
                    bool& flag; bool previous;
                    ContinuationScope(bool& value) : flag(value), previous(value) { flag = true; }
                    ~ContinuationScope() { flag = previous; }
                } continuationScope(continuationExecution);
                request->continuation(*ai);
            }
            else ai->DoSpecificAction(request->action, request->event, true);
        }
        catch (ByteBufferException const&) {
            sLog.outError("ManTech: malformed world action %s guid=%u", request->action.c_str(), request->guid.GetCounter());
        }
    }
    lastDrained.store(drained, std::memory_order_relaxed);
    lastDrainUs.store(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - start).count()), std::memory_order_relaxed);
}
WorldActions::Stats WorldActions::GetStats()
{
    std::lock_guard<std::mutex> lock(mutex);
    std::map<std::string, size_t> counts;
    std::string top; size_t maximum = 0;
    for (auto const& request : pending)
        if (++counts[request.action] > maximum) { maximum = counts[request.action]; top = request.action; }
    return {pending.size(), accepted.load(), rejected.load(), executed.load(), cancelled.load(), top, maximum, lastBudgetMs.load(), lastDrained.load(), lastDrainUs.load()};
}
void WorldActions::Clear() { std::lock_guard<std::mutex> lock(mutex); pending.clear(); perBot.clear(); }
}
