#include "botpch.h"
#include "PlayerbotNpcInspector.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotLLMInterface.h"
#include "PlayerbotRendezvousManager.h"
#include "PlayerbotTraining.h"
#include "RandomPlayerbotMgr.h"
#include "TravelMgr.h"
#include "Entities/Bag.h"
#include "Chat/Chat.h"
#include <boost/property_tree/json_parser.hpp>
#include <chrono>
#include <future>
#include <sstream>
#include <set>

namespace
{
    using NpcInspectionClock = std::chrono::steady_clock;
    constexpr size_t kMaximumBody = 120000;
    struct Pending
    {
        ObjectGuid viewer;
        uint32 request;
        std::string body;
        std::future<std::string> social;
    };
    std::vector<Pending> pending;
    std::map<ObjectGuid, NpcInspectionClock::time_point> lastRequest;

    std::string Escape(const std::string& value)
    {
        std::string result;
        for (unsigned char c : value)
        {
            if (c == '%') result += "%25";
            else if (c == '\t') result += "%09";
            else if (c == '\n') result += "%0A";
            else if (c == '\r') result += "%0D";
            else if (c >= 32) result += char(c);
        }
        return result;
    }
    void Row(std::string& body, const std::string& section, const std::string& label,
        const std::string& value, const std::string& link = "", uint32 id = 0)
    {
        std::string row = "R\t" + section + '\t' + Escape(label) + '\t' + Escape(value) + '\t' + link + '\t' + std::to_string(id) + '\n';
        if (body.size() + row.size() < kMaximumBody - 300) body += row;
        else if (body.find("R\toverview\tDisplay limit\t") == std::string::npos)
            body += "R\toverview\tDisplay limit\tThis profile exceeds the display limit; some records are omitted.\t\t0\n";
    }
    void Send(Player* viewer, uint32 request, const std::string& body)
    {
        if (!viewer || !viewer->IsInWorld() || !viewer->isRealPlayer() || !viewer->GetSession()) return;
        const size_t size = 200;
        const size_t parts = std::max<size_t>(1, (body.size() + size - 1) / size);
        for (size_t part = 0; part < parts; ++part)
        {
            std::string payload = "LWOWN1\tD\t" + std::to_string(request) + '\t' +
                std::to_string(part + 1) + '\t' + std::to_string(parts) + '\t' + body.substr(part * size, size);
            WorldPacket packet;
            ChatHandler::BuildChatPacket(packet, CHAT_MSG_WHISPER, payload.c_str(), LANG_ADDON,
                CHAT_TAG_NONE, viewer->GetObjectGuid(), viewer->GetName());
            viewer->GetSession()->SendPacket(packet);
        }
        sLog.outString("Living NPC event=snapshot_sent player=%u request=%u bytes=%u parts=%u",
            viewer->GetGUIDLow(), request, uint32(body.size()), uint32(parts));
    }
    void Error(Player* viewer, uint32 request, const std::string& message)
    {
        Send(viewer, request, "E\t" + Escape(message) + '\n');
    }
    std::string Money(uint32 copper)
    {
        return std::to_string(copper / 10000) + "g " + std::to_string(copper / 100 % 100) + "s " + std::to_string(copper % 100) + "c";
    }
    void ItemRow(std::string& body, uint32 entry, uint32 count, const std::string& location)
    {
        const ItemPrototype* item = sObjectMgr.GetItemPrototype(entry);
        if (item) Row(body, "inventory", item->Name1, std::to_string(count) + " x | " + location, "item", entry);
    }
    void SpellRow(std::string& body, const std::string& section, uint32 id, const std::string& suffix)
    {
        const SpellEntry* spell = sSpellTemplate.LookupEntry<SpellEntry>(id);
        if (!spell) return;
        std::string detail = spell->Rank[0] ? spell->Rank[0] : "";
        if (!suffix.empty()) detail += (detail.empty() ? "" : " | ") + suffix;
        Row(body, section, spell->SpellName[0], detail, "spell", id);
    }
    void Training(std::string& body, Player* bot)
    {
        AiObjectContext* context = bot->GetPlayerbotAI()->GetAiObjectContext();
        context->ClearValues("trainable spells");
        context->ClearValues("available trainers");
        const std::string type = std::to_string(TRAINER_TYPE_CLASS);
        const auto spells = context->GetValue<std::vector<TrainerSpell const*>>("trainable spells", type)->Get();
        std::set<uint32> offered;
        for (const TrainerSpell* spell : spells)
            if (spell && LivingWowCanTrainSpell(bot, spell))
                for (uint32 learned : spell->learnedSpell) offered.insert(learned);
        Row(body, "training", "Class training", offered.empty() ? "Up to date with currently eligible trainer spells." :
            std::to_string(offered.size()) + " spells or ranks available to learn.");
        Row(body, "training", "Trainer fees", "Free for Living bots. Normal learning requirements apply.");

        std::vector<int32> entries = context->GetValue<std::vector<int32>>("available trainers", type)->Get();
        float nearest = std::numeric_limits<float>::max();
        std::string trainerName;
        const float radius = float(std::max<uint32>(100, sPlayerbotAIConfig.chatDirectorPartyLocalServiceRadiusYards));
        if (!offered.empty() && !entries.empty())
        {
            PlayerTravelInfo info(bot);
            WorldPosition center(bot);
            for (TravelDestination* destination : sTravelMgr.GetDestinations(info,
                (uint32)TravelDestinationPurpose::Trainer, entries, true, radius, false))
            {
                if (!destination || !LivingWowHasClassTraining(bot, destination->GetEntry()) ||
                    GuidPosition(HIGHGUID_UNIT, destination->GetEntry()).IsHostileTo(bot)) continue;
                std::list<uint8> chances = {100};
                WorldPosition* point = destination->GetNextPoint(center, chances, true);
                if (!point || point->getMapId() != bot->GetMapId()) continue;
                float distance = center.distance(*point);
                if (distance <= radius && distance < nearest)
                {
                    nearest = distance;
                    const CreatureInfo* trainer = sObjectMgr.GetCreatureTemplate(destination->GetEntry());
                    trainerName = trainer ? trainer->Name : "Class trainer";
                }
            }
            Row(body, "training", "Town errand", trainerName.empty() ?
                "Needs training; no suitable trainer within " + std::to_string(uint32(radius)) + " yards." :
                trainerName + " is about " + std::to_string(uint32(nearest)) + " yards away. Training has first priority during town errands.");
        }
        for (uint32 id : offered) SpellRow(body, "training", id, "Available now");
    }
    std::string Snapshot(uint32 guid, const std::string& name, uint32 level, uint32 playerClass)
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        const bool live = bot && bot->IsInWorld() && bot->GetPlayerbotAI() && !bot->isRealPlayer();
        if (live) { level = bot->GetLevel(); playerClass = bot->getClass(); }
        std::string body = "H\t" + std::to_string(guid) + '\t' + Escape(name) + '\t' +
            std::to_string(level) + '\t' + std::to_string(playerClass) + '\t' + (live ? "1" : "0") + '\n';
        Row(body, "overview", "Data source", live ? "Live realm snapshot" : "Offline bot: last saved game data");
        Row(body, "overview", "Captured", std::to_string(time(nullptr)));
        if (auto build = CharacterDatabase.PQuery("SELECT main_specialization,off_specialization,active_specialization,"
            "gear_profile,gear_ambition,performance_drive,role_flexibility,dungeon_interest,raid_aspiration "
            "FROM bot_build_profile WHERE character_guid='%u'", guid))
        {
            const char* labels[] = {"Main specialization", "Off specialization", "Active specialization", "Gear preference",
                "Gear ambition", "Performance drive", "Role flexibility", "Dungeon interest", "Raid aspiration"};
            for (uint32 i = 0; i < 9; ++i) Row(body, i < 3 ? "overview" : "personality", labels[i], (*build)[i].GetCppString());
        }
        if (live)
        {
            Row(body, "overview", "Money", Money(bot->GetMoney()));
            Row(body, "overview", "Area", WorldPosition(bot).getAreaName());
            Row(body, "overview", "Party activity", PlayerbotRendezvousManager::PartyActivityOwnerName(
                sPlayerbotRendezvousManager.GetPartyActivityOwner(guid)));
            Row(body, "overview", "Activity progress", PlayerbotRendezvousManager::PartyActivityPhaseName(
                sPlayerbotRendezvousManager.GetPartyActivityPhase(guid)));
            for (uint8 slot = 0; slot < BANK_SLOT_BAG_END; ++slot)
            {
                Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
                if (!item) continue;
                const std::string location = slot < EQUIPMENT_SLOT_END ? "Equipped" : slot >= BANK_SLOT_ITEM_START ? "Bank" : "Bags";
                ItemRow(body, item->GetEntry(), item->GetCount(), location);
                if (item->IsBag())
                {
                    Bag* bag = static_cast<Bag*>(item);
                    for (uint32 n = 0; n < bag->GetBagSize(); ++n)
                        if (Item* content = bag->GetItemByPos(n)) ItemRow(body, content->GetEntry(), content->GetCount(), location);
                }
            }
            for (uint8 slot = KEYRING_SLOT_START; slot < KEYRING_SLOT_END; ++slot)
                if (Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot)) ItemRow(body, item->GetEntry(), item->GetCount(), "Keyring");
            for (uint32 skill = 1; skill < sSkillLineStore.GetNumRows(); ++skill)
                if (const SkillLineEntry* entry = sSkillLineStore.LookupEntry(skill))
                    if (uint32 value = bot->GetSkillValue(skill))
                        Row(body, "skills", entry->name[0], std::to_string(value) + " / " + std::to_string(bot->GetSkillMax(skill)));
            for (const auto& spell : bot->GetSpellMap())
                if (spell.second.state != PLAYERSPELL_REMOVED && !spell.second.disabled && spell.second.active)
                    SpellRow(body, "skills", spell.first, "Known spell");
            Training(body, bot);
        }
        else
        {
            if (auto money = CharacterDatabase.PQuery("SELECT money FROM characters WHERE guid='%u'", guid))
                Row(body, "overview", "Saved money", Money((*money)[0].GetUInt32()));
            if (auto items = CharacterDatabase.PQuery("SELECT i.item_template,x.count FROM character_inventory i "
                "JOIN item_instance x ON x.guid=i.item WHERE i.guid='%u' ORDER BY i.bag,i.slot LIMIT 400", guid))
                do { ItemRow(body, (*items)[0].GetUInt32(), (*items)[1].GetUInt32(), "Saved inventory"); } while (items->NextRow());
            if (auto skills = CharacterDatabase.PQuery("SELECT skill,value,max FROM character_skills WHERE guid='%u'", guid))
                do {
                    if (const SkillLineEntry* skill = sSkillLineStore.LookupEntry((*skills)[0].GetUInt32()))
                        Row(body, "skills", skill->name[0], (*skills)[1].GetCppString() + " / " + (*skills)[2].GetCppString());
                } while (skills->NextRow());
            if (auto spells = CharacterDatabase.PQuery("SELECT spell FROM character_spell WHERE guid='%u' AND active=1 AND disabled=0", guid))
                do { SpellRow(body, "skills", (*spells)[0].GetUInt32(), "Saved spell"); } while (spells->NextRow());
            Row(body, "training", "Training eligibility", "Available when this bot is online; saved spells are listed under Skills.");
        }
        return body;
    }
}

bool PlayerbotNpcInspector::Handle(Player* viewer, const std::string& message)
{
    if (message.find("LWOWN1\t") != 0) return false;
    if (!viewer || !viewer->isRealPlayer() || message.size() > 100) return true;
    std::istringstream input(message);
    std::string prefix, action, requestText, argument;
    std::getline(input, prefix, '\t'); std::getline(input, action, '\t');
    std::getline(input, requestText, '\t'); std::getline(input, argument, '\t');
    if (requestText.empty() || requestText.size() > 9 || requestText.find_first_not_of("0123456789") != std::string::npos) return true;
    uint32 request = uint32(std::strtoul(requestText.c_str(), nullptr, 10));
    auto now = NpcInspectionClock::now();
    auto previous = lastRequest.find(viewer->GetObjectGuid());
    if (previous != lastRequest.end() && now - previous->second < std::chrono::seconds(1))
    { Error(viewer, request, "Please wait a moment before refreshing."); return true; }
    lastRequest[viewer->GetObjectGuid()] = now;
    if (action == "SEARCH")
    {
        if (argument.size() < 2 || argument.size() > 32 ||
            !std::all_of(argument.begin(), argument.end(), [](unsigned char c) { return std::isalpha(c) || c >= 128 || c == '-'; }))
        { Error(viewer, request, "Enter at least two letters of a Living bot's name."); return true; }
        CharacterDatabase.escape_string(argument);
        std::string body;
        uint32 matches = 0;
        if (auto results = CharacterDatabase.PQuery("SELECT guid,name,level,class,online FROM characters WHERE name LIKE '%s%%' ORDER BY name LIMIT 50", argument.c_str()))
            do {
                uint32 guid = (*results)[0].GetUInt32();
                if (!sRandomPlayerbotMgr.IsRandomBot(guid)) continue;
                Player* online = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, guid));
                if (online && online->isRealPlayer()) continue;
                body += "S\t" + std::to_string(guid) + '\t' + Escape((*results)[1].GetCppString()) + '\t' +
                    (*results)[2].GetCppString() + '\t' + (*results)[3].GetCppString() + '\t' + (*results)[4].GetCppString() + '\n';
                ++matches;
            } while (results->NextRow());
        if (!matches) Error(viewer, request, "No Living bots match that name.");
        else Send(viewer, request, body);
        return true;
    }
    if (action != "GET" || argument.empty() || argument.size() > 10 ||
        argument.find_first_not_of("0123456789") != std::string::npos)
    { Error(viewer, request, "Invalid inspection request."); return true; }
    uint64 parsedGuid = std::strtoull(argument.c_str(), nullptr, 10);
    if (!parsedGuid || parsedGuid > 0xFFFFFFFF || !sRandomPlayerbotMgr.IsRandomBot(uint32(parsedGuid)))
    { Error(viewer, request, "Living NPC inspects Living bots. Select a bot or search by name."); return true; }
    if (pending.size() >= 16)
    { Error(viewer, request, "Inspection is busy. Please try again shortly."); return true; }
    uint32 guid = uint32(parsedGuid);
    Player* online = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, guid));
    if (online && online->isRealPlayer())
    { Error(viewer, request, "Living NPC inspects bots, not human players."); return true; }
    auto record = CharacterDatabase.PQuery("SELECT name,level,class FROM characters WHERE guid='%u'", guid);
    if (!record) { Error(viewer, request, "Bot not found."); return true; }
    Pending work;
    work.viewer = viewer->GetObjectGuid(); work.request = request;
    work.body = Snapshot(guid, (*record)[0].GetCppString(), (*record)[1].GetUInt32(), (*record)[2].GetUInt32());
    work.social = std::async(std::launch::async, [guid]() {
        std::vector<std::string> debug;
        return PlayerbotLLMInterface::Generate("{\"bot_guid\":" + std::to_string(guid) + '}',
            5, 64, debug, true, "/v2/npc-inspection");
    });
    pending.push_back(std::move(work));
    return true;
}

void PlayerbotNpcInspector::Update()
{
    for (auto it = lastRequest.begin(); it != lastRequest.end();)
        if (NpcInspectionClock::now() - it->second > std::chrono::minutes(5)) it = lastRequest.erase(it); else ++it;
    for (auto it = pending.begin(); it != pending.end();)
    {
        if (it->social.wait_for(std::chrono::seconds(0)) != std::future_status::ready) { ++it; continue; }
        bool received = false;
        try
        {
            std::string response = it->social.get();
            boost::property_tree::ptree data;
            std::istringstream stream(response); boost::property_tree::read_json(stream, data);
            for (const auto& row : data.get_child("rows"))
            {
                std::string section = row.second.get<std::string>("section", "");
                if (section != "personality" && section != "memories") continue;
                Row(it->body, section, row.second.get<std::string>("label", ""), row.second.get<std::string>("value", ""));
            }
            received = true;
        }
        catch (...) { }
        if (!received)
        {
            Row(it->body, "personality", "Stored traits", "Temporarily unavailable. Refresh to try again.");
            Row(it->body, "memories", "Stored memories", "Temporarily unavailable. Refresh to try again.");
        }
        Send(sObjectAccessor.FindPlayer(it->viewer), it->request, it->body);
        it = pending.erase(it);
    }
}
