#pragma once
#include "AuctionHouse/AuctionHouseMgr.h"
#include <mutex>
namespace ahbot
{
class NativeAuctionView
{
public:
    explicit NativeAuctionView(AuctionHouseObject* house) : lock(house->GetLock())
    {
        auto bounds = house->GetAuctionsBounds_locked();
        entries.insert(bounds.first, bounds.second);
    }
    AuctionHouseObject::AuctionEntryMap const& Get() const { return entries; }
private:
    std::lock_guard<std::recursive_mutex> lock;
    AuctionHouseObject::AuctionEntryMap entries;
};
}
