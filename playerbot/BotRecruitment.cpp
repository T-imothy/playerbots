#include "playerbot/playerbot.h"
#include "BotRecruitment.h"
#include "RecruitmentPolicy.h"
#include "PlayerbotMgr.h"
#include "RandomPlayerbotMgr.h"
#include "RandomItemMgr.h"
#include "Talentspec.h"
#include "strategy/actions/WhoAction.h"
#include "strategy/actions/UseMeetingStoneAction.h"
#include "Social/SocialMgr.h"
#include <chrono>
#include <deque>
#include <mutex>
#include <set>
#include <sstream>
#include <cctype>

using namespace ai;
namespace limits = ai::RecruitmentPolicy;

namespace
{
    uint64 Now()
    {
        return std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    }

    struct Request
    {
        ObjectGuid owner, bot, leader;
        Group* invitation = nullptr;
        Group* membership = nullptr;
        EventOwner ownerIdentity, botIdentity;
        std::string id, operation, arguments;
        uint64 expires = 0;
        unsigned size = 40;
        uint32 map = 0, instance = 0;
        bool started = false;
    };
    struct Receipt
    {
        std::string payload, response;
        uint64 expires;
    };
    struct Reservation
    {
        ObjectGuid owner;
        uint64 expires;
    };
    struct Service
    {
        std::mutex mutex;
        std::deque<Request> incoming;
        std::set<uint32> managedInvites; // Protected by mutex for AI readers.
        // Everything below is world-thread owned, never consulted by AI workers.
        std::map<uint32, Request> invites, summons;
        std::map<uint32, Reservation> reservations;
        std::map<std::pair<uint32, std::string>, Receipt> receipts;
        std::map<std::string, Receipt> preparation;
        std::map<uint32, uint64> discoveryTime;
        uint32 elapsed = 0;
        uint64 nextDiscovery = 0;
        bool explicitPreparation = false;
        uint64 preparationSecond = 0;
        unsigned gearWork = 0, supplyWork = 0;
        std::map<uint32, unsigned> playerPreparationWork;
    };
    Service& State() { static Service state; return state; }
    void ForgetInvite(uint32 guid)
    {
        std::lock_guard<std::mutex> guard(State().mutex);
        State().managedInvites.erase(guid);
    }
    Player* Find(ObjectGuid guid) { return guid ? sObjectMgr.GetPlayer(guid) : nullptr; }
    bool Connected(Player* player)
    {
        return player && player->GetSession() && !player->GetSession()->isLogingOut();
    }
    Group* Party(Player* player)
    {
        Group* group = player ? player->GetGroup() : nullptr;
        return group && group->IsBattleGroup() ? player->GetOriginalGroup() : group;
    }
    Group* InvitingGroup(Player* player)
    {
        Group* group = Party(player);
        return group ? group : player->GetGroupInvite();
    }
    bool IsBot(Player* player)
    {
        return Connected(player) && player->GetPlayerbotAI() && !player->isRealPlayer();
    }
    void Tell(Player* owner, const std::string& text)
    {
        if (Connected(owner))
            ChatHandler(owner->GetSession()).PSendSysMessage("%s", text.c_str());
    }
    void Whisper(Player* owner, Player* bot, const std::string& text)
    {
        if (!Connected(owner) || !IsBot(bot))
            return;
        WorldPacket packet;
        ChatHandler::BuildChatPacket(packet, CHAT_MSG_WHISPER, text.c_str(), LANG_UNIVERSAL,
            CHAT_TAG_NONE, bot->GetObjectGuid(), bot->GetName());
        owner->GetSession()->SendPacket(packet);
    }
    std::string Payload(Request const& request)
    {
        return request.operation + " " + std::to_string(request.bot.GetCounter()) + " " + request.arguments;
    }
    std::string Response(Request const& request, const std::string& status, const std::string& reason)
    {
        return "PBRECRUIT 1 " + request.id + " " + std::to_string(request.bot.GetCounter()) +
            " " + status + " " + reason;
    }
    void Report(Request const& request, const std::string& status, const std::string& reason)
    {
        std::string response = Response(request, status, reason);
        if (!request.id.empty())
        {
            auto it = State().receipts.find({request.owner.GetCounter(), request.id});
            if (it != State().receipts.end())
                it->second.response = response;
            Tell(Find(request.owner), response);
        }
        else
        {
            Player* bot = Find(request.bot);
            Tell(Find(request.owner), std::string(bot ? bot->GetName() : "Bot") + ": " + status + " (" + reason + ")");
        }
    }
    bool IsBusyQueue(Player* bot)
    {
        if (bot->InBattleGround() || bot->InBattleGroundQueue())
            return true;
#ifdef MANGOSBOT_ZERO
        return sWorld.GetLFGQueue().IsPlayerInQueue(bot->GetObjectGuid());
#elif defined(MANGOSBOT_ONE)
        return bot->GetSession()->m_lfgInfo.queued;
#else
        return bot->GetLfgData().GetState() != LFG_STATE_NONE;
#endif
    }
    std::string Identity(Player* owner, Player* bot)
    {
        if (!Connected(owner) || !owner->isRealPlayer()) return "requester_offline";
        if (!IsBot(bot)) return "not_available_bot";
        uint32 account = bot->GetSession()->GetAccountId();
        bool own = account == owner->GetSession()->GetAccountId();
        bool publicBot = sPlayerbotAIConfig.IsInRandomAccountList(account) || sPlayerbotAIConfig.IsFreeAltBot(bot);
        bool guild = sPlayerbotAIConfig.allowGuildBots && owner->GetGuildId() && owner->GetGuildId() == bot->GetGuildId();
        if (!own && !publicBot && !guild) return "not_authorized";
        if (!owner->IsGameMaster() && owner->GetTeam() != bot->GetTeam() &&
            !sWorld.getConfig(CONFIG_BOOL_ALLOW_TWO_SIDE_INTERACTION_GROUP)) return "wrong_faction";
        if (bot->GetSocial()->HasIgnore(owner->GetObjectGuid())) return "ignored";
        return "";
    }
    std::string Control(Player* owner, Player* bot)
    {
        std::string reason = Identity(owner, bot);
        if (!reason.empty()) return reason;
        Group* group = Party(bot);
        if (group && group != Party(owner)) return "external_group";
        Player* master = bot->GetPlayerbotAI()->GetMaster();
        if (master && master->isRealPlayer() && master != owner) return "other_controller";
        bool own = owner->GetSession()->GetAccountId() == bot->GetSession()->GetAccountId();
        if (!own && master != owner && (!group || !group->IsLeader(owner->GetObjectGuid())))
            return "not_controller";
        if (!bot->GetPlayerbotAI()->GetSecurity()->CheckLevelFor(PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, true, owner))
            return "not_authorized";
        return "";
    }
    bool Enqueue(Request request)
    {
        Service& state = State();
        std::lock_guard<std::mutex> guard(state.mutex);
        if (state.incoming.size() >= limits::MaxIncoming) return false;
        unsigned count = 0;
        for (auto const& pending : state.incoming)
        {
            if (pending.owner == request.owner)
            {
                if (pending.bot == request.bot && pending.operation == request.operation &&
                    pending.id == request.id && pending.arguments == request.arguments)
                    return true;
                ++count;
            }
        }
        if (count >= limits::MaxIncomingPerPlayer) return false;
        state.incoming.push_back(request);
        return true;
    }
    bool HasRoom(std::map<uint32, Request> const& pending, ObjectGuid owner)
    {
        unsigned count = 0;
        for (auto const& entry : pending)
            if (entry.second.owner == owner) ++count;
        return pending.size() < limits::MaxPending && count < limits::MaxPendingPerPlayer;
    }
    void ClearInvite(Request const& request)
    {
        Player* bot = Find(request.bot);
        if (IsBot(bot) && request.botIdentity.Get() == bot && bot->GetGroupInvite() && bot->GetGroupInvite() == request.invitation)
            bot->UninviteFromGroup();
    }
    std::string InviteReason(Request const& request, Player* owner, Player* bot)
    {
        std::string reason = BotRecruitment::Eligibility(owner, bot);
        if (!reason.empty()) return reason;
        if (!owner->IsInWorld() || owner->IsBeingTeleported()) return "requester_transfer";
        Group* group = bot->GetGroupInvite();
        if (!group || group != request.invitation || group != InvitingGroup(owner) || group->GetLeaderGuid() != request.leader)
            return "stale_invite";
        if (!group->IsLeader(owner->GetObjectGuid()) && !group->IsAssistant(owner->GetObjectGuid()))
            return "not_leader";
        if (!limits::HasVacancy(group->GetMembersCount(), request.size, group->IsRaidGroup()))
            return "group_full";
        if (!bot->IsInWorld() || bot->IsBeingTeleported()) return "bot_transfer";
        if (bot->HasCharmer()) return "controlled";
        if (owner->GetMapId() == bot->GetMapId() && owner->GetInstanceId() && bot->GetInstanceId() &&
            owner->GetInstanceId() != bot->GetInstanceId()) return "different_instance";
        return "";
    }
    std::string Waiting(Player* owner, Player* bot)
    {
        if (!owner->IsInWorld() || owner->IsBeingTeleported() || !bot->IsInWorld() || bot->IsBeingTeleported()) return "transfer";
        if (owner->GetTransport() || bot->GetTransport() || owner->IsTaxiFlying() || bot->IsTaxiFlying()) return "transport";
        if (bot->HasCharmer()) return "controlled";
        if (owner->IsInCombat() || bot->IsInCombat()) return "combat";
        if (!owner->IsAlive()) return "requester_dead";
        if (owner->InBattleGround() || IsBusyQueue(bot)) return "queued_activity";
        if (!bot->IsAlive() && !sPlayerbotAIConfig.recruitmentRevive) return "revival_disabled";
        return "";
    }
    bool Arrived(Player* owner, Player* bot)
    {
        return owner->IsInWorld() && !owner->IsBeingTeleported() && bot->IsInWorld() &&
            !bot->IsBeingTeleported() && bot->GetMap() == owner->GetMap() &&
            limits::Arrived(bot->IsInWorld(), bot->IsBeingTeleported(), bot->IsAlive(), bot->IsInCombat(),
                bot->GetMapId(), bot->GetInstanceId(), owner->GetMapId(), owner->GetInstanceId(),
                bot->GetDistance(owner), bot->GetMap() == owner->GetMap() && bot->IsWithinLOSInMap(owner));
    }
    bool Number(std::string const& text, uint32& value)
    {
        if (text.empty() || text.size() > 10) return false;
        uint64 result = 0;
        for (unsigned char c : text)
        {
            if (!std::isdigit(c)) return false;
            result = result * 10 + c - '0';
            if (result > UINT32_MAX) return false;
        }
        value = uint32(result);
        return true;
    }
    void Dispatch(Request request)
    {
        Service& state = State();
        Player* owner = Find(request.owner);
        Player* bot = Find(request.bot);
        if (!Connected(owner) || request.ownerIdentity.Get() != owner) return;
        if (request.bot && request.botIdentity.Get() != bot)
        { Report(request,"refused","bot_session_changed"); return; }
        if (limits::Expired(Now(), request.expires))
        {
            if (request.operation == "accept") ClearInvite(request);
            Report(request, "timed_out", "queue_deadline");
            return;
        }
        if (!request.id.empty())
        {
            auto key = std::make_pair(request.owner.GetCounter(), request.id);
            auto previous = state.receipts.find(key);
            if (previous != state.receipts.end())
            {
                Tell(owner, previous->second.payload == Payload(request) ? previous->second.response : Response(request, "refused", "id_conflict"));
                return;
            }
            unsigned count = 0;
            for (auto const& receipt : state.receipts) if (receipt.first.first == key.first) ++count;
            if (state.receipts.size() >= limits::MaxReceipts || count >= limits::MaxReceiptsPerPlayer)
            {
                Tell(owner, Response(request, "refused", "receipt_limit"));
                return;
            }
            state.receipts[key] = {Payload(request), Response(request, "pending", "queued"), Now() + limits::ReceiptSeconds};
        }
        if (request.operation == "cancel")
        {
            uint32 guid = request.bot.GetCounter();
            for (auto* pending : {&state.invites, &state.summons})
                for (auto it = pending->begin(); it != pending->end();)
                    if (it->second.owner == request.owner && (!guid || guid == it->first))
                    {
                        if (pending == &state.invites) { ClearInvite(it->second); ForgetInvite(it->first); }
                        Report(it->second, "cancelled", it->second.started ? "transfer_may_complete" : "requested");
                        it = pending->erase(it);
                    }
                    else ++it;
            for (auto it = state.reservations.begin(); it != state.reservations.end();)
                if (it->second.owner == request.owner && (!guid || guid == it->first)) it = state.reservations.erase(it);
                else ++it;
            Report(request, "cancelled", "completed_work_kept");
            return;
        }
        if (request.operation == "discover")
        {
            uint32 cls, low, high, cursor;
            std::string a,b,c,d,extra;
            std::istringstream args(request.arguments);
            args >> a >> b >> c >> d;
            if ((args >> extra) || !Number(a,cls) || !Number(b,low) || !Number(c,high) || !Number(d,cursor) ||
                !cls || cls > 11 || !low || high < low || high > sWorld.getConfig(CONFIG_UINT32_MAX_PLAYER_LEVEL))
            { Report(request,"refused","arguments"); return; }
            if (Now() < state.nextDiscovery || Now() < state.discoveryTime[owner->GetGUIDLow()])
            { Report(request,"refused","discovery_rate_limit"); return; }
            state.nextDiscovery = Now() + 1;
            state.discoveryTime[owner->GetGUIDLow()] = Now() + 2;
            auto const& bots = sRandomPlayerbotMgr.GetAllBots();
            auto it = bots.upper_bound(cursor);
            unsigned scanned = 0, returned = 0;
            std::string batch;
            for (; it != bots.end() && scanned < limits::ScanPerRequest && returned < limits::ResultsPerRequest; ++it)
            {
                ++scanned; cursor = it->first;
                Player* candidate = it->second;
                if (!IsBot(candidate) || candidate->getClass() != cls || candidate->GetLevel() < low || candidate->GetLevel() > high)
                    continue;
                if (!BotRecruitment::Eligibility(owner,candidate).empty()) continue;
                auto reservation = state.reservations.find(cursor);
                if (reservation != state.reservations.end() && reservation->second.owner != request.owner) continue;
                ++returned;
                std::string row = "PBRECRUIT 1 " + request.id + " " + std::to_string(cursor) + " eligible ok " +
                    candidate->GetName() + " " + std::to_string(cls) + " " + std::to_string(candidate->GetLevel());
                Tell(owner,row);
                batch += row + "\n";
            }
            Report(request,"complete", "cursor=" + std::to_string(it == bots.end() ? 0 : cursor) + ";scanned=" + std::to_string(scanned));
            if (!request.id.empty())
                state.receipts[{request.owner.GetCounter(),request.id}].response.insert(0,batch);
            return;
        }
        std::string reason = request.operation == "summon" || request.operation == "prepare" ?
            Control(owner,bot) : BotRecruitment::Eligibility(owner,bot);
        if (request.operation == "who")
        {
            if (!Identity(owner,bot).empty()) { Report(request,"refused","not_available_bot"); return; }
            if (!reason.empty() && reason != "existing")
            { Whisper(owner,bot,"Recruitment unavailable: " + reason); return; }
            if (!bot->IsInWorld() || bot->IsBeingTeleported())
            { Whisper(owner,bot,"Recruitment pending: transfer"); return; }
            WhoAction action(bot->GetPlayerbotAI());
            std::string reply = action.QuerySpec("");
            Player* master = bot->GetPlayerbotAI()->GetMaster();
            if (master) reply += ", playing with " + std::string(master->GetName());
            Whisper(owner,bot,reply);
            return;
        }
        if (request.operation == "status")
        {
            if (!Identity(owner,bot).empty()) { Report(request,"refused","not_available_bot"); return; }
            if (reason == "existing")
                Report(request, Arrived(owner,bot) ? "arrived" : "joined", Arrived(owner,bot) ? "ok" :
                    (Waiting(owner,bot).empty() ? "not_nearby" : Waiting(owner,bot)));
            else Report(request,reason.empty() ? "eligible" : "refused",reason.empty() ? "ok" : reason);
            return;
        }
        if (!reason.empty()) { Report(request,reason == "existing" ? "joined" : "refused",reason); return; }
        if (request.operation == "reserve" || request.operation == "invite")
        {
            auto reservation = state.reservations.find(bot->GetGUIDLow());
            if (reservation != state.reservations.end() && reservation->second.owner != request.owner)
            { Report(request,"refused","reserved"); return; }
            if (request.operation == "reserve")
            {
                unsigned count = 0;
                for (auto const& entry : state.reservations) if (entry.second.owner == request.owner) ++count;
                if (state.reservations.size() >= limits::MaxPending || count >= limits::MaxPendingPerPlayer) { Report(request,"refused","busy"); return; }
                state.reservations[bot->GetGUIDLow()] = {request.owner, Now() + limits::ReserveSeconds};
                Report(request,"reserved","expires_in=15"); return;
            }
            uint32 size;
            if (!Number(request.arguments,size) || !limits::ValidSize(size)) { Report(request,"refused","size_required"); return; }
            Group* group = InvitingGroup(owner);
            if (group && !group->IsLeader(request.owner)) { Report(request,"refused","not_leader"); return; }
            if (group && !limits::HasVacancy(group->GetMembersCount(),size,group->IsRaidGroup()))
            { Report(request,"refused","group_full"); return; }
            WorldPacket packet; packet << std::string(bot->GetName()); packet << uint32(0);
            owner->GetSession()->HandleGroupInviteOpcode(packet);
            if (!bot->GetGroupInvite()) { Report(request,"refused","native_invite_denied"); return; }
            request.size = size; request.leader = bot->GetGroupInvite()->GetLeaderGuid();
            request.invitation = bot->GetGroupInvite();
            request.expires = Now() + limits::InviteSeconds;
            if (!state.invites.count(bot->GetGUIDLow()) && !HasRoom(state.invites,request.owner))
            { ClearInvite(request); Report(request,"refused","busy"); return; }
            state.invites[bot->GetGUIDLow()] = request;
            Report(request,"invite_pending","ok"); return;
        }
        if (request.operation == "summon")
        {
            if (state.summons.count(bot->GetGUIDLow())) { Report(request,"summon_pending","existing_request"); return; }
            if (!HasRoom(state.summons,request.owner)) { Report(request,"refused","busy"); return; }
            request.expires = Now() + limits::SummonSeconds;
            request.leader = Party(owner) ? Party(owner)->GetLeaderGuid() : request.owner;
            request.membership = Party(owner);
            state.summons[bot->GetGUIDLow()] = request;
            Report(request,"summon_pending","waiting_for_safe_state"); return;
        }
        if (request.operation == "prepare")
        {
            if (!Arrived(owner,bot)) { Report(request,"refused","not_arrived"); return; }
            if (request.arguments != "gear" && request.arguments != "food" && request.arguments != "potions" &&
                request.arguments != "consumes" && request.arguments != "reagents" && request.arguments != "ammo") { Report(request,"refused","unsupported_preparation"); return; }
            // Explicit IDs provide replay safety; no implicit legacy deduplication here.
            state.explicitPreparation = true;
            PlayerbotHolder* holder = owner->GetPlayerbotMgr();
            if (!holder) holder = &sRandomPlayerbotMgr;
            std::string result = holder->ProcessBotCommand(request.arguments,request.bot,request.owner,
                false,owner->GetSession()->GetAccountId(),owner->GetGuildId());
            state.explicitPreparation = false;
            Report(request,result.find("refused:") == 0 || result == "Not in your guild or account" ||
                result == "Can not control alt-bots with this command." ? "refused" : "complete",result); return;
        }
        Report(request,"refused","unsupported_operation");
    }
}

std::string BotRecruitment::Eligibility(Player* owner, Player* bot)
{
    std::string reason = Identity(owner,bot);
    if (!reason.empty()) return reason;
    Group* group = Party(bot);
    if (group) return group == Party(owner) ? "existing" : "external_group";
    Player* master = bot->GetPlayerbotAI()->GetMaster();
    if (master && master->isRealPlayer() && master != owner) return "other_controller";
    if (owner->InBattleGround() || IsBusyQueue(bot)) return "queued_activity";
    if (bot->GetGroupInvite() && bot->GetGroupInvite() != InvitingGroup(owner)) return "invited_elsewhere";
    if (!bot->GetPlayerbotAI()->GetSecurity()->CheckLevelFor(PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE,true,owner)) return "recruitment_policy";
    return "";
}

bool BotRecruitment::CanInvite(Player* owner, Player* bot)
{
    if (!owner || !owner->isRealPlayer() || !bot || !bot->GetPlayerbotAI() || bot->isRealPlayer()) return true;
    std::string reason = Eligibility(owner,bot);
    auto reservation = State().reservations.find(bot->GetGUIDLow());
    if (reason.empty() && reservation != State().reservations.end() && reservation->second.expires > Now() && reservation->second.owner != owner->GetObjectGuid()) reason = "reserved";
    if (reason.empty() && !HasRoom(State().invites,owner->GetObjectGuid())) reason = "busy";
    if (reason.empty()) return true;
    Tell(owner,std::string(bot->GetName()) + ": invitation refused (" + reason + ")");
    return false;
}

void BotRecruitment::OnInvite(Player* owner, Player* bot)
{
    if (!owner || !owner->isRealPlayer() || !IsBot(bot) || !bot->GetGroupInvite()) return;
    Request request;
    request.ownerIdentity = EventOwner(owner); request.botIdentity = EventOwner(bot);
    request.owner = owner->GetObjectGuid(); request.bot = bot->GetObjectGuid(); request.operation = "accept";
    request.invitation = bot->GetGroupInvite();
    request.leader = bot->GetGroupInvite()->GetLeaderGuid(); request.expires = Now() + limits::InviteSeconds;
    // Native human invitations reach here on the world thread. Replace any
    // superseded invitation immediately so its old deadline cannot clear this one.
    auto previous = State().invites.find(bot->GetGUIDLow());
    if (previous != State().invites.end()) Report(previous->second,"cancelled","superseded");
    State().invites[bot->GetGUIDLow()] = request;
    std::lock_guard<std::mutex> guard(State().mutex);
    State().managedInvites.insert(bot->GetGUIDLow());
}

bool BotRecruitment::HasPendingInvite(Player* bot)
{
    if (!bot) return false;
    std::lock_guard<std::mutex> guard(State().mutex);
    return State().managedInvites.count(bot->GetGUIDLow()) != 0;
}

bool BotRecruitment::Queue(Player* owner, Player* bot, const std::string& operation)
{
    if (!owner || !bot || !owner->isRealPlayer() || bot->isRealPlayer()) return false;
    Request request;
    request.ownerIdentity = EventOwner(owner); request.botIdentity = EventOwner(bot);
    request.owner = owner->GetObjectGuid(); request.bot = bot->GetObjectGuid(); request.operation = operation;
    if (operation == "invite") request.arguments = "40";
    request.expires = Now() + limits::InviteSeconds;
    if (Enqueue(request)) return true;
    Tell(owner,"Bot request refused: busy; retry.");
    return false;
}

bool BotRecruitment::HandleCommand(Player* owner, const std::string& command)
{
    if (command.compare(0,8,"recruit ") != 0) return false;
    std::istringstream input(command);
    std::string prefix,version,id,operation,guid;
    input >> prefix >> version >> id >> operation;
    if (command.size() > 240 || version != "v1" || id.empty() || id.size() > 32 ||
        id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != std::string::npos)
    { Tell(owner,"PBRECRUIT 1 - 0 refused syntax"); return true; }
    if (operation != "discover" && operation != "status" && operation != "reserve" &&
        operation != "invite" && operation != "summon" && operation != "prepare" && operation != "cancel")
    { Tell(owner,"PBRECRUIT 1 " + id + " 0 refused unsupported_operation"); return true; }
    Request request; request.owner = owner->GetObjectGuid(); request.id = id; request.operation = operation;
    if (operation != "discover")
    {
        uint32 number;
        input >> guid;
        if (!Number(guid,number)) { Tell(owner,Response(request,"refused","guid_required")); return true; }
        if (number) request.bot = ObjectGuid(HIGHGUID_PLAYER,number);
    }
    std::getline(input,request.arguments);
    if (!request.arguments.empty() && request.arguments[0] == ' ') request.arguments.erase(0,1);
    request.ownerIdentity = EventOwner(owner);
    request.botIdentity = EventOwner(Find(request.bot));
    request.expires = Now() + limits::InviteSeconds;
    if (!Enqueue(request)) Tell(owner,Response(request,"refused","busy"));
    return true;
}

void BotRecruitment::Update(uint32 diff)
{
    Service& state = State();
    state.elapsed += diff;
    if (state.elapsed < limits::TickMilliseconds) return;
    state.elapsed = 0;
    uint64 now = Now();
    for (auto it = state.receipts.begin(); it != state.receipts.end();)
        if (limits::Expired(now,it->second.expires)) it = state.receipts.erase(it); else ++it;
    for (auto it = state.preparation.begin(); it != state.preparation.end();)
        if (limits::Expired(now,it->second.expires)) it = state.preparation.erase(it); else ++it;
    for (auto it = state.discoveryTime.begin(); it != state.discoveryTime.end();)
        if (limits::Expired(now,it->second)) it = state.discoveryTime.erase(it); else ++it;
    for (auto it = state.reservations.begin(); it != state.reservations.end();)
        if (limits::Expired(now,it->second.expires) || !Connected(Find(it->second.owner))) it = state.reservations.erase(it); else ++it;
    std::deque<Request> incoming;
    {
        std::lock_guard<std::mutex> guard(state.mutex);
        for (unsigned i = 0; i < limits::CommandsPerTick && !state.incoming.empty(); ++i)
        { incoming.push_back(state.incoming.front()); state.incoming.pop_front(); }
    }
    for (auto const& request : incoming) Dispatch(request);
    unsigned accepted = 0;
    for (auto it = state.invites.begin(); it != state.invites.end();)
    {
        Request request = it->second;
        Player* owner = Find(request.owner); Player* bot = Find(request.bot);
        std::string reason = limits::Expired(now,request.expires) ? "deadline" :
            request.ownerIdentity.Get() != owner || !owner ? "requester_session_changed" :
            request.botIdentity.Get() != bot || !bot ? "bot_session_changed" : InviteReason(request,owner,bot);
        if (reason == "bot_transfer" || reason == "requester_transfer" || reason == "controlled") { ++it; continue; }
        if (reason.empty() && accepted >= 8) { ++it; continue; }
        if (reason.empty())
        {
            ++accepted;
            if (bot->isAFK()) bot->ToggleAFK();
            WorldPacket packet; packet << uint32(0);
            bot->GetSession()->HandleGroupAcceptOpcode(packet);
            if (Party(bot) && Party(bot) == Party(owner))
            {
                // Preserve health, death state, equipment, talents and combat.
                bot->GetPlayerbotAI()->SetMaster(owner);
                bot->GetPlayerbotAI()->ChangeStrategy("-lfg,-bg,+" + bot->GetPlayerbotAI()->GetDefaultMovementStrategy(),BotState::BOT_STATE_NON_COMBAT);
                Report(request,"joined","ok");
            }
            else { ClearInvite(request); Report(request,"refused","accept_failed"); }
        }
        else { ClearInvite(request); Report(request,reason == "deadline" ? "timed_out" : "refused",reason); }
        state.reservations.erase(it->first);
        ForgetInvite(it->first);
        it = state.invites.erase(it);
    }
    unsigned teleports = 0;
    for (auto it = state.summons.begin(); it != state.summons.end();)
    {
        Request& request = it->second;
        Player* owner = Find(request.owner); Player* bot = Find(request.bot);
        std::string reason = request.ownerIdentity.Get() != owner || !owner ? "requester_session_changed" :
            request.botIdentity.Get() != bot || !bot ? "bot_session_changed" : Control(owner,bot);
        if (reason.empty() && (Party(owner) ? Party(owner)->GetLeaderGuid() : request.owner) != request.leader) reason = "leader_changed";
        if (reason.empty() && request.membership &&
            (Party(owner) != request.membership || Party(bot) != request.membership)) reason = "membership_changed";
        if (reason.empty() && limits::Expired(now,request.expires)) reason = "deadline";
        if (!reason.empty())
        { Report(request,reason == "deadline" ? "timed_out" : "refused",reason); it = state.summons.erase(it); continue; }
        if (request.started && owner->IsInWorld() && (owner->GetMapId() != request.map || owner->GetInstanceId() != request.instance))
        { Report(request,"refused","destination_changed"); it = state.summons.erase(it); continue; }
        if (Arrived(owner,bot))
        { Report(request,"arrived","ok"); it = state.summons.erase(it); continue; }
        reason = Waiting(owner,bot);
        if (reason == "revival_disabled" || reason == "queued_activity")
        { Report(request,"refused",reason); it = state.summons.erase(it); continue; }
        if (reason.empty() && !request.started && teleports < 2)
        {
            ++teleports;
            if (owner->GetMapId() == bot->GetMapId() && owner->GetInstanceId() != bot->GetInstanceId())
            { Report(request,"refused","different_instance"); it = state.summons.erase(it); continue; }
            SummonAction action(bot->GetPlayerbotAI());
            Event event("summon", "", owner);
            request.map = owner->GetMapId(); request.instance = owner->GetInstanceId();
            request.started = action.ExecuteImmediate(event);
            if (!request.started)
            { Report(request,"refused","destination_or_summon_policy"); it = state.summons.erase(it); continue; }
            Report(request,"summon_pending","teleport_started");
        }
        ++it;
    }
}

bool BotRecruitment::IsPreparation(const std::string& command)
{
    return command == "gear" || command == "equip" || command == "food" || command == "drink" ||
        command == "potions" || command == "pots" || command == "consumes" || command == "consumables" || command == "consums" ||
        command == "reagents" || command == "regs" || command == "reg" || command == "ammo";
}

std::string BotRecruitment::PreparationReason(Player* owner, Player* bot)
{
    std::string reason = Control(owner,bot);
    if (!reason.empty()) return reason;
    if (!owner->IsInWorld() || owner->IsBeingTeleported() || !bot->IsInWorld() || bot->IsBeingTeleported()) return "transfer";
    if (!bot->IsAlive()) return "dead";
    if (bot->IsInCombat() || owner->IsInCombat()) return "combat";
    if (bot->HasCharmer() || bot->GetTransport() || bot->IsTaxiFlying()) return "transport_or_controlled";
    if (owner->InBattleGround() || bot->InBattleGround()) return "battleground";
    return "";
}

std::string BotRecruitment::Prepare(Player* owner, Player* bot, const std::string& command,
    const std::string& parameter, const std::function<std::string()>& apply)
{
    std::string reason = PreparationReason(owner,bot);
    if (!reason.empty()) return "refused: " + reason;
    // No distance restriction for manual preparation. Pending summons must finish.
    auto summon = State().summons.find(bot->GetGUIDLow());
    if (summon != State().summons.end()) return "refused: summon_pending";
    std::string key = std::to_string(owner->GetGUIDLow()) + ":" + std::to_string(bot->GetGUIDLow()) + ":" +
        command + ":" + parameter + ":" + std::to_string(bot->GetLevel()) + ":" + TalentSpec(bot).GetTalentLink();
    auto old = State().preparation.find(key);
    if (!State().explicitPreparation && old != State().preparation.end() && old->second.expires > Now())
        return old->second.response;
    if (State().preparation.size() >= limits::MaxReceipts) return "refused: busy";
    if (State().preparationSecond != Now())
    {
        State().preparationSecond = Now();
        State().gearWork = State().supplyWork = 0;
        State().playerPreparationWork.clear();
    }
    bool gear = command == "gear" || command == "equip";
    unsigned& work = gear ? State().gearWork : State().supplyWork;
    unsigned& playerWork = State().playerPreparationWork[owner->GetGUIDLow()];
    if (work >= (gear ? 2u : 32u) || playerWork >= 8) return "refused: preparation_rate_limit";
    ++work; ++playerWork;
    if ((command == "gear" || command == "equip") && !sRandomItemMgr.GetPlayerSpecId(bot))
        return "refused: unsupported_spec";
    std::string result = apply();
    if (result.find("refused:") != 0)
        State().preparation[key] = {"",result,Now() + limits::LegacyPreparationSeconds};
    return result;
}
