#include "botpch.h"
#include "PlayerbotActionBroker.h"

#include "PlayerbotChatDirector.h"
#include "PlayerbotLLMInterface.h"
#include "RandomPlayerbotMgr.h"
#include "ServerFacade.h"
#include "TravelMgr.h"
#include "strategy/ItemVisitors.h"
#include "strategy/actions/MailAction.h"
#include "strategy/values/BudgetValues.h"
#include "strategy/values/ItemUsageValue.h"

#include <future>
#include <regex>
#include <sstream>
#include <thread>

using namespace ai;

static uint32 CountBrokerPlayerItem(Player* player, uint32 entry);

static bool MoveToMeetingPlayer(Player* bot, Player* player)
{
    if (!bot || !player || bot->IsInCombat() || bot->GetMapId() != player->GetMapId())
        return false;
    bot->GetMotionMaster()->MovePoint(0, player->GetPositionX(), player->GetPositionY(), player->GetPositionZ(),
        FORCED_MOVEMENT_RUN, true);
    return true;
}

static std::string MeetingPlayerLocation(Player* player)
{
    if (!player)
        return "your location";
    uint32 areaId = sServerFacade.GetAreaId(player);
    AreaTableEntry const* area = GetAreaEntryByAreaID(areaId);
    AreaTableEntry const* zone = GetAreaEntryByAreaID(player->GetZoneId());
    return area && area->area_name[0] ? area->area_name[0] :
        (zone && zone->area_name[0] ? zone->area_name[0] : "your location");
}

static Item* SplitBrokerItem(Player* bot, Item* item, uint32 quantity)
{
    if (!bot || !item || !quantity || item->GetCount() < quantity)
        return nullptr;
    if (item->GetCount() == quantity)
        return item;

    uint8 destinationBag = INVENTORY_SLOT_BAG_0;
    uint8 destinationSlot = 0;
    bool found = false;
    for (uint8 slot = INVENTORY_SLOT_ITEM_START; slot < INVENTORY_SLOT_ITEM_END && !found; ++slot)
    {
        if (!bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
        {
            destinationSlot = slot;
            found = true;
        }
    }
    for (uint8 bagSlot = INVENTORY_SLOT_BAG_START; bagSlot < INVENTORY_SLOT_BAG_END && !found; ++bagSlot)
    {
        Bag* bag = (Bag*)bot->GetItemByPos(INVENTORY_SLOT_BAG_0, bagSlot);
        if (!bag)
            continue;
        for (uint32 slot = 0; slot < bag->GetBagSize(); ++slot)
        {
            if (!bag->GetItemByPos(slot))
            {
                destinationBag = bagSlot;
                destinationSlot = (uint8)slot;
                found = true;
                break;
            }
        }
    }
    if (!found)
        return nullptr;

    uint16 source = ((uint16)item->GetBagSlot() << 8) | item->GetSlot();
    uint16 destination = ((uint16)destinationBag << 8) | destinationSlot;
    uint32 entry = item->GetEntry();
    bot->SplitItem(source, destination, quantity);
    Item* split = bot->GetItemByPos(destinationBag, destinationSlot);
    return split && split->GetEntry() == entry && split->GetCount() == quantity ? split : nullptr;
}

PlayerbotActionBroker& PlayerbotActionBroker::instance()
{
    static PlayerbotActionBroker broker;
    return broker;
}

static Item* FindBrokerItem(Player* bot, uint32 itemEntry, uint32 itemGuid)
{
    FindItemByIdVisitor visitor(itemEntry);
    bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    for (Item* item : visitor.GetResult())
        if (item->GetGUIDLow() == itemGuid)
            return item;
    return nullptr;
}

PlayerbotActionBroker::Transaction* PlayerbotActionBroker::Find(uint32 botGuid, uint32 playerGuid)
{
    for (auto& pair : transactions)
        if (pair.second.botGuid == botGuid && pair.second.playerGuid == playerGuid &&
            pair.second.state != "completed" && pair.second.state != "cancelled" && pair.second.state != "expired" && pair.second.state != "failed")
            return &pair.second;
    return nullptr;
}

const PlayerbotActionBroker::Transaction* PlayerbotActionBroker::Find(uint32 botGuid, uint32 playerGuid) const
{
    for (const auto& pair : transactions)
        if (pair.second.botGuid == botGuid && pair.second.playerGuid == playerGuid &&
            pair.second.state != "completed" && pair.second.state != "cancelled" && pair.second.state != "expired" && pair.second.state != "failed")
            return &pair.second;
    return nullptr;
}

bool PlayerbotActionBroker::Create(const ChatDirectorActionProposal& proposal, const ChatDirectorEvent& event)
{
    if ((proposal.delivery != "direct" && proposal.delivery != "meeting" && proposal.delivery != "mail") ||
        (proposal.type != "give_item" && proposal.type != "sell_item" && proposal.type != "buy_item" && proposal.type != "conjure_water"))
        return false;
    if (proposal.botGuid == 0 || proposal.targetGuid != event.speakerGuid || proposal.quantity == 0 || Find(proposal.botGuid, proposal.targetGuid))
        return false;

    std::smatch match;
    bool conjure = proposal.type == "conjure_water";
    bool buying = proposal.type == "buy_item";
    uint32 itemEntry = 0, itemGuid = 0, spellId = 0;
    if (buying)
    {
        if (proposal.delivery == "mail" || !std::regex_match(proposal.capabilityRef, match, std::regex(R"(buy:([0-9]+))"))) return false;
        itemEntry = (uint32)std::stoul(match[1].str());
    }
    else if (conjure)
    {
        if (proposal.delivery == "mail" || !std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(spell:conjure_water:([0-9]+):([0-9]+))"))) return false;
        spellId = (uint32)std::stoul(match[1].str());
        itemEntry = (uint32)std::stoul(match[2].str());
    }
    else
    {
        if (!std::regex_match(proposal.capabilityRef, match, std::regex(R"(item:([0-9]+):([0-9]+))"))) return false;
        itemEntry = (uint32)std::stoul(match[1].str());
        itemGuid = (uint32)std::stoul(match[2].str());
        if (reservedItems.find(itemGuid) != reservedItems.end()) return false;
    }

    Player* bot = sRandomPlayerbotMgr.GetPlayerBot(proposal.botGuid);
    Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, proposal.targetGuid));
    Item* item = !conjure && !buying && bot ? FindBrokerItem(bot, itemEntry, itemGuid) : nullptr;
    bool sameZone = bot && player && bot->GetMapId() == player->GetMapId() && bot->GetZoneId() == player->GetZoneId();
    if (!bot || !player || (!conjure && !buying && !item) || !bot->IsAlive() || !player->IsAlive() || bot->GetTeam() != player->GetTeam() ||
        (proposal.delivery != "mail" && !sameZone) || (proposal.delivery == "direct" && !bot->IsWithinDistInMap(player, INTERACTION_DISTANCE)) ||
        (!conjure && !buying && (!item->CanBeTraded() || item->IsSoulBound() || item->GetCount() < proposal.quantity)))
        return false;
    if (!conjure && !crafting && !buying && proposal.delivery == "mail" && item->IsConjuredConsumable())
        return false;
    if (!conjure && !crafting && !buying && proposal.delivery != "mail")
    {
        ItemPosCountVec destination;
        uint8 bagSlot = 0;
        if (player->CanStoreItem(NULL_BAG, NULL_SLOT, destination, item, bagSlot, false) != EQUIP_ERR_OK)
            return false;
    }
    if (conjure && (bot->getClass() != CLASS_MAGE || proposal.quantity > 5 ||
        !bot->GetPlayerbotAI()->CanCastSpell(spellId, bot, 0))) return false;

    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemEntry);
    if (!proto) return false;
    uint32 value = (conjure || buying) ? 0 : proposal.quantity * ItemUsageValue::GetBotSellPrice(proto, bot);
    uint32 price = buying ? proposal.quantity * ItemUsageValue::GetBotBuyPrice(proto, bot) : (proposal.type == "sell_item" ? value : 0);
    uint32 freeMoney = buying ? bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint32>(
        "free money for", std::to_string((uint32)NeedMoneyFor::anything))->Get() : 0;
    if (buying && (CountBrokerPlayerItem(player, itemEntry) < proposal.quantity || !price ||
        reservedMoney[bot->GetGUIDLow()] + price > freeMoney)) return false;
    if (proposal.type == "give_item" || conjure)
    {
        auto& history = giftHistory[proposal.targetGuid];
        const auto cutoff = std::chrono::steady_clock::now() - std::chrono::hours(1);
        history.erase(std::remove_if(history.begin(), history.end(), [&](const auto& stamp) { return stamp < cutoff; }), history.end());
        if (proposal.quantity > 5 || value > 100 || proto->Quality > ITEM_QUALITY_NORMAL || history.size() >= 3)
            return false;
    }

    if (!conjure && !crafting && !buying && proposal.delivery == "mail" && item->GetCount() != proposal.quantity)
    {
        item = SplitBrokerItem(bot, item, proposal.quantity);
        if (!item)
            return false;
        itemGuid = item->GetGUIDLow();
    }
    if (proposal.type == "give_item" || conjure)
        giftHistory[proposal.targetGuid].push_back(std::chrono::steady_clock::now());

    Transaction transaction;
    transaction.transactionId = "wow-tx-" + event.eventId + "-" + proposal.proposalId;
    transaction.eventId = event.eventId;
    transaction.proposalId = proposal.proposalId;
    transaction.botGuid = proposal.botGuid;
    transaction.playerGuid = proposal.targetGuid;
    transaction.itemEntry = itemEntry;
    transaction.itemGuid = itemGuid;
    transaction.spellId = spellId;
    transaction.quantity = proposal.quantity;
    transaction.priceCopper = price;
    transaction.type = proposal.type;
    transaction.delivery = proposal.delivery;
    transaction.state = (conjure || crafting) ? "preparing" : (proposal.delivery == "mail" ? "mail_travel" : (proposal.delivery == "meeting" ? "meeting" : "offered"));
    transaction.preparingSince = std::chrono::steady_clock::now();
    transaction.expires = std::chrono::steady_clock::now() + std::chrono::seconds(proposal.delivery == "mail" ? 1800 : (proposal.delivery == "meeting" ? 300 : 60));
    transactions[transaction.transactionId] = transaction;
    if (itemGuid) reservedItems[itemGuid] = transaction.transactionId;
    if (buying) reservedMoney[bot->GetGUIDLow()] += price;
    Report(transactions[transaction.transactionId]);

    if (conjure)
        bot->GetPlayerbotAI()->DoSpecificAction("conjure water", Event("chat action conjure", "", player), true);
    else if (proposal.delivery == "direct")
    {
        WorldPacket packet(CMSG_INITIATE_TRADE);
        packet << player->GetObjectGuid();
        bot->GetSession()->HandleInitiateTradeOpcode(packet);
        if (bot->GetTradeData() && bot->GetTrader() == player)
            PopulateTrade(bot, player);
    }
    else if (proposal.delivery == "mail")
    {
        std::ostringstream action;
        action << "request travel target::" << (uint32)TravelDestinationPurpose::Mail;
        bot->GetPlayerbotAI()->DoSpecificAction(action.str(), Event("chat action mail", "", player), true);
    }
    else if (proposal.delivery == "meeting")
    {
        Transaction& active = transactions[transaction.transactionId];
        if (bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
        {
            active.state = "offered";
            WorldPacket packet(CMSG_INITIATE_TRADE);
            packet << player->GetObjectGuid();
            bot->GetSession()->HandleInitiateTradeOpcode(packet);
            Report(active);
            if (bot->GetTradeData() && bot->GetTrader() == player)
                PopulateTrade(bot, player);
        }
        else
        {
            if (MoveToMeetingPlayer(bot, player))
                active.lastMeetingMove = std::chrono::steady_clock::now();
            else
                bot->Whisper("I can't head over right now. I'll hold the item for a few minutes.",
                    LANG_UNIVERSAL, player->GetObjectGuid());
        }
    }
    return true;
}

bool PlayerbotActionBroker::Authorizes(Player* bot, Player* trader) const
{
    return bot && trader && Find(bot->GetGUIDLow(), trader->GetGUIDLow()) != nullptr;
}

bool PlayerbotActionBroker::PopulateTrade(Player* bot, Player* trader)
{
    Transaction* transaction = bot && trader ? Find(bot->GetGUIDLow(), trader->GetGUIDLow()) : nullptr;
    if (!transaction || !bot->GetTradeData() || bot->GetTrader() != trader)
        return false;
    if (transaction->type == "buy_item")
    {
        if (bot->GetMoney() < transaction->priceCopper)
        {
            CancelTrade(bot, trader, "reserved funds became unavailable");
            return false;
        }
        WorldPacket gold(CMSG_SET_TRADE_GOLD, 4);
        gold << transaction->priceCopper;
        bot->GetSession()->HandleSetTradeGoldOpcode(gold);
        if (!bot->GetTradeData() || bot->GetTradeData()->GetMoney() != transaction->priceCopper)
            return false;
        transaction->state = "trading";
        transaction->failureReason.clear();
        Report(*transaction);
        return true;
    }
    Item* offered = bot->GetTradeData()->GetItem((TradeSlots)0);
    if (offered && offered->GetGUIDLow() == transaction->itemGuid && offered->GetCount() == transaction->quantity)
        return true;
    Item* item = FindBrokerItem(bot, transaction->itemEntry, transaction->itemGuid);
    if (!item || item->GetCount() < transaction->quantity || !item->CanBeTraded())
    {
        FindItemByIdVisitor visitor(transaction->itemEntry);
        bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
        for (Item* candidate : visitor.GetResult())
        {
            auto reservation = reservedItems.find(candidate->GetGUIDLow());
            if (candidate->GetCount() >= transaction->quantity && candidate->CanBeTraded() &&
                (reservation == reservedItems.end() || reservation->second == transaction->transactionId))
            {
                reservedItems.erase(transaction->itemGuid);
                item = candidate;
                transaction->itemGuid = candidate->GetGUIDLow();
                reservedItems[transaction->itemGuid] = transaction->transactionId;
                break;
            }
        }
    }
    if (!item || item->GetCount() < transaction->quantity || !item->CanBeTraded())
    {
        CancelTrade(bot, trader, "reserved item is no longer available");
        return false;
    }
    if (item->GetCount() != transaction->quantity)
    {
        Item* split = SplitBrokerItem(bot, item, transaction->quantity);
        if (!split)
        {
            CancelTrade(bot, trader, "could not prepare the promised quantity");
            return false;
        }
        reservedItems.erase(transaction->itemGuid);
        item = split;
        transaction->itemGuid = split->GetGUIDLow();
        reservedItems[transaction->itemGuid] = transaction->transactionId;
    }
    WorldPacket packet(CMSG_SET_TRADE_ITEM, 3);
    packet << (uint8)0 << (uint8)item->GetBagSlot() << (uint8)item->GetSlot();
    bot->GetSession()->HandleSetTradeItemOpcode(packet);
    offered = bot->GetTradeData() ? bot->GetTradeData()->GetItem((TradeSlots)0) : nullptr;
    if (!offered || offered->GetGUIDLow() != transaction->itemGuid || offered->GetCount() != transaction->quantity)
        return false;

    transaction->state = "trading";
    transaction->failureReason.clear();
    Report(*transaction);
    return true;
}

bool PlayerbotActionBroker::ValidateTrade(Player* bot, Player* trader)
{
    Transaction* transaction = bot && trader ? Find(bot->GetGUIDLow(), trader->GetGUIDLow()) : nullptr;
    if (!transaction || !bot->GetTradeData() || !trader->GetTradeData())
        return false;
    if (transaction->type == "buy_item")
    {
        uint32 received = 0;
        for (uint32 slot = 0; slot < TRADE_SLOT_TRADED_COUNT; ++slot)
        {
            if (bot->GetTradeData()->GetItem((TradeSlots)slot)) return false;
            Item* item = trader->GetTradeData()->GetItem((TradeSlots)slot);
            if (item)
            {
                if (item->GetEntry() != transaction->itemEntry || !item->CanBeTraded()) return false;
                received += item->GetCount();
            }
        }
        return received == transaction->quantity && bot->GetTradeData()->GetMoney() == transaction->priceCopper &&
            trader->GetTradeData()->GetMoney() == 0;
    }
    Item* offered = bot->GetTradeData()->GetItem((TradeSlots)0);
    if (!offered || offered->GetGUIDLow() != transaction->itemGuid || offered->GetCount() != transaction->quantity)
        return false;
    ItemPosCountVec destination;
    uint8 bagSlot = 0;
    if (trader->CanStoreItem(NULL_BAG, NULL_SLOT, destination, offered, bagSlot, false) != EQUIP_ERR_OK)
    {
        if (transaction->failureReason != "player inventory has no room")
        {
            transaction->failureReason = "player inventory has no room";
            bot->Whisper("Your bags look full. Make some room and try accepting again.",
                LANG_UNIVERSAL, trader->GetObjectGuid());
            Report(*transaction);
        }
        return false;
    }
    for (uint32 slot = 1; slot < TRADE_SLOT_TRADED_COUNT; ++slot)
        if (bot->GetTradeData()->GetItem((TradeSlots)slot))
            return false;
    for (uint32 slot = 0; slot < TRADE_SLOT_TRADED_COUNT; ++slot)
        if (trader->GetTradeData()->GetItem((TradeSlots)slot))
            return false;
    return bot->GetTradeData()->GetMoney() == 0 && trader->GetTradeData()->GetMoney() == transaction->priceCopper;
}

static Item* FindBrokerItemStack(Player* bot, uint32 itemEntry, uint32 quantity)
{
    FindItemByIdVisitor visitor(itemEntry);
    bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    for (Item* item : visitor.GetResult())
        if (item->GetCount() == quantity && item->CanBeTraded() && !item->IsInTrade())
            return item;
    return nullptr;
}

static uint32 CountBrokerPlayerItem(Player* player, uint32 entry)
{
    uint32 count = 0;
    for (uint8 slot = INVENTORY_SLOT_ITEM_START; slot < INVENTORY_SLOT_ITEM_END; ++slot)
        if (Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
            if (item->GetEntry() == entry && item->CanBeTraded() && !item->IsSoulBound()) count += item->GetCount();
    for (uint8 bagSlot = INVENTORY_SLOT_BAG_START; bagSlot < INVENTORY_SLOT_BAG_END; ++bagSlot)
        if (Bag* bag = (Bag*)player->GetItemByPos(INVENTORY_SLOT_BAG_0, bagSlot))
            for (uint32 slot = 0; slot < bag->GetBagSize(); ++slot)
                if (Item* item = bag->GetItemByPos(slot))
                    if (item->GetEntry() == entry && item->CanBeTraded() && !item->IsSoulBound()) count += item->GetCount();
    return count;
}

void PlayerbotActionBroker::CompleteTrade(Player* bot, Player* trader)
{
    Transaction* transaction = bot && trader ? Find(bot->GetGUIDLow(), trader->GetGUIDLow()) : nullptr;
    if (!transaction) return;
    transaction->state = "completed";
    reservedItems.erase(transaction->itemGuid);
    if (transaction->type == "buy_item") reservedMoney[transaction->botGuid] -= std::min(reservedMoney[transaction->botGuid], transaction->priceCopper);
    Report(*transaction);
}

void PlayerbotActionBroker::CancelTrade(Player* bot, Player* trader, const std::string& reason)
{
    Transaction* transaction = bot && trader ? Find(bot->GetGUIDLow(), trader->GetGUIDLow()) : nullptr;
    if (!transaction) return;
    transaction->state = "cancelled";
    transaction->failureReason = reason;
    reservedItems.erase(transaction->itemGuid);
    if (transaction->type == "buy_item") reservedMoney[transaction->botGuid] -= std::min(reservedMoney[transaction->botGuid], transaction->priceCopper);
    Report(*transaction);
}

void PlayerbotActionBroker::Update()
{
    const auto now = std::chrono::steady_clock::now();
    for (auto& pair : transactions)
    {
        Transaction& transaction = pair.second;
        if (transaction.state != "preparing" && transaction.state != "mail_travel" && transaction.state != "meeting" && transaction.state != "offered" && transaction.state != "trading")
            continue;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(transaction.botGuid);
        Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, transaction.playerGuid));
        bool buying = transaction.type == "buy_item";
        Item* item = bot && transaction.itemGuid ? FindBrokerItem(bot, transaction.itemEntry, transaction.itemGuid) : nullptr;
        if (bot && !buying && transaction.state != "preparing" &&
            (!item || item->GetCount() < transaction.quantity || !item->CanBeTraded()))
        {
            FindItemByIdVisitor visitor(transaction.itemEntry);
            bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
            for (Item* candidate : visitor.GetResult())
            {
                auto reservation = reservedItems.find(candidate->GetGUIDLow());
                if (candidate->GetCount() >= transaction.quantity && candidate->CanBeTraded() &&
                    (reservation == reservedItems.end() || reservation->second == transaction.transactionId))
                {
                    reservedItems.erase(transaction.itemGuid);
                    item = candidate;
                    transaction.itemGuid = candidate->GetGUIDLow();
                    reservedItems[transaction.itemGuid] = transaction.transactionId;
                    break;
                }
            }
        }
        bool incompatible = transaction.delivery != "mail" && bot && player &&
            (bot->GetMapId() != player->GetMapId() || bot->GetZoneId() != player->GetZoneId());
        if (!bot || !player || !bot->IsAlive() || !player->IsAlive() || incompatible ||
            (buying && CountBrokerPlayerItem(player, transaction.itemEntry) < transaction.quantity) ||
            (!buying && transaction.state != "preparing" && (!item || item->GetCount() < transaction.quantity || !item->CanBeTraded())))
        {
            transaction.state = "cancelled";
            if (!bot || !player || !bot->IsAlive() || !player->IsAlive())
                transaction.failureReason = "participant became unavailable";
            else if (incompatible)
                transaction.failureReason = "participants are no longer in the same zone";
            else if (!buying && !item)
                transaction.failureReason = "reserved item is no longer in inventory";
            else if (!buying && item->GetCount() < transaction.quantity)
                transaction.failureReason = "reserved item quantity changed";
            else if (!buying && !item->CanBeTraded())
                transaction.failureReason = "reserved item is no longer tradeable";
            else
                transaction.failureReason = "requested trade resources became unavailable";
            reservedItems.erase(transaction.itemGuid);
            if (buying) reservedMoney[transaction.botGuid] -= std::min(reservedMoney[transaction.botGuid], transaction.priceCopper);
            Report(transaction);
            continue;
        }
        if (transaction.state == "preparing")
        {
            Item* created = FindBrokerItemStack(bot, transaction.itemEntry, transaction.quantity);
            if (created)
            {
                transaction.itemGuid = created->GetGUIDLow();
                reservedItems[transaction.itemGuid] = transaction.transactionId;
                if (transaction.delivery == "direct" && bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
                {
                    transaction.state = "offered";
                    WorldPacket packet(CMSG_INITIATE_TRADE);
                    packet << player->GetObjectGuid();
                    bot->GetSession()->HandleInitiateTradeOpcode(packet);
                    bot->Whisper(crafting ? "It's ready. Open trade." : "Water is ready. Open trade.",
                        LANG_UNIVERSAL, player->GetObjectGuid());
                }
                else
                {
                    transaction.state = "meeting";
                    if (MoveToMeetingPlayer(bot, player))
                    {
                        transaction.lastMeetingMove = now;
                        bot->Whisper(crafting ? "It's ready. I'm heading to you." : "Water is ready. I'm heading to you.", LANG_UNIVERSAL, player->GetObjectGuid());
                    }
                    else
                        bot->Whisper(crafting ? "It's ready, but I can't head over right now." : "Water is ready, but I can't head over right now.", LANG_UNIVERSAL, player->GetObjectGuid());
                }
                Report(transaction);
            }
            else if (std::chrono::duration_cast<std::chrono::seconds>(now - transaction.preparingSince).count() >= 12)
            {
                transaction.state = "failed";
                transaction.failureReason = crafting ? "crafting did not produce the promised item" : "conjuring did not produce the promised stack";
                bot->Whisper(crafting ? "I couldn't finish that craft after all, sorry." : "Couldn't conjure that water after all, sorry.", LANG_UNIVERSAL, player->GetObjectGuid());
                Report(transaction);
            }
            continue;
        }
        if (transaction.state == "mail_travel")
        {
            ObjectGuid mailbox = MailProcessor::FindMailbox(bot->GetPlayerbotAI());
            if (mailbox && bot->GetMoney() >= 30)
            {
                WorldPacket packet(CMSG_SEND_MAIL);
                packet << mailbox << player->GetName();
                packet << std::string(transaction.priceCopper ? "Living TBC sale" : "Living TBC gift");
                packet << std::string("An item promised in chat.");
                packet << (uint32)0 << (uint32)0 << (uint8)1;
                packet << (uint8)0 << item->GetObjectGuid();
                packet << (uint32)0 << transaction.priceCopper << (uint64)0 << (uint8)0;
                bot->GetSession()->HandleSendMail(packet);
                if (!FindBrokerItem(bot, transaction.itemEntry, transaction.itemGuid))
                {
                    transaction.state = "completed";
                    reservedItems.erase(transaction.itemGuid);
                }
                else
                {
                    transaction.state = "failed";
                    transaction.failureReason = "mail draft was rejected";
                    reservedItems.erase(transaction.itemGuid);
                }
                Report(transaction);
                continue;
            }
        }
        if (transaction.state == "meeting" && !bot->IsWithinDistInMap(player, INTERACTION_DISTANCE) &&
            !bot->IsInCombat() && (transaction.lastMeetingMove.time_since_epoch().count() == 0 ||
            std::chrono::duration_cast<std::chrono::seconds>(now - transaction.lastMeetingMove).count() >= 5))
        {
            if (MoveToMeetingPlayer(bot, player))
                transaction.lastMeetingMove = now;
        }
        if (transaction.state == "meeting" && bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
        {
            transaction.state = "offered";
            WorldPacket packet(CMSG_INITIATE_TRADE);
            packet << player->GetObjectGuid();
            bot->GetSession()->HandleInitiateTradeOpcode(packet);
            Report(transaction);
            if (bot->GetTradeData() && bot->GetTrader() == player)
                PopulateTrade(bot, player);
        }
        if (transaction.state == "offered" && bot->GetTradeData() && bot->GetTrader() == player)
            PopulateTrade(bot, player);
        if ((transaction.state == "mail_travel" || transaction.state == "meeting" || transaction.state == "offered" || transaction.state == "trading") && now >= transaction.expires)
        {
            transaction.state = "expired";
            transaction.failureReason = "transaction expired";
            reservedItems.erase(transaction.itemGuid);
            if (buying) reservedMoney[transaction.botGuid] -= std::min(reservedMoney[transaction.botGuid], transaction.priceCopper);
            Report(transaction);
        }
    }
}

void PlayerbotActionBroker::Report(const Transaction& transaction) const
{
    Player* bot = sRandomPlayerbotMgr.GetPlayerBot(transaction.botGuid);
    Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, transaction.playerGuid));
    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(transaction.itemEntry);
    std::ostringstream body;
    body << "{\"transaction_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(transaction.transactionId)
         << "\",\"event_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(transaction.eventId)
         << "\",\"proposal_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(transaction.proposalId)
         << "\",\"bot_guid\":" << transaction.botGuid << ",\"bot_name\":\""
         << PlayerbotLLMInterface::SanitizeForJson(bot ? bot->GetName() : "") << "\",\"player_guid\":" << transaction.playerGuid
         << ",\"player_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(player ? player->GetName() : "")
         << "\",\"type\":\"" << transaction.type << "\",\"capability_ref\":\"item:" << transaction.itemEntry << ':' << transaction.itemGuid
         << "\",\"item_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(proto ? proto->Name1 : "")
         << "\",\"quantity\":" << transaction.quantity << ",\"price_copper\":" << transaction.priceCopper
         << ",\"delivery\":\"" << transaction.delivery << "\",\"state\":\"" << transaction.state
         << "\",\"failure_reason\":\"" << PlayerbotLLMInterface::SanitizeForJson(transaction.failureReason)
         << "\",\"expires_at\":\"world-clock\"}";
    std::string payload = body.str();
    std::thread([payload]() {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(payload, 3, 2, debug, true, "/v2/action-status");
    }).detach();
}
