#include "botpch.h"
#include "PlayerbotRendezvousManager.h"

#include "Entities/Transports.h"
#include "Mails/Mail.h"
#include "MotionGenerators/PathFinder.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "PlayerbotInventoryPressure.h"
#include "PlayerbotOrganicEconomy.h"
#include "RandomPlayerbotMgr.h"
#include "ServerFacade.h"
#include "TravelMgr.h"
#include "strategy/values/TravelValues.h"

#include <cmath>
#include <limits>
#include <sstream>
#include <vector>

namespace
{
    constexpr float kRunSpeedYardsPerSecond = 7.0f;
    constexpr uint32 kErrandVendor = 1 << 0;
    constexpr uint32 kErrandRepair = 1 << 1;
    constexpr uint32 kErrandBank = 1 << 2;
    constexpr uint32 kErrandMail = 1 << 3;
    constexpr uint32 kErrandAuction = 1 << 4;
    constexpr uint32 kErrandProfession = 1 << 5;

    bool IsRealObserver(Player* player)
    {
        return player && player->IsInWorld() && player->isRealPlayer();
    }

    bool IsCastingHearthstone(Player* player)
    {
        Spell* spell = player ? player->GetCurrentSpell(CURRENT_GENERIC_SPELL) : nullptr;
        return spell && spell->m_spellInfo && spell->m_spellInfo->Id == 8690;
    }

    bool IsCapital(Player* player)
    {
        AreaTableEntry const* area = player ? GetAreaEntryByAreaID(sServerFacade.GetAreaId(player)) : nullptr;
        AreaTableEntry const* zone = player ? GetAreaEntryByAreaID(player->GetZoneId()) : nullptr;
        return (area && (area->flags & AREA_FLAG_CAPITAL)) || (zone && (zone->flags & AREA_FLAG_CAPITAL));
    }

    uint32 SettlementKey(Player* bot, Player* human)
    {
        if (!bot || !human || bot->GetMapId() != human->GetMapId() ||
            !bot->IsWithinDistInMap(human, 120.0f))
            return 0;
        if (IsCapital(human))
            return 0x80000000u | human->GetZoneId();

        PlayerbotAI* ai = bot->GetPlayerbotAI();
        if (!ai)
            return 0;
        bool vendor = false, supportingService = false;
        uint32 serviceKinds = 0;
        std::list<ObjectGuid> npcs = ai->GetAiObjectContext()->
            GetValue<std::list<ObjectGuid>>("nearest npcs no los")->Get();
        for (ObjectGuid const& guid : npcs)
        {
            Unit* npc = ai->GetUnit(guid);
            if (!npc)
                continue;
            if (npc->HasFlag(UNIT_NPC_FLAGS, UNIT_NPC_FLAG_VENDOR | UNIT_NPC_FLAG_REPAIR))
            {
                vendor = true;
                ++serviceKinds;
            }
            if (npc->HasFlag(UNIT_NPC_FLAGS, UNIT_NPC_FLAG_TRAINER | UNIT_NPC_FLAG_TRAINER_CLASS |
                UNIT_NPC_FLAG_TRAINER_PROFESSION | UNIT_NPC_FLAG_INNKEEPER | UNIT_NPC_FLAG_BANKER |
                UNIT_NPC_FLAG_AUCTIONEER | UNIT_NPC_FLAG_FLIGHTMASTER))
            {
                supportingService = true;
                ++serviceKinds;
            }
        }
        return vendor && supportingService && serviceKinds >= 2 ? sServerFacade.GetAreaId(human) : 0;
    }

    uint32 PersonalErrandMask(Player* bot)
    {
        if (!bot || !bot->GetPlayerbotAI())
            return 0;
        PlayerbotAI* ai = bot->GetPlayerbotAI();
        LivingWowInventoryPressureSummary pressure = sPlayerbotInventoryPressure.Analyze(bot);
        uint32 errands = 0;
        if (pressure.vendorStacks)
            errands |= kErrandVendor;
        if (ai->GetAiObjectContext()->GetValue<uint8>("durability inventory")->Get() < 85)
            errands |= kErrandRepair;
        if (pressure.StorableStacks() && (pressure.bagUsage >= 70 || pressure.StorableStacks() >= 3))
            errands |= kErrandBank;

        time_t now = time(nullptr);
        for (PlayerMails::iterator mail = bot->GetMailBegin(); mail != bot->GetMailEnd(); ++mail)
        {
            if ((*mail)->state != MAIL_STATE_DELETED && now >= (*mail)->deliver_time &&
                ((*mail)->has_items || (*mail)->money))
            {
                errands |= kErrandMail;
                break;
            }
        }

        std::string goal = sPlayerbotOrganicEconomy.CurrentGoalType(bot->GetGUIDLow());
        if (pressure.auctionStacks || goal == "list_surplus")
            errands |= kErrandAuction;
        if (goal == "profession_skill_up")
            errands |= kErrandProfession;
        return errands;
    }

    TravelDestinationPurpose ErrandPurpose(uint32 errand)
    {
        if (errand == kErrandVendor)
            return TravelDestinationPurpose::Vendor;
        if (errand == kErrandRepair)
            return TravelDestinationPurpose::Repair;
        if (errand == kErrandBank)
            return TravelDestinationPurpose::Bank;
        if (errand == kErrandMail)
            return TravelDestinationPurpose::Mail;
        if (errand == kErrandAuction)
            return TravelDestinationPurpose::AH;
        return TravelDestinationPurpose::Trainer;
    }

    bool FindSettlementErrandDestination(Player* bot, uint32 errand,
        TravelDestination*& selectedDestination, WorldPosition*& selectedPosition)
    {
        selectedDestination = nullptr;
        selectedPosition = nullptr;
        if (!bot || !bot->GetPlayerbotAI())
            return false;
        PlayerTravelInfo info(bot);
        DestinationList destinations = sTravelMgr.GetDestinations(
            info, (uint32)ErrandPurpose(errand), {}, true, 600.0f, false);
        WorldPosition center(bot);
        float bestDistance = std::numeric_limits<float>::max();
        for (TravelDestination* destination : destinations)
        {
            if (!destination)
                continue;
            std::list<uint8> chances = {100};
            WorldPosition* position = destination->GetNextPoint(center, chances, true);
            if (!position || position->getMapId() != bot->GetMapId())
                continue;
            float distance = center.distance(*position);
            if (distance > 600.0f || distance >= bestDistance)
                continue;
            bestDistance = distance;
            selectedDestination = destination;
            selectedPosition = position;
        }
        return selectedDestination && selectedPosition;
    }

    uint32 GroundedSettlementErrandMask(Player* bot)
    {
        uint32 requested = PersonalErrandMask(bot);
        uint32 grounded = 0;
        const uint32 errands[] = {kErrandVendor, kErrandRepair, kErrandBank,
            kErrandMail, kErrandAuction, kErrandProfession};
        for (uint32 errand : errands)
        {
            if (!(requested & errand))
                continue;
            TravelDestination* destination = nullptr;
            WorldPosition* position = nullptr;
            if (FindSettlementErrandDestination(bot, errand, destination, position))
                grounded |= errand;
        }
        return grounded;
    }

    std::string ErrandTelemetryNames(uint32 errands);

    bool SetAutomaticErrandTarget(Player* bot, uint32 errands)
    {
        if (!bot || !bot->GetPlayerbotAI() || !errands)
            return false;
        const uint32 priorities[] = {kErrandVendor, kErrandRepair, kErrandBank,
            kErrandMail, kErrandAuction, kErrandProfession};
        for (uint32 errand : priorities)
        {
            if (!(errands & errand))
                continue;
            TravelDestination* destination = nullptr;
            WorldPosition* position = nullptr;
            if (!FindSettlementErrandDestination(bot, errand, destination, position))
                continue;
            PlayerbotAI* ai = bot->GetPlayerbotAI();
            TravelTarget* target = ai->GetAiObjectContext()->GetValue<TravelTarget*>("travel target")->Get();
            sTravelMgr.SetNullTravelTarget(target);
            target->SetTarget(destination, position);
            target->SetForced(true);
            target->SetStatus(TravelStatus::TRAVEL_STATUS_TRAVEL);
            ai->GetAiObjectContext()->ClearValues("no active travel destinations");
            ai->ChangeStrategy("nc +travel once", BotState::BOT_STATE_NON_COMBAT);
            ai->StopMoving();
            sLog.outString("Living WoW party errands event=target_selected bot=%u task=%s map=%u area=%s distance=%.1f",
                bot->GetGUIDLow(), ErrandTelemetryNames(errand).c_str(), position->getMapId(),
                position->getAreaName().c_str(), WorldPosition(bot).distance(*position));
            return true;
        }
        return false;
    }

    std::vector<std::string> PersonalErrands(uint32 errands)
    {
        std::vector<std::string> names;
        if (errands & kErrandVendor)
            names.push_back("sell some junk");
        if (errands & kErrandRepair)
            names.push_back("repair my gear");
        if (errands & kErrandBank)
            names.push_back("put some materials in the bank");
        if (errands & kErrandMail)
            names.push_back("pick up my mail");
        if (errands & kErrandAuction)
            names.push_back("check the auction house");
        if (errands & kErrandProfession)
            names.push_back("work on my profession");
        return names;
    }

    std::string ErrandTelemetryNames(uint32 errands)
    {
        std::string names;
        auto append = [&names](const char* name)
        {
            if (!names.empty()) names += ',';
            names += name;
        };
        if (errands & kErrandVendor) append("vendor");
        if (errands & kErrandRepair) append("repair");
        if (errands & kErrandBank) append("bank");
        if (errands & kErrandMail) append("mail");
        if (errands & kErrandAuction) append("auction");
        if (errands & kErrandProfession) append("profession");
        return names.empty() ? "none" : names;
    }

    std::string ErrandAnnouncement(std::vector<std::string> const& errands)
    {
        if (errands.empty())
            return "";
        std::ostringstream message;
        message << "I've got to ";
        size_t shown = std::min<size_t>(3, errands.size());
        for (size_t index = 0; index < shown; ++index)
        {
            if (index)
                message << (index + 1 == shown ? (shown == 2 ? " and " : ", and ") : ", ");
            message << errands[index];
        }
        if (errands.size() > shown)
            message << ", plus a couple other things";
        message << ". I'll catch back up when I'm done.";
        return message.str();
    }
}

PlayerbotRendezvousManager& PlayerbotRendezvousManager::instance()
{
    static PlayerbotRendezvousManager manager;
    return manager;
}

bool PlayerbotRendezvousManager::RegisterPartyAssist(Player* bot, Player* inviter)
{
    if (!bot || !inviter || !bot->GetPlayerbotAI() || !bot->IsInWorld() || !inviter->IsInWorld() ||
        !inviter->isRealPlayer() || bot->GetTeam() != inviter->GetTeam() || !bot->GetGroup() ||
        bot->GetGroup() != inviter->GetGroup() || bot->InBattleGround() || inviter->InBattleGround() ||
        bot->GetMap()->IsDungeon() || inviter->GetMap()->IsDungeon())
        return false;

    // A bot can temporarily serve only one human-created party. Existing
    // autonomous bot groups are never registered here and are therefore never
    // dismantled by the return lifecycle.
    if (partySessions.find(bot->GetGUIDLow()) != partySessions.end())
        return true;

    PartySession session;
    session.botGuid = bot->GetGUIDLow();
    session.playerGuid = inviter->GetGUIDLow();
    session.groupId = bot->GetGroup()->GetId();
    session.originMapId = bot->GetMapId();
    session.originInstanceId = bot->GetInstanceId();
    session.originX = bot->GetPositionX();
    session.originY = bot->GetPositionY();
    session.originZ = bot->GetPositionZ();
    session.originO = bot->GetOrientation();
    session.previousActivity = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
    session.state = "pending";
    session.stateSince = std::chrono::steady_clock::now();
    partySessions[session.botGuid] = session;
    LogPartyEvent(partySessions[session.botGuid], "registered");
    return true;
}

bool PlayerbotRendezvousManager::ResumePartyAssist(Player* bot, Player* player, const std::string& reason)
{
    if (!bot || !player || !bot->GetGroup() || bot->GetGroup() != player->GetGroup() ||
        !bot->IsInWorld() || !player->IsInWorld() || !bot->IsAlive() || !player->IsAlive() ||
        bot->IsTaxiFlying() || bot->GetTransport() ||
        bot->InBattleGround() || bot->GetMap()->IsDungeon() || player->GetMap()->IsDungeon())
        return false;

    auto found = partySessions.find(bot->GetGUIDLow());
    if (found == partySessions.end())
    {
        if (!RegisterPartyAssist(bot, player))
            return false;
        found = partySessions.find(bot->GetGUIDLow());
    }
    PartySession& session = found->second;
    if (session.groupId != bot->GetGroup()->GetId())
        return false;

    if (bot->IsInCombat())
    {
        if (session.state != "free_time")
            return false;
        session.freeTimeRecallRequested = true;
        session.reason = "free_time_recall_after_combat";
        LogPartyEvent(session, "free_time_recall_queued");
        return true;
    }

    if (session.state == "free_time")
    {
        bot->GetPlayerbotAI()->SetMaster(player);
        bot->GetPlayerbotAI()->RequestStrategyReset(false);
        bot->GetPlayerbotAI()->DoSpecificAction(
            "reset travel target", Event("living party free time", "resume", player), true);
    }

    session.playerGuid = player->GetGUIDLow();
    session.state = "pending";
    session.reason = reason;
    session.forceRelocation = true;
    session.approachIssued = false;
    session.freeTimeRecallRequested = false;
    session.freeTimeUntil = std::chrono::steady_clock::time_point();
    session.nextApproachAttempt = std::chrono::steady_clock::time_point();
    session.stateSince = std::chrono::steady_clock::now();
    LogPartyEvent(session, "party_return_queued");
    return true;
}

bool PlayerbotRendezvousManager::BeginPartyFreeTime(Player* bot, Player* player, const std::string& reason)
{
    if (!bot || !player || !bot->GetPlayerbotAI() || !bot->GetGroup() ||
        bot->GetGroup() != player->GetGroup() || !bot->GetGroup()->IsLeader(player->GetObjectGuid()) ||
        !bot->IsInWorld() || !player->IsInWorld() || !bot->IsAlive() || !player->IsAlive() ||
        bot->IsInCombat() || player->IsInCombat() || bot->IsTaxiFlying() || bot->GetTransport() ||
        bot->InBattleGround() || bot->GetMap()->IsDungeon() || player->GetMap()->IsDungeon() ||
        bot->GetMapId() != player->GetMapId() || !bot->IsWithinDistInMap(player, 120.0f))
        return false;

    auto found = partySessions.find(bot->GetGUIDLow());
    if (found == partySessions.end())
    {
        if (!RegisterPartyAssist(bot, player))
            return false;
        found = partySessions.find(bot->GetGUIDLow());
    }
    PartySession& session = found->second;
    if (session.groupId != bot->GetGroup()->GetId())
        return false;
    if (session.state == "free_time")
        return true;

    PlayerbotAI* ai = bot->GetPlayerbotAI();
    ai->StopMoving();
    ai->DoSpecificAction("reset travel target", Event("living party free time", "begin", player), true);
    ai->SetMaster(nullptr);
    ai->ChangeStrategy(
        "nc -follow,+rpg,+rpg craft,+travel,-rpg quest,-rpg explore,-rpg bg,-rpg player,-rpg guild",
        BotState::BOT_STATE_NON_COMBAT);

    const auto now = std::chrono::steady_clock::now();
    session.playerGuid = player->GetGUIDLow();
    session.state = "free_time";
    session.reason = reason;
    session.freeTimeRecallRequested = false;
    session.freeTimePlayerZoneId = player->GetZoneId();
    session.freeTimePlayerAreaId = sServerFacade.GetAreaId(player);
    bool automaticSettlement = reason == "automatic_settlement_errands";
    session.freeTimeUntil = now + (automaticSettlement ? std::chrono::minutes(5) : std::chrono::minutes(30));
    session.automaticErrandScopeMask = automaticSettlement ? GroundedSettlementErrandMask(bot) : 0;
    session.automaticErrandMask = session.automaticErrandScopeMask;
    session.automaticErrandLastX = bot->GetPositionX();
    session.automaticErrandLastY = bot->GetPositionY();
    session.automaticErrandHardDeadline = automaticSettlement ?
        now + std::chrono::minutes(15) : std::chrono::steady_clock::time_point();
    session.nextAutomaticErrandCheck = automaticSettlement ?
        now + std::chrono::seconds(45) : std::chrono::steady_clock::time_point();
    session.nextAutomaticErrandProgressLog = automaticSettlement ?
        now + std::chrono::minutes(1) : std::chrono::steady_clock::time_point();
    session.stateSince = now;
    LogPartyEvent(session, "free_time_started");
    if (automaticSettlement)
    {
        SetAutomaticErrandTarget(bot, session.automaticErrandMask);
        LogAutomaticErrandEvent(session, bot, "started", session.automaticErrandMask,
            session.automaticErrandMask);
    }
    return true;
}

bool PlayerbotRendezvousManager::IsPartyFreeTime(uint32 botGuid) const
{
    auto found = partySessions.find(botGuid);
    return found != partySessions.end() && found->second.state == "free_time";
}

std::string PlayerbotRendezvousManager::PartyState(uint32 botGuid) const
{
    auto found = partySessions.find(botGuid);
    return found == partySessions.end() ? "none" : found->second.state;
}

std::string PlayerbotRendezvousManager::PartyReason(uint32 botGuid) const
{
    auto found = partySessions.find(botGuid);
    return found == partySessions.end() ? "" : found->second.reason;
}

uint32 PlayerbotRendezvousManager::PartyDeadRecoveryAttempts(uint32 botGuid) const
{
    auto found = partySessions.find(botGuid);
    return found == partySessions.end() ? 0 : found->second.deadRecoveryAttempts;
}

uint32 PlayerbotRendezvousManager::PartyDeadRecoverySeconds(uint32 botGuid) const
{
    auto found = partySessions.find(botGuid);
    if (found == partySessions.end() || found->second.deadRecoveryStarted.time_since_epoch().count() == 0)
        return 0;
    return (uint32)std::max<long long>(0, std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::steady_clock::now() - found->second.deadRecoveryStarted).count());
}

PlayerbotRendezvousManager::Session* PlayerbotRendezvousManager::Find(uint32 botGuid, uint32 playerGuid)
{
    auto found = sessions.find(botGuid);
    return found != sessions.end() && found->second.playerGuid == playerGuid ? &found->second : nullptr;
}

const PlayerbotRendezvousManager::Session* PlayerbotRendezvousManager::Find(uint32 botGuid, uint32 playerGuid) const
{
    auto found = sessions.find(botGuid);
    return found != sessions.end() && found->second.playerGuid == playerGuid ? &found->second : nullptr;
}

bool PlayerbotRendezvousManager::IsPointUnobserved(Player* bot, float x, float y, float z) const
{
    return bot && IsPointUnobservedOnMap(bot->GetMap(), bot, x, y, z);
}

bool PlayerbotRendezvousManager::IsPointUnobservedOnMap(Map* map, Player* bot, float x, float y, float z) const
{
    if (!map || !bot) return false;
    float visibility = map->GetVisibilityDistance();
    for (const auto& reference : map->GetPlayers())
    {
        Player* observer = reference.getSource();
        if (!IsRealObserver(observer)) continue;
        if (observer->IsWithinDist3d(x, y, z, visibility) && observer->IsWithinLOS(x, y, z + bot->GetCollisionHeight(), false))
            return false;
    }
    return true;
}

bool PlayerbotRendezvousManager::ValidPath(Player* bot, float sx, float sy, float sz, Player* player) const
{
    if (!bot || !player || !player->GetMap()) return false;
    PathFinder path(player->GetMapId(), player->GetInstanceId());
    if (!path.calculate(Vector3(sx, sy, sz), Vector3(player->GetPositionX(), player->GetPositionY(), player->GetPositionZ()), true))
        return false;
    PathType type = path.getPathType();
    return !(type & PATHFIND_NOPATH) && !(type & PATHFIND_SHORTCUT) && !(type & PATHFIND_INCOMPLETE);
}

bool PlayerbotRendezvousManager::FindStagingPoint(Player* bot, Player* player, float& x, float& y, float& z) const
{
    if (!bot || !player || !player->GetMap()) return false;
    uint32 targetSeconds = std::max<uint32>(5, std::min<uint32>(30, sPlayerbotAIConfig.chatDirectorRendezvousTargetSeconds));
    uint32 maximumSeconds = std::max<uint32>(targetSeconds,
        std::min<uint32>(60, sPlayerbotAIConfig.chatDirectorRendezvousMaximumSeconds));
    const float rings[] = { kRunSpeedYardsPerSecond * targetSeconds,
        kRunSpeedYardsPerSecond * ((targetSeconds + maximumSeconds) / 2.0f),
        kRunSpeedYardsPerSecond * maximumSeconds };
    for (float radius : rings)
    {
        for (uint32 step = 0; step < 16; ++step)
        {
            float angle = float(step) * float(M_PI) / 8.0f;
            float cx = player->GetPositionX() + std::cos(angle) * radius;
            float cy = player->GetPositionY() + std::sin(angle) * radius;
            float cz = player->GetMap()->GetHeight(cx, cy, player->GetPositionZ() + 25.0f);
            if (cz < -100000.0f || !IsPointUnobservedOnMap(player->GetMap(), bot, cx, cy, cz) ||
                !ValidPath(bot, cx, cy, cz, player))
                continue;
            x = cx; y = cy; z = cz + 0.1f;
            return true;
        }
    }
    return false;
}

PlayerbotRendezvousManager::RequestResult PlayerbotRendezvousManager::Request(
    Player* bot, Player* player, const std::string& actionId, bool returnAfter)
{
    if (!bot || !player || !bot->IsInWorld() || !player->IsInWorld() ||
        bot->IsInCombat() || !bot->IsAlive() || !player->IsAlive() || bot->IsTaxiFlying())
        return RequestResult::unavailable;
    if (sessions.find(bot->GetGUIDLow()) != sessions.end())
        return Find(bot->GetGUIDLow(), player->GetGUIDLow()) ? RequestResult::accepted : RequestResult::unavailable;

    const bool sameMap = bot->GetMapId() == player->GetMapId() &&
        bot->GetInstanceId() == player->GetInstanceId();
    // Cross-map rendezvous is reserved for one-way, world-authoritative
    // handoffs such as assembling a bot guild event. Transactions that must
    // return to the original activity keep their existing same-map contract.
    if (!sameMap && (returnAfter || bot->InBattleGround() || player->InBattleGround() ||
        bot->GetMap()->IsDungeon() || player->GetMap()->IsDungeon()))
        return RequestResult::unavailable;
    if (sameMap && bot->GetTransport())
        return RequestResult::unavailable;

    const auto now = std::chrono::steady_clock::now();
    bool deferredCrossMapArrival = false;
    Session session;
    session.botGuid = bot->GetGUIDLow();
    session.playerGuid = player->GetGUIDLow();
    session.mapId = bot->GetMapId();
    session.originX = bot->GetPositionX(); session.originY = bot->GetPositionY();
    session.originZ = bot->GetPositionZ(); session.originO = bot->GetOrientation();
    session.actionId = actionId;
    session.previousActivity = bot->GetPlayerbotAI()->HandleRemoteCommand("action");
    session.state = "approaching";
    session.returnAfter = returnAfter;
    session.started = session.stateSince = now;

    float distance = sameMap ? bot->GetDistance(player) : 100000.0f;
    uint32 triggerSeconds = std::max<uint32>(10, std::min<uint32>(300,
        sPlayerbotAIConfig.chatDirectorRendezvousTriggerSeconds));
    bool needsCatchup = distance > kRunSpeedYardsPerSecond * triggerSeconds;
    if (needsCatchup)
    {
        if (!sPlayerbotAIConfig.chatDirectorRendezvousCatchup)
            return RequestResult::unavailable;
        auto cooldown = lastRelocation.find(bot->GetGUIDLow());
        if (cooldown != lastRelocation.end() &&
            std::chrono::duration_cast<std::chrono::seconds>(now - cooldown->second).count() <
                std::max<uint32>(60, sPlayerbotAIConfig.chatDirectorRendezvousCooldownSeconds))
            return RequestResult::unavailable;
        // Never make either end of the relocation disappear in front of a real
        // observer. Camera orientation is not authoritative server data, so LOS
        // and visibility from every nearby human are the conservative boundary.
        if (!IsPointUnobserved(bot, session.originX, session.originY, session.originZ))
            return RequestResult::unsafe;
        float stageX = 0.0f, stageY = 0.0f, stageZ = 0.0f;
        if (!FindStagingPoint(bot, player, stageX, stageY, stageZ))
            return RequestResult::unsafe;
        GenericTransport* transport = bot->GetTransport();
        bot->GetPlayerbotAI()->StopMoving();
        if (transport)
            transport->RemovePassenger(bot);
        if (sameMap)
            bot->NearTeleportTo(stageX, stageY, stageZ, bot->GetAngle(player));
        else
        {
            if (!bot->TeleportTo(player->GetMapId(), stageX, stageY, stageZ, player->GetOrientation()))
                return RequestResult::unavailable;
            deferredCrossMapArrival = true;
        }
        session.relocated = true;
        lastRelocation[bot->GetGUIDLow()] = now;
    }

    if (deferredCrossMapArrival)
        session.state = "relocating";
    sessions[session.botGuid] = session;
    // TeleportTo completes the map transfer asynchronously. Installing a
    // movement generator while m_currMap is detached violates a CMaNGOS map
    // invariant, so cross-map arrivals begin following from Update only after
    // IsBeingTeleported has cleared and both actors share the destination map.
    if (!deferredCrossMapArrival)
        bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
    LogEvent(sessions[session.botGuid], session.relocated ? "relocated_for_arrival" : "ordinary_arrival");
    return session.relocated ? RequestResult::accepted : RequestResult::ordinary_travel;
}

void PlayerbotRendezvousManager::BeginDeparture(uint32 botGuid, uint32 playerGuid, const std::string& reason)
{
    Session* session = Find(botGuid, playerGuid);
    if (!session) return;
    if (!session->returnAfter)
    {
        sessions.erase(botGuid);
        return;
    }
    Player* bot = sRandomPlayerbotMgr.GetPlayerBot(botGuid);
    Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, playerGuid));
    session->state = "departing";
    session->reason = reason;
    session->stateSince = std::chrono::steady_clock::now();
    if (bot && player && bot->GetMapId() == player->GetMapId())
    {
        float angle = player->GetAngle(bot);
        float x = bot->GetPositionX() + std::cos(angle) * 45.0f;
        float y = bot->GetPositionY() + std::sin(angle) * 45.0f;
        float z = bot->GetMap()->GetHeight(x, y, bot->GetPositionZ() + 10.0f);
        if (z > -100000.0f)
            bot->GetMotionMaster()->MovePoint(bot->GetMapId(), x, y, z, FORCED_MOVEMENT_RUN);
    }
    LogEvent(*session, "departure_started");
}

bool PlayerbotRendezvousManager::ReturnToActivity(Session& session, Player* bot)
{
    if (!bot || !bot->IsInWorld()) return false;
    if (session.relocated && bot->GetMapId() == session.mapId &&
        IsPointUnobserved(bot, bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()) &&
        IsPointUnobserved(bot, session.originX, session.originY, session.originZ))
    {
        float ground = bot->GetMap()->GetHeight(session.originX, session.originY, session.originZ + 10.0f);
        if (ground > -100000.0f)
            bot->NearTeleportTo(session.originX, session.originY, ground + 0.1f, session.originO);
    }
    // Re-evaluate the high-level travel/quest target against current world state;
    // the saved activity is diagnostic context, never an unvalidated command.
    bot->GetPlayerbotAI()->DoSpecificAction("reset travel target", Event("living rendezvous resume"), true);
    return true;
}

void PlayerbotRendezvousManager::Cancel(uint32 botGuid, uint32 playerGuid, const std::string& reason)
{
    Session* session = Find(botGuid, playerGuid);
    if (session && session->actionId.find("guild-event:") == 0)
    {
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(botGuid);
        if (bot && bot->GetPlayerbotAI())
            bot->GetPlayerbotAI()->ChangeStrategy(
                "-stay,+follow,-wander", BotState::BOT_STATE_NON_COMBAT);
    }
    BeginDeparture(botGuid, playerGuid, reason);
}

void PlayerbotRendezvousManager::Update()
{
    const auto now = std::chrono::steady_clock::now();
    if (nextPartyDiscovery.time_since_epoch().count() == 0 || now >= nextPartyDiscovery)
    {
        nextPartyDiscovery = now + std::chrono::seconds(2);
        for (uint32 botGuid : sRandomPlayerbotMgr.GetChatBotGuids())
        {
            if (partySessions.find(botGuid) != partySessions.end())
                continue;
            Player* bot = sRandomPlayerbotMgr.GetPlayerBot(botGuid);
            if (!bot || !bot->IsInWorld() || !bot->GetPlayerbotAI() || !bot->GetGroup())
                continue;
            Player* human = FindPartyHuman(bot);
            if (!human || bot->GetGroup()->GetLeaderGuid() != human->GetObjectGuid())
                continue;

            // Group membership persists across realm restarts, while the
            // rendezvous registry intentionally does not. Reconstruct only a
            // human-led mixed party through the typed invitation lifecycle.
            // UpdatePartyAssists serializes every reconstructed arrival.
            if (RegisterPartyAssist(bot, human))
                LogPartyEvent(partySessions[botGuid], "recovered_persisted_party");
        }
    }
    UpdatePartyAssists();
    for (auto iterator = sessions.begin(); iterator != sessions.end(); )
    {
        Session& session = iterator->second;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(session.botGuid);
        Player* player = sObjectAccessor.FindPlayer(ObjectGuid(HIGHGUID_PLAYER, session.playerGuid));
        bool erase = false;
        if (!bot || !bot->IsInWorld()) erase = true;
        else if (session.state == "relocating")
        {
            if (!player || !player->IsInWorld())
            {
                LogEvent(session, "relocation_player_unavailable");
                erase = true;
            }
            else if (!bot->IsBeingTeleported())
            {
                if (bot->GetMapId() != player->GetMapId() ||
                    bot->GetInstanceId() != player->GetInstanceId())
                {
                    LogEvent(session, "relocation_map_mismatch");
                    erase = true;
                }
                else
                {
                    session.state = "approaching";
                    session.stateSince = now;
                    bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
                    LogEvent(session, "relocation_attached");
                }
            }
        }
        else if (session.state == "approaching")
        {
            if (!player || !player->IsInWorld() || player->GetMapId() != bot->GetMapId())
            {
                session.state = "departing"; session.reason = "player_unavailable"; session.stateSince = now;
            }
            else if (bot->IsInCombat())
            {
                if (!session.combatPaused)
                {
                    // Do not synchronously clear the movement generator here.
                    // This update can run immediately after NearTeleportTo;
                    // Playerbots may still hold the active generator for its
                    // next AI tick, and deleting it here causes a use-after-free.
                    // Normal combat AI owns subsequent movement until combat ends.
                    session.combatPaused = true;
                    session.stateSince = now;
                    LogEvent(session, "combat_paused");
                }
            }
            else if (session.combatPaused)
            {
                session.combatPaused = false;
                session.stateSince = now;
                bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
                LogEvent(session, "combat_resumed");
            }
            else if (bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
            {
                if (!session.returnAfter)
                {
                    if (session.actionId.find("guild-event:") == 0)
                    {
                        // Guild formation is a barrier, not a collection of
                        // independent arrivals. Keep early members beside the
                        // stationary organizer until the lifecycle confirms
                        // the complete online roster; otherwise autonomous AI
                        // can wander away while later members are arriving.
                        session.state = "assembled";
                        session.stateSince = now;
                        bot->GetPlayerbotAI()->ChangeStrategy(
                            "+stay,-follow,-wander", BotState::BOT_STATE_NON_COMBAT);
                        bot->GetPlayerbotAI()->StopMoving();
                        LogEvent(session, "assembly_held");
                    }
                    else
                    {
                        // Other one-way rendezvous operations hand movement
                        // back to their owning workflow immediately.
                        LogEvent(session, "arrival_handed_off");
                        erase = true;
                    }
                }
                else
                {
                    session.state = "arrived";
                    session.stateSince = now;
                    LogEvent(session, "arrived");
                }
            }
            else if (std::chrono::duration_cast<std::chrono::seconds>(now - session.stateSince).count() >= 2)
            {
                bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
                session.stateSince = now;
            }
        }
        else if (session.state == "assembled")
        {
            if (!player || !player->IsInWorld() || !player->GetGroup() ||
                bot->GetGroup() != player->GetGroup())
            {
                bot->GetPlayerbotAI()->ChangeStrategy(
                    "-stay,+follow,-wander", BotState::BOT_STATE_NON_COMBAT);
                LogEvent(session, "assembly_cancelled");
                erase = true;
            }
            else if (!bot->IsInCombat() &&
                !bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
            {
                session.state = "approaching";
                session.stateSince = now;
                bot->GetPlayerbotAI()->ChangeStrategy(
                    "-stay,+follow,-wander", BotState::BOT_STATE_NON_COMBAT);
                bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
                LogEvent(session, "assembly_rejoin");
            }
            else if (!bot->IsInCombat() && sServerFacade.isMoving(bot))
                bot->GetPlayerbotAI()->StopMoving();
        }
        else if (session.state == "arrived")
        {
            if (!player || !player->IsInWorld() || player->GetMapId() != bot->GetMapId())
            {
                session.state = "departing"; session.reason = "player_unavailable"; session.stateSince = now;
            }
            else if (!bot->IsInCombat() && !bot->IsWithinDistInMap(player, INTERACTION_DISTANCE))
            {
                // The trade has not completed merely because the bot reached
                // the player. Recover from incidental movement instead of
                // silently abandoning the still-authorized transaction.
                session.state = "approaching";
                session.stateSince = now;
                bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
                LogEvent(session, "arrival_distance_recovered");
            }
            else if (!bot->IsInCombat())
                bot->GetPlayerbotAI()->StopMoving();
        }
        else if (session.state == "departing")
        {
            long elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - session.stateSince).count();
            bool hidden = IsPointUnobserved(bot, bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ());
            if (hidden || elapsed >= std::max<uint32>(15,
                std::min<uint32>(300, sPlayerbotAIConfig.chatDirectorRendezvousDepartureSeconds)))
            {
                ReturnToActivity(session, bot);
                LogEvent(session, hidden ? "activity_restored" : "natural_resume_no_visible_teleport");
                erase = true;
            }
        }
        if (erase) iterator = sessions.erase(iterator); else ++iterator;
    }
}

Player* PlayerbotRendezvousManager::FindPartyHuman(Player* bot) const
{
    if (!bot || !bot->GetGroup()) return nullptr;
    for (GroupReference* reference = bot->GetGroup()->GetFirstMember(); reference; reference = reference->next())
    {
        Player* member = reference->getSource();
        if (member && member->IsInWorld() && member->isRealPlayer())
            return member;
    }
    return nullptr;
}

bool PlayerbotRendezvousManager::PartyHasHuman(Player* bot) const
{
    return FindPartyHuman(bot) != nullptr;
}

bool PlayerbotRendezvousManager::PartySafeToRelease(Player* bot) const
{
    return bot && bot->IsInWorld() && bot->IsAlive() && !bot->IsInCombat() && !bot->GetTransport() &&
        !bot->IsTaxiFlying() && !bot->InBattleGround() && !bot->GetMap()->IsDungeon();
}

bool PlayerbotRendezvousManager::StartPartyApproach(PartySession& session, Player* bot, Player* player)
{
    if (!bot || !player || !bot->IsInWorld() || !player->IsInWorld())
    {
        session.reason = "participant_unavailable";
        return false;
    }
    if (!bot->IsAlive())
    {
        session.reason = "bot_dead";
        return false;
    }
    if (bot->IsInCombat())
    {
        session.reason = "bot_in_combat";
        return false;
    }
    if (bot->IsTaxiFlying())
    {
        session.reason = "bot_on_taxi";
        return false;
    }
    if (bot->InBattleGround() || bot->GetMap()->IsDungeon() || player->InBattleGround() ||
        player->GetMap()->IsDungeon())
    {
        session.reason = "restricted_map";
        return false;
    }
    if (!player->IsAlive())
    {
        session.reason = "player_dead";
        return false;
    }

    const auto now = std::chrono::steady_clock::now();
    bool sameMap = bot->GetMapId() == player->GetMapId() && bot->GetInstanceId() == player->GetInstanceId();
    float distance = sameMap ? bot->GetDistance(player) : 100000.0f;
    uint32 triggerSeconds = std::max<uint32>(10, std::min<uint32>(300,
        sPlayerbotAIConfig.chatDirectorRendezvousTriggerSeconds));
    bool needsCatchup = !sameMap || distance > kRunSpeedYardsPerSecond * triggerSeconds;

    if (needsCatchup)
    {
        if (!sPlayerbotAIConfig.chatDirectorRendezvousCatchup)
        {
            session.reason = "catchup_disabled";
            return false;
        }
        auto cooldown = lastRelocation.find(bot->GetGUIDLow());
        if (!session.forceRelocation && cooldown != lastRelocation.end() &&
            std::chrono::duration_cast<std::chrono::seconds>(now - cooldown->second).count() <
                std::max<uint32>(60, sPlayerbotAIConfig.chatDirectorRendezvousCooldownSeconds))
        {
            session.reason = "relocation_cooldown";
            return false;
        }

        // FindStagingPoint uses the target player's map and authoritative path
        // data. This also permits a /who invite from another outdoor zone.
        float stageX = 0.0f, stageY = 0.0f, stageZ = 0.0f;
        if (!FindStagingPoint(bot, player, stageX, stageY, stageZ))
        {
            session.reason = "no_hidden_staging_point";
            return false;
        }
        GenericTransport* transport = bot->GetTransport();
        bot->GetPlayerbotAI()->StopMoving();
        if (transport)
        {
            // Playerbots' normal MoveOffTransport path removes the passenger
            // before teleporting. Reuse the same authoritative transition for
            // party assists instead of leaving zeppelin passengers pending
            // forever.
            transport->RemovePassenger(bot);
            LogPartyEvent(session, "transport_detached_for_arrival");
        }
        if (sameMap)
            bot->NearTeleportTo(stageX, stageY, stageZ, bot->GetAngle(player));
        else if (!bot->TeleportTo(player->GetMapId(), stageX, stageY, stageZ, player->GetOrientation()))
        {
            session.reason = "cross_map_teleport_rejected";
            return false;
        }
        session.relocated = true;
        session.forceRelocation = false;
        lastRelocation[bot->GetGUIDLow()] = now;
        LogPartyEvent(session, "relocated_for_arrival");
    }
    else
        LogPartyEvent(session, "ordinary_arrival");

    session.reason.clear();
    session.state = "approaching";
    session.stateSince = now;
    session.approachIssued = false;
    return true;
}

bool PlayerbotRendezvousManager::ReturnPartyToActivity(PartySession& session, Player* bot)
{
    if (!bot || !bot->IsInWorld()) return false;
    if (session.relocated && IsPointUnobserved(bot, bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()))
    {
        Map* originMap = sMapMgr.FindMap(session.originMapId, session.originInstanceId);
        if (originMap)
        {
            bool originHidden = true;
            float visibility = originMap->GetVisibilityDistance();
            for (const auto& reference : originMap->GetPlayers())
            {
                Player* observer = reference.getSource();
                if (IsRealObserver(observer) && observer->IsWithinDist3d(session.originX, session.originY,
                    session.originZ, visibility) && observer->IsWithinLOS(session.originX, session.originY,
                    session.originZ + bot->GetCollisionHeight(), false))
                {
                    originHidden = false;
                    break;
                }
            }
            if (originHidden)
                bot->TeleportTo(session.originMapId, session.originX, session.originY, session.originZ, session.originO);
        }
    }
    bot->GetPlayerbotAI()->SetMaster(nullptr);
    bot->GetPlayerbotAI()->DoSpecificAction("reset travel target", Event("living party assist resume"), true);
    return true;
}

void PlayerbotRendezvousManager::UpdatePartyAssists()
{
    const auto now = std::chrono::steady_clock::now();
    bool relocationIssuedThisUpdate = false;
    for (auto iterator = partySessions.begin(); iterator != partySessions.end(); )
    {
        PartySession& session = iterator->second;
        Player* bot = sRandomPlayerbotMgr.GetPlayerBot(session.botGuid);
        bool erase = false;
        if (!bot || !bot->IsInWorld())
            erase = true;
        else
        {
            Group* group = bot->GetGroup();
            bool originalParty = group && group->GetId() == session.groupId;
            Player* human = originalParty ? FindPartyHuman(bot) : nullptr;
            bool waitingForReconnect = false;

            // Group membership persists while a real player is temporarily
            // disconnected. Keep the bots and their party-assist state intact
            // for a bounded reconnect window, but do not delay an intentional
            // leave because the player's group membership is then already gone.
            ObjectGuid assistedHuman(HIGHGUID_PLAYER, session.playerGuid);
            bool assistedHumanStillMember = originalParty && group->IsMember(assistedHuman);
            if (!human && assistedHumanStillMember)
            {
                if (session.humanAbsentSince.time_since_epoch().count() == 0)
                {
                    session.humanAbsentSince = now;
                    session.reason = "waiting_for_human_reconnect";
                    LogPartyEvent(session, "reconnect_grace_started");
                }
                uint32 graceSeconds = std::max<uint32>(60, std::min<uint32>(900,
                    sPlayerbotAIConfig.chatDirectorPartyDisconnectGraceSeconds));
                waitingForReconnect = std::chrono::duration_cast<std::chrono::seconds>(
                    now - session.humanAbsentSince).count() < graceSeconds;
            }
            else if (human && session.humanAbsentSince.time_since_epoch().count() != 0)
            {
                session.humanAbsentSince = std::chrono::steady_clock::time_point();
                session.reason.clear();
                LogPartyEvent(session, "human_reconnected");
            }

            // During logout and instance/map transfers the human can remain
            // an authoritative group member while temporarily having no live
            // Player object. Preserve the reconnect grace state, but do not
            // fall through into active/free-time/hearth branches that
            // dereference the absent human. The next world update resumes the
            // same session as soon as FindPartyHuman can resolve the player.
            if (waitingForReconnect)
            {
                ++iterator;
                continue;
            }

            // A bot in a human party may reach a spirit healer only because
            // its automated corpse navigation failed. Do not make the human
            // party wait through resurrection sickness for that automation
            // failure. Keep the normal durability loss, and leave autonomous
            // and bot-only resurrection behavior unchanged.
            if (originalParty && human && bot->IsAlive() &&
                bot->HasAura(SPELL_ID_PASSIVE_RESURRECTION_SICKNESS))
            {
                bot->RemoveAurasDueToSpell(SPELL_ID_PASSIVE_RESURRECTION_SICKNESS);
                LogPartyEvent(session, "party_resurrection_sickness_cleared");
            }

            // The normal dead strategy can be starved by a persistent
            // human-master follow goal. Preserve the party rendezvous while
            // first asking the existing corpse actions to recover normally,
            // then fall back to the normal spirit-healer path after a bounded
            // wait. Never teleport or resurrect the corpse directly here.
            if (originalParty && human && !bot->IsAlive())
            {
                if (session.deadRecoveryStarted.time_since_epoch().count() == 0)
                {
                    session.deadRecoveryStarted = now;
                    session.nextDeadRecoveryAttempt = now;
                    session.deadRecoveryAttempts = 0;
                    session.reason = "waiting_for_corpse_recovery";
                    LogPartyEvent(session, "dead_recovery_started");
                }

                if (now >= session.nextDeadRecoveryAttempt)
                {
                    long recoverySeconds = std::chrono::duration_cast<std::chrono::seconds>(
                        now - session.deadRecoveryStarted).count();
                    Corpse* corpse = bot->GetCorpse();
                    const char* action = !corpse ? "auto release" :
                        (recoverySeconds >= 60 ? "spirit healer" : "find corpse");
                    bool accepted = bot->GetPlayerbotAI()->DoSpecificAction(
                        action, Event("living party dead recovery", "", human), true);
                    ++session.deadRecoveryAttempts;
                    session.nextDeadRecoveryAttempt = now + std::chrono::seconds(10);
                    session.reason = std::string(action) + (accepted ? "_accepted" : "_not_ready");
                    LogPartyEvent(session, accepted ? "dead_recovery_step" : "dead_recovery_wait");
                }

                ++iterator;
                continue;
            }

            if (session.deadRecoveryStarted.time_since_epoch().count() != 0)
            {
                session.deadRecoveryStarted = std::chrono::steady_clock::time_point();
                session.nextDeadRecoveryAttempt = std::chrono::steady_clock::time_point();
                session.deadRecoveryAttempts = 0;
                session.state = "pending";
                session.reason = "dead_recovery_completed";
                session.forceRelocation = true;
                session.approachIssued = false;
                session.nextApproachAttempt = std::chrono::steady_clock::time_point();
                session.stateSince = now;
                LogPartyEvent(session, "dead_recovery_completed");
            }

            // Human-led mixed parties take a natural, bounded break when they
            // settle in a capital or a genuine service hub. Only bots with
            // authoritative work leave follow, and their start times are
            // staggered so entering town does not produce a chat chorus.
            if (originalParty && human && session.state == "active" && bot->IsAlive() && human->IsAlive() &&
                !bot->IsInCombat() && !human->IsInCombat() && !bot->IsTaxiFlying() && !bot->GetTransport() &&
                group->IsLeader(human->GetObjectGuid()) &&
                (!session.nextSettlementCheck.time_since_epoch().count() || now >= session.nextSettlementCheck))
            {
                session.nextSettlementCheck = now + std::chrono::seconds(5);
                uint32 settlement = SettlementKey(bot, human);
                if (!settlement)
                {
                    session.settlementKey = 0;
                    session.automaticErrandReadyAt = std::chrono::steady_clock::time_point();
                }
                else if (session.settlementKey != settlement)
                {
                    session.settlementKey = settlement;
                    session.automaticErrandReadyAt = now + std::chrono::seconds(8 + (session.botGuid % 5));
                }
                else if (now >= session.automaticErrandReadyAt &&
                    (!session.automaticErrandCooldownUntil.time_since_epoch().count() ||
                     now >= session.automaticErrandCooldownUntil))
                {
                    uint32 errandMask = GroundedSettlementErrandMask(bot);
                    std::vector<std::string> errands = PersonalErrands(errandMask);
                    session.automaticErrandCooldownUntil = now + std::chrono::minutes(errands.empty() ? 2 : 10);
                    if (!errands.empty())
                    {
                        std::string announcement = ErrandAnnouncement(errands);
                        if (BeginPartyFreeTime(bot, human, "automatic_settlement_errands"))
                        {
                            bot->GetPlayerbotAI()->SayToParty(announcement, true);
                            LogPartyEvent(session, "automatic_settlement_errands_started");
                        }
                    }
                }
            }

            bool canSyncHearth = originalParty && human && bot->IsAlive() && human->IsAlive() &&
                !bot->IsInCombat() && !human->IsInCombat() &&
                !bot->IsTaxiFlying() && !bot->GetTransport() && !bot->IsBeingTeleported() &&
                session.state != "departing" && session.state != "hearth_sync" &&
                session.state != "free_time";
            if (canSyncHearth && IsCastingHearthstone(human))
            {
                session.state = "hearth_sync";
                session.reason = "human_hearthstone";
                session.hearthStartMapId = human->GetMapId();
                session.hearthStartX = human->GetPositionX();
                session.hearthStartY = human->GetPositionY();
                session.hearthStartZ = human->GetPositionZ();
                session.hearthStarted = now;
                bot->GetPlayerbotAI()->DoSpecificAction(
                    "hearthstone", Event("living party hearth", "follow human hearth", human), true);
                LogPartyEvent(session, "hearth_sync_started");
            }

            if (session.state == "departing")
            {
                if (PartySafeToRelease(bot))
                {
                    long elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - session.stateSince).count();
                    bool hidden = IsPointUnobserved(bot, bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ());
                    if (hidden || elapsed >= std::max<uint32>(15,
                        std::min<uint32>(300, sPlayerbotAIConfig.chatDirectorRendezvousDepartureSeconds)))
                    {
                        ReturnPartyToActivity(session, bot);
                        LogPartyEvent(session, hidden ? "activity_restored" : "natural_resume_no_visible_teleport");
                        erase = true;
                    }
                }
            }
            else if ((!originalParty || !human) && !waitingForReconnect)
            {
                if (session.state != "departing" && PartySafeToRelease(bot))
                {
                    if (group && group->GetId() == session.groupId && !PartyHasHuman(bot))
                    {
                        WorldPacket packet;
                        packet << uint32(PARTY_OP_LEAVE) << bot->GetName() << uint32(0);
                        bot->GetSession()->HandleGroupDisbandOpcode(packet);
                    }
                    session.state = "departing";
                    session.reason = originalParty ? "last_human_left" : "party_ended";
                    session.stateSince = now;
                    // Walk away naturally first; the hidden return occurs only
                    // after no real player can observe either endpoint.
                    float angle = bot->GetOrientation();
                    float x = bot->GetPositionX() + std::cos(angle) * 45.0f;
                    float y = bot->GetPositionY() + std::sin(angle) * 45.0f;
                    float z = bot->GetMap()->GetHeight(x, y, bot->GetPositionZ() + 10.0f);
                    if (z > -100000.0f)
                        bot->GetMotionMaster()->MovePoint(bot->GetMapId(), x, y, z, FORCED_MOVEMENT_RUN);
                    LogPartyEvent(session, "departure_started");
                }
            }
            else if (session.state == "hearth_sync")
            {
                long elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - session.hearthStarted).count();
                if (!IsCastingHearthstone(human))
                {
                    if (elapsed >= 8)
                    {
                        // A bot's own hearth bind may differ from the human's.
                        // Reuse the authoritative party rendezvous after the cast
                        // so every bot converges on the human's actual destination.
                        session.state = "pending";
                        session.reason = "follow_human_hearth_destination";
                        session.forceRelocation = true;
                        session.approachIssued = false;
                        session.nextApproachAttempt = std::chrono::steady_clock::time_point();
                        session.stateSince = now;
                        LogPartyEvent(session, "hearth_destination_queued");
                    }
                    else
                    {
                        Spell* spell = bot->GetCurrentSpell(CURRENT_GENERIC_SPELL);
                        if (spell && spell->m_spellInfo && spell->m_spellInfo->Id == 8690)
                            bot->InterruptSpell(CURRENT_GENERIC_SPELL, false);
                        bool nearby = bot->GetMapId() == human->GetMapId() &&
                            bot->GetInstanceId() == human->GetInstanceId() && bot->IsWithinDistInMap(human, 12.0f);
                        session.state = nearby ? "active" : "approaching";
                        session.reason = "human_hearth_cancelled";
                        session.approachIssued = false;
                        session.stateSince = now;
                        LogPartyEvent(session, "hearth_sync_cancelled");
                    }
                }
            }
            else if (session.state == "free_time")
            {
                bool humanMovedOn = human->GetMapId() != bot->GetMapId() ||
                    human->GetZoneId() != session.freeTimePlayerZoneId;
                bool automaticSettlement = session.reason == "automatic_settlement_errands";
                if (automaticSettlement && !IsCapital(human) &&
                    sServerFacade.GetAreaId(human) != session.freeTimePlayerAreaId)
                    humanMovedOn = true;
                bool errandsFinished = false;
                bool automaticHardTimeout = false;
                bool automaticIdleTimeout = false;
                if (automaticSettlement &&
                    std::chrono::duration_cast<std::chrono::seconds>(now - session.stateSince).count() >= 45 &&
                    (!session.nextAutomaticErrandCheck.time_since_epoch().count() ||
                     now >= session.nextAutomaticErrandCheck))
                {
                    session.nextAutomaticErrandCheck = now + std::chrono::seconds(10);
                    uint32 previousErrands = session.automaticErrandMask;
                    // Keep the announced task list stable. A new goal or item
                    // acquired during free time belongs to the next visit and
                    // must not silently expand the promise already made.
                    uint32 remainingErrands = PersonalErrandMask(bot) & session.automaticErrandScopeMask;
                    float dx = bot->GetPositionX() - session.automaticErrandLastX;
                    float dy = bot->GetPositionY() - session.automaticErrandLastY;
                    bool traveled = dx * dx + dy * dy >= 25.0f;

                    if (remainingErrands != previousErrands)
                    {
                        session.automaticErrandMask = remainingErrands;
                        session.freeTimeUntil = std::min(session.automaticErrandHardDeadline,
                            now + std::chrono::minutes(5));
                        LogAutomaticErrandEvent(session, bot, "tasks_changed", previousErrands,
                            remainingErrands);
                        if (remainingErrands)
                            SetAutomaticErrandTarget(bot, remainingErrands);
                    }
                    if (traveled)
                    {
                        session.automaticErrandLastX = bot->GetPositionX();
                        session.automaticErrandLastY = bot->GetPositionY();
                        session.freeTimeUntil = std::min(session.automaticErrandHardDeadline,
                            now + std::chrono::minutes(5));
                        if (!session.nextAutomaticErrandProgressLog.time_since_epoch().count() ||
                            now >= session.nextAutomaticErrandProgressLog)
                        {
                            session.nextAutomaticErrandProgressLog = now + std::chrono::minutes(1);
                            LogAutomaticErrandEvent(session, bot, "travel_progress", remainingErrands,
                                remainingErrands);
                        }
                    }
                    errandsFinished = remainingErrands == 0;
                    automaticHardTimeout = !errandsFinished && now >= session.automaticErrandHardDeadline;
                    automaticIdleTimeout = !errandsFinished && !automaticHardTimeout &&
                        now >= session.freeTimeUntil;
                    bool firstStopReport = !session.freeTimeRecallRequested;
                    if (errandsFinished && firstStopReport)
                        LogAutomaticErrandEvent(session, bot, "completed", previousErrands, 0);
                    else if (automaticHardTimeout && firstStopReport)
                        LogAutomaticErrandEvent(session, bot, "hard_timeout", previousErrands,
                            remainingErrands);
                    else if (automaticIdleTimeout && firstStopReport)
                        LogAutomaticErrandEvent(session, bot, "idle_timeout", previousErrands,
                            remainingErrands);
                }
                bool freeTimeExpired = automaticSettlement ?
                    (automaticHardTimeout || automaticIdleTimeout) : now >= session.freeTimeUntil;
                if (human->IsInCombat() || humanMovedOn || errandsFinished || freeTimeExpired)
                    session.freeTimeRecallRequested = true;
                if (session.freeTimeRecallRequested && !bot->IsInCombat())
                {
                    std::string returnReason = humanMovedOn ? "free_time_party_moved_on" :
                        errandsFinished ? "automatic_settlement_errands_complete" :
                        automaticHardTimeout ? "automatic_settlement_errands_hard_timeout" :
                        automaticIdleTimeout ? "automatic_settlement_errands_idle_timeout" :
                        "free_time_complete";
                    ResumePartyAssist(bot, human, returnReason);
                }
            }
            else if (session.state == "pending")
            {
                session.playerGuid = human->GetGUIDLow();
                // Do not wait for one bot to finish its visible run before
                // starting another. Only serialize the actual teleport calls
                // by one world update so group and movement state are never
                // mutated repeatedly inside the same update iteration.
                if (!relocationIssuedThisUpdate &&
                    (session.nextApproachAttempt.time_since_epoch().count() == 0 || now >= session.nextApproachAttempt))
                {
                    // Combat, transit, and destination terrain can make an
                    // arrival temporarily unavailable. Retry without requiring
                    // the bot's remote departure point to be unobserved.
                    session.nextApproachAttempt = now + std::chrono::seconds(5);
                    ++session.approachAttempts;
                    bool wasRelocated = session.relocated;
                    bool started = StartPartyApproach(session, bot, human);
                    if (started && !wasRelocated && session.relocated)
                        relocationIssuedThisUpdate = true;
                    if (!started &&
                        (session.approachAttempts == 1 || session.approachAttempts % 6 == 0))
                    {
                        LogPartyEvent(session, "arrival_retry_wait");
                    }
                }
            }
            else if (session.state == "approaching")
            {
                if (bot->GetMapId() == human->GetMapId() && bot->GetInstanceId() == human->GetInstanceId())
                {
                    if (bot->IsWithinDistInMap(human, 12.0f))
                    {
                        session.state = "active";
                        session.stateSince = now;
                        session.lastHumanDistance = bot->GetDistance(human);
                        session.lastFollowProgress = now;
                        session.nextFollowRepair = now + std::chrono::seconds(6);
                        LogPartyEvent(session, "arrived");
                    }
                    else if (!session.approachIssued && !bot->IsInCombat() && !bot->IsBeingTeleported())
                    {
                        // Do not replace the follow movement generator every
                        // world update. Playerbots' normal party strategies can
                        // resume it if another authoritative action interrupts.
                        bot->GetMotionMaster()->MoveFollow(human, 2.0f, 0.0f, true, false);
                        session.approachIssued = true;
                    }
                }
            }
            else if (session.state == "active")
            {
                bool sameMap = bot->GetMapId() == human->GetMapId() &&
                    bot->GetInstanceId() == human->GetInstanceId();
                float distance = sameMap ? bot->GetDistance(human) : 100000.0f;
                if (sameMap && distance <= 12.0f)
                {
                    session.staleCombatSince = std::chrono::steady_clock::time_point();
                    session.lastHumanDistance = distance;
                    session.lastFollowProgress = now;
                    session.nextFollowRepair = now + std::chrono::seconds(6);
                }
                else
                {
                    // A stale combat flag can starve the normal follow and
                    // rendezvous paths forever: Playerbots remains in its combat
                    // engine, fails to select a target, and this maintenance
                    // branch traditionally refuses to move a combat-flagged bot.
                    // Clear only an ungrounded flag after a sustained timeout.
                    // Real combat always has a victim, attacker, hostile threat
                    // reference, cast, or loss-of-control state and is untouched.
                    bool ungroundedCombat = bot->IsInCombat() && sameMap && distance > 20.0f &&
                        !human->IsInCombat() && !bot->GetVictim() && bot->getAttackers().empty() &&
                        !bot->getHostileRefManager().getFirst() && !bot->IsNonMeleeSpellCasted(false) &&
                        !bot->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) &&
                        !bot->IsBeingTeleported() && !bot->IsTaxiFlying() && !bot->GetTransport() &&
                        !bot->InBattleGround() && !bot->duel;
                    if (ungroundedCombat)
                    {
                        if (session.staleCombatSince.time_since_epoch().count() == 0)
                        {
                            session.staleCombatSince = now;
                            session.reason = "stale_combat_follow_blocked";
                            LogPartyEvent(session, "stale_combat_follow_blocked");
                        }
                        long staleSeconds = std::chrono::duration_cast<std::chrono::seconds>(
                            now - session.staleCombatSince).count();
                        if (staleSeconds >= 12)
                        {
                            bot->CombatStop(true);
                            PlayerbotAI* ai = bot->GetPlayerbotAI();
                            ai->ChangeEngine(BotState::BOT_STATE_NON_COMBAT);
                            session.staleCombatSince = std::chrono::steady_clock::time_point();
                            session.lastFollowProgress = now - std::chrono::seconds(18);
                            session.nextFollowRepair = now;
                            session.reason = "stale_combat_cleared";
                            LogPartyEvent(session, "stale_combat_cleared");
                        }
                    }
                    else
                        session.staleCombatSince = std::chrono::steady_clock::time_point();

                    bool followBlocked = bot->IsInCombat() || bot->IsBeingTeleported() ||
                        bot->IsTaxiFlying() || bot->GetTransport();
                    if (!followBlocked)
                    {
                        if (session.lastFollowProgress.time_since_epoch().count() == 0 ||
                            distance + 1.5f < session.lastHumanDistance)
                        {
                            session.lastHumanDistance = distance;
                            session.lastFollowProgress = now;
                        }
                        long stalled = std::chrono::duration_cast<std::chrono::seconds>(
                            now - session.lastFollowProgress).count();
                        if (sameMap && distance > 20.0f && stalled >= 6 &&
                            (session.nextFollowRepair.time_since_epoch().count() == 0 || now >= session.nextFollowRepair))
                        {
                            bot->GetMotionMaster()->MoveFollow(human, 2.0f, 0.0f, true, false);
                            session.nextFollowRepair = now + std::chrono::seconds(6);
                            session.reason = "active_follow_reissued";
                            LogPartyEvent(session, "active_follow_repaired");
                        }
                        if ((!sameMap || distance > 70.0f) && stalled >= 18)
                        {
                            session.state = "pending";
                            session.reason = "active_follow_stalled";
                            session.forceRelocation = true;
                            session.approachIssued = false;
                            session.nextApproachAttempt = std::chrono::steady_clock::time_point();
                            session.stateSince = now;
                            LogPartyEvent(session, "active_follow_relocation_queued");
                        }
                    }
                }
            }
        }
        if (erase) iterator = partySessions.erase(iterator); else ++iterator;
    }
}

void PlayerbotRendezvousManager::LogPartyEvent(const PartySession& session, const char* event) const
{
    sLog.outString("Living WoW party rendezvous event=%s bot=%u player=%u group=%u state=%s relocated=%u prior_activity=%s reason=%s",
        event, session.botGuid, session.playerGuid, session.groupId, session.state.c_str(), session.relocated ? 1 : 0,
        session.previousActivity.c_str(), session.reason.c_str());
}

void PlayerbotRendezvousManager::LogAutomaticErrandEvent(const PartySession& session, Player* bot,
    const char* event, uint32 previousErrands, uint32 remainingErrands) const
{
    uint32 completedErrands = previousErrands & ~remainingErrands;
    sLog.outString("Living WoW party errands event=%s bot=%u player=%u group=%u completed=%s remaining=%s map=%u x=%.1f y=%.1f",
        event, session.botGuid, session.playerGuid, session.groupId,
        ErrandTelemetryNames(completedErrands).c_str(), ErrandTelemetryNames(remainingErrands).c_str(),
        bot ? bot->GetMapId() : 0, bot ? bot->GetPositionX() : 0.0f, bot ? bot->GetPositionY() : 0.0f);
}

bool PlayerbotRendezvousManager::IsActive(uint32 botGuid, uint32 playerGuid) const
{
    return Find(botGuid, playerGuid) != nullptr;
}

bool PlayerbotRendezvousManager::WasRelocated(uint32 botGuid, uint32 playerGuid) const
{
    const Session* session = Find(botGuid, playerGuid);
    return session && session->relocated;
}

std::string PlayerbotRendezvousManager::State(uint32 botGuid, uint32 playerGuid) const
{
    const Session* session = Find(botGuid, playerGuid);
    return session ? session->state : "none";
}

void PlayerbotRendezvousManager::LogEvent(const Session& session, const char* event) const
{
    sLog.outString("Living WoW rendezvous event=%s action=%s bot=%u player=%u state=%s relocated=%u prior_activity=%s reason=%s",
        event, session.actionId.c_str(), session.botGuid, session.playerGuid, session.state.c_str(),
        session.relocated ? 1 : 0, session.previousActivity.c_str(), session.reason.c_str());
}
