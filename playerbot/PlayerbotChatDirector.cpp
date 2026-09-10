#include "botpch.h"
#include "PlayerbotChatDirector.h"

#include "PlayerbotAI.h"
#include "PlayerbotActionBroker.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotLLMInterface.h"
#include "RandomPlayerbotMgr.h"
#include "ServerFacade.h"
#include "strategy/ItemVisitors.h"
#include "strategy/values/ItemUsageValue.h"

#include <algorithm>
#include <boost/algorithm/string.hpp>
#include <regex>
#include <set>
#include <sstream>
#include <thread>

PlayerbotChatDirector& PlayerbotChatDirector::instance()
{
    static PlayerbotChatDirector director;
    return director;
}

static void PopulateQuestLog(Player* bot, ChatDirectorCandidate& candidate)
{
    const uint8 maxReportedQuests = 12;
    uint8 reported = 0;
    std::ostringstream quests;
    for (uint16 slot = 0; slot < MAX_QUEST_LOG_SIZE; ++slot)
    {
        uint32 questId = bot->GetQuestSlotQuestId(slot);
        if (!questId)
            continue;
        if (reported >= maxReportedQuests)
        {
            candidate.questLogTruncated = true;
            break;
        }
        Quest const* quest = sObjectMgr.GetQuestTemplate(questId);
        if (!quest)
            continue;
        if (reported++) quests << "; ";
        quests << quest->GetTitle();
        if (bot->GetQuestStatus(questId) == QUEST_STATUS_COMPLETE)
            quests << " [complete]";
    }
    candidate.questLog = quests.str();
}

class ChatCapabilityItemVisitor : public ai::IterateItemsVisitor
{
public:
    std::vector<Item*> items;
    bool Visit(Item* item) override
    {
        if (item && item->CanBeTraded() && !item->IsSoulBound() && !item->IsInTrade())
            items.push_back(item);
        return items.size() < 24;
    }
};

static std::set<std::string> InventorySearchTerms(const std::string& text)
{
    static const std::set<std::string> ignored = {
        "and", "any", "anyone", "can", "could", "does", "for", "from", "give", "got", "have",
        "looking", "need", "please", "sell", "some", "someone", "the", "trade", "want", "with", "you", "your"
    };
    std::set<std::string> terms;
    std::string lowered = boost::algorithm::to_lower_copy(text);
    static const std::regex wordPattern("[a-z0-9]+");
    for (std::sregex_iterator it(lowered.begin(), lowered.end(), wordPattern), end; it != end; ++it)
    {
        std::string token = it->str();
        if (token.size() < 3 || ignored.find(token) != ignored.end())
            continue;
        if (token.size() > 4 && token.back() == 's')
            token.pop_back();
        terms.insert(token);
    }
    return terms;
}

static uint32 InventoryRelevance(const std::string& message, const ChatDirectorCandidate& candidate)
{
    std::set<std::string> requested = InventorySearchTerms(message);
    if (requested.empty())
        return 0;
    uint32 best = 0;
    for (const ChatDirectorCapability& capability : candidate.actionCapabilities)
    {
        std::set<std::string> item = InventorySearchTerms(capability.itemName);
        uint32 overlap = 0;
        for (const std::string& term : requested)
            if (item.find(term) != item.end()) ++overlap;
        if (overlap)
            best = std::max<uint32>(best, 45 + overlap * 20);
    }
    return best;
}

static uint32 CountTradeablePlayerItem(Player* player, uint32 entry)
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

static void PopulateGrounding(Player* bot, Player* speaker, const std::string& message, ChatDirectorCandidate& candidate)
{
    candidate.subzone = sServerFacade.GetAreaId(bot);
    if (AreaTableEntry const* zone = GetAreaEntryByAreaID(bot->GetZoneId()))
        candidate.zoneName = zone->area_name[0];
    if (AreaTableEntry const* subzone = GetAreaEntryByAreaID(candidate.subzone))
        candidate.subzoneName = subzone->area_name[0];
    if (!speaker)
        return;
    bool sameZone = bot->GetMapId() == speaker->GetMapId() && bot->GetZoneId() == speaker->GetZoneId();
    bool direct = sameZone && bot->IsWithinDistInMap(speaker, INTERACTION_DISTANCE);

    ChatCapabilityItemVisitor visitor;
    bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    ai::ListItemsVisitor countVisitor;
    bot->GetPlayerbotAI()->InventoryIterateItems(&countVisitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    uint32 reported = 0;
    for (Item* item : visitor.items)
    {
        ItemPrototype const* proto = item->GetProto();
        if (!proto || proto->Class == ITEM_CLASS_QUEST || reported >= 16)
            continue;
        uint32 total = std::max<int32>(0, countVisitor.items[proto->ItemId]);
        uint32 unitPrice = ai::ItemUsageValue::GetBotSellPrice(proto, bot);
        bool gift = proto->Quality <= ITEM_QUALITY_NORMAL && unitPrice <= 100 &&
            (proto->Class == ITEM_CLASS_CONSUMABLE || proto->Class == ITEM_CLASS_TRADE_GOODS);
        bool manaDrink = ai::ItemUsageValue::IsManaFoodOrDrink(proto);
        bool healthFood = ai::ItemUsageValue::IsHpFoodOrDrink(proto);
        uint32 retained = 0;
        if (gift)
        {
            if (manaDrink && bot->GetPowerType() == POWER_MANA)
                retained = std::min<uint32>(total, 2);
            else if (healthFood)
                retained = std::min<uint32>(total, 2);
            else
                retained = std::min<uint32>(total, 1);
        }
        uint32 available = total > retained ? total - retained : 0;
        uint32 maxQuantity = std::min<uint32>(item->GetCount(), gift ? std::min<uint32>(5, available) : item->GetCount());
        if (!maxQuantity)
            continue;
        if (gift && unitPrice && maxQuantity * unitPrice > 100)
            maxQuantity = std::min<uint32>(maxQuantity, 100 / unitPrice);
        if (!maxQuantity)
            continue;
        ChatDirectorCapability capability;
        std::ostringstream ref;
        ref << "item:" << proto->ItemId << ':' << item->GetGUIDLow();
        capability.capabilityRef = ref.str();
        capability.type = gift ? "give_item" : "sell_item";
        capability.itemName = proto->Name1;
        if (manaDrink) capability.itemKind = "water";
        else if (healthFood) capability.itemKind = "food";
        else capability.itemKind = "item";
        capability.quantity = maxQuantity;
        capability.minQuantity = 1;
        capability.maxQuantity = maxQuantity;
        capability.priceCopper = gift ? 0 : maxQuantity * unitPrice;
        capability.valueCopper = maxQuantity * unitPrice;
        if (direct) capability.deliveries.push_back("direct");
        if (sameZone) capability.deliveries.push_back("meeting");
        if (!item->IsConjuredConsumable()) capability.deliveries.push_back("mail");
        if (capability.deliveries.empty()) continue;
        candidate.actionCapabilities.push_back(std::move(capability));
        ++reported;
    }

    if (bot->getClass() == CLASS_MAGE && sameZone && !bot->IsInCombat())
    {
        uint32 bestSpell = 0, createdItem = 0, createdCount = 0;
        ai::ListItemsVisitor inventory;
        bot->GetPlayerbotAI()->InventoryIterateItems(&inventory, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
        for (const auto& spellPair : bot->GetSpellMap())
        {
            SpellEntry const* spell = sServerFacade.LookupSpellInfo(spellPair.first);
            if (!spell || spell->Effect[0] != SPELL_EFFECT_CREATE_ITEM)
                continue;
            std::string spellName = boost::algorithm::to_lower_copy(std::string(spell->SpellName[0]));
            if (spellName.find("conjure water") == std::string::npos || spell->Id <= bestSpell)
                continue;
            ItemPrototype const* itemProto = sObjectMgr.GetItemPrototype(spell->EffectItemType[0]);
            uint32 count = std::max<int32>(1, spell->CalculateSimpleValue(EFFECT_INDEX_0));
            if (!itemProto || count > 5 || inventory.items[itemProto->ItemId] != 0 ||
                bot->CanUseItem(itemProto) != EQUIP_ERR_OK || !bot->GetPlayerbotAI()->CanCastSpell(spell->Id, bot, 0))
                continue;
            bestSpell = spell->Id;
            createdItem = itemProto->ItemId;
            createdCount = count;
        }
        if (bestSpell && createdItem)
        {
            ChatDirectorCapability capability;
            std::ostringstream ref;
            ref << "spell:conjure_water:" << bestSpell << ':' << createdItem;
            capability.capabilityRef = ref.str();
            capability.type = "conjure_water";
            capability.itemName = sObjectMgr.GetItemPrototype(createdItem)->Name1;
            capability.itemKind = "water";
            capability.quantity = createdCount;
            capability.minQuantity = createdCount;
            capability.maxQuantity = createdCount;
            if (direct) capability.deliveries.push_back("direct");
            capability.deliveries.push_back("meeting");
            candidate.actionCapabilities.push_back(std::move(capability));
        }
    }

    if (sameZone)
    {
        for (uint32 itemId : ChatHelper::parseItems(message, true))
        {
            ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);
            uint32 available = std::min<uint32>(5, CountTradeablePlayerItem(speaker, itemId));
            uint32 unitPrice = proto ? ai::ItemUsageValue::GetBotBuyPrice(proto, bot) : 0;
            if (!proto || proto->Class == ITEM_CLASS_QUEST || !available || !unitPrice || bot->GetMoney() < unitPrice)
                continue;
            ChatDirectorCapability capability;
            capability.capabilityRef = "buy:" + std::to_string(itemId);
            capability.type = "buy_item";
            capability.itemName = proto->Name1;
            if (ai::ItemUsageValue::IsManaFoodOrDrink(proto)) capability.itemKind = "water";
            else if (ai::ItemUsageValue::IsHpFoodOrDrink(proto)) capability.itemKind = "food";
            else capability.itemKind = "item";
            capability.quantity = available;
            capability.minQuantity = 1;
            capability.maxQuantity = std::min<uint32>(available, bot->GetMoney() / unitPrice);
            capability.priceCopper = unitPrice;
            capability.valueCopper = unitPrice;
            if (direct) capability.deliveries.push_back("direct");
            capability.deliveries.push_back("meeting");
            candidate.actionCapabilities.push_back(std::move(capability));
        }
    }

}

void PlayerbotChatDirector::MaybeCreateAmbientEvent(std::chrono::steady_clock::time_point now)
{
    if (nextAmbient.time_since_epoch().count() == 0)
    {
        nextAmbient = now + std::chrono::seconds(urand(120, 300));
        lastConversation = now;
        return;
    }
    if (now < nextAmbient || std::chrono::duration_cast<std::chrono::seconds>(now - lastConversation).count() < 30)
        return;
    nextAmbient = now + std::chrono::seconds(urand(120, 300));

    Player* listener = nullptr;
    for (const auto& pair : sRandomPlayerbotMgr.GetPlayers())
    {
        if (pair.second && pair.second->IsInWorld())
        {
            listener = pair.second;
            break;
        }
    }
    if (!listener)
        return;

    ChatDirectorEvent event;
    event.key = "ambient";
    event.channelType = "general";
    event.channelName = "General";
    event.speakerName = "World";
    event.message = "[ambient opportunity: continue the current local conversation naturally, or stay silent]";
    event.ambient = true;
    event.zone = listener->GetZoneId();
    event.team = listener->GetTeam();
    event.firstSeen = now - std::chrono::milliseconds(150);
    std::ostringstream id;
    id << "wow-ambient-" << time(nullptr) << '-' << ++sequence;
    event.eventId = id.str();

    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld() || !bot->IsAlive() || bot->GetTeam() != event.team || bot->GetZoneId() != event.zone)
            continue;
        ChatDirectorCandidate candidate;
        candidate.guid = bot->GetGUIDLow();
        candidate.name = bot->GetName();
        candidate.race = bot->getRace();
        candidate.cls = bot->getClass();
        candidate.level = bot->GetLevel();
        candidate.zone = bot->GetZoneId();
        candidate.grouped = bot->GetGroup() != nullptr;
        candidate.inCombat = bot->IsInCombat();
        candidate.available = true;
        candidate.currentActivity = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
        PopulateQuestLog(bot, candidate);
        PopulateGrounding(bot, nullptr, event.message, candidate);
        if (PlayerbotAI::IsTank(bot, false)) candidate.role = "tank";
        else if (PlayerbotAI::IsHeal(bot, false)) candidate.role = "healer";
        else candidate.role = "damage";
        event.candidates[candidate.guid] = std::move(candidate);
    }
    if (!event.candidates.empty())
        pending[event.eventId] = std::move(event);
}

static bool HasCompletedQuest(Player* bot)
{
    for (uint16 slot = 0; slot < MAX_QUEST_LOG_SIZE; ++slot)
    {
        uint32 questId = bot->GetQuestSlotQuestId(slot);
        if (questId && bot->GetQuestStatus(questId) == QUEST_STATUS_COMPLETE)
            return true;
    }
    return false;
}

void PlayerbotChatDirector::MaybeReportBotHealth(std::chrono::steady_clock::time_point now)
{
    if (nextHealthSample.time_since_epoch().count() != 0 && now < nextHealthSample)
        return;
    nextHealthSample = now + std::chrono::seconds(10);

    std::vector<std::string> samples;
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld())
            continue;
        BotHealthState& state = botHealth[guid];
        bool levelChanged = state.lastLevel != 0 && state.lastLevel != bot->GetLevel();
        state.lastLevel = bot->GetLevel();
        if (state.lastMoved.time_since_epoch().count() == 0)
        {
            state.x = bot->GetPositionX();
            state.y = bot->GetPositionY();
            state.lastMoved = now;
        }
        float dx = bot->GetPositionX() - state.x;
        float dy = bot->GetPositionY() - state.y;
        if (dx * dx + dy * dy >= 1.0f)
        {
            state.x = bot->GetPositionX();
            state.y = bot->GetPositionY();
            state.lastMoved = now;
        }
        std::string action = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
        std::string lowered = boost::algorithm::to_lower_copy(action);
        bool completedQuest = HasCompletedQuest(bot);
        if (completedQuest && state.completedQuestSince.time_since_epoch().count() == 0)
            state.completedQuestSince = now;
        if (!completedQuest)
            state.completedQuestSince = std::chrono::steady_clock::time_point();
        MovementFlags movementFlags = bot->m_movementInfo.GetMovementFlags();
        bool playerStay = lowered.find("stay") != std::string::npos || lowered.find("wait") != std::string::npos;
        bool airborne = movementFlags & (MOVEFLAG_FALLING | MOVEFLAG_FALLINGFAR | MOVEFLAG_FLYING |
            MOVEFLAG_LEVITATING | MOVEFLAG_HOVER | MOVEFLAG_SWIMMING);
        bool excluded = !bot->IsAlive() || bot->IsInCombat() || bot->IsTaxiFlying() || bot->IsInWater() ||
            bot->IsNonMeleeSpellCasted(false) || bot->GetTransport() || playerStay || airborne;
        bool expectsMovement = lowered.find("move") != std::string::npos || lowered.find("travel") != std::string::npos ||
            lowered.find("quest") != std::string::npos || lowered.find("rpg") != std::string::npos;
        long stillSeconds = std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMoved).count();
        long completeSeconds = completedQuest ? std::chrono::duration_cast<std::chrono::seconds>(now - state.completedQuestSince).count() : 0;
        bool movementStalled = expectsMovement && stillSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        bool questStalled = completedQuest && completeSeconds >= sPlayerbotAIConfig.chatDirectorQuestStuckSeconds;
        bool suspected = !excluded && (movementStalled || questStalled);
        std::string classification = "active";
        if (!bot->IsAlive()) classification = "dead";
        else if (bot->IsInCombat()) classification = "combat";
        else if (bot->IsTaxiFlying() || bot->GetTransport()) classification = "transport";
        else if (playerStay) classification = "group_wait";
        else if (questStalled) classification = "quest_turn_in_stalled";
        else if (movementStalled) classification = "movement_stalled";
        else if (!expectsMovement && stillSeconds >= 60) classification = "rpg_pause";

        // Recovery mode 1 observes only; mode 2 performs the least invasive
        // recovery step on the world thread. Resetting the travel target makes
        // normal quest/travel strategies choose again without teleporting or
        // modifying authoritative quest state.
        if (suspected && sPlayerbotAIConfig.chatDirectorBotRecoveryMode >= 2)
        {
            const auto oneHourAgo = now - std::chrono::hours(1);
            state.recoveryAttempts.erase(std::remove_if(state.recoveryAttempts.begin(), state.recoveryAttempts.end(),
                [&](const std::chrono::steady_clock::time_point& attempt) { return attempt < oneHourAgo; }), state.recoveryAttempts.end());
            bool cooldownReady = state.lastRecovery.time_since_epoch().count() == 0 ||
                std::chrono::duration_cast<std::chrono::seconds>(now - state.lastRecovery).count() >=
                    sPlayerbotAIConfig.chatDirectorRecoveryCooldownSeconds;
            if (cooldownReady && state.recoveryAttempts.size() < sPlayerbotAIConfig.chatDirectorMaxRecoveriesPerHour)
            {
                bool recovered = bot->GetPlayerbotAI()->DoSpecificAction(
                    "reset travel target", Event("living chat director recovery"), true);
                state.lastRecovery = now;
                state.recoveryAttempts.push_back(now);
                state.recoveryResult = recovered ? "travel_target_reset" : "travel_target_reset_rejected";
                if (recovered)
                {
                    state.lastMoved = now;
                    state.completedQuestSince = completedQuest ? now : std::chrono::steady_clock::time_point();
                    classification = "recovering_travel_target";
                    suspected = false;
                }
            }
        }

        float terrainZ = bot->GetMap()->GetHeight(bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ() + 2.0f);
        bool validTerrain = terrainZ > -100000.0f;
        float offset = validTerrain ? bot->GetPositionZ() - terrainZ : 0.0f;
        bool outdoors = bot->GetTerrain() && bot->GetTerrain()->IsOutdoors(bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ());
        float nearbyZ = bot->GetMap()->GetHeight(bot->GetPositionX() + 1.0f, bot->GetPositionY(), bot->GetPositionZ() + 2.0f);
        bool steep = validTerrain && nearbyZ > -100000.0f && std::abs(nearbyZ - terrainZ) > 0.75f;
        bool heightCandidate = !excluded && outdoors && !steep && validTerrain && offset >= 0.75f;
        if (heightCandidate && state.heightFaultSince.time_since_epoch().count() == 0)
            state.heightFaultSince = now;
        if (!heightCandidate)
            state.heightFaultSince = std::chrono::steady_clock::time_point();
        bool heightFault = heightCandidate && std::chrono::duration_cast<std::chrono::seconds>(now - state.heightFaultSince).count() >= 3;

        uint32 areaId = sServerFacade.GetAreaId(bot);
        std::string zoneName, subzoneName;
        if (AreaTableEntry const* zone = GetAreaEntryByAreaID(bot->GetZoneId())) zoneName = zone->area_name[0];
        if (AreaTableEntry const* area = GetAreaEntryByAreaID(areaId)) subzoneName = area->area_name[0];
        std::ostringstream json;
        json << "{\"bot_guid\":" << guid << ",\"bot_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(bot->GetName())
             << "\",\"level\":" << (uint32)bot->GetLevel() << ",\"level_changed\":" << (levelChanged ? "true" : "false")
             << "\",\"classification\":\"" << classification << "\",\"suspected_stuck\":" << (suspected ? "true" : "false")
             << ",\"current_action\":\"" << PlayerbotLLMInterface::SanitizeForJson(action)
             << "\",\"quest_state\":\"" << (completedQuest ? "completed_quest_pending" : "none_completed")
             << "\",\"path_status\":\"not_instrumented\",\"zone_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(zoneName)
             << "\",\"subzone_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(subzoneName)
             << "\",\"x\":" << bot->GetPositionX() << ",\"y\":" << bot->GetPositionY()
             << ",\"server_z\":" << bot->GetPositionZ() << ",\"terrain_z\":" << (validTerrain ? terrainZ : bot->GetPositionZ())
             << ",\"mmap_z\":null,\"height_offset\":" << offset << ",\"height_fault\":" << (heightFault ? "true" : "false")
             << ",\"movement_flags\":" << movementFlags
             << ",\"last_movement_seconds\":" << stillSeconds << ",\"last_progress_seconds\":" << completeSeconds
             << ",\"recovery_mode\":" << sPlayerbotAIConfig.chatDirectorBotRecoveryMode
             << ",\"recovery_result\":\"" << PlayerbotLLMInterface::SanitizeForJson(state.recoveryResult) << "\""
             << ",\"recoveries_last_hour\":" << state.recoveryAttempts.size()
             << ",\"grouped\":" << (bot->GetGroup() ? "true" : "false") << "}";
        samples.push_back(json.str());
    }

    std::vector<std::string> payloads;
    // Keep telemetry requests comfortably below the gateway's 64 KiB v2 body
    // limit. Current-action diagnostics can be several hundred bytes per bot.
    static constexpr size_t healthBatchSize = 25;
    for (size_t start = 0; start < samples.size(); start += healthBatchSize)
    {
        std::ostringstream body;
        body << "{\"samples\":[";
        for (size_t i = start; i < samples.size() && i < start + healthBatchSize; ++i)
        {
            if (i != start) body << ',';
            body << samples[i];
        }
        body << "]}";
        payloads.push_back(body.str());
    }
    if (!payloads.empty())
    {
        std::thread([payloads]() {
            std::vector<std::string> debug;
            for (const std::string& payload : payloads)
                PlayerbotLLMInterface::Generate(payload, 3, 2, debug, true, "/v2/bot-health");
        }).detach();
    }
}

std::string PlayerbotChatDirector::ChannelType(uint32 msgType, const std::string& channelName) const
{
    if (msgType == CHAT_MSG_WHISPER) return "whisper";
    if (msgType == CHAT_MSG_PARTY) return "party";
#ifdef MANGOSBOT_TWO
    if (msgType == CHAT_MSG_PARTY_LEADER) return "party";
#endif
    if (msgType == CHAT_MSG_RAID || msgType == CHAT_MSG_RAID_LEADER) return "raid";
    if (msgType == CHAT_MSG_GUILD) return "guild";
    if (msgType == CHAT_MSG_SAY) return "say";
    if (msgType == CHAT_MSG_YELL) return "yell";
    if (msgType != CHAT_MSG_CHANNEL) return "say";

    std::string lowered = boost::algorithm::to_lower_copy(channelName);
    if (lowered.find("world") != std::string::npos) return "world";
    if (lowered.find("trade") != std::string::npos) return "trade";
    if (lowered.find("lookingforgroup") != std::string::npos || lowered.find("looking for group") != std::string::npos) return "lfg";
    return "general";
}

void PlayerbotChatDirector::Observe(Player* bot, uint32 msgType, uint32 speakerGuid, const std::string& speakerName,
    const std::string& message, const std::string& channelName)
{
    if (!sPlayerbotAIConfig.chatDirectorV2 || !bot || !bot->GetPlayerbotAI() || message.empty())
        return;

    std::string channelType = ChannelType(msgType, channelName);
    std::ostringstream keyStream;
    keyStream << speakerGuid << ':' << msgType << ':' << channelName << ':' << message;
    std::string key = keyStream.str();

    std::lock_guard<std::mutex> guard(mutex);
    lastConversation = std::chrono::steady_clock::now();
    auto found = pending.find(key);
    if (found == pending.end())
    {
        ChatDirectorEvent event;
        event.key = key;
        event.channelType = channelType;
        event.channelName = channelName;
        event.speakerName = speakerName;
        event.speakerGuid = speakerGuid;
        event.message = message;
        event.zone = bot->GetZoneId();
        event.team = bot->GetTeam();
        event.firstSeen = std::chrono::steady_clock::now();
        std::ostringstream id;
        id << "wow-" << time(nullptr) << '-' << ++sequence;
        event.eventId = id.str();
        if (Player* speaker = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, speakerGuid)))
            event.speakerLevel = speaker->GetLevel();
        found = pending.emplace(key, std::move(event)).first;
    }

    ChatDirectorCandidate candidate;
    candidate.guid = bot->GetGUIDLow();
    candidate.name = bot->GetName();
    candidate.race = bot->getRace();
    candidate.cls = bot->getClass();
    candidate.level = bot->GetLevel();
    candidate.zone = bot->GetZoneId();
    candidate.grouped = bot->GetGroup() != nullptr;
    candidate.inCombat = bot->IsInCombat();
    candidate.available = bot->IsInWorld() && bot->IsAlive();
    candidate.currentActivity = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
        PopulateQuestLog(bot, candidate);
        Player* speaker = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, speakerGuid));
        PopulateGrounding(bot, speaker, message, candidate);
    if (PlayerbotAI::IsTank(bot, false)) candidate.role = "tank";
    else if (PlayerbotAI::IsHeal(bot, false)) candidate.role = "healer";
    else candidate.role = "damage";
    found->second.candidates[candidate.guid] = std::move(candidate);
}

static std::string JsonUnescape(const std::string& value)
{
    std::string output;
    output.reserve(value.size());
    for (size_t i = 0; i < value.size(); ++i)
    {
        if (value[i] != '\\' || i + 1 >= value.size())
        {
            output += value[i];
            continue;
        }
        char next = value[++i];
        if (next == 'n' || next == 'r') output += ' ';
        else if (next == 't') output += ' ';
        else if (next == 'u')
        {
            if (i + 4 < value.size()) i += 4;
            output += '?';
        }
        else output += next;
    }
    return output;
}

std::string PlayerbotChatDirector::BuildJson(const ChatDirectorEvent& event) const
{
    std::vector<ChatDirectorCandidate> choices;
    for (const auto& pair : event.candidates)
        choices.push_back(pair.second);

    std::stable_sort(choices.begin(), choices.end(), [&](const ChatDirectorCandidate& left, const ChatDirectorCandidate& right)
    {
        bool leftNamed = boost::algorithm::icontains(event.message, left.name);
        bool rightNamed = boost::algorithm::icontains(event.message, right.name);
        if (leftNamed != rightNamed) return leftNamed;
        uint32 leftInventory = InventoryRelevance(event.message, left);
        uint32 rightInventory = InventoryRelevance(event.message, right);
        if (leftInventory != rightInventory) return leftInventory > rightInventory;
        size_t leftHash = std::hash<std::string>{}(event.message + std::to_string(left.guid));
        size_t rightHash = std::hash<std::string>{}(event.message + std::to_string(right.guid));
        return leftHash < rightHash;
    });
    if (event.channelType == "whisper" && choices.size() > 1)
        choices.resize(1);
    else if (choices.size() > 12)
        choices.resize(12);

    std::ostringstream json;
    json << "{\"event_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.eventId) << "\",";
    json << "\"event_type\":\"" << (event.ambient ? "ambient" : "message") << "\",";
    json << "\"channel\":{\"type\":\"" << event.channelType << "\",\"name\":\""
         << PlayerbotLLMInterface::SanitizeForJson(event.channelName) << "\",\"zone\":" << event.zone << "},";
    json << "\"faction\":\"" << (event.team == ALLIANCE ? "alliance" : "horde") << "\",";
    json << "\"speaker\":{\"guid\":" << event.speakerGuid << ",\"name\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.speakerName)
         << "\",\"kind\":\"" << (event.ambient ? "system" : "player") << "\",\"level\":" << (uint32)event.speakerLevel << "},";
    json << "\"message\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.message) << "\",\"candidates\":[";
    bool first = true;
    for (const ChatDirectorCandidate& candidate : choices)
    {
        if (!first) json << ',';
        first = false;
        json << "{\"guid\":" << candidate.guid << ",\"name\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.name)
             << "\",\"race\":" << (uint32)candidate.race << ",\"class\":" << (uint32)candidate.cls
             << ",\"level\":" << (uint32)candidate.level << ",\"zone\":" << candidate.zone
             << ",\"subzone\":" << candidate.subzone << ",\"zone_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.zoneName)
             << "\",\"subzone_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.subzoneName) << "\""
             << ",\"role\":\"" << candidate.role << "\",\"grouped\":" << (candidate.grouped ? "true" : "false")
             << ",\"current_activity\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.currentActivity) << "\""
             << ",\"quest_log\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.questLog) << "\""
             << ",\"quest_log_truncated\":" << (candidate.questLogTruncated ? "true" : "false")
             << ",\"inCombat\":" << (candidate.inCombat ? "true" : "false")
             << ",\"available\":" << (candidate.available ? "true" : "false") << ",\"action_capabilities\":[";
        bool firstCapability = true;
        for (const ChatDirectorCapability& capability : candidate.actionCapabilities)
        {
            if (!firstCapability) json << ',';
            firstCapability = false;
            json << "{\"capability_ref\":\"" << capability.capabilityRef << "\",\"type\":\"" << capability.type
                 << "\",\"item_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(capability.itemName)
                 << "\",\"item_kind\":\"" << capability.itemKind
                 << "\",\"min_quantity\":" << (capability.minQuantity ? capability.minQuantity : capability.quantity)
                 << ",\"max_quantity\":" << (capability.maxQuantity ? capability.maxQuantity : capability.quantity)
                 << ",\"price_copper\":" << capability.priceCopper << ",\"value_copper\":" << capability.valueCopper
                 << ",\"deliveries\":[";
            for (size_t deliveryIndex = 0; deliveryIndex < capability.deliveries.size(); ++deliveryIndex)
            {
                if (deliveryIndex) json << ',';
                json << "\"" << capability.deliveries[deliveryIndex] << "\"";
            }
            json << "]}";
        }
        json << "]}";
    }
    json << "]}";
    return json.str();
}

std::vector<ChatDirectorReply> PlayerbotChatDirector::ParseReplies(const std::string& response) const
{
    std::vector<ChatDirectorReply> replies;
    std::regex pattern(R"re("bot_guid"\s*:\s*([0-9]+)\s*,\s*"text"\s*:\s*"((?:\\.|[^"\\])*)"\s*,\s*"delay_ms"\s*:\s*([0-9]+)(?:\s*,\s*"requires_action_id"\s*:\s*"((?:\\.|[^"\\])*)")?)re");
    for (std::sregex_iterator it(response.begin(), response.end(), pattern), end; it != end; ++it)
    {
        ChatDirectorReply reply;
        reply.botGuid = (uint32)std::stoul((*it)[1].str());
        reply.text = JsonUnescape((*it)[2].str());
        reply.delayMs = std::max<uint32>(1200, std::min<uint32>(8000, (uint32)std::stoul((*it)[3].str())));
        if ((*it)[4].matched) reply.requiresActionId = JsonUnescape((*it)[4].str());
        if (!reply.text.empty()) replies.push_back(std::move(reply));
    }
    return replies;
}

std::vector<ChatDirectorActionProposal> PlayerbotChatDirector::ParseActionProposals(const std::string& response) const
{
    std::vector<ChatDirectorActionProposal> proposals;
    std::regex pattern(R"re("proposal_id"\s*:\s*"([^"\\]+)"\s*,\s*"bot_guid"\s*:\s*([0-9]+)\s*,\s*"target_guid"\s*:\s*([0-9]+)\s*,\s*"type"\s*:\s*"([^"\\]+)"\s*,\s*"capability_ref"\s*:\s*"([^"\\]+)"\s*,\s*"quantity"\s*:\s*([0-9]+)\s*,\s*"delivery"\s*:\s*"([^"\\]+)"\s*,\s*"intent"\s*:\s*"((?:\\.|[^"\\])*)")re");
    for (std::sregex_iterator it(response.begin(), response.end(), pattern), end; it != end; ++it)
    {
        ChatDirectorActionProposal proposal;
        proposal.proposalId = (*it)[1].str();
        proposal.botGuid = (uint32)std::stoul((*it)[2].str());
        proposal.targetGuid = (uint32)std::stoul((*it)[3].str());
        proposal.type = (*it)[4].str();
        proposal.capabilityRef = (*it)[5].str();
        proposal.quantity = (uint32)std::stoul((*it)[6].str());
        proposal.delivery = (*it)[7].str();
        proposal.intent = JsonUnescape((*it)[8].str());
        proposals.push_back(std::move(proposal));
    }
    return proposals;
}

void PlayerbotChatDirector::Dispatch(const ScheduledReply& scheduledReply)
{
    Player* bot = sRandomPlayerbotMgr.GetPlayerBot(scheduledReply.reply.botGuid);
    if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld())
        return;
    PlayerbotAI* ai = bot->GetPlayerbotAI();
    const std::string& channel = scheduledReply.event.channelType;
    const std::string& text = scheduledReply.reply.text;
    if (channel == "whisper") ai->Whisper(text, scheduledReply.event.speakerName, true);
    else if (channel == "party") ai->SayToParty(text, true);
    else if (channel == "raid") ai->SayToRaid(text);
    else if (channel == "guild") ai->SayToGuild(text, true);
    else if (channel == "world") ai->SayToWorld(text);
    else if (channel == "trade") ai->SayToTrade(text);
    else if (channel == "lfg") ai->SayToLFG(text);
    else if (channel == "yell") ai->Yell(text, true);
    else if (channel == "say") ai->Say(text, true);
    else ai->SayToGeneral(text);
}

void PlayerbotChatDirector::Update()
{
    if (!sPlayerbotAIConfig.chatDirectorV2)
        return;
    const auto now = std::chrono::steady_clock::now();
    MaybeCreateAmbientEvent(now);
    MaybeReportBotHealth(now);
    sPlayerbotActionBroker.Update();

    std::vector<ChatDirectorEvent> ready;
    {
        std::lock_guard<std::mutex> guard(mutex);
        for (auto it = pending.begin(); it != pending.end();)
        {
            if (std::chrono::duration_cast<std::chrono::milliseconds>(now - it->second.firstSeen).count() < 150)
            {
                ++it;
                continue;
            }
            ready.push_back(std::move(it->second));
            it = pending.erase(it);
        }
    }

    for (ChatDirectorEvent& event : ready)
    {
        std::string request = BuildJson(event);
        ActiveRequest activeRequest;
        activeRequest.event = std::move(event);
        activeRequest.response = std::async(std::launch::async, [request]()
        {
            std::vector<std::string> debug;
            return PlayerbotLLMInterface::Generate(request, sPlayerbotAIConfig.llmGenerationTimeout,
                sPlayerbotAIConfig.llmMaxSimultaniousGenerations, debug, true);
        });
        active.push_back(std::move(activeRequest));
    }

    for (auto it = active.begin(); it != active.end();)
    {
        if (it->response.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready)
        {
            ++it;
            continue;
        }
        std::string response = it->response.get();
        std::vector<ChatDirectorReply> replies = ParseReplies(response);
        std::vector<ChatDirectorActionProposal> proposals = ParseActionProposals(response);
        std::map<std::string, bool> created;
        for (const ChatDirectorActionProposal& proposal : proposals)
            created[proposal.proposalId] = sPlayerbotActionBroker.Create(proposal, it->event);
        for (ChatDirectorReply& reply : replies)
        {
            if (it->event.candidates.find(reply.botGuid) == it->event.candidates.end())
                continue;
            if (!reply.requiresActionId.empty() && !created[reply.requiresActionId])
                continue;
            ScheduledReply item;
            item.event = it->event;
            item.reply = std::move(reply);
            item.due = now + std::chrono::milliseconds(item.reply.delayMs);
            scheduled.push_back(std::move(item));
        }
        it = active.erase(it);
    }

    for (auto it = scheduled.begin(); it != scheduled.end();)
    {
        if (now < it->due)
        {
            ++it;
            continue;
        }
        if (std::chrono::duration_cast<std::chrono::seconds>(now - it->event.firstSeen).count() <= 15 || it->event.channelType == "whisper")
            Dispatch(*it);
        it = scheduled.erase(it);
    }
}
