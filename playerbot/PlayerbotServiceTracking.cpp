#include "playerbot/playerbot.h"
#include "PlayerbotServiceTracking.h"
#include "PlayerbotAIConfig.h"
#include "RandomPlayerbotMgr.h"
#include "TravelMgr.h"
#include "strategy/values/BudgetValues.h"
#include "strategy/values/ItemUsageValue.h"
#include "Mails/Mail.h"
#include <atomic>

using namespace ai;

namespace
{
    std::atomic<bool> ready{false};
    time_t nextSchema = 0, nextSample = 0, nextPrune = 0;
    uint32 sampleCursor = 0;

    std::string SqlText(std::string value, size_t limit)
    {
        value.resize(std::min(limit, value.size()));
        CharacterDatabase.escape_string(value);
        return value;
    }

    struct Identity
    {
        std::string name, role = "solo";
        uint32 group = 0, leader = 0;
        Identity(Player* bot) : name(SqlText(bot->GetName(), 64))
        {
            if (Group* party = bot->GetGroup())
            {
                group = party->GetId();
                leader = party->GetLeaderGuid().GetCounter();
                bool human = false;
                uint32 seen = 0;
                for (GroupReference* ref = party->GetFirstMember(); ref; ref = ref->next())
                    if (Player* member = ref->getSource())
                    {
                        ++seen;
                        human |= member->isRealPlayer();
                    }
                role = human ? "human_party" : seen < party->GetMembersCount() ? "group_unknown" :
                    leader == bot->GetGUIDLow() ? "bot_party_leader" : "bot_party_follower";
            }
        }
    };

    bool Trackable(Player* bot)
    {
        return ready && bot && bot->IsInWorld() && bot->GetPlayerbotAI() && !bot->isRealPlayer();
    }

    void Observe(Player* bot, const char* service, bool needed, const std::string& condition)
    {
        PlayerbotAI* ai = bot->GetPlayerbotAI();
        AiObjectContext* context = ai->GetAiObjectContext();
        Identity who(bot);
        TravelTarget* target = AI_VALUE(TravelTarget*, "travel target");
        std::string destination = target && target->GetDestination() ?
            SqlText(target->GetDestination()->GetTitle(), 255) : "";
        // Context, not an invented reason why this particular service is delayed.
        std::string state = !needed ? "not_needed" : !bot->IsAlive() ? "dead" :
            bot->IsInCombat() ? "combat" : !condition.empty() ? condition :
            ai->HasStrategy("follow", BotState::BOT_STATE_NON_COMBAT) && who.group && who.leader != bot->GetGUIDLow() ?
                "following_party" : target && target->GetStatus() == TravelStatus::TRAVEL_STATUS_TRAVEL ?
                    "traveling_current_destination" : "pending_service_selection";
        CharacterDatabase.PExecute(
            "INSERT INTO living_service_needs (bot_guid,service,bot_name,party_role,group_id,leader_guid,"
            "need_active,first_needed_at,last_observed_at,observation_state,active_destination_entry,"
            "active_destination,travel_status,travel_retries) "
            "VALUES (%u,'%s','%s','%s',%u,%u,%u,IF(%u,UNIX_TIMESTAMP(),NULL),UNIX_TIMESTAMP(),'%s',%i,'%s',%u,%u) "
            "ON DUPLICATE KEY UPDATE bot_name=VALUES(bot_name),party_role=VALUES(party_role),"
            "group_id=VALUES(group_id),leader_guid=VALUES(leader_guid),"
            "first_needed_at=IF(VALUES(need_active),IF(COALESCE(need_active,0)=1,COALESCE(first_needed_at,UNIX_TIMESTAMP()),UNIX_TIMESTAMP()),NULL),"
            "need_active=VALUES(need_active),last_observed_at=VALUES(last_observed_at),"
            "observation_state=VALUES(observation_state),active_destination_entry=VALUES(active_destination_entry),"
            "active_destination=VALUES(active_destination),travel_status=VALUES(travel_status),travel_retries=VALUES(travel_retries)",
            bot->GetGUIDLow(), service, who.name.c_str(), who.role.c_str(), who.group, who.leader,
            unsigned(needed), unsigned(needed), state.c_str(), target ? target->GetEntry() : 0,
            destination.c_str(), target ? unsigned(target->GetStatus()) : 0, target ? target->GetRetryCount(true) : 0);
    }

    void Sample(Player* bot)
    {
        PlayerbotAI* ai = bot->GetPlayerbotAI();
        AiObjectContext* context = ai->GetAiObjectContext();
        // Reuse cached gameplay predicates; do not choose destinations or change strategies.
        Observe(bot, "class_training", !AI_VALUE2(std::vector<TrainerSpell const*>, "trainable spells", TRAINER_TYPE_CLASS).empty(), "");
        Observe(bot, "profession_training", !AI_VALUE2(std::vector<TrainerSpell const*>, "trainable spells", TRAINER_TYPE_TRADESKILLS).empty(), "");
        Observe(bot, "repair", AI_VALUE(bool, "should repair"),
            !ai->HasStrategy("rpg maintenance", BotState::BOT_STATE_NON_COMBAT) ? "repair_strategy_disabled" :
            AI_VALUE(uint32, "min repair cost") >= AI_VALUE2(uint32, "free money for", uint32(NeedMoneyFor::repair)) ? "repair_budget_insufficient" : "");
        Observe(bot, "sell", AI_VALUE(bool, "should sell"),
            !ai->HasStrategy("rpg vendor", BotState::BOT_STATE_NON_COMBAT) ? "vendor_strategy_disabled" :
            AI_VALUE(bool, "can sell") ? "" : "no_vendor_classified_items");
        Observe(bot, "auction_post", AI_VALUE(bool, "should ah sell"), AI_VALUE(bool, "can ah sell") ? "" : "auction_strategy_items_or_budget_unavailable");
        const std::string bankUsage = "usage " + std::to_string(uint8(ItemUsage::ITEM_USAGE_BANK));
        bool needsWithdrawal = false;
        for (Item* item : ai->InventoryParseItems("all", IterateItemsMask::ITERATE_ITEMS_IN_BANK))
            if (ItemUsageValue::ForBankWithdrawal(ai, item) != ItemUsage::ITEM_USAGE_BANK)
            {
                needsWithdrawal = true;
                break;
            }
        Observe(bot, "bank_deposit", AI_VALUE2(uint32, "item count", bankUsage) > 0,
            AI_VALUE(uint8, "bank space") > 80 ? "bank_space_low" : "");
        Observe(bot, "bank_withdraw", needsWithdrawal, AI_VALUE(uint8, "bag space") > 80 ? "bag_space_low" : "");
        bool mailWaiting = false;
        for (auto it = bot->GetMailBegin(); it != bot->GetMailEnd(); ++it)
            if (*it && (*it)->state != MAIL_STATE_DELETED && (*it)->deliver_time <= time(nullptr) && ((*it)->money || (*it)->has_items))
                mailWaiting = true;
        Observe(bot, "mail", mailWaiting, !AI_VALUE(bool, "should get mail") ? "mail_collection_policy_wait" :
            AI_VALUE(bool, "can get mail") ? "" : "mail_strategy_or_bag_pressure");
        Observe(bot, "profession_supplies", AI_VALUE(bool, "needs profession reagents"), AI_VALUE(bool, "can buy") ? "" : "purchase_prerequisites_unavailable");
    }
}

unsigned PlayerbotServiceTracking::Durability(Player* bot)
{
    unsigned total = 0;
    // DurabilityRepairAll repairs worn gear and bag contents, not bank contents.
    for (uint8 slot = EQUIPMENT_SLOT_START; slot < INVENTORY_SLOT_ITEM_END; ++slot)
        if (Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
            total += item->GetUInt32Value(ITEM_FIELD_DURABILITY);
    for (uint8 slot = INVENTORY_SLOT_BAG_START; slot < INVENTORY_SLOT_BAG_END; ++slot)
        if (Bag* bag = (Bag*)bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
            for (uint32 i = 0; i < bag->GetBagSize(); ++i)
                if (Item* item = bag->GetItemByPos(i)) total += item->GetUInt32Value(ITEM_FIELD_DURABILITY);
    return total;
}

bool PlayerbotServiceTracking::Result(Player* bot, const char* service, unsigned target, unsigned item,
    const char* metric, unsigned before, unsigned after, bool increase, const char* failure)
{
    const bool verified = LivingServiceChanged(before, after, increase);
    if (!Trackable(bot)) return verified;
    Identity who(bot);
    const std::string reason = SqlText(verified ? "verified_change" : failure, 80);
    CharacterDatabase.PExecute(
        "INSERT INTO living_service_events (bot_guid,bot_name,service,party_role,group_id,leader_guid,target_entry,item_entry,"
        "metric,before_value,after_value,verified,reason,created_at) VALUES (%u,'%s','%s','%s',%u,%u,%u,%u,'%s',%u,%u,%u,'%s',UNIX_TIMESTAMP())",
        bot->GetGUIDLow(), who.name.c_str(), service, who.role.c_str(), who.group, who.leader, target, item,
        metric, before, after, unsigned(verified), reason.c_str());
    // An operation may only partly satisfy a need. Only Observe changes need_active.
    CharacterDatabase.PExecute(
        "INSERT INTO living_service_needs (bot_guid,service,bot_name,party_role,group_id,leader_guid,attempt_count,verified_count,"
        "last_attempt_at,last_verified_at,last_result) VALUES (%u,'%s','%s','%s',%u,%u,1,%u,UNIX_TIMESTAMP(),IF(%u,UNIX_TIMESTAMP(),NULL),'%s') "
        "ON DUPLICATE KEY UPDATE attempt_count=attempt_count+1,verified_count=verified_count+VALUES(verified_count),"
        "last_attempt_at=VALUES(last_attempt_at),last_verified_at=COALESCE(VALUES(last_verified_at),last_verified_at),last_result=VALUES(last_result)",
        bot->GetGUIDLow(), service, who.name.c_str(), who.role.c_str(), who.group, who.leader,
        unsigned(verified), unsigned(verified), reason.c_str());
    return verified;
}

void PlayerbotServiceTracking::Update()
{
    const time_t now = time(nullptr);
    if (!ready && now >= nextSchema)
    {
        nextSchema = now + 300;
        auto result = CharacterDatabase.Query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() "
            "AND table_name IN ('living_service_events','living_service_needs')");
        ready = result && result->Fetch()[0].GetUInt32() == 2;
        if (!ready) sLog.outError("Living WoW service tracking unavailable: apply sql/service_tracking.sql to characters database");
    }
    if (!ready || now < nextSample) return;
    nextSample = now + 1;
    // Ten bots per second bounds world-thread work; a 1,000-bot roster takes about 100 seconds.
    auto& players = sRandomPlayerbotMgr.GetAllBots();
    auto it = players.upper_bound(sampleCursor);
    unsigned sampled = 0;
    for (; it != players.end() && sampled < 10; ++it)
    {
        sampleCursor = it->first;
        if (!Trackable(it->second)) continue;
        Sample(it->second);
        ++sampled;
    }
    if (it == players.end()) { sampleCursor = 0; nextSample = now + 60; }
    if (now >= nextPrune)
    {
        nextPrune = now + 60;
        // Bounded batches; retain at most seven days / roughly 200,000 recent operation rows.
        CharacterDatabase.Execute("DELETE FROM living_service_events WHERE created_at < UNIX_TIMESTAMP()-604800 ORDER BY id LIMIT 10000");
        CharacterDatabase.Execute("DELETE FROM living_service_events WHERE id < (SELECT cutoff FROM "
            "(SELECT id AS cutoff FROM living_service_events ORDER BY id DESC LIMIT 1 OFFSET 199999) AS retained) ORDER BY id LIMIT 10000");
    }
}
