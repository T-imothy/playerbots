#include "botpch.h"
#include "PlayerbotOrganicEconomy.h"

#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotLLMInterface.h"
#include "RandomPlayerbotMgr.h"
#include "ServerFacade.h"
#include "strategy/ItemVisitors.h"
#include "strategy/values/ItemUsageValue.h"

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <fstream>
#include <regex>
#include <set>
#include <sstream>

namespace
{
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

    bool IsCity(uint32 zone)
    {
        static const std::set<uint32> cities = {1497,1519,1537,1637,1638,1657,3487,3557,3703};
        return cities.find(zone) != cities.end();
    }

    std::vector<uint32> KnownCraftOutputs(Player* bot, uint32 limit = 8)
    {
        std::vector<uint32> outputs;
        std::set<uint32> seen;
        for (const auto& spellPair : bot->GetSpellMap())
        {
            SpellEntry const* spell = sServerFacade.LookupSpellInfo(spellPair.first);
            if (!spell || spellPair.second.state == PLAYERSPELL_REMOVED || spellPair.second.disabled)
                continue;
            for (uint32 effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            {
                if (spell->Effect[effect] != SPELL_EFFECT_CREATE_ITEM || !spell->EffectItemType[effect])
                    continue;
                uint32 item = spell->EffectItemType[effect];
                if (sObjectMgr.GetItemPrototype(item) && seen.insert(item).second)
                    outputs.push_back(item);
                if (outputs.size() >= limit)
                    return outputs;
            }
        }
        return outputs;
    }

    bool HasAuctionSurplus(Player* bot)
    {
        ai::ListItemsVisitor inventory;
        bot->GetPlayerbotAI()->InventoryIterateItems(&inventory, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
        for (const auto& entry : inventory.items)
        {
            if (entry.second <= 0)
                continue;
            ai::ItemQualifier qualifier(entry.first);
            ai::ItemUsage usage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<ai::ItemUsage>(
                "item usage", qualifier.GetQualifier())->Get();
            if (usage == ai::ItemUsage::ITEM_USAGE_AH)
                return true;
        }
        return false;
    }
}

PlayerbotOrganicEconomy& PlayerbotOrganicEconomy::instance()
{
    static PlayerbotOrganicEconomy economy;
    return economy;
}

PlayerbotOrganicEconomy::Policy PlayerbotOrganicEconomy::LoadPolicy()
{
    Policy result;
    std::ifstream input("/srv/living-wow/config/economy.json");
    if (!input)
        return result;
    std::string source((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    std::smatch mode;
    if (std::regex_search(source, mode, std::regex("\\\"mode\\\"\\s*:\\s*\\\"(off|observe|active)\\\"")))
        result.mode = mode[1].str();
    result.careers = JsonBool(source, "careerGoals", false);
    result.posting = JsonBool(source, "characterAuctionPosting", false);
    result.buying = JsonBool(source, "characterAuctionBuying", false);
    result.commissions = JsonBool(source, "craftingCommissions", false);
    // The feature flag is the execution gate. The validated launcher keeps
    // advertising.enabled synchronized, but matching a bare "enabled" key
    // here would accidentally read the commissions section first.
    result.advertising = JsonBool(source, "professionAdvertising", false);
    result.cadenceSeconds = std::max<uint32>(60, std::min<uint32>(3600, JsonUInt(source, "cadenceSeconds", 600)));
    result.botAdCooldownSeconds = std::max<uint32>(60, JsonUInt(source, "botCooldownSeconds", 3600));
    result.channelAdCooldownSeconds = std::max<uint32>(60, JsonUInt(source, "channelCooldownSeconds", 600));
    return result;
}

std::map<uint32, PlayerbotOrganicEconomy::Profile> PlayerbotOrganicEconomy::LoadProfiles()
{
    std::map<uint32, Profile> profiles;
    std::unique_ptr<QueryResult> result = CharacterDatabase.Query(
        "SELECT profile.character_guid,profile.career_participant,COALESCE(profile.intended_profession_one,0),"
        "COALESCE(profile.intended_profession_two,0),COALESCE(goal.capability_ref,''),"
        "COALESCE(goal.goal_type,''),COALESCE(goal.state,'') FROM organic_economy_profile profile "
        "LEFT JOIN organic_economy_goal goal ON goal.goal_id=(SELECT MAX(candidate.goal_id) FROM organic_economy_goal candidate "
        "WHERE candidate.character_guid=profile.character_guid AND candidate.state IN ('active','proposed') "
        "AND (candidate.expires_at IS NULL OR candidate.expires_at>NOW()))");
    if (!result)
        return profiles;
    do
    {
        Field* fields = result->Fetch();
        Profile profile;
        profile.career = fields[1].GetBool();
        profile.intendedOne = fields[2].GetUInt32();
        profile.intendedTwo = fields[3].GetUInt32();
        profile.currentGoalId = fields[4].GetString();
        profile.currentGoalType = fields[5].GetString();
        profile.currentGoalState = fields[6].GetString();
        profiles[fields[0].GetUInt32()] = profile;
    } while (result->NextRow());
    return profiles;
}

std::string PlayerbotOrganicEconomy::CurrentGoalType(uint32 characterGuid) const
{
    auto found = profiles.find(characterGuid);
    return found == profiles.end() ? "" : found->second.currentGoalType;
}

bool PlayerbotOrganicEconomy::SafeForEconomy(Player* bot) const
{
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsInCombat() || bot->InBattleGround())
        return false;
    PlayerbotAI* ai = bot->GetPlayerbotAI();
    if (!ai || ai->GetMaster())
        return false;
    Group* group = bot->GetGroup();
    if (group)
    {
        for (GroupReference* reference = group->GetFirstMember(); reference; reference = reference->next())
        {
            Player* member = reference->getSource();
            if (member && !member->GetPlayerbotAI())
                return false;
        }
    }
    return true;
}

bool PlayerbotOrganicEconomy::Submit(const Policy& currentPolicy)
{
    profiles = LoadProfiles();
    std::ostringstream events, plans;
    events << "{\"events\":[";
    plans << "{\"bots\":[";
    bool firstEvent = true, firstBot = true;
    uint32 reportedBots = 0;
    uint32 now = uint32(time(nullptr));
    // GetPlayers() contains only the legacy manager-owned subset after the
    // Linux migration. ChatBotGuids is the same live-bot registry used by
    // health telemetry and therefore includes the autonomous population.
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        // The persistent profile table is the authoritative allow-list. It is
        // populated only for RNDBOT accounts by the migration, whereas the
        // legacy numeric random-account range can be stale after importing an
        // existing realm and would incorrectly exclude every live bot.
        if (!bot || !bot->IsInWorld() || !bot->GetPlayerbotAI())
            continue;
        auto profileIt = profiles.find(guid);
        if (profileIt == profiles.end())
            continue;
        ++reportedBots;
        Profile profile = profileIt->second;
        const uint32 professionIds[] = {164,165,171,182,186,197,202,333,393,755};
        uint32 professionOne = 0, professionTwo = 0, skillOne = 0, skillTwo = 0;
        for (uint32 skillId : professionIds)
        {
            uint32 value = bot->GetSkillValue(skillId);
            if (!value) continue;
            if (!professionOne) { professionOne = skillId; skillOne = value; }
            else if (!professionTwo) { professionTwo = skillId; skillTwo = value; break; }
        }
        std::vector<uint32> outputs = KnownCraftOutputs(bot);
        bool surplus = HasAuctionSurplus(bot);
        if (!firstEvent) events << ',';
        firstEvent = false;
        events << "{\"event_id\":\"profile-" << guid << '-' << now
            << "\",\"type\":\"profile_snapshot\",\"character_guid\":" << guid
            << ",\"character_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(bot->GetName())
            << "\",\"account_id\":" << bot->GetSession()->GetAccountId()
            << ",\"career_participant\":" << (profile.career ? "true" : "false")
            << ",\"intended_profession_one\":" << profile.intendedOne
            << ",\"intended_profession_two\":" << profile.intendedTwo
            << ",\"profession_one\":" << professionOne << ",\"profession_two\":" << professionTwo
            << ",\"profession_one_skill\":" << skillOne << ",\"profession_two_skill\":" << skillTwo
            << ",\"current_goal_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(profile.currentGoalId)
            << "\",\"current_goal_type\":\"" << PlayerbotLLMInterface::SanitizeForJson(profile.currentGoalType)
            << "\",\"current_goal_state\":\"" << PlayerbotLLMInterface::SanitizeForJson(profile.currentGoalState)
            << "\""
            << ",\"known_recipe_outputs\":[";
        for (size_t i = 0; i < outputs.size(); ++i) { if (i) events << ','; events << outputs[i]; }
        events << "],\"auction_surplus\":" << (surplus ? "true" : "false") << '}';
        if (!profile.career || currentPolicy.mode == "off")
            continue;
        if (!firstBot) plans << ',';
        firstBot = false;
        plans << "{\"character_guid\":" << guid << ",\"candidate_goals\":["
            << "{\"goal_id\":\"supplies:" << guid
            << "\",\"type\":\"maintain_supplies\",\"utility\":10,\"eligible\":true,\"duration_seconds\":3600}";
        if (!outputs.empty())
            plans << ",{\"goal_id\":\"profession:" << guid << ':' << outputs.front()
                << "\",\"type\":\"profession_skill_up\",\"utility\":30,\"eligible\":true,\"duration_seconds\":5400}";
        if (surplus)
            plans << ",{\"goal_id\":\"auction:" << guid
                << "\",\"type\":\"list_surplus\",\"utility\":20,\"eligible\":true,\"duration_seconds\":3600}";
        if (currentPolicy.advertising && IsCity(bot->GetZoneId()) && !outputs.empty())
            plans << ",{\"goal_id\":\"advertise:" << guid << ':' << outputs.front()
                << "\",\"type\":\"profession_advertisement\",\"utility\":4,\"eligible\":true,\"duration_seconds\":1800}";
        plans << "]}";
    }
    events << "]}"; plans << "]}";
    if (!reportedBots)
        return false;
    std::string eventBody = events.str(), planBody = plans.str();
    pendingPlans = std::async(std::launch::async, [eventBody, planBody]()
    {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(eventBody, 9, sPlayerbotAIConfig.llmMaxSimultaniousGenerations,
            debug, true, "/v2/economy-events");
        return PlayerbotLLMInterface::Generate(planBody, 9, sPlayerbotAIConfig.llmMaxSimultaniousGenerations,
            debug, true, "/v2/economy-plans");
    });
    return true;
}

bool PlayerbotOrganicEconomy::Advertise(Player* bot, uint32 itemEntry, const Policy& currentPolicy)
{
    auto now = std::chrono::steady_clock::now();
    if (!currentPolicy.advertising || !IsCity(bot->GetZoneId()) ||
        (lastChannelAd.time_since_epoch().count() && now - lastChannelAd < std::chrono::seconds(currentPolicy.channelAdCooldownSeconds)) ||
        (adCooldowns[bot->GetGUIDLow()].time_since_epoch().count() && now - adCooldowns[bot->GetGUIDLow()] < std::chrono::seconds(currentPolicy.botAdCooldownSeconds)))
        return false;
    std::vector<uint32> known = KnownCraftOutputs(bot, 40);
    if (std::find(known.begin(), known.end(), itemEntry) == known.end())
        return false;
    ItemPrototype const* item = sObjectMgr.GetItemPrototype(itemEntry);
    if (!item)
        return false;
    std::ostringstream text;
    text << "Crafter available: " << item->Name1 << ". Whisper me if you need one made.";
    if (!bot->GetPlayerbotAI()->SayToTrade(text.str()))
        return false;
    lastChannelAd = now;
    adCooldowns[bot->GetGUIDLow()] = now;
    return true;
}

void PlayerbotOrganicEconomy::ApplyPlans(const std::string& response, const Policy& currentPolicy)
{
    if (response.empty()) return;
    boost::property_tree::ptree root;
    std::istringstream input(response);
    try { boost::property_tree::read_json(input, root); }
    catch (...) { return; }
    auto children = root.get_child_optional("plans");
    if (!children) return;
    for (const auto& child : *children)
    {
        uint32 guid = child.second.get<uint32>("character_guid", 0);
        std::string planId = child.second.get<std::string>("plan_id", "");
        std::string goalId = child.second.get<std::string>("goal_id", "");
        std::string goalType = child.second.get<std::string>("goal_type", "");
        std::string source = child.second.get<std::string>("source", "deterministic_fallback");
        if (!guid || planId.empty() || goalId.empty()) continue;
        CharacterDatabase.PExecute(
            "UPDATE organic_economy_goal SET state='expired' WHERE character_guid='%u' AND state IN ('candidate','proposed','active')", guid);
        CharacterDatabase.PExecute(
            "INSERT INTO organic_economy_goal (character_guid,goal_type,capability_ref,state,utility,source,authoritative_payload,expires_at) "
            "VALUES ('%u','%s','%s','%s',0,'%s','{}',DATE_ADD(NOW(),INTERVAL 1 HOUR))",
            guid, goalType.c_str(), goalId.c_str(), currentPolicy.mode == "active" ? "active" : "proposed", source.c_str());
        if (currentPolicy.mode != "active") continue;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!SafeForEconomy(bot)) continue;
        auto now = std::chrono::steady_clock::now();
        if (actionCooldowns[guid].time_since_epoch().count() && now - actionCooldowns[guid] < std::chrono::minutes(10))
            continue;
        bool executed = false;
        if (goalType == "profession_skill_up" && currentPolicy.careers)
            executed = bot->GetPlayerbotAI()->DoSpecificAction("rpg craft", Event("organic economy", "", bot), true);
        else if (goalType == "list_surplus" && currentPolicy.posting)
            executed = bot->GetPlayerbotAI()->DoSpecificAction("ah", Event("organic economy", "vendor", bot), true);
        else if (goalType == "profession_advertisement" && currentPolicy.advertising)
        {
            size_t split = goalId.rfind(':');
            uint32 itemEntry = split == std::string::npos ? 0 : uint32(std::stoul(goalId.substr(split + 1)));
            executed = Advertise(bot, itemEntry, currentPolicy);
        }
        if (executed)
        {
            actionCooldowns[guid] = now;
            CharacterDatabase.PExecute("UPDATE organic_economy_goal SET state='completed' WHERE character_guid='%u' AND capability_ref='%s' AND state='active'", guid, goalId.c_str());
        }
    }
}

void PlayerbotOrganicEconomy::Update()
{
    auto now = std::chrono::steady_clock::now();
    if (!nextPolicyLoad.time_since_epoch().count() || now >= nextPolicyLoad)
    {
        policy = LoadPolicy();
        nextPolicyLoad = now + std::chrono::seconds(60);
    }
    if (pendingPlans.valid() && pendingPlans.wait_for(std::chrono::seconds(0)) == std::future_status::ready)
        ApplyPlans(pendingPlans.get(), policy);
    if (policy.mode == "off" || pendingPlans.valid() || (nextSubmit.time_since_epoch().count() && now < nextSubmit))
        return;
    // Random bots populate after the world update loop begins. An empty first
    // sample should retry quickly instead of hiding Observe telemetry for the
    // full planner cadence.
    bool submitted = Submit(policy);
    nextSubmit = now + std::chrono::seconds(submitted ? policy.cadenceSeconds : 30);
}
