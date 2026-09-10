#include "botpch.h"
#include "PlayerbotPartyInvitationMgr.h"
#include "PartyDeparturePolicy.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotChatDirector.h"
#include "PlayerbotSocialActionBroker.h"
#include "PlayerbotRendezvousManager.h"
#include "RandomPlayerbotMgr.h"
#include "strategy/actions/MovementActions.h"

namespace
{
std::set<uint32> Roster(Group* group)
{
    std::set<uint32> result;
    if (!group) return result;
    result.insert(group->GetLeaderGuid().GetCounter());
    for (const auto& slot : group->GetMemberSlots()) result.insert(slot.guid.GetCounter());
    return result;
}
std::set<uint32> Humans(Group* group)
{
    std::set<uint32> result;
    for (uint32 guid : Roster(group))
        if (!sRandomPlayerbotMgr.IsRandomBot(guid)) result.insert(guid);
    return result;
}
void Whisper(Player* bot, Player* player, const std::string& text)
{
    if (bot && player && bot->IsInWorld() && player->IsInWorld())
        bot->GetPlayerbotAI()->Whisper(text, player->GetName(), false, PlayerbotAI::ChatMessageClass::social);
}
bool Safe(Player* bot)
{
    return bot && bot->IsInWorld() && !bot->IsBeingTeleported() && !bot->IsInCombat() &&
        !bot->IsTaxiFlying() && !bot->GetTransport() && !bot->InBattleGround() &&
        !bot->GetMap()->IsDungeon();
}
Group* Destination(Player* player)
{
    return player->GetGroup() ? player->GetGroup() : player->GetGroupInvite();
}
}

PlayerbotPartyInvitationMgr& PlayerbotPartyInvitationMgr::instance()
{
    static PlayerbotPartyInvitationMgr manager;
    return manager;
}

bool PlayerbotPartyInvitationMgr::Queue(Player* bot, Player* player)
{
    if (!sPlayerbotAIConfig.chatDirectorSocialActions || !bot || !player || !player->isRealPlayer() ||
        !bot->GetPlayerbotAI() || !sRandomPlayerbotMgr.IsRandomBot(bot) || bot == player ||
        player->GetTeam() != bot->GetTeam() || player->InBattleGround() || bot->InBattleGround()) return false;
    Group* source = bot->GetGroup() ? bot->GetGroup() : bot->GetGroupInvite();
    Group* destination = Destination(player);
    if (!source || source == destination) return false;
    if (destination && (destination->IsFull() ||
        (!destination->IsLeader(player->GetObjectGuid()) && !destination->IsAssistant(player->GetObjectGuid())))) return false;
    std::lock_guard<std::mutex> lock(mutex);
    if (incoming.size() >= 64) return false;
    Request request;
    if (!sequence) sequence = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    request.id = ++sequence;
    request.bot = bot->GetGUIDLow(); request.requester = player->GetGUIDLow();
    request.source = source->GetId(); request.sourceLeader = source->GetLeaderGuid().GetCounter();
    request.roster = Roster(source); request.humans = Humans(source);
    request.destination = destination ? destination->GetId() : 0;
    request.destinationLeader = destination ? destination->GetLeaderGuid().GetCounter() : request.requester;
    request.expires = std::chrono::steady_clock::now() + std::chrono::minutes(5);
    incoming.push_back(request);
    return true;
}

void PlayerbotPartyInvitationMgr::AddCapabilities(Player* bot, Player* speaker, ChatDirectorCandidate& candidate)
{
    std::lock_guard<std::recursive_mutex> lock(stateMutex);
    if (!bot || !speaker) return;
    auto found = requests.find(bot->GetGUIDLow());
    if (found == requests.end()) return;
    const Request& request = found->second;
    Group* group = bot->GetGroup();
    if (!group || group != speaker->GetGroup() || group->GetId() != request.source ||
        group->GetLeaderGuid().GetCounter() != request.sourceLeader || Roster(group) != request.roster ||
        std::chrono::steady_clock::now() >= request.expires ||
        !living_party_departure::MayVote(request.humans, request.sourceLeader, speaker->GetGUIDLow()) ||
        request.votes.count(speaker->GetGUIDLow())) return;
    for (bool approve : {true, false})
    {
        ChatDirectorCapability capability;
        capability.type = approve ? "approve_party_departure" : "decline_party_departure";
        capability.capabilityRef = "party:departure:" + std::to_string(request.id) + ":" +
            std::to_string(request.bot) + ":" + std::to_string(speaker->GetGUIDLow()) + (approve ? ":yes" : ":no");
        capability.itemKind = "social"; capability.groupId = request.source;
        capability.actorGuid = request.bot;
        capability.quantity = capability.minQuantity = capability.maxQuantity = 1;
        capability.deliveries.push_back("immediate");
        capability.description = std::string(approve ? "Approve" : "Decline") +
            " this bot's pending request to leave your party for an outside human invitation. "
            "Only select for an explicit answer to that departure request, not an unrelated yes/no. "
            "This records this speaker's vote only; the realm checks leader authority or a strict human majority.";
        candidate.actionCapabilities.push_back(std::move(capability));
    }
}

bool PlayerbotPartyInvitationMgr::Vote(Player* bot, Player* speaker, const std::string& ref, bool approve)
{
    std::lock_guard<std::recursive_mutex> lock(stateMutex);
    ChatDirectorCandidate candidate;
    AddCapabilities(bot, speaker, candidate);
    for (const auto& capability : candidate.actionCapabilities)
        if (capability.capabilityRef == ref && capability.type ==
            (approve ? "approve_party_departure" : "decline_party_departure"))
        {
            requests.at(bot->GetGUIDLow()).votes[speaker->GetGUIDLow()] = approve;
            return true;
        }
    return false;
}

bool PlayerbotPartyInvitationMgr::Update()
{
    std::lock_guard<std::recursive_mutex> lock(stateMutex);
    const auto now = std::chrono::steady_clock::now();
    std::vector<Request> queued;
    { std::lock_guard<std::mutex> lock(mutex); queued.swap(incoming); }
    for (const Request& request : queued)
    {
        if (requests.count(request.bot)) continue; // Repeated invites never extend a request.
        if (requests.size() >= 64) continue;
        requests.emplace(request.bot, request);
    }
    bool dockAttempted = false;
    for (auto it = requests.begin(); it != requests.end(); )
    {
        Request& request = it->second;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(request.bot);
        Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, request.requester));
        auto finish = [&](const std::string& code, const std::string& message)
        {
            Whisper(bot, player, message);
            sLog.outString("Living WoW party invitation bot=%u requester=%u request=%llu result=%s",
                request.bot, request.requester, (unsigned long long)request.id, code.c_str());
            it = requests.erase(it);
        };
        if (!bot || !player || !bot->IsInWorld() || !player->IsInWorld())
        { finish("unavailable", "I couldn't complete that invitation. Please invite me again when we're both available."); continue; }
        if (now >= request.expires)
        { finish("expired", "I couldn't get permission or finish leaving safely in time. Please invite me again later."); continue; }
        if (bot->IsBeingTeleported() || player->IsBeingTeleported()) { ++it; continue; }
        if (bot->GetGroup() && bot->GetGroup() == player->GetGroup())
        { finish("already_joined", "I'm in your party now."); continue; }
        Group* source = bot->GetGroup() ? bot->GetGroup() : bot->GetGroupInvite();
        Group* destination = Destination(player);
        const bool destinationValid = !destination ? !request.destination && request.destinationLeader == request.requester :
            destination->GetLeaderGuid().GetCounter() == request.destinationLeader &&
            (!request.destination || destination->GetId() == request.destination) && !destination->IsFull() &&
            (destination->IsLeader(player->GetObjectGuid()) || destination->IsAssistant(player->GetObjectGuid()));
        if (!destinationValid || !source || source->GetId() != request.source ||
            source->GetLeaderGuid().GetCounter() != request.sourceLeader || Roster(source) != request.roster)
        { finish("party_changed", "The party changed, so I cancelled that request. Please invite me again if you still need me."); continue; }
        if (!bot->GetGroup() && !request.humans.empty())
        { finish("human_invite_pending", "I already have an invitation from another player's party. I can't replace their invitation right now."); continue; }
        if (!request.humans.empty())
        {
            if (!request.announced)
            {
                bool otherRequest = false;
                for (const auto& pair : requests)
                    if (pair.first != request.bot && pair.second.source == request.source && pair.second.announced)
                        otherRequest = true;
                if (otherRequest)
                { finish("consent_busy", "Someone else is already asking to leave this party. Please try me again shortly."); continue; }
                request.announced = true;
                Whisper(bot, player, "I'm grouped with other players. I'll ask permission before leaving and let you know.");
                const bool humanLeader = request.humans.count(request.sourceLeader);
                bot->GetPlayerbotAI()->SayToParty("Hey, " + std::string(player->GetName()) +
                    " invited me to another party. Is it all right if I drop group? " +
                    (humanLeader ? "I'll wait for our leader's answer." :
                    "I need " + std::to_string(living_party_departure::Required(request.humans, request.sourceLeader)) +
                    " of our " + std::to_string(request.humans.size()) + " human members to agree."), true,
                    PlayerbotAI::ChatMessageClass::social);
            }
            if (!living_party_departure::Approved(request.humans, request.sourceLeader, request.votes))
            {
                unsigned possible = 0;
                for (uint32 voter : request.humans)
                    if (living_party_departure::MayVote(request.humans, request.sourceLeader, voter) &&
                        (!request.votes.count(voter) || request.votes.at(voter))) ++possible;
                if (possible < living_party_departure::Required(request.humans, request.sourceLeader))
                { finish("declined", "Sorry, my current party needs me to stay. I can't leave this party."); continue; }
                ++it; continue;
            }
        }
        if (now < request.nextAttempt) { ++it; continue; }
        request.nextAttempt = now + std::chrono::seconds(2);
        if (bot->GetTransport() && !dockAttempted)
        {
            dockAttempted = true;
            ai::MovementAction::ExitTransportAtDock(bot->GetPlayerbotAI());
            ++it; continue; // Never mutate group in the same update as a dock transfer.
        }
        if (!Safe(bot))
        {
            if (!request.announced)
            {
                request.announced = true;
                Whisper(bot, player, bot->GetTransport() ?
                    "I'll join you once I get safely off at the next dock." :
                    "I'll join you once it's safe to leave my current activity.");
            }
            ++it; continue;
        }
        // Consume the exact native source membership or invitation. The Group
        // may be deleted by either operation: never use source afterward.
        if (bot->GetGroup())
        {
            WorldPacket leave;
            leave << uint32(PARTY_OP_LEAVE) << bot->GetName() << uint32(0);
            bot->GetSession()->HandleGroupDisbandOpcode(leave);
        }
        else if (source->IsLeader(bot->GetObjectGuid()) && !source->IsCreated())
        { source->RemoveAllInvites(); delete source; }
        else bot->UninviteFromGroup();
        if (bot->GetGroup() || bot->GetGroupInvite())
        { finish("release_failed", "I couldn't leave that party safely. I'm still unavailable."); continue; }
        bot->GetPlayerbotAI()->SetMaster(nullptr);
        bot->GetPlayerbotAI()->RequestStrategyReset(true);
        sPlayerbotSocialActionBroker.ReserveForPlayer(request.bot, request.requester);
        if (!request.humans.empty())
        { finish("released_with_consent", "I've left that group. You can invite me now."); continue; }
        WorldPacket invite;
        invite << bot->GetName();
        player->GetSession()->HandleGroupInviteOpcode(invite);
        Group* pending = bot->GetGroupInvite();
        if (pending && (pending->IsLeader(player->GetObjectGuid()) || pending == player->GetGroup()))
        {
            WorldPacket accept;
            bot->GetSession()->HandleGroupAcceptOpcode(accept);
        }
        if (bot->GetGroup() && bot->GetGroup() == player->GetGroup())
        {
            sPlayerbotSocialActionBroker.CompleteGroupReservation(request.bot, request.requester);
            bot->GetPlayerbotAI()->SetMaster(player);
            sPlayerbotRendezvousManager.RegisterPartyAssist(bot, player);
            sPlayerbotChatDirector.ObservePartyJoin(bot, player);
            finish("joined", "I've joined your party.");
        }
        else finish("invite_changed", "I've left my old party, but couldn't accept that invitation. Please invite me again.");
    }
    return dockAttempted;
}
