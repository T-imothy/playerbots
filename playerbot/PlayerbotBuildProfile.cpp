#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotBuildProfile.h"
#include "playerbot/BuildWorldSafety.h"
#include "playerbot/PlayerbotBankCapacity.h"
#include "playerbot/AiFactory.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/RandomItemMgr.h"
#include "playerbot/RandomPlayerbotMgr.h"
#include "playerbot/strategy/actions/ChangeTalentsAction.h"
#include "playerbot/strategy/actions/EquipAction.h"

#include "Entities/Player.h"
#include "Groups/Group.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <limits>
#include <sstream>

using namespace ai;

namespace
{
    std::string ReadPolicy(bool& persistentProfiles, bool& temporaryPartyBuilds, bool& offspecScoring,
        bool& sharedItemBonuses, bool& armorPreference, bool& offspecLoot, bool& gearingGoals,
        uint8& sharedMaximum, uint8& physicalPenalty, uint8& casterPenalty,
        uint8& preferredReplacement, uint8& minimumFree, uint8& maximumBagUse)
    {
        const char* configured = std::getenv("LIVING_WOW_BOT_BUILDS_CONFIG");
        std::ifstream input(configured && *configured ? configured : "/srv/living-wow/config/bot-builds.json");
        if (!input.good()) return "observe";
        std::stringstream buffer; buffer << input.rdbuf();
        const std::string json = buffer.str();
        const std::pair<const char*, bool*> flags[] = {
            {"persistentProfiles", &persistentProfiles}, {"temporaryPartyBuilds", &temporaryPartyBuilds},
            {"offspecScoring", &offspecScoring}, {"sharedItemBonuses", &sharedItemBonuses},
            {"armorPreference", &armorPreference}, {"offspecLoot", &offspecLoot},
            {"gearingGoals", &gearingGoals}};
        for (const auto& flag : flags)
        {
            const std::string needle = std::string("\"") + flag.first + "\"";
            size_t at = json.find(needle);
            if (at == std::string::npos || (at = json.find(':', at)) == std::string::npos) continue;
            std::string tail = json.substr(at + 1, 8);
            if (tail.find("true") != std::string::npos) *flag.second = true;
            else if (tail.find("false") != std::string::npos) *flag.second = false;
        }
        const std::pair<const char*, uint8*> numbers[] = {
            {"sharedUseBonusMaximumPercent", &sharedMaximum},
            {"physicalLowerArmorPenaltyPercent", &physicalPenalty},
            {"casterLowerArmorPenaltyPercent", &casterPenalty},
            {"preferredArmorReplacementPercent", &preferredReplacement},
            {"minimumFreeBagSlots", &minimumFree},
            {"maximumOffspecBagUsagePercent", &maximumBagUse}};
        for (const auto& number : numbers)
        {
            const std::string needle = std::string("\"") + number.first + "\"";
            size_t at = json.find(needle);
            if (at == std::string::npos || (at = json.find(':', at)) == std::string::npos) continue;
            while (++at < json.size() && !std::isdigit((unsigned char)json[at])) {}
            if (at < json.size()) *number.second = (uint8)std::min<unsigned long>(100, std::strtoul(json.c_str() + at, NULL, 10));
        }
        size_t p = json.find("\"mode\"");
        if (p == std::string::npos || (p = json.find(':', p)) == std::string::npos ||
            (p = json.find('"', p)) == std::string::npos) return "observe";
        size_t e = json.find('"', p + 1);
        return e == std::string::npos ? "observe" : json.substr(p + 1, e - p - 1);
    }

    uint32 PathRole(uint8 cls, uint32 pathId)
    {
        return (uint32)ChangeTalentsAction::GetPathRole(cls, pathId);
    }

    std::string Lower(std::string value)
    {
        std::transform(value.begin(), value.end(), value.begin(), ::tolower);
        return value;
    }

    std::string JsonEscape(const std::string& value)
    {
        std::string result;
        for (char c : value)
        {
            if (c == '\\' || c == '"') result += '\\';
            if (c == '\n' || c == '\r' || c == '\t') result += ' ';
            else result += c;
        }
        return result;
    }

    const char* EquipmentSlotName(uint8 slot)
    {
        static const char* names[EQUIPMENT_SLOT_END] = {
            "head", "neck", "shoulders", "shirt", "chest", "waist", "legs", "feet", "wrists",
            "hands", "finger one", "finger two", "trinket one", "trinket two", "back", "main hand",
            "off hand", "ranged", "tabard"
        };
        return slot < EQUIPMENT_SLOT_END ? names[slot] : "unknown";
    }

    bool EmptySlotIsDeficient(Player* bot, uint8 slot)
    {
        if (!bot) return false;
        switch (slot)
        {
            case EQUIPMENT_SLOT_BODY: case EQUIPMENT_SLOT_TABARD: return false;
            case EQUIPMENT_SLOT_HEAD: return bot->GetLevel() >= 10;
            case EQUIPMENT_SLOT_NECK: case EQUIPMENT_SLOT_SHOULDERS: return bot->GetLevel() >= 15;
            case EQUIPMENT_SLOT_FINGER1: case EQUIPMENT_SLOT_FINGER2: return bot->GetLevel() >= 10;
            case EQUIPMENT_SLOT_TRINKET1: case EQUIPMENT_SLOT_TRINKET2: return bot->GetLevel() >= 30;
            case EQUIPMENT_SLOT_OFFHAND: case EQUIPMENT_SLOT_RANGED: return false;
            default: return true;
        }
    }
}

PlayerbotBuildProfileMgr& PlayerbotBuildProfileMgr::instance()
{
    static PlayerbotBuildProfileMgr singleton;
    return singleton;
}

PlayerbotBuildProfileMgr::PlayerbotBuildProfileMgr() {}

uint32 PlayerbotBuildProfileMgr::StableValue(uint32 guid, uint32 salt)
{
    uint64 value = uint64(guid) * 1103515245ULL + uint64(salt) * 2654435761ULL + 12345ULL;
    value ^= value >> 17; value *= 1099511628211ULL; value ^= value >> 23;
    return uint32(value & 0xffffffffULL);
}

std::string PlayerbotBuildProfileMgr::GearProfileName(uint32 bucket)
{
    if (bucket < 20) return "relaxed";
    if (bucket < 65) return "practical";
    if (bucket < 90) return "prepared";
    return "competitive";
}

std::string PlayerbotBuildProfileMgr::Escape(const std::string& value)
{
    std::string escaped = value;
    CharacterDatabase.escape_string(escaped);
    return escaped;
}

void PlayerbotBuildProfileMgr::EnsureSchema()
{
    if (schemaReady) return;
    CharacterDatabase.DirectPExecute(
        "CREATE TABLE IF NOT EXISTS bot_build_profile ("
        "character_guid INT UNSIGNED NOT NULL,main_path_id INT UNSIGNED NOT NULL DEFAULT 0,"
        "off_path_id INT UNSIGNED NOT NULL DEFAULT 0,active_path_id INT UNSIGNED NOT NULL DEFAULT 0,"
        "main_specialization VARCHAR(32) NOT NULL,off_specialization VARCHAR(32) NOT NULL,"
        "active_specialization VARCHAR(32) NOT NULL,active_reason VARCHAR(32) NOT NULL DEFAULT 'main',"
        "main_archetype VARCHAR(80) NOT NULL DEFAULT '',off_archetype VARCHAR(80) NOT NULL DEFAULT '',"
        "active_archetype VARCHAR(80) NOT NULL DEFAULT '',"
        "party_session_id INT UNSIGNED NOT NULL DEFAULT 0,gear_profile VARCHAR(16) NOT NULL DEFAULT 'practical',"
        "gear_ambition TINYINT UNSIGNED NOT NULL DEFAULT 50,performance_drive TINYINT UNSIGNED NOT NULL DEFAULT 50,"
        "role_flexibility TINYINT UNSIGNED NOT NULL DEFAULT 50,dungeon_interest TINYINT UNSIGNED NOT NULL DEFAULT 50,"
        "raid_aspiration TINYINT UNSIGNED NOT NULL DEFAULT 50,revision INT UNSIGNED NOT NULL DEFAULT 1,"
        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
        "PRIMARY KEY(character_guid),KEY ix_bot_build_profile_active(active_specialization,gear_profile)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    CharacterDatabase.DirectPExecute(
        "CREATE TABLE IF NOT EXISTS bot_build_equipment ("
        "character_guid INT UNSIGNED NOT NULL,build_slot ENUM('main','off') NOT NULL,equipment_slot TINYINT UNSIGNED NOT NULL,"
        "item_guid INT UNSIGNED NOT NULL DEFAULT 0,item_entry INT UNSIGNED NOT NULL DEFAULT 0,"
        "item_location ENUM('equipped','bags','bank') NOT NULL DEFAULT 'equipped',score INT UNSIGNED NOT NULL DEFAULT 0,"
        "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
        "PRIMARY KEY(character_guid,build_slot,equipment_slot),KEY ix_bot_build_equipment_item(item_guid)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    schemaReady = true;
}

uint32 PlayerbotBuildProfileMgr::ChooseMainPath(Player* bot) const
{
    if (!bot) return 0;
    uint32 stored = sRandomPlayerbotMgr.GetValue(bot->GetGUIDLow(), "specNo");
    if (stored)
        for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
            if ((uint32)path.id + 1 == stored) return path.id;
    int tree = AiFactory::GetPlayerSpecTab(bot);
    for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
        if (!path.talentSpec.empty() && path.talentSpec.back().highestTree() == tree &&
            Lower(path.name).find("pve") != std::string::npos) return path.id;
    const std::vector<TalentPath>& paths = sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath;
    return paths.empty() ? 0 : paths[StableValue(bot->GetGUIDLow(), 11) % paths.size()].id;
}

uint32 PlayerbotBuildProfileMgr::PairScore(Player* bot, uint32 mainPathId, uint32 candidatePathId,
    uint8 roleFlexibility) const
{
    if (!bot || mainPathId == candidatePathId) return 0;
    std::string mainName, candidateName;
    for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
    {
        if ((uint32)path.id == mainPathId) mainName = Lower(path.name);
        if ((uint32)path.id == candidatePathId) candidateName = Lower(path.name);
    }
    std::string mainSpec = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), mainPathId);
    std::string candidateSpec = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), candidatePathId);
    const bool feralPair = (mainName.find("feral cat") != std::string::npos && candidateName.find("feral tank") != std::string::npos) ||
        (mainName.find("feral tank") != std::string::npos && candidateName.find("feral cat") != std::string::npos);
    if (mainSpec == candidateSpec && !feralPair) return 0;
    uint32 overlap = feralPair ? 95 : 45;
    if ((mainSpec == "restoration" && candidateSpec == "balance") ||
        (mainSpec == "balance" && candidateSpec == "restoration") ||
        (mainSpec == "elemental" && candidateSpec == "restoration") ||
        (mainSpec == "restoration" && candidateSpec == "elemental") ||
        (mainSpec == "holy" && candidateSpec == "discipline") ||
        (mainSpec == "discipline" && candidateSpec == "holy") ||
        (mainSpec == "arms" && candidateSpec == "fury") ||
        (mainSpec == "fury" && candidateSpec == "arms")) overlap = 90;
    uint32 mainRole = PathRole(bot->getClass(), mainPathId);
    uint32 candidateRole = PathRole(bot->getClass(), candidatePathId);
    uint32 coverage = (mainRole & candidateRole) == 0 ? 100 : 35;
    uint32 affinity = (mainRole & candidateRole) == 0 ? roleFlexibility : 100 - roleFlexibility;
    return overlap * 60 + coverage * 25 + affinity * 15;
}

uint32 PlayerbotBuildProfileMgr::ChooseOffPath(Player* bot, uint32 mainPathId, uint8 roleFlexibility) const
{
    uint32 selected = mainPathId, best = 0;
    for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
    {
        uint32 score = PairScore(bot, mainPathId, path.id, roleFlexibility);
        score += StableValue(bot->GetGUIDLow(), path.id + 101) % 7;
        if (score > best) { best = score; selected = path.id; }
    }
    return selected;
}

uint32 PlayerbotBuildProfileMgr::PathForSpecialization(Player* bot, const std::string& specialization,
    uint32 avoidPath) const
{
    if (!bot) return std::numeric_limits<uint32>::max();
    uint32 fallback = std::numeric_limits<uint32>::max();
    for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
        if ((uint32)path.id != avoidPath && ChangeTalentsAction::GetPathSpecialization(bot->getClass(), path.id) == specialization)
        {
            if (fallback == std::numeric_limits<uint32>::max()) fallback = path.id;
            if (Lower(path.name).find("pve") != std::string::npos) return path.id;
        }
    return fallback;
}

bool PlayerbotBuildProfileMgr::IsPathUsableForRole(Player* bot, uint32 pathId, uint32 roleMask) const
{
    if (!bot) return false;
    const uint32 pathRole = PathRole(bot->getClass(), pathId);
    if (roleMask && !(pathRole & roleMask)) return false;
    if (bot->getClass() != CLASS_DRUID) return true;

    // In TBC the Feral tree contains two mechanically different builds whose
    // specialization label is identical.  A cat build without Cat Form and a
    // tank build without Bear Form are not executable builds, even if their
    // talents are otherwise valid.
    const std::string weight = Lower(ChangeTalentsAction::GetPathWeightName(bot->getClass(), pathId));
    const std::string name = Lower(ChangeTalentsAction::GetPathName(bot->getClass(), pathId));
    const bool catBuild = weight == "feraldps" || name.find("feral cat") != std::string::npos;
    const bool bearBuild = weight == "feraltank" || name.find("feral tank") != std::string::npos;
    if (catBuild) return bot->HasSpell(768);                    // Cat Form
    if (bearBuild) return bot->HasSpell(5487) || bot->HasSpell(9634); // Bear / Dire Bear Form
    return true;
}

uint32 PlayerbotBuildProfileMgr::BestPathForRole(Player* bot, uint32 roleMask)
{
    if (!bot) return std::numeric_limits<uint32>::max();
    const LivingBotBuildProfile& profile = Get(bot);
    const uint32 preferred[] = {profile.mainPathId, profile.offPathId};
    for (uint32 pathId : preferred)
        if (IsPathUsableForRole(bot, pathId, roleMask)) return pathId;

    // Prefer a PvE archetype for ordinary world and party play, then accept
    // another valid premade path if the configured catalog has no PvE label.
    for (uint8 pass = 0; pass < 2; ++pass)
        for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
        {
            const bool pve = Lower(path.name).find("pve") != std::string::npos;
            if ((pass == 0) != pve) continue;
            if (IsPathUsableForRole(bot, path.id, roleMask)) return path.id;
        }
    return std::numeric_limits<uint32>::max();
}

uint32 PlayerbotBuildProfileMgr::EffectiveMainPath(Player* bot, const LivingBotBuildProfile& profile) const
{
    if (!bot) return std::numeric_limits<uint32>::max();
    const uint32 preferredRole = PathRole(bot->getClass(), profile.mainPathId);
    if (IsPathUsableForRole(bot, profile.mainPathId, preferredRole)) return profile.mainPathId;

    for (uint8 pass = 0; pass < 2; ++pass)
        for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
        {
            const bool pve = Lower(path.name).find("pve") != std::string::npos;
            if ((pass == 0) != pve) continue;
            if (IsPathUsableForRole(bot, path.id, preferredRole)) return path.id;
        }

    // A preferred tank form may not have been learned yet.  In that case a
    // druid levels as ranged damage instead of pretending it can tank.
    if (bot->getClass() == CLASS_DRUID)
        for (uint8 pass = 0; pass < 2; ++pass)
            for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
            {
                const bool pve = Lower(path.name).find("pve") != std::string::npos;
                if ((pass == 0) != pve) continue;
                if (IsPathUsableForRole(bot, path.id, BOT_ROLE_DPS)) return path.id;
            }
    return profile.mainPathId;
}

LivingBotBuildProfile PlayerbotBuildProfileMgr::Create(Player* bot)
{
    LivingBotBuildProfile result;
    result.characterGuid = bot->GetGUIDLow();
    result.mainPathId = ChooseMainPath(bot);
    result.mainSpecialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), result.mainPathId);
    result.mainArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), result.mainPathId);
    const uint32 bucket = StableValue(result.characterGuid, 1) % 100;
    result.gearProfile = GearProfileName(bucket);
    result.gearAmbition = result.gearProfile == "relaxed" ? 10 + StableValue(result.characterGuid, 2) % 15 :
        result.gearProfile == "practical" ? 25 + StableValue(result.characterGuid, 2) % 35 :
        result.gearProfile == "prepared" ? 60 + StableValue(result.characterGuid, 2) % 25 :
        85 + StableValue(result.characterGuid, 2) % 16;
    result.performanceDrive = StableValue(result.characterGuid, 3) % 101;
    result.roleFlexibility = StableValue(result.characterGuid, 4) % 101;
    result.dungeonInterest = StableValue(result.characterGuid, 5) % 101;
    result.raidAspiration = StableValue(result.characterGuid, 6) % 101;
    result.offPathId = ChooseOffPath(bot, result.mainPathId, result.roleFlexibility);
    result.offSpecialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), result.offPathId);
    result.offArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), result.offPathId);
    result.activePathId = result.mainPathId;
    result.activeSpecialization = result.mainSpecialization;
    result.activeArchetype = result.mainArchetype;
    Save(result);
    return result;
}

void PlayerbotBuildProfileMgr::Save(const LivingBotBuildProfile& p)
{
    CharacterDatabase.PExecute(
        "INSERT INTO bot_build_profile(character_guid,main_path_id,off_path_id,active_path_id,main_specialization,"
        "off_specialization,active_specialization,active_reason,main_archetype,off_archetype,active_archetype,"
        "party_session_id,gear_profile,gear_ambition,"
        "performance_drive,role_flexibility,dungeon_interest,raid_aspiration,revision,created_at) "
        "VALUES(%u,%u,%u,%u,'%s','%s','%s','%s','%s','%s','%s',%u,'%s',%u,%u,%u,%u,%u,%u,NOW()) "
        "ON DUPLICATE KEY UPDATE main_path_id=VALUES(main_path_id),off_path_id=VALUES(off_path_id),"
        "active_path_id=VALUES(active_path_id),main_specialization=VALUES(main_specialization),"
        "off_specialization=VALUES(off_specialization),active_specialization=VALUES(active_specialization),"
        "active_reason=VALUES(active_reason),main_archetype=VALUES(main_archetype),off_archetype=VALUES(off_archetype),"
        "active_archetype=VALUES(active_archetype),party_session_id=VALUES(party_session_id),gear_profile=VALUES(gear_profile),"
        "gear_ambition=VALUES(gear_ambition),performance_drive=VALUES(performance_drive),"
        "role_flexibility=VALUES(role_flexibility),dungeon_interest=VALUES(dungeon_interest),"
        "raid_aspiration=VALUES(raid_aspiration),revision=VALUES(revision)",
        p.characterGuid, p.mainPathId, p.offPathId, p.activePathId, Escape(p.mainSpecialization).c_str(),
        Escape(p.offSpecialization).c_str(), Escape(p.activeSpecialization).c_str(), Escape(p.activeReason).c_str(),
        Escape(p.mainArchetype).c_str(), Escape(p.offArchetype).c_str(), Escape(p.activeArchetype).c_str(),
        p.partySessionId, Escape(p.gearProfile).c_str(), p.gearAmbition, p.performanceDrive, p.roleFlexibility,
        p.dungeonInterest, p.raidAspiration, p.revision);
}

const LivingBotBuildProfile& PlayerbotBuildProfileMgr::Get(Player* bot)
{
    static LivingBotBuildProfile empty;
    if (!bot) return empty;
    EnsureSchema();
    uint32 guid = bot->GetGUIDLow();
    std::map<uint32, LivingBotBuildProfile>::iterator cached = profiles.find(guid);
    if (cached != profiles.end()) return cached->second;
    std::unique_ptr<QueryResult> row = CharacterDatabase.PQuery(
        "SELECT main_path_id,off_path_id,active_path_id,main_specialization,off_specialization,active_specialization,"
        "active_reason,main_archetype,off_archetype,active_archetype,party_session_id,gear_profile,gear_ambition,"
        "performance_drive,role_flexibility,dungeon_interest,"
        "raid_aspiration,revision FROM bot_build_profile WHERE character_guid=%u", guid);
    LivingBotBuildProfile profile;
    if (!row) profile = Create(bot);
    else
    {
        Field* f = row->Fetch(); profile.characterGuid = guid; profile.mainPathId = f[0].GetUInt32();
        profile.offPathId = f[1].GetUInt32(); profile.activePathId = f[2].GetUInt32();
        profile.mainSpecialization = f[3].GetString(); profile.offSpecialization = f[4].GetString();
        profile.activeSpecialization = f[5].GetString(); profile.activeReason = f[6].GetString();
        profile.mainArchetype = f[7].GetString(); profile.offArchetype = f[8].GetString();
        profile.activeArchetype = f[9].GetString(); profile.partySessionId = f[10].GetUInt32();
        profile.gearProfile = f[11].GetString(); profile.gearAmbition = f[12].GetUInt8();
        profile.performanceDrive = f[13].GetUInt8(); profile.roleFlexibility = f[14].GetUInt8();
        profile.dungeonInterest = f[15].GetUInt8(); profile.raidAspiration = f[16].GetUInt8();
        profile.revision = f[17].GetUInt32();
    }
    profiles[guid] = profile;
    LoadEquipment(guid);
    return profiles[guid];
}

void PlayerbotBuildProfileMgr::LoadEquipment(uint32 characterGuid)
{
    savedEquipment[characterGuid].clear();
    savedEquipmentEntries[characterGuid].clear();
    std::unique_ptr<QueryResult> rows = CharacterDatabase.PQuery(
        "SELECT build_slot,equipment_slot,item_guid,item_entry FROM bot_build_equipment WHERE character_guid=%u", characterGuid);
    if (!rows) return;
    do
    {
        Field* f = rows->Fetch();
        savedEquipment[characterGuid][f[0].GetString()][f[1].GetUInt8()] = f[2].GetUInt32();
        savedEquipmentEntries[characterGuid][f[0].GetString()][f[1].GetUInt8()] = f[3].GetUInt32();
    } while (rows->NextRow());
}

void PlayerbotBuildProfileMgr::CaptureEquipment(Player* bot, const LivingBotBuildProfile& profile)
{
    if (!bot || mode == "off") return;
    const char* build = profile.activePathId == profile.offPathId ? "off" :
        profile.activePathId == profile.mainPathId ? "main" : NULL;
    // A form-aware leveling fallback is intentionally not a third permanent
    // equipment set. Do not let its temporary gear overwrite the saved main
    // set merely because it is currently active.
    if (!build) return;
    uint64 signature = 1469598103934665603ULL;
    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
    {
        Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
        signature ^= uint64(slot + 1) * 1099511628211ULL;
        signature ^= item ? item->GetGUIDLow() : 0;
        signature *= 1099511628211ULL;
    }
    if (equipmentSignatures[profile.characterGuid][build] == signature) return;
    equipmentSignatures[profile.characterGuid][build] = signature;
    savedEquipment[profile.characterGuid][build].clear();
    savedEquipmentEntries[profile.characterGuid][build].clear();
    CharacterDatabase.PExecute("DELETE FROM bot_build_equipment WHERE character_guid=%u AND build_slot='%s'",
        profile.characterGuid, build);
    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
        if (Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
        {
            savedEquipment[profile.characterGuid][build][slot] = item->GetGUIDLow();
            savedEquipmentEntries[profile.characterGuid][build][slot] = item->GetEntry();
            CharacterDatabase.PExecute(
                "REPLACE INTO bot_build_equipment(character_guid,build_slot,equipment_slot,item_guid,item_entry,item_location,score) "
                "VALUES(%u,'%s',%u,%u,%u,'equipped',%u)", profile.characterGuid, build, slot,
                item->GetGUIDLow(), item->GetEntry(), sRandomItemMgr.GetStatWeight(bot, item->GetEntry()));
        }
}

void PlayerbotBuildProfileMgr::EquipSavedSet(Player* bot, const char* buildSlot)
{
    if (!bot || !buildSlot || !bot->GetPlayerbotAI()) return;
    std::map<uint8, uint32>& set = savedEquipment[bot->GetGUIDLow()][buildSlot];
    for (std::map<uint8, uint32>::const_iterator i = set.begin(); i != set.end(); ++i)
    {
        Item* item = bot->GetItemByGuid(ObjectGuid(HIGHGUID_ITEM, i->second));
        if (!item) continue;
        const uint8 bag = item->GetBagSlot();
        const uint8 slot = item->GetSlot();
        const bool inBackpack = bag == INVENTORY_SLOT_BAG_0 && slot >= INVENTORY_SLOT_ITEM_START && slot < INVENTORY_SLOT_ITEM_END;
        const bool inEquippedBag = bag >= INVENTORY_SLOT_BAG_START && bag < INVENTORY_SLOT_BAG_END;
        if (inBackpack || inEquippedBag)
            EquipAction::EquipItem(bot->GetPlayerbotAI(), bot, item, true);
    }
}

void PlayerbotBuildProfileMgr::Update(Player* bot)
{
    if (!living_build_safety::HasWorld(bot) || !bot->GetPlayerbotAI()) return;
    time_t now = time(NULL);
    if (now - lastPolicyLoad >= 5)
    {
        mode = ReadPolicy(persistentProfiles, temporaryPartyBuilds, offspecScoring, sharedItemBonuses,
            armorPreference, offspecLoot, gearingGoals, sharedUseBonusMaximumPercent,
            physicalLowerArmorPenaltyPercent, casterLowerArmorPenaltyPercent,
            preferredArmorReplacementPercent, minimumFreeBagSlots, maximumOffspecBagUsagePercent);
        lastPolicyLoad = now;
    }
    if (mode == "off" || !persistentProfiles) return;
    Get(bot);
    if (nextAvailabilitySync[bot->GetGUIDLow()] <= now)
    {
        ReconcileAvailableBuild(bot);
        nextAvailabilitySync[bot->GetGUIDLow()] = now + 10;
    }
    const LivingBotBuildProfile& profile = Get(bot);
    if (nextSnapshot[bot->GetGUIDLow()] > now) return;
    CaptureEquipment(bot, profile);
    nextSnapshot[bot->GetGUIDLow()] = now + 60;
}

void PlayerbotBuildProfileMgr::ReconcileAvailableBuild(Player* bot)
{
    if (!IsActive() || !living_build_safety::CanReconcile(bot)) return;
    LivingBotBuildProfile profile = Get(bot);
    if (profile.partySessionId || (profile.activeReason != "main" && profile.activeReason != "ability_fallback"))
        return;

    const uint32 desiredPath = EffectiveMainPath(bot, profile);
    if (desiredPath == std::numeric_limits<uint32>::max()) return;
    const std::string desiredReason = desiredPath == profile.mainPathId ? "main" : "ability_fallback";
    if (profile.activePathId == desiredPath && profile.activeReason == desiredReason &&
        bot->GetFreeTalentPoints() == 0) return;

    CaptureEquipment(bot, profile);
    std::ostringstream details;
    if (!ChangeTalentsAction::ApplyPremadePath(bot, desiredPath, &details)) return;
    profile.activePathId = desiredPath;
    profile.activeSpecialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), desiredPath);
    profile.activeArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), desiredPath);
    profile.activeReason = desiredReason;
    ++profile.revision;
    profiles[profile.characterGuid] = profile;
    Save(profile);
    if (desiredPath == profile.mainPathId) EquipSavedSet(bot, "main");
    else if (desiredPath == profile.offPathId) EquipSavedSet(bot, "off");
    sLog.outString("Living WoW available build sync bot=%u name=%s preferred=%s active=%s reason=%s",
        bot->GetGUIDLow(), bot->GetName(), profile.mainSpecialization.c_str(),
        profile.activeSpecialization.c_str(), profile.activeReason.c_str());
}

bool PlayerbotBuildProfileMgr::ActivateTemporary(Player* bot, const std::string& specialization,
    uint32 partySessionId, const std::string& reason, std::string& outcome)
{
    LivingBotBuildProfile profile = Get(bot);
    // Prefer the main identity when two archetypes share one specialization
    // label (notably Feral cat and Feral tank). Role-driven callers use the
    // path-specific entry point below and therefore remain unambiguous.
    uint32 pathId = specialization == profile.mainSpecialization ? profile.mainPathId :
        specialization == profile.offSpecialization ? profile.offPathId : PathForSpecialization(bot, specialization);
    if (pathId == std::numeric_limits<uint32>::max())
    { outcome = "specialization_not_supported_by_class"; return false; }
    return ActivateTemporaryPath(bot, pathId, partySessionId, reason, outcome);
}

bool PlayerbotBuildProfileMgr::ActivateTemporaryPath(Player* bot, uint32 pathId,
    uint32 partySessionId, const std::string& reason, std::string& outcome)
{
    if (!IsActive()) { outcome = "build_profiles_observe_only"; return false; }
    if (!temporaryPartyBuilds) { outcome = "temporary_party_builds_disabled"; return false; }
    LivingBotBuildProfile profile = Get(bot);
    const std::string specialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), pathId);
    if (specialization.empty()) { outcome = "specialization_not_supported_by_class"; return false; }
    if (!IsPathUsableForRole(bot, pathId)) { outcome = "required_form_not_learned"; return false; }
    CaptureEquipment(bot, profile);
    std::ostringstream details;
    if (!ChangeTalentsAction::ApplyPremadePath(bot, pathId, &details))
    { outcome = "talent_assignment_incomplete"; return false; }
    profile.activePathId = pathId; profile.activeSpecialization = specialization;
    profile.activeArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), pathId);
    profile.activeReason = reason; profile.partySessionId = partySessionId; ++profile.revision;
    profiles[profile.characterGuid] = profile; Save(profile);
    if (pathId == profile.offPathId) EquipSavedSet(bot, "off");
    else if (pathId == profile.mainPathId) EquipSavedSet(bot, "main");
    outcome = "completed"; return true;
}

bool PlayerbotBuildProfileMgr::SetMain(Player* bot, const std::string& specialization, std::string& outcome)
{
    if (!IsActive()) { outcome = "build_profiles_observe_only"; return false; }
    LivingBotBuildProfile profile = Get(bot);
    CaptureEquipment(bot, profile);
    uint32 pathId = PathForSpecialization(bot, specialization);
    if (pathId == std::numeric_limits<uint32>::max())
    { outcome = "specialization_not_supported_by_class"; return false; }
    profile.mainPathId = pathId; profile.mainSpecialization = specialization;
    profile.mainArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), pathId);
    profile.offPathId = ChooseOffPath(bot, pathId, profile.roleFlexibility);
    profile.offSpecialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), profile.offPathId);
    profile.offArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), profile.offPathId);
    const uint32 effectivePath = EffectiveMainPath(bot, profile);
    profile.activePathId = effectivePath;
    profile.activeSpecialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), effectivePath);
    profile.activeReason = effectivePath == pathId ? "main" : "ability_fallback";
    profile.activeArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), effectivePath);
    profile.partySessionId = 0; ++profile.revision;
    std::ostringstream details;
    if (!ChangeTalentsAction::ApplyPremadePath(bot, effectivePath, &details))
    { outcome = "talent_assignment_incomplete"; return false; }
    profiles[profile.characterGuid] = profile; Save(profile);
    if (effectivePath == profile.mainPathId) EquipSavedSet(bot, "main");
    else if (effectivePath == profile.offPathId) EquipSavedSet(bot, "off");
    outcome = "completed"; return true;
}

bool PlayerbotBuildProfileMgr::SetOffspec(Player* bot, const std::string& specialization, std::string& outcome)
{
    if (!IsActive()) { outcome = "build_profiles_observe_only"; return false; }
    LivingBotBuildProfile profile = Get(bot);
    uint32 pathId = PathForSpecialization(bot, specialization, profile.mainPathId);
    if (pathId == std::numeric_limits<uint32>::max() || pathId == profile.mainPathId)
    { outcome = "offspec_must_use_a_distinct_build"; return false; }
    profile.offPathId = pathId; profile.offSpecialization = specialization;
    profile.offArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), pathId); ++profile.revision;
    profiles[profile.characterGuid] = profile; Save(profile); outcome = "completed"; return true;
}

bool PlayerbotBuildProfileMgr::ClearTemporary(Player* bot, uint32 partySessionId, std::string& outcome)
{
    if (!IsActive()) { outcome = "build_profiles_observe_only"; return false; }
    LivingBotBuildProfile profile = Get(bot);
    if (!profile.partySessionId) { outcome = "completed"; return true; }
    if (partySessionId && profile.partySessionId != partySessionId) { outcome = "stale_party_session"; return false; }
    const uint32 effectivePath = EffectiveMainPath(bot, profile);
    std::ostringstream details;
    if (!ChangeTalentsAction::ApplyPremadePath(bot, effectivePath, &details))
    { outcome = "talent_assignment_incomplete"; return false; }
    CaptureEquipment(bot, profile);
    profile.activePathId = effectivePath;
    profile.activeSpecialization = ChangeTalentsAction::GetPathSpecialization(bot->getClass(), effectivePath);
    profile.activeArchetype = ChangeTalentsAction::GetPathName(bot->getClass(), effectivePath);
    profile.activeReason = effectivePath == profile.mainPathId ? "main" : "ability_fallback";
    profile.partySessionId = 0; ++profile.revision;
    profiles[profile.characterGuid] = profile; Save(profile);
    if (effectivePath == profile.mainPathId) EquipSavedSet(bot, "main");
    else if (effectivePath == profile.offPathId) EquipSavedSet(bot, "off");
    outcome = "completed"; return true;
}

std::string PlayerbotBuildProfileMgr::GetMainSpecialization(Player* bot) { return Get(bot).mainSpecialization; }
std::string PlayerbotBuildProfileMgr::GetOffSpecialization(Player* bot) { return Get(bot).offSpecialization; }
std::string PlayerbotBuildProfileMgr::GetActiveSpecialization(Player* bot) { return Get(bot).activeSpecialization; }

std::string PlayerbotBuildProfileMgr::GetMainWeightName(Player* bot)
{ return ChangeTalentsAction::GetPathWeightName(bot->getClass(), Get(bot).mainPathId); }
std::string PlayerbotBuildProfileMgr::GetOffWeightName(Player* bot)
{ return ChangeTalentsAction::GetPathWeightName(bot->getClass(), Get(bot).offPathId); }
std::string PlayerbotBuildProfileMgr::GetActiveWeightName(Player* bot)
{ return ChangeTalentsAction::GetPathWeightName(bot->getClass(), Get(bot).activePathId); }

std::string PlayerbotBuildProfileMgr::BestSpecializationForRole(Player* bot, uint32 roleMask)
{
    const uint32 pathId = BestPathForRole(bot, roleMask);
    return pathId == std::numeric_limits<uint32>::max() ? "" :
        ChangeTalentsAction::GetPathSpecialization(bot->getClass(), pathId);
}

uint8 PlayerbotBuildProfileMgr::PreferredArmorSubclass(Player* bot)
{
    if (!bot) return ITEM_SUBCLASS_ARMOR_CLOTH;
    switch (bot->getClass())
    {
        case CLASS_WARRIOR: case CLASS_PALADIN: return bot->GetLevel() >= 40 ? ITEM_SUBCLASS_ARMOR_PLATE : ITEM_SUBCLASS_ARMOR_MAIL;
        case CLASS_HUNTER: case CLASS_SHAMAN: return bot->GetLevel() >= 40 ? ITEM_SUBCLASS_ARMOR_MAIL : ITEM_SUBCLASS_ARMOR_LEATHER;
        case CLASS_ROGUE: case CLASS_DRUID: return ITEM_SUBCLASS_ARMOR_LEATHER;
        default: return ITEM_SUBCLASS_ARMOR_CLOTH;
    }
}

bool PlayerbotBuildProfileMgr::IsPhysicalOrTankWeight(const std::string& value)
{
    static const char* names[] = {"arms","fury","prot","retrib","enhance","feraltank","feraldps",
        "assas","combat","subtle","beast","marks","surv"};
    for (const char* name : names) if (value == name) return true;
    return false;
}

LivingGearScores PlayerbotBuildProfileMgr::Evaluate(Player* bot, ItemPrototype const* proto)
{
    LivingGearScores score;
    if (!bot || !proto) return score;
    score.mainScore = sRandomItemMgr.GetStatWeightForName(bot->getClass(), proto->ItemId, GetMainWeightName(bot));
    score.offScore = sRandomItemMgr.GetStatWeightForName(bot->getClass(), proto->ItemId, GetOffWeightName(bot));
    score.activeScore = sRandomItemMgr.GetStatWeightForName(bot->getClass(), proto->ItemId, GetActiveWeightName(bot));
    score.sharedBonus = sharedItemBonuses ? std::min<uint32>(score.mainScore * sharedUseBonusMaximumPercent / 100,
        score.offScore * 25 / 100) : 0;
    score.sharedUpgrade = score.mainScore > 0 && score.offScore > 0;
    score.preferredArmor = true;
    if (armorPreference && proto->Class == ITEM_CLASS_ARMOR && proto->InventoryType != INVTYPE_CLOAK &&
        proto->SubClass > ITEM_SUBCLASS_ARMOR_MISC && proto->SubClass < PreferredArmorSubclass(bot))
    {
        score.preferredArmor = false;
        score.armorPenaltyPercent = IsPhysicalOrTankWeight(GetActiveWeightName(bot)) ?
            physicalLowerArmorPenaltyPercent : casterLowerArmorPenaltyPercent;
    }
    uint32 active = score.activeScore;
    if (score.armorPenaltyPercent) active = active * (100 - score.armorPenaltyPercent) / 100;
    score.effectiveScore = active + std::min<uint32>(active * sharedUseBonusMaximumPercent / 100, score.sharedBonus);
    return score;
}

uint8 PlayerbotBuildProfileMgr::OffspecUpgradeThreshold(Player* bot)
{
    const std::string profile = Get(bot).gearProfile;
    return profile == "relaxed" ? 25 : profile == "practical" ? 15 : profile == "prepared" ? 10 : 5;
}

uint8 PlayerbotBuildProfileMgr::OffspecCarryLimit(Player* bot)
{
    const std::string profile = Get(bot).gearProfile;
    return profile == "relaxed" ? 2 : profile == "practical" ? 3 : profile == "prepared" ? 4 : 6;
}

bool PlayerbotBuildProfileMgr::IsOffspecUpgrade(Player* bot, ItemPrototype const* proto,
    ItemPrototype const* comparison)
{
    if (!OffspecScoringEnabled() || !bot || !proto || Get(bot).offPathId == Get(bot).mainPathId) return false;
    uint32 candidate = sRandomItemMgr.GetStatWeightForName(bot->getClass(), proto->ItemId, GetOffWeightName(bot));
    if (!candidate) return false;
    if (!comparison)
    {
        uint16 destination = 0;
        if (RandomPlayerbotMgr::CanEquipUnseenItem(bot, NULL_SLOT, destination, proto->ItemId) == EQUIP_ERR_OK)
        {
            const uint8 slot = destination & 255;
            uint32 currentEntry = savedEquipmentEntries[bot->GetGUIDLow()]["off"][slot];
            if (currentEntry) comparison = sObjectMgr.GetItemPrototype(currentEntry);
        }
    }
    uint32 current = comparison ? sRandomItemMgr.GetStatWeightForName(bot->getClass(), comparison->ItemId,
        GetOffWeightName(bot)) : 0;
    return !current || uint64(candidate) * 100 >= uint64(current) * (100 + OffspecUpgradeThreshold(bot));
}

bool PlayerbotBuildProfileMgr::CanCarryOffspecItem(Player* bot, ItemPrototype const* proto, bool acquiring)
{
    if (!bot || !proto) return false;
    uint32 capacity = INVENTORY_SLOT_ITEM_END - INVENTORY_SLOT_ITEM_START, used = 0, offItems = 0;
    bool carried = false;
    auto countItem = [&](Item* item)
    {
        ++used;
        carried |= item->GetEntry() == proto->ItemId;
        // Every spare off-spec candidate uses the kit budget, including
        // equipment that also scores well for the main spec.
        if (IsOffspecUpgrade(bot, item->GetProto())) ++offItems;
    };
    for (uint8 slot = INVENTORY_SLOT_ITEM_START; slot < INVENTORY_SLOT_ITEM_END; ++slot)
        if (Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
        {
            countItem(item);
        }
    for (uint8 bag = INVENTORY_SLOT_BAG_START; bag < INVENTORY_SLOT_BAG_END; ++bag)
        if (Bag* container = (Bag*)bot->GetItemByPos(INVENTORY_SLOT_BAG_0, bag))
        {
            capacity += container->GetBagSize();
            for (uint8 slot = 0; slot < container->GetBagSize(); ++slot)
                if (Item* item = bot->GetItemByPos(bag, slot))
                {
                    countItem(item);
                }
        }
    return PlayerbotBankCapacity::Fits(capacity, used, offItems, minimumFreeBagSlots,
        maximumOffspecBagUsagePercent, OffspecCarryLimit(bot), acquiring || !carried);
}

std::vector<LivingGearDeficiency> PlayerbotBuildProfileMgr::GetGearingDeficiencies(Player* bot)
{
    std::vector<LivingGearDeficiency> result;
    if (!bot || !GearingGoalsEnabled()) return result;
    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
    {
        Item* item = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
        LivingGearDeficiency deficiency; deficiency.slot = slot;
        if (!item)
        {
            if (!EmptySlotIsDeficient(bot, slot)) continue;
            deficiency.reason = "empty_slot"; deficiency.severity = 100000;
        }
        else
        {
            ItemPrototype const* proto = item->GetProto();
            if (!proto) continue;
            deficiency.itemEntry = proto->ItemId;
            LivingGearScores scores = Evaluate(bot, proto);
            if (!scores.preferredArmor)
            {
                deficiency.reason = "inappropriate_armor";
                deficiency.severity = 80000 + std::min<uint32>(19999, bot->GetLevel() * 100);
            }
            else if (proto->ItemLevel + 5 < bot->GetLevel())
            {
                deficiency.reason = "severely_outdated";
                deficiency.severity = 50000 + (bot->GetLevel() - proto->ItemLevel) * 500;
            }
            else continue;
        }
        result.push_back(deficiency);
    }
    std::sort(result.begin(), result.end(), [](const LivingGearDeficiency& left, const LivingGearDeficiency& right)
    { return left.severity != right.severity ? left.severity > right.severity : left.slot < right.slot; });
    const std::string profile = Get(bot).gearProfile;
    const size_t limit = profile == "competitive" ? 5 : profile == "prepared" ? 3 : 1;
    if (result.size() > limit) result.resize(limit);
    return result;
}

bool PlayerbotBuildProfileMgr::HasGearingDeficiency(Player* bot)
{
    return !GetGearingDeficiencies(bot).empty();
}

uint32 PlayerbotBuildProfileMgr::GearingGoalUtility(Player* bot)
{
    return 35 + Get(bot).gearAmbition / 4;
}

std::string PlayerbotBuildProfileMgr::DiagnosticsJson(Player* bot)
{
    const LivingBotBuildProfile& p = Get(bot);
    std::vector<LivingGearDeficiency> deficiencies = GetGearingDeficiencies(bot);
    std::ostringstream out;
    out << "{\"main_specialization\":\"" << p.mainSpecialization << "\",\"main_archetype\":\""
        << JsonEscape(p.mainArchetype) << "\",\"off_specialization\":\""
        << p.offSpecialization << "\",\"off_archetype\":\"" << JsonEscape(p.offArchetype)
        << "\",\"active_specialization\":\"" << p.activeSpecialization
        << "\",\"active_archetype\":\"" << JsonEscape(p.activeArchetype)
        << "\",\"active_reason\":\"" << p.activeReason << "\",\"temporary\":"
        << (p.partySessionId ? "true" : "false") << ",\"offspec_ready\":"
        << (p.offPathId != p.mainPathId ? "true" : "false") << ",\"gear_profile\":\"" << p.gearProfile
        << "\",\"gear_ambition\":" << (uint32)p.gearAmbition << ",\"performance_drive\":"
        << (uint32)p.performanceDrive << ",\"role_flexibility\":" << (uint32)p.roleFlexibility
        << ",\"dungeon_interest\":" << (uint32)p.dungeonInterest << ",\"raid_aspiration\":"
        << (uint32)p.raidAspiration << ",\"weakest_slots\":[";
    for (size_t i = 0; i < deficiencies.size(); ++i)
    {
        if (i) out << ',';
        out << "{\"slot\":" << (uint32)deficiencies[i].slot << ",\"slot_name\":\""
            << EquipmentSlotName(deficiencies[i].slot) << "\",\"current_item_entry\":"
            << deficiencies[i].itemEntry << ",\"reason\":\"" << deficiencies[i].reason << "\"}";
    }
    out << "],\"revision\":" << p.revision << '}';
    return out.str();
}
