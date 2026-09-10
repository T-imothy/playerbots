#include "botpch.h"
#include "PlayerbotRendezvousManager.h"

#include "Entities/Transports.h"
#include "MotionGenerators/PathFinder.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "RandomPlayerbotMgr.h"

#include <cmath>

namespace
{
    constexpr float kRunSpeedYardsPerSecond = 7.0f;

    bool IsRealObserver(Player* player)
    {
        return player && player->IsInWorld() && player->isRealPlayer();
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
        bot->IsInCombat() || bot->IsTaxiFlying() || bot->GetTransport() ||
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

    session.playerGuid = player->GetGUIDLow();
    session.state = "pending";
    session.reason = reason;
    session.forceRelocation = true;
    session.approachIssued = false;
    session.nextApproachAttempt = std::chrono::steady_clock::time_point();
    session.stateSince = std::chrono::steady_clock::now();
    LogPartyEvent(session, "party_return_queued");
    return true;
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
    if (!bot || !player || !bot->IsInWorld() || !player->IsInWorld() || bot->GetMapId() != player->GetMapId() ||
        bot->IsInCombat() || !bot->IsAlive() || !player->IsAlive() || bot->GetTransport() || bot->IsTaxiFlying())
        return RequestResult::unavailable;
    if (Find(bot->GetGUIDLow(), player->GetGUIDLow())) return RequestResult::accepted;

    const auto now = std::chrono::steady_clock::now();
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

    float distance = bot->GetDistance(player);
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
        bot->GetPlayerbotAI()->StopMoving();
        bot->NearTeleportTo(stageX, stageY, stageZ, bot->GetAngle(player));
        session.relocated = true;
        lastRelocation[bot->GetGUIDLow()] = now;
    }

    sessions[session.botGuid] = session;
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
                session.state = "arrived";
                session.stateSince = now;
                LogEvent(session, "arrived");
            }
            else if (std::chrono::duration_cast<std::chrono::seconds>(now - session.stateSince).count() >= 2)
            {
                bot->GetMotionMaster()->MoveFollow(player, 2.0f, 0.0f, true, false);
                session.stateSince = now;
            }
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
