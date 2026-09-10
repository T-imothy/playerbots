#ifndef _PLAYERBOT_INVENTORY_PRESSURE_H
#define _PLAYERBOT_INVENTORY_PRESSURE_H

#include "Common.h"

#include <string>

class Item;
class Player;

enum class LivingWowItemDisposition : uint8
{
    Keep,
    Craft,
    Bank,
    Auction,
    Vendor
};

struct LivingWowInventoryPressureSummary
{
    uint32 keepStacks = 0;
    uint32 craftStacks = 0;
    uint32 bankStacks = 0;
    uint32 auctionStacks = 0;
    uint32 vendorStacks = 0;
    uint32 reservedStacks = 0;
    uint8 bagUsage = 0;
    uint8 bankUsage = 100;

    uint32 StorableStacks() const
    {
        return bankStacks + craftStacks + auctionStacks;
    }

    bool HasBankableStorage() const
    {
        return bankUsage < 100 && StorableStacks();
    }

    bool HasQuickMaintenance() const
    {
        return vendorStacks || HasBankableStorage();
    }
};

class PlayerbotInventoryPressure
{
public:
    static PlayerbotInventoryPressure& instance();
    LivingWowItemDisposition Classify(Player* bot, Item* item, bool* hardReserved = nullptr) const;
    LivingWowInventoryPressureSummary Analyze(Player* bot) const;
    void Defer(Player* bot, const LivingWowInventoryPressureSummary& summary, const std::string& reason) const;
    static const char* Name(LivingWowItemDisposition disposition);
};

#define sPlayerbotInventoryPressure PlayerbotInventoryPressure::instance()

#endif
