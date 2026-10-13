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
#include <memory>
#include "LFG/LFGQueue.h"
#include <set>
#include <sstream>
#include <cctype>
#include <iomanip>

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
        std::string id, operation, arguments, epoch;
        bool diagnostics = false;
        bool arrivalEvaluated = false;
        limits::ArrivalResult arrival;
        std::string diagnosticStage, diagnosticReason, mutation = "none";
        uint64 expires = 0;
        unsigned size = 40;
        uint32 map = 0, instance = 0;
        uint32 entryMap = 0;
        bool started = false;
        bool leftPreviousInstance = false;
        unsigned attempts = 0;
        uint64 nextAttempt = 0;
        float x = 0, y = 0, z = 0;
        std::string waitReason;
        std::shared_ptr<bool> queuesCancelled;
    };
    struct Receipt
    {
        std::string payload, response;
        uint64 expires;
        std::string diagnostic;
        std::string recoveryResponse, recoveryDiagnostic;
    };
    struct Reservation
    {
        ObjectGuid owner;
        uint64 expires;
    };
    struct PreparationTrace
    {
        bool entered = false;
        std::string refusal;
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
        // Terminal preparation decisions stay replayable for this process.
        // Never evict a gear receipt and allow the same ID to reroll equipment.
        std::map<std::pair<uint32, std::string>, Receipt> preparationReceipts;
        std::map<std::string, Receipt> preparation;
        std::map<uint32, uint64> discoveryTime;
        uint32 elapsed = 0;
        uint64 nextDiscovery = 0;
        bool explicitPreparation = false;
        PreparationTrace* preparationTrace = nullptr;
        const std::string epoch = std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        uint64 diagnosticSecond = 0;
        unsigned diagnosticWork = 0;
        std::map<uint32, unsigned> diagnosticOwnerWork;
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
        return request.operation + " " + std::to_string(request.bot.GetCounter()) + " " + request.arguments +
            (request.epoch.empty() ? "" : " diag_epoch=" + request.epoch);
    }
    std::string Response(Request const& request, const std::string& status, const std::string& reason)
    {
        return "PBRECRUIT 1 " + request.id + " " + std::to_string(request.bot.GetCounter()) +
            " " + status + " " + reason;
    }
    std::string Diagnostic(Request const& request, const std::string& status, const std::string& reason)
    {
        std::string stage = request.diagnosticStage;
        if (stage.empty()) stage = request.operation == "prepare" ? "pre_mutation_refused" : request.operation == "status" ? "current_readiness" :
            request.operation == "summon" && status == "arrived" ? "accepted_landing" : "not_evaluated";
        std::string condition = request.diagnosticReason;
        if (condition.empty()) condition = request.arrivalEvaluated && !request.arrival.Ready() ?
            limits::ArrivalReason(request.arrival.condition) : request.diagnosticStage == "pre_mutation_refused" ? reason :
            request.arrivalEvaluated ? "ok" : reason;
        for (char& c : condition) if (!std::isalnum(static_cast<unsigned char>(c)) && c != '_') c = '_';
        if (condition.empty()) condition = "unknown";
        if (condition.size() > 96) condition.resize(96);
        auto location = [](bool known, uint32 value) { return known ? std::to_string(value) : "na"; };
        std::ostringstream out;
        out << "PBRECRUIT_DIAG 1 " << (request.id.empty() ? "-" : request.id) << " " << request.owner.GetCounter()
            << " " << request.bot.GetCounter() << " " << request.operation << " " << stage << " " << condition << " ";
        if (request.arrival.distanceKnown) out << std::fixed << std::setprecision(6) << request.arrival.distance;
        else out << "na";
        out << " " << std::fixed << std::setprecision(6) << request.arrival.limit
            << " " << location(request.arrival.requesterLocationKnown, request.arrival.requesterMap)
            << " " << location(request.arrival.requesterLocationKnown, request.arrival.requesterInstance)
            << " " << location(request.arrival.botLocationKnown, request.arrival.botMap)
            << " " << location(request.arrival.botLocationKnown, request.arrival.botInstance)
            << " " << request.mutation;
        return out.str();
    }
    void LogDiagnostic(Request const& request, const std::string& diagnostic)
    {
        Service& state = State();
        if (state.diagnosticSecond != Now())
        {
            state.diagnosticSecond = Now(); state.diagnosticWork = 0; state.diagnosticOwnerWork.clear();
        }
        if (state.diagnosticWork >= limits::DiagnosticEventsPerSecond) return;
        unsigned& count = state.diagnosticOwnerWork[request.owner.GetCounter()];
        if (count >= limits::DiagnosticEventsPerPlayerPerSecond) return;
        ++count; ++state.diagnosticWork;
        sLog.outString("PLAYERBOT_RECRUIT_DIAG: %s", diagnostic.c_str());
    }
    void Replay(Player* owner, Receipt const& receipt, bool diagnostics)
    {
        if (!receipt.recoveryResponse.empty()) Tell(owner,receipt.recoveryResponse);
        if (!receipt.recoveryDiagnostic.empty()) Tell(owner,receipt.recoveryDiagnostic);
        Tell(owner, receipt.response);
        if (diagnostics && !receipt.diagnostic.empty()) Tell(owner, receipt.diagnostic);
    }
    void RejectUncached(Request request, Player* owner, const std::string& reason)
    {
        request.diagnosticStage = "pre_mutation_refused"; request.diagnosticReason = reason;
        const std::string diagnostic = Diagnostic(request,"refused",reason);
        Tell(owner,Response(request,"refused",reason));
        if (request.diagnostics) Tell(owner,diagnostic);
        if (request.operation == "prepare" || request.diagnostics) LogDiagnostic(request,diagnostic);
    }
    void Report(Request const& request, const std::string& status, const std::string& reason)
    {
        std::string response = Response(request, status, reason);
        std::string diagnostic = Diagnostic(request, status, reason);
        if (!request.id.empty())
        {
            auto it = State().receipts.find({request.owner.GetCounter(), request.id});
            if (it != State().receipts.end())
            { it->second.response = response; it->second.diagnostic = diagnostic; }
            auto retained = State().preparationReceipts.find({request.owner.GetCounter(), request.id});
            if (retained != State().preparationReceipts.end())
            { retained->second.response = response; retained->second.diagnostic = diagnostic; }
            Tell(Find(request.owner), response);
            if (request.diagnostics) Tell(Find(request.owner), diagnostic);
        }
        else
        {
            Player* bot = Find(request.bot);
            Tell(Find(request.owner), std::string(bot ? bot->GetName() : "Bot") + ": " + status + " (" + reason + ")");
        }
        if (request.operation == "prepare" || request.diagnostics) LogDiagnostic(request, diagnostic);
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
        if (sObjectMgr.GetPlayer(bot->GetName()) != bot) return "name_identity_conflict";
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
                // Reserve a separate full-raid intake for summon bursts.
                // Other recruitment requests retain their smaller bound.
                if ((pending.operation == "summon") == (request.operation == "summon")) ++count;
            }
        }
        const unsigned ownerLimit = request.operation == "summon" ?
            limits::MaxPendingPerPlayer : limits::MaxIncomingPerPlayer;
        if (count >= ownerLimit) return false;
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
        if (!owner->IsInWorld() || owner->IsBeingTeleported()) return "requester_transfer";
        if (!bot->IsInWorld() || bot->IsBeingTeleported()) return "bot_transfer";
        if (owner->GetTransport() || owner->IsTaxiFlying()) return "requester_transport";
        // Bot combat, death, control, flights and queues are cancelled by the
        // explicit summon action. Never wait for autonomous activity to finish.
        return "";
    }

    bool LeavePreviousRaid(Player* owner, Player* bot)
    {
        // A native same-map teleport is a near teleport, even when the two
        // players occupy different raid copies. Leave the old map first and
        // retain its bind until the worldport has finished.
        Group* group = Party(owner);
        Map* destination = owner->GetMap();
        if (!owner->isRealPlayer() || bot->isRealPlayer() ||
            !sPlayerbotAIConfig.IsInRandomAccountList(bot->GetSession()->GetAccountId()) ||
            !group || group != Party(bot) || group != owner->GetGroup() ||
            group != bot->GetGroup() || !group->IsRaidGroup() ||
            !destination || !destination->IsRaid() || !bot->GetMap()->IsRaid() ||
            owner->GetMapId() != bot->GetMapId() ||
            owner->GetInstanceId() == bot->GetInstanceId())
            return false;
#ifdef MANGOSBOT_ZERO
        InstanceGroupBind* groupBind = group->GetBoundInstance(owner->GetMapId());
#else
        InstanceGroupBind* groupBind = group->GetBoundInstance(destination, destination->GetDifficulty());
#endif
        if (!groupBind || groupBind->state != destination->GetPersistentState())
            return false;
        DungeonMap* raid = static_cast<DungeonMap*>(destination);
        if (raid->GetPlayersCountExceptGMs() >= raid->GetMaxPlayers() ||
            (raid->GetInstanceData() && raid->GetInstanceData()->IsEncounterInProgress()))
            return false;

        float x, y, z;
        uint32 homeMap;
        bot->GetHomebindLocation(x, y, z, homeMap);
        MapEntry const* home = sMapStore.LookupEntry(homeMap);
        if (!home || home->Instanceable() || homeMap == bot->GetMapId())
            return false;
        bot->BreakCharmIncoming();
        bot->BreakCharmOutgoing();
        if (bot->HasCharmer()) return false;
        if (!bot->TaxiFlightInterrupt() && bot->IsTaxiFlying())
            bot->OnTaxiFlightEject();
        bot->InterruptNonMeleeSpells(false);
        if (!bot->TeleportToHomebind()) return false;
        SummonAction::CancelAutonomousQueues(bot);
        bot->GetPlayerbotAI()->ChangeStrategy("-lfg,-bg", BotState::BOT_STATE_NON_COMBAT);
        sLog.outString("PLAYERBOT_SUMMON: public bot %u leaving previous raid instance for group map %u instance %u requester %u",
            bot->GetGUIDLow(), owner->GetMapId(), owner->GetInstanceId(), owner->GetGUIDLow());
        return true;
    }
    limits::ArrivalResult EvaluateArrival(Player* owner, Player* bot)
    {
        limits::ArrivalResult result;
        const bool ownerWorld = owner && owner->IsInWorld(), botWorld = bot && bot->IsInWorld();
        const bool ownerTransfer = owner && owner->IsBeingTeleported(), botTransfer = bot && bot->IsBeingTeleported();
        if (ownerWorld && !ownerTransfer)
        { result.requesterLocationKnown = true; result.requesterMap = owner->GetMapId(); result.requesterInstance = owner->GetInstanceId(); }
        if (botWorld && !botTransfer)
        { result.botLocationKnown = true; result.botMap = bot->GetMapId(); result.botInstance = bot->GetInstanceId(); }
        using C = limits::ArrivalCondition;
        if (!ownerWorld) result.condition = C::RequesterNotInWorld;
        else if (!botWorld) result.condition = C::BotNotInWorld;
        else if (ownerTransfer) result.condition = C::RequesterTransferring;
        else if (botTransfer) result.condition = C::BotTransferring;
        else if (!bot->IsAlive()) result.condition = C::BotDead;
        else if (result.botMap != result.requesterMap) result.condition = C::DifferentMap;
        else if (result.botInstance != result.requesterInstance || bot->GetMap() != owner->GetMap()) result.condition = C::DifferentInstance;
        else
        {
            // No distance or LOS access until both native objects are usable
            // and belong to the same map object and instance.
            result.distance = bot->GetDistance(owner);
            result.distanceKnown = std::isfinite(result.distance);
            if (!result.distanceKnown || result.distance > result.limit) result.condition = C::TooFar;
            else if (!bot->IsWithinLOSInMap(owner)) result.condition = C::NoLineOfSight;
        }
        return result;
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
        if (!Connected(owner) || request.ownerIdentity.Get() != owner)
        {
            if (request.operation == "prepare") LogDiagnostic(request,Diagnostic(request,"refused","requester_session_changed"));
            return;
        }
        if (!request.epoch.empty() && request.epoch != state.epoch)
        {
            RejectUncached(request,owner,"epoch_changed");
            return;
        }
        if (!request.id.empty())
        {
            auto key = std::make_pair(request.owner.GetCounter(), request.id);
            auto retained = state.preparationReceipts.find(key);
            auto previous = state.receipts.find(key);
            const Receipt* receipt = retained != state.preparationReceipts.end() ? &retained->second :
                previous != state.receipts.end() ? &previous->second : nullptr;
            if (receipt)
            {
                if (receipt->payload == Payload(request)) Replay(owner,*receipt,request.diagnostics);
                else RejectUncached(request,owner,"id_conflict");
                return;
            }
        }
        if (request.bot && request.botIdentity.Get() != bot)
        { Report(request,"refused","bot_session_changed"); return; }
        if (request.entryMap && (Party(owner) != request.membership ||
            Party(bot) != request.membership || !request.membership ||
            request.membership->GetLeaderGuid() != request.leader))
        { Report(request,"refused","membership_changed"); return; }
        if (limits::Expired(Now(), request.expires))
        {
            if (request.operation == "accept") ClearInvite(request);
            Report(request, "timed_out", "queue_deadline");
            return;
        }
        if (!request.id.empty())
        {
            auto key = std::make_pair(request.owner.GetCounter(), request.id);
            unsigned count = 0;
            for (auto const& receipt : state.receipts) if (receipt.first.first == key.first) ++count;
            if (state.receipts.size() >= limits::MaxReceipts || count >= limits::MaxReceiptsPerPlayer)
            {
                RejectUncached(request, owner, "receipt_limit");
                return;
            }
            if (request.operation == "prepare")
            {
                unsigned retained = 0;
                for (auto const& receipt : state.preparationReceipts) if (receipt.first.first == key.first) ++retained;
                if (state.preparationReceipts.size() >= limits::MaxPreparationReceipts || retained >= limits::MaxPreparationReceiptsPerPlayer)
                { RejectUncached(request,owner,"receipt_limit"); return; }
                state.preparationReceipts[key] = {Payload(request),Response(request,"pending","queued"),0};
            }
            state.receipts[key] = {Payload(request), Response(request, "pending", "queued"), Now() + limits::ReceiptSeconds};
        }
        if (request.operation == "capabilities")
        {
            if (!owner->isRealPlayer() || request.bot || !request.arguments.empty()) { Report(request,"refused","syntax"); return; }
            Report(request,"complete","arrival_diag_v1=1;receipt_v1=1;epoch=" + state.epoch + ";receipt_seconds=600;prepare_receipts=process"); return;
        }
        if (request.operation == "receipt")
        {
            auto key = std::make_pair(request.owner.GetCounter(),request.arguments);
            auto retained = state.preparationReceipts.find(key); auto previous = state.receipts.find(key);
            const Receipt* receipt = retained != state.preparationReceipts.end() ? &retained->second :
                previous != state.receipts.end() ? &previous->second : nullptr;
            if (!receipt) { Report(request,"unknown","receipt_missing"); return; }
            std::istringstream payload(receipt->payload); std::string operation; uint32 guid = 0; payload >> operation >> guid;
            if (guid != request.bot.GetCounter()) { Report(request,"refused","receipt_bot_mismatch"); return; }
            const std::string recovered = receipt->response, detail = receipt->diagnostic;
            Replay(owner,*receipt,true); Report(request,"complete","receipt_found");
            auto current = state.receipts.find({request.owner.GetCounter(),request.id});
            if (current != state.receipts.end())
            { current->second.recoveryResponse = recovered; current->second.recoveryDiagnostic = detail; }
            return;
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
#if defined(MANGOSBOT_ZERO)
            const uint32 expansionLevelCap = 60;
#elif defined(MANGOSBOT_ONE)
            const uint32 expansionLevelCap = 70;
#else
            const uint32 expansionLevelCap = 80;
#endif
            uint32 cls, low, high, cursor;
            std::string a,b,c,d,extra;
            std::istringstream args(request.arguments);
            args >> a >> b >> c >> d;
            if ((args >> extra) || !Number(a,cls) || !Number(b,low) || !Number(c,high) || !Number(d,cursor) ||
                !cls || cls > 11 || !low || high < low || high > expansionLevelCap ||
                high > sWorld.getConfig(CONFIG_UINT32_MAX_PLAYER_LEVEL))
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
            {
                request.arrival = EvaluateArrival(owner,bot); request.arrivalEvaluated = true;
                Report(request, request.arrival.Ready() ? "arrived" : "joined", request.arrival.Ready() ? "ok" :
                    (Waiting(owner,bot).empty() ? "not_nearby" : Waiting(owner,bot)));
            }
            else Report(request,reason.empty() ? "eligible" : "refused",reason.empty() ? "ok" : reason);
            return;
        }
        if (!reason.empty())
        {
            if (request.operation == "prepare") request.diagnosticStage = "pre_mutation_refused";
            Report(request,reason == "existing" ? "joined" : "refused",reason); return;
        }
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
            auto pending = state.summons.find(bot->GetGUIDLow());
            if (pending != state.summons.end())
            {
                // Preserve an in-flight transfer; acknowledge the actual stage.
                // Different owners must never refresh another player's request.
                if (pending->second.owner != request.owner)
                { Report(request,"refused","other_controller"); return; }
                // Protocol clients poll status after existing_request; their
                // duplicate ID is not the owner of the original completion.
                Report(request,"summon_pending",!request.id.empty() ? "existing_request" :
                    (pending->second.waitReason.empty() ? "teleport_started" : pending->second.waitReason));
                return;
            }
            if (!HasRoom(state.summons,request.owner)) { Report(request,"refused","busy"); return; }
            request.expires = Now() + limits::SummonSeconds;
            request.leader = Party(owner) ? Party(owner)->GetLeaderGuid() : request.owner;
            request.membership = Party(owner);
            state.summons[bot->GetGUIDLow()] = request;
            Report(request,"summon_pending","queued"); return;
        }
        if (request.operation == "prepare")
        {
            request.arrival = EvaluateArrival(owner,bot); request.arrivalEvaluated = true;
            request.diagnosticStage = "pre_mutation_refused";
            if (!request.arrival.Ready()) { Report(request,"refused","not_arrived"); return; }
            if (request.arguments != "gear" && request.arguments != "food" && request.arguments != "potions" &&
                request.arguments != "consumes" && request.arguments != "reagents" && request.arguments != "ammo") { Report(request,"refused","unsupported_preparation"); return; }
            // Explicit IDs provide replay safety; no implicit legacy deduplication here.
            PreparationTrace trace;
            struct Scope
            {
                Service& state; bool oldExplicit; PreparationTrace* oldTrace;
                Scope(Service& s, PreparationTrace& t) : state(s), oldExplicit(s.explicitPreparation), oldTrace(s.preparationTrace)
                { state.explicitPreparation = true; state.preparationTrace = &t; }
                ~Scope() { state.explicitPreparation = oldExplicit; state.preparationTrace = oldTrace; }
            } scope(state,trace);
            PlayerbotHolder* holder = owner->GetPlayerbotMgr();
            if (!holder) holder = &sRandomPlayerbotMgr;
            std::string result = holder->ProcessBotCommand(request.arguments,request.bot,request.owner,
                false,owner->GetSession()->GetAccountId(),owner->GetGuildId());
            const bool refused = result.find("refused:") == 0 || result == "Not in your guild or account" ||
                result == "Can not control alt-bots with this command.";
            request.mutation = trace.entered ? (refused ? "uncertain" : "completed") : "none";
            request.diagnosticStage = trace.entered ? (refused ? "mutation_uncertain" : "mutation_complete") :
                (refused ? "pre_mutation_refused" : "no_mutation_complete");
            request.diagnosticReason = trace.refusal.empty() ? (refused ?
                (result.find("refused:") == 0 ? result.substr(8) : result) : "ok") : trace.refusal;
            while (!request.diagnosticReason.empty() && request.diagnosticReason[0] == ' ') request.diagnosticReason.erase(0,1);
            Report(request,refused ? "refused" : "complete",result); return;
        }
        Report(request,"refused","unsupported_operation");
    }
}

std::string BotRecruitment::Eligibility(Player* owner, Player* bot)
{
    std::string reason = Identity(owner,bot);
    if (!reason.empty()) return reason;
    // Discovery is GUID-addressed, but native invitations and subsequent bot
    // whispers resolve a name. Duplicate database names must never redirect an
    // invitation to a different player (including a real player or lower level
    // bot). Recheck on reserve/invite/status too, not just during discovery.
    if (sObjectMgr.GetPlayer(bot->GetName()) != bot) return "name_identity_conflict";
    Group* group = Party(bot);
    if (group) return group == Party(owner) ? "existing" : "external_group";
    Player* master = bot->GetPlayerbotAI()->GetMaster();
    if (master && master->isRealPlayer() && master != owner) return "other_controller";
    if (owner->InBattleGround()) return "requester_battleground";
    if (bot->GetGroupInvite() && bot->GetGroupInvite() != InvitingGroup(owner)) return "invited_elsewhere";
    // Queue enrollment is autonomous activity, not ownership. Keep every other
    // permission check, then cancel personal queues only when accepting the invite.
    if (bot->GetPlayerbotAI()->GetSecurity()->LevelFor(owner, nullptr, false, true) <
        PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE) return "recruitment_policy";
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

void BotRecruitment::FollowMoltenCoreEntry(Player* owner, const WorldPacket& packet)
{
    if (!Connected(owner) || !owner->isRealPlayer() ||
        !owner->IsBeingTeleportedFar() || owner->GetMapId() != 0 ||
        owner->GetTeleportDest().mapid != 409 || packet.size() < 8)
        return;
    WorldPacket copy(packet);
    copy.rpos(0);
    ObjectGuid npc;
    copy >> npc;
    // Lothos Riftwaker is the same creature entry in all three client eras.
    if (!npc.IsCreature() || npc.GetEntry() != 14387)
        return;
    Group* group = Party(owner);
    if (!group || !group->IsRaidGroup())
        return;

    unsigned queued = 0;
    for (GroupReference* member = group->GetFirstMember(); member; member = member->next())
    {
        Player* follower = member->getSource();
        // The human accepted entry for this raid's companions. Capture the
        // entire authorized roster, including stragglers and public bots in
        // another MC save. The coordinator owns native transfer/lockout checks.
        if (!IsBot(follower) || Party(follower) != group || !Control(owner, follower).empty())
            continue;
        Request request;
        request.owner = owner->GetObjectGuid(); request.bot = follower->GetObjectGuid();
        request.ownerIdentity = EventOwner(owner); request.botIdentity = EventOwner(follower);
        request.operation = "summon"; request.expires = Now() + limits::SummonSeconds;
        request.entryMap = 409;
        request.membership = group; request.leader = group->GetLeaderGuid();
        if (Enqueue(request)) ++queued;
        else Report(request, "refused", "busy");
    }
    sLog.outString("PLAYERBOT_RAID_ENTRY: requester %u Lothos transfer accepted; queued %u authorized raid companions",
        owner->GetGUIDLow(), queued);
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
    const bool diagnostics = operation == "status_diag" || operation == "prepare_diag" || operation == "summon_diag";
    if (diagnostics) operation.erase(operation.size()-5);
    if (operation != "discover" && operation != "status" && operation != "reserve" &&
        operation != "invite" && operation != "summon" && operation != "prepare" && operation != "cancel" &&
        operation != "capabilities" && operation != "receipt")
    { Tell(owner,"PBRECRUIT 1 " + id + " 0 refused unsupported_operation"); return true; }
    Request request; request.owner = owner->GetObjectGuid(); request.id = id; request.operation = operation;
    request.diagnostics = diagnostics;
    if (operation != "discover")
    {
        uint32 number;
        input >> guid;
        if (!Number(guid,number)) { Tell(owner,Response(request,"refused","guid_required")); return true; }
        if (number) request.bot = ObjectGuid(HIGHGUID_PLAYER,number);
    }
    std::getline(input,request.arguments);
    if (!request.arguments.empty() && request.arguments[0] == ' ') request.arguments.erase(0,1);
    if (diagnostics || operation == "receipt")
    {
        std::istringstream args(request.arguments); std::string argument, extra;
        if (operation == "prepare" || operation == "receipt") args >> argument;
        args >> request.epoch;
        if (request.epoch.empty() || request.epoch.size() > 32 || args >> extra ||
            request.epoch.find_first_not_of("0123456789") != std::string::npos ||
            (operation == "receipt" && (argument.empty() || argument == request.id || argument.size()>32 ||
                argument.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != std::string::npos)))
        { Tell(owner,Response(request,"refused","syntax")); return true; }
        request.arguments = argument;
    }
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
            if (!request.queuesCancelled)
            {
                request.queuesCancelled = std::make_shared<bool>(false);
                it->second.queuesCancelled = request.queuesCancelled;
                SummonAction::CancelAutonomousQueues(bot);
                // Drain earlier LFG matchmaking callbacks before accepting. Otherwise
                // an already queued match could move this bot out of its new party.
                auto ready = request.queuesCancelled;
                sWorld.GetLFGQueue().GetMessager().AddMessage([ready](LFGQueue*)
                {
                    sWorld.GetMessager().AddMessage([ready](World*) { *ready = true; });
                });
            }
            if (!*request.queuesCancelled) { ++it; continue; }
            ++accepted;
            if (bot->isAFK()) bot->ToggleAFK();
            WorldPacket packet; packet << uint32(0);
            bot->GetSession()->HandleGroupAcceptOpcode(packet);
            if (Party(bot) && Party(bot) == Party(owner))
            {
                // Preserve health, death state, equipment, talents and combat.
                bot->GetPlayerbotAI()->SetMaster(owner);
                // The legacy invitation action reset off-map bot raid binds.
                // Managed human invites must also prepare public companions for
                // the requester's established raid save, without resetting players.
                SummonAction::PrepareRaidBinding(owner, bot);
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
        if (reason.empty() && limits::Expired(now,request.expires))
        {
            reason = Waiting(owner,bot);
            if (reason.empty()) reason = request.started ? "arrival_not_confirmed" :
                (request.waitReason.empty() ? "work_budget" : request.waitReason);
            Report(request,"timed_out",reason);
            it = state.summons.erase(it); continue;
        }
        if (!reason.empty())
        { Report(request,reason == "deadline" ? "timed_out" : "refused",reason); it = state.summons.erase(it); continue; }
        if (request.entryMap && owner->IsInWorld() && !owner->IsBeingTeleported())
        {
            if (owner->GetMapId() != request.entryMap)
            { Report(request,"refused","raid_entry_failed"); it = state.summons.erase(it); continue; }
            if (!request.started && bot->IsInWorld() && !bot->IsBeingTeleported())
            {
                // An independently completed NPC/portal entry needs no second
                // teleport or refill. Other raid copies use LeavePreviousRaid
                // below; far/near transfers wait for their native ACK first.
                if (bot->GetMapId() == request.entryMap && bot->GetInstanceId() == owner->GetInstanceId())
                { Report(request,"arrived","already_inside"); it = state.summons.erase(it); continue; }
            }
        }
        if (request.started) bot->GetPlayerbotAI()->CompleteSummonRevival();
        // Confirm the accepted landing point, not the requester's later position.
        // A moving leader must not turn a successful teleport into a timeout.
        bool landed = request.started && bot->IsInWorld() && !bot->IsBeingTeleported() &&
            bot->IsAlive() && bot->GetMapId() == request.map && bot->GetInstanceId() == request.instance &&
            bot->IsWithinDist3d(request.x,request.y,request.z,10.0f);
        if (landed)
        {
            request.diagnosticStage = "accepted_landing"; request.diagnosticReason = "ok";
            request.arrival.requesterLocationKnown = request.arrival.botLocationKnown = true;
            request.arrival.requesterMap = request.arrival.botMap = request.map;
            request.arrival.requesterInstance = request.arrival.botInstance = request.instance;
            // Refill only after this explicit request reaches its accepted
            // destination. Failed requests and replayed receipts cannot heal.
            bot->SetHealth(bot->GetMaxHealth());
            bot->SetPower(POWER_MANA, bot->GetMaxPower(POWER_MANA));
            Report(request,"arrived","ok"); it = state.summons.erase(it); continue;
        }
        reason = Waiting(owner,bot);
        if (!reason.empty())
        {
            if (reason != request.waitReason)
            { request.waitReason = reason; Report(request,"summon_pending",reason); }
            ++it; continue;
        }
        // A completed but rejected/fallback transfer can be retried. Never
        // overwrite a pending native transfer or keep retrying a denied entry.
        if (now < request.nextAttempt) { ++it; continue; }
        if (request.attempts >= 3)
        { Report(request,"refused","arrival_not_confirmed"); it = state.summons.erase(it); continue; }
        if (teleports < 2)
        {
            ++teleports;
            if (owner->GetMapId() == bot->GetMapId() && owner->GetInstanceId() != bot->GetInstanceId() &&
                owner->GetMap()->Instanceable())
            {
                // Only one departure per request. A failed/fallback worldport
                // must not become a loop between two copies of the same raid.
                if (request.started || request.leftPreviousInstance || !LeavePreviousRaid(owner, bot))
                { Report(request,"refused","different_instance"); it = state.summons.erase(it); continue; }
                request.leftPreviousInstance = true;
                request.waitReason = "leaving_previous_instance";
                Report(request,"summon_pending",request.waitReason);
                ++it; continue;
            }
            SummonAction action(bot->GetPlayerbotAI());
            Event event("summon", "", owner);
            request.map = owner->GetMapId(); request.instance = owner->GetInstanceId();
            request.started = action.ExecuteImmediate(event);
            if (!request.started)
            {
                reason = action.GetFailureReason();
                if (reason != request.waitReason)
                    sLog.outString("PLAYERBOT_SUMMON: bot %u requester %u destination map %u instance %u refused %s retryable %u",
                        bot->GetGUIDLow(), owner->GetGUIDLow(), request.map, request.instance, reason.c_str(), action.CanRetry() ? 1u : 0u);
                if (!action.CanRetry())
                { Report(request,"refused",reason); it = state.summons.erase(it); continue; }
                request.nextAttempt = now + 2;
                if (reason != request.waitReason)
                { request.waitReason = reason; Report(request,"summon_pending",reason); }
                ++it; continue;
            }
            WorldLocation const& destination = bot->GetTeleportDest();
            request.x = destination.coord_x; request.y = destination.coord_y; request.z = destination.coord_z;
            ++request.attempts;
            request.nextAttempt = now + 2;
            request.waitReason = "teleport_started";
            Report(request,"summon_pending",request.waitReason);
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

std::string BotRecruitment::PreparationReason(Player* owner, Player* bot, bool allowCombat)
{
    std::string reason = Control(owner,bot);
    if (!reason.empty()) return reason;
    if (!owner->IsInWorld() || owner->IsBeingTeleported() || !bot->IsInWorld() || bot->IsBeingTeleported()) return "transfer";
    if (!bot->IsAlive()) return "dead";
    if (!allowCombat && (bot->IsInCombat() || owner->IsInCombat())) return "combat";
    if (bot->HasCharmer() || bot->GetTransport() || bot->IsTaxiFlying()) return "transport_or_controlled";
    if (owner->InBattleGround() || bot->InBattleGround()) return "battleground";
    return "";
}

std::string BotRecruitment::Prepare(Player* owner, Player* bot, const std::string& command,
    const std::string& parameter, const std::function<std::string()>& apply)
{
    const bool gear = command == "gear" || command == "equip";
    auto refuse = [&](const std::string& reason)
    {
        if (State().preparationTrace) State().preparationTrace->refusal = reason;
        return "refused: " + reason;
    };
    std::string reason = PreparationReason(owner,bot,gear);
    if (!reason.empty()) return refuse(reason);
    // No distance restriction for manual preparation. Pending summons must finish.
    auto summon = State().summons.find(bot->GetGUIDLow());
    if (summon != State().summons.end()) return refuse("summon_pending");
    auto restoreGearResources = [&](const std::string& response)
    {
        // Repeated legacy gear commands reuse equipment work, but must retain
        // the health/mana refill that equipment stat initialization provided.
        // Only recognized successful gear responses qualify; supply commands
        // and refused/unknown requests must not refill resources.
        if (gear && (response == "random gear equipped" || response == "random green gear equipped" ||
            response == "random blue gear equipped" || response == "random epic gear equipped" ||
            response == "gear upgraded" || response == "random best gear equipped" ||
            response == "random gear upgraded to some slots"))
        {
            bot->SetHealth(bot->GetMaxHealth());
            if (bot->GetMaxPower(POWER_MANA))
                bot->SetPower(POWER_MANA, bot->GetMaxPower(POWER_MANA));
        }
        return response;
    };
    std::string key = std::to_string(owner->GetGUIDLow()) + ":" + std::to_string(bot->GetGUIDLow()) + ":" +
        command + ":" + parameter + ":" + std::to_string(bot->GetLevel()) + ":" + TalentSpec(bot).GetTalentLink();
    auto old = State().preparation.find(key);
    if (!State().explicitPreparation && old != State().preparation.end() && old->second.expires > Now())
        return restoreGearResources(old->second.response);
    if (State().preparation.size() >= limits::MaxReceipts) return refuse("busy");
    if (State().preparationSecond != Now())
    {
        State().preparationSecond = Now();
        State().gearWork = State().supplyWork = 0;
        State().playerPreparationWork.clear();
    }
    unsigned& work = gear ? State().gearWork : State().supplyWork;
    unsigned& playerWork = State().playerPreparationWork[owner->GetGUIDLow()];
    if (work >= (gear ? 2u : 32u) || playerWork >= 8) return refuse("preparation_rate_limit");
    ++work; ++playerWork;
    if ((command == "gear" || command == "equip") && !sRandomItemMgr.GetPlayerSpecId(bot))
        return refuse("unsupported_spec");
    if (State().preparationTrace) State().preparationTrace->entered = true;
    std::string result = restoreGearResources(apply());
    if (result.find("refused:") != 0)
        State().preparation[key] = {"",result,Now() + limits::LegacyPreparationSeconds};
    return result;
}
