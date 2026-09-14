#pragma once
#include "TravelMgr.h"
#include <functional>
#include <future>

namespace ai
{
    void StartPlayerbotTravelWorkers();
    void StopPlayerbotTravelWorkers();
    // Invalid future means admission was deferred, not that no destination exists.
    std::future<PartitionedTravelList> SubmitPlayerbotTravelSearch(std::function<PartitionedTravelList()> work);
}
