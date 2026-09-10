#include "botpch.h"
#include "PlayerbotChatDirector.h"

#include "PlayerbotAI.h"
#include "PlayerbotActionBroker.h"
#include "PlayerbotSocialActionBroker.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotOrganicEconomy.h"
#include "PlayerbotChatJson.h"
#include "PlayerbotLLMInterface.h"
#include "PlayerbotRendezvousManager.h"
#include "RandomPlayerbotMgr.h"
#include "TravelMgr.h"
#include "ServerFacade.h"
#include "strategy/ItemVisitors.h"
#include "strategy/values/BudgetValues.h"
#include "strategy/values/ItemUsageValue.h"

#include <algorithm>
#include <boost/algorithm/string.hpp>
#include <fstream>
#include <functional>
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
        ChatDirectorQuest structured;
        structured.questId = questId;
        structured.title = quest->GetTitle();
        structured.status = bot->GetQuestStatus(questId) == QUEST_STATUS_COMPLETE ? "complete" : "in_progress";
        structured.shareable = bot->CanShareQuest(questId);
        QuestStatusMap const& statusMap = bot->getQuestStatusMap();
        QuestStatusMap::const_iterator status = statusMap.find(questId);
        if (status != statusMap.end())
        {
            for (uint8 objective = 0; objective < QUEST_ITEM_OBJECTIVES_COUNT; ++objective)
            {
                if (!quest->ReqItemId[objective] || !quest->ReqItemCount[objective])
                    continue;
                ItemPrototype const* item = sObjectMgr.GetItemPrototype(quest->ReqItemId[objective]);
                ChatDirectorQuest::Objective detail;
                detail.type = "item";
                detail.name = item ? item->Name1 : quest->ObjectiveText[objective];
                detail.current = status->second.m_itemcount[objective];
                detail.required = quest->ReqItemCount[objective];
                structured.objectives.push_back(detail);
            }
            for (uint8 objective = 0; objective < QUEST_OBJECTIVES_COUNT; ++objective)
            {
                int32 entry = quest->ReqCreatureOrGOId[objective];
                if (!entry || !quest->ReqCreatureOrGOCount[objective])
                    continue;
                ChatDirectorQuest::Objective detail;
                detail.type = entry < 0 ? "gameobject" : "creature";
                if (entry < 0)
                {
                    GameObjectInfo const* object = sObjectMgr.GetGameObjectInfo((uint32)-entry);
                    detail.name = object ? object->name : quest->ObjectiveText[objective];
                }
                else
                {
                    CreatureInfo const* creature = sObjectMgr.GetCreatureTemplate((uint32)entry);
                    detail.name = creature ? creature->Name : quest->ObjectiveText[objective];
                }
                detail.current = status->second.m_creatureOrGOcount[objective];
                detail.required = quest->ReqCreatureOrGOCount[objective];
                structured.objectives.push_back(detail);
            }

            for (uint8 source = 0; source < QUEST_SOURCE_ITEM_IDS_COUNT; ++source)
            {
                if (!quest->ReqSourceId[source] || !quest->ReqSourceCount[source])
                    continue;
                ItemPrototype const* item = sObjectMgr.GetItemPrototype(quest->ReqSourceId[source]);
                ChatDirectorQuest::SourceItem detail;
                detail.itemId = quest->ReqSourceId[source];
                detail.name = item ? item->Name1 : std::string("quest source item");
                detail.current = bot->GetItemCount(detail.itemId, false);
                detail.required = quest->ReqSourceCount[source];
                if (item)
                {
                    for (uint8 spell = 0; spell < MAX_ITEM_PROTO_SPELLS; ++spell)
                    {
                        if (!item->Spells[spell].SpellId || item->Spells[spell].SpellTrigger != ITEM_SPELLTRIGGER_ON_USE)
                            continue;
                        detail.useSpellId = item->Spells[spell].SpellId;
                        SpellEntry const* spellInfo = sServerFacade.LookupSpellInfo(detail.useSpellId);
                        // This helper also snapshots the real human speaker. A
                        // real player deliberately has no PlayerbotAI, so never
                        // dereference it while grounding the player's quest log.
                        PlayerbotAI* playerbotAi = bot->GetPlayerbotAI();
                        detail.usableNow = spellInfo && playerbotAi && !bot->IsInCombat() &&
                            playerbotAi->CanCastSpell(detail.useSpellId, bot, 0, false);
                        if (!detail.usableNow)
                            detail.blocker = !playerbotAi ? "player_controlled" : bot->IsInCombat() ? "in_combat" :
                                (spellInfo && spellInfo->RequiresSpellFocus ? "required_location_or_object_not_nearby" : "cast_requirements_not_met");
                        break;
                    }
                }
                structured.sourceItems.push_back(std::move(detail));
            }
        }
        candidate.quests.push_back(std::move(structured));
    }
    candidate.questLog = quests.str();
}

static void PopulateSpeakerQuestState(Player* player, ChatDirectorEvent& event)
{
    if (!player)
        return;
    ChatDirectorCandidate state;
    PopulateQuestLog(player, state);
    event.speakerQuestLog = std::move(state.questLog);
    event.speakerQuestLogTruncated = state.questLogTruncated;
    event.speakerQuests = std::move(state.quests);
}

class ChatCapabilityItemVisitor : public ai::IterateItemsVisitor
{
public:
    std::vector<Item*> items;
    bool Visit(Item* item) override
    {
        if (item && item->CanBeTraded() && !item->IsSoulBound() && !item->IsInTrade())
            items.push_back(item);
        return true;
    }
};

static const char* ItemUsageName(ai::ItemUsage usage)
{
    switch (usage)
    {
        case ai::ItemUsage::ITEM_USAGE_EQUIP: return "equip";
        case ai::ItemUsage::ITEM_USAGE_BAD_EQUIP: return "bad_equip";
        case ai::ItemUsage::ITEM_USAGE_BROKEN_EQUIP: return "broken_equip";
        case ai::ItemUsage::ITEM_USAGE_QUEST: return "quest";
        case ai::ItemUsage::ITEM_USAGE_SKILL: return "skill";
        case ai::ItemUsage::ITEM_USAGE_USE: return "use";
        case ai::ItemUsage::ITEM_USAGE_GUILD_TASK: return "guild_task";
        case ai::ItemUsage::ITEM_USAGE_DISENCHANT: return "disenchant";
        case ai::ItemUsage::ITEM_USAGE_AH: return "auction";
        case ai::ItemUsage::ITEM_USAGE_BROKEN_AH: return "broken_auction";
        case ai::ItemUsage::ITEM_USAGE_KEEP: return "keep";
        case ai::ItemUsage::ITEM_USAGE_VENDOR: return "vendor";
        case ai::ItemUsage::ITEM_USAGE_AMMO: return "ammo";
        case ai::ItemUsage::ITEM_USAGE_FORCE_NEED: return "force_need";
        case ai::ItemUsage::ITEM_USAGE_FORCE_GREED: return "force_greed";
        case ai::ItemUsage::ITEM_USAGE_BANK: return "bank";
        default: return "none";
    }
}

static bool IsProtectedEconomicUsage(ai::ItemUsage usage)
{
    return usage == ai::ItemUsage::ITEM_USAGE_EQUIP || usage == ai::ItemUsage::ITEM_USAGE_QUEST ||
        usage == ai::ItemUsage::ITEM_USAGE_KEEP || usage == ai::ItemUsage::ITEM_USAGE_FORCE_NEED ||
        usage == ai::ItemUsage::ITEM_USAGE_BANK;
}

static std::set<std::string> InventorySearchTerms(const std::string& text)
{
    static const std::set<std::string> ignored = {
        "and", "any", "anyone", "buy", "can", "could", "does", "for", "from", "give", "got", "have",
        "looking", "need", "please", "purchase", "sell", "selling", "some", "someone", "the", "trade",
        "want", "with", "wtb", "wts", "you", "your"
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

static void AddSocialCapability(ChatDirectorCandidate& candidate, const std::string& ref,
    const std::string& type, uint32 groupId, uint32 actorGuid, uint32 questId, const std::string& description)
{
    ChatDirectorCapability capability;
    capability.capabilityRef = ref;
    capability.type = type;
    capability.itemKind = "social";
    capability.quantity = 1;
    capability.minQuantity = 1;
    capability.maxQuantity = 1;
    capability.groupId = groupId;
    capability.actorGuid = actorGuid;
    capability.questId = questId;
    capability.description = description;
    capability.deliveries.push_back("immediate");
    candidate.actionCapabilities.push_back(std::move(capability));
}

static void PopulateSocialState(Player* bot, Player* speaker, ChatDirectorCandidate& candidate)
{
    if (!sPlayerbotAIConfig.chatDirectorSocialActions || !bot || !speaker)
        return;
    Group* group = bot->GetGroup();
    if (bot->GetMapId() == speaker->GetMapId() && bot->GetZoneId() == speaker->GetZoneId() &&
        !bot->IsWithinDistInMap(speaker, INTERACTION_DISTANCE))
    {
        std::ostringstream ref;
        ref << "meet:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow();
        AddSocialCapability(candidate, ref.str(), "meet_player", 0, bot->GetGUIDLow(), 0,
            "Travel to meet the player only after an explicit meetup request has been accepted.");
    }
    candidate.groupState.pendingInvite = bot->GetGroupInvite() != nullptr;
    if (!group)
    {
        if (!speaker->GetGroup() && !speaker->GetGroupInvite() && !bot->GetGroupInvite())
        {
            std::ostringstream ref;
            ref << "group:create:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow();
            AddSocialCapability(candidate, ref.str(), "create_group_and_invite", 0, bot->GetGUIDLow(), 0,
                "Create a new party and invite the player.");
        }
        if (Group* invite = bot->GetGroupInvite())
        {
            std::ostringstream ref;
            ref << "group:accept:" << invite->GetLeaderGuid().GetCounter();
            AddSocialCapability(candidate, ref.str(), "accept_group_invite", 0, bot->GetGUIDLow(), 0,
                "Accept the current pending party invitation.");
        }
        return;
    }

    ChatDirectorGroupState& state = candidate.groupState;
    state.groupId = group->GetId();
    state.leaderGuid = group->GetLeaderGuid().GetCounter();
    state.memberCount = group->GetMembersCount();
    state.raid = group->IsRaidGroup();
    state.capacity = state.raid ? 40 : 5;
    state.isLeader = group->IsLeader(bot->GetObjectGuid());
    state.isAssistant = group->IsAssistant(bot->GetObjectGuid());
    state.full = group->IsFull();
    if (Player* leader = sObjectAccessor.FindPlayer(group->GetLeaderGuid()))
        state.leaderName = leader->GetName();
    for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (member && member->IsInWorld() && member->isRealPlayer())
            state.humanMembers.push_back(member->GetName());
    }

    if (!speaker->GetGroup() && !speaker->GetGroupInvite() && !state.full)
    {
        std::ostringstream ref;
        if (state.isLeader)
        {
            ref << "group:invite:" << state.groupId << ':' << state.leaderGuid << ':' << speaker->GetGUIDLow();
            AddSocialCapability(candidate, ref.str(), "invite_to_existing_group", state.groupId,
                state.leaderGuid, 0, "Invite the player to this existing party.");
        }
        else
        {
            Player* leader = sObjectAccessor.FindPlayer(group->GetLeaderGuid());
            if (leader && leader->GetPlayerbotAI() && !leader->isRealPlayer())
            {
                ref << "group:request-leader:" << state.groupId << ':' << state.leaderGuid << ':' << speaker->GetGUIDLow();
                AddSocialCapability(candidate, ref.str(), "request_leader_invite", state.groupId,
                    state.leaderGuid, 0, "Ask the AI party leader to invite the player.");
            }
        }
    }

    if (state.isLeader && group->IsMember(speaker->GetObjectGuid()) && speaker != bot)
    {
        std::ostringstream ref;
        ref << "group:pass:" << state.groupId << ':' << speaker->GetGUIDLow();
        AddSocialCapability(candidate, ref.str(), "pass_leadership", state.groupId, bot->GetGUIDLow(), 0,
            "Pass party leadership to the requesting player.");
    }

    if (!bot->IsInCombat() && !bot->GetMap()->IsDungeon())
    {
        std::ostringstream ref;
        ref << "group:leave:" << state.groupId;
        AddSocialCapability(candidate, ref.str(), "leave_group", state.groupId, bot->GetGUIDLow(), 0,
            "Leave the current party only after an explicit confirmed request.");
    }

    if (speaker->GetGroup() == group)
    {
        for (ChatDirectorQuest& quest : candidate.quests)
        {
            std::ostringstream planRef;
            planRef << "quest:plan:" << quest.questId << ':' << state.groupId;
            AddSocialCapability(candidate, planRef.str(), "accept_party_quest_plan", state.groupId,
                bot->GetGUIDLow(), quest.questId, "Prefer this authoritative party quest when choosing the next objective.");
            Quest const* questTemplate = sObjectMgr.GetQuestTemplate(quest.questId);
            if (!quest.shareable || !questTemplate || !speaker->CanTakeQuest(questTemplate, false))
                continue;
            std::ostringstream shareRef;
            shareRef << "quest:share:" << quest.questId << ':' << state.groupId;
            AddSocialCapability(candidate, shareRef.str(), "share_quest", state.groupId,
                bot->GetGUIDLow(), quest.questId, "Share this quest with the party.");
        }
    }
}

static uint32 InventoryRelevance(const std::string& message, const ChatDirectorCandidate& candidate)
{
    std::set<std::string> requested = InventorySearchTerms(message);
    if (requested.empty())
        return 0;
    uint32 best = 0;
    for (const ChatDirectorCapability& capability : candidate.actionCapabilities)
    {
        if (requested.find("food") != requested.end() && (capability.itemKind == "food" || capability.itemKind == "food_water"))
            best = std::max<uint32>(best, 65);
        if (requested.find("water") != requested.end() && capability.itemKind == "water")
            best = std::max<uint32>(best, 65);
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

static bool IsPlayerSaleRequest(const std::string& message)
{
    std::string lowered = boost::algorithm::to_lower_copy(message);
    return std::regex_search(lowered, std::regex(R"(\bwts\b)")) ||
        lowered.find("want to buy") != std::string::npos ||
        lowered.find("wants to buy") != std::string::npos ||
        lowered.find("anyone buy") != std::string::npos ||
        lowered.find("somebody buy") != std::string::npos ||
        lowered.find("someone buy") != std::string::npos ||
        lowered.find("sell you") != std::string::npos ||
        lowered.find("selling") != std::string::npos;
}

static std::set<uint32> FindPlayerSaleItems(Player* player, const std::string& message)
{
    std::set<uint32> entries;
    for (uint32 itemId : ChatHelper::parseItems(message, true))
        entries.insert(itemId);
    if (!player || !IsPlayerSaleRequest(message))
        return entries;

    const std::set<std::string> requested = InventorySearchTerms(message);
    auto consider = [&](Item* item)
    {
        if (!item || !item->CanBeTraded() || item->IsSoulBound() || item->IsInTrade())
            return;
        ItemPrototype const* proto = item->GetProto();
        if (!proto || proto->Class == ITEM_CLASS_QUEST)
            return;
        std::set<std::string> itemTerms = InventorySearchTerms(proto->Name1);
        uint32 overlap = 0;
        for (const std::string& term : itemTerms)
            if (requested.find(term) != requested.end()) ++overlap;
        bool genericFood = requested.find("food") != requested.end() && ai::ItemUsageValue::IsHpFoodOrDrink(proto);
        bool genericWater = requested.find("water") != requested.end() && ai::ItemUsageValue::IsManaFoodOrDrink(proto);
        // One distinctive item-name word is enough for a broad offer ("a potion").
        // For multiword requests require at least half the item words, so ordinary
        // prose cannot expose unrelated bag contents to the model.
        bool nameMatch = overlap != 0 && (requested.size() == 1 || overlap * 2 >= itemTerms.size());
        if (nameMatch || genericFood || genericWater)
            entries.insert(proto->ItemId);
    };

    for (uint8 slot = INVENTORY_SLOT_ITEM_START; slot < INVENTORY_SLOT_ITEM_END; ++slot)
        consider(player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot));
    for (uint8 bagSlot = INVENTORY_SLOT_BAG_START; bagSlot < INVENTORY_SLOT_BAG_END; ++bagSlot)
    {
        Bag* bag = (Bag*)player->GetItemByPos(INVENTORY_SLOT_BAG_0, bagSlot);
        if (!bag) continue;
        for (uint32 slot = 0; slot < bag->GetBagSize(); ++slot)
            consider(bag->GetItemByPos(slot));
    }
    return entries;
}

static uint32 BuyerDemandScore(Player* bot, ai::ItemUsage usage, ItemPrototype const* proto, uint32 current,
    uint32& desired, std::string& reason)
{
    desired = current;
    const std::string activeGoal = bot ? sPlayerbotOrganicEconomy.CurrentGoalType(bot->GetGUIDLow()) : "";
    switch (usage)
    {
        case ai::ItemUsage::ITEM_USAGE_EQUIP:
        case ai::ItemUsage::ITEM_USAGE_FORCE_NEED:
            desired = std::max<uint32>(current + 1, 1); reason = "upgrade"; return 95;
        case ai::ItemUsage::ITEM_USAGE_QUEST:
            desired = std::max<uint32>(current + 1, 1); reason = "quest"; return 90;
        case ai::ItemUsage::ITEM_USAGE_AMMO:
            desired = std::max<uint32>(current + 1, proto->GetMaxStackSize() * 2);
            reason = "ammo";
            return activeGoal == "maintain_supplies" ? 95 : 85;
        case ai::ItemUsage::ITEM_USAGE_USE:
            desired = std::max<uint32>(current + 1, proto->GetMaxStackSize());
            reason = "consumable";
            return activeGoal == "maintain_supplies" ? 90 : 80;
        case ai::ItemUsage::ITEM_USAGE_SKILL:
        case ai::ItemUsage::ITEM_USAGE_GUILD_TASK:
            desired = std::max<uint32>(current + 1, proto->GetMaxStackSize());
            reason = "profession";
            return activeGoal == "profession_skill_up" ? 95 : 75;
        case ai::ItemUsage::ITEM_USAGE_DISENCHANT:
            desired = current + 1; reason = "disenchant"; return 55;
        case ai::ItemUsage::ITEM_USAGE_AH:
        case ai::ItemUsage::ITEM_USAGE_FORCE_GREED:
            desired = current + std::min<uint32>(3, std::max<uint32>(1, proto->GetMaxStackSize()));
            reason = "resale";
            return 40;
        case ai::ItemUsage::ITEM_USAGE_KEEP:
        case ai::ItemUsage::ITEM_USAGE_BANK:
            desired = std::max<uint32>(current + 1, proto->GetMaxStackSize());
            reason = "stock";
            return activeGoal == "maintain_supplies" ? 75 : 40;
        default:
            // Friendly opportunistic purchases remain possible, but the gateway
            // demand threshold admits only unusually helpful personalities.
            desired = current + 1; reason = "social_help"; return 10;
    }
}

static bool CraftCommissionsEnabled()
{
    static bool enabled = false;
    static std::chrono::steady_clock::time_point loaded;
    std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
    if (loaded.time_since_epoch().count() && now - loaded < std::chrono::seconds(60))
        return enabled;
    loaded = now;
    enabled = false;
    std::ifstream input("/srv/living-wow/config/economy.json");
    if (!input) return false;
    std::string source((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    std::smatch mode, flag;
    if (!std::regex_search(source, mode, std::regex("\\\"mode\\\"\\s*:\\s*\\\"(off|observe|active)\\\"")) ||
        mode[1].str() != "active" ||
        !std::regex_search(source, flag, std::regex("\\\"craftingCommissions\\\"\\s*:\\s*(true|false)")) ||
        flag[1].str() != "true")
        return false;
    size_t start = source.find("\"commissions\"");
    size_t end = source.find("\"advertising\"", start == std::string::npos ? 0 : start);
    if (start == std::string::npos) return false;
    std::string section = source.substr(start, end == std::string::npos ? std::string::npos : end - start);
    std::smatch detail;
    enabled = std::regex_search(section, detail, std::regex("\\\"enabled\\\"\\s*:\\s*(true|false)")) &&
        detail[1].str() == "true";
    return enabled;
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
    candidate.distanceToSpeaker = bot->GetMapId() == speaker->GetMapId() ?
        bot->GetDistance(speaker) : -1.0f;
    bool sameZone = bot->GetMapId() == speaker->GetMapId() && bot->GetZoneId() == speaker->GetZoneId();
    bool direct = sameZone && bot->IsWithinDistInMap(speaker, INTERACTION_DISTANCE);

    ChatCapabilityItemVisitor visitor;
    bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    const std::set<std::string> requestedTerms = InventorySearchTerms(message);
    auto relevance = [&](Item* item)
    {
        if (!item || !item->GetProto())
            return uint32(0);
        std::set<std::string> itemTerms = InventorySearchTerms(item->GetProto()->Name1);
        uint32 overlap = 0;
        for (const std::string& term : requestedTerms)
            if (itemTerms.find(term) != itemTerms.end()) ++overlap;
        return overlap;
    };
    std::stable_sort(visitor.items.begin(), visitor.items.end(), [&](Item* left, Item* right)
    {
        uint32 leftRelevance = relevance(left);
        uint32 rightRelevance = relevance(right);
        return leftRelevance > rightRelevance;
    });

    ai::ListItemsVisitor countVisitor;
    bot->GetPlayerbotAI()->InventoryIterateItems(&countVisitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
    uint32 reported = 0;
    for (Item* item : visitor.items)
    {
        ItemPrototype const* proto = item->GetProto();
        if (!proto || proto->Class == ITEM_CLASS_QUEST || reported >= 16)
            continue;
        ai::ItemUsage usage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<ai::ItemUsage>(
            "item usage", ai::ItemQualifier(item).GetQualifier())->Get();
        uint32 total = std::max<int32>(0, countVisitor.items[proto->ItemId]);
        uint32 unitPrice = ai::ItemUsageValue::GetBotSellPrice(proto, bot);
        bool manaDrink = ai::ItemUsageValue::IsManaFoodOrDrink(proto);
        bool healthFood = ai::ItemUsageValue::IsHpFoodOrDrink(proto);
        uint32 retained = 0;
        if (IsProtectedEconomicUsage(usage)) retained = total;
        else if (usage == ai::ItemUsage::ITEM_USAGE_SKILL || usage == ai::ItemUsage::ITEM_USAGE_GUILD_TASK ||
            usage == ai::ItemUsage::ITEM_USAGE_AMMO) retained = std::min<uint32>(total, proto->GetMaxStackSize());
        else if (usage == ai::ItemUsage::ITEM_USAGE_USE || manaDrink || healthFood)
            retained = std::min<uint32>(total, (manaDrink || healthFood) ? 2 : 1);
        uint32 available = total > retained ? total - retained : 0;
        uint32 maxQuantity = std::min<uint32>(item->GetCount(), available);
        if (!maxQuantity)
            continue;
        uint32 marketPrice = ai::ItemUsageValue::GetAHMedianBuyoutPricePerItem(proto);
        uint32 marketSamples = (uint32)sRandomPlayerbotMgr.GetAhPrices(proto->ItemId).size();
        uint32 vendorPrice = proto->SellPrice;
        uint32 botBuyPrice = ai::ItemUsageValue::GetBotBuyPrice(proto, bot);
        bool giftEligible = !IsProtectedEconomicUsage(usage);
        ChatDirectorCapability capability;
        std::ostringstream ref;
        ref << "item:" << proto->ItemId << ':' << item->GetGUIDLow();
        capability.capabilityRef = ref.str();
        capability.type = "sell_item";
        capability.itemName = proto->Name1;
        capability.itemUsage = ItemUsageName(usage);
        capability.economicVersion = 1;
        capability.itemId = proto->ItemId;
        capability.quality = proto->Quality;
        if (manaDrink) capability.itemKind = "water";
        else if (healthFood) capability.itemKind = "food";
        else capability.itemKind = "item";
        capability.quantity = maxQuantity;
        capability.minQuantity = 1;
        capability.maxQuantity = maxQuantity;
        capability.totalQuantity = total;
        capability.reserveQuantity = retained;
        capability.disposableQuantity = available;
        capability.priceCopper = maxQuantity * unitPrice;
        capability.valueCopper = maxQuantity * unitPrice;
        capability.vendorSellCopper = vendorPrice;
        capability.playerbotSellCopper = unitPrice;
        capability.playerbotBuyCopper = botBuyPrice;
        capability.marketUnitCopper = marketPrice;
        capability.marketSamples = marketSamples;
        capability.minimumUnitPriceCopper = std::max<uint32>(vendorPrice + std::max<uint32>(1, vendorPrice / 10), std::max<uint32>(1, unitPrice * 35 / 100));
        capability.maximumUnitPriceCopper = std::max<uint32>(unitPrice * 5, marketPrice * 2);
        capability.giftEligible = giftEligible;
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
            capability.giftEligible = true;
            if (direct) capability.deliveries.push_back("direct");
            capability.deliveries.push_back("meeting");
            candidate.actionCapabilities.push_back(std::move(capability));
        }
    }

    if (sameZone)
    {
        for (uint32 itemId : FindPlayerSaleItems(speaker, message))
        {
            ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);
            uint32 available = std::min<uint32>(5, CountTradeablePlayerItem(speaker, itemId));
            uint32 unitPrice = proto ? ai::ItemUsageValue::GetBotBuyPrice(proto, bot) : 0;
            uint32 freeMoney = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint32>(
                "free money for", std::to_string((uint32)NeedMoneyFor::anything))->Get();
            uint32 minimumUnitPrice = std::max<uint32>(1, unitPrice / 2);
            if (!proto || proto->Class == ITEM_CLASS_QUEST || !available || !unitPrice || freeMoney < minimumUnitPrice)
                continue;
            ai::ItemQualifier qualifier(itemId);
            ai::ItemUsage usage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<ai::ItemUsage>(
                "item usage", qualifier.GetQualifier())->Get();
            uint32 currentQuantity = std::max<int32>(0, countVisitor.items[itemId]);
            uint32 desiredQuantity = currentQuantity;
            std::string demandReason;
            uint32 demandScore = BuyerDemandScore(bot, usage, proto, currentQuantity, desiredQuantity, demandReason);
            if (proto->Class == ITEM_CLASS_CONTAINER && proto->SubClass == ITEM_SUBCLASS_CONTAINER &&
                proto->ContainerSlots > ai::ItemUsageValue::GetSmallestBagSize(bot))
            {
                demandScore = 100;
                demandReason = "bag_space_upgrade";
                desiredQuantity = currentQuantity + 1;
            }
            uint32 missingQuantity = desiredQuantity > currentQuantity ? desiredQuantity - currentQuantity : 0;
            uint32 affordableQuantity = std::min<uint32>(available, std::max<uint32>(1, freeMoney / unitPrice));
            affordableQuantity = std::min<uint32>(affordableQuantity, std::min<uint32>(5, missingQuantity));
            if (!affordableQuantity) continue;
            uint32 maximumUnitPrice = std::min<uint32>(unitPrice, freeMoney / affordableQuantity);
            if (maximumUnitPrice < minimumUnitPrice) continue;
            ChatDirectorCapability capability;
            capability.capabilityRef = "buy:" + std::to_string(itemId);
            capability.type = "buy_item";
            capability.itemName = proto->Name1;
            if (ai::ItemUsageValue::IsManaFoodOrDrink(proto)) capability.itemKind = "water";
            else if (ai::ItemUsageValue::IsHpFoodOrDrink(proto)) capability.itemKind = "food";
            else capability.itemKind = "item";
            capability.quantity = available;
            capability.minQuantity = 1;
            capability.maxQuantity = affordableQuantity;
            capability.priceCopper = unitPrice;
            capability.valueCopper = unitPrice;
            capability.economicVersion = 1;
            capability.itemId = proto->ItemId;
            capability.quality = proto->Quality;
            capability.itemUsage = ItemUsageName(usage);
            capability.demandReason = demandReason;
            capability.demandScore = demandScore;
            capability.currentQuantity = currentQuantity;
            capability.desiredQuantity = desiredQuantity;
            capability.totalQuantity = available;
            capability.disposableQuantity = capability.maxQuantity;
            capability.playerbotBuyCopper = unitPrice;
            capability.playerbotSellCopper = ai::ItemUsageValue::GetBotSellPrice(proto, bot);
            capability.vendorSellCopper = proto->SellPrice;
            capability.marketUnitCopper = ai::ItemUsageValue::GetAHMedianBuyoutPricePerItem(proto);
            capability.marketSamples = (uint32)sRandomPlayerbotMgr.GetAhPrices(proto->ItemId).size();
            capability.minimumUnitPriceCopper = minimumUnitPrice;
            capability.maximumUnitPriceCopper = maximumUnitPrice;
            if (demandReason == "bag_space_upgrade")
            {
                uint8 used = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
                capability.description = "Immediate bag-space upgrade; current inventory usage is " +
                    std::to_string((uint32)used) + " percent. If no free receive slot exists, vendor safely before trading.";
            }
            if (direct) capability.deliveries.push_back("direct");
            capability.deliveries.push_back("meeting");
            candidate.actionCapabilities.push_back(std::move(capability));
        }
    }

    if (sameZone && CraftCommissionsEnabled())
    {
        std::string lowered = boost::algorithm::to_lower_copy(message);
        bool craftRequest = lowered.find("craft") != std::string::npos || lowered.find("make") != std::string::npos ||
            lowered.find("forge") != std::string::npos || lowered.find("sew") != std::string::npos ||
            lowered.find("brew") != std::string::npos || lowered.find("commission") != std::string::npos;
        if (craftRequest)
        {
            const std::set<std::string> requested = InventorySearchTerms(message);
            uint32 reportedRecipes = 0;
            for (const auto& spellPair : bot->GetSpellMap())
            {
                uint32 spellId = spellPair.first;
                SpellEntry const* spell = sServerFacade.LookupSpellInfo(spellId);
                if (!spell || spellPair.second.state == PLAYERSPELL_REMOVED || spellPair.second.disabled)
                    continue;
                for (uint32 effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
                {
                    if (spell->Effect[effect] != SPELL_EFFECT_CREATE_ITEM || !spell->EffectItemType[effect])
                        continue;
                    uint32 itemEntry = spell->EffectItemType[effect];
                    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemEntry);
                    if (!proto) continue;
                    std::set<std::string> itemTerms = InventorySearchTerms(proto->Name1);
                    bool namedMatch = false;
                    for (const std::string& term : requested)
                        if (itemTerms.find(term) != itemTerms.end()) { namedMatch = true; break; }
                    if (!namedMatch && requested.size() > 1) continue;
                    bool canCraft = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<bool>(
                        "can craft spell", std::to_string(spellId))->Get();
                    uint32 craftCount = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint32>(
                        "has reagents for", std::to_string(spellId))->Get();
                    if (!canCraft || !craftCount) continue;
                    ChatDirectorCapability capability;
                    capability.capabilityRef = "spell:craft:" + std::to_string(spellId) + ':' + std::to_string(itemEntry);
                    capability.type = "craft_commission";
                    capability.itemId = itemEntry;
                    capability.itemName = proto->Name1;
                    capability.itemKind = "crafted_item";
                    capability.itemUsage = "commission";
                    capability.quantity = 1;
                    capability.minQuantity = 1;
                    capability.maxQuantity = 1;
                    capability.priceCopper = ai::ItemUsageValue::GetCraftingFee(proto);
                    capability.description = "Known recipe; bot-owned materials and required station are ready.";
                    if (direct) capability.deliveries.push_back("direct");
                    capability.deliveries.push_back("meeting");
                    if (!(proto->Flags & ITEM_FLAG_CONJURED)) capability.deliveries.push_back("mail");
                    candidate.actionCapabilities.push_back(std::move(capability));
                    if (++reportedRecipes >= 6) break;
                }
                if (reportedRecipes >= 6) break;
            }
        }
    }

    // A full party member can truthfully offer a scoped vendor trip.  The
    // action broker, not the language model, owns the travel and return.
    if (speaker && sameZone && bot->GetGroup() && bot->GetGroup() == speaker->GetGroup() &&
        !bot->IsInCombat())
    {
        uint8 bagUsage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
        if (bagUsage > 80)
        {
            ChatDirectorCapability capability;
            capability.capabilityRef = "vendor:" + std::to_string(bot->GetGUIDLow()) + ':' +
                std::to_string(speaker->GetGUIDLow());
            capability.type = "vendor_bags";
            capability.quantity = 1;
            capability.minQuantity = 1;
            capability.maxQuantity = 1;
            capability.deliveries.push_back("immediate");
            capability.description = "Inventory is " + std::to_string((uint32)bagUsage) +
                " percent full and contains items safe to sell to a normal vendor.";
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

static uint32 SharedQuestId(Player* left, Player* right)
{
    if (!left || !right)
        return 0;
    std::set<uint32> leftQuests;
    for (uint16 slot = 0; slot < MAX_QUEST_LOG_SIZE; ++slot)
    {
        uint32 questId = left->GetQuestSlotQuestId(slot);
        if (questId && left->GetQuestStatus(questId) == QUEST_STATUS_INCOMPLETE)
            leftQuests.insert(questId);
    }
    for (uint16 slot = 0; slot < MAX_QUEST_LOG_SIZE; ++slot)
    {
        uint32 questId = right->GetQuestSlotQuestId(slot);
        if (questId && right->GetQuestStatus(questId) == QUEST_STATUS_INCOMPLETE && leftQuests.find(questId) != leftQuests.end())
            return questId;
    }
    return 0;
}

void PlayerbotChatDirector::MaybeCreateProactiveGroupEvent(std::chrono::steady_clock::time_point now)
{
    static std::chrono::steady_clock::time_point nextCheck;
    if (!sPlayerbotAIConfig.chatDirectorSocialActions || !sPlayerbotAIConfig.chatDirectorProactiveGrouping ||
        (nextCheck.time_since_epoch().count() && now < nextCheck))
        return;
    nextCheck = now + std::chrono::seconds(5);

    for (const auto& playerPair : sRandomPlayerbotMgr.GetPlayers())
    {
        Player* player = playerPair.second;
        if (!player || !player->IsInWorld() || !player->isRealPlayer() || !player->IsAlive() || player->IsInCombat() ||
            player->isAFK() || player->isDND() || player->InBattleGround() || player->GetGroup() || player->GetGroupInvite())
            continue;
        auto playerCooldown = proactivePlayerCooldowns.find(player->GetGUIDLow());
        if (playerCooldown != proactivePlayerCooldowns.end() &&
            std::chrono::duration_cast<std::chrono::seconds>(now - playerCooldown->second).count() <
                sPlayerbotAIConfig.chatDirectorProactivePlayerCooldownSeconds)
            continue;

        for (uint32 botGuid : sRandomPlayerbotMgr.GetChatBotGuids())
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(botGuid);
            if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld() || !bot->IsAlive() || bot->IsInCombat() ||
                bot->InBattleGround() || bot->GetTeam() != player->GetTeam() || bot->GetMapId() != player->GetMapId() ||
                bot->GetInstanceId() != player->GetInstanceId() || !bot->IsWithinDistInMap(player, (float)sPlayerbotAIConfig.chatDirectorSharedActivityDistance) ||
                std::abs((int)bot->GetLevel() - (int)player->GetLevel()) > (int)sPlayerbotAIConfig.chatDirectorMaximumLevelDifference)
                continue;
            Group* group = bot->GetGroup();
            if (group && (group->IsFull() || (!group->IsLeader(bot->GetObjectGuid()) &&
                (!sObjectAccessor.FindPlayer(group->GetLeaderGuid()) ||
                 !sObjectAccessor.FindPlayer(group->GetLeaderGuid())->GetPlayerbotAI()))))
                continue;
            uint32 sharedQuest = SharedQuestId(bot, player);
            if (!sharedQuest)
                continue;

            std::ostringstream pairKey;
            pairKey << player->GetGUIDLow() << ':' << botGuid;
            SharedActivityState& state = sharedActivity[pairKey.str()];
            if (state.firstSeen.time_since_epoch().count() == 0 ||
                (state.lastSeen.time_since_epoch().count() &&
                 std::chrono::duration_cast<std::chrono::seconds>(now - state.lastSeen).count() > 15))
                state.firstSeen = now;
            state.lastSeen = now;
            if (state.lastOffer.time_since_epoch().count() &&
                std::chrono::duration_cast<std::chrono::seconds>(now - state.lastOffer).count() <
                    sPlayerbotAIConfig.chatDirectorProactivePairCooldownSeconds)
                continue;
            if (std::chrono::duration_cast<std::chrono::seconds>(now - state.firstSeen).count() <
                sPlayerbotAIConfig.chatDirectorSharedActivitySeconds)
                continue;

            Quest const* quest = sObjectMgr.GetQuestTemplate(sharedQuest);
            ChatDirectorEvent event;
            std::ostringstream id;
            id << "wow-proactive-group-" << time(nullptr) << '-' << ++sequence;
            event.eventId = id.str();
            event.key = event.eventId;
            event.channelType = "whisper";
            event.channelName = "whisper";
            event.speakerName = player->GetName();
            event.speakerGuid = player->GetGUIDLow();
            event.speakerLevel = player->GetLevel();
            PopulateSpeakerQuestState(player, event);
            event.zone = player->GetZoneId();
            event.team = player->GetTeam();
            event.ambient = true;
            event.factualGrounding = true;
            event.groundingType = "shared_quest_activity";
            event.firstSeen = now;
            event.message = "[authoritative proactive grouping opportunity] The player and this character have been working near each other on the shared quest " +
                std::string(quest ? quest->GetTitle() : "the same objective") +
                ". Ask naturally whether the player wants to group. Do not send or claim an invitation until the player agrees.";

            ChatDirectorCandidate candidate;
            candidate.guid = botGuid;
            candidate.name = bot->GetName();
            candidate.race = bot->getRace();
            candidate.cls = bot->getClass();
            candidate.level = bot->GetLevel();
            candidate.zone = bot->GetZoneId();
            candidate.grouped = group != nullptr;
            candidate.inCombat = false;
            candidate.available = true;
            candidate.currentActivity = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
            PopulateQuestLog(bot, candidate);
            PopulateGrounding(bot, player, event.message, candidate);
            PopulateSocialState(bot, player, candidate);
            if (PlayerbotAI::IsTank(bot, false)) candidate.role = "tank";
            else if (PlayerbotAI::IsHeal(bot, false)) candidate.role = "healer";
            else candidate.role = "damage";
            bool canOfferGroup = false;
            for (const ChatDirectorCapability& capability : candidate.actionCapabilities)
                if (capability.type == "create_group_and_invite" || capability.type == "invite_to_existing_group" ||
                    capability.type == "request_leader_invite") canOfferGroup = true;
            event.candidates[botGuid] = std::move(candidate);
            if (canOfferGroup)
            {
                std::lock_guard<std::mutex> guard(mutex);
                pending[event.eventId] = std::move(event);
                state.lastOffer = now;
                proactivePlayerCooldowns[player->GetGUIDLow()] = now;
                return;
            }
        }
    }
}

struct ProgressionQuestSnapshot
{
    uint32 active = 0;
    std::set<uint32> completed;
    std::string signature;
    std::string objectiveJson;
};

static ProgressionQuestSnapshot GetProgressionQuestSnapshot(Player* bot)
{
    ProgressionQuestSnapshot snapshot;
    std::ostringstream signature;
    std::ostringstream objectives;
    bool firstQuest = true;
    objectives << '{';
    QuestStatusMap const& statusMap = bot->getQuestStatusMap();
    for (uint16 slot = 0; slot < MAX_QUEST_LOG_SIZE; ++slot)
    {
        uint32 questId = bot->GetQuestSlotQuestId(slot);
        if (!questId) continue;
        ++snapshot.active;
        QuestStatus status = bot->GetQuestStatus(questId);
        if (status == QUEST_STATUS_COMPLETE) snapshot.completed.insert(questId);
        signature << questId << ':' << (uint32)status;
        QuestStatusMap::const_iterator progress = statusMap.find(questId);
        if (progress == statusMap.end()) continue;
        if (!firstQuest) objectives << ',';
        firstQuest = false;
        objectives << '\"' << questId << "\":{\"items\":[";
        for (uint8 i = 0; i < QUEST_ITEM_OBJECTIVES_COUNT; ++i)
        {
            if (i) objectives << ',';
            objectives << progress->second.m_itemcount[i];
            signature << ":i" << (uint32)i << '=' << progress->second.m_itemcount[i];
        }
        objectives << "],\"targets\":[";
        for (uint8 i = 0; i < QUEST_OBJECTIVES_COUNT; ++i)
        {
            if (i) objectives << ',';
            objectives << progress->second.m_creatureOrGOcount[i];
            signature << ":t" << (uint32)i << '=' << progress->second.m_creatureOrGOcount[i];
        }
        objectives << "]}";
    }
    objectives << '}';
    snapshot.signature = signature.str();
    snapshot.objectiveJson = objectives.str();
    return snapshot;
}

void PlayerbotChatDirector::MaybeReportBotHealth(std::chrono::steady_clock::time_point now)
{
    if (nextHealthSample.time_since_epoch().count() != 0 && now < nextHealthSample)
        return;
    const uint32 fullSampleSeconds = std::max<uint32>(60, sPlayerbotAIConfig.chatDirectorHealthSampleSeconds);
    const bool canarySampling = !sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.empty();
    nextHealthSample = now + std::chrono::seconds(canarySampling ? std::min<uint32>(10, fullSampleSeconds) : fullSampleSeconds);
    static std::chrono::steady_clock::time_point nextFullHealthSample;
    const bool fullSample = nextFullHealthSample.time_since_epoch().count() == 0 || now >= nextFullHealthSample;
    if (fullSample) nextFullHealthSample = now + std::chrono::seconds(fullSampleSeconds);

    std::vector<std::string> samples;
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld())
            continue;
        const bool recoveryCanary = std::find(sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.begin(),
            sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.end(), guid) !=
            sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.end();
        if (!fullSample && !recoveryCanary) continue;
        BotHealthState& state = botHealth[guid];
        if (state.lastMeaningfulProgress.time_since_epoch().count() == 0)
            state.lastMeaningfulProgress = now;
        bool levelChanged = state.lastLevel != 0 && state.lastLevel != bot->GetLevel();
        uint32 currentXp = bot->GetUInt32Value(PLAYER_XP);
        bool xpChanged = state.lastXp != 0 && state.lastXp != currentXp;
        state.lastLevel = bot->GetLevel();
        state.lastXp = currentXp;
        if (state.lastMoved.time_since_epoch().count() == 0)
        {
            state.x = bot->GetPositionX();
            state.y = bot->GetPositionY();
            state.lastMoved = now;
        }
        float dx = bot->GetPositionX() - state.x;
        float dy = bot->GetPositionY() - state.y;
        bool movedThisSample = dx * dx + dy * dy >= 1.0f;
        if (movedThisSample)
        {
            state.x = bot->GetPositionX();
            state.y = bot->GetPositionY();
            state.lastMoved = now;
        }
        std::string action = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
        std::string lowered = boost::algorithm::to_lower_copy(action);
        Player* humanMaster = bot->GetPlayerbotAI()->GetMaster();
        if (bot->GetGroup() && humanMaster && humanMaster->isRealPlayer() && humanMaster->IsInWorld() &&
            humanMaster->GetMapId() == bot->GetMapId() && bot->GetDistance(humanMaster) >
                7.0f * std::max<uint32>(10, sPlayerbotAIConfig.chatDirectorRendezvousTriggerSeconds) &&
            (lowered.find("follow") != std::string::npos || bot->GetPlayerbotAI()->HasRealPlayerMaster()))
        {
            sPlayerbotRendezvousManager.Request(bot, humanMaster,
                "group-follow-" + std::to_string(bot->GetGUIDLow()), false);
        }
        ProgressionQuestSnapshot questSnapshot = GetProgressionQuestSnapshot(bot);
        bool questProgressChanged = !state.questProgressSignature.empty() &&
            state.questProgressSignature != questSnapshot.signature;
        state.questProgressSignature = questSnapshot.signature;
        for (uint32 questId : questSnapshot.completed)
            if (!state.completedQuestSince.count(questId)) state.completedQuestSince[questId] = now;
        for (auto it = state.completedQuestSince.begin(); it != state.completedQuestSince.end();)
            if (!questSnapshot.completed.count(it->first)) it = state.completedQuestSince.erase(it); else ++it;
        MovementFlags movementFlags = bot->m_movementInfo.GetMovementFlags();
        bool playerStay = lowered.find("stay") != std::string::npos || lowered.find("wait") != std::string::npos;
        bool airborne = movementFlags & (MOVEFLAG_FALLING | MOVEFLAG_FALLINGFAR | MOVEFLAG_FLYING |
            MOVEFLAG_LEVITATING | MOVEFLAG_HOVER | MOVEFLAG_SWIMMING);
        bool excluded = !bot->IsAlive() || bot->IsInCombat() || bot->IsTaxiFlying() || bot->IsInWater() ||
            bot->IsNonMeleeSpellCasted(false) || bot->GetTransport() || playerStay || airborne;
        bool expectsMovement = lowered.find("move") != std::string::npos || lowered.find("travel") != std::string::npos ||
            lowered.find("quest") != std::string::npos || lowered.find("rpg") != std::string::npos;
        // Position changes alone are not meaningful progression. Bots that
        // shuffle a few yards while repeatedly producing no action must remain
        // eligible for recovery.
        if (levelChanged || xpChanged || questProgressChanged)
        {
            state.lastMeaningfulProgress = now;
            state.recoveryStep = 0;
            state.recoveryQuestId = 0;
            state.recoveryResult.clear();
        }
        long stillSeconds = std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMoved).count();
        long progressSeconds = std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMeaningfulProgress).count();
        uint32 stalledQuestId = 0;
        long oldestCompleteSeconds = 0;
        for (const auto& complete : state.completedQuestSince)
        {
            long age = std::chrono::duration_cast<std::chrono::seconds>(now - complete.second).count();
            if (age > oldestCompleteSeconds) oldestCompleteSeconds = age;
            if (!stalledQuestId && age >= sPlayerbotAIConfig.chatDirectorQuestStuckSeconds) stalledQuestId = complete.first;
        }
        bool noActions = lowered.find("no actions executed") != std::string::npos;
        // A bot carrying a completed quest gets a short grace period for the
        // ordinary travel strategy to find its turn-in. Do not spend its first
        // limited recovery attempt on generic objective reselection while that
        // more authoritative diagnosis is aging toward questStalled.
        bool movementStalled = questSnapshot.completed.empty() && expectsMovement && noActions &&
            progressSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        bool questStalled = stalledQuestId && noActions &&
            progressSeconds >= sPlayerbotAIConfig.chatDirectorQuestStuckSeconds;
        uint8 bagUsed = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
        bool inventoryBlocked = bagUsed >= 95;
        bool suspected = !excluded && (movementStalled || questStalled);
        std::string classification = "active";
        if (!bot->IsAlive()) classification = "dead";
        else if (bot->IsInCombat()) classification = "combat";
        else if (bot->IsTaxiFlying() || bot->GetTransport()) classification = "transport";
        else if (playerStay) classification = "group_wait";
        else if (inventoryBlocked && stillSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds) classification = "inventory_blocked";
        else if (questStalled) classification = "completed_quest_awaiting_turn_in";
        else if (movementStalled) classification = "movement_stalled";
        else if (!expectsMovement && stillSeconds >= 60) classification = "rpg_pause";

        // Recovery mode 1 observes only; mode 2 performs the least invasive
        // recovery step on the world thread. Resetting the travel target makes
        // normal quest/travel strategies choose again without teleporting or
        // modifying authoritative quest state.
        bool recoveryAllowed = sPlayerbotAIConfig.chatDirectorBotRecoveryMode >= 2 ||
            (sPlayerbotAIConfig.chatDirectorBotRecoveryMode == 1 && recoveryCanary);
        if (suspected && recoveryAllowed)
        {
            const auto oneHourAgo = now - std::chrono::hours(1);
            state.recoveryAttempts.erase(std::remove_if(state.recoveryAttempts.begin(), state.recoveryAttempts.end(),
                [&](const std::chrono::steady_clock::time_point& attempt) { return attempt < oneHourAgo; }), state.recoveryAttempts.end());
            bool cooldownReady = state.lastRecovery.time_since_epoch().count() == 0 ||
                std::chrono::duration_cast<std::chrono::seconds>(now - state.lastRecovery).count() >=
                    sPlayerbotAIConfig.chatDirectorRecoveryCooldownSeconds;
            if (cooldownReady && state.recoveryAttempts.size() < sPlayerbotAIConfig.chatDirectorMaxRecoveriesPerHour)
            {
                bool recovered = false;
                std::string recovery;
                if (inventoryBlocked && sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep >= 5)
                {
                    bool reset = bot->GetPlayerbotAI()->DoSpecificAction("progression reset travel target", Event("living progression inventory recovery"), true);
                    recovered = reset && bot->GetPlayerbotAI()->DoSpecificAction(
                        "request progression vendor travel target", Event("can move around"), true);
                    recovery = recovered ? "vendor_route_requested" :
                        (reset ? "vendor_request_rejected" : "vendor_reset_rejected");
                    state.recoveryStep = 5;
                }
                else if (questStalled && sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep >= 3)
                {
                    bool reset = bot->GetPlayerbotAI()->DoSpecificAction("progression reset travel target", Event("living progression turnin recovery"), true);
                    recovered = reset && bot->GetPlayerbotAI()->DoSpecificAction(
                        "request quest turnin target::" + std::to_string(stalledQuestId),
                        Event("can move around"), true);
                    recovery = recovered ? "quest_turnin_route_requested" :
                        (reset ? "quest_turnin_request_rejected" : "quest_turnin_reset_rejected");
                    state.recoveryQuestId = stalledQuestId;
                    state.recoveryStep = 3;
                }
                else if (state.recoveryStep >= 2 && sPlayerbotAIConfig.chatDirectorQuestInteraction &&
                    lowered.find("quest") != std::string::npos && sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep >= 6)
                {
                    recovered = bot->GetPlayerbotAI()->DoSpecificAction("use random quest item", Event("living progression quest item recovery"), true);
                    recovery = recovered ? "quest_item_used" : "quest_item_not_usable";
                    state.recoveryStep = 6;
                }
                else
                {
                    // ResetTargetAction returns false when there was no active
                    // target to clear. That is not a reason to skip choosing a
                    // new target: action-starved bots commonly have no target.
                    bool reset = bot->GetPlayerbotAI()->DoSpecificAction(
                        "progression reset travel target", Event("living progression objective recovery"), true);
                    recovered = reset;
                    if (recovered && sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep >= 2)
                        recovered = bot->GetPlayerbotAI()->DoSpecificAction(
                            "request progression quest travel target", Event("can move around"), true);
                    recovery = recovered ? "objective_route_requested" :
                        (reset ? "objective_request_rejected" : "objective_reset_rejected");
                    state.recoveryStep = std::min<uint32>(2, sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep);
                }
                state.lastRecovery = now;
                state.recoveryAttempts.push_back(now);
                state.recoveryResult = recovery;
                if (recovered)
                {
                    state.lastMoved = now;
                    classification = "recovering";
                    suspected = false;
                }
            }
        }

        // Recovery destination searches finish asynchronously. The ordinary
        // Playerbots scheduler can retain a validated READY/TRAVEL target yet
        // never select its low-relevance movement action under a busy 600-bot
        // workload. Advance only canary recovery targets and still execute the
        // normal MoveToTravelTargetAction safety checks on the world thread.
        TravelTarget* recoveryTarget = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<TravelTarget*>("travel target")->Get();
        bool boundedRecoveryTarget = false;
        if (recoveryCanary && state.recoveryStep > 0 && recoveryTarget)
        {
            for (std::string const& condition : recoveryTarget->GetConditions())
            {
                if (condition == "can move around")
                {
                    boundedRecoveryTarget = true;
                    break;
                }
            }
        }
        TravelStatus recoveryStatus = recoveryTarget ? recoveryTarget->GetStatus() :
            TravelStatus::TRAVEL_STATUS_NONE;
        if (!excluded && boundedRecoveryTarget &&
            (recoveryStatus == TravelStatus::TRAVEL_STATUS_READY ||
             recoveryStatus == TravelStatus::TRAVEL_STATUS_TRAVEL))
            bot->GetPlayerbotAI()->DoSpecificAction(
                "move to travel target", Event("living progression route continuation"), true);

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
        std::string pathStatus = movementStalled ? "movement_blocked" : (expectsMovement ? "route_ready" : "not_applicable");
        std::string zoneName, subzoneName;
        if (AreaTableEntry const* zone = GetAreaEntryByAreaID(bot->GetZoneId())) zoneName = zone->area_name[0];
        if (AreaTableEntry const* area = GetAreaEntryByAreaID(areaId)) subzoneName = area->area_name[0];
        std::ostringstream json;
        json << "{\"bot_guid\":" << guid << ",\"bot_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(bot->GetName())
             << "\",\"level\":" << (uint32)bot->GetLevel() << ",\"level_changed\":" << (levelChanged ? "true" : "false")
             << ",\"xp\":" << currentXp << ",\"xp_changed\":" << (xpChanged ? "true" : "false")
             << ",\"played_seconds\":" << bot->GetTotalPlayedTime()
             << ",\"active_quests\":" << questSnapshot.active << ",\"completed_turn_ins\":" << questSnapshot.completed.size()
             << ",\"completed_quest_ids\":[";
        bool firstCompleted = true;
        for (uint32 questId : questSnapshot.completed)
        {
            if (!firstCompleted) json << ',';
            firstCompleted = false;
            json << questId;
        }
        json << "],\"bag_used_percent\":" << (uint32)bagUsed << ",\"objective_counters\":" << questSnapshot.objectiveJson
             << ",\"classification\":\"" << classification << "\",\"suspected_stuck\":" << (suspected ? "true" : "false")
             << ",\"current_action\":\"" << PlayerbotLLMInterface::SanitizeForJson(action)
             << "\",\"quest_state\":\"" << (!questSnapshot.completed.empty() ? "completed_quest_pending" : "none_completed")
             << "\",\"path_status\":\"" << pathStatus << "\",\"zone_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(zoneName)
             << "\",\"subzone_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(subzoneName)
             << "\",\"x\":" << bot->GetPositionX() << ",\"y\":" << bot->GetPositionY()
             << ",\"server_z\":" << bot->GetPositionZ() << ",\"terrain_z\":" << (validTerrain ? terrainZ : bot->GetPositionZ())
             << ",\"mmap_z\":null,\"height_offset\":" << offset << ",\"height_fault\":" << (heightFault ? "true" : "false")
             << ",\"movement_flags\":" << movementFlags
             << ",\"last_movement_seconds\":" << stillSeconds << ",\"last_progress_seconds\":" << progressSeconds
             << ",\"oldest_completed_quest_seconds\":" << oldestCompleteSeconds
             << ",\"recovery_mode\":" << sPlayerbotAIConfig.chatDirectorBotRecoveryMode
             << ",\"recovery_canary\":" << (recoveryCanary ? "true" : "false")
             << ",\"recovery_result\":\"" << PlayerbotLLMInterface::SanitizeForJson(state.recoveryResult) << "\""
             << ",\"recoveries_last_hour\":" << state.recoveryAttempts.size()
             << ",\"recovery_step\":" << state.recoveryStep
             << ",\"recovery_target_quest_id\":" << state.recoveryQuestId
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
        body << "{\"effective_policy\":{\"mode\":\"" <<
            (sPlayerbotAIConfig.chatDirectorBotRecoveryMode == 0 ? "off" : (sPlayerbotAIConfig.chatDirectorBotRecoveryMode == 1 ? "observe" : "recover")) <<
            "\",\"sample_seconds\":" << sPlayerbotAIConfig.chatDirectorHealthSampleSeconds <<
            ",\"maximum_recovery_step\":" << sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep << "},\"samples\":[";
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

void PlayerbotChatDirector::MaybeReportProgressionTrace(std::chrono::steady_clock::time_point now)
{
    if (sPlayerbotAIConfig.chatDirectorDeepTraceBotGuids.empty()) return;
    if (nextProgressionTraceSample.time_since_epoch().count() != 0 && now < nextProgressionTraceSample) return;
    nextProgressionTraceSample = now + std::chrono::seconds(
        std::max<uint32>(5, sPlayerbotAIConfig.chatDirectorDeepTraceSampleSeconds));

    std::ostringstream body;
    body << "{\"samples\":[";
    bool first = true;
    for (uint32 guid : sPlayerbotAIConfig.chatDirectorDeepTraceBotGuids)
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld()) continue;
        BotHealthState& state = botHealth[guid];
        ProgressionQuestSnapshot quests = GetProgressionQuestSnapshot(bot);
        std::string action = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
        uint8 bagUsed = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
        long movementAge = state.lastMoved.time_since_epoch().count() == 0 ? 0 :
            std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMoved).count();
        long progressAge = state.lastMeaningfulProgress.time_since_epoch().count() == 0 ? 0 :
            std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMeaningfulProgress).count();
        if (!first) body << ',';
        first = false;
        body << "{\"deep_trace\":true,\"trace_kind\":\"world_action_evaluation\",\"bot_guid\":" << guid
             << ",\"bot_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(bot->GetName())
             << "\",\"level\":" << (uint32)bot->GetLevel() << ",\"xp\":" << bot->GetUInt32Value(PLAYER_XP)
             << ",\"alive\":" << (bot->IsAlive() ? "true" : "false")
             << ",\"in_combat\":" << (bot->IsInCombat() ? "true" : "false")
             << ",\"grouped\":" << (bot->GetGroup() ? "true" : "false")
             << ",\"bag_used_percent\":" << (uint32)bagUsed
             << ",\"travel_target_active\":" << (bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<bool>("travel target active")->Get() ? "true" : "false")
             << ",\"can_move_around\":" << (bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<bool>("can move around")->Get() ? "true" : "false")
             << ",\"no_quest_destinations\":" << (bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<bool>("no active travel destinations", "quest")->Get() ? "true" : "false")
             << ",\"has_focus_travel_target\":" << (bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<bool>("has focus travel target")->Get() ? "true" : "false")
             << ",\"last_movement_seconds\":" << movementAge << ",\"last_progress_seconds\":" << progressAge
             << ",\"x\":" << bot->GetPositionX() << ",\"y\":" << bot->GetPositionY() << ",\"z\":" << bot->GetPositionZ()
             << ",\"objective_counters\":" << quests.objectiveJson << ",\"completed_quest_ids\":[";
        bool firstQuest = true;
        for (uint32 questId : quests.completed)
        {
            if (!firstQuest) body << ',';
            firstQuest = false;
            body << questId;
        }
        body << "],\"recovery_result\":\"" << PlayerbotLLMInterface::SanitizeForJson(state.recoveryResult)
             << "\",\"recovery_step\":" << state.recoveryStep
             << ",\"recovery_target_quest_id\":" << state.recoveryQuestId
             << ",\"action_trace\":\"" << PlayerbotLLMInterface::SanitizeForJson(action) << "\"}";
    }
    body << "]}";
    if (first) return;
    const std::string payload = body.str();
    std::thread([payload]() {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(payload, 3, 2, debug, true, "/v2/bot-health");
    }).detach();
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
    // The manager-level public fan-out and the outgoing-packet observer can
    // describe the same built-in channel differently (for example, "" and
    // "General - Mulgore"). Canonical channel type keeps those observations in
    // one 150 ms event, so a successful market offer cannot be followed by a
    // second contradictory no-buyer event.
    keyStream << speakerGuid << ':' << msgType << ':' << channelType << ':' << message;
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
        {
            event.speakerLevel = speaker->GetLevel();
            PopulateSpeakerQuestState(speaker, event);
        }
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
        PopulateSocialState(bot, speaker, candidate);
    if (PlayerbotAI::IsTank(bot, false)) candidate.role = "tank";
    else if (PlayerbotAI::IsHeal(bot, false)) candidate.role = "healer";
    else candidate.role = "damage";
    found->second.candidates[candidate.guid] = std::move(candidate);
}

void PlayerbotChatDirector::ObserveGroupInviteConflict(Player* bot, Player* initiator)
{
    if (!sPlayerbotAIConfig.chatDirectorV2 || !bot || !initiator || !bot->GetPlayerbotAI() || !bot->GetGroup())
        return;

    ChatDirectorEvent event;
    std::ostringstream id;
    id << "wow-group-conflict-" << time(nullptr) << '-' << ++sequence;
    event.eventId = id.str();
    event.key = event.eventId;
    event.channelType = "whisper";
    event.channelName = "whisper";
    event.speakerName = initiator->GetName();
    event.speakerGuid = initiator->GetGUIDLow();
    event.speakerLevel = initiator->GetLevel();
    PopulateSpeakerQuestState(initiator, event);
    event.zone = initiator->GetZoneId();
    event.team = initiator->GetTeam();
    event.message = "[authoritative group invite conflict] The player tried to invite this character, but the character is already grouped. Explain the real group state and offer an existing-group invitation only if the supplied capability permits it.";
    event.factualGrounding = true;
    event.groundingType = "group_invite_conflict";
    event.firstSeen = std::chrono::steady_clock::now();

    ChatDirectorCandidate candidate;
    candidate.guid = bot->GetGUIDLow();
    candidate.name = bot->GetName();
    candidate.race = bot->getRace();
    candidate.cls = bot->getClass();
    candidate.level = bot->GetLevel();
    candidate.zone = bot->GetZoneId();
    candidate.grouped = true;
    candidate.inCombat = bot->IsInCombat();
    candidate.available = bot->IsAlive();
    candidate.currentActivity = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
    PopulateQuestLog(bot, candidate);
    PopulateGrounding(bot, initiator, event.message, candidate);
    PopulateSocialState(bot, initiator, candidate);
    if (PlayerbotAI::IsTank(bot, false)) candidate.role = "tank";
    else if (PlayerbotAI::IsHeal(bot, false)) candidate.role = "healer";
    else candidate.role = "damage";
    event.candidates[candidate.guid] = std::move(candidate);

    std::lock_guard<std::mutex> guard(mutex);
    lastConversation = std::chrono::steady_clock::now();
    pending[event.eventId] = std::move(event);
}

void PlayerbotChatDirector::ObservePartyQuestPlan(Player* bot, uint32 questId, const std::string& questName,
    const std::string& objective, const std::string& areaName, uint32 distanceYards)
{
    if (!sPlayerbotAIConfig.chatDirectorV2 || !bot || !bot->GetPlayerbotAI() || !bot->GetGroup() ||
        !questId || questName.empty() || bot->IsInCombat())
        return;

    Player* realPlayer = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (member && member->IsInWorld() && member->isRealPlayer())
        {
            realPlayer = member;
            break;
        }
    }
    if (!realPlayer)
        return;

    const auto now = std::chrono::steady_clock::now();
    std::ostringstream cooldownKey;
    cooldownKey << bot->GetGUIDLow() << ':' << questId;
    std::ostringstream groupCooldownKey;
    groupCooldownKey << "group:" << bot->GetGroup()->GetId();

    std::lock_guard<std::mutex> guard(mutex);
    auto prior = questPlanCooldowns.find(cooldownKey.str());
    if (prior != questPlanCooldowns.end() &&
        std::chrono::duration_cast<std::chrono::seconds>(now - prior->second).count() < 180)
        return;
    auto groupPrior = questPlanCooldowns.find(groupCooldownKey.str());
    if (groupPrior != questPlanCooldowns.end() &&
        std::chrono::duration_cast<std::chrono::seconds>(now - groupPrior->second).count() < 90)
        return;
    questPlanCooldowns[cooldownKey.str()] = now;
    questPlanCooldowns[groupCooldownKey.str()] = now;

    ChatDirectorEvent event;
    event.key = "party-quest-plan:" + cooldownKey.str();
    event.channelType = bot->GetGroup()->IsRaidGroup() ? "raid" : "party";
    event.channelName = event.channelType;
    event.speakerName = "Party quest state";
    event.speakerGuid = realPlayer->GetGUIDLow();
    event.speakerLevel = realPlayer->GetLevel();
    PopulateSpeakerQuestState(realPlayer, event);
    event.zone = realPlayer->GetZoneId();
    event.team = realPlayer->GetTeam();
    event.ambient = true;
    event.factualGrounding = true;
    event.groundingType = "party_quest_plan";
    event.firstSeen = now;
    std::ostringstream id;
    id << "wow-party-quest-" << time(nullptr) << '-' << ++sequence;
    event.eventId = id.str();

    std::ostringstream message;
    message << "[authoritative party quest planning opportunity] " << bot->GetName()
            << " selected quest " << questName;
    if (!objective.empty()) message << "; objective: " << objective;
    if (!areaName.empty()) message << "; destination: " << areaName;
    message << "; approximate distance: " << distanceYards << " yards. "
            << "Decide naturally whether this is worth discussing; compare the party quest logs. "
            << "Do not expose distance, internal travel status, IDs, or objective counters.";
    event.message = message.str();

    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || member->isRealPlayer() || !member->GetPlayerbotAI())
            continue;
        ChatDirectorCandidate candidate;
        candidate.guid = member->GetGUIDLow();
        candidate.name = member->GetName();
        candidate.race = member->getRace();
        candidate.cls = member->getClass();
        candidate.level = member->GetLevel();
        candidate.zone = member->GetZoneId();
        candidate.grouped = true;
        candidate.inCombat = member->IsInCombat();
        candidate.available = member->IsAlive() && !member->IsInCombat();
        candidate.currentActivity = member->GetPlayerbotAI()->HandleRemoteCommand("action");
        PopulateQuestLog(member, candidate);
        PopulateGrounding(member, realPlayer, event.message, candidate);
        PopulateSocialState(member, realPlayer, candidate);
        if (PlayerbotAI::IsTank(member, false)) candidate.role = "tank";
        else if (PlayerbotAI::IsHeal(member, false)) candidate.role = "healer";
        else candidate.role = "damage";
        event.candidates[candidate.guid] = std::move(candidate);
    }
    if (!event.candidates.empty())
        pending[event.eventId] = std::move(event);
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

static void AppendQuestJson(std::ostringstream& json, const ChatDirectorQuest& quest)
{
    json << "{\"quest_id\":" << quest.questId << ",\"title\":\""
         << PlayerbotLLMInterface::SanitizeForJson(quest.title) << "\",\"status\":\"" << quest.status
         << "\",\"shareable\":" << (quest.shareable ? "true" : "false") << ",\"objectives\":[";
    for (size_t objectiveIndex = 0; objectiveIndex < quest.objectives.size(); ++objectiveIndex)
    {
        if (objectiveIndex) json << ',';
        const ChatDirectorQuest::Objective& objective = quest.objectives[objectiveIndex];
        json << "{\"type\":\"" << objective.type << "\",\"name\":\""
             << PlayerbotLLMInterface::SanitizeForJson(objective.name) << "\",\"current\":" << objective.current
             << ",\"required\":" << objective.required << ",\"complete\":"
             << (objective.current >= objective.required ? "true" : "false") << "}";
    }
    json << "],\"source_items\":[";
    for (size_t sourceIndex = 0; sourceIndex < quest.sourceItems.size(); ++sourceIndex)
    {
        if (sourceIndex) json << ',';
        const ChatDirectorQuest::SourceItem& source = quest.sourceItems[sourceIndex];
        json << "{\"item_id\":" << source.itemId << ",\"name\":\""
             << PlayerbotLLMInterface::SanitizeForJson(source.name) << "\",\"current\":" << source.current
             << ",\"required\":" << source.required << ",\"use_spell_id\":" << source.useSpellId
             << ",\"usable_now\":" << (source.usableNow ? "true" : "false") << ",\"blocker\":\""
             << PlayerbotLLMInterface::SanitizeForJson(source.blocker) << "\"}";
    }
    json << "]}";
}

static uint32 QuestMessageRelevance(const std::string& message, const ChatDirectorCandidate& candidate)
{
    uint32 relevance = 0;
    for (const ChatDirectorQuest& quest : candidate.quests)
    {
        if (quest.status == "complete")
            continue;
        if (!quest.title.empty() && boost::algorithm::icontains(message, quest.title))
            relevance = std::max<uint32>(relevance, 2);
        for (const ChatDirectorQuest::Objective& objective : quest.objectives)
            if (!objective.name.empty() && objective.current < objective.required &&
                boost::algorithm::icontains(message, objective.name))
                relevance = std::max<uint32>(relevance, 1);
        for (const ChatDirectorQuest::SourceItem& source : quest.sourceItems)
            if (!source.name.empty() && boost::algorithm::icontains(message, source.name))
                relevance = std::max<uint32>(relevance, 2);
    }
    return relevance;
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
        uint32 leftQuest = QuestMessageRelevance(event.message, left);
        uint32 rightQuest = QuestMessageRelevance(event.message, right);
        if (leftQuest != rightQuest) return leftQuest > rightQuest;
        uint32 leftInventory = InventoryRelevance(event.message, left);
        uint32 rightInventory = InventoryRelevance(event.message, right);
        if (leftInventory != rightInventory) return leftInventory > rightInventory;
        if (leftInventory || rightInventory)
        {
            if (left.inCombat != right.inCombat) return !left.inCombat;
            bool leftDistance = left.distanceToSpeaker >= 0.0f;
            bool rightDistance = right.distanceToSpeaker >= 0.0f;
            if (leftDistance != rightDistance) return leftDistance;
            if (leftDistance && rightDistance && left.distanceToSpeaker != right.distanceToSpeaker)
                return left.distanceToSpeaker < right.distanceToSpeaker;
        }
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
    json << "\"contract_version\":3,\"message_raw\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.message) << "\",";
    json << "\"event_type\":\"" << (event.ambient ? "ambient" : "message") << "\",";
    json << "\"bridge_capabilities\":{\"reply_channel\":true,\"negotiated_price\":true,\"economic_capabilities\":1},";
    json << "\"channel\":{\"type\":\"" << event.channelType << "\",\"name\":\""
         << PlayerbotLLMInterface::SanitizeForJson(event.channelName) << "\",\"zone\":" << event.zone << "},";
    json << "\"faction\":\"" << (event.team == ALLIANCE ? "alliance" : "horde") << "\",";
    json << "\"speaker\":{\"guid\":" << event.speakerGuid << ",\"name\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.speakerName)
         << "\",\"kind\":\"" << (event.ambient ? "system" : "player") << "\",\"level\":" << (uint32)event.speakerLevel
         << ",\"quest_log\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.speakerQuestLog)
         << "\",\"quest_log_truncated\":" << (event.speakerQuestLogTruncated ? "true" : "false") << ",\"quests\":[";
    for (size_t questIndex = 0; questIndex < event.speakerQuests.size(); ++questIndex)
    {
        if (questIndex) json << ',';
        const ChatDirectorQuest& quest = event.speakerQuests[questIndex];
        AppendQuestJson(json, quest);
    }
    json << "]},";
    json << "\"message\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.message) << "\",";
    json << "\"requested_items\":[";
    bool firstRequestedItem = true;
    uint32 requestedItemCount = 0;
    for (uint32 itemId : ChatHelper::parseItems(event.message, true))
    {
        ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);
        if (!proto || requestedItemCount >= 6)
            continue;
        if (!firstRequestedItem) json << ',';
        firstRequestedItem = false;
        json << "{\"item_id\":" << itemId << ",\"item_name\":\""
             << PlayerbotLLMInterface::SanitizeForJson(proto->Name1) << "\"}";
        ++requestedItemCount;
    }
    json << "],";
    json << "\"grounding_events\":[";
    if (event.factualGrounding)
        json << "{\"type\":\"" << (event.groundingType.empty() ? "server_event" : event.groundingType)
             << "\",\"authoritative\":true}";
    json << "],\"candidates\":[";
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
             << ",\"distance_yards\":" << candidate.distanceToSpeaker
             << ",\"role\":\"" << candidate.role << "\",\"grouped\":" << (candidate.grouped ? "true" : "false")
             << ",\"current_activity\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.currentActivity) << "\""
             << ",\"quest_log\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.questLog) << "\""
             << ",\"quest_log_truncated\":" << (candidate.questLogTruncated ? "true" : "false")
             << ",\"group_state\":{\"group_id\":" << candidate.groupState.groupId
             << ",\"leader_guid\":" << candidate.groupState.leaderGuid << ",\"leader_name\":\""
             << PlayerbotLLMInterface::SanitizeForJson(candidate.groupState.leaderName)
             << "\",\"member_count\":" << candidate.groupState.memberCount << ",\"capacity\":" << candidate.groupState.capacity
             << ",\"raid\":" << (candidate.groupState.raid ? "true" : "false")
             << ",\"is_leader\":" << (candidate.groupState.isLeader ? "true" : "false")
             << ",\"is_assistant\":" << (candidate.groupState.isAssistant ? "true" : "false")
             << ",\"full\":" << (candidate.groupState.full ? "true" : "false")
             << ",\"pending_invite\":" << (candidate.groupState.pendingInvite ? "true" : "false")
             << ",\"human_members\":[";
        for (size_t humanIndex = 0; humanIndex < candidate.groupState.humanMembers.size(); ++humanIndex)
        {
            if (humanIndex) json << ',';
            json << "\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.groupState.humanMembers[humanIndex]) << "\"";
        }
        json << "]},\"quests\":[";
        for (size_t questIndex = 0; questIndex < candidate.quests.size(); ++questIndex)
        {
            if (questIndex) json << ',';
            const ChatDirectorQuest& quest = candidate.quests[questIndex];
            AppendQuestJson(json, quest);
        }
        json << "]"
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
                 << "\",\"item_usage\":\"" << capability.itemUsage
                 << "\",\"demand_reason\":\"" << capability.demandReason
                 << "\",\"economic_version\":" << capability.economicVersion
                 << ",\"demand_score\":" << capability.demandScore
                 << ",\"current_quantity\":" << capability.currentQuantity
                 << ",\"desired_quantity\":" << capability.desiredQuantity
                 << ",\"item_id\":" << capability.itemId << ",\"quality\":" << capability.quality
                 << ",\"min_quantity\":" << (capability.minQuantity ? capability.minQuantity : capability.quantity)
                 << ",\"max_quantity\":" << (capability.maxQuantity ? capability.maxQuantity : capability.quantity)
                 << ",\"total_quantity\":" << capability.totalQuantity
                 << ",\"reserve_quantity\":" << capability.reserveQuantity
                 << ",\"disposable_quantity\":" << capability.disposableQuantity
                 << ",\"price_copper\":" << capability.priceCopper << ",\"value_copper\":" << capability.valueCopper
                 << ",\"vendor_sell_copper\":" << capability.vendorSellCopper
                 << ",\"playerbot_sell_copper\":" << capability.playerbotSellCopper
                 << ",\"playerbot_buy_copper\":" << capability.playerbotBuyCopper
                 << ",\"market_unit_copper\":" << capability.marketUnitCopper
                 << ",\"market_samples\":" << capability.marketSamples
                 << ",\"minimum_unit_price_copper\":" << capability.minimumUnitPriceCopper
                 << ",\"maximum_unit_price_copper\":" << capability.maximumUnitPriceCopper
                 << ",\"gift_eligible\":" << (capability.giftEligible ? "true" : "false")
                 << ",\"quest_id\":" << capability.questId << ",\"group_id\":" << capability.groupId
                 << ",\"actor_guid\":" << capability.actorGuid << ",\"description\":\""
                 << PlayerbotLLMInterface::SanitizeForJson(capability.description) << "\""
                 << ",\"deliveries\":[";
            for (size_t deliveryIndex = 0; deliveryIndex < capability.deliveries.size(); ++deliveryIndex)
            {
                if (deliveryIndex) json << ',';
                json << "\"" << capability.deliveries[deliveryIndex] << "\"";
            }
            json << "]}";
        }
        Player* candidateBot = sRandomPlayerbotMgr.GetPlayerBot(candidate.guid);
        Player* conversationSpeaker = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, event.speakerGuid));
        json << "],\"party_combat_state\":"
             << (candidateBot ? sPlayerbotPartyCombatCoordinator.GetCandidateJson(candidateBot, conversationSpeaker) : "null")
             << "}";
    }
    json << "],\"active_economic_quotes\":[";
    sPlayerbotActionBroker.AppendEconomicQuotesJson(event.speakerGuid, event.candidates, json);
    json << "]}";
    return json.str();
}

std::vector<ChatDirectorReply> PlayerbotChatDirector::ParseReplies(const std::string& response) const
{
    std::vector<ChatDirectorReply> replies;
    LivingWowChatJson::Envelope envelope;
    std::string error;
    if (!LivingWowChatJson::ParseEnvelope(response, envelope, error))
    {
        sLog.outError("Living WoW Chat v2 response rejected: %s", error.c_str());
        return replies;
    }
    for (const LivingWowChatJson::Reply& parsed : envelope.replies)
    {
        ChatDirectorReply reply;
        reply.botGuid = parsed.botGuid;
        reply.text = parsed.text;
        reply.delayMs = std::max<uint32>(1200, std::min<uint32>(8000, parsed.delayMs));
        reply.requiresActionId = parsed.requiresActionId;
        reply.replyChannel = parsed.replyChannel;
        if (!reply.text.empty()) replies.push_back(std::move(reply));
    }
    return replies;
}

std::vector<ChatDirectorActionProposal> PlayerbotChatDirector::ParseActionProposals(const std::string& response) const
{
    std::vector<ChatDirectorActionProposal> proposals;
    LivingWowChatJson::Envelope envelope;
    std::string error;
    if (!LivingWowChatJson::ParseEnvelope(response, envelope, error))
        return proposals;
    for (const LivingWowChatJson::Proposal& parsed : envelope.proposals)
    {
        ChatDirectorActionProposal proposal;
        proposal.proposalId = parsed.proposalId;
        proposal.botGuid = parsed.botGuid;
        proposal.targetGuid = parsed.targetGuid;
        proposal.type = parsed.type;
        proposal.capabilityRef = parsed.capabilityRef;
        proposal.quantity = parsed.quantity;
        proposal.priceCopper = parsed.priceCopper;
        proposal.delivery = parsed.delivery;
        proposal.intent = parsed.intent;
        proposal.quoteId = parsed.quoteId;
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
    const std::string& channel = scheduledReply.reply.replyChannel.empty() ?
        scheduledReply.event.channelType : scheduledReply.reply.replyChannel;
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

void PlayerbotChatDirector::MaybeReportOrganicEconomy(std::chrono::steady_clock::time_point now)
{
    if (nextEconomySample.time_since_epoch().count() && now < nextEconomySample)
        return;
    nextEconomySample = now + std::chrono::minutes(10);
    std::ostringstream events, plans;
    events << "{\"events\":[";
    plans << "{\"bots\":[";
    bool firstEvent = true, firstBot = true;
    for (const auto& entry : sRandomPlayerbotMgr.GetPlayers())
    {
        Player* bot = entry.second;
        if (!bot || !bot->IsInWorld() || !sPlayerbotAIConfig.IsInRandomAccountList(bot->GetSession()->GetAccountId()))
            continue;
        uint32 guid = bot->GetGUIDLow(), account = bot->GetSession()->GetAccountId();
        bool career = ((uint64(guid) * 1103515245ULL + uint64(account) * 12345ULL) % 100ULL) < 80ULL;
        const uint32 professions[] = {164,165,171,182,186,197,202,333,393,755};
        uint32 firstProfession = 0, secondProfession = 0, firstSkill = 0, secondSkill = 0;
        for (uint32 skillId : professions)
        {
            uint32 value = bot->GetSkillValue(skillId);
            if (!value) continue;
            if (!firstProfession) { firstProfession = skillId; firstSkill = value; }
            else if (!secondProfession) { secondProfession = skillId; secondSkill = value; break; }
        }
        if (!firstEvent) events << ',';
        firstEvent = false;
        events << "{\"event_id\":\"profile-" << guid << '-' << time(nullptr)
            << "\",\"type\":\"profile_snapshot\",\"character_guid\":" << guid
            << ",\"character_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(bot->GetName())
            << "\",\"account_id\":" << account << ",\"career_participant\":" << (career ? "true" : "false")
            << ",\"profession_one\":" << firstProfession << ",\"profession_two\":" << secondProfession
            << ",\"profession_one_skill\":" << firstSkill << ",\"profession_two_skill\":" << secondSkill << '}';
        if (!career) continue;
        if (!firstBot) plans << ',';
        firstBot = false;
        plans << "{\"character_guid\":" << guid << ",\"candidate_goals\":["
            << "{\"goal_id\":\"supplies:" << guid
            << "\",\"type\":\"maintain_supplies\",\"utility\":10,\"eligible\":true,\"duration_seconds\":3600}";
        if (firstProfession)
            plans << ",{\"goal_id\":\"profession:" << guid << ':' << firstProfession
                << "\",\"type\":\"profession_skill_up\",\"utility\":25,\"eligible\":true,\"duration_seconds\":5400}";
        plans << "]}";
    }
    events << "]}"; plans << "]}";
    const std::string eventBody = events.str(), planBody = plans.str();
    std::thread([eventBody, planBody]()
    {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(eventBody, 9, sPlayerbotAIConfig.llmMaxSimultaniousGenerations, debug, true, "/v2/economy-events");
        PlayerbotLLMInterface::Generate(planBody, 9, sPlayerbotAIConfig.llmMaxSimultaniousGenerations, debug, true, "/v2/economy-plans");
    }).detach();
}

void PlayerbotChatDirector::Update()
{
    if (!sPlayerbotAIConfig.chatDirectorV2)
        return;
    const auto now = std::chrono::steady_clock::now();
    MaybeCreateAmbientEvent(now);
    MaybeCreateProactiveGroupEvent(now);
    MaybeReportBotHealth(now);
    MaybeReportProgressionTrace(now);
    sPlayerbotOrganicEconomy.Update();
    sPlayerbotActionBroker.Update();
    sPlayerbotSocialActionBroker.Update();

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
        LivingWowChatJson::Envelope envelope;
        std::string envelopeError;
        LivingWowChatJson::ParseEnvelope(response, envelope, envelopeError);
        for (const auto& quote : envelope.economicOffers) sPlayerbotActionBroker.UpsertEconomicQuote(quote, false);
        for (const auto& quote : envelope.economicQuoteUpdates) sPlayerbotActionBroker.UpsertEconomicQuote(quote, true);
        std::vector<ChatDirectorActionProposal> proposals = ParseActionProposals(response);
        std::map<std::string, bool> created;
        for (const ChatDirectorActionProposal& proposal : proposals)
        {
            bool social = sPlayerbotSocialActionBroker.Supports(proposal.type);
            bool partyCombat = sPlayerbotPartyCombatCoordinator.SupportsProposal(proposal.type);
            PlayerbotActionResult actionResult;
            bool made = false;
            if (partyCombat)
            {
                Player* bot = sRandomPlayerbotMgr.GetPlayerBot(proposal.botGuid);
                Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, proposal.targetGuid));
                made = bot && player && sPlayerbotPartyCombatCoordinator.ExecuteProposal(bot, player,
                    proposal.type, proposal.capabilityRef, proposal.intent) == "completed";
            }
            else if (social)
                made = sPlayerbotSocialActionBroker.Create(proposal, it->event);
            else
            {
                actionResult = sPlayerbotActionBroker.Create(proposal, it->event);
                made = actionResult.created;
            }
            created[proposal.proposalId] = made;
            if (made || social || partyCombat || (proposal.type != "give_item" && proposal.type != "sell_item" &&
                proposal.type != "buy_item" && proposal.type != "accept_player_gift" &&
                proposal.type != "conjure_water"))
                continue;

            sPlayerbotActionBroker.ReportRejected(proposal, it->event, actionResult.reasonCode);
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(proposal.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, proposal.targetGuid));
            if (bot && player && proposal.targetGuid == it->event.speakerGuid)
            {
                std::string failure = actionResult.playerMessage.empty() ?
                    "Sorry, I can't complete that transaction right now." : actionResult.playerMessage;
                bot->Whisper(failure, LANG_UNIVERSAL, player->GetObjectGuid());
            }
        }
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
