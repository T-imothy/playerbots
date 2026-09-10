#include "botpch.h"
#include "PlayerbotSocialActionBroker.h"

#include "PlayerbotActionBroker.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotChatDirector.h"
#include "PlayerbotLLMInterface.h"
#include "RandomPlayerbotMgr.h"

#include <regex>
#include <sstream>
#include <thread>

PlayerbotSocialActionBroker& PlayerbotSocialActionBroker::instance()
{
    static PlayerbotSocialActionBroker broker;
    return broker;
}

bool PlayerbotSocialActionBroker::Supports(const std::string& type) const
{
    return sPlayerbotAIConfig.chatDirectorSocialActions && (type == "create_group_and_invite" || type == "invite_to_existing_group" ||
        type == "request_leader_invite" || type == "accept_group_invite" ||
        type == "pass_leadership" || type == "leave_group" ||
        type == "share_quest" || type == "accept_party_quest_plan");
}

bool PlayerbotSocialActionBroker::ValidateCommon(Player* bot, Player* player) const
{
    return bot && player && bot->GetPlayerbotAI() && bot->IsInWorld() && player->IsInWorld() &&
        bot->IsAlive() && player->IsAlive() && bot->GetTeam() == player->GetTeam() &&
        !bot->InBattleGround() && !player->InBattleGround();
}

static bool InviteSocialPlayer(Player* inviter, Player* player)
{
    if (!inviter || !player || !inviter->GetSession() || player->GetGroup() || player->GetGroupInvite())
        return false;
    Group* group = inviter->GetGroup();
    if (group && (!group->IsLeader(inviter->GetObjectGuid()) || group->IsFull()))
        return false;
    WorldPacket packet;
    packet << player->GetName();
    packet << uint32(0);
    inviter->GetSession()->HandleGroupInviteOpcode(packet);
    return player->GetGroupInvite() != nullptr;
}

bool PlayerbotSocialActionBroker::Create(const ChatDirectorActionProposal& proposal, const ChatDirectorEvent& event)
{
    if (!Supports(proposal.type) || !proposal.botGuid || proposal.targetGuid != event.speakerGuid)
        return false;
    auto candidate = event.candidates.find(proposal.botGuid);
    if (candidate == event.candidates.end())
        return false;
    bool supplied = false;
    for (const ChatDirectorCapability& capability : candidate->second.actionCapabilities)
        if (capability.capabilityRef == proposal.capabilityRef && capability.type == proposal.type)
            supplied = true;
    if (!supplied)
        return false;

    Player* bot = sRandomPlayerbotMgr.GetPlayerBot(proposal.botGuid);
    Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, proposal.targetGuid));
    if (!ValidateCommon(bot, player))
        return false;

    Action action;
    action.actionId = "wow-social-" + event.eventId + "-" + proposal.proposalId;
    action.eventId = event.eventId;
    action.proposalId = proposal.proposalId;
    action.type = proposal.type;
    action.capabilityRef = proposal.capabilityRef;
    action.botGuid = proposal.botGuid;
    action.playerGuid = proposal.targetGuid;
    action.state = "preparing";
    action.expires = std::chrono::steady_clock::now() + std::chrono::seconds(90);

    std::smatch match;
    bool completed = false;
    if (proposal.type == "create_group_and_invite" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(group:create:([0-9]+):([0-9]+))")))
    {
        completed = !bot->GetGroup() && !player->GetGroup() && InviteSocialPlayer(bot, player);
    }
    else if ((proposal.type == "invite_to_existing_group" || proposal.type == "request_leader_invite") &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(group:(?:invite|request-leader):([0-9]+):([0-9]+):([0-9]+))")))
    {
        uint32 groupId = (uint32)std::stoul(match[1].str());
        uint32 leaderGuid = (uint32)std::stoul(match[2].str());
        Group* group = bot->GetGroup();
        Player* leader = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, leaderGuid));
        action.groupId = groupId;
        completed = group && group->GetId() == groupId && !group->IsFull() &&
            group->GetLeaderGuid().GetCounter() == leaderGuid && leader && leader->GetPlayerbotAI() &&
            InviteSocialPlayer(leader, player);
    }
    else if (proposal.type == "accept_group_invite" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(group:accept:([0-9]+))")))
    {
        Group* invite = bot->GetGroupInvite();
        uint32 leaderGuid = (uint32)std::stoul(match[1].str());
        if (invite && invite->GetLeaderGuid().GetCounter() == leaderGuid)
        {
            WorldPacket packet;
            bot->GetSession()->HandleGroupAcceptOpcode(packet);
            completed = bot->GetGroup() != nullptr;
        }
    }
    else if (proposal.type == "pass_leadership" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(group:pass:([0-9]+):([0-9]+))")))
    {
        uint32 groupId = (uint32)std::stoul(match[1].str());
        Group* group = bot->GetGroup();
        action.groupId = groupId;
        if (group && group->GetId() == groupId && group->IsLeader(bot->GetObjectGuid()) &&
            group->IsMember(player->GetObjectGuid()))
        {
            WorldPacket packet;
            packet << player->GetObjectGuid();
            bot->GetSession()->HandleGroupSetLeaderOpcode(packet);
            completed = group->IsLeader(player->GetObjectGuid());
        }
    }
    else if (proposal.type == "leave_group" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(group:leave:([0-9]+))")))
    {
        uint32 groupId = (uint32)std::stoul(match[1].str());
        Group* group = bot->GetGroup();
        action.groupId = groupId;
        if (group && group->GetId() == groupId && !bot->IsInCombat() && !bot->GetMap()->IsDungeon())
        {
            WorldPacket packet;
            bot->GetSession()->HandleGroupDisbandOpcode(packet);
            completed = bot->GetGroup() == nullptr;
        }
    }
    else if (proposal.type == "share_quest" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(quest:share:([0-9]+):([0-9]+))")))
    {
        uint32 questId = (uint32)std::stoul(match[1].str());
        uint32 groupId = (uint32)std::stoul(match[2].str());
        Group* group = bot->GetGroup();
        action.groupId = groupId;
        action.questId = questId;
        if (group && group->GetId() == groupId && group == player->GetGroup() && bot->CanShareQuest(questId))
        {
            WorldPacket packet;
            packet << questId;
            bot->GetSession()->HandlePushQuestToParty(packet);
            completed = true;
        }
    }
    else if (proposal.type == "accept_party_quest_plan" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(quest:plan:([0-9]+):([0-9]+))")))
    {
        uint32 questId = (uint32)std::stoul(match[1].str());
        uint32 groupId = (uint32)std::stoul(match[2].str());
        Group* group = bot->GetGroup();
        action.groupId = groupId;
        action.questId = questId;
        completed = group && group->GetId() == groupId && group == player->GetGroup() &&
            bot->GetQuestStatus(questId) != QUEST_STATUS_NONE;
        if (completed)
        {
            preferredQuests[bot->GetGUIDLow()] = std::make_pair(questId, std::chrono::steady_clock::now() + std::chrono::minutes(20));
            bot->GetPlayerbotAI()->DoSpecificAction("reset travel target", Event("living party quest plan", std::to_string(questId), player), true);
        }
    }

    action.state = completed ? "completed" : "rejected";
    if (!completed)
        action.failureReason = "authoritative group or quest state no longer permits the action";
    actions[action.actionId] = action;
    Report(actions[action.actionId]);
    return completed;
}

uint32 PlayerbotSocialActionBroker::PreferredQuest(uint32 botGuid) const
{
    auto found = preferredQuests.find(botGuid);
    if (found == preferredQuests.end() || found->second.second <= std::chrono::steady_clock::now())
        return 0;
    return found->second.first;
}

void PlayerbotSocialActionBroker::Update()
{
    const auto now = std::chrono::steady_clock::now();
    for (auto& pair : actions)
    {
        Action& action = pair.second;
        if (action.state == "preparing" && now >= action.expires)
        {
            action.state = "expired";
            action.failureReason = "social action expired";
            Report(action);
        }
    }
    for (auto it = preferredQuests.begin(); it != preferredQuests.end();)
        if (it->second.second <= now) it = preferredQuests.erase(it); else ++it;
}

void PlayerbotSocialActionBroker::Report(const Action& action) const
{
    Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
    Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
    std::ostringstream body;
    body << "{\"transaction_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.actionId)
         << "\",\"event_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.eventId)
         << "\",\"proposal_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.proposalId)
         << "\",\"bot_guid\":" << action.botGuid << ",\"bot_name\":\""
         << PlayerbotLLMInterface::SanitizeForJson(bot ? bot->GetName() : "") << "\",\"player_guid\":" << action.playerGuid
         << ",\"player_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(player ? player->GetName() : "")
         << "\",\"type\":\"" << action.type << "\",\"capability_ref\":\""
         << PlayerbotLLMInterface::SanitizeForJson(action.capabilityRef)
         << "\",\"item_name\":\"\",\"quantity\":0,\"price_copper\":0,\"delivery\":\"immediate\",\"state\":\""
         << action.state << "\",\"failure_reason\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.failureReason)
         << "\",\"group_id\":" << action.groupId << ",\"quest_id\":" << action.questId << ",\"expires_at\":\"world-clock\"}";
    std::string payload = body.str();
    std::thread([payload]() {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(payload, 3, 2, debug, true, "/v2/action-status");
    }).detach();
}
