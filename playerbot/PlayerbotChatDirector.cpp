#include "botpch.h"
#include "PlayerbotChatDirector.h"

#include "PlayerbotAI.h"
#include "PlayerbotActionBroker.h"
#include "PlayerbotSocialActionBroker.h"
#include "PlayerbotNaturalLanguageCapabilityRegistry.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotOrganicEconomy.h"
#include "PlayerbotInventoryPressure.h"
#include "PlayerbotChatJson.h"
#include "PlayerbotLLMInterface.h"
#include "PlayerbotRendezvousManager.h"
#include "RandomPlayerbotMgr.h"
#include "TravelMgr.h"
#include "ServerFacade.h"
#include "GameEvents/GameEventMgr.h"
#include "strategy/ItemVisitors.h"
#include "strategy/values/BudgetValues.h"
#include "strategy/values/ItemUsageValue.h"

#include <algorithm>
#include <boost/algorithm/string.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <fstream>
#include <functional>
#include <regex>
#include <set>
#include <sstream>
#include <thread>

struct GuildPolicySnapshot
{
    std::string mode = "observe";
    std::string rolloutScope = "canary";
    std::set<uint32> canaryGuildIds;
};

static bool GuildExecutionEnabled(const std::string& mode, const std::string& scope,
    const std::set<uint32>& canaries, uint32 guildId)
{
    return mode == "active" && (scope == "global" || canaries.count(guildId));
}

static GuildPolicySnapshot ReadGuildPolicy()
{
    GuildPolicySnapshot policy;
    std::ifstream input("/srv/living-wow/config/guilds.json");
    if (!input.good())
        return policy;
    std::ostringstream value;
    value << input.rdbuf();
    std::smatch match;
    const std::string text = value.str();
    if (std::regex_search(text, match, std::regex("\\\"mode\\\"\\s*:\\s*\\\"(off|observe|active)\\\"")))
        policy.mode = match[1].str();
    if (std::regex_search(text, match, std::regex("\\\"scope\\\"\\s*:\\s*\\\"(canary|global)\\\"")))
        policy.rolloutScope = match[1].str();
    if (std::regex_search(text, match, std::regex("\\\"canaryGuildIds\\\"\\s*:\\s*\\[([^\\]]*)\\]")))
    {
        const std::string ids = match[1].str();
        const std::regex number("[0-9]+");
        for (std::sregex_iterator it(ids.begin(), ids.end(), number), end; it != end; ++it)
        {
            uint32 guildId = uint32(std::stoul(it->str()));
            if (guildId)
                policy.canaryGuildIds.insert(guildId);
        }
    }
    return policy;
}

static std::string GuildFocus(uint32 guildId, uint32 offset)
{
    static const char* focuses[] = {"social leveling", "dungeons", "crafting and trade", "exploration and questing"};
    return focuses[(guildId + offset) % 4];
}

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

static void PopulatePartyPetitionMembers(Player* bot, Group* group, uint32 petitionGuid,
    ChatDirectorCandidate& candidate)
{
    if (!bot || !group || !petitionGuid)
        return;
    for (GroupReference* reference = group->GetFirstMember(); reference; reference = reference->next())
    {
        Player* member = reference->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->GetSession())
            continue;
        auto signedAlready = CharacterDatabase.PQuery(
            "SELECT playerguid FROM petition_sign WHERE player_account = '%u' AND petitionguid = '%u'",
            member->GetSession()->GetAccountId(), petitionGuid);
        if (signedAlready)
        {
            candidate.signedPartyMembers.push_back(member->GetName());
            continue;
        }
        if (!member->GetGuildId() && !member->GetGuildIdInvited() &&
            member->GetMapId() == bot->GetMapId() &&
            sServerFacade.GetDistance2d(bot, member) <= sPlayerbotAIConfig.spellDistance)
            candidate.eligiblePetitionPartyMembers.push_back(member->GetName());
    }
}

static bool PartyContainsRealHuman(Group* group)
{
    if (!group)
        return false;
    for (GroupReference* reference = group->GetFirstMember(); reference; reference = reference->next())
    {
        Player* member = reference->getSource();
        if (member && member->IsInWorld() && member->isRealPlayer())
            return true;
    }
    return false;
}

static bool FindOwnedGuildPetition(Player* owner, uint32& petitionGuid, std::string& petitionName,
    uint32& signatures, uint32& required)
{
    petitionGuid = signatures = 0;
    petitionName.clear();
    required = sWorld.getConfig(CONFIG_UINT32_MIN_PETITION_SIGNS);
    if (!owner || owner->GetGuildId() || owner->GetGuildIdInvited())
        return false;
    Item* petition = owner->GetItemByEntry(5863);
    if (!petition)
        return false;
    petitionGuid = petition->GetObjectGuid().GetCounter();
    auto petitionRow = CharacterDatabase.PQuery(
        "SELECT name FROM petition WHERE petitionguid = '%u' AND ownerguid = '%u'",
        petitionGuid, owner->GetGUIDLow());
    if (!petitionRow)
        return false;
    petitionName = petitionRow->Fetch()[0].GetString();
    auto signatureRows = CharacterDatabase.PQuery(
        "SELECT playerguid FROM petition_sign WHERE petitionguid = '%u'", petitionGuid);
    signatures = signatureRows ? signatureRows->GetRowCount() : 0;
    return signatures < required;
}

static void PopulatePublicPetitionVolunteer(Player* bot, Player* speaker, const std::string& message,
    ChatDirectorCandidate& candidate)
{
    if (!bot || !speaker || !bot->GetSession() || bot == speaker || bot->GetTeam() != speaker->GetTeam() ||
        bot->GetMapId() != speaker->GetMapId() || !bot->IsAlive() || bot->IsInCombat() ||
        bot->GetGuildId() || bot->GetGuildIdInvited() || bot->InBattleGround() ||
        bot->IsTaxiFlying() || bot->GetTransport() || sPlayerbotRendezvousManager.IsActive(
            bot->GetGUIDLow(), speaker->GetGUIDLow()))
        return;

    std::string lowered = boost::algorithm::to_lower_copy(message);
    if ((lowered.find("charter") == std::string::npos && lowered.find("petition") == std::string::npos) ||
        (lowered.find("sign") == std::string::npos && lowered.find("signature") == std::string::npos))
        return;

    Group* botGroup = bot->GetGroup();
    if (botGroup && PartyContainsRealHuman(botGroup))
        return;

    std::vector<Player*> owners;
    owners.push_back(speaker);
    if (Group* speakerGroup = speaker->GetGroup())
        for (GroupReference* reference = speakerGroup->GetFirstMember(); reference; reference = reference->next())
        {
            Player* member = reference->getSource();
            if (member && member != speaker)
                owners.push_back(member);
        }

    Player* selectedOwner = nullptr;
    uint32 selectedPetition = 0, selectedSignatures = 0, selectedRequired = 0;
    std::string selectedName;
    for (Player* owner : owners)
    {
        uint32 petitionGuid = 0, signatures = 0, required = 0;
        std::string petitionName;
        if (!owner || !owner->GetPlayerbotAI() ||
            !FindOwnedGuildPetition(owner, petitionGuid, petitionName, signatures, required))
            continue;
        bool explicitlyNamed = boost::algorithm::icontains(message, owner->GetName());
        if (!selectedOwner || explicitlyNamed)
        {
            selectedOwner = owner;
            selectedPetition = petitionGuid;
            selectedName = petitionName;
            selectedSignatures = signatures;
            selectedRequired = required;
        }
        if (explicitlyNamed)
            break;
    }
    if (!selectedOwner)
        return;

    uint32 pendingVolunteers = sPlayerbotSocialActionBroker.PendingPetitionVolunteers(selectedPetition);
    if (selectedSignatures + pendingVolunteers >= selectedRequired)
        return;

    auto priorSignature = CharacterDatabase.PQuery(
        "SELECT playerguid FROM petition_sign WHERE player_account = '%u' AND petitionguid = '%u'",
        bot->GetSession()->GetAccountId(), selectedPetition);
    if (priorSignature)
        return;

    candidate.volunteerPetitionOwnerGuid = selectedOwner->GetGUIDLow();
    candidate.volunteerPetitionOwnerName = selectedOwner->GetName();
    candidate.volunteerPetitionGuid = selectedPetition;
    candidate.volunteerPetitionName = selectedName;
    candidate.volunteerPetitionSignatures = selectedSignatures;
    candidate.volunteerPetitionRequired = selectedRequired;

    ChatDirectorCapability capability;
    std::ostringstream ref;
    ref << "guild:petition-volunteer:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
        << ':' << selectedOwner->GetGUIDLow() << ':' << selectedPetition;
    capability.capabilityRef = ref.str();
    capability.type = "volunteer_for_guild_charter";
    capability.itemName = selectedName;
    capability.itemKind = "guild_charter";
    capability.demandReason = std::string("charter_owner:") + selectedOwner->GetName();
    capability.quantity = capability.minQuantity = capability.maxQuantity = 1;
    capability.actorGuid = bot->GetGUIDLow();
    capability.questId = selectedPetition;
    capability.description = std::string("Volunteer to sign ") + selectedOwner->GetName() + "'s existing " + selectedName +
        " guild charter. Whisper the owner, rendezvous through the safe travel manager, sign only through the normal "
        "petition exchange, and then return to the previous activity.";
    capability.deliveries.push_back("immediate");
    candidate.actionCapabilities.push_back(std::move(capability));
}

static void PopulateGuildState(Player* bot, Player* speaker, ChatDirectorCandidate& candidate)
{
    if (!bot || !speaker || !bot->GetGuildId())
        return;
    Guild* guild = sGuildMgr.GetGuildById(bot->GetGuildId());
    if (!guild)
        return;
    candidate.guildId = guild->GetId();
    candidate.guildName = guild->GetName();
    candidate.guildLeaderGuid = guild->GetLeaderGuid().GetCounter();
    candidate.guildRank = bot->GetRank();
    candidate.guildMemberCount = guild->GetMemberSize();
    candidate.isGuildLeader = guild->GetLeaderGuid() == bot->GetObjectGuid();

    std::ostringstream membershipRef;
    membershipRef << "guild:membership:" << guild->GetId() << ':' << bot->GetGUIDLow();
    AddSocialCapability(candidate, membershipRef.str(), "report_guild_membership", guild->GetId(),
        bot->GetGUIDLow(), 0, "Report the authoritative membership and recruiting state for " + guild->GetName() + ".");
    if (speaker->GetGuildId() == bot->GetGuildId())
    {
        std::ostringstream scheduleRef, resourcesRef;
        scheduleRef << "guild:schedule:" << guild->GetId() << ':' << bot->GetGUIDLow();
        resourcesRef << "guild:resources:" << guild->GetId() << ':' << bot->GetGUIDLow();
        AddSocialCapability(candidate, scheduleRef.str(), "report_guild_schedule", guild->GetId(),
            bot->GetGUIDLow(), 0, "Report authoritative upcoming guild events and current roster needs.");
        AddSocialCapability(candidate, resourcesRef.str(), "report_guild_resources", guild->GetId(),
            bot->GetGUIDLow(), 0, "Report authoritative guild-bank supply goals and current shortages.");
    }

    if (speaker == bot)
        return;

    uint32 botRank = bot->GetRank();
    uint32 speakerRank = speaker->GetRank();
    if (!speaker->GetGuildId() && !speaker->GetGuildIdInvited() &&
        guild->HasRankRight(botRank, GR_RIGHT_INVITE) && guild->GetMemberSize() < 1000)
    {
        std::ostringstream ref;
        ref << "guild:invite:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
            << ':' << candidate.guildId;
        AddSocialCapability(candidate, ref.str(), "invite_to_guild", 0, bot->GetGUIDLow(), 0,
            "Invite the requesting player to this exact guild after a scoped confirmation.");
    }

    if (speaker->GetGuildId() == candidate.guildId)
    {
        if (candidate.isGuildLeader)
        {
            std::ostringstream ref;
            ref << "guild:transfer-leader:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
                << ':' << candidate.guildId;
            AddSocialCapability(candidate, ref.str(), "transfer_guild_leadership", 0,
                bot->GetGUIDLow(), 0, "Transfer leadership of this exact guild to the requesting guild member. "
                "This consequential action always requires a second scoped confirmation.");
        }
        if (guild->HasRankRight(botRank, GR_RIGHT_PROMOTE) && speakerRank > botRank + 1)
        {
            std::ostringstream ref;
            ref << "guild:promote:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
                << ':' << candidate.guildId;
            AddSocialCapability(candidate, ref.str(), "promote_guild_member", 0, bot->GetGUIDLow(), 0,
                "Promote the requesting member by one rank under this guild's current rank rules.");
        }
        if (guild->HasRankRight(botRank, GR_RIGHT_DEMOTE) && speakerRank > botRank &&
            speakerRank < guild->GetLowestRank())
        {
            std::ostringstream ref;
            ref << "guild:demote:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
                << ':' << candidate.guildId;
            AddSocialCapability(candidate, ref.str(), "demote_guild_member", 0, bot->GetGUIDLow(), 0,
                "Demote the requesting member by one rank under this guild's current rank rules.");
        }
        if (guild->HasRankRight(botRank, GR_RIGHT_REMOVE) && speakerRank > botRank)
        {
            std::ostringstream ref;
            ref << "guild:remove:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
                << ':' << candidate.guildId;
            AddSocialCapability(candidate, ref.str(), "remove_guild_member", 0, bot->GetGUIDLow(), 0,
                "Remove the requesting member from this exact guild after a scoped confirmation.");
        }
    }

    bool contextualRequester = speaker->GetGuildId() == candidate.guildId ||
        (bot->GetGroup() && bot->GetGroup() == speaker->GetGroup());
    if (!candidate.isGuildLeader && contextualRequester)
    {
        std::ostringstream ref;
        ref << "guild:leave:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
            << ':' << candidate.guildId;
        AddSocialCapability(candidate, ref.str(), "leave_guild", 0, bot->GetGUIDLow(), 0,
            "Leave this exact guild after a scoped confirmation and normal server security checks.");
    }
}

static void PopulateSocialState(Player* bot, Player* speaker, ChatDirectorCandidate& candidate)
{
    if (!sPlayerbotAIConfig.chatDirectorSocialActions || !bot || !speaker)
        return;
    PopulateGuildState(bot, speaker, candidate);
    Group* group = bot->GetGroup();
    if (bot->GetMapId() == speaker->GetMapId() &&
        sServerFacade.GetDistance2d(bot, speaker) <= sPlayerbotAIConfig.farDistance)
    {
        const char* emotes[] = {"wave", "bow", "cheer", "salute", "laugh", "dance"};
        for (const char* emote : emotes)
        {
            std::ostringstream ref;
            ref << "social:emote:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow() << ':' << emote;
            AddSocialCapability(candidate, ref.str(), "perform_emote", 0, bot->GetGUIDLow(), 0,
                "Perform the " + std::string(emote) + " emote toward the requesting player.");
        }
    }
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

    if (speaker->GetGroup() == group && !bot->IsInCombat() && !bot->GetMap()->IsDungeon())
    {
        std::ostringstream ref;
        ref << "group:leave:" << state.groupId;
        AddSocialCapability(candidate, ref.str(), "leave_group", state.groupId, bot->GetGUIDLow(), 0,
            "Leave the current party only after an explicit confirmed request.");
    }

    if (state.humanMembers.empty() && speaker->GetGroup() != group && !bot->GetMap()->IsDungeon() &&
        !bot->InBattleGround() && !bot->IsTaxiFlying())
    {
        std::ostringstream ref;
        ref << "group:leave-ai-for-player:" << state.groupId << ':' << speaker->GetGUIDLow();
        AddSocialCapability(candidate, ref.str(), "leave_ai_party_for_player", state.groupId,
            bot->GetGUIDLow(), 0, "Leave this AI-only party for the requesting player. If combat is active, wait until it ends, then confirm only after the bot is actually ungrouped.");
    }

    if (speaker->GetGroup() == group)
    {
        std::ostringstream waitRef;
        waitRef << "travel:wait:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow() << ':' << state.groupId;
        AddSocialCapability(candidate, waitRef.str(), "wait_here", state.groupId, bot->GetGUIDLow(), 0,
            "Stop moving and wait at the current safe location until the party resumes.");
        if (!bot->IsInCombat() && !bot->InBattleGround() && !bot->IsTaxiFlying() &&
            bot->GetPlayerbotAI()->CanDoSpecificAction("hearthstone", true, true))
        {
            std::ostringstream hearthRef;
            hearthRef << "travel:hearth:" << bot->GetGUIDLow() << ':' << speaker->GetGUIDLow()
                << ':' << state.groupId;
            AddSocialCapability(candidate, hearthRef.str(), "use_hearthstone", state.groupId,
                bot->GetGUIDLow(), 0, "Use this character's ready hearthstone through normal game rules.");
        }
        Item* petition = (!bot->GetGuildId() && !bot->GetGuildIdInvited()) ?
            bot->GetItemByEntry(5863) : nullptr;
        if (petition)
        {
            uint32 petitionGuid = petition->GetObjectGuid().GetCounter();
            auto petitionRow = CharacterDatabase.PQuery(
                "SELECT name FROM petition WHERE petitionguid = '%u' AND ownerguid = '%u'",
                petitionGuid, bot->GetGUIDLow());
            if (!petitionRow)
                petition = nullptr;
            else
            {
                candidate.hasPetition = true;
                candidate.petitionName = petitionRow->Fetch()[0].GetString();
            }
        }
        if (petition)
        {
            uint32 petitionGuid = petition->GetObjectGuid().GetCounter();
            auto signatures = CharacterDatabase.PQuery(
                "SELECT playerguid FROM petition_sign WHERE petitionguid = '%u'", petitionGuid);
            uint32 signatureCount = signatures ? signatures->GetRowCount() : 0;
            uint32 required = sWorld.getConfig(CONFIG_UINT32_MIN_PETITION_SIGNS);
            candidate.petitionSignatures = signatureCount;
            candidate.petitionRequired = required;
            PopulatePartyPetitionMembers(bot, group, petitionGuid, candidate);
            uint32 eligible = candidate.eligiblePetitionPartyMembers.size();
            if (eligible)
            {
                std::ostringstream petitionRef;
                petitionRef << "guild:petition-solicit:" << bot->GetGUIDLow() << ':'
                    << speaker->GetGUIDLow() << ':' << state.groupId << ':' << petitionGuid;
                std::ostringstream description;
                description << "Ask up to " << std::min<uint32>(eligible, required - signatureCount)
                    << " eligible, nearby, unsigned members of this party to sign this bot's existing guild charter. "
                    << "The requesting player may already have signed; solicit the other eligible party members.";
                AddSocialCapability(candidate, petitionRef.str(), "solicit_petition_signatures",
                    state.groupId, bot->GetGUIDLow(), 0, description.str());
            }
        }

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
    candidate.alive = bot->IsAlive();
    candidate.ghost = bot->HasFlag(PLAYER_FLAGS, PLAYER_FLAGS_GHOST);
    candidate.partyAssistState = sPlayerbotRendezvousManager.PartyState(bot->GetGUIDLow());
    candidate.partyAssistReason = sPlayerbotRendezvousManager.PartyReason(bot->GetGUIDLow());
    candidate.deadRecoveryAttempts = sPlayerbotRendezvousManager.PartyDeadRecoveryAttempts(bot->GetGUIDLow());
    candidate.deadRecoverySeconds = sPlayerbotRendezvousManager.PartyDeadRecoverySeconds(bot->GetGUIDLow());
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
    if (speaker && bot->GetGroup() && bot->GetGroup() == speaker->GetGroup() &&
        !bot->IsInCombat())
    {
        uint8 bagUsage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
        ChatDirectorCapability report;
        report.capabilityRef = "bags:report:" + std::to_string(bot->GetGUIDLow()) + ':' +
            std::to_string(speaker->GetGUIDLow());
        report.type = "report_bag_state";
        report.itemKind = "inventory_status";
        report.currentQuantity = bagUsage;
        report.desiredQuantity = 100 - bagUsage;
        report.groupId = bot->GetGroup()->GetId();
        report.actorGuid = bot->GetGUIDLow();
        report.description = "Inventory is " + std::to_string((uint32)bagUsage) +
            " percent full with " + std::to_string((uint32)(100 - bagUsage)) + " percent free.";
        report.deliveries.push_back("immediate");
        candidate.actionCapabilities.push_back(std::move(report));
        LivingWowInventoryPressureSummary pressure = sPlayerbotInventoryPressure.Analyze(bot);
        if (bagUsage >= 80 && pressure.HasQuickMaintenance())
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
                " percent full; quick maintenance has " + std::to_string(pressure.vendorStacks) +
                " vendor stacks and " + std::to_string(pressure.StorableStacks()) + " storable stacks.";
            candidate.actionCapabilities.push_back(std::move(capability));
        }

        Group* party = bot->GetGroup();
        if (party->IsLeader(speaker->GetObjectGuid()))
        {
            ChatDirectorCapability capability;
            capability.actorGuid = bot->GetGUIDLow();
            capability.groupId = party->GetId();
            capability.quantity = capability.minQuantity = capability.maxQuantity = 1;
            capability.deliveries.push_back("immediate");
            if (sPlayerbotRendezvousManager.IsPartyFreeTime(bot->GetGUIDLow()))
            {
                capability.capabilityRef = "party:resume-assist:" + std::to_string(bot->GetGUIDLow()) + ':' +
                    std::to_string(speaker->GetGUIDLow()) + ':' + std::to_string(party->GetId());
                capability.type = "resume_party_assist";
                capability.description = "Recall this party member from personal errands and resume close party follow.";
            }
            else if ((bot->GetMapId() == speaker->GetMapId() && bot->IsWithinDistInMap(speaker, 120.0f)) ||
                sPlayerbotSocialActionBroker.HasActiveVendorTrip(bot->GetGUIDLow()))
            {
                capability.capabilityRef = "party:free-time:" + std::to_string(bot->GetGUIDLow()) + ':' +
                    std::to_string(speaker->GetGUIDLow()) + ':' + std::to_string(party->GetId());
                capability.type = "grant_party_free_time";
                capability.description = sPlayerbotSocialActionBroker.HasActiveVendorTrip(bot->GetGUIDLow()) ?
                    "After the current vendor or bank trip finishes, continue with safe personal mail, auction, repair, trainer, profession, and other city errands." :
                    "Temporarily release this party member from close follow for safe personal vendor, mail, bank, auction, repair, trainer, and profession errands.";
            }
            if (!capability.type.empty())
                candidate.actionCapabilities.push_back(std::move(capability));
        }
        sPlayerbotSocialActionBroker.AddSharedObjectCapabilities(bot, speaker, candidate);
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

void PlayerbotChatDirector::MaybeAdvertiseGuilds(std::chrono::steady_clock::time_point now)
{
    if (!sPlayerbotAIConfig.chatDirectorSocialActions)
        return;
    if (!nextGuildAdvertisement.time_since_epoch().count())
    {
        nextGuildAdvertisement = now + std::chrono::seconds(urand(300, 600));
        return;
    }
    if (now < nextGuildAdvertisement)
        return;

    struct Advertisement
    {
        Player* bot = nullptr;
        std::string key;
        std::string text;
        bool charter = false;
    };
    std::vector<Advertisement> charters;
    std::vector<Advertisement> guilds;
    std::set<uint32> representedGuilds;

    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld() || !bot->IsAlive() ||
            bot->IsInCombat() || bot->InBattleGround() || bot->IsTaxiFlying() || bot->GetTransport())
            continue;

        uint32 petitionGuid = 0, signatures = 0, required = 0;
        std::string petitionName;
        if (FindOwnedGuildPetition(bot, petitionGuid, petitionName, signatures, required))
        {
            std::string key = "petition:" + std::to_string(petitionGuid);
            auto cooldown = guildAdvertisementCooldowns.find(key);
            if (cooldown == guildAdvertisementCooldowns.end() || now >= cooldown->second)
            {
                uint32 pending = sPlayerbotSocialActionBroker.PendingPetitionVolunteers(petitionGuid);
                uint32 remaining = required > signatures + pending ? required - signatures - pending : 0;
                if (remaining)
                {
                    std::ostringstream text;
                    text << "Looking for " << remaining << " more "
                         << (remaining == 1 ? "person" : "people") << " to sign the "
                         << petitionName << " guild charter. Whisper " << bot->GetName()
                         << " if you can help.";
                    charters.push_back({bot, key, text.str(), true});
                }
            }
        }

        uint32 guildId = bot->GetGuildId();
        if (!guildId || representedGuilds.find(guildId) != representedGuilds.end())
            continue;
        Guild* guild = sGuildMgr.GetGuildById(guildId);
        if (!guild || guild->GetMemberSize() >= 1000 ||
            !guild->HasRankRight(bot->GetRank(), GR_RIGHT_INVITE))
            continue;
        // Prefer the leader as the public face. An officer with invite rights
        // remains a valid fallback when the leader is offline.
        Player* leader = sObjectAccessor.FindPlayer(guild->GetLeaderGuid());
        if (leader && leader->IsInWorld() && leader->GetPlayerbotAI() && leader != bot)
            continue;
        representedGuilds.insert(guildId);
        std::string key = "guild:" + std::to_string(guildId);
        auto cooldown = guildAdvertisementCooldowns.find(key);
        if (cooldown != guildAdvertisementCooldowns.end() && now < cooldown->second)
            continue;
        std::ostringstream text;
        text << guild->GetName() << " is recruiting. Whisper " << bot->GetName()
             << " if you're interested in joining.";
        guilds.push_back({bot, key, text.str(), false});
    }

    std::vector<Advertisement>& pool = !charters.empty() &&
        (guilds.empty() || urand(0, 1) == 0) ? charters : guilds;
    if (pool.empty())
    {
        nextGuildAdvertisement = now + std::chrono::minutes(5);
        return;
    }
    Advertisement& selected = pool[urand(0, pool.size() - 1)];
    if (selected.bot->GetPlayerbotAI()->SayToGeneral(selected.text))
    {
        guildAdvertisementCooldowns[selected.key] = now +
            (selected.charter ? std::chrono::minutes(45) : std::chrono::minutes(90));
        nextGuildAdvertisement = now + std::chrono::seconds(urand(600, 1200));
        sLog.outString("Living WoW guild advertisement bot=%u type=%s key=%s",
            selected.bot->GetGUIDLow(), selected.charter ? "charter" : "recruitment", selected.key.c_str());
    }
    else
        nextGuildAdvertisement = now + std::chrono::minutes(5);
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

static bool HasActiveProgressionQuestUseItem(Player* bot)
{
    if (!bot)
        return false;
    for (uint16 slot = 0; slot < MAX_QUEST_LOG_SIZE; ++slot)
    {
        uint32 questId = bot->GetQuestSlotQuestId(slot);
        if (!questId || bot->GetQuestStatus(questId) != QUEST_STATUS_INCOMPLETE)
            continue;
        Quest const* quest = sObjectMgr.GetQuestTemplate(questId);
        if (!quest)
            continue;

        std::vector<uint32> itemIds;
        if (quest->GetSrcItemId())
            itemIds.push_back(quest->GetSrcItemId());
        for (uint8 source = 0; source < QUEST_SOURCE_ITEM_IDS_COUNT; ++source)
            if (quest->ReqSourceId[source] && quest->ReqSourceCount[source] &&
                std::find(itemIds.begin(), itemIds.end(), quest->ReqSourceId[source]) == itemIds.end())
                itemIds.push_back(quest->ReqSourceId[source]);

        for (uint32 itemId : itemIds)
        {
            if (!bot->GetItemCount(itemId, false))
                continue;
            ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);
            if (!proto)
                continue;
            for (uint8 spell = 0; spell < MAX_ITEM_PROTO_SPELLS; ++spell)
                if (proto->Spells[spell].SpellId &&
                    proto->Spells[spell].SpellTrigger == ITEM_SPELLTRIGGER_ON_USE)
                    return true;
        }
    }
    return false;
}

void PlayerbotChatDirector::MaybeReportBotHealth(std::chrono::steady_clock::time_point now)
{
    if (nextHealthSample.time_since_epoch().count() != 0 && now < nextHealthSample)
        return;
    const uint32 fullSampleSeconds = std::max<uint32>(60, sPlayerbotAIConfig.chatDirectorHealthSampleSeconds);
    const bool canarySampling = !sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.empty();
    const bool globalRecovery = sPlayerbotAIConfig.chatDirectorBotRecoveryMode >= 2;
    const bool recoverySampling = canarySampling || globalRecovery;
    nextHealthSample = now + std::chrono::seconds(recoverySampling ? std::min<uint32>(10, fullSampleSeconds) : fullSampleSeconds);
    static std::chrono::steady_clock::time_point nextFullHealthSample;
    const bool fullSample = nextFullHealthSample.time_since_epoch().count() == 0 || now >= nextFullHealthSample;
    if (fullSample) nextFullHealthSample = now + std::chrono::seconds(fullSampleSeconds);
    // A global recovery rollout must not start hundreds of asynchronous route
    // searches during the same world update. Cover the population once per
    // full telemetry interval in stable, small GUID buckets instead.
    static uint32 recoverySweepBucket = 0;
    static constexpr uint32 recoverySweepBuckets = 30;
    const uint32 currentRecoverySweepBucket = recoverySweepBucket;
    if (globalRecovery)
        recoverySweepBucket = (recoverySweepBucket + 1) % recoverySweepBuckets;

    std::vector<std::string> samples;
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->GetPlayerbotAI() || !bot->IsInWorld())
            continue;
        const bool recoveryCanary = std::find(sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.begin(),
            sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.end(), guid) !=
            sPlayerbotAIConfig.chatDirectorRecoveryCanaryBotGuids.end();
        BotHealthState& state = botHealth[guid];
        const bool recoverySweepMember = globalRecovery &&
            guid % recoverySweepBuckets == currentRecoverySweepBucket;
        const bool activeGlobalRecovery = globalRecovery && state.recoveryStep > 0;
        const bool emitHealthSample = fullSample || recoveryCanary;
        if (!fullSample && !recoveryCanary && !recoverySweepMember && !activeGlobalRecovery) continue;
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
            if (state.nearbyRerouteResult == "requested")
            {
                state.nearbyRerouteResult = "movement_confirmed";
                state.objectiveRouteFailures = 0;
            }
        }
        std::string action = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
        std::string lowered = boost::algorithm::to_lower_copy(action);
        // Party travel is registered once by the authoritative invitation
        // lifecycle. Health sampling must never create a second rendezvous or
        // relocate an already-persisted party during login.
        ProgressionQuestSnapshot questSnapshot = GetProgressionQuestSnapshot(bot);
        TravelTarget* observedTravelTarget = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<TravelTarget*>("travel target")->Get();
        TravelStatus observedTravelStatus = observedTravelTarget ?
            observedTravelTarget->GetStatus() : TravelStatus::TRAVEL_STATUS_NONE;
        bool observedTravelActive = observedTravelTarget &&
            (observedTravelStatus == TravelStatus::TRAVEL_STATUS_READY ||
             observedTravelStatus == TravelStatus::TRAVEL_STATUS_TRAVEL ||
             observedTravelStatus == TravelStatus::TRAVEL_STATUS_WORK);
        bool travelAdvanced = false;
        if (observedTravelActive)
        {
            std::string targetPosition = observedTravelTarget->GetPosStr();
            float targetDistance = observedTravelTarget->Distance(bot);
            if (state.travelTargetPosition != targetPosition)
            {
                // Installing a validated target is a real goal transition, but
                // it is not yet movement. Start a separate route-progress clock
                // so a newly selected long route gets a fair chance to advance.
                state.travelTargetPosition = targetPosition;
                state.lastTravelDistance = targetDistance;
                state.lastTravelAdvance = now;
            }
            else if (state.lastTravelDistance < 0.0f ||
                targetDistance + 5.0f <= state.lastTravelDistance)
            {
                travelAdvanced = state.lastTravelDistance >= 0.0f;
                state.lastTravelDistance = targetDistance;
                state.lastTravelAdvance = now;
            }
            if (travelAdvanced)
                state.travelAdvancedSinceReport = true;
        }
        else
        {
            state.travelTargetPosition.clear();
            state.lastTravelDistance = -1.0f;
            state.lastTravelAdvance = std::chrono::steady_clock::time_point();
        }
        bool questProgressChanged = !state.questProgressSignature.empty() &&
            state.questProgressSignature != questSnapshot.signature;
        state.questProgressSignature = questSnapshot.signature;
        for (uint32 questId : questSnapshot.completed)
            if (!state.completedQuestSince.count(questId)) state.completedQuestSince[questId] = now;
        for (auto it = state.completedQuestSince.begin(); it != state.completedQuestSince.end();)
            if (!questSnapshot.completed.count(it->first)) it = state.completedQuestSince.erase(it); else ++it;
        for (auto it = state.turninRouteFailures.begin(); it != state.turninRouteFailures.end();)
            if (!questSnapshot.completed.count(it->first)) it = state.turninRouteFailures.erase(it); else ++it;
        for (auto it = state.turninDeferredUntil.begin(); it != state.turninDeferredUntil.end();)
        {
            if (!questSnapshot.completed.count(it->first))
                it = state.turninDeferredUntil.erase(it);
            else
                ++it;
        }
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
        if (levelChanged || xpChanged || questProgressChanged || travelAdvanced)
        {
            state.lastMeaningfulProgress = now;
            state.objectiveRouteFailures = 0;
            if (state.nearbyRerouteResult != "movement_confirmed")
                state.nearbyRerouteResult.clear();
            // Unrelated XP, levels, or another quest changing must not discard
            // an exact turn-in task that is still authoritatively pending.
            // That race repeatedly pulled canaries away before they reached
            // their quest taker.
            bool recoveryQuestStillPending = state.recoveryQuestId &&
                questSnapshot.completed.count(state.recoveryQuestId);
            if (!recoveryQuestStillPending)
            {
                state.recoveryStep = 0;
                state.questItemFollowup = false;
                state.recoveryQuestId = 0;
                state.recoveryStartedAt = std::chrono::steady_clock::time_point();
                state.recoveryInteractionAttempts = 0;
                state.lastRecoveryInteraction = std::chrono::steady_clock::time_point();
                state.recoveryResult.clear();
            }
        }
        long stillSeconds = std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMoved).count();
        long progressSeconds = std::chrono::duration_cast<std::chrono::seconds>(now - state.lastMeaningfulProgress).count();
        uint32 stalledQuestId = 0;
        std::vector<uint32> stalledQuestIds;
        long oldestCompleteSeconds = 0;
        uint32 deferredTurninCount = 0;
        for (const auto& complete : state.completedQuestSince)
        {
            long age = std::chrono::duration_cast<std::chrono::seconds>(now - complete.second).count();
            if (age > oldestCompleteSeconds) oldestCompleteSeconds = age;
            Quest const* quest = sObjectMgr.GetQuestTemplate(complete.first);
            auto deferred = state.turninDeferredUntil.find(complete.first);
            if (deferred != state.turninDeferredUntil.end() && now < deferred->second)
            {
                ++deferredTurninCount;
                continue;
            }
            // A completed-but-currently-unrewardable quest must not starve all
            // other valid turn-ins behind its lower numeric ID. Keep it in the
            // authoritative pending set for later diagnosis, but recover the
            // oldest quest the core can actually reward now.
            if (age >= sPlayerbotAIConfig.chatDirectorQuestStuckSeconds &&
                quest && bot->CanRewardQuest(quest, false))
            {
                stalledQuestIds.push_back(complete.first);
                if (!stalledQuestId)
                    stalledQuestId = complete.first;
            }
        }
        bool noActions = lowered.find("no actions executed") != std::string::npos;
        bool routeAdvancing = observedTravelActive &&
            state.lastTravelAdvance.time_since_epoch().count() != 0 &&
            std::chrono::duration_cast<std::chrono::seconds>(
                now - state.lastTravelAdvance).count() <
                sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        // A bot carrying a completed quest gets a short grace period for the
        // ordinary travel strategy to find its turn-in. Do not spend its first
        // limited recovery attempt on generic objective reselection while that
        // more authoritative diagnosis is aging toward questStalled.
        bool movementStalled = questSnapshot.completed.empty() && expectsMovement && noActions &&
            !routeAdvancing && stillSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds &&
            progressSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        // A completed quest has its own authoritative age. Unrelated kill XP,
        // another quest objective, or ordinary combat must not restart that
        // clock forever. Safety exclusions below still prevent recovery during
        // combat, transports, death, or human-directed party activity.
        bool questStalled = stalledQuestId != 0;
        uint8 bagUsed = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
        bool inventoryBlocked = bagUsed >= 95;
        bool inventoryStalled = inventoryBlocked && noActions &&
            stillSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        bool suspected = !excluded && (movementStalled || questStalled || inventoryStalled);
        std::string classification = "active";
        if (!bot->IsAlive()) classification = "dead";
        else if (bot->IsInCombat()) classification = "combat";
        else if (bot->IsTaxiFlying() || bot->GetTransport()) classification = "transport";
        else if (playerStay) classification = "group_wait";
        else if (inventoryStalled) classification = "inventory_blocked";
        else if (questStalled) classification = "completed_quest_awaiting_turn_in";
        else if (movementStalled) classification = "movement_stalled";
        else if (!expectsMovement && stillSeconds >= 60) classification = "rpg_pause";

        // Recovery mode 1 observes only; mode 2 performs the least invasive
        // recovery step on the world thread. Resetting the travel target makes
        // normal quest/travel strategies choose again without teleporting or
        // modifying authoritative quest state.
        const bool recoveryExecutionScope = globalRecovery ||
            (sPlayerbotAIConfig.chatDirectorBotRecoveryMode == 1 && recoveryCanary);
        const bool recoveryAttemptEligible = recoveryExecutionScope &&
            (!globalRecovery || recoveryCanary || recoverySweepMember);
        TravelTarget* inFlightRecoveryTarget = observedTravelTarget;
        TravelStatus inFlightRecoveryStatus = observedTravelStatus;
        long recoveryAgeSeconds = state.recoveryStartedAt.time_since_epoch().count() == 0 ? 0 :
            std::chrono::duration_cast<std::chrono::seconds>(now - state.recoveryStartedAt).count();
        long travelAdvanceAgeSeconds = state.lastTravelAdvance.time_since_epoch().count() == 0 ?
            recoveryAgeSeconds : std::chrono::duration_cast<std::chrono::seconds>(
                now - state.lastTravelAdvance).count();
        bool recoveryPrepareTimedOut = state.recoveryStep > 0 &&
            inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_PREPARE &&
            recoveryAgeSeconds >= 2 * (long)sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        bool recoveryMovementTimedOut = state.recoveryStep > 0 && observedTravelActive && !excluded &&
            stillSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds &&
            travelAdvanceAgeSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds;
        bool recoveryRouteTerminal = state.recoveryStep > 0 &&
            (inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_NONE ||
             inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_COOLDOWN ||
             inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_EXPIRED ||
             recoveryPrepareTimedOut || recoveryMovementTimedOut);
        if (recoveryRouteTerminal)
        {
            uint32 terminalStep = state.recoveryStep;
            uint32 terminalQuestId = state.recoveryQuestId;
            state.lastRecoveryQuestId = terminalQuestId ? terminalQuestId : state.lastRecoveryQuestId;
            if ((terminalStep == 2 || terminalStep == 6) && HasActiveProgressionQuestUseItem(bot))
                state.questItemFollowup = true;
            std::string terminalResult = terminalStep == 3 ? "quest_turnin_route_terminal" :
                (terminalStep == 5 ? "vendor_route_terminal" : "objective_route_terminal");
            state.recoveryTerminalReason = recoveryPrepareTimedOut ? "prepare_timeout" :
                (recoveryMovementTimedOut ? "movement_timeout" : "status_terminal");
            // A terminal target remains the authoritative travel value until it
            // is explicitly replaced. Merely releasing recoveryStep left the
            // normal travel strategy evaluating the same cooldown/expired
            // target and produced the persistent travel/no-action loop.
            bool terminalCleared = bot->GetPlayerbotAI()->DoSpecificAction(
                "progression reset travel target",
                Event("living progression clear terminal route"), true);
            std::string routeOutcome = bot->GetPlayerbotAI()->GetAiObjectContext()->
                GetValue<std::string>("manual string", "future travel outcome")->Get();
            int routeQuestId = bot->GetPlayerbotAI()->GetAiObjectContext()->
                GetValue<int>("manual int", "future travel quest id")->Get();
            bool pendingTurninFailed = terminalStep == 3 && terminalQuestId &&
                questSnapshot.completed.count(terminalQuestId);
            if (pendingTurninFailed)
            {
                uint32 failures = ++state.turninRouteFailures[terminalQuestId];
                if (failures >= 2)
                {
                    state.turninDeferredUntil[terminalQuestId] = now + std::chrono::minutes(30);
                    terminalResult += "_deferred";
                }
            }
            if (terminalStep == 2)
            {
                ++state.objectiveRouteFailures;
                if (state.objectiveRouteFailures >= 2)
                {
                    bool nearbyHuman = false;
                    const std::list<ObjectGuid>& nearbyPlayers = bot->GetPlayerbotAI()->GetAiObjectContext()->
                        GetValue<std::list<ObjectGuid> >("nearest non bot players")->Get();
                    for (ObjectGuid const& nearbyGuid : nearbyPlayers)
                    {
                        Player* nearby = sObjectAccessor.FindPlayer(nearbyGuid);
                        if (nearby && nearby->GetMapId() == bot->GetMapId() &&
                            bot->GetDistance(nearby) <= 60.0f)
                        {
                            nearbyHuman = true;
                            break;
                        }
                    }
                    if (bot->GetGroup())
                        state.nearbyRerouteResult = "skipped_grouped";
                    else if (nearbyHuman)
                        state.nearbyRerouteResult = "skipped_human_nearby";
                    else
                    {
                        bool nudged = bot->GetPlayerbotAI()->DoSpecificAction(
                            "move random", Event("living progression nearby reroute"), true);
                        state.nearbyRerouteResult = nudged ? "requested" : "rejected";
                    }
                }
            }
            state.recoveryResult = terminalResult +
                (terminalCleared ? "_cleared" : "_clear_rejected");
            if (routeQuestId == (int)terminalQuestId && !routeOutcome.empty())
                state.recoveryResult += "_" + routeOutcome;
            // Terminal targets cannot be advanced. Keeping their recovery step
            // nonzero made hundreds of bots bypass the global sampling buckets
            // every ten seconds forever. Release the hot-loop state and let the
            // next bounded sweep choose a fresh, reason-specific action.
            state.recoveryStep = 0;
            state.recoveryQuestId = 0;
            state.recoveryStartedAt = std::chrono::steady_clock::time_point();
            state.recoveryInteractionAttempts = 0;
            state.lastRecoveryInteraction = std::chrono::steady_clock::time_point();
            state.travelTargetPosition.clear();
            state.lastTravelDistance = -1.0f;
            state.lastTravelAdvance = std::chrono::steady_clock::time_point();
        }
        bool turninRecoveryInFlight = state.recoveryStep == 3 && state.recoveryQuestId &&
            questSnapshot.completed.count(state.recoveryQuestId) && inFlightRecoveryTarget &&
            (inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_PREPARE ||
             inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_READY ||
             inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_TRAVEL ||
             inFlightRecoveryStatus == TravelStatus::TRAVEL_STATUS_WORK);
        // Do not let the hourly recovery cooldown replace a still-valid exact
        // turn-in with a newer completed quest just before the first one arrives.
        if (suspected && recoveryAttemptEligible && !turninRecoveryInFlight)
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
                    // Reset returns false when there is no active target. That
                    // is already a clean starting state, so still request the
                    // exact authoritative quest taker.
                    recovered = false;
                    for (uint32 candidateQuestId : stalledQuestIds)
                    {
                        if (!bot->GetPlayerbotAI()->DoSpecificAction(
                            "request quest turnin target::" + std::to_string(candidateQuestId),
                            Event("can move around"), true))
                            continue;
                        stalledQuestId = candidateQuestId;
                        recovered = true;
                        break;
                    }
                    state.lastRecoveryQuestId = stalledQuestId;
                    recovery = recovered ? "quest_turnin_route_requested" :
                        (reset ? "quest_turnin_request_rejected" : "quest_turnin_request_rejected_no_prior_target");
                    state.recoveryQuestId = stalledQuestId;
                    state.recoveryStep = 3;
                    state.recoveryInteractionAttempts = 0;
                    state.lastRecoveryInteraction = std::chrono::steady_clock::time_point();
                }
                else
                {
                    // A route can bring the bot to the correct quest area yet
                    // still leave an authoritative source item unused. Detect
                    // that from quest and inventory state, not from the action
                    // debug string. This covers both quest-start SrcItemId
                    // tools and ReqSourceId items acquired during the quest.
                    bool questItemAttempted = (state.questItemFollowup || state.recoveryStep >= 2) &&
                        sPlayerbotAIConfig.chatDirectorQuestInteraction &&
                        sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep >= 6 &&
                        HasActiveProgressionQuestUseItem(bot);
                    state.questItemFollowup = false;
                    if (questItemAttempted)
                    {
                        recovered = bot->GetPlayerbotAI()->DoSpecificAction(
                            "use random quest item", Event("living progression quest item recovery"), true);
                        if (recovered)
                        {
                            recovery = "quest_item_used_or_approaching_target";
                            state.recoveryStep = 6;
                        }
                    }

                    // ResetTargetAction returns false when there was no active
                    // target to clear. That is not a reason to skip choosing a
                    // new target: action-starved bots commonly have no target.
                    if (!recovered)
                    {
                        bool reset = bot->GetPlayerbotAI()->DoSpecificAction(
                            "progression reset travel target", Event("living progression objective recovery"), true);
                        recovered = reset;
                        if (recovered && sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep >= 2)
                            recovered = bot->GetPlayerbotAI()->DoSpecificAction(
                                "request progression quest travel target", Event("can move around"), true);
                        recovery = recovered ? "objective_route_requested" :
                            (questItemAttempted ? "quest_item_not_usable_and_objective_rejected" :
                                (reset ? "objective_request_rejected" : "objective_reset_rejected"));
                        state.recoveryStep = std::min<uint32>(2, sPlayerbotAIConfig.chatDirectorRecoveryMaximumStep);
                    }
                }
                state.lastRecovery = now;
                state.recoveryAttempts.push_back(now);
                state.recoveryResult = recovery;
                if (state.recoveryStep > 0)
                    state.recoveryStartedAt = now;
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
        // workload. Advance every in-scope recovery target while still using
        // the normal MoveToTravelTargetAction safety checks on the world thread.
        TravelTarget* recoveryTarget = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<TravelTarget*>("travel target")->Get();
        bool boundedRecoveryTarget = false;
        bool recoveryMoveUseful = false;
        bool recoveryMovePossible = false;
        std::string recoveryMoveResult = "not_applicable";
        if (recoveryExecutionScope && state.recoveryStep > 0 && recoveryTarget)
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
        std::string recoveryPrepareResult = "not_applicable";
        if (!excluded && recoveryExecutionScope && state.recoveryStep > 0 && recoveryTarget &&
            recoveryStatus == TravelStatus::TRAVEL_STATUS_PREPARE)
        {
            // Prepared recovery searches are futures. Under the 600-bot
            // scheduler the ordinary low-relevance chooser can remain starved
            // even after the exact result is ready. Poll and install it through
            // the normal action; Execute remains non-blocking while pending.
            bool useful = bot->GetPlayerbotAI()->CanDoSpecificAction(
                "choose travel target", true, false);
            bool possible = bot->GetPlayerbotAI()->CanDoSpecificAction(
                "choose travel target", false, true);
            if (useful && possible)
            {
                bool finalized = bot->GetPlayerbotAI()->DoSpecificAction(
                    "choose travel target", Event("living progression finalize recovery target"), true);
                recoveryPrepareResult = finalized ? "target_finalized" : "target_not_ready";
                recoveryStatus = recoveryTarget->GetStatus();
            }
            else if (!useful)
                recoveryPrepareResult = "target_finalize_not_useful";
            else
                recoveryPrepareResult = "target_finalize_impossible";
        }
        bool exactTurninTarget = false;
        if (recoveryExecutionScope && state.recoveryStep == 3 && state.recoveryQuestId && recoveryTarget)
        {
            // Async travel requests share legacy metadata slots with ordinary
            // Playerbots travel. If another request updates those slots while
            // an exact turn-in route is being calculated, the finished target
            // can lose its recovery condition and priority. Re-establish them
            // only when the installed world-authoritative destination is the
            // exact QuestTaker for this recovery's recorded completed quest.
            QuestTravelDestination* questDestination =
                dynamic_cast<QuestTravelDestination*>(recoveryTarget->GetDestination());
            if (questDestination && questDestination->GetQuestId() == state.recoveryQuestId &&
                questDestination->GetPurpose() == TravelDestinationPurpose::QuestTaker)
            {
                exactTurninTarget = true;
                boundedRecoveryTarget = true;
                // The guarded movement action checks can-move-around on every
                // execution. Keeping that volatile value as a target lifetime
                // condition made long routes cool down before arrival.
                recoveryTarget->SetConditions({});
                recoveryTarget->SetRelevance(std::max<uint32>(recoveryTarget->GetRelevance(), 199u));
                // MoveToTravelTargetAction recognizes the exact QuestTaker
                // purpose plus this relevance as bounded recovery priority.
                // Its normal path, group, taxi, and free-movement guards remain.
                if (recoveryTarget->GetTimeLeft() < 15 * 60 * 1000)
                    recoveryTarget->SetExpireIn(15 * 60 * 1000);
            }
        }

        // A QuestTaker travel target only gets the bot near the authoritative
        // creature or gameobject. Complete the ordinary, legitimate interaction
        // and verify the quest reward before releasing the persistent task.
        std::string recoveryInteractionResult = "not_applicable";
        if (!excluded && exactTurninTarget)
        {
            GuidPosition* targetPosition = dynamic_cast<GuidPosition*>(recoveryTarget->GetPosition());
            WorldObject* questTaker = targetPosition ?
                targetPosition->GetWorldObject(bot->GetInstanceId()) : nullptr;
            float interactionDistance = questTaker ? bot->GetDistance(questTaker) :
                recoveryTarget->Distance(bot);
            if (recoveryStatus == TravelStatus::TRAVEL_STATUS_WORK &&
                interactionDistance > INTERACTION_DISTANCE)
            {
                // WORK is not success. If the legacy destination bounding box
                // reports arrival too early, resume guarded travel to the exact
                // spawn instead of abandoning the turn-in.
                recoveryTarget->SetStatus(TravelStatus::TRAVEL_STATUS_TRAVEL);
                recoveryStatus = TravelStatus::TRAVEL_STATUS_TRAVEL;
                recoveryInteractionResult = "quest_turnin_early_arrival_corrected";
            }
            if (questTaker && interactionDistance <= INTERACTION_DISTANCE)
            {
                bool retryReady = state.lastRecoveryInteraction.time_since_epoch().count() == 0 ||
                    std::chrono::duration_cast<std::chrono::seconds>(
                        now - state.lastRecoveryInteraction).count() >= 5;
                if (retryReady && state.recoveryInteractionAttempts < 3)
                {
                    state.lastRecoveryInteraction = now;
                    ++state.recoveryInteractionAttempts;
                    Event interaction("living progression turnin interaction",
                        questTaker->GetObjectGuid(), bot);
                    bool processed = bot->GetPlayerbotAI()->DoSpecificAction(
                        "talk to quest giver", interaction, true);
                    if (bot->GetQuestRewardStatus(state.recoveryQuestId))
                    {
                        recoveryInteractionResult = "quest_turnin_completed";
                        state.recoveryResult = recoveryInteractionResult;
                        state.recoveryStep = 0;
                        state.recoveryQuestId = 0;
                        state.recoveryInteractionAttempts = 0;
                        state.lastRecoveryInteraction = std::chrono::steady_clock::time_point();
                    }
                    else
                    {
                        recoveryInteractionResult = processed ?
                            "quest_turnin_not_rewarded" : "quest_turnin_interaction_rejected";
                        state.recoveryResult = recoveryInteractionResult;
                    }
                }
                else if (state.recoveryInteractionAttempts >= 3)
                    recoveryInteractionResult = "quest_turnin_interaction_failed";
                else
                    recoveryInteractionResult = "quest_turnin_interaction_backoff";
            }
            else if (!questTaker && recoveryTarget->Distance(bot) <= sPlayerbotAIConfig.sightDistance)
                recoveryInteractionResult = "quest_turnin_target_not_loaded";
            else if (recoveryInteractionResult == "not_applicable")
                recoveryInteractionResult = "quest_turnin_traveling";
        }
        if (!excluded && boundedRecoveryTarget &&
            (recoveryStatus == TravelStatus::TRAVEL_STATUS_READY ||
             recoveryStatus == TravelStatus::TRAVEL_STATUS_TRAVEL))
        {
            // A movement generator that has reported movement while producing
            // no position change for the full stall threshold is stale. Clear
            // it before asking the ordinary guarded action to continue; this
            // does not relocate the bot or bypass path validation.
            if (stillSeconds >= sPlayerbotAIConfig.chatDirectorMovementStuckSeconds &&
                sServerFacade.isMoving(bot))
            {
                bot->GetPlayerbotAI()->StopMoving();
                recoveryMoveResult = "stale_movement_cleared";
            }
            recoveryMoveUseful = bot->GetPlayerbotAI()->CanDoSpecificAction(
                "move to travel target", true, false);
            recoveryMovePossible = bot->GetPlayerbotAI()->CanDoSpecificAction(
                "move to travel target", false, true);
            if (recoveryMoveUseful && recoveryMovePossible)
            {
                bool advanced = bot->GetPlayerbotAI()->DoSpecificAction(
                    "move to travel target", Event("living progression route continuation"), true);
                recoveryMoveResult = advanced ? "movement_started" : "movement_failed";
            }
            else if (!recoveryMoveUseful)
                recoveryMoveResult = "movement_not_useful";
            else
                recoveryMoveResult = "movement_impossible";
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
        std::string pathStatus = movementStalled ? "movement_blocked" : (expectsMovement ? "route_ready" : "not_applicable");
        std::string zoneName, subzoneName;
        if (AreaTableEntry const* zone = GetAreaEntryByAreaID(bot->GetZoneId())) zoneName = zone->area_name[0];
        if (AreaTableEntry const* area = GetAreaEntryByAreaID(areaId)) subzoneName = area->area_name[0];
        uint32 diagnosticQuestId = state.recoveryQuestId ? state.recoveryQuestId : state.lastRecoveryQuestId;
        Quest const* diagnosticQuest = diagnosticQuestId ? sObjectMgr.GetQuestTemplate(diagnosticQuestId) : nullptr;
        std::string diagnosticQuestTitle = diagnosticQuest ? diagnosticQuest->GetTitle() : "";
        int futureTurninQuestId = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<int>("manual int", "future travel quest id")->Get();
        std::string futureTurninOutcome = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<std::string>("manual string", "future travel outcome")->Get();
        int futureTurninRanges = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<int>("manual int", "future travel range count")->Get();
        int futureTurninPoints = bot->GetPlayerbotAI()->GetAiObjectContext()->
            GetValue<int>("manual int", "future travel point count")->Get();
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
             << "\",\"travel_advanced\":" << (state.travelAdvancedSinceReport ? "true" : "false")
             << ",\"quest_state\":\"" << (!questSnapshot.completed.empty() ? "completed_quest_pending" : "none_completed")
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
             << ",\"recovery_quest_item_followup\":" << (state.questItemFollowup ? "true" : "false")
             << ",\"recovery_target_quest_id\":" << state.recoveryQuestId
             << ",\"recovery_last_quest_id\":" << state.lastRecoveryQuestId
             << ",\"recovery_target_quest_title\":\"" << PlayerbotLLMInterface::SanitizeForJson(diagnosticQuestTitle)
             << "\",\"deferred_turnin_count\":" << deferredTurninCount
             << ",\"recovery_target_status\":" << (uint32)recoveryStatus
             << ",\"recovery_route_age_seconds\":" << recoveryAgeSeconds
             << ",\"recovery_route_timed_out\":" <<
                ((recoveryPrepareTimedOut || recoveryMovementTimedOut) ? "true" : "false")
             << ",\"recovery_terminal_reason\":\"" <<
                PlayerbotLLMInterface::SanitizeForJson(state.recoveryTerminalReason) << "\""
             << ",\"objective_route_failures\":" << state.objectiveRouteFailures
             << ",\"nearby_reroute_result\":\"" <<
                PlayerbotLLMInterface::SanitizeForJson(state.nearbyRerouteResult) << "\""
             << ",\"turnin_route_quest_id\":" << futureTurninQuestId
             << ",\"turnin_route_outcome\":\"" << PlayerbotLLMInterface::SanitizeForJson(futureTurninOutcome)
             << "\",\"turnin_route_range_count\":" << futureTurninRanges
             << ",\"turnin_route_point_count\":" << futureTurninPoints
             << ",\"recovery_target_bounded\":" << (boundedRecoveryTarget ? "true" : "false")
             << ",\"recovery_prepare_result\":\"" << recoveryPrepareResult << "\""
             << ",\"recovery_move_useful\":" << (recoveryMoveUseful ? "true" : "false")
             << ",\"recovery_move_possible\":" << (recoveryMovePossible ? "true" : "false")
             << ",\"recovery_move_result\":\"" << recoveryMoveResult << "\""
             << ",\"recovery_interaction_result\":\"" << recoveryInteractionResult << "\""
             << ",\"recovery_interaction_attempts\":" << state.recoveryInteractionAttempts
             << ",\"grouped\":" << (bot->GetGroup() ? "true" : "false") << "}";
        if (emitHealthSample)
        {
            samples.push_back(json.str());
            state.travelAdvancedSinceReport = false;
        }
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
        PopulatePublicPetitionVolunteer(bot, speaker, message, candidate);
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

    Player* conversationSpeaker = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, event.speakerGuid));
    uint32 partyId = conversationSpeaker && conversationSpeaker->GetGroup() ?
        conversationSpeaker->GetGroup()->GetId() : 0;
    uint32 speakerGuildId = conversationSpeaker ? conversationSpeaker->GetGuildId() : 0;
    std::string partySessionId = partyId ? "party:" + std::to_string(partyId) :
        speakerGuildId ? "guild:" + std::to_string(speakerGuildId) + ":player:" +
            std::to_string(event.speakerGuid) : "player:" + std::to_string(event.speakerGuid);

    std::ostringstream json;
    json << "{\"event_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.eventId) << "\",";
    json << "\"contract_version\":4,\"message_raw\":\"" << PlayerbotLLMInterface::SanitizeForJson(event.message) << "\",";
    json << "\"event_type\":\"" << (event.ambient ? "ambient" : "message") << "\",";
    json << "\"bridge_capabilities\":{\"reply_channel\":true,\"negotiated_price\":true,\"economic_capabilities\":1,"
         << "\"capability_planner\":2,\"capability_catalog\":\"2.0.0\","
         << "\"stable_party_session\":true,\"typed_action_outcomes\":true},";
    json << "\"party_session_id\":\"" << partySessionId << "\",";
    json << "\"channel\":{\"type\":\"" << event.channelType << "\",\"name\":\""
         << PlayerbotLLMInterface::SanitizeForJson(event.channelName) << "\",\"zone\":" << event.zone
         << ",\"id\":\"" << partySessionId << "\",\"party_session_id\":\"" << partySessionId << "\"},";
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
        json << "]},\"petition_state\":{\"has_charter\":" << (candidate.hasPetition ? "true" : "false")
             << ",\"name\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.petitionName)
             << "\",\"signatures\":" << candidate.petitionSignatures
             << ",\"required_signatures\":" << candidate.petitionRequired
             << ",\"signed_party_members\":[";
        for (size_t signerIndex = 0; signerIndex < candidate.signedPartyMembers.size(); ++signerIndex)
        {
            if (signerIndex) json << ',';
            json << "\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.signedPartyMembers[signerIndex]) << "\"";
        }
        json << "],\"eligible_party_members\":[";
        for (size_t signerIndex = 0; signerIndex < candidate.eligiblePetitionPartyMembers.size(); ++signerIndex)
        {
            if (signerIndex) json << ',';
            json << "\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.eligiblePetitionPartyMembers[signerIndex]) << "\"";
        }
        json << "]},\"volunteer_opportunity\":{\"owner_guid\":" << candidate.volunteerPetitionOwnerGuid
             << ",\"owner_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.volunteerPetitionOwnerName)
             << "\",\"petition_guid\":" << candidate.volunteerPetitionGuid << ",\"charter_name\":\""
             << PlayerbotLLMInterface::SanitizeForJson(candidate.volunteerPetitionName)
             << "\",\"signatures\":" << candidate.volunteerPetitionSignatures
             << ",\"required_signatures\":" << candidate.volunteerPetitionRequired
             << "},\"guild_state\":{\"guild_id\":" << candidate.guildId
             << ",\"guild_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.guildName)
             << "\",\"leader_guid\":" << candidate.guildLeaderGuid
             << ",\"rank\":" << candidate.guildRank
             << ",\"member_count\":" << candidate.guildMemberCount
             << ",\"is_leader\":" << (candidate.isGuildLeader ? "true" : "false")
             << "},\"quests\":[";
        for (size_t questIndex = 0; questIndex < candidate.quests.size(); ++questIndex)
        {
            if (questIndex) json << ',';
            const ChatDirectorQuest& quest = candidate.quests[questIndex];
            AppendQuestJson(json, quest);
        }
        json << "]"
             << ",\"inCombat\":" << (candidate.inCombat ? "true" : "false")
             << ",\"alive\":" << (candidate.alive ? "true" : "false")
             << ",\"ghost\":" << (candidate.ghost ? "true" : "false")
             << ",\"party_assist_state\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.partyAssistState)
             << "\",\"party_assist_reason\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.partyAssistReason)
             << "\",\"dead_recovery_attempts\":" << candidate.deadRecoveryAttempts
             << ",\"dead_recovery_seconds\":" << candidate.deadRecoverySeconds
             << ",\"available\":" << (candidate.available ? "true" : "false");
        uint32 stateRevision = candidate.groupState.groupId ^ (candidate.groupState.leaderGuid << 1) ^
            (candidate.groupState.memberCount << 24) ^ (candidate.inCombat ? 0x40000000 : 0) ^
            (uint32)candidate.actionCapabilities.size() ^ (candidate.petitionSignatures << 8) ^
            (uint32)candidate.eligiblePetitionPartyMembers.size() ^ candidate.guildId ^
            (candidate.guildLeaderGuid << 3) ^ (candidate.guildRank << 16) ^
            candidate.volunteerPetitionOwnerGuid ^ (candidate.volunteerPetitionGuid << 5) ^
            (candidate.volunteerPetitionSignatures << 20);
        json << ",\"state_revision\":" << stateRevision << ",\"action_capabilities\":[";
        bool firstCapability = true;
        for (const ChatDirectorCapability& capability : candidate.actionCapabilities)
        {
            if (!firstCapability) json << ',';
            firstCapability = false;
            std::string family;
            if (capability.type == "report_bag_state" || capability.type == "vendor_bags" ||
                capability.type == "offer_vendor_trip" || capability.type == "repair" ||
                capability.type == "bank_items" || capability.type == "retrieve_mail") family = "vendorInventory";
            else if (capability.type == "meet_player" || capability.type == "travel_to_party" ||
                capability.type == "return_to_activity" || capability.type == "resume_party_assist" ||
                capability.type == "grant_party_free_time" || capability.type == "wait_here" ||
                capability.type == "use_hearthstone") family = "travel";
            else if (capability.type == "transfer_guild_leadership" ||
                capability.type == "solicit_petition_signatures" ||
                capability.type == "perform_emote") family = "socialGovernance";
            else if (capability.type.find("group") != std::string::npos || capability.type == "pass_leadership" ||
                capability.type == "set_party_role" || capability.type == "clear_party_role" ||
                capability.type == "set_puller" || capability.type == "hold_attacks" ||
                capability.type == "resume_assist") family = "grouping";
            else if (capability.type.find("quest") != std::string::npos) family = "quests";
            std::string confirmation = (capability.type == "leave_group" ||
                capability.type == "transfer_guild_leadership" ||
                capability.type == "leave_ai_party_for_player") ? "explicit_confirmation" : "low_risk";
            json << "{\"capability_ref\":\"" << capability.capabilityRef << "\",\"ref\":\""
                 << capability.capabilityRef << "\",\"type\":\"" << capability.type
                 << "\",\"family\":\"" << family << "\",\"confirmation_class\":\"" << confirmation
                 << "\",\"actor_guid\":" << (capability.actorGuid ? capability.actorGuid : candidate.guid)
                 << ",\"target_guid\":" << event.speakerGuid << ",\"party_session_id\":\"" << partySessionId
                 << "\",\"state_revision\":" << stateRevision << ",\"expires_seconds\":90"
                 << ",\"item_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(capability.itemName)
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
        uint32 bagUsage = candidateBot && candidateBot->GetPlayerbotAI() ?
            candidateBot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get() : 0;
        json << "],\"facts\":{\"bag_usage_percent\":" << bagUsage
             << ",\"safe_for_travel\":" << (!candidate.inCombat ? "true" : "false")
             << ",\"current_activity\":\"" << PlayerbotLLMInterface::SanitizeForJson(candidate.currentActivity)
             << "\"},\"party_combat_state\":"
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

    // Group-conflict events are planned asynchronously.  The bot can leave
    // its AI-only party through a newer, authoritative chat action before the
    // older explanation is ready.  Never deliver wording based on that stale
    // group snapshot after membership has changed.
    if (scheduledReply.event.groundingType == "group_invite_conflict")
    {
        std::map<uint32, ChatDirectorCandidate>::const_iterator snapshot =
            scheduledReply.event.candidates.find(scheduledReply.reply.botGuid);
        if (snapshot != scheduledReply.event.candidates.end())
        {
            uint32 currentGroupId = bot->GetGroup() ? bot->GetGroup()->GetId() : 0;
            if (currentGroupId != snapshot->second.groupState.groupId)
            {
                sLog.outDetail("Living WoW stale chat reply suppressed bot=%u event=%s old_group=%u current_group=%u",
                    bot->GetGUIDLow(), scheduledReply.event.eventId.c_str(),
                    snapshot->second.groupState.groupId, currentGroupId);
                return;
            }
        }
    }
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

void PlayerbotChatDirector::ReloadGuildPolicy(std::chrono::steady_clock::time_point now)
{
    if (nextGuildPolicyReload.time_since_epoch().count() && now < nextGuildPolicyReload)
        return;
    nextGuildPolicyReload = now + std::chrono::seconds(60);
    const GuildPolicySnapshot policy = ReadGuildPolicy();
    guildPolicyMode = policy.mode;
    guildRolloutScope = policy.rolloutScope;
    guildCanaryIds = policy.canaryGuildIds;
}

static std::string EscapeGuildAddon(const std::string& value)
{
    std::string result;
    for (std::string::const_iterator i = value.begin(); i != value.end(); ++i)
        result += (*i == '\t' || *i == '\n' || *i == '\r' || *i == '|') ? ' ' : *i;
    return result;
}

static void SendGuildAddon(Player* source, Player* target, const std::string& payload)
{
    if (!source || !target || !target->GetSession())
        return;
    WorldPacket data;
    ChatHandler::BuildChatPacket(data, CHAT_MSG_GUILD, payload.c_str(), LANG_ADDON,
        CHAT_TAG_NONE, source->GetObjectGuid(), source->GetName());
    target->GetSession()->SendPacket(data);
}

static std::vector<std::string> SplitGuildAddon(const std::string& message)
{
    std::vector<std::string> fields;
    size_t start = 0;
    while (start <= message.size())
    {
        const size_t end = message.find('\t', start);
        fields.push_back(message.substr(start, end == std::string::npos ? std::string::npos : end - start));
        if (end == std::string::npos)
            break;
        start = end + 1;
    }
    return fields;
}

static std::string GuildAddonText(const std::string& value, size_t maximum)
{
    std::string result = EscapeGuildAddon(value);
    if (result.size() > maximum)
        result.resize(maximum);
    return result;
}

static bool GuildAddonCoordinator(Player* bot)
{
    if (!bot || !bot->GetGuildId())
        return false;
    uint32 coordinator = 0;
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* candidate = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!candidate || !candidate->IsInWorld() || !candidate->GetSession() ||
            candidate->GetGuildId() != bot->GetGuildId())
            continue;
        if (!coordinator || candidate->GetGUIDLow() < coordinator)
            coordinator = candidate->GetGUIDLow();
    }
    return coordinator == bot->GetGUIDLow();
}

static bool CanManageGuildCalendar(Guild* guild, Player* player)
{
    return guild && player && (guild->GetLeaderGuid() == player->GetObjectGuid() ||
        guild->HasRankRight(player->GetRank(), GR_RIGHT_MODIFY_GUILD_INFO));
}

static void SendSeasonalCalendar(Player* source, Player* receiver, uint32 rangeStart, uint32 rangeEnd)
{
    if (!source || !receiver || rangeEnd <= rangeStart || rangeEnd - rangeStart > 370 * DAY)
        return;
    const GameEventMgr::GameEventDataMap& events = sGameEventMgr.GetEventMap();
    uint32 sent = 0;
    for (uint32 eventId = 1; eventId < events.size() && sent < 64; ++eventId)
    {
        const GameEventData& item = events[eventId];
        const bool seasonal = item.holiday_id != HOLIDAY_NONE ||
            item.scheduleType == GAME_EVENT_SCHEDULE_YEARLY ||
            (item.scheduleType >= GAME_EVENT_SCHEDULE_DMF_1 && item.scheduleType <= GAME_EVENT_SCHEDULE_DMF_BUILDING_STAGE_2_3) ||
            item.scheduleType == GAME_EVENT_SCHEDULE_LUNAR_NEW_YEAR ||
            item.scheduleType == GAME_EVENT_SCHEDULE_EASTER;
        if (!seasonal || !item.isValid() || item.description.empty() || !item.occurence || !item.length)
            continue;
        const int64 period = int64(item.occurence) * MINUTE;
        const int64 duration = int64(item.length) * MINUTE;
        int64 occurrence = int64(item.start);
        if (occurrence + duration < rangeStart)
        {
            const int64 difference = int64(rangeStart) - occurrence - duration;
            occurrence += ((difference / period) + 1) * period;
        }
        while (occurrence < rangeEnd && occurrence <= int64(item.end) && sent < 64)
        {
            const int64 occurrenceEnd = std::min<int64>(occurrence + duration, int64(item.end));
            if (occurrenceEnd >= rangeStart)
            {
                std::ostringstream payload;
                payload << "LWOWG1\tSEA\tworld-" << eventId << '-' << occurrence << '\t'
                    << occurrence << '\t' << occurrenceEnd << '\t'
                    << GuildAddonText(item.description, 100);
                SendGuildAddon(source, receiver, payload.str());
                ++sent;
            }
            occurrence += period;
        }
    }
}

static bool SafeGuildWireId(const std::string& value, size_t maximum);

void PlayerbotChatDirector::SendGuildAddonSnapshot(Player* source, Player* receiver)
{
    if (!source || !receiver || !source->GetGuildId() || source->GetGuildId() != receiver->GetGuildId())
        return;
    Guild* guild = sGuildMgr.GetGuildById(source->GetGuildId());
    if (!guild)
        return;
    const uint32 revision = uint32(time(nullptr));
    std::ostringstream snapshot;
    snapshot << "LWOWG1\tSNAP\t" << revision << '\t' << GuildAddonText(guild->GetName(), 48)
        << '\t' << GuildFocus(guild->GetId(), 0) << '\t' << GuildFocus(guild->GetId(), 1)
        << '\t' << (guildPolicyMode == "active" ? "active guild society" : "guild society observation")
        << '\t' << (CanManageGuildCalendar(guild, receiver) ? 1 : 0);
    SendGuildAddon(source, receiver, snapshot.str());
    std::string leaderName;
    sObjectMgr.GetPlayerNameByGUID(guild->GetLeaderGuid(), leaderName);
    std::ostringstream officer;
    officer << "LWOWG1\tOFF\t" << revision << '\t' << EscapeGuildAddon(leaderName) << "\tguild master";
    SendGuildAddon(source, receiver, officer.str());

    auto officers = CharacterDatabase.PQuery(
        "SELECT character_guid,duty FROM guild_society_officer WHERE guild_id=%u AND state='active' ORDER BY duty LIMIT 8",
        guild->GetId());
    if (officers)
    {
        do
        {
            Field* fields = officers->Fetch();
            std::string name;
            sObjectMgr.GetPlayerNameByGUID(ObjectGuid(HIGHGUID_PLAYER, fields[0].GetUInt32()), name);
            if (name.empty() || name == leaderName)
                continue;
            std::ostringstream payload;
            payload << "LWOWG1\tOFF\t" << revision << '\t' << GuildAddonText(name, 32)
                << '\t' << GuildAddonText(fields[1].GetString(), 32);
            SendGuildAddon(source, receiver, payload.str());
        }
        while (officers->NextRow());
    }

    const uint32 nowEpoch = uint32(time(nullptr));
    auto scheduled = CharacterDatabase.PQuery(
        "SELECT event_id,scheduled_at,state,event_type,title,minimum_members,maximum_members,tank_slots,healer_slots,damage_slots,"
        "IFNULL(ends_at,0),organizer_guid,details FROM guild_society_event WHERE guild_id=%u "
        "AND scheduled_at BETWEEN %u AND %u ORDER BY scheduled_at LIMIT 40",
        guild->GetId(), nowEpoch > 30 * DAY ? nowEpoch - 30 * DAY : 0, nowEpoch + 370 * DAY);
    if (scheduled)
    {
        do
        {
            Field* fields = scheduled->Fetch();
            const std::string eventId = fields[0].GetString();
            std::string organizer;
            sObjectMgr.GetPlayerNameByGUID(ObjectGuid(HIGHGUID_PLAYER, fields[11].GetUInt32()), organizer);
            const std::string details = fields[12].GetString();
            std::ostringstream needs;
            if (fields[7].GetUInt32() || fields[8].GetUInt32() || fields[9].GetUInt32())
                needs << fields[7].GetUInt32() << " tank, " << fields[8].GetUInt32() << " healer, "
                    << fields[9].GetUInt32() << " damage";
            else if (fields[5].GetUInt32() > 1)
                needs << fields[5].GetUInt32() << '-' << fields[6].GetUInt32() << " members";
            std::ostringstream payload;
            payload << "LWOWG1\tEVT\t" << revision << '\t' << GuildAddonText(eventId, 64) << '\t'
                << fields[1].GetUInt32() << '\t' << GuildAddonText(fields[2].GetString(), 20) << '\t'
                << GuildAddonText(fields[3].GetString(), 16) << '\t' << GuildAddonText(fields[4].GetString(), 40)
                << '\t' << GuildAddonText(needs.str(), 24) << '\t' << fields[10].GetUInt32() << '\t'
                << GuildAddonText(organizer, 20) << '\t';
            SendGuildAddon(source, receiver, payload.str());
            if (!details.empty())
            {
                std::ostringstream note;
                note << "LWOWG1\tNOTE\t" << revision << '\t' << GuildAddonText(eventId, 64)
                    << '\t' << GuildAddonText(details, 140);
                SendGuildAddon(source, receiver, note.str());
            }
        }
        while (scheduled->NextRow());
    }

    auto rsvps = CharacterDatabase.PQuery(
        "SELECT r.event_id,c.name,r.response,r.role FROM guild_society_rsvp r "
        "JOIN guild_society_event e ON e.event_id=r.event_id JOIN characters c ON c.guid=r.character_guid "
        "WHERE e.guild_id=%u ORDER BY e.scheduled_at,r.response,c.name LIMIT 120", guild->GetId());
    if (rsvps)
    {
        do
        {
            Field* fields = rsvps->Fetch();
            std::ostringstream payload;
            payload << "LWOWG1\tATT\t" << revision << '\t' << GuildAddonText(fields[0].GetString(), 64)
                << '\t' << GuildAddonText(fields[1].GetString(), 32) << '\t'
                << GuildAddonText(fields[2].GetString(), 16) << '\t' << GuildAddonText(fields[3].GetString(), 16);
            SendGuildAddon(source, receiver, payload.str());
        }
        while (rsvps->NextRow());
    }

    SendSeasonalCalendar(source, receiver, nowEpoch > 7 * DAY ? nowEpoch - 7 * DAY : 0, nowEpoch + 370 * DAY);
}

bool PlayerbotChatDirector::HandleGuildAddonMessage(Player* receiverBot, Player* sender, const std::string& message)
{
    if (message.find("LWOWG1\t") != 0 || !receiverBot || !sender || !sender->isRealPlayer() ||
        !receiverBot->GetGuildId() || receiverBot->GetGuildId() != sender->GetGuildId())
        return false;
    if (!GuildAddonCoordinator(receiverBot))
        return true;
    guildAddonClients.insert(sender->GetGUIDLow());
    ReloadGuildPolicy(std::chrono::steady_clock::now());
    Guild* guild = sGuildMgr.GetGuildById(sender->GetGuildId());
    if (!guild)
        return true;
    const std::vector<std::string> fields = SplitGuildAddon(message);
    const auto notifyCalendarClients = [&]()
    {
        for (uint32 guid : guildAddonClients)
        {
            Player* client = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, guid));
            if (client && client->GetGuildId() == guild->GetId())
                SendGuildAddon(receiverBot, client, "LWOWG1\tPUSH\tGuild calendar updated.");
        }
    };
    if (message.find("LWOWG1\tHELLO") == 0 || message.find("LWOWG1\tGET") == 0)
        SendGuildAddonSnapshot(receiverBot, sender);
    else if (fields.size() >= 5 && fields[1] == "RSVP")
    {
        const std::string eventId = fields[3];
        const std::string response = fields[4];
        if (!SafeGuildWireId(eventId, 64) ||
            (response != "accepted" && response != "tentative" && response != "declined"))
        {
            SendGuildAddon(receiverBot, sender, "LWOWG1\tERR\t0\tThat RSVP is not valid.");
            return true;
        }
        auto event = CharacterDatabase.PQuery(
            "SELECT event_id FROM guild_society_event WHERE event_id='%s' AND guild_id=%u "
            "AND state IN ('draft','announced','forming') LIMIT 1", eventId.c_str(), guild->GetId());
        if (!event)
        {
            SendGuildAddon(receiverBot, sender, "LWOWG1\tERR\t0\tThat guild event is no longer accepting RSVPs.");
            return true;
        }
        const uint32 nowEpoch = uint32(time(nullptr));
        CharacterDatabase.PExecute(
            "INSERT INTO guild_society_rsvp (event_id,character_guid,response,role,human,updated_at) "
            "VALUES ('%s',%u,'%s','',1,%u) ON DUPLICATE KEY UPDATE response=VALUES(response),human=1,updated_at=VALUES(updated_at)",
            eventId.c_str(), sender->GetGUIDLow(), response.c_str(), nowEpoch);
        SendGuildAddon(receiverBot, sender, "LWOWG1\tACK\t0\tYour RSVP was saved.");
        notifyCalendarClients();
    }
    else if (fields.size() >= 8 && fields[1] == "CREATE")
    {
        if (guildPolicyMode != "active" || !CanManageGuildCalendar(guild, sender))
        {
            SendGuildAddon(receiverBot, sender, "LWOWG1\tERR\t0\tOnly the guild master or an authorized officer can add guild events.");
            return true;
        }
        std::string title = fields[3], eventType = fields[4], details = fields[7];
        const uint32 starts = uint32(std::strtoul(fields[5].c_str(), nullptr, 10));
        const uint32 ends = uint32(std::strtoul(fields[6].c_str(), nullptr, 10));
        const uint32 nowEpoch = uint32(time(nullptr));
        const bool allowedType = eventType == "social" || eventType == "quest" || eventType == "dungeon" ||
            eventType == "supply" || eventType == "leveling";
        if (title.empty() || title.size() > 80 || details.size() > 80 || !allowedType ||
            starts + 3600 < nowEpoch || starts > nowEpoch + 370 * DAY || ends < starts + 30 * MINUTE || ends > starts + 7 * DAY)
        {
            SendGuildAddon(receiverBot, sender, "LWOWG1\tERR\t0\tThat guild event has an invalid name, type, date, or duration.");
            return true;
        }
        title = EscapeGuildAddon(title); details = EscapeGuildAddon(details);
        CharacterDatabase.escape_string(title); CharacterDatabase.escape_string(details);
        std::ostringstream eventId;
        eventId << "calendar-" << guild->GetId() << '-' << sender->GetGUIDLow() << '-' << starts;
        const uint32 minimum = eventType == "dungeon" ? 5 : 1;
        const uint32 maximum = eventType == "dungeon" || eventType == "quest" || eventType == "leveling" ? 5 : 40;
        CharacterDatabase.PExecute(
            "INSERT INTO guild_society_event (event_id,guild_id,event_type,state,title,details,target_id,organizer_guid,scheduled_at,ends_at,"
            "minimum_members,maximum_members,tank_slots,healer_slots,damage_slots,failure_reason,created_at,updated_at) "
            "VALUES ('%s',%u,'%s','announced','%s','%s',0,%u,%u,%u,%u,%u,%u,%u,%u,'',%u,%u) "
            "ON DUPLICATE KEY UPDATE title=VALUES(title),details=VALUES(details),event_type=VALUES(event_type),ends_at=VALUES(ends_at),updated_at=VALUES(updated_at)",
            eventId.str().c_str(), guild->GetId(), eventType.c_str(), title.c_str(), details.c_str(), sender->GetGUIDLow(),
            starts, ends, minimum, maximum, eventType == "dungeon" ? 1 : 0, eventType == "dungeon" ? 1 : 0,
            eventType == "dungeon" ? 3 : 0, nowEpoch, nowEpoch);
        SendGuildAddon(receiverBot, sender, "LWOWG1\tACK\t0\tGuild event added to the shared calendar.");
        notifyCalendarClients();
    }
    else if (fields.size() >= 5 && fields[1] == "CALENDAR")
    {
        const uint32 starts = uint32(std::strtoul(fields[3].c_str(), nullptr, 10));
        const uint32 ends = uint32(std::strtoul(fields[4].c_str(), nullptr, 10));
        SendSeasonalCalendar(receiverBot, sender, starts, ends);
    }
    return true;
}

static bool GuildGroupHasRealPlayer(Player* bot)
{
    Group* group = bot ? bot->GetGroup() : nullptr;
    if (!group)
        return false;
    for (GroupReference* member = group->GetFirstMember(); member; member = member->next())
    {
        Player* player = member->getSource();
        if (player && player->isRealPlayer())
            return true;
    }
    return false;
}

static bool SafeGuildEventParticipant(Player* bot, uint32 guildId)
{
    return bot && bot->GetPlayerbotAI() && bot->IsInWorld() && bot->GetSession() &&
        bot->GetGuildId() == guildId && bot->IsAlive() && !bot->IsInCombat() &&
        !bot->IsBeingTeleported() && !bot->IsTaxiFlying() && !bot->GetTransport() &&
        !bot->InBattleGround() && !bot->GetPlayerbotAI()->HasRealPlayerMaster() &&
        !GuildGroupHasRealPlayer(bot);
}

static bool SafeGuildWireId(const std::string& value, size_t maximum)
{
    return !value.empty() && value.size() <= maximum &&
        std::regex_match(value, std::regex("[A-Za-z0-9:_-]+"));
}

static uint32 GuildEventGroupSize(Player* organizer)
{
    Group* group = organizer ? organizer->GetGroup() : nullptr;
    if (!group)
        return 0;
    uint32 members = 0;
    for (GroupReference* reference = group->GetFirstMember(); reference; reference = reference->next())
    {
        Player* member = reference->getSource();
        if (member && member->IsInWorld() && member->GetSession())
            ++members;
    }
    return members;
}

void PlayerbotChatDirector::UpdateGuildEventLifecycle(std::chrono::steady_clock::time_point now)
{
    if (nextGuildLifecycleUpdate.time_since_epoch().count() && now < nextGuildLifecycleUpdate)
        return;
    nextGuildLifecycleUpdate = now + std::chrono::seconds(10);
    if (guildPolicyMode != "active")
        return;

    auto events = CharacterDatabase.PQuery(
        "SELECT event_id,guild_id,event_type,state,title,organizer_guid,scheduled_at,minimum_members,"
        "maximum_members,tank_slots,healer_slots,damage_slots,created_at FROM guild_society_event "
        "WHERE state IN ('forming','traveling','active') ORDER BY created_at LIMIT 24");
    if (!events)
        return;

    const uint32 nowEpoch = uint32(time(nullptr));
    do
    {
        Field* fields = events->Fetch();
        const std::string eventId = fields[0].GetString();
        const uint32 guildId = fields[1].GetUInt32();
        const std::string eventType = fields[2].GetString();
        const std::string state = fields[3].GetString();
        const std::string title = fields[4].GetString();
        const uint32 organizerGuid = fields[5].GetUInt32();
        const uint32 scheduledAt = fields[6].GetUInt32();
        const uint32 minimumMembers = std::max<uint32>(1, fields[7].GetUInt32());
        const uint32 maximumMembers = std::max<uint32>(minimumMembers, fields[8].GetUInt32());
        const uint32 tankSlots = fields[9].GetUInt32();
        const uint32 healerSlots = fields[10].GetUInt32();
        const uint32 damageSlots = fields[11].GetUInt32();
        const uint32 createdAt = fields[12].GetUInt32();
        if (!SafeGuildWireId(eventId, 100) ||
            !GuildExecutionEnabled(guildPolicyMode, guildRolloutScope, guildCanaryIds, guildId))
            continue;

        Player* organizer = sRandomPlayerbotMgr.GetPlayerBot(organizerGuid);
        const uint32 groupSize = GuildEventGroupSize(organizer);
        const uint32 age = nowEpoch > createdAt ? nowEpoch - createdAt : 0;
        std::string nextState, failureReason;
        if (state == "forming" || state == "traveling")
        {
            if (groupSize >= minimumMembers)
                nextState = "active";
            else if (age >= 300)
            {
                nextState = "failed";
                failureReason = "formation_timeout";
            }
        }
        else if (state == "active")
        {
            if (groupSize < minimumMembers)
            {
                nextState = age >= 300 ? "completed" : "failed";
                if (nextState == "failed")
                    failureReason = "group_disbanded_early";
            }
            else if (age >= 1800)
                nextState = "completed";
        }
        if (nextState.empty())
            continue;

        const bool terminal = nextState == "completed" || nextState == "failed";
        const std::string endsAt = terminal ? std::to_string(nowEpoch) : "NULL";
        CharacterDatabase.PExecute(
            "UPDATE guild_society_event SET state='%s',failure_reason='%s',ends_at=%s,updated_at=%u "
            "WHERE event_id='%s' AND state='%s'", nextState.c_str(), failureReason.c_str(),
            endsAt.c_str(), nowEpoch, eventId.c_str(), state.c_str());

        const std::string safeType = PlayerbotLLMInterface::SanitizeForJson(eventType);
        const std::string safeTitle = PlayerbotLLMInterface::SanitizeForJson(title);
        std::ostringstream telemetry;
        telemetry << "{\"events\":[{\"event_id\":\"lifecycle-" << eventId << '-' << nowEpoch
            << "\",\"type\":\"guild_event\",\"guild_event_id\":\"" << eventId
            << "\",\"guild_id\":" << guildId << ",\"event_type\":\"" << safeType
            << "\",\"title\":\"" << safeTitle << "\",\"scheduled_at\":" << scheduledAt
            << ",\"ends_at\":" << (terminal ? nowEpoch : 0)
            << ",\"state\":\"" << nextState << "\",\"organizer_guid\":" << organizerGuid
            << ",\"minimum_members\":" << minimumMembers << ",\"maximum_members\":" << maximumMembers
            << ",\"tank_slots\":" << tankSlots << ",\"healer_slots\":" << healerSlots
            << ",\"damage_slots\":" << damageSlots << ",\"failure_reason\":\"" << failureReason << "\"}]}";
        const std::string body = telemetry.str();
        std::thread([body]()
        {
            std::vector<std::string> debug;
            PlayerbotLLMInterface::Generate(body, 9, 1000000, debug, true, "/v2/guilds/events");
        }).detach();
    }
    while (events->NextRow());
}

void PlayerbotChatDirector::ApplyGuildPlans(const std::string& response,
    std::chrono::steady_clock::time_point /*now*/)
{
    if (response.empty() || guildPolicyMode != "active")
        return;
    boost::property_tree::ptree root;
    std::istringstream input(response);
    try { boost::property_tree::read_json(input, root); }
    catch (...) { return; }
    auto decisions = root.get_child_optional("decisions");
    if (!decisions)
        return;
    for (const auto& child : *decisions)
    {
        const uint32 guildId = child.second.get<uint32>("guild_id", 0);
        const std::string decisionId = child.second.get<std::string>("decision_id", "");
        const std::string candidateId = child.second.get<std::string>("candidate_id", "");
        const std::string decisionType = child.second.get<std::string>("decision_type", "");
        const std::string source = child.second.get<std::string>("source", "deterministic_fallback");
        const bool gatewayAllowed = child.second.get<bool>("execution_allowed", false);
        const bool worldAllowed = GuildExecutionEnabled(
            guildPolicyMode, guildRolloutScope, guildCanaryIds, guildId);
        if (!guildId || !gatewayAllowed || !worldAllowed ||
            !SafeGuildWireId(decisionId, 64) || !SafeGuildWireId(candidateId, 100) ||
            !SafeGuildWireId(decisionType, 64) || !SafeGuildWireId(source, 32))
            continue;
        if (CharacterDatabase.PQuery(
                "SELECT decision_id FROM guild_society_decision WHERE decision_id='%s' LIMIT 1", decisionId.c_str()))
            continue;
        Guild* guild = sGuildMgr.GetGuildById(guildId);
        const uint32 leaderAccount = guild ? sObjectMgr.GetPlayerAccountIdByGUID(guild->GetLeaderGuid()) : 0;
        if (!guild || !sPlayerbotAIConfig.IsInRandomAccountList(leaderAccount))
            continue;

        const uint32 decisionEpoch = uint32(time(nullptr));
        auto activeEvent = CharacterDatabase.PQuery(
            "SELECT event_id FROM guild_society_event WHERE guild_id=%u "
            "AND state IN ('announced','forming','traveling','active') LIMIT 1", guildId);
        if (activeEvent)
        {
            CharacterDatabase.PExecute(
                "INSERT INTO guild_society_decision (decision_id,guild_id,decision_type,candidate_id,state,source,rejection_code,created_at,updated_at) "
                "VALUES ('%s',%u,'%s','%s','rejected','%s','active_event_in_progress',%u,%u)",
                decisionId.c_str(), guildId, decisionType.c_str(), candidateId.c_str(), source.c_str(),
                decisionEpoch, decisionEpoch);
            continue;
        }

        const bool groupEvent = decisionType == "schedule_quest_group" ||
            decisionType == "schedule_leveling_group" || decisionType == "schedule_dungeon";
        std::string state = "rejected", rejection = groupEvent ? "no_safe_roster" : "executor_not_available";
        std::string eventState = "failed", eventType, title;
        uint32 organizerGuid = 0, accepted = 0;
        if (groupEvent)
        {
            std::vector<Player*> eligible;
            Player* leader = sRandomPlayerbotMgr.GetPlayerBot(guild->GetLeaderGuid().GetCounter());
            if (SafeGuildEventParticipant(leader, guildId))
                eligible.push_back(leader);
            for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
            {
                Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
                if (!SafeGuildEventParticipant(bot, guildId) || bot == leader)
                    continue;
                eligible.push_back(bot);
            }
            std::vector<Player*> roster;
            auto addUnique = [&roster](Player* bot)
            {
                if (bot && std::find(roster.begin(), roster.end(), bot) == roster.end())
                    roster.push_back(bot);
            };
            const uint32 minimum = decisionType == "schedule_dungeon" ? 5 : 2;
            if (decisionType == "schedule_dungeon")
            {
                // Do not take the first five online members and then discover
                // that they have no healer. Build the authoritative roster by
                // role before any existing AI-only groups are disturbed.
                for (Player* bot : eligible)
                    if (PlayerbotAI::IsTank(bot, false)) { addUnique(bot); break; }
                for (Player* bot : eligible)
                    if (PlayerbotAI::IsHeal(bot, false) &&
                        std::find(roster.begin(), roster.end(), bot) == roster.end())
                    { addUnique(bot); break; }
                for (Player* bot : eligible)
                {
                    addUnique(bot);
                    if (roster.size() >= 5) break;
                }
            }
            else
                for (Player* bot : eligible)
                {
                    addUnique(bot);
                    if (roster.size() >= 5) break;
                }
            uint32 tanks = 0, healers = 0;
            for (Player* bot : roster)
            {
                if (PlayerbotAI::IsTank(bot, false)) ++tanks;
                if (PlayerbotAI::IsHeal(bot, false)) ++healers;
            }
            bool rolesReady = decisionType != "schedule_dungeon" || (tanks > 0 && healers > 0);
            if (roster.size() >= minimum && rolesReady)
            {
                // Guild events may reclaim bots only from AI-only groups; the
                // safety predicate above has already excluded every group with
                // a real player. Release the full selected roster first so an
                // organizer that was a nonleader cannot issue doomed invites.
                bool released = true;
                for (Player* member : roster)
                {
                    if (!member->GetGroup()) continue;
                    if (!member->GetPlayerbotAI()->DoSpecificAction(
                            "leave", Event("guild society event", "", member), true) && member->GetGroup())
                        released = false;
                }
                Player* organizer = roster.front();
                organizerGuid = organizer->GetGUIDLow();
                accepted = released && !organizer->GetGroup() ? 1 : 0;
                for (size_t index = 1; released && index < roster.size(); ++index)
                {
                    Player* member = roster[index];
                    if (member->GetGroup() == organizer->GetGroup() && organizer->GetGroup())
                    {
                        ++accepted;
                        continue;
                    }
                    if (member->GetPlayerbotAI()->DoSpecificAction(
                            "join", Event("create group", "", organizer), true))
                        ++accepted;
                }
                if (accepted >= minimum)
                {
                    state = "completed";
                    rejection.clear();
                    eventState = "forming";
                }
                else
                    rejection = "group_formation_failed";
            }
            eventType = decisionType == "schedule_dungeon" ? "dungeon" :
                decisionType == "schedule_quest_group" ? "quest" : "leveling";
            title = decisionType == "schedule_dungeon" ? "Guild dungeon group" :
                decisionType == "schedule_quest_group" ? "Guild quest group" : "Guild leveling group";
        }
        const uint32 nowEpoch = uint32(time(nullptr));
        CharacterDatabase.PExecute(
            "INSERT INTO guild_society_decision (decision_id,guild_id,decision_type,candidate_id,state,source,rejection_code,created_at,updated_at) "
            "VALUES ('%s',%u,'%s','%s','%s','%s','%s',%u,%u)", decisionId.c_str(), guildId,
            decisionType.c_str(), candidateId.c_str(), state.c_str(), source.c_str(), rejection.c_str(), nowEpoch, nowEpoch);
        if (!groupEvent)
            continue;
        const std::string eventId = "society-" + std::to_string(guildId) + "-" + std::to_string(nowEpoch);
        CharacterDatabase.PExecute(
            "INSERT INTO guild_society_event (event_id,guild_id,event_type,state,title,target_id,organizer_guid,scheduled_at,minimum_members,maximum_members,tank_slots,healer_slots,damage_slots,failure_reason,created_at,updated_at) "
            "VALUES ('%s',%u,'%s','%s','%s',0,%u,%u,%u,5,%u,%u,%u,'%s',%u,%u) "
            "ON DUPLICATE KEY UPDATE state=VALUES(state),organizer_guid=VALUES(organizer_guid),failure_reason=VALUES(failure_reason),updated_at=VALUES(updated_at)",
            eventId.c_str(), guildId, eventType.c_str(), eventState.c_str(), title.c_str(), organizerGuid,
            nowEpoch, decisionType == "schedule_dungeon" ? 5 : 2,
            decisionType == "schedule_dungeon" ? 1 : 0, decisionType == "schedule_dungeon" ? 1 : 0,
            decisionType == "schedule_dungeon" ? 3 : 0, rejection.c_str(), nowEpoch, nowEpoch);
        std::ostringstream telemetry;
        telemetry << "{\"events\":[{\"event_id\":\"execution-" << decisionId
            << "\",\"type\":\"guild_event\",\"guild_event_id\":\"" << eventId
            << "\",\"guild_id\":" << guildId << ",\"event_type\":\"" << eventType
            << "\",\"title\":\"" << title << "\",\"scheduled_at\":" << nowEpoch
            << ",\"state\":\"" << eventState << "\",\"organizer_guid\":" << organizerGuid
            << ",\"minimum_members\":" << (decisionType == "schedule_dungeon" ? 5 : 2)
            << ",\"maximum_members\":5,\"tank_slots\":" << (decisionType == "schedule_dungeon" ? 1 : 0)
            << ",\"healer_slots\":" << (decisionType == "schedule_dungeon" ? 1 : 0)
            << ",\"damage_slots\":" << (decisionType == "schedule_dungeon" ? 3 : 0)
            << ",\"failure_reason\":\"" << rejection << "\"}]}";
        const std::string body = telemetry.str();
        std::thread([body]()
        {
            std::vector<std::string> debug;
            PlayerbotLLMInterface::Generate(body, 9, 1000000, debug, true, "/v2/guilds/events");
        }).detach();
    }
}

void PlayerbotChatDirector::MaybeReportGuildSocieties(std::chrono::steady_clock::time_point now)
{
    ReloadGuildPolicy(now);
    UpdateGuildEventLifecycle(now);
    if (pendingGuildPlans.valid() && pendingGuildPlans.wait_for(std::chrono::seconds(0)) == std::future_status::ready)
        ApplyGuildPlans(pendingGuildPlans.get(), now);
    if (guildPolicyMode == "off")
        return;
    if (pendingGuildPlans.valid())
        return;
    if (nextGuildSample.time_since_epoch().count() && now < nextGuildSample)
        return;
    nextGuildSample = now + std::chrono::minutes(15);

    // GetPlayers() is only the legacy manager-owned subset. The GUID list is
    // the authoritative population used by progression and organic economy.
    std::map<uint32, Player*> representatives;
    std::map<uint32, uint32> onlineMembers, totalLevels, maximumLevels;
    std::map<uint32, uint32> dungeonReady, tankCandidates, healerCandidates, damageCandidates;
    for (uint32 guid : sRandomPlayerbotMgr.GetChatBotGuids())
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(guid);
        if (!bot || !bot->IsInWorld() || !bot->GetGuildId() || !bot->GetSession() ||
            !sPlayerbotAIConfig.IsInRandomAccountList(bot->GetSession()->GetAccountId()))
            continue;
        representatives.insert(std::make_pair(bot->GetGuildId(), bot));
        const uint32 guildId = bot->GetGuildId();
        ++onlineMembers[guildId];
        totalLevels[guildId] += bot->GetLevel();
        maximumLevels[guildId] = std::max<uint32>(maximumLevels[guildId], bot->GetLevel());
        if (bot->GetLevel() >= 10)
        {
            ++dungeonReady[guildId];
            switch (bot->getClass())
            {
                case CLASS_WARRIOR: case CLASS_PALADIN: case CLASS_DRUID: ++tankCandidates[guildId]; break;
                default: break;
            }
            switch (bot->getClass())
            {
                case CLASS_PRIEST: case CLASS_DRUID: case CLASS_SHAMAN: case CLASS_PALADIN: ++healerCandidates[guildId]; break;
                default: break;
            }
            ++damageCandidates[guildId];
        }
    }
    // Random bots finish logging in asynchronously after realm startup. An
    // empty first pass is not a valid fifteen-minute observation sample.
    if (representatives.empty())
    {
        nextGuildSample = now + std::chrono::minutes(1);
        return;
    }

    std::ostringstream enrich, plans, events;
    enrich << "{\"guilds\":[";
    plans << "{\"guilds\":[";
    events << "{\"effective_policy\":{\"schemaVersion\":1,\"mode\":\"" << guildPolicyMode
        << "\",\"rollout\":{\"scope\":\"" << guildRolloutScope << "\",\"canaryGuildIds\":[";
    bool firstCanary = true;
    for (uint32 guildId : guildCanaryIds)
    {
        if (!firstCanary) events << ',';
        firstCanary = false;
        events << guildId;
    }
    events << "]}},\"events\":[";
    bool first = true;
    const uint32 nowEpoch = uint32(time(nullptr));
    for (const auto& entry : representatives)
    {
        const uint32 guildId = entry.first;
        Player* representative = entry.second;
        Guild* guild = sGuildMgr.GetGuildById(guildId);
        if (!guild)
            continue;
        const uint32 leaderAccount = sObjectMgr.GetPlayerAccountIdByGUID(guild->GetLeaderGuid());
        const bool botLed = sPlayerbotAIConfig.IsInRandomAccountList(leaderAccount);
        std::string leaderName;
        sObjectMgr.GetPlayerNameByGUID(guild->GetLeaderGuid(), leaderName);
        const uint32 members = guild->GetMemberSize();
        const char* faction = representative->GetTeam() == ALLIANCE ? "alliance" : "horde";
        const char* band = members <= 20 ? "small" : members <= 45 ? "medium" : "large";
        const uint32 target = members <= 20 ? 10 + guildId % 11 : members <= 45 ? 21 + guildId % 25 : 46 + guildId % 35;
        const uint32 online = onlineMembers[guildId];
        const uint32 averageLevel = online ? totalLevels[guildId] / online : 0;
        const bool dungeonEligible = dungeonReady[guildId] >= 5 &&
            tankCandidates[guildId] > 0 && healerCandidates[guildId] > 0;
        const uint32 recruitmentGap = target > members ? target - members : 0;
        const bool executionEnabled = GuildExecutionEnabled(
            guildPolicyMode, guildRolloutScope, guildCanaryIds, guildId);
        const std::string primary = GuildFocus(guildId, 0), secondary = GuildFocus(guildId, 1);
        const std::string name = PlayerbotLLMInterface::SanitizeForJson(guild->GetName());
        const std::string leader = PlayerbotLLMInterface::SanitizeForJson(leaderName);
        if (!first)
        {
            enrich << ',';
            plans << ',';
            events << ',';
        }
        first = false;
        enrich << "{\"guild_id\":" << guildId << ",\"guild_name\":\"" << name
            << "\",\"bot_led\":" << (botLed ? "true" : "false") << ",\"faction\":\"" << faction
            << "\",\"leader_guid\":" << guild->GetLeaderGuid().GetCounter() << ",\"leader_name\":\"" << leader
            << "\",\"member_count\":" << members
            << ",\"size_band\":\"" << band << "\",\"target_size\":" << target
            << ",\"primary_focus\":\"" << primary << "\",\"secondary_focus\":\"" << secondary << "\""
            << ",\"identity_candidates\":{\"culture\":[\"friendly and dependable\",\"adventurous and helpful\"],"
               "\"motto\":[\"No one adventures alone\",\"Prepared for the road ahead\"],"
               "\"recruitment_style\":[\"welcoming\",\"organized but relaxed\"]}}";
        plans << "{\"guild_id\":" << guildId << ",\"bot_led\":" << (botLed ? "true" : "false")
            << ",\"online_members\":" << online << ",\"average_level\":" << averageLevel
            << ",\"maximum_level\":" << maximumLevels[guildId]
            << ",\"dungeon_ready_members\":" << dungeonReady[guildId]
            << ",\"tank_candidates\":" << tankCandidates[guildId]
            << ",\"healer_candidates\":" << healerCandidates[guildId]
            << ",\"damage_candidates\":" << damageCandidates[guildId]
            << ",\"candidate_decisions\":[{\"candidate_id\":\"quest:" << guildId
            << ":" << averageLevel << "\",\"type\":\"schedule_quest_group\",\"utility\":20,"
               "\"eligible\":" << (online >= 2 ? "true" : "false") << "}"
            << ",{\"candidate_id\":\"leveling:" << guildId << ":" << averageLevel
            << "\",\"type\":\"schedule_leveling_group\",\"utility\":" << (averageLevel < 15 ? 24 : 16)
            << ",\"eligible\":" << (online >= 2 ? "true" : "false") << "}"
            << ",{\"candidate_id\":\"dungeon:" << guildId << ":" << dungeonReady[guildId]
            << "\",\"type\":\"schedule_dungeon\",\"utility\":25,\"eligible\":"
            << (dungeonEligible ? "true" : "false") << "}"
            << ",{\"candidate_id\":\"recruit:" << guildId << ":" << recruitmentGap
            << "\",\"type\":\"recruit_members\",\"utility\":" << (18 + std::min<uint32>(20, recruitmentGap))
            << ",\"eligible\":" << (recruitmentGap ? "true" : "false") << "}"
            << ",{\"candidate_id\":\"officers:" << guildId << ":" << members
            << "\",\"type\":\"review_officer_coverage\",\"utility\":12,\"eligible\":"
            << (members >= 10 ? "true" : "false") << "}]}";
        events << "{\"event_id\":\"snapshot-" << guildId << '-' << nowEpoch
            << "\",\"type\":\"guild_snapshot\",\"guild_id\":" << guildId << ",\"guild_name\":\"" << name
            << "\",\"bot_led\":" << (botLed ? "true" : "false") << ",\"faction\":\"" << faction
            << "\",\"leader_guid\":" << guild->GetLeaderGuid().GetCounter() << ",\"leader_name\":\"" << leader
            << "\",\"member_count\":" << members << ",\"size_band\":\"" << band
            << "\",\"target_size\":" << target << ",\"primary_focus\":\"" << primary
            << "\",\"secondary_focus\":\"" << secondary << "\",\"state\":\""
            << (executionEnabled ? "active" : "observed")
            << "\",\"online_members\":" << online << ",\"average_level\":" << averageLevel
            << ",\"maximum_level\":" << maximumLevels[guildId]
            << ",\"dungeon_ready_members\":" << dungeonReady[guildId]
            << ",\"tank_candidates\":" << tankCandidates[guildId]
            << ",\"healer_candidates\":" << healerCandidates[guildId] << "}";

        CharacterDatabase.PExecute(
            "INSERT INTO guild_society_profile (guild_id,bot_led,faction,leader_guid,size_band,target_size,primary_focus,secondary_focus,culture,motto,recruitment_style,state,created_at,updated_at) "
            "VALUES (%u,%u,'%s',%u,'%s',%u,'%s','%s','','','welcoming','%s',%u,%u) ON DUPLICATE KEY UPDATE "
            "bot_led=VALUES(bot_led),faction=VALUES(faction),leader_guid=VALUES(leader_guid),size_band=VALUES(size_band),"
            "target_size=VALUES(target_size),primary_focus=VALUES(primary_focus),secondary_focus=VALUES(secondary_focus),"
            "state=VALUES(state),updated_at=VALUES(updated_at)", guildId, botLed ? 1 : 0, faction,
            guild->GetLeaderGuid().GetCounter(), band, target, primary.c_str(), secondary.c_str(),
            executionEnabled ? "active" : "observed", nowEpoch, nowEpoch);
    }
    enrich << "]}";
    plans << "]}";
    events << "]}";
    const std::string enrichBody = enrich.str(), planBody = plans.str(), eventBody = events.str();
    pendingGuildPlans = std::async(std::launch::async, [enrichBody, planBody, eventBody]()
    {
        std::vector<std::string> debug;
        // These are bounded internal telemetry posts, not model generations.
        // They must not disappear when player chat occupies every provider slot.
        const int telemetryConcurrencyCeiling = 1000000;
        PlayerbotLLMInterface::Generate(eventBody, 9, telemetryConcurrencyCeiling,
            debug, true, "/v2/guilds/events");
        PlayerbotLLMInterface::Generate(enrichBody, 9, telemetryConcurrencyCeiling,
            debug, true, "/v2/guilds/enrich");
        return PlayerbotLLMInterface::Generate(planBody, 9, telemetryConcurrencyCeiling,
            debug, true, "/v2/guilds/plans");
    });
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
    MaybeAdvertiseGuilds(now);
    MaybeCreateProactiveGroupEvent(now);
    MaybeReportBotHealth(now);
    MaybeReportProgressionTrace(now);
    MaybeReportGuildSocieties(now);
    sPlayerbotOrganicEconomy.Update();
    sPlayerbotActionBroker.Update();
    sPlayerbotSocialActionBroker.Update();

    // Do not create one std::async thread for every queued chat event. The
    // provider also has a concurrency gate, but threads waiting behind that
    // gate still consume realm resources during an event burst.
    size_t maxRequests = sPlayerbotAIConfig.llmMaxSimultaniousGenerations ?
        sPlayerbotAIConfig.llmMaxSimultaniousGenerations : 1;
    size_t requestSlots = active.size() < maxRequests ? maxRequests - active.size() : 0;
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
            if (ready.size() >= requestSlots)
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
            const LivingCapabilityRegistration* registration =
                sPlayerbotNaturalLanguageCapabilityRegistry.Resolve(proposal.type);
            if (!registration)
            {
                created[proposal.proposalId] = false;
                continue;
            }
            bool social = registration->executor == LivingCapabilityExecutor::social &&
                sPlayerbotSocialActionBroker.Supports(proposal.type);
            bool partyCombat = registration->executor == LivingCapabilityExecutor::partyCombat &&
                sPlayerbotPartyCombatCoordinator.SupportsProposal(proposal.type);
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
            else if (registration->executor == LivingCapabilityExecutor::economy)
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
