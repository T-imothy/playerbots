#ifndef _PLAYERBOT_RENDEZVOUS_MANAGER_H
#define _PLAYERBOT_RENDEZVOUS_MANAGER_H

#include <chrono>
#include <map>
#include <string>

class Player;
class Map;

class PlayerbotRendezvousManager
{
public:
    enum class RequestResult { accepted, ordinary_travel, unavailable, unsafe };

    static PlayerbotRendezvousManager& instance();
    RequestResult Request(Player* bot, Player* player, const std::string& actionId, bool returnAfter);
    // Registers a temporary human-created party assist without moving the bot
    // inside the invitation handler. The world update performs any relocation
    // after the group opcode and Playerbots strategy reset have completed.
    bool RegisterPartyAssist(Player* bot, Player* inviter);
    void BeginDeparture(uint32 botGuid, uint32 playerGuid, const std::string& reason);
    void Cancel(uint32 botGuid, uint32 playerGuid, const std::string& reason);
    void Update();
    bool IsActive(uint32 botGuid, uint32 playerGuid) const;
    bool WasRelocated(uint32 botGuid, uint32 playerGuid) const;
    std::string State(uint32 botGuid, uint32 playerGuid) const;

private:
    struct PartySession
    {
        uint32 botGuid = 0;
        uint32 playerGuid = 0;
        uint32 groupId = 0;
        uint32 originMapId = 0;
        uint32 originInstanceId = 0;
        float originX = 0.0f;
        float originY = 0.0f;
        float originZ = 0.0f;
        float originO = 0.0f;
        std::string previousActivity;
        std::string state;
        std::string reason;
        bool relocated = false;
        bool approachIssued = false;
        std::chrono::steady_clock::time_point stateSince;
    };

    struct Session
    {
        uint32 botGuid = 0;
        uint32 playerGuid = 0;
        uint32 mapId = 0;
        float originX = 0.0f;
        float originY = 0.0f;
        float originZ = 0.0f;
        float originO = 0.0f;
        std::string actionId;
        std::string previousActivity;
        std::string state;
        std::string reason;
        bool returnAfter = true;
        bool relocated = false;
        bool combatPaused = false;
        std::chrono::steady_clock::time_point started;
        std::chrono::steady_clock::time_point stateSince;
    };

    Session* Find(uint32 botGuid, uint32 playerGuid);
    const Session* Find(uint32 botGuid, uint32 playerGuid) const;
    bool IsPointUnobserved(Player* bot, float x, float y, float z) const;
    bool IsPointUnobservedOnMap(Map* map, Player* bot, float x, float y, float z) const;
    bool FindStagingPoint(Player* bot, Player* player, float& x, float& y, float& z) const;
    bool ValidPath(Player* bot, float sx, float sy, float sz, Player* player) const;
    bool ReturnToActivity(Session& session, Player* bot);
    void UpdatePartyAssists();
    Player* FindPartyHuman(Player* bot) const;
    bool PartyHasHuman(Player* bot) const;
    bool PartySafeToRelease(Player* bot) const;
    bool StartPartyApproach(PartySession& session, Player* bot, Player* player);
    bool ReturnPartyToActivity(PartySession& session, Player* bot);
    void LogPartyEvent(const PartySession& session, const char* event) const;
    void LogEvent(const Session& session, const char* event) const;

    std::map<uint32, Session> sessions;
    std::map<uint32, PartySession> partySessions;
    std::map<uint32, std::chrono::steady_clock::time_point> lastRelocation;
};

#define sPlayerbotRendezvousManager PlayerbotRendezvousManager::instance()

#endif
