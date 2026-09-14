#include "playerbot/playerbot.h"
#include "AsyncTravel.h"
#include "MapTaskExecutor.h"
#include <atomic>
#include <memory>
#include <mutex>

namespace
{
    // Match TravelMgr's five destination permits. Admission is below the native
    // executor's 256-queued-job inline fallback, so map owners never run searches.
    constexpr unsigned TravelWorkers = 5;
    constexpr unsigned TravelCapacity = 128;
    std::mutex travelAdmission;
    std::unique_ptr<MapTaskExecutor> travelWorkers;
    std::atomic<unsigned> travelJobs{0};
}

void ai::StartPlayerbotTravelWorkers()
{
    std::lock_guard<std::mutex> lock(travelAdmission);
    if (!travelWorkers) travelWorkers = std::make_unique<MapTaskExecutor>(TravelWorkers);
}

std::future<ai::PartitionedTravelList> ai::SubmitPlayerbotTravelSearch(std::function<PartitionedTravelList()> work)
{
    std::lock_guard<std::mutex> lock(travelAdmission);
    if (!travelWorkers || travelJobs.load() >= TravelCapacity) return {};
    ++travelJobs;
    try
    {
        auto task = std::make_shared<std::packaged_task<PartitionedTravelList()>>(std::move(work));
        auto result = task->get_future();
        travelWorkers->Submit([task] {
            struct Release { ~Release() { --travelJobs; } } release;
            (*task)();
        });
        // packaged_task futures do not join on destruction. Captures contain
        // copied travel inputs, never the submitting bot, session or action.
        return result;
    }
    catch (...) { --travelJobs; throw; }
}

void ai::StopPlayerbotTravelWorkers()
{
    std::unique_ptr<MapTaskExecutor> draining;
    {
        std::lock_guard<std::mutex> lock(travelAdmission);
        draining = std::move(travelWorkers);
    }
    // OnShutdown runs after updates stop, before native logout/cache destruction.
    // Drain accepted value-only searches while their destination data still lives.
    draining.reset();
}
