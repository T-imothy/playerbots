#include "playerbot/playerbot.h"
#include "AsyncBotChat.h"
#include "MapTaskExecutor.h"
#include "ObjectAccessor.h"
#include "BotSlots.h"
#include "PlayerbotAI.h"
#include <atomic>
#include <chrono>
#include <deque>
#include <mutex>

namespace
{
    std::unique_ptr<MapTaskExecutor> workers;
    std::atomic<uint32> jobs{0};
    uint32 workerLimit = 0;
    struct Delivery
    {
        ObjectGuid guid;
        uint32 account;
        std::weak_ptr<BotChatLifetime> lifetime;
        std::future<BotChatPackets> future;
        BotChatPackets packets;
        bool incoming;
        ai::EventOwner recipient;
        size_t index = 0;
        std::chrono::steady_clock::time_point next{};
    };
    std::mutex deliveryMutex;
    std::deque<Delivery> submitted, pending;
    std::atomic<uint32> deliveries{0};
}

void StartPlayerbotChatWorkers(uint32 limit)
{
    // Started before any map jobs; stopped only after map owners join.
    workerLimit = limit;
    if (limit) workers = std::make_unique<MapTaskExecutor>(limit);
}

std::future<BotChatPackets> SubmitPlayerbotChatGeneration(std::function<BotChatPackets()> work)
{
    uint32 count = jobs.load();
    while (count < workerLimit)
        if (jobs.compare_exchange_weak(count, count + 1))
        {
            auto task = std::make_shared<std::packaged_task<BotChatPackets()>>(std::move(work));
            auto result = task->get_future();
            try
            {
                // At most workerLimit outstanding jobs: this cannot hit the
                // native executor's 256-queued-job inline fallback. No network
                // work or sleeping occurs on a map or world thread.
                workers->Submit([task] {
                    struct Release { ~Release() { --jobs; } } release;
                    (*task)();
                });
            }
            catch (...) { --jobs; throw; }
            return result;
        }
    // Preserve the existing saturated-generation behavior (empty response),
    // but reject before allocating an OS thread or starting network work.
    std::promise<BotChatPackets> empty;
    empty.set_value({});
    return empty.get_future();
}

void QueuePlayerbotChatPackets(ObjectGuid guid, uint32 account,
    std::weak_ptr<BotChatLifetime> lifetime, std::future<BotChatPackets> packets, bool incoming, ai::EventOwner recipient)
{
    if (!packets.valid() || lifetime.expired()) return;
    uint32 count = deliveries.load();
    while (count < 256)
        if (deliveries.compare_exchange_weak(count, count + 1))
        {
            try
            {
                std::lock_guard<std::mutex> lock(deliveryMutex);
                submitted.push_back({guid, account, std::move(lifetime), std::move(packets), {}, incoming, recipient});
            }
            catch (...) { --deliveries; throw; }
            return;
        }
}

void UpdatePlayerbotChatPackets()
{
    // World maintenance after joined map jobs; all session resolution and
    // delivery stay on the native lifetime owner. Futures from packaged_task
    // never join a worker on destruction (including logout cancellation).
    {
        std::lock_guard<std::mutex> lock(deliveryMutex);
        while (!submitted.empty())
        {
            pending.push_back(std::move(submitted.front()));
            submitted.pop_front();
        }
    }
    auto const started = std::chrono::steady_clock::now();
    size_t const visits = pending.size();
    uint32 sent = 0;
    for (size_t n = 0; n < visits && sent < 32; ++n)
    {
        if (std::chrono::steady_clock::now() - started >= std::chrono::milliseconds(2)) break;
        Delivery delivery = std::move(pending.front());
        pending.pop_front();
        auto lifetime = delivery.lifetime.lock();
        bool done = !lifetime;
        if (!done && delivery.future.valid() &&
            delivery.future.wait_for(std::chrono::seconds(0)) == std::future_status::ready)
        {
            try { delivery.packets = delivery.future.get(); }
            catch (std::exception const& error)
            {
                sLog.outError("BotLLM: response worker failed (%s)", error.what());
            }
            done = delivery.packets.empty();
            if (!done)
                delivery.next = std::chrono::steady_clock::now() +
                    std::chrono::milliseconds(delivery.incoming ? delivery.packets.front().second : 0);
        }
        if (!done && !delivery.future.valid() && std::chrono::steady_clock::now() >= delivery.next)
        {
            Player* player = sObjectAccessor.FindPlayer(delivery.guid);
            WorldSession* session = player ? player->GetSession() : nullptr;
            PlayerbotAI* ai = player ? GetBotAI(player) : nullptr;
            done = !session || !ai || session->GetAccountId() != delivery.account ||
                ai->GetChatLifetime().lock() != lifetime || session->isLogingOut();
            if (!done)
            {
                auto const& packet = delivery.packets[delivery.index];
                if (delivery.recipient.HasOwner())
                {
                    Player* target = delivery.recipient.Get();
                    WorldSession* targetSession = target ? target->GetSession() : nullptr;
                    if (!targetSession || !targetSession->HasNetworkTransport() || targetSession->isLogingOut())
                    {
                        --deliveries;
                        continue;
                    }
                    targetSession->SendPacket(&packet.first);
                }
                else if (delivery.incoming)
                    session->QueuePacket(std::make_unique<WorldPacket>(packet.first));
                else
                    ai->HandleBotOutgoingPacket(packet.first);
                ++sent;
                ++delivery.index;
                done = delivery.index == delivery.packets.size();
                if (!done)
                    delivery.next = std::chrono::steady_clock::now() + std::chrono::milliseconds(
                        delivery.incoming ? delivery.packets[delivery.index].second : packet.second);
            }
        }
        if (done) --deliveries;
        else pending.push_back(std::move(delivery));
    }
}

void StopPlayerbotChatWorkers()
{
    workerLimit = 0;
    workers.reset(); // Join value-only jobs while config/logging still exist.
    std::lock_guard<std::mutex> lock(deliveryMutex);
    submitted.clear();
    pending.clear();
    deliveries = 0;
}
