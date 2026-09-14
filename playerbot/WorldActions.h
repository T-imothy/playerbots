#pragma once
#include "strategy/Event.h"
#include "AsyncBotChat.h"
#include "MapWork.h"
#include <deque>
#include <atomic>
#include <functional>
#include <mutex>
#include <unordered_map>

class PlayerbotAI;
namespace ai {
class WorldActions {
public:
    static WorldActions& Instance();
    static bool IsMapExecution() { return mapExecution; }
    static bool IsContinuation() { return continuationExecution; }
    class MapScope {
        bool previous;
    public:
        MapScope() : previous(mapExecution) { mapExecution = true; }
        ~MapScope() { mapExecution = previous; }
        MapScope(MapScope const&) = delete;
    };
    using Continuation = std::function<void(PlayerbotAI&)>;
    bool Enqueue(Player* bot, std::string const& action, Event const& event, Continuation continuation = {});
    // Preserve the nominal 8ms slice at ~30ms ticks, but do not starve the
    // serialized owner when map work lengthens ticks. No accumulated time credit.
    static uint32_t DrainBudgetMs(uint32_t diff) {
        const uint32_t proportional = diff / 4;
        return proportional < 8 ? 8 : (proportional > 32 ? 32 : proportional);
    }
    void Drain(uint32_t diff = 0);
    void Clear();
    struct Stats { size_t pending; uint64_t accepted, rejected, executed, cancelled; std::string topAction; size_t topPending; uint32_t budgetMs, lastDrained; uint64_t lastDrainUs; };
    Stats GetStats();
private:
    struct Request {
        ObjectGuid guid;
        uint32 account;
        std::weak_ptr<BotChatLifetime> lifetime;
        MapWorkStamp stamp;
        std::string action;
        Event event;
        Continuation continuation;
    };
    static thread_local bool mapExecution;
    static thread_local bool continuationExecution;
    std::atomic<uint64_t> accepted{0}, rejected{0}, executed{0}, cancelled{0};
    std::atomic<uint32_t> lastBudgetMs{8}, lastDrained{0};
    std::atomic<uint64_t> lastDrainUs{0};
    std::mutex mutex;
    std::deque<Request> pending;
    std::unordered_map<uint32, unsigned> perBot;
};
}
