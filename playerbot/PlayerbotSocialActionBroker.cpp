#include "botpch.h"
#include "PlayerbotSocialActionBroker.h"

#include "PlayerbotActionBroker.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotChatDirector.h"
#include "PlayerbotLLMInterface.h"
#include "PlayerbotRendezvousManager.h"
#include "LootObjectStack.h"
#include "RandomPlayerbotMgr.h"
#include "TravelMgr.h"
#include "strategy/values/TravelValues.h"

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
        type == "leave_ai_party_for_player" ||
        type == "share_quest" || type == "accept_party_quest_plan" || type == "meet_player" ||
        type == "vendor_bags" || type == "gather_node" || type == "decline_gather_node");
}

static bool GroupHasRealHuman(Group* group)
{
    if (!group) return false;
    for (GroupReference* reference = group->GetFirstMember(); reference; reference = reference->next())
    {
        Player* member = reference->getSource();
        if (member && member->IsInWorld() && member->isRealPlayer())
            return true;
    }
    return false;
}

static bool LeaveAiOnlyParty(Player* bot, uint32 expectedGroupId)
{
    Group* group = bot ? bot->GetGroup() : nullptr;
    if (!bot || !group || group->GetId() != expectedGroupId || GroupHasRealHuman(group) ||
        bot->IsInCombat() || bot->GetMap()->IsDungeon() || bot->InBattleGround() ||
        bot->IsTaxiFlying() || bot->GetTransport())
        return false;

    WorldPacket packet;
    packet << uint32(PARTY_OP_LEAVE) << bot->GetName() << uint32(0);
    bot->GetSession()->HandleGroupDisbandOpcode(packet);
    if (bot->GetGroup())
        return false;
    bot->GetPlayerbotAI()->SetMaster(nullptr);
    bot->GetPlayerbotAI()->ResetStrategies();
    bot->GetPlayerbotAI()->Reset();
    return true;
}

bool PlayerbotSocialActionBroker::ValidateCommon(Player* bot, Player* player) const
{
    return bot && player && bot->GetPlayerbotAI() && bot->IsInWorld() && player->IsInWorld() &&
        bot->IsAlive() && player->IsAlive() && bot->GetTeam() == player->GetTeam() &&
        !bot->InBattleGround() && !player->InBattleGround();
}

bool PlayerbotSocialActionBroker::HasActiveVendorTrip(uint32 botGuid) const
{
    for (const auto& pair : actions)
        if (pair.second.botGuid == botGuid && pair.second.type == "vendor_bags" &&
            (pair.second.state == "vendor_travel" || pair.second.state == "returning"))
            return true;
    return false;
}

bool PlayerbotSocialActionBroker::StartVendorTrip(Player* bot, Player* player, const std::string& actionId,
    const std::string& eventId, const std::string& proposalId, bool announce)
{
    if (!ValidateCommon(bot, player) || !bot->GetGroup() || bot->GetGroup() != player->GetGroup() ||
        bot->IsInCombat() || HasActiveVendorTrip(bot->GetGUIDLow()))
        return false;
    uint8 bagUsage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
    if (bagUsage <= 80)
        return false;

    PlayerbotAI* ai = bot->GetPlayerbotAI();
    AiObjectContext* context = ai->GetAiObjectContext();
    TravelTarget* currentTarget = context->GetValue<TravelTarget*>("travel target")->Get();
    // The stock reset action is useful only when no travel target is active,
    // which makes it unable to interrupt a follower's current quest target.
    // This scoped broker owns the replacement and clears it directly.
    sTravelMgr.SetNullTravelTarget(currentTarget);
    context->ClearValues("no active travel destinations");
    if (!ai->DoSpecificAction("request progression vendor travel target",
        Event("living vendor bags", "", player), true))
    {
        sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=request_rejected bag=%u",
            bot->GetGUIDLow(), bot->GetName(), (uint32)bagUsage);
        return false;
    }

    Action action;
    action.actionId = actionId;
    action.eventId = eventId;
    action.proposalId = proposalId;
    action.type = "vendor_bags";
    action.capabilityRef = "vendor:" + std::to_string(bot->GetGUIDLow()) + ':' +
        std::to_string(player->GetGUIDLow());
    action.botGuid = bot->GetGUIDLow();
    action.playerGuid = player->GetGUIDLow();
    action.groupId = bot->GetGroup()->GetId();
    action.initialBagUsage = bagUsage;
    action.state = "vendor_travel";
    action.stateSince = std::chrono::steady_clock::now();
    action.expires = std::chrono::steady_clock::now() + std::chrono::minutes(5);
    // The scoped trip owns non-combat movement until the bot has sold its
    // inventory. Otherwise ordinary party follow continually pulls the bot
    // back to the human while TravelStrategy tries to reach the vendor.
    action.restoreFollow = ai->HasStrategy("follow", BotState::BOT_STATE_NON_COMBAT);
    if (action.restoreFollow)
        ai->ChangeStrategy("nc -follow", BotState::BOT_STATE_NON_COMBAT);
    ai->StopMoving();
    actions[action.actionId] = action;
    vendorCooldowns[action.botGuid] = std::chrono::steady_clock::now() + std::chrono::minutes(10);
    Report(actions[action.actionId]);
    sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=requested bag=%u player=%u",
        bot->GetGUIDLow(), bot->GetName(), (uint32)bagUsage, player->GetGUIDLow());
    if (announce)
        bot->GetPlayerbotAI()->SayToParty("My bags are full. I need to make a quick vendor run; I'll catch back up.", true);
    return true;
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

bool PlayerbotSocialActionBroker::CanGatherNode(Player* bot, Player* player, ObjectGuid guid)
{
    if (!bot || !player || !guid.IsGameObject() || !bot->GetPlayerbotAI() || !bot->GetGroup() ||
        bot->GetGroup() != player->GetGroup() || !player->isRealPlayer())
        return true;

    LootObject loot(bot, guid);
    GameObject* node = bot->GetPlayerbotAI()->GetGameObject(guid);
    if (!node || (loot.skillId != SKILL_MINING && loot.skillId != SKILL_HERBALISM))
        return true;

    uint32 required = std::max<uint32>(1, loot.reqSkillValue);
    bool playerCanGather = player->HasSkill((SkillType)loot.skillId) &&
        uint32(player->GetSkillValue(loot.skillId)) >= required;
    if (loot.skillId == SKILL_MINING && !player->HasItemCount(2901, 1))
        playerCanGather = false;
    // Do not ask the human to reserve a node they cannot actually use.
    if (!playerCanGather)
        return true;

    const auto now = std::chrono::steady_clock::now();
    auto found = gatheringOffers.find(bot->GetGUIDLow());
    if (found != gatheringOffers.end() && found->second.objectGuid == guid.GetRawValue() &&
        found->second.playerGuid == player->GetGUIDLow() && found->second.expires > now)
        return found->second.state == "approved";

    GatheringOffer offer;
    offer.botGuid = bot->GetGUIDLow();
    offer.playerGuid = player->GetGUIDLow();
    offer.groupId = bot->GetGroup()->GetId();
    offer.objectGuid = guid.GetRawValue();
    offer.objectEntry = guid.GetEntry();
    offer.skillId = loot.skillId;
    offer.requiredSkill = required;
    offer.nodeName = node->GetName();
    offer.state = "pending";
    offer.expires = now + std::chrono::seconds(90);
    gatheringOffers[offer.botGuid] = offer;

    std::ostringstream text;
    text << "I see " << offer.nodeName << ". Can I gather it?";
    bot->GetPlayerbotAI()->SayToParty(text.str(), true);
    sLog.outString("Living WoW gathering permission bot=%u player=%u node=%u skill=%u required=%u result=offered",
        offer.botGuid, offer.playerGuid, offer.objectEntry, offer.skillId, offer.requiredSkill);
    return false;
}

void PlayerbotSocialActionBroker::AddGatheringCapabilities(Player* bot, Player* player,
    ChatDirectorCandidate& candidate)
{
    if (!bot || !player)
        return;
    auto found = gatheringOffers.find(bot->GetGUIDLow());
    if (found == gatheringOffers.end())
        return;
    GatheringOffer const& offer = found->second;
    if (offer.state != "pending" || offer.playerGuid != player->GetGUIDLow() ||
        offer.expires <= std::chrono::steady_clock::now() || !bot->GetGroup() ||
        bot->GetGroup() != player->GetGroup() || bot->GetGroup()->GetId() != offer.groupId)
        return;

    for (const std::string& decision : { std::string("allow"), std::string("decline") })
    {
        ChatDirectorCapability capability;
        capability.capabilityRef = "gather:" + decision + ':' + std::to_string(offer.botGuid) + ':' +
            std::to_string(offer.playerGuid) + ':' + std::to_string(offer.objectGuid);
        capability.type = decision == "allow" ? "gather_node" : "decline_gather_node";
        capability.itemKind = "gathering_node";
        capability.quantity = capability.minQuantity = capability.maxQuantity = 1;
        capability.groupId = offer.groupId;
        capability.actorGuid = offer.botGuid;
        capability.description = decision == "allow" ?
            "Gather the exact nearby " + offer.nodeName + " after the human granted permission." :
            "Leave the exact nearby " + offer.nodeName + " for the human player.";
        capability.deliveries.push_back("immediate");
        candidate.actionCapabilities.push_back(std::move(capability));
    }
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

    if (proposal.type == "vendor_bags" && HasActiveVendorTrip(proposal.botGuid))
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
    action.expires = std::chrono::steady_clock::now() + std::chrono::seconds(
        proposal.type == "vendor_bags" ? 300 : proposal.type == "leave_ai_party_for_player" ? 180 : 90);

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
            Player* inviter = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, leaderGuid));
            WorldPacket packet;
            bot->GetSession()->HandleGroupAcceptOpcode(packet);
            completed = bot->GetGroup() != nullptr;
            if (completed && inviter && inviter->isRealPlayer())
                sPlayerbotRendezvousManager.RegisterPartyAssist(bot, inviter);
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
    else if (proposal.type == "leave_ai_party_for_player" &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(group:leave-ai-for-player:([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[2].str()) == player->GetGUIDLow())
    {
        uint32 groupId = (uint32)std::stoul(match[1].str());
        action.groupId = groupId;
        Group* group = bot->GetGroup();
        if (group && group->GetId() == groupId && !GroupHasRealHuman(group) &&
            !bot->GetMap()->IsDungeon() && !bot->InBattleGround() && !bot->IsTaxiFlying() && !bot->GetTransport())
        {
            if (bot->IsInCombat())
            {
                action.state = "waiting_to_leave_ai_party";
                bot->Whisper("I'm in a fight right now. I'll leave this group when it's safe, then let you know.",
                    LANG_UNIVERSAL, player->GetObjectGuid());
                actions[action.actionId] = action;
                Report(actions[action.actionId]);
                return true;
            }
            completed = LeaveAiOnlyParty(bot, groupId);
            if (completed)
                bot->Whisper("I'm free now. You can invite me.", LANG_UNIVERSAL, player->GetObjectGuid());
        }
        else
            action.failureReason = GroupHasRealHuman(group) ? "a human is now in the party" :
                "the AI-only party is no longer safe to leave";
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
    else if (proposal.type == "vendor_bags" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(vendor:([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[1].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[2].str()) == player->GetGUIDLow() &&
        bot->GetGroup() && bot->GetGroup() == player->GetGroup() && !bot->IsInCombat())
    {
        if (StartVendorTrip(bot, player, action.actionId, action.eventId, action.proposalId, false))
            return true;
        action.failureReason = "no safe vendor trip is currently available";
    }
    else if ((proposal.type == "gather_node" || proposal.type == "decline_gather_node") &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(gather:(allow|decline):([0-9]+):([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[2].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[3].str()) == player->GetGUIDLow())
    {
        uint64 objectGuid = std::stoull(match[4].str());
        auto offer = gatheringOffers.find(bot->GetGUIDLow());
        completed = offer != gatheringOffers.end() && offer->second.state == "pending" &&
            offer->second.objectGuid == objectGuid && offer->second.playerGuid == player->GetGUIDLow() &&
            offer->second.expires > std::chrono::steady_clock::now() && bot->GetGroup() == player->GetGroup();
        if (completed && proposal.type == "gather_node")
        {
            ObjectGuid guid(objectGuid);
            LootObject loot(bot, guid);
            completed = !bot->IsInCombat() && loot.IsLootPossible(bot);
            if (completed)
            {
                offer->second.state = "approved";
                offer->second.expires = std::chrono::steady_clock::now() + std::chrono::minutes(2);
                completed = bot->GetPlayerbotAI()->GetAiObjectContext()->
                    GetValue<LootObjectStack*>("available loot")->Get()->Add(guid);
            }
        }
        else if (completed)
        {
            offer->second.state = "declined";
            offer->second.expires = std::chrono::steady_clock::now() + std::chrono::minutes(10);
        }
    }
    else if (proposal.type == "meet_player" &&
        std::regex_match(proposal.capabilityRef, match, std::regex(R"(meet:([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[1].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[2].str()) == player->GetGUIDLow())
    {
        PlayerbotRendezvousManager::RequestResult result = sPlayerbotRendezvousManager.Request(
            bot, player, action.actionId, true);
        if (result == PlayerbotRendezvousManager::RequestResult::accepted ||
            result == PlayerbotRendezvousManager::RequestResult::ordinary_travel)
        {
            action.state = "meeting";
            actions[action.actionId] = action;
            Report(actions[action.actionId]);
            return true;
        }
        action.failureReason = result == PlayerbotRendezvousManager::RequestResult::unsafe ?
            "no observer-safe rendezvous route" : "bot cannot leave its current activity";
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
    for (auto offer = gatheringOffers.begin(); offer != gatheringOffers.end(); )
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(offer->second.botGuid);
        Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, offer->second.playerGuid));
        if (offer->second.expires <= now || !bot || !player || !bot->GetGroup() ||
            bot->GetGroup() != player->GetGroup() || bot->GetGroup()->GetId() != offer->second.groupId)
            offer = gatheringOffers.erase(offer);
        else
            ++offer;
    }
    if (!nextVendorScan.time_since_epoch().count() || now >= nextVendorScan)
    {
        nextVendorScan = now + std::chrono::seconds(5);
        for (const auto& entry : sRandomPlayerbotMgr.GetPlayers())
        {
            Player* bot = entry.second;
            if (!bot || !bot->IsInWorld() || !bot->GetPlayerbotAI() || !bot->GetGroup() ||
                !bot->IsAlive() || bot->IsInCombat() || HasActiveVendorTrip(bot->GetGUIDLow()))
                continue;
            uint8 bagUsage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
            if (bagUsage < 90)
            {
                vendorPressureNotified.erase(bot->GetGUIDLow());
                continue;
            }
            auto cooldown = vendorCooldowns.find(bot->GetGUIDLow());
            if (cooldown != vendorCooldowns.end() && cooldown->second > now)
                continue;
            Player* player = nullptr;
            Group::MemberSlotList const& members = bot->GetGroup()->GetMemberSlots();
            for (Group::MemberSlotList::const_iterator member = members.begin(); member != members.end(); ++member)
            {
                Player* candidate = sObjectAccessor.FindPlayer(member->guid);
                if (candidate && !candidate->GetPlayerbotAI())
                {
                    player = candidate;
                    if (bot->GetGroup()->IsLeader(candidate->GetObjectGuid()))
                        break;
                }
            }
            if (!player)
                continue;
            if (bagUsage < 100)
            {
                if (vendorPressureNotified.insert(bot->GetGUIDLow()).second)
                {
                    std::ostringstream notice;
                    notice << "I'm at " << (uint32)bagUsage << "% bag space. Can I go vendor?";
                    bot->GetPlayerbotAI()->SayToParty(notice.str(), true);
                    sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=permission_requested bag=%u player=%u",
                        bot->GetGUIDLow(), bot->GetName(), (uint32)bagUsage, player->GetGUIDLow());
                }
                continue;
            }
            std::ostringstream id;
            id << "wow-social-vendor-auto-" << bot->GetGUIDLow() << '-' << time(nullptr);
            StartVendorTrip(bot, player, id.str(), "inventory-full", "proactive-vendor", true);
        }
    }
    for (auto& pair : actions)
    {
        Action& action = pair.second;
        if (action.state == "waiting_to_leave_ai_party")
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
            Group* group = bot ? bot->GetGroup() : nullptr;
            if (!bot || !player || !ValidateCommon(bot, player) || !group || group->GetId() != action.groupId ||
                GroupHasRealHuman(group))
            {
                action.state = "rejected";
                action.failureReason = group && GroupHasRealHuman(group) ? "a human joined the party" :
                    "party or character state changed before release";
                Report(action);
            }
            else if (!bot->IsInCombat() && LeaveAiOnlyParty(bot, action.groupId))
            {
                action.state = "completed";
                action.completedAt = now;
                bot->Whisper("I'm free now. You can invite me.", LANG_UNIVERSAL, player->GetObjectGuid());
                Report(action);
            }
            else if (now >= action.expires)
            {
                action.state = "expired";
                action.failureReason = "could not safely leave the AI-only party before the offer expired";
                Report(action);
            }
        }
        else if (action.state == "vendor_travel")
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
            if (!bot || !player || !ValidateCommon(bot, player) || bot->GetGroup() != player->GetGroup())
            {
                action.state = "failed";
                action.failureReason = "party or character state changed during vendor trip";
                Report(action);
                if (bot && bot->GetPlayerbotAI() && action.restoreFollow)
                    bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
                action.restoreFollow = false;
            }
            else
            {
                // The destination request resolves asynchronously. Re-running
                // choose is cheap and becomes effective as soon as it is ready.
                bot->GetPlayerbotAI()->DoSpecificAction("choose travel target", Event("living vendor bags", "", player), true);
                TravelTarget* target = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<TravelTarget*>("travel target")->Get();
                bool targetReady = target && target->GetPosition() &&
                    (target->GetStatus() == TravelStatus::TRAVEL_STATUS_TRAVEL ||
                     target->GetStatus() == TravelStatus::TRAVEL_STATUS_READY);
                if (targetReady)
                {
                    // Human-led bots do not normally load TravelStrategy. A
                    // scoped travel-once strategy makes this one validated
                    // vendor target executable and removes itself on arrival.
                    bot->GetPlayerbotAI()->ChangeStrategy("nc +travel once", BotState::BOT_STATE_NON_COMBAT);
                    long departureSeconds = std::chrono::duration_cast<std::chrono::seconds>(
                        now - action.stateSince).count();
                    if (!action.outboundRelocated && !bot->IsInCombat() && departureSeconds >= 3)
                    {
                        WorldPosition* destination = target->GetPosition();
                        bot->GetPlayerbotAI()->StopMoving();
                        bool relocated = false;
                        if (destination->getMapId() == bot->GetMapId())
                        {
                            bot->NearTeleportTo(destination->getX(), destination->getY(),
                                destination->getZ(), destination->getO());
                            relocated = true;
                        }
                        else
                            relocated = bot->TeleportTo(destination->getMapId(), destination->getX(),
                                destination->getY(), destination->getZ(), destination->getO());
                        action.outboundRelocated = relocated;
                        if (relocated)
                            sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=relocated map=%u area=%s",
                                bot->GetGUIDLow(), bot->GetName(), destination->getMapId(),
                                destination->getAreaName().c_str());
                    }
                }

                if (!bot->IsBeingTeleported() && target && (target->GetStatus() == TravelStatus::TRAVEL_STATUS_WORK ||
                    target->Distance(bot) <= INTERACTION_DISTANCE))
                {
                    bot->GetPlayerbotAI()->ChangeStrategy("nc -travel once", BotState::BOT_STATE_NON_COMBAT);
                    bot->GetPlayerbotAI()->StopMoving();
                    long sinceSell = action.lastSellAttempt.time_since_epoch().count() ?
                        std::chrono::duration_cast<std::chrono::seconds>(now - action.lastSellAttempt).count() : 2;
                    if (sinceSell >= 1)
                    {
                        action.lastSellAttempt = now;
                        ++action.sellAttempts;
                        bool sold = bot->GetPlayerbotAI()->DoSpecificAction("sell",
                            Event("rpg action", "vendor", player), true);
                        // Bag-space is a cached Playerbots value. Invalidate it
                        // after each real sell attempt so completion observes
                        // the changed inventory instead of the pre-trip value.
                        bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("bag space");
                        sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=%s attempt=%u distance=%.1f",
                            bot->GetGUIDLow(), bot->GetName(), sold ? "sell_action" : "nothing_safe_to_sell",
                            (uint32)action.sellAttempts, target->Distance(bot));
                    }
                }
                uint8 usage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
                if (usage < action.initialBagUsage)
                {
                    bot->GetPlayerbotAI()->ChangeStrategy("nc -travel once", BotState::BOT_STATE_NON_COMBAT);
                    TravelTarget* completedTarget = bot->GetPlayerbotAI()->GetAiObjectContext()->
                        GetValue<TravelTarget*>("travel target")->Get();
                    sTravelMgr.SetNullTravelTarget(completedTarget);
                    bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("no active travel destinations");
                    if (action.restoreFollow)
                        bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
                    action.restoreFollow = false;
                    vendorPressureNotified.erase(bot->GetGUIDLow());
                    if (sPlayerbotRendezvousManager.ResumePartyAssist(bot, player, "vendor_trip_complete"))
                        action.state = "returning";
                    else
                    {
                        action.state = "completed";
                        action.completedAt = now;
                        action.failureReason = "items sold; party return could not be queued";
                    }
                    Report(action);
                }
                else if (action.sellAttempts >= 5)
                {
                    TravelTarget* completedTarget = bot->GetPlayerbotAI()->GetAiObjectContext()->
                        GetValue<TravelTarget*>("travel target")->Get();
                    sTravelMgr.SetNullTravelTarget(completedTarget);
                    bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("no active travel destinations");
                    if (action.restoreFollow)
                        bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
                    action.restoreFollow = false;
                    action.failureReason = "no additional safe vendor items freed a bag slot";
                    if (sPlayerbotRendezvousManager.ResumePartyAssist(bot, player, "vendor_trip_no_space_freed"))
                        action.state = "returning";
                    else
                    {
                        action.state = "failed";
                        action.completedAt = now;
                    }
                    Report(action);
                }
                else if (now >= action.expires)
                {
                    action.state = "expired";
                    action.failureReason = "vendor trip did not free bag space in time";
                    Report(action);
                    bot->GetPlayerbotAI()->ChangeStrategy("nc -travel once", BotState::BOT_STATE_NON_COMBAT);
                    if (action.restoreFollow)
                        bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
                    action.restoreFollow = false;
                }
            }
        }
        else if (action.state == "returning")
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
            if (bot && player && bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
            {
                sPlayerbotRendezvousManager.BeginDeparture(action.botGuid, action.playerGuid, "vendor_return_complete");
                action.state = "completed";
                action.completedAt = now;
                Report(action);
            }
        }
        else if (action.state == "meeting")
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
            if (bot && player && bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
            {
                action.state = "completed";
                action.completedAt = now;
                Report(action);
            }
            else if (now >= action.expires)
            {
                action.state = "expired";
                action.failureReason = "meeting offer expired";
                sPlayerbotRendezvousManager.BeginDeparture(action.botGuid, action.playerGuid, action.failureReason);
                Report(action);
            }
        }
        else if (action.state == "completed" && action.type == "meet_player" &&
            std::chrono::duration_cast<std::chrono::seconds>(now - action.completedAt).count() >= 30)
        {
            sPlayerbotRendezvousManager.BeginDeparture(action.botGuid, action.playerGuid, "meetup_completed");
            action.state = "departing";
            Report(action);
        }
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
    uint32 currentGroupId = player && player->GetGroup() ? player->GetGroup()->GetId() : action.groupId;
    std::string partySessionId = currentGroupId ? "party:" + std::to_string(currentGroupId) : "";
    std::ostringstream body;
    body << "{\"transaction_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.actionId)
         << "\",\"event_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.eventId)
         << "\",\"proposal_id\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.proposalId)
         << "\",\"party_session_id\":\"" << partySessionId
         << "\",\"bot_guid\":" << action.botGuid << ",\"bot_name\":\""
         << PlayerbotLLMInterface::SanitizeForJson(bot ? bot->GetName() : "") << "\",\"player_guid\":" << action.playerGuid
         << ",\"player_name\":\"" << PlayerbotLLMInterface::SanitizeForJson(player ? player->GetName() : "")
         << "\",\"type\":\"" << action.type << "\",\"capability_ref\":\""
         << PlayerbotLLMInterface::SanitizeForJson(action.capabilityRef)
         << "\",\"item_name\":\"\",\"quantity\":0,\"price_copper\":0,\"delivery\":\"immediate\",\"state\":\""
         << action.state << "\",\"rendezvous_state\":\"" << sPlayerbotRendezvousManager.State(action.botGuid, action.playerGuid)
         << "\",\"catchup_relocated\":" << (sPlayerbotRendezvousManager.WasRelocated(action.botGuid, action.playerGuid) ? "true" : "false")
         << ",\"failure_reason\":\"" << PlayerbotLLMInterface::SanitizeForJson(action.failureReason)
         << "\",\"group_id\":" << action.groupId << ",\"quest_id\":" << action.questId << ",\"expires_at\":\"world-clock\"}";
    std::string payload = body.str();
    std::thread([payload]() {
        std::vector<std::string> debug;
        PlayerbotLLMInterface::Generate(payload, 3, 2, debug, true, "/v2/action-status");
    }).detach();
}
