
#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotAuctionEligibility.h"
#include "playerbot/PlayerbotServiceTracking.h"
#include "AhAction.h"
#include "playerbot/PlayerbotActionBroker.h"
#include "playerbot/strategy/values/ItemCountValue.h"
#include "playerbot/RandomItemMgr.h"
#include "playerbot/strategy/values/BudgetValues.h"
#include "playerbot/strategy/values/ItemUsageValue.h"
#include <chrono>
#include <fstream>
#include <regex>
#include <sstream>

using namespace ai;

namespace
{
    struct OrganicAuctionPolicy
    {
        std::string mode = "observe";
        bool posting = false;
        bool buying = false;
        uint32 humanPreference = 5;
        uint32 maxPurchasesPerHour = 3;
        uint32 maxDailySpendPercent = 25;
    };

    bool JsonBool(const std::string& source, const std::string& key, bool fallback)
    {
        std::smatch match;
        std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*(true|false)");
        return std::regex_search(source, match, pattern) ? match[1].str() == "true" : fallback;
    }

    uint32 JsonUInt(const std::string& source, const std::string& key, uint32 fallback)
    {
        std::smatch match;
        std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*([0-9]+)");
        return std::regex_search(source, match, pattern) ? uint32(std::stoul(match[1].str())) : fallback;
    }

    OrganicAuctionPolicy GetOrganicAuctionPolicy()
    {
        static OrganicAuctionPolicy policy;
        static std::chrono::steady_clock::time_point loaded;
        std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
        if (loaded.time_since_epoch().count() && now - loaded < std::chrono::seconds(60))
            return policy;
        loaded = now;
        std::ifstream input("/srv/living-wow/config/economy.json");
        if (!input)
            return policy;
        std::string source((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
        std::smatch mode;
        if (std::regex_search(source, mode, std::regex("\\\"mode\\\"\\s*:\\s*\\\"(off|observe|active)\\\"")))
            policy.mode = mode[1].str();
        policy.posting = JsonBool(source, "characterAuctionPosting", false);
        policy.buying = JsonBool(source, "characterAuctionBuying", false);
        policy.humanPreference = std::min<uint32>(5, JsonUInt(source, "humanListingPreferencePercent", 5));
        policy.maxPurchasesPerHour = std::min<uint32>(20, JsonUInt(source, "maximumPurchasesPerBotPerHour", 3));
        policy.maxDailySpendPercent = std::min<uint32>(100, JsonUInt(source, "maximumDiscretionarySpendPercentPerDay", 25));
        return policy;
    }

    uint32 ListingLimit(uint32 level)
    {
        if (level < 20) return 3;
        if (level < 40) return 7;
        if (level < 60) return 12;
        return 20;
    }

    uint32 CharacterAuctionCount(uint32 guid)
    {
        std::unique_ptr<QueryResult> result = CharacterDatabase.PQuery(
            "SELECT COUNT(*) FROM auction WHERE itemowner='%u'", guid);
        return result ? (*result)[0].GetUInt32() : 0;
    }

    uint32 CharacterAccount(uint32 guid)
    {
        static std::map<uint32, uint32> accounts;
        static std::chrono::steady_clock::time_point refreshed;
        std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
        if (!refreshed.time_since_epoch().count() || now - refreshed > std::chrono::seconds(60))
        {
            accounts.clear();
            refreshed = now;
        }
        std::map<uint32, uint32>::const_iterator found = accounts.find(guid);
        if (found != accounts.end()) return found->second;
        std::unique_ptr<QueryResult> result = CharacterDatabase.PQuery(
            "SELECT account FROM characters WHERE guid='%u'", guid);
        uint32 account = result ? (*result)[0].GetUInt32() : 0;
        accounts[guid] = account;
        return account;
    }

    uint32 RecentPurchases(uint32 guid, uint32 seconds, uint32* spent = nullptr)
    {
        std::unique_ptr<QueryResult> result = CharacterDatabase.PQuery(
            "SELECT COUNT(*),COALESCE(SUM(unit_price_copper*quantity),0) FROM organic_economy_auction_history "
            "WHERE buyer_guid='%u' AND outcome IN ('bid','sold') AND occurred_at>DATE_SUB(NOW(),INTERVAL %u SECOND)", guid, seconds);
        if (!result) { if (spent) *spent = 0; return 0; }
        if (spent) *spent = (*result)[1].GetUInt32();
        return (*result)[0].GetUInt32();
    }
}

bool AhAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    std::string text = event.getParam();

    std::list<ObjectGuid> npcs = AI_VALUE(std::list<ObjectGuid>, "nearest npcs");
    for (std::list<ObjectGuid>::iterator i = npcs.begin(); i != npcs.end(); i++)
    {
        Unit* npc = bot->GetNPCIfCanInteractWith(*i, UNIT_NPC_FLAG_AUCTIONEER);
        if (!npc)
            continue;

        if (!sRandomPlayerbotMgr.m_ahActionMutex.try_lock()) //Another bot is using the Auction right now. Try again later.
            return false;

        bool doneAuction = ExecuteCommand(requester, text, npc);

        sRandomPlayerbotMgr.m_ahActionMutex.unlock();

        return doneAuction;
    }

    ai->TellPlayerNoFacing(requester, "Cannot find auctioneer nearby");
    return false;
}

bool AhAction::ExecuteCommand(Player* requester, std::string text, Unit* auctioneer)
{
    uint32 time;
#ifdef MANGOSBOT_ZERO
    time = 8 * HOUR / MINUTE;
#else
    time = 12 * HOUR / MINUTE;
#endif

    if (text == "vendor")
    {
        OrganicAuctionPolicy policy = GetOrganicAuctionPolicy();
        if (policy.mode != "active" || !policy.posting)
            return false;
        uint32 listingLimit = ListingLimit(bot->GetLevel());
        uint32 activeListings = CharacterAuctionCount(bot->GetGUIDLow());
        if (activeListings >= listingLimit)
            return false;
        AuctionHouseEntry const* auctionHouseEntry = bot->GetSession()->GetCheckedAuctionHouseForAuctioneer(auctioneer->GetObjectGuid());
        if (!auctionHouseEntry)
            return false;

        std::list<Item*> items = AI_VALUE2(std::list<Item*>, "inventory items", "usage " + std::to_string((uint8)ItemUsage::ITEM_USAGE_AH));

        bool postedItem = false;

        std::map<uint32, uint32> pricePerItemCache;

        //resulting undercut value for reporting
        uint32 resultingUndercut = 0;
        uint32 postedItems = 0;

        for (auto item : items)
        {
            if (!LivingWowAuctionItemEligible(item))
                continue;
            if (activeListings + postedItems >= listingLimit)
                break;
            if (sPlayerbotActionBroker.IsItemReserved(item->GetGUIDLow()))
                continue;
            if (std::unique_ptr<QueryResult> acquired = CharacterDatabase.PQuery(
                "SELECT 1 FROM organic_economy_auction_history WHERE buyer_guid='%u' AND item_entry='%u' AND outcome='sold' AND occurred_at>DATE_SUB(NOW(),INTERVAL 1 DAY) LIMIT 1", bot->GetGUIDLow(), item->GetEntry()))
                continue;
            RESET_AI_VALUE2(ItemUsage, "item usage", ItemQualifier(item).GetQualifier());
            if(AI_VALUE2(ItemUsage, "item usage", ItemQualifier(item).GetQualifier()) != ItemUsage::ITEM_USAGE_AH)
                continue;

            auto pmo = sPerformanceMonitor.start(PERF_MON_VALUE, "IsMoreProfitableToSellToAHThanToVendor", ai);
            bool isMoreProfitableToSellToAHThanToVendor = ItemUsageValue::IsMoreProfitableToSellToAHThanToVendor(item->GetProto(), bot);
            pmo.reset();

            if (!isMoreProfitableToSellToAHThanToVendor)
                continue;

            uint32 deposit = AuctionHouseMgr::GetAuctionDeposit(auctionHouseEntry, time * MINUTE, item);

            RESET_AI_VALUE2(uint32, "free money for", (uint32)NeedMoneyFor::ah);
            uint32 freeMoney = AI_VALUE2(uint32, "free money for", (uint32)NeedMoneyFor::ah);

            if (deposit > freeMoney)
                return false;

            const ItemPrototype* proto = item->GetProto();

            if (!pricePerItemCache[proto->ItemId])
            {
                uint32 basePerItem = ItemUsageValue::GetBotSellPrice(proto, bot);
                uint32 initialPricePercentage = urand(75, 100);
                uint32 pricePerItem = (basePerItem * initialPricePercentage) / 100;
                if (!pricePerItem)
                    pricePerItem = 1;
                pricePerItemCache[proto->ItemId] = pricePerItem;
            }

            uint32 listingTime = time;
            if (proto->Quality >= ITEM_QUALITY_RARE)
                listingTime = 48 * 60;
            else if (proto->InventoryType != INVTYPE_NON_EQUIP)
                listingTime = 24 * 60;
            bool didPost = PostItem(requester, item, pricePerItemCache[proto->ItemId] * item->GetCount(), auctioneer, listingTime);

            if (didPost)
            {
                    postedItem |= true;
                    postedItems++;
            }

            if (!urand(0, 5 + (items.size()- postedItems)/10))
                break;
        }

        return postedItem;
    }

    int pos = text.find(" ");
    if (pos == std::string::npos) return false;

    std::string priceStr = text.substr(0, pos);
    uint32 price = ChatHelper::parseMoney(priceStr);

    std::list<Item*> found = ai->InventoryParseItems(text, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    if (found.empty())
        return false;

    Item* item = *found.begin();

    return PostItem(requester, item, price, auctioneer, time);
}

bool AhAction::PostItem(Player* requester, Item* item, uint32 price, Unit* auctioneer, uint32 time)
{
    // Recheck here for explicit commands and changes since candidate evaluation.
    // Rejected candidates are not attempted listings or completed operations.
    if (!LivingWowAuctionItemEligible(item)) return false;
    ObjectGuid itemGuid = item->GetObjectGuid();
    ItemPrototype const* proto = item->GetProto();

    ItemQualifier itemQualifier(item);

    uint32 cnt = item->GetCount();

    WorldPacket packet;
    packet << auctioneer->GetObjectGuid();
#ifdef MANGOSBOT_TWO
    packet << (uint32)1;
#endif
    packet << itemGuid;
#ifdef MANGOSBOT_TWO
    packet << cnt;
#endif
    packet << price * 95 / 100; //bid price?
    packet << price; //buyout price?
    packet << time;

    AuctionHouseEntry const* house = bot->GetSession()->GetCheckedAuctionHouseForAuctioneer(auctioneer->GetObjectGuid());
    const uint32 deposit = house ? AuctionHouseMgr::GetAuctionDeposit(house, time * MINUTE, item) : 0;
    bot->GetSession()->HandleAuctionSellItem(packet);
    uint32 postedAuction = 0;
    if (house)
        for (const auto& row : sAuctionMgr.GetAuctionsMap(house)->GetAuctions())
            if (row.second && row.second->owner == bot->GetGUIDLow() && row.second->itemGuidLow == itemGuid.GetCounter())
            { postedAuction = row.second->Id; break; }
    if (!PlayerbotServiceTracking::Result(bot, "auction_post", auctioneer->GetEntry(), proto->ItemId,
        "owned_auction_id", 0, postedAuction)) return false;

    if (bot->GetItemByGuid(itemGuid))
        return false;

    CharacterDatabase.PExecute("INSERT INTO organic_economy_auction_history "
        "(auction_id,auction_house_id,seller_guid,item_guid,item_entry,quantity,unit_price_copper,deposit_copper,outcome) "
        "VALUES (0,'%u','%u','%u','%u','%u','%u','%u','posted')",
        house ? house->houseId : 0, bot->GetGUIDLow(), itemGuid.GetCounter(), proto->ItemId, cnt, price / std::max<uint32>(1, cnt), deposit);
    sPlayerbotAIConfig.logEvent(ai, "AhAction", proto->Name1, std::to_string(proto->ItemId));

    std::ostringstream out;
    out << "Posting " << ChatHelper::formatItem(itemQualifier, cnt) << " for " << ChatHelper::formatMoney(price) << " to the AH";
    ai->TellPlayerNoFacing(requester, out.str(), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
    return true;
}

bool AhBidAction::ExecuteCommand(Player* requester, std::string text, Unit* auctioneer)
{
    OrganicAuctionPolicy policy = GetOrganicAuctionPolicy();
    if (text == "vendor" && (policy.mode != "active" || !policy.buying))
        return false;
    AuctionHouseEntry const* auctionHouseEntry = bot->GetSession()->GetCheckedAuctionHouseForAuctioneer(auctioneer->GetObjectGuid());
    if (!auctionHouseEntry)
        return false;

    // always return pointer
    AuctionHouseObject* auctionHouse = sAuctionMgr.GetAuctionsMap(auctionHouseEntry);

    if (!auctionHouse)
        return false;

    AuctionHouseObject::AuctionEntryMap const& map = auctionHouse->GetAuctions();

    if (map.empty())
        return false;

    AuctionEntry* auction = nullptr;

    std::vector<std::pair<AuctionEntry*, uint32>> auctionPowers;

    if (text == "vendor")
    {
        ItemUsage usage;
        auto data = WorldPacket();
        uint32 count, totalcount = 0;
        auctionHouse->BuildListBidderItems(data, bot, 9999, count, totalcount);

        if (totalcount > 10) //Already have 10 bids, stop.
            return false;

        std::unordered_map <ItemUsage, int32> freeMoney;

        freeMoney[ItemUsage::ITEM_USAGE_EQUIP] = freeMoney[ItemUsage::ITEM_USAGE_BAD_EQUIP] = (uint32)NeedMoneyFor::gear;
        freeMoney[ItemUsage::ITEM_USAGE_USE] = (uint32)NeedMoneyFor::consumables;
        freeMoney[ItemUsage::ITEM_USAGE_SKILL] = freeMoney[ItemUsage::ITEM_USAGE_DISENCHANT] =(uint32)NeedMoneyFor::tradeskill;
        freeMoney[ItemUsage::ITEM_USAGE_AMMO] = (uint32)NeedMoneyFor::ammo;
        freeMoney[ItemUsage::ITEM_USAGE_QUEST] = freeMoney[ItemUsage::ITEM_USAGE_AH] = freeMoney[ItemUsage::ITEM_USAGE_VENDOR] = freeMoney[ItemUsage::ITEM_USAGE_FORCE_NEED] = freeMoney[ItemUsage::ITEM_USAGE_FORCE_GREED] = (uint32)NeedMoneyFor::anything;

        uint32 checkNumAuctions = map.size();
        if (!sPlayerbotAIConfig.botCheckAllAuctionListings)
        {
            checkNumAuctions = urand(50, 250);
        }

        for (uint32 i = 0; i < checkNumAuctions; i++)
        {
            auto curAuction = std::next(std::begin(map), urand(0, map.size()-1));

            auction = curAuction->second;

            if (!auction)
                continue;

            if (std::find_if(auctionPowers.begin(), auctionPowers.end(), [auction](std::pair<AuctionEntry*, uint32> i){return i.first == auction;}) != auctionPowers.end())
                continue;

            auction = auctionHouse->GetAuction(auction->Id);

            if (!auction)
                continue;

            if (auction->owner == bot->GetGUIDLow())
                continue;
            uint32 sellerAccount = CharacterAccount(auction->owner);
            if (!sellerAccount || sellerAccount == bot->GetSession()->GetAccountId())
                continue;
            if (RecentPurchases(bot->GetGUIDLow(), HOUR) >= policy.maxPurchasesPerHour)
                break;
            std::unique_ptr<QueryResult> loop = CharacterDatabase.PQuery(
                "SELECT COUNT(*) FROM organic_economy_auction_history WHERE seller_guid='%u' AND buyer_guid='%u' "
                "AND outcome='sold' AND occurred_at>DATE_SUB(NOW(),INTERVAL 7 DAY)", auction->owner, bot->GetGUIDLow());
            if (loop && (*loop)[0].GetUInt32() >= 3)
                continue;

            uint32 totalCost = std::min(auction->buyout, uint32(std::max(auction->bid, auction->startbid) * frand(1.05f, 1.25f)));

            usage = AI_VALUE2(ItemUsage, "item usage", ItemQualifier(auction).GetQualifier());

            if (freeMoney.find(usage) == freeMoney.end() || totalCost > AI_VALUE2(uint32, "free money for", freeMoney[usage]))
                continue;

            uint32 power = 1;

            switch (usage)
            {
            case ItemUsage::ITEM_USAGE_EQUIP:
            case ItemUsage::ITEM_USAGE_BAD_EQUIP:
                power = sRandomItemMgr.GetLiveStatWeight(bot, auction->itemTemplate);
                break;
            case ItemUsage::ITEM_USAGE_AH:
            {
                // Organic buyers must have a real use; pure bot arbitrage creates churn.
                continue;
                auto pmo = sPerformanceMonitor.start(PERF_MON_VALUE, "IsWorthBuyingFromAhToResellAtAH", ai);
                bool isWorthBuyingFromAhToResellAtAH = ItemUsageValue::IsWorthBuyingFromAhToResellAtAH(sObjectMgr.GetItemPrototype(auction->itemTemplate), totalCost, auction->itemCount);
                pmo.reset();

                if (!isWorthBuyingFromAhToResellAtAH)
                    continue;
                power = 1000;
                break;
            }
            case ItemUsage::ITEM_USAGE_VENDOR:
                //basically if AH price is lower than vendor sell price then it's worth it
                if (totalCost / auction->itemCount >= (int32)sObjectMgr.GetItemPrototype(auction->itemTemplate)->SellPrice)
                    continue;
                power = 1000;
                break;
            case ItemUsage::ITEM_USAGE_FORCE_NEED:
            case ItemUsage::ITEM_USAGE_FORCE_GREED:
                power = 1000;
                break;
            }

            power *= 1000;
            power /= (totalCost +1);
            if (!sPlayerbotAIConfig.IsInRandomAccountList(sellerAccount))
                power = uint32(double(power) * (1.0 + double(policy.humanPreference) / 100.0));
            uint32 spentToday = 0;
            RecentPurchases(bot->GetGUIDLow(), DAY, &spentToday);
            if (spentToday + totalCost > (bot->GetMoney() + spentToday) * policy.maxDailySpendPercent / 100) continue;

            auctionPowers.push_back(std::make_pair(auction, power));
        }

        std::sort(auctionPowers.begin(), auctionPowers.end(), [](std::pair<AuctionEntry*, uint32> i, std::pair<AuctionEntry*, uint32> j) {return i > j; });

        bool bidItems = false;

        for (auto auctionPower : auctionPowers)
        {
            auction = auctionPower.first;

            if (!auction)
                continue;

            auction = auctionHouse->GetAuction(auction->Id);

            if (!auction)
                continue;

            usage = AI_VALUE2(ItemUsage, "item usage", ItemQualifier(auction).GetQualifier());

            uint32 currentBidPrice = std::max(auction->bid, auction->startbid);
            uint32 currentBuyoutPrice = auction->buyout;

            bool shouldBuyout = false;

            //determine if should look at buyout or bid price depending on item usage
            uint32 price = currentBuyoutPrice;

            if (usage == ItemUsage::ITEM_USAGE_VENDOR || usage == ItemUsage::ITEM_USAGE_FORCE_GREED || usage == ItemUsage::ITEM_USAGE_NONE)
            {
                //do not care for buyout price for items that bot does not need
                price = currentBidPrice;
            }
            else if (currentBidPrice < static_cast<uint32>(currentBuyoutPrice * 0.3f) && !urand(0,1))
            {
                //if bid price < 30% of buyout, then might as well (50/50) chance consider bid price directly
                price = currentBidPrice;
            }

            //first check if has money for buyout price (if checking against buyout price)
            if (price == currentBuyoutPrice && (freeMoney.find(usage) == freeMoney.end() || price > AI_VALUE2(uint32, "free money for", freeMoney[usage])))
            {
                //check for free money for bid price next if has no money for buyout
                price = currentBidPrice;
            }

            //check if have money for bid price (if checking against bid price)
            if (price != currentBuyoutPrice && (freeMoney.find(usage) == freeMoney.end() || price > AI_VALUE2(uint32, "free money for", freeMoney[usage])))
            {
                if (!urand(0, 5))
                    break;
                else
                    continue;
            }

            freeMoney[ItemUsage::ITEM_USAGE_EQUIP] = freeMoney[ItemUsage::ITEM_USAGE_BAD_EQUIP] = (uint32)NeedMoneyFor::gear;
            freeMoney[ItemUsage::ITEM_USAGE_USE] = (uint32)NeedMoneyFor::consumables;
            freeMoney[ItemUsage::ITEM_USAGE_SKILL] = freeMoney[ItemUsage::ITEM_USAGE_DISENCHANT] = (uint32)NeedMoneyFor::tradeskill;
            freeMoney[ItemUsage::ITEM_USAGE_AMMO] = (uint32)NeedMoneyFor::ammo;
            freeMoney[ItemUsage::ITEM_USAGE_QUEST] = freeMoney[ItemUsage::ITEM_USAGE_AH] = freeMoney[ItemUsage::ITEM_USAGE_VENDOR] = freeMoney[ItemUsage::ITEM_USAGE_FORCE_NEED] = freeMoney[ItemUsage::ITEM_USAGE_FORCE_GREED] = (uint32)NeedMoneyFor::anything;
         
            ItemUsage usage = AI_VALUE2(ItemUsage, "item usage", ItemQualifier(auction).GetQualifier());

            std::string reason = ItemUsageValue::ReasonForNeed(usage, auction, auction->itemCount, bot);            

            bidItems = BidItem(requester, auction, price, auctioneer, price == currentBuyoutPrice, reason);

            if (bidItems)
                totalcount++;

            if (!urand(0, 5) || totalcount > 10)
                break;

            RESET_AI_VALUE2(uint32, "free money for", freeMoney[usage]);
        }

        return bidItems;
    }

    int pos = text.find(" ");
    if (pos == std::string::npos) return false;

    std::string priceStr = text.substr(0, pos);
    uint32 price = ChatHelper::parseMoney(priceStr);

    for (auto curAuction : map)
    {
        auction = curAuction.second;

        if (auction->owner == bot->GetGUIDLow())
            continue;

        ItemPrototype const* proto = sObjectMgr.GetItemPrototype(auction->itemTemplate);

        if (!proto)
            continue;

        if(!proto->Name1)
            continue;

        if (!strstri(proto->Name1, text.c_str()))
            continue;

        if (price && auction->bid + 5 > price)
            continue;

        uint32 cost = std::min(auction->buyout, uint32(std::max(auction->bid, auction->startbid) * frand(1.05f, 1.25f)));

        uint32 power = auction->itemCount;
        power *= 1000;
        power /= cost;

        auctionPowers.push_back(std::make_pair(auction, power));
    }

    if (auctionPowers.empty())
        return false;

    std::sort(auctionPowers.begin(), auctionPowers.end(), [](std::pair<AuctionEntry*, uint32> i, std::pair<AuctionEntry*, uint32> j) {return i > j; });

    auction = auctionPowers.begin()->first;

    uint32 cost = std::min(auction->buyout, uint32(std::max(auction->bid, auction->startbid) * frand(1.05f, 1.25f)));

    return BidItem(requester, auction, cost, auctioneer, cost == auction->buyout);
}

bool AhBidAction::BidItem(Player* requester, AuctionEntry* auction, uint32 price, Unit* auctioneer, bool isBuyout, std::string reason)
{
    AuctionHouseEntry const* auctionHouseEntry = bot->GetSession()->GetCheckedAuctionHouseForAuctioneer(auctioneer->GetObjectGuid());
    if (!auctionHouseEntry)
        return false;

    // always return pointer
    AuctionHouseObject* auctionHouse = sAuctionMgr.GetAuctionsMap(auctionHouseEntry);

    if (!auctionHouse)
        return false;

    auction = auctionHouse->GetAuction(auction->Id);

    if (!auction)
        return false;

    WorldPacket packet;
    packet << auctioneer->GetObjectGuid();
    packet << auction->Id;
    packet << price;

    uint32 oldMoney = bot->GetMoney();
    ItemQualifier itemQualifier(auction);
    uint32 count = auction->itemCount;

    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(auction->itemTemplate);

    const uint32 auctionItemEntry = auction->itemTemplate;
    bot->GetSession()->HandleAuctionPlaceBid(packet);
    PlayerbotServiceTracking::Result(bot, "auction_bid", auctioneer->GetEntry(), auctionItemEntry,
        "money_debited_for_bid", oldMoney, bot->GetMoney(), false);

    if (bot->GetMoney() < oldMoney)
    {
        CharacterDatabase.PExecute("INSERT INTO organic_economy_auction_history "
            "(auction_id,auction_house_id,seller_guid,buyer_guid,item_guid,item_entry,quantity,unit_price_copper,outcome) "
            "VALUES ('%u','%u','%u','%u','%u','%u','%u','%u','%s')", auction->Id, auctionHouseEntry->houseId,
            auction->owner, bot->GetGUIDLow(), auction->itemGuidLow, auction->itemTemplate, count,
            price / std::max<uint32>(1, count), isBuyout ? "sold" : "bid");
        sPlayerbotAIConfig.logEvent(ai, "AhBidAction", proto->Name1, std::to_string(proto->ItemId));
        std::ostringstream out;
        if (isBuyout)
        {
            out << "Buying out " << ChatHelper::formatItem(itemQualifier, count) << " for " << ChatHelper::formatMoney(price) << " on the AH";
        }
        else
        {
            out << "Bidding " << ChatHelper::formatMoney(price) << " on " << ChatHelper::formatItem(itemQualifier, count) << " on the AH";
        }
        if (!reason.empty())
            out << " " << reason;
        ai->TellPlayerNoFacing(requester, out.str(), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
        return true;
    }
    return false;
}