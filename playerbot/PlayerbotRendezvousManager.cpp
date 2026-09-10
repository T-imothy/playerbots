#include "botpch.h"
#include "PlayerbotRendezvousManager.h"

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
    if (!bot || !bot->GetMap()) return false;
    float visibility = bot->GetMap()->GetVisibilityDistance();
    for (const auto& reference : bot->GetMap()->GetPlayers())
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
    if (!bot || !player || bot->GetMapId() != player->GetMapId()) return false;
    PathFinder path(bot->GetMapId(), bot->GetInstanceId());
    if (!path.calculate(Vector3(sx, sy, sz), Vector3(player->GetPositionX(), player->GetPositionY(), player->GetPositionZ()), true))
        return false;
    PathType type = path.getPathType();
    return !(type & PATHFIND_NOPATH) && !(type & PATHFIND_SHORTCUT) && !(type & PATHFIND_INCOMPLETE);
}

bool PlayerbotRendezvousManager::FindStagingPoint(Player* bot, Player* player, float& x, float& y, float& z) const
{
    if (!bot || !player || bot->GetMapId() != player->GetMapId()) return false;
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
            float cz = bot->GetMap()->GetHeight(cx, cy, player->GetPositionZ() + 25.0f);
            if (cz < -100000.0f || !IsPointUnobserved(bot, cx, cy, cz) || !ValidPath(bot, cx, cy, cz, player))
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
