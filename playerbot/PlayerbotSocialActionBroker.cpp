#include "botpch.h"
#include "PlayerbotSocialActionBroker.h"

#include "PlayerbotActionBroker.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotChatDirector.h"
#include "PlayerbotLLMInterface.h"
#include "PlayerbotInventoryPressure.h"
#include "PlayerbotRendezvousManager.h"
#include "LootObjectStack.h"
#include "RandomPlayerbotMgr.h"
#include "ServerFacade.h"
#include "TravelMgr.h"
#include "strategy/values/TravelValues.h"

#include <algorithm>
#include <regex>
#include <limits>
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
        type == "solicit_petition_signatures" ||
        type == "share_quest" || type == "accept_party_quest_plan" || type == "meet_player" ||
        type == "vendor_bags" || type == "gather_node" || type == "decline_gather_node" ||
        type == "open_chest" || type == "decline_chest" ||
        type == "reserve_gathering_nodes" || type == "release_gathering_nodes" ||
        type == "ask_gathering_nodes" || type == "grant_party_free_time" ||
        type == "resume_party_assist");
}

static std::string GatheringPolicyKey(uint32 groupId, uint32 playerGuid, uint32 skillId)
{
    return std::to_string(groupId) + ':' + std::to_string(playerGuid) + ':' + std::to_string(skillId);
}

static std::string SharedObjectPartyKey(uint32 groupId, uint32 playerGuid)
{
    return std::to_string(groupId) + ':' + std::to_string(playerGuid);
}

static std::string SharedObjectKey(uint32 groupId, uint32 playerGuid, uint64 objectGuid)
{
    return SharedObjectPartyKey(groupId, playerGuid) + ':' + std::to_string(objectGuid);
}

static const char* GatheringSkillName(uint32 skillId)
{
    return skillId == SKILL_MINING ? "mining" : "herbalism";
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
    if (bagUsage < 80)
        return false;

    LivingWowInventoryPressureSummary pressure = sPlayerbotInventoryPressure.Analyze(bot);
    std::string maintenanceType;
    if (pressure.vendorStacks)
        maintenanceType = "vendor";
    else if (pressure.HasBankableStorage())
        maintenanceType = "bank";
    else
    {
        std::string reason = pressure.StorableStacks() && pressure.bankUsage >= 100 ?
            "bank_full" : "no_quick_disposition";
        sPlayerbotInventoryPressure.Defer(bot, pressure, reason);
        if (announce)
            bot->GetPlayerbotAI()->SayToParty(
                "My bags are packed, but everything left is protected for quests, crafting, banking, or the auction house. I'll sort it out after the group.", true);
        return false;
    }

    PlayerbotAI* ai = bot->GetPlayerbotAI();
    AiObjectContext* context = ai->GetAiObjectContext();
    TravelTarget* currentTarget = context->GetValue<TravelTarget*>("travel target")->Get();
    // The stock reset action is useful only when no travel target is active,
    // which makes it unable to interrupt a follower's current quest target.
    // This scoped broker owns the replacement and clears it directly.
    sTravelMgr.SetNullTravelTarget(currentTarget);
    context->ClearValues("no active travel destinations");
    if (!SetMaintenanceTarget(bot, maintenanceType))
    {
        sPlayerbotInventoryPressure.Defer(bot, pressure, "no_same_map_maintenance_destination");
        sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=target_rejected kind=%s bag=%u",
            bot->GetGUIDLow(), bot->GetName(), maintenanceType.c_str(), (uint32)bagUsage);
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
    action.bestBagUsage = bagUsage;
    // Four free backpack slots is a useful maintenance result for an active
    // party, rather than declaring success after selling a single stack.
    action.targetBagUsage = 75;
    action.serviceReadyAt = std::chrono::steady_clock::now() + std::chrono::seconds(10 + action.botGuid % 51);
    action.maintenanceType = maintenanceType;
    action.state = "vendor_travel";
    action.stateSince = std::chrono::steady_clock::now();
    action.expires = std::chrono::steady_clock::now() + std::chrono::minutes(5);
    // The scoped trip owns non-combat movement until the bot has sold its
    // inventory. Otherwise ordinary party follow continually pulls the bot
    // back to the human while TravelStrategy tries to reach the vendor.
    // A scoped maintenance trip must always restore ordinary party following,
    // even when the bot joined with a stale/non-follow strategy or the trip
    // could not free a slot.
    action.restoreFollow = true;
    if (ai->HasStrategy("follow", BotState::BOT_STATE_NON_COMBAT))
        ai->ChangeStrategy("nc -follow", BotState::BOT_STATE_NON_COMBAT);
    ai->StopMoving();
    actions[action.actionId] = action;
    vendorCooldowns[action.botGuid] = std::chrono::steady_clock::now() + std::chrono::minutes(10);
    Report(actions[action.actionId]);
    sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=requested bag=%u player=%u",
        bot->GetGUIDLow(), bot->GetName(), (uint32)bagUsage, player->GetGUIDLow());
    if (announce)
        bot->GetPlayerbotAI()->SayToParty(maintenanceType == "bank" ?
            "My bags are full of things I need to keep. I'll put them in the bank and catch back up." :
            "My bags are full. I need to make a quick vendor run; I'll catch back up.", true);
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

bool PlayerbotSocialActionBroker::CanUseSharedObject(Player* bot, Player* player, ObjectGuid guid)
{
    if (!bot || !player || !guid.IsGameObject() || !bot->GetPlayerbotAI() || !bot->GetGroup() ||
        bot->GetGroup() != player->GetGroup() || !player->isRealPlayer())
        return true;

    LootObject loot(bot, guid);
    GameObject* node = bot->GetPlayerbotAI()->GetGameObject(guid);
    if (!node)
        return true;

    bool gatheringNode = loot.skillId == SKILL_MINING || loot.skillId == SKILL_HERBALISM;
    bool ordinaryChest = node->GetGoType() == GAMEOBJECT_TYPE_CHEST &&
        !sObjectMgr.IsGameObjectForQuests(guid.GetEntry()) && !gatheringNode;
    if (!gatheringNode && !ordinaryChest)
        return true;
    if (ordinaryChest && !loot.IsLootPossible(bot))
        return true;

    uint32 required = gatheringNode ? std::max<uint32>(1, loot.reqSkillValue) : 0;
    if (gatheringNode)
    {
        bool playerCanGather = player->HasSkill((SkillType)loot.skillId) &&
            uint32(player->GetSkillValue(loot.skillId)) >= required;
        if (loot.skillId == SKILL_MINING && !player->HasItemCount(2901, 1))
            playerCanGather = false;
        // Do not ask the human to reserve a node they cannot actually use.
        if (!playerCanGather)
            return true;

        auto policy = gatheringPolicies.find(GatheringPolicyKey(
            bot->GetGroup()->GetId(), player->GetGUIDLow(), loot.skillId));
        if (policy != gatheringPolicies.end())
        {
            if (policy->second.mode == "human_reserved")
                return false;
            if (policy->second.mode == "bots_open")
                return true;
        }
    }

    const auto now = std::chrono::steady_clock::now();
    const uint32 groupId = bot->GetGroup()->GetId();
    const std::string partyKey = SharedObjectPartyKey(groupId, player->GetGUIDLow());
    const std::string objectKey = SharedObjectKey(groupId, player->GetGUIDLow(), guid.GetRawValue());
    auto found = sharedObjectOffers.find(bot->GetGUIDLow());
    if (found != sharedObjectOffers.end() && found->second.objectGuid == guid.GetRawValue() &&
        found->second.playerGuid == player->GetGUIDLow() && found->second.expires > now)
        return found->second.state == "approved";

    // A bot may hold only one unresolved offer. Previously, walking among two
    // nearby containers replaced this entry on every AI pass, invalidating the
    // player's reply and producing a fresh announcement each time.
    if (found != sharedObjectOffers.end() && found->second.expires > now &&
        found->second.state == "pending")
        return false;

    auto objectCooldown = sharedObjectCooldowns.find(objectKey);
    if (objectCooldown != sharedObjectCooldowns.end() && objectCooldown->second > now)
        return false;

    // The party resolves one world-object question at a time, even when a town
    // contains several crates or barrels. This also gives short replies such as
    // "yes" exactly one stable offer to confirm.
    for (const auto& pair : sharedObjectOffers)
        if (pair.second.playerGuid == player->GetGUIDLow() && pair.second.groupId == groupId &&
            (pair.second.state == "pending" || pair.second.state == "approved") &&
            pair.second.expires > now)
            return false;


    auto partyCooldown = sharedObjectPartyCooldowns.find(partyKey);
    if (partyCooldown != sharedObjectPartyCooldowns.end() && partyCooldown->second > now)
        return false;

    SharedObjectOffer offer;
    offer.botGuid = bot->GetGUIDLow();
    offer.playerGuid = player->GetGUIDLow();
    offer.groupId = groupId;
    offer.objectGuid = guid.GetRawValue();
    offer.objectEntry = guid.GetEntry();
    offer.skillId = loot.skillId;
    offer.requiredSkill = required;
    offer.nodeName = node->GetName();
    if (offer.nodeName.empty() && node->GetGOInfo())
        offer.nodeName = node->GetGOInfo()->name;
    if (offer.nodeName.empty())
        offer.nodeName = ordinaryChest ? "a chest" : "a resource node";
    offer.objectKind = ordinaryChest ? "chest" : "gathering_node";
    offer.state = "pending";
    offer.expires = now + std::chrono::seconds(90);
    sharedObjectOffers[offer.botGuid] = offer;
    sharedObjectCooldowns[objectKey] = now + std::chrono::minutes(10);
    sharedObjectPartyCooldowns[partyKey] = now + std::chrono::seconds(60);

    std::ostringstream text;
    if (ordinaryChest)
        text << "There's " << offer.nodeName << " here. Do you want me to open it?";
    else
        text << "I see " << offer.nodeName << ". Can I gather it?";
    bot->GetPlayerbotAI()->SayToParty(text.str(), true);
    sLog.outString("Living WoW shared object permission bot=%u player=%u object=%u kind=%s skill=%u required=%u result=offered",
        offer.botGuid, offer.playerGuid, offer.objectEntry, offer.objectKind.c_str(), offer.skillId, offer.requiredSkill);
    return false;
}

bool PlayerbotSocialActionBroker::SetMaintenanceTarget(Player* bot, const std::string& maintenanceType) const
{
    if (!bot || !bot->GetPlayerbotAI())
        return false;
    TravelDestinationPurpose purpose = maintenanceType == "bank" ?
        TravelDestinationPurpose::Bank : TravelDestinationPurpose::Vendor;
    PlayerTravelInfo info(bot);
    DestinationList destinations = sTravelMgr.GetDestinations(
        info, (uint32)purpose, {}, true, 50000.0f, false);
    WorldPosition center(bot);
    TravelDestination* bestDestination = nullptr;
    WorldPosition* bestPosition = nullptr;
    float bestDistance = std::numeric_limits<float>::max();
    // Dungeon maps do not contain ordinary vendors or bankers. For a scoped
    // party maintenance break, select the closest reachable world service and
    // return through the preserved mixed-party session afterward. Outdoor
    // maintenance remains same-map only.
    bool allowCrossMap = bot->GetMap() && bot->GetMap()->IsDungeon();
    for (TravelDestination* destination : destinations)
    {
        if (!destination)
            continue;
        std::list<uint8> chances = { 100 };
        WorldPosition* position = destination->GetNextPoint(center, chances, true);
        if (!position || (!allowCrossMap && position->getMapId() != bot->GetMapId()))
            continue;
        float distance = center.distance(*position);
        if (distance < bestDistance)
        {
            bestDistance = distance;
            bestDestination = destination;
            bestPosition = position;
        }
    }
    if (!bestDestination || !bestPosition)
        return false;
    TravelTarget* target = bot->GetPlayerbotAI()->GetAiObjectContext()->
        GetValue<TravelTarget*>("travel target")->Get();
    sTravelMgr.SetNullTravelTarget(target);
    target->SetTarget(bestDestination, bestPosition);
    target->SetForced(true);
    target->SetStatus(TravelStatus::TRAVEL_STATUS_TRAVEL);
    bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("no active travel destinations");
    sLog.outString("Living WoW vendor maintenance bot=%u result=target_selected kind=%s map=%u area=%s distance=%.1f",
        bot->GetGUIDLow(), maintenanceType.c_str(), bestPosition->getMapId(),
        bestPosition->getAreaName().c_str(), bestDistance);
    return true;
}

bool PlayerbotSocialActionBroker::ContinueAtBank(Action& action, Player* bot)
{
    if (!bot || action.maintenanceType == "bank")
        return false;
    LivingWowInventoryPressureSummary pressure = sPlayerbotInventoryPressure.Analyze(bot);
    if (!pressure.HasBankableStorage())
        return false;
    if (!SetMaintenanceTarget(bot, "bank"))
        return false;
    action.maintenanceType = "bank";
    action.sellAttempts = 0;
    action.lastSellAttempt = std::chrono::steady_clock::time_point();
    action.stateSince = std::chrono::steady_clock::now();
    bot->GetPlayerbotAI()->SayToParty(
        "I sold what I could. I'm putting the materials and other things I need to keep in the bank too.", true);
    Report(action);
    return true;
}

void PlayerbotSocialActionBroker::QueuePartyReturn(Action& action, Player* bot, Player* player,
    const std::string& reason, bool success)
{
    if (!bot || !bot->GetPlayerbotAI())
        return;
    bot->GetPlayerbotAI()->ChangeStrategy("nc -travel once", BotState::BOT_STATE_NON_COMBAT);
    TravelTarget* completedTarget = bot->GetPlayerbotAI()->GetAiObjectContext()->
        GetValue<TravelTarget*>("travel target")->Get();
    sTravelMgr.SetNullTravelTarget(completedTarget);
    bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("no active travel destinations");
    vendorPressureNotified.erase(bot->GetGUIDLow());
    // The ordinary rendezvous manager intentionally rejects instances. A
    // vendor trip that began inside a dungeon is narrower: the bot is still in
    // the same party, and the validated maintenance action owns its return.
    // Teleport to the live party member so normal instance binding chooses the
    // correct copy, then let the returning state restore follow on arrival.
    bool dungeonReturn = false;
    if (player && player->GetMap() && player->GetMap()->IsDungeon() &&
        !bot->IsInCombat() && !bot->IsBeingTeleported())
    {
        dungeonReturn = bot->TeleportTo(player->GetMapId(), player->GetPositionX(),
            player->GetPositionY(), player->GetPositionZ(), player->GetOrientation());
    }
    if (dungeonReturn || (player && sPlayerbotRendezvousManager.ResumePartyAssist(bot, player, reason)))
    {
        action.state = "returning";
        action.expires = std::chrono::steady_clock::now() + std::chrono::seconds(90);
    }
    else
    {
        if (action.restoreFollow)
            bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
        action.restoreFollow = false;
        action.state = success ? "completed" : "failed";
        action.completedAt = std::chrono::steady_clock::now();
        if (action.failureReason.empty())
            action.failureReason = "party return could not be queued";
    }
    Report(action);
}

void PlayerbotSocialActionBroker::AddSharedObjectCapabilities(Player* bot, Player* player,
    ChatDirectorCandidate& candidate)
{
    if (!bot || !player || !bot->GetGroup() || bot->GetGroup() != player->GetGroup())
        return;

    for (uint32 skillId : { uint32(SKILL_MINING), uint32(SKILL_HERBALISM) })
    {
        if (!player->HasSkill((SkillType)skillId))
            continue;
        std::string skillName = GatheringSkillName(skillId);
        for (const std::string& mode : { std::string("reserve"), std::string("release"), std::string("ask") })
        {
            ChatDirectorCapability capability;
            capability.capabilityRef = "gather-policy:" + mode + ':' +
                std::to_string(bot->GetGUIDLow()) + ':' + std::to_string(player->GetGUIDLow()) + ':' +
                std::to_string(bot->GetGroup()->GetId()) + ':' + std::to_string(skillId);
            capability.type = mode == "reserve" ? "reserve_gathering_nodes" :
                mode == "release" ? "release_gathering_nodes" : "ask_gathering_nodes";
            capability.itemKind = skillName;
            capability.quantity = capability.minQuantity = capability.maxQuantity = 1;
            capability.groupId = bot->GetGroup()->GetId();
            capability.actorGuid = bot->GetGUIDLow();
            capability.description = mode == "reserve" ?
                "Reserve all " + skillName + " nodes the human can gather for the human for this party session, without asking at each node." :
                mode == "release" ?
                "Allow party bots to gather " + skillName + " nodes without asking the human until the policy changes." :
                "Restore asking the human for permission each time a party bot finds a " + skillName + " node the human can gather.";
            capability.deliveries.push_back("immediate");
            candidate.actionCapabilities.push_back(std::move(capability));
        }
    }

    auto found = sharedObjectOffers.find(bot->GetGUIDLow());
    if (found == sharedObjectOffers.end())
        return;
    SharedObjectOffer const& offer = found->second;
    if (offer.state != "pending" || offer.playerGuid != player->GetGUIDLow() ||
        offer.expires <= std::chrono::steady_clock::now() || !bot->GetGroup() ||
        bot->GetGroup() != player->GetGroup() || bot->GetGroup()->GetId() != offer.groupId)
        return;

    for (const std::string& decision : { std::string("allow"), std::string("decline") })
    {
        ChatDirectorCapability capability;
        std::string prefix = offer.objectKind == "chest" ? "chest" : "gather";
        capability.capabilityRef = prefix + ':' + decision + ':' + std::to_string(offer.botGuid) + ':' +
            std::to_string(offer.playerGuid) + ':' + std::to_string(offer.objectGuid);
        capability.type = offer.objectKind == "chest" ?
            (decision == "allow" ? "open_chest" : "decline_chest") :
            (decision == "allow" ? "gather_node" : "decline_gather_node");
        capability.itemKind = offer.objectKind;
        capability.quantity = capability.minQuantity = capability.maxQuantity = 1;
        capability.groupId = offer.groupId;
        capability.actorGuid = offer.botGuid;
        capability.description = decision == "allow" ?
            (offer.objectKind == "chest" ? "Open the exact nearby " : "Gather the exact nearby ") +
                offer.nodeName + " after the human granted permission." :
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
        proposal.type == "vendor_bags" ? 300 : proposal.type == "grant_party_free_time" ? 360 :
        proposal.type == "leave_ai_party_for_player" ? 180 : 90);

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
    else if (proposal.type == "solicit_petition_signatures" &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(guild:petition-solicit:([0-9]+):([0-9]+):([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[1].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[2].str()) == player->GetGUIDLow())
    {
        uint32 groupId = (uint32)std::stoul(match[3].str());
        uint32 petitionGuid = (uint32)std::stoul(match[4].str());
        Group* group = bot->GetGroup();
        Item* petition = bot->GetItemByEntry(5863);
        action.groupId = groupId;
        action.questId = petitionGuid;
        uint32 required = sWorld.getConfig(CONFIG_UINT32_MIN_PETITION_SIGNS);
        auto signatures = CharacterDatabase.PQuery(
            "SELECT playerguid FROM petition_sign WHERE petitionguid = '%u'", petitionGuid);
        uint32 signatureCount = signatures ? signatures->GetRowCount() : 0;
        if (group && group == player->GetGroup() && group->GetId() == groupId && petition &&
            petition->GetObjectGuid().GetCounter() == petitionGuid && !bot->GetGuildId() &&
            !bot->GetGuildIdInvited() && signatureCount < required)
        {
            uint32 offered = 0;
            uint32 slots = required - signatureCount;
            for (GroupReference* reference = group->GetFirstMember(); reference && offered < slots;
                reference = reference->next())
            {
                Player* member = reference->getSource();
                if (!member || member == bot || !member->IsInWorld() || !member->GetSession() ||
                    member->GetGuildId() || member->GetGuildIdInvited() ||
                    member->GetMapId() != bot->GetMapId() ||
                    sServerFacade.GetDistance2d(bot, member) > sPlayerbotAIConfig.spellDistance)
                    continue;
                auto signedAlready = CharacterDatabase.PQuery(
                    "SELECT playerguid FROM petition_sign WHERE player_account = '%u' AND petitionguid = '%u'",
                    member->GetSession()->GetAccountId(), petitionGuid);
                if (signedAlready)
                    continue;
                if (bot->GetPlayerbotAI()->DoSpecificAction("offer petition",
                    Event("living charter solicitation", member->GetObjectGuid(), player), true))
                    ++offered;
            }
            completed = offered > 0;
            if (completed)
                sLog.outString("Living WoW charter solicitation owner=%u requester=%u group=%u petition=%u offered=%u",
                    bot->GetGUIDLow(), player->GetGUIDLow(), groupId, petitionGuid, offered);
            else
                action.failureReason = "no eligible unsigned party member is currently close enough";
        }
        else
            action.failureReason = "the charter, party, or signature state changed before solicitation";
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
    else if (proposal.type == "grant_party_free_time" &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(party:free-time:([0-9]+):([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[1].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[2].str()) == player->GetGUIDLow() &&
        bot->GetGroup() && bot->GetGroup() == player->GetGroup() &&
        bot->GetGroup()->GetId() == (uint32)std::stoul(match[3].str()))
    {
        action.groupId = bot->GetGroup()->GetId();
        if (HasActiveVendorTrip(bot->GetGUIDLow()))
        {
            action.state = "waiting_for_vendor_trip";
            actions[action.actionId] = action;
            Report(actions[action.actionId]);
            return true;
        }
        completed = sPlayerbotRendezvousManager.BeginPartyFreeTime(
            bot, player, "party_leader_granted_free_time");
    }
    else if (proposal.type == "resume_party_assist" &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(party:resume-assist:([0-9]+):([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[1].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[2].str()) == player->GetGUIDLow() &&
        bot->GetGroup() && bot->GetGroup() == player->GetGroup() &&
        bot->GetGroup()->GetId() == (uint32)std::stoul(match[3].str()))
    {
        completed = sPlayerbotRendezvousManager.ResumePartyAssist(
            bot, player, "party_leader_recalled_free_time");
    }
    else if ((proposal.type == "reserve_gathering_nodes" ||
              proposal.type == "release_gathering_nodes" || proposal.type == "ask_gathering_nodes") &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"(gather-policy:(reserve|release|ask):([0-9]+):([0-9]+):([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[2].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[3].str()) == player->GetGUIDLow())
    {
        uint32 groupId = (uint32)std::stoul(match[4].str());
        uint32 skillId = (uint32)std::stoul(match[5].str());
        Group* group = bot->GetGroup();
        completed = group && group == player->GetGroup() && group->GetId() == groupId &&
            (skillId == SKILL_MINING || skillId == SKILL_HERBALISM);
        if (completed)
        {
            GatheringPolicy policy;
            policy.playerGuid = player->GetGUIDLow();
            policy.groupId = groupId;
            policy.skillId = skillId;
            policy.mode = match[1].str() == "reserve" ? "human_reserved" :
                match[1].str() == "release" ? "bots_open" : "ask";
            std::string key = GatheringPolicyKey(groupId, policy.playerGuid, skillId);
            if (policy.mode == "ask")
                gatheringPolicies.erase(key);
            else
                gatheringPolicies[key] = policy;

            for (auto offer = sharedObjectOffers.begin(); offer != sharedObjectOffers.end(); )
                if (offer->second.groupId == groupId && offer->second.playerGuid == policy.playerGuid &&
                    offer->second.skillId == skillId)
                    offer = sharedObjectOffers.erase(offer);
                else
                    ++offer;
            sLog.outString("Living WoW gathering policy player=%u group=%u skill=%u mode=%s actor=%u",
                policy.playerGuid, groupId, skillId, policy.mode.c_str(), bot->GetGUIDLow());
        }
    }
    else if ((proposal.type == "gather_node" || proposal.type == "decline_gather_node" ||
              proposal.type == "open_chest" || proposal.type == "decline_chest") &&
        std::regex_match(proposal.capabilityRef, match,
            std::regex(R"((gather|chest):(allow|decline):([0-9]+):([0-9]+):([0-9]+))")) &&
        (uint32)std::stoul(match[3].str()) == bot->GetGUIDLow() &&
        (uint32)std::stoul(match[4].str()) == player->GetGUIDLow())
    {
        uint64 objectGuid = std::stoull(match[5].str());
        auto offer = sharedObjectOffers.find(bot->GetGUIDLow());
        bool approving = proposal.type == "gather_node" || proposal.type == "open_chest";
        bool kindMatches = offer != sharedObjectOffers.end() &&
            ((offer->second.objectKind == "chest") == (match[1].str() == "chest"));
        completed = offer != sharedObjectOffers.end() && kindMatches && offer->second.state == "pending" &&
            offer->second.objectGuid == objectGuid && offer->second.playerGuid == player->GetGUIDLow() &&
            offer->second.expires > std::chrono::steady_clock::now() && bot->GetGroup() == player->GetGroup();
        if (completed && approving)
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
        if (completed)
            sLog.outString("Living WoW shared object permission bot=%u player=%u object=%u kind=%s result=%s",
                bot->GetGUIDLow(), player->GetGUIDLow(), offer->second.objectEntry,
                offer->second.objectKind.c_str(), approving ? "approved_queued" : "declined");
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
    if (!completed && action.failureReason.empty())
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
    for (auto cooldown = sharedObjectCooldowns.begin(); cooldown != sharedObjectCooldowns.end(); )
        if (cooldown->second <= now)
            cooldown = sharedObjectCooldowns.erase(cooldown);
        else
            ++cooldown;
    for (auto cooldown = sharedObjectPartyCooldowns.begin(); cooldown != sharedObjectPartyCooldowns.end(); )
        if (cooldown->second <= now)
            cooldown = sharedObjectPartyCooldowns.erase(cooldown);
        else
            ++cooldown;
    for (auto policy = gatheringPolicies.begin(); policy != gatheringPolicies.end(); )
    {
        Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, policy->second.playerGuid));
        if (!player || !player->GetGroup() || player->GetGroup()->GetId() != policy->second.groupId)
            policy = gatheringPolicies.erase(policy);
        else
            ++policy;
    }
    for (auto offer = sharedObjectOffers.begin(); offer != sharedObjectOffers.end(); )
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(offer->second.botGuid);
        Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, offer->second.playerGuid));
        if (offer->second.expires <= now || !bot || !player || !bot->GetGroup() ||
            bot->GetGroup() != player->GetGroup() || bot->GetGroup()->GetId() != offer->second.groupId)
            offer = sharedObjectOffers.erase(offer);
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
        else if (action.state == "waiting_for_vendor_trip")
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
            Group* group = bot ? bot->GetGroup() : nullptr;
            if (!bot || !player || !ValidateCommon(bot, player) || !group ||
                group != player->GetGroup() || group->GetId() != action.groupId ||
                !group->IsLeader(player->GetObjectGuid()))
            {
                action.state = "rejected";
                action.failureReason = "party or leader state changed before personal errands could begin";
                Report(action);
            }
            else if (!HasActiveVendorTrip(action.botGuid))
            {
                if (sPlayerbotRendezvousManager.IsPartyFreeTime(action.botGuid) ||
                    sPlayerbotRendezvousManager.BeginPartyFreeTime(
                        bot, player, "party_leader_granted_free_time_after_maintenance"))
                {
                    action.state = "completed";
                    action.completedAt = now;
                    Report(action);
                }
                else if (now >= action.expires)
                {
                    action.state = "expired";
                    action.failureReason = "personal errands could not begin safely after maintenance";
                    Report(action);
                }
                else if (!bot->IsInCombat())
                    sPlayerbotRendezvousManager.ResumePartyAssist(
                        bot, player, "party_free_time_waiting_for_safe_return");
            }
            else if (now >= action.expires)
            {
                action.state = "expired";
                action.failureReason = "the existing maintenance trip did not finish before personal errands expired";
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
                        bool sameMap = destination->getMapId() == bot->GetMapId();
                        bool relocated = false;
                        if (sameMap)
                        {
                            bot->NearTeleportTo(destination->getX(), destination->getY(),
                                destination->getZ(), destination->getO());
                            relocated = true;
                        }
                        else if (bot->GetMap() && bot->GetMap()->IsDungeon())
                        {
                            relocated = bot->TeleportTo(destination->getMapId(), destination->getX(),
                                destination->getY(), destination->getZ(), destination->getO());
                        }
                        action.outboundRelocated = relocated;
                        if (relocated)
                        {
                            bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("nearest npcs");
                            sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=relocated map=%u area=%s",
                                bot->GetGUIDLow(), bot->GetName(), destination->getMapId(),
                                destination->getAreaName().c_str());
                        }
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
                        // Relocation invalidates the cached nearby-NPC list.
                        // Refresh it before the vendor/banker interaction so
                        // preflight and execution see the same destination.
                        bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("nearest npcs");
                        if (action.maintenanceType == "vendor" && !action.repairAttempted)
                        {
                            action.repairAttempted = true;
                            bot->GetPlayerbotAI()->DoSpecificAction("repair",
                                Event("rpg action", "living-wow-maintenance", player), true);
                        }
                        bool sold = action.maintenanceType == "bank" ?
                            bot->GetPlayerbotAI()->DoSpecificAction("bank",
                                Event("rpg action", "living-wow-safe-storage", nullptr), true) :
                            bot->GetPlayerbotAI()->DoSpecificAction("sell",
                                Event("rpg action", "living-wow-safe-vendor", player), true);
                        // Bag-space is a cached Playerbots value. Invalidate it
                        // after each real sell attempt so completion observes
                        // the changed inventory instead of the pre-trip value.
                        bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("bag space");
                        bot->GetPlayerbotAI()->GetAiObjectContext()->ClearValues("bank space");
                        sLog.outString("Living WoW vendor maintenance bot=%u name=%s result=%s attempt=%u distance=%.1f",
                            bot->GetGUIDLow(), bot->GetName(), sold ?
                                (action.maintenanceType == "bank" ? "bank_action" : "sell_action") :
                                (action.maintenanceType == "bank" ? "nothing_safe_to_bank" : "nothing_safe_to_sell"),
                            (uint32)action.sellAttempts, target->Distance(bot));
                    }
                }
                uint8 usage = bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<uint8>("bag space")->Get();
                action.bestBagUsage = std::min(action.bestBagUsage, usage);
                LivingWowInventoryPressureSummary remaining = sPlayerbotInventoryPressure.Analyze(bot);
                bool serviceTimeElapsed = now >= action.serviceReadyAt;
                bool targetReached = usage <= action.targetBagUsage;
                bool noSafeMaintenance = !remaining.vendorStacks && !remaining.HasBankableStorage();
                if (serviceTimeElapsed && (targetReached ||
                    (noSafeMaintenance && usage < action.initialBagUsage)))
                {
                    if (targetReached)
                        bot->GetPlayerbotAI()->SayToParty(action.maintenanceType == "bank" ?
                            "I put the things I need to keep in the bank. Heading back now." :
                            "I cleared enough bag space to keep going. Heading back now.", true);
                    else
                    {
                        std::ostringstream notice;
                        notice << "I freed what I safely could. My bags are still " << (uint32)usage
                            << "% full because the rest is protected, so I'm heading back.";
                        bot->GetPlayerbotAI()->SayToParty(notice.str(), true);
                    }
                    QueuePartyReturn(action, bot, player,
                        targetReached ? "vendor_trip_complete" : "vendor_trip_partial",
                        targetReached);
                }
                else if (action.sellAttempts >= 5)
                {
                    if (!ContinueAtBank(action, bot))
                    {
                        if (!serviceTimeElapsed)
                            continue;
                        action.failureReason = "no additional safe maintenance items freed a bag slot";
                        sPlayerbotInventoryPressure.Defer(bot, remaining, "quick_maintenance_freed_no_slot");
                        bot->GetPlayerbotAI()->SayToParty(action.bestBagUsage < action.initialBagUsage ?
                            "I freed what I safely could. The rest is quest gear or other protected supplies, so I'm heading back." :
                            "I couldn't free a slot without losing quest items or other protected supplies. I'm heading back.", true);
                        QueuePartyReturn(action, bot, player, "vendor_trip_no_space_freed",
                            action.bestBagUsage < action.initialBagUsage);
                    }
                }
                else if (now >= action.expires)
                {
                    action.failureReason = "vendor trip did not free bag space in time";
                    LivingWowInventoryPressureSummary pressure = sPlayerbotInventoryPressure.Analyze(bot);
                    sPlayerbotInventoryPressure.Defer(bot, pressure, "party_maintenance_timeout");
                    QueuePartyReturn(action, bot, player, "vendor_trip_timeout", false);
                }
            }
        }
        else if (action.state == "returning")
        {
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(action.botGuid);
            Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, action.playerGuid));
            if (bot && player && bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
            {
                if (action.restoreFollow)
                    bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
                action.restoreFollow = false;
                action.state = "completed";
                action.completedAt = now;
                Report(action);
            }
            else if (now >= action.expires)
            {
                if (bot && bot->GetPlayerbotAI() && action.restoreFollow)
                    bot->GetPlayerbotAI()->ChangeStrategy("nc +follow", BotState::BOT_STATE_NON_COMBAT);
                action.restoreFollow = false;
                action.state = "failed";
                action.failureReason = "party return timed out";
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
