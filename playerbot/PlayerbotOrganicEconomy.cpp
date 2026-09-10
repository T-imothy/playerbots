#include "botpch.h"
#include "PlayerbotOrganicEconomy.h"
#include "LivingProfessionPlan.h"
#include "PlayerbotInventoryPressure.h"
#include "PlayerbotActionBroker.h"
#include "PlayerbotGuildSupplies.h"

#include "PlayerbotAI.h"
#include "PlayerbotBuildProfile.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotLLMInterface.h"
#include "PlayerbotRendezvousManager.h"
#include "RandomPlayerbotMgr.h"
#include "ServerFacade.h"
#include "strategy/ItemVisitors.h"
#include "strategy/values/ItemUsageValue.h"
#include "strategy/values/TravelValues.h"
#include "strategy/actions/BankAction.h"
#include "strategy/actions/AhAction.h"

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <fstream>
#include <regex>
#include <set>
#include <sstream>

namespace
{
    std::vector<uint32> EconomyWorkOrder(std::vector<uint32> ready, const std::set<uint32>& verifying, uint32 cursor)
    {
        if (ready.empty()) return ready;
        std::rotate(ready.begin(), ready.begin() + cursor % ready.size(), ready.end());
        std::stable_partition(ready.begin(), ready.end(), [&](uint32 guid) { return verifying.count(guid) != 0; });
        if (ready.size() > 8) ready.resize(8);
        return ready;
    }

    bool PreserveCraftResult(const std::string& attemptGoal, const std::string& activeGoal, uint32 started, uint32 now)
    {
        return attemptGoal == activeGoal && now >= started && now - started < 120;
    }

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

    // Primary-profession recipes only: knowing Cooking must not turn every
    // career into a cooking goal. Spell/skill and all reagents are real state.
    uint32 CraftSkill(Player* bot, const SpellEntry* spell)
    {
        if (!spell || spell->Effect[0] != SPELL_EFFECT_CREATE_ITEM || !spell->EffectItemType[0]) return 0;
        auto bounds = sSpellMgr.GetSkillLineAbilityMapBoundsBySpellId(spell->Id);
        for (auto it = bounds.first; it != bounds.second; ++it)
        {
            const auto* line = it->second;
            const uint32 value = bot->GetSkillValuePure(line->skillId);
            if (LivingProfessions::Primary(line->skillId) && value &&
                value < bot->GetSkillMaxPure(line->skillId) && value < line->max_value)
                return line->skillId;
        }
        return 0;
    }

    bool SafeCraftReagents(Player* bot, const SpellEntry* spell, bool includeBank = false, bool requireCounts = true)
    {
        ai::FindAllItemVisitor visitor;
        bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);
        if (includeBank)
            bot->GetPlayerbotAI()->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BANK);
        std::map<uint32, uint32> needed;
        for (uint32 i = 0; i < MAX_SPELL_REAGENTS; ++i)
            if (spell->Reagent[i] > 0 && spell->ReagentCount[i]) needed[spell->Reagent[i]] += spell->ReagentCount[i];
        for (const auto& reagent : needed)
        {
            // The native spell consumes stacks itself. Reject the whole entry
            // if any stack is promised, rather than risk consuming that stack.
            if (sGuildSupplies.ReservedEntry(bot->GetGUIDLow(), reagent.first) ||
                ai::ItemUsageValue::IsNeededForQuest(bot, reagent.first, true)) return false;
            for (Item* item : visitor.GetResult())
                if (item->GetEntry() == reagent.first &&
                    sPlayerbotActionBroker.IsItemReserved(item->GetGUIDLow())) return false;
            if (requireCounts && bot->GetItemCount(reagent.first, includeBank) < reagent.second) return false;
        }
        return !needed.empty(); // No conjuring or reagent cheats.
    }

    uint32 ReadyCraftSpell(Player* bot)
    {
        // Called on the existing ten-minute planning snapshot, not every tick.
        // CanCastSpell validates tools, local forge/anvil, bag space and cooldown.
        for (const auto& known : bot->GetSpellMap())
        {
            if (known.second.state == PLAYERSPELL_REMOVED || known.second.disabled) continue;
            const auto* spell = sServerFacade.LookupSpellInfo(known.first);
            if (CraftSkill(bot, spell) && SafeCraftReagents(bot, spell) &&
                bot->GetPlayerbotAI()->CanCastSpell(known.first, bot, 0, true)) return known.first;
        }
        return 0;
    }

    uint32 BankCraftSpell(Player* bot)
    {
        // Only propose a bank trip when ALL ingredients already exist in this
        // character's real possessions. No speculative shopping or remote craft.
        for (const auto& known : bot->GetSpellMap())
        {
            if (known.second.state == PLAYERSPELL_REMOVED || known.second.disabled) continue;
            const auto* spell = sServerFacade.LookupSpellInfo(known.first);
            if (CraftSkill(bot, spell) && !SafeCraftReagents(bot, spell) &&
                SafeCraftReagents(bot, spell, true)) return known.first;
        }
        return 0;
    }

    uint32 MarketCraftSpell(Player* bot)
    {
        // Use real cached listings, not hypothetical market stock. At most two
        // missing reagent types per job; larger gathering chains are separate.
        for (const auto& known : bot->GetSpellMap())
        {
            if (known.second.state == PLAYERSPELL_REMOVED || known.second.disabled) continue;
            const auto* spell = sServerFacade.LookupSpellInfo(known.first);
            if (!CraftSkill(bot, spell) || !SafeCraftReagents(bot, spell, true, false)) continue;
            std::map<uint32,uint32> needed;
            for (uint32 i=0;i<MAX_SPELL_REAGENTS;++i)
                if (spell->Reagent[i]>0 && spell->ReagentCount[i]) needed[spell->Reagent[i]]+=spell->ReagentCount[i];
            uint32 missing=0;bool obtainable=true;
            for (const auto& reagent:needed)
            {
                const uint32 owned=bot->GetItemCount(reagent.first,true);
                if (owned>=reagent.second) continue;
                if (++missing>2 || (!ai::AhBidAction::HasPendingMaterial(bot,reagent.first) &&
                    !ai::AhBidAction::HasMaterialOffer(bot,reagent.first,reagent.second-owned)))
                { obtainable=false;break; }
            }
            if (obtainable && missing) return known.first;
        }
        return 0;
    }
}

PlayerbotOrganicEconomy& PlayerbotOrganicEconomy::instance()
{
    static PlayerbotOrganicEconomy economy;
    return economy;
}

bool PlayerbotOrganicEconomy::CanLearnProfessionSpell(Player* bot, uint32 learnedSpell) const
{
    if (!bot || bot->isRealPlayer() || !bot->GetPlayerbotAI()) return true;
    const SpellLearnSkillNode* node = sSpellMgr.GetSpellLearnSkill(learnedSpell);
    if (!node || !LivingProfessions::Primary(node->skill) || bot->GetSkillValue(node->skill)) return true;
    auto row = profiles.find(bot->GetGUIDLow());
    // The first population snapshot may not have loaded yet. Defer only new
    // primary professions until that happens; existing skills remain trainable.
    if (row == profiles.end()) return policy.mode == "off";
    const Profile& p = row->second;
    unsigned learnedCount = 0;
    for (unsigned skill : LivingProfessions::Skills)
        if (bot->GetSkillValue(skill)) ++learnedCount;
    return LivingProfessions::Allows(false, p.career, p.planVersion,
        p.intendedOne, p.intendedTwo, node->skill, false, learnedCount);
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
        "COALESCE(goal.goal_type,''),COALESCE(goal.state,''),profile.profession_plan_version,actor.race FROM organic_economy_profile profile "
        "JOIN characters actor ON actor.guid=profile.character_guid "
        "LEFT JOIN organic_economy_goal goal ON goal.goal_id=(SELECT MAX(candidate.goal_id) FROM organic_economy_goal candidate "
        "WHERE candidate.character_guid=profile.character_guid AND candidate.state IN ('active','proposed','candidate') "
        "AND (candidate.expires_at IS NULL OR candidate.expires_at>NOW()))");
    if (result)
    {
        do
        {
            Field* fields = result->Fetch();
            Profile profile;
            profile.career = fields[1].GetBool();
            profile.planVersion = fields[7].GetUInt32();
            profile.race = fields[8].GetUInt32();
            profile.intendedOne = fields[2].GetUInt32();
            profile.intendedTwo = fields[3].GetUInt32();
            profile.currentGoalId = fields[4].GetString();
            profile.currentGoalType = fields[5].GetString();
            profile.currentGoalState = fields[6].GetString();
            profiles[fields[0].GetUInt32()] = profile;
        } while (result->NextRow());
    }

    LivingProfessions::Counts coverage[2] = {};
    unsigned population[2] = {};
    for (const auto& row : profiles)
    {
        const Profile& p = row.second;
        if (!p.career) continue;
        unsigned faction = LivingProfessions::Faction(p.race);
        ++population[faction];
        LivingProfessions::Add(coverage[faction], p.intendedOne);
        if (p.intendedTwo != p.intendedOne) LivingProfessions::Add(coverage[faction], p.intendedTwo);
    }

    // The schema migration seeds profiles for bots that exist at install time,
    // but the configured population may grow later. Enrol newly created live
    // random bots here so economy participation scales with the population.
    // Existing profiles and learned professions are never rewritten.
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        if (profiles.find(guid) != profiles.end())
            continue;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetSession())
            continue;

        uint32 account = bot->GetSession()->GetAccountId();
        uint64 seed = uint64(guid) * 1103515245ULL + uint64(account) * 12345ULL;
        Profile profile;
        profile.career = (seed % 100ULL) < 80ULL;
        profile.race = bot->getRace();
        profile.planVersion = 1;
        unsigned faction = LivingProfessions::Faction(profile.race);
        std::vector<unsigned> learned;
        for (unsigned skill : LivingProfessions::Skills)
            if (bot->GetSkillValue(skill)) learned.push_back(skill);
        auto planned = LivingProfessions::Choose(bot->getClass(), LivingProfessions::Mix(seed),
            learned, coverage[faction], population[faction] + 1);
        profile.intendedOne = planned.first;
        profile.intendedTwo = planned.second;
        if (profile.career)
        {
            ++population[faction];
            LivingProfessions::Add(coverage[faction], planned.first);
            LivingProfessions::Add(coverage[faction], planned.second);
        }
        uint32 generosity = uint32((uint64(guid) * 1664525ULL + 1013904223ULL) % 101ULL);
        uint32 thrift = uint32((uint64(guid) * 22695477ULL + 1ULL) % 101ULL);
        uint32 patience = uint32((uint64(guid) * 214013ULL + 2531011ULL) % 101ULL);
        uint32 risk = uint32((uint64(guid) * 134775813ULL + 1ULL) % 101ULL);
        CharacterDatabase.PExecute(
            "INSERT IGNORE INTO organic_economy_profile "
            "(character_guid,account_id,career_participant,intended_profession_one,intended_profession_two,"
            "generosity,thrift,bargaining_patience,risk_tolerance,profession_plan_version) VALUES (%u,%u,%u,%u,%u,%u,%u,%u,%u,1)",
            guid, account, profile.career ? 1 : 0, profile.intendedOne, profile.intendedTwo,
            generosity, thrift, patience, risk);
        profiles[guid] = profile;
    }
    return profiles;
}

std::string PlayerbotOrganicEconomy::CurrentGoalType(uint32 characterGuid) const
{
    auto found = profiles.find(characterGuid);
    return found == profiles.end() ? "" : found->second.currentGoalType;
}

uint32 PlayerbotOrganicEconomy::RecipeMaterialQuantity(uint32 guid, uint32 entry) const
{
    auto found = profiles.find(guid);
    if (policy.mode != "active" || !policy.careers || found == profiles.end() ||
        found->second.currentGoalState != "active" || found->second.currentGoalType != "profession_skill_up") return 0;
    const std::string prefix = "profession:" + std::to_string(guid) + ":";
    const auto& id = found->second.currentGoalId;
    if (id.compare(0, prefix.size(), prefix)) return 0;
    const std::string suffix = id.substr(prefix.size());
    if (suffix.empty() || suffix.size() > 9 || suffix.find_first_not_of("0123456789") != std::string::npos) return 0;
    const auto* spell = sServerFacade.LookupSpellInfo(uint32(std::stoul(suffix)));
    if (!spell) return 0;
    uint32 count = 0;
    for (uint32 i = 0; i < MAX_SPELL_REAGENTS; ++i)
        if (spell->Reagent[i] > 0 && uint32(spell->Reagent[i]) == entry) count += spell->ReagentCount[i];
    return count;
}

bool PlayerbotOrganicEconomy::SafeForEconomy(Player* bot) const
{
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsInCombat() || bot->InBattleGround() ||
        bot->IsTaxiFlying() || bot->GetTransport() || bot->IsBeingTeleported() ||
        !bot->GetMap() || bot->GetMap()->IsDungeon())
        return false;
    PlayerbotAI* ai = bot->GetPlayerbotAI();
    bool partyFreeTime = sPlayerbotRendezvousManager.IsPartyFreeTime(bot->GetGUIDLow());
    if (!ai || sPlayerbotRendezvousManager.BlocksAutonomousPartyWork(bot->GetGUIDLow()) ||
        (ai->GetMaster() && !partyFreeTime))
        return false;
    Group* group = bot->GetGroup();
    if (group)
    {
        for (GroupReference* reference = group->GetFirstMember(); reference; reference = reference->next())
        {
            Player* member = reference->getSource();
            if (member && !member->GetPlayerbotAI() && !partyFreeTime)
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
        uint32 readyRecipe = profile.career && currentPolicy.careers ? ReadyCraftSpell(bot) : 0;
        if (!readyRecipe && profile.career && currentPolicy.careers) readyRecipe = BankCraftSpell(bot);
        if (!readyRecipe && profile.career && currentPolicy.careers && currentPolicy.buying) readyRecipe = MarketCraftSpell(bot);
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
        const bool gearingNeed = sPlayerbotBuildProfiles.GearingGoalsEnabled() &&
            sPlayerbotBuildProfiles.HasGearingDeficiency(bot);
        if ((!profile.career && !gearingNeed) || currentPolicy.mode == "off")
            continue;
        if (!firstBot) plans << ',';
        firstBot = false;
        plans << "{\"character_guid\":" << guid << ",\"candidate_goals\":[";
        bool firstGoal = true;
        if (gearingNeed)
        {
            plans << "{\"goal_id\":\"gear:" << guid
                << "\",\"type\":\"equipment_upgrade\",\"utility\":"
                << sPlayerbotBuildProfiles.GearingGoalUtility(bot)
                << ",\"eligible\":true,\"duration_seconds\":3600}";
            firstGoal = false;
        }
        if (profile.career)
        {
            if (!firstGoal) plans << ',';
            plans << "{\"goal_id\":\"supplies:" << guid
                << "\",\"type\":\"maintain_supplies\",\"utility\":10,\"eligible\":true,\"duration_seconds\":3600}";
            firstGoal = false;
        }
        if (readyRecipe)
            plans << ",{\"goal_id\":\"profession:" << guid << ':' << readyRecipe
                << "\",\"type\":\"profession_skill_up\",\"utility\":70,\"eligible\":true,\"duration_seconds\":1800}";
        if (profile.career && profile.currentGoalType == "storage_pressure")
            plans << ",{\"goal_id\":\"storage:" << guid
                << "\",\"type\":\"storage_pressure\",\"utility\":100,\"eligible\":true,\"duration_seconds\":1800}";
        if (profile.career && surplus)
            plans << ",{\"goal_id\":\"auction:" << guid
                << "\",\"type\":\"list_surplus\",\"utility\":20,\"eligible\":true,\"duration_seconds\":3600}";
        if (profile.career && currentPolicy.advertising && IsCity(bot->GetZoneId()) && !outputs.empty())
            plans << ",{\"goal_id\":\"advertise:" << guid << ':' << outputs.front()
                << "\",\"type\":\"profession_advertisement\",\"utility\":4,\"eligible\":true,\"duration_seconds\":1800}";
        plans << "]}";
    }
    events << "]}"; plans << "]}";

    // Mirror the real character-owned auction table for Admin observability.
    // Keep this separate from the bot profile batch so population growth cannot
    // truncate listings or their authoritative reconciliation marker.
    std::ostringstream auctionEvents, activeAuctionIds;
    auctionEvents << "{\"events\":[";
    activeAuctionIds << '[';
    bool firstAuction = true, auctionSnapshotTruncated = false;
    uint32 emittedAuctions = 0;
    auto auctions = CharacterDatabase.PQuery(
        "SELECT a.id,a.houseid,a.itemowner,c.name,a.item_template,a.item_count,"
        "a.startbid,a.buyoutprice,a.time FROM auction a LEFT JOIN characters c "
        "ON c.guid=a.itemowner WHERE a.itemowner<>0 ORDER BY a.id LIMIT 2001");
    if (auctions)
    {
        do
        {
            if (emittedAuctions >= 2000)
            {
                auctionSnapshotTruncated = true;
                break;
            }
            Field* fields = auctions->Fetch();
            const uint32 auctionId = fields[0].GetUInt32();
            const uint32 sellerGuid = fields[2].GetUInt32();
            const uint32 itemEntry = fields[4].GetUInt32();
            ItemPrototype const* item = sObjectMgr.GetItemPrototype(itemEntry);
            if (!auctionId || !sellerGuid || !item)
                continue;
            if (!firstAuction) { auctionEvents << ','; activeAuctionIds << ','; }
            firstAuction = false;
            ++emittedAuctions;
            activeAuctionIds << auctionId;
            auctionEvents << "{\"event_id\":\"auction-" << auctionId << '-' << now
                << "\",\"type\":\"auction_snapshot\",\"auction_id\":" << auctionId
                << ",\"auction_house_id\":" << fields[1].GetUInt32()
                << ",\"seller_guid\":" << sellerGuid
                << ",\"seller_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(fields[3].GetString())
                << "\",\"seller_type\":\"" << (profiles.count(sellerGuid) ? "bot" : "human")
                << "\",\"item_entry\":" << itemEntry
                << ",\"item_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(item->Name1)
                << "\",\"quantity\":" << fields[5].GetUInt32()
                << ",\"bid_copper\":" << fields[6].GetUInt32()
                << ",\"buyout_copper\":" << fields[7].GetUInt32()
                << ",\"state\":\"active\",\"expires_at\":" << fields[8].GetUInt64() << '}';
        } while (auctions->NextRow());
    }
    activeAuctionIds << ']';
    if (!firstAuction) auctionEvents << ',';
    auctionEvents << "{\"event_id\":\"auction-snapshot-complete-" << now
        << "\",\"type\":\"auction_snapshot_complete\",\"truncated\":"
        << (auctionSnapshotTruncated ? "true" : "false") << ",\"active_auction_ids\":"
        << activeAuctionIds.str() << "}]}";

    if (!reportedBots)
        return false;
    std::string eventBody = events.str(), auctionBody = auctionEvents.str(), planBody = plans.str();
    pendingPlans = std::async(std::launch::async, [eventBody, auctionBody, planBody]()
    {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(eventBody, 9, sPlayerbotAIConfig.llmMaxSimultaniousGenerations,
            debug, true, "/v2/economy-events");
        PlayerbotLLMInterface::Generate(auctionBody, 9, sPlayerbotAIConfig.llmMaxSimultaniousGenerations,
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

bool PlayerbotOrganicEconomy::ExecuteGoal(Player* bot, Profile& profile,
    const Policy& currentPolicy, std::string& failureReason)
{
    if (!bot || !bot->GetPlayerbotAI())
    {
        failureReason = "bot_unavailable";
        return false;
    }
    PlayerbotAI* ai = bot->GetPlayerbotAI();
    const std::string& goalType = profile.currentGoalType;
    const std::string& goalId = profile.currentGoalId;
    if (goalType == "equipment_upgrade" && sPlayerbotBuildProfiles.GearingGoalsEnabled())
    {
        if (!sPlayerbotBuildProfiles.HasGearingDeficiency(bot)) return true;
        if (ai->DoSpecificAction("equip upgrades", Event("organic economy gearing", "", bot), true))
        {
            failureReason = "equipping_owned_upgrade";
            return false;
        }
        if (currentPolicy.buying &&
            ai->DoSpecificAction("rpg ah buy", Event("organic economy gearing", "", bot), true))
        {
            failureReason = "purchased_character_owned_upgrade";
            return false;
        }
        if (currentPolicy.buying)
        {
            std::ostringstream action;
            action << "request travel target::" << (uint32)TravelDestinationPurpose::AH;
            if (ai->DoSpecificAction(action.str(), Event("organic economy gearing", "", bot), true))
                failureReason = "traveling_to_character_auction_upgrade";
            else
                failureReason = "awaiting_organic_upgrade_source";
        }
        else
        {
            ai->ChangeStrategy("nc +travel", BotState::BOT_STATE_NON_COMBAT);
            failureReason = "awaiting_quest_vendor_craft_or_loot_upgrade";
        }
        return false;
    }
    if (goalType == "profession_skill_up" && currentPolicy.careers)
    {
        const uint32 epoch = uint32(time(nullptr));
        auto pending = craftAttempts.find(bot->GetGUIDLow());
        if (pending != craftAttempts.end() && pending->second.goal != goalId)
        { craftAttempts.erase(pending); pending = craftAttempts.end(); }
        if (pending != craftAttempts.end())
        {
            const CraftAttempt attempt = pending->second;
            if (bot->GetSkillValuePure(attempt.skill) > attempt.beforeSkill)
            {
                craftAttempts.erase(pending);
                return true; // Actual skill gain, never a queued command.
            }
            if (bot->IsNonMeleeSpellCasted(true) || epoch < attempt.started + 30)
            { failureReason = "awaiting_profession_result"; return false; }
            failureReason = bot->GetItemCount(attempt.output, false) > attempt.beforeOutput ?
                "crafted_without_skill_gain" : "craft_interrupted_or_rejected";
            craftAttempts.erase(pending);
            return false;
        }
        const std::string prefix = "profession:" + std::to_string(bot->GetGUIDLow()) + ":";
        const std::string suffix = goalId.compare(0, prefix.size(), prefix) == 0 ? goalId.substr(prefix.size()) : "";
        if (suffix.empty() || suffix.size() > 9 || suffix.find_first_not_of("0123456789") != std::string::npos)
        { failureReason = "invalid_profession_recipe"; return false; }
        const uint32 recipe = uint32(std::stoul(suffix));
        const auto* spell = sServerFacade.LookupSpellInfo(recipe);
        const uint32 skill = CraftSkill(bot, spell);
        if (!bot->HasSpell(recipe) || !skill)
        { failureReason = "recipe_unavailable_or_no_skill_gain"; return false; }
        if (!SafeCraftReagents(bot, spell))
        {
            if (!SafeCraftReagents(bot, spell, true, false))
            { failureReason = "missing_or_reserved_recipe_materials"; return false; }
            std::map<uint32, uint32> needed;
            for (uint32 i = 0; i < MAX_SPELL_REAGENTS; ++i)
                if (spell->Reagent[i] > 0 && spell->ReagentCount[i]) needed[spell->Reagent[i]] += spell->ReagentCount[i];
            ai::BankAction bank(ai);
            // At most one real stack transfer per reagent per sweep; a rejected
            // transfer never grants stock or reports a profession completion.
            for (const auto& reagent : needed)
            {
                if (bot->GetItemCount(reagent.first, false) >= reagent.second) continue;
                if (bot->GetItemCount(reagent.first, true) < reagent.second)
                {
                    ai::AhBidAction market(ai);
                    if (ai::AhBidAction::HasPendingMaterial(bot, reagent.first))
                    {
                        market.CollectRecipeMaterial(reagent.first, failureReason);
                        if (failureReason == "recipe_mailbox_out_of_range")
                        {
                            std::ostringstream route; route << "request travel target::" << (uint32)TravelDestinationPurpose::Mail;
                            ai->DoSpecificAction(route.str(), Event("can move around", "", bot), true);
                        }
                        return false;
                    }
                    if (!currentPolicy.buying) { failureReason = "recipe_purchasing_disabled"; return false; }
                    market.BuyRecipeMaterial(reagent.first, reagent.second, failureReason);
                    if (failureReason == "recipe_auctioneer_out_of_range" &&
                        ai::AhBidAction::HasMaterialOffer(bot, reagent.first, reagent.second - bot->GetItemCount(reagent.first,true)))
                    {
                        std::ostringstream route; route << "request travel target::" << (uint32)TravelDestinationPurpose::AH;
                        if (ai->DoSpecificAction(route.str(), Event("can move around", "", bot), true))
                            failureReason = "traveling_to_recipe_auction";
                    }
                    return false; // A paid order is not inventory or a completed craft.
                }
                bank.WithdrawForRecipe(reagent.first, reagent.second, failureReason);
                if (failureReason == "recipe_banker_out_of_range")
                {
                    std::ostringstream route;
                    route << "request travel target::" << (uint32)TravelDestinationPurpose::Bank;
                    if (ai->DoSpecificAction(route.str(), Event("can move around", "", bot), true))
                        failureReason = "traveling_to_owned_recipe_materials";
                    else failureReason = "recipe_bank_route_pending";
                    return false;
                }
                if (bot->GetItemCount(reagent.first, false) < reagent.second) return false;
            }
            if (!SafeCraftReagents(bot, spell)) return false;
        }
        if (!ai->CanCastSpell(recipe, bot, 0, true))
        { failureReason = "recipe_requires_safe_local_tools_or_space"; return false; }
        CraftAttempt attempt;
        attempt.goal = goalId; attempt.spell = recipe; attempt.skill = skill;
        attempt.beforeSkill = bot->GetSkillValuePure(skill);
        attempt.output = spell->EffectItemType[0]; attempt.beforeOutput = bot->GetItemCount(attempt.output, false);
        attempt.started = epoch;
        if (ai->CastSpell(recipe, bot)) craftAttempts[bot->GetGUIDLow()] = attempt;
        failureReason = craftAttempts.count(bot->GetGUIDLow()) ? "awaiting_profession_result" : "craft_rejected";
        return false;
    }
    if (goalType == "list_surplus" && currentPolicy.posting)
    {
        if (!HasAuctionSurplus(bot))
            return true;
        if (ai->DoSpecificAction("ah", Event("rpg action", "vendor", bot), true))
            return true;
        std::ostringstream action;
        action << "request travel target::" << (uint32)TravelDestinationPurpose::AH;
        if (ai->DoSpecificAction(action.str(), Event("organic economy auction", "", bot), true))
            failureReason = "traveling_to_auctioneer";
        else
            failureReason = "auctioneer_route_pending";
        return false;
    }
    if (goalType == "storage_pressure" && currentPolicy.careers)
    {
        LivingWowInventoryPressureSummary pressure = sPlayerbotInventoryPressure.Analyze(bot);
        if (pressure.bagUsage < 85 ||
            (!pressure.vendorStacks && !pressure.bankStacks && !pressure.craftStacks && !pressure.auctionStacks))
            return true;
        if (pressure.vendorStacks)
        {
            if (ai->DoSpecificAction("sell", Event("rpg action", "living-wow-safe-vendor", bot), true))
                return false;
            if (ai->DoSpecificAction("request progression vendor travel target",
                    Event("organic economy storage", "", bot), true))
                failureReason = "traveling_to_vendor";
            else
                failureReason = "vendor_route_pending";
            return false;
        }
        if (pressure.craftStacks &&
            ai->DoSpecificAction("craft random item", Event("organic economy storage", "", bot), true))
            return false;
        if (pressure.bankStacks && pressure.bankUsage < 95)
        {
            if (ai->DoSpecificAction("bank", Event("rpg action", "living-wow-safe-storage", bot), true))
                return false;
            std::ostringstream action;
            action << "request travel target::" << (uint32)TravelDestinationPurpose::Bank;
            if (ai->DoSpecificAction(action.str(), Event("organic economy storage", "", bot), true))
                failureReason = "traveling_to_bank";
            else
                failureReason = "bank_route_pending";
            return false;
        }
        if (pressure.auctionStacks && currentPolicy.posting)
        {
            if (ai->DoSpecificAction("ah", Event("rpg action", "vendor", bot), true))
                return false;
            std::ostringstream action;
            action << "request travel target::" << (uint32)TravelDestinationPurpose::AH;
            if (ai->DoSpecificAction(action.str(), Event("organic economy storage", "", bot), true))
                failureReason = "traveling_to_auctioneer";
            else
                failureReason = "auctioneer_route_pending";
            return false;
        }
        failureReason = "protected_inventory_only";
        return false;
    }
    if (goalType == "profession_advertisement" && currentPolicy.advertising)
    {
        size_t split = goalId.rfind(':');
        uint32 itemEntry = split == std::string::npos ? 0 : uint32(std::stoul(goalId.substr(split + 1)));
        if (Advertise(bot, itemEntry, currentPolicy))
            return true;
        failureReason = "advertisement_cooldown_or_location";
        return false;
    }
    if (goalType == "maintain_supplies")
    {
        // Existing Playerbots maintenance values own exact purchases. Keeping
        // the travel strategy active lets those validated needs select a real
        // vendor without inventing stock or granting supplies here.
        ai->ChangeStrategy("nc +travel", BotState::BOT_STATE_NON_COMBAT);
        return true;
    }
    failureReason = "unsupported_goal_type";
    return false;
}

void PlayerbotOrganicEconomy::ProcessActiveGoals(const Policy& currentPolicy,
    std::chrono::steady_clock::time_point now)
{
    if (currentPolicy.mode != "active" || profiles.empty())
        return;
    std::vector<uint32> guids;
    guids.reserve(profiles.size());
    std::set<uint32> verifying;
    for (const auto& entry : profiles)
    {
        if (entry.second.currentGoalState != "active" || entry.second.currentGoalId.empty()) continue;
        auto retry = retryCooldowns.find(entry.first);
        if (retry != retryCooldowns.end() && now < retry->second) continue;
        guids.push_back(entry.first);
        auto attempt = craftAttempts.find(entry.first);
        if (entry.second.currentGoalType == "profession_skill_up" && attempt != craftAttempts.end() &&
            attempt->second.goal == entry.second.currentGoalId) verifying.insert(entry.first);
    }
    const auto work = EconomyWorkOrder(guids, verifying, executionCursor);
    for (uint32 guid : work)
    {
        Profile& profile = profiles[guid];
        if (profile.currentGoalState != "active" || profile.currentGoalId.empty()) continue;
        if (retryCooldowns[guid].time_since_epoch().count() && now < retryCooldowns[guid]) continue;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        // Result inspection doesn't move, respec, buy or cast. A human joining
        // after the cast must not prevent us observing its real outcome.
        if (!bot || !bot->IsInWorld() || (!verifying.count(guid) && !SafeForEconomy(bot)))
        { retryCooldowns[guid] = now + std::chrono::seconds(30); continue; }
        std::string failureReason;
        bool completed = ExecuteGoal(bot, profile, currentPolicy, failureReason);
        retryCooldowns[guid] = now + std::chrono::seconds(completed ? 600 : 20);
        if (!completed)
        {
            if (lastBlockers[guid] != failureReason)
            {
                lastBlockers[guid] = failureReason;
                CharacterDatabase.PExecute("UPDATE organic_economy_goal SET failure_reason='%s' WHERE character_guid=%u AND capability_ref='%s' AND state='active'",
                    failureReason.c_str(), guid, profile.currentGoalId.c_str());
            }
            continue;
        }
        lastBlockers.erase(guid);
        actionCooldowns[guid] = now;
        CharacterDatabase.PExecute(
            "UPDATE organic_economy_goal SET state='completed',failure_reason='' WHERE character_guid='%u' AND capability_ref='%s' AND state='active'",
            guid, profile.currentGoalId.c_str());
        profile.currentGoalState = "completed";
    }
    if (!guids.empty()) executionCursor = (executionCursor + work.size()) % guids.size();
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
        auto attempt = craftAttempts.find(guid);
        auto active = profiles.find(guid);
        if (currentPolicy.mode == "active" && attempt != craftAttempts.end() && active != profiles.end() &&
            active->second.currentGoalState == "active" &&
            PreserveCraftResult(attempt->second.goal, active->second.currentGoalId, attempt->second.started, uint32(time(nullptr))))
            continue; // Inspect the in-flight result before replacing its goal.
        CharacterDatabase.PExecute(
            "UPDATE organic_economy_goal SET state='expired' WHERE character_guid='%u' AND state IN ('candidate','proposed','active')", guid);
        CharacterDatabase.PExecute(
            "INSERT INTO organic_economy_goal (character_guid,goal_type,capability_ref,state,utility,source,authoritative_payload,expires_at) "
            "VALUES ('%u','%s','%s','%s',0,'%s','{}',DATE_ADD(NOW(),INTERVAL 1 HOUR))",
            guid, goalType.c_str(), goalId.c_str(), currentPolicy.mode == "active" ? "active" : "proposed", source.c_str());
        Profile& profile = profiles[guid];
        profile.currentGoalId = goalId;
        profile.currentGoalType = goalType;
        profile.currentGoalState = currentPolicy.mode == "active" ? "active" : "proposed";
        retryCooldowns.erase(guid);
        lastBlockers.erase(guid);
        craftAttempts.erase(guid);
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
    if (!nextExecutionSweep.time_since_epoch().count() || now >= nextExecutionSweep)
    {
        ProcessActiveGoals(policy, now);
        nextExecutionSweep = now + std::chrono::seconds(5);
    }
    if (policy.mode == "off" || pendingPlans.valid() || (nextSubmit.time_since_epoch().count() && now < nextSubmit))
        return;
    // Random bots populate after the world update loop begins. An empty first
    // sample should retry quickly instead of hiding Observe telemetry for the
    // full planner cadence.
    bool submitted = Submit(policy);
    nextSubmit = now + std::chrono::seconds(submitted ? policy.cadenceSeconds : 30);
}
