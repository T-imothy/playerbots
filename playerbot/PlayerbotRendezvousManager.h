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
    // Re-arm an existing mixed-party assist after a scoped trip (for example,
    // vending) so the bot returns through the same catch-up relocation used
    // after an invitation instead of selecting ordinary long-distance travel.
    bool ResumePartyAssist(Player* bot, Player* player, const std::string& reason);
    // Temporarily release a human-led party bot from close follow so its
    // existing RPG/economy strategies can perform personal errands. The bot
    // remains in the party and can be recalled through ResumePartyAssist.
    bool BeginPartyFreeTime(Player* bot, Player* player, const std::string& reason);
    bool IsPartyFreeTime(uint32 botGuid) const;
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
        bool forceRelocation = false;
        bool approachIssued = false;
        bool freeTimeRecallRequested = false;
        uint32 approachAttempts = 0;
        uint32 deadRecoveryAttempts = 0;
        float lastHumanDistance = 0.0f;
        uint32 hearthStartMapId = 0;
        uint32 freeTimePlayerZoneId = 0;
        float hearthStartX = 0.0f;
        float hearthStartY = 0.0f;
        float hearthStartZ = 0.0f;
        std::chrono::steady_clock::time_point stateSince;
        std::chrono::steady_clock::time_point nextApproachAttempt;
        std::chrono::steady_clock::time_point humanAbsentSince;
        std::chrono::steady_clock::time_point lastFollowProgress;
        std::chrono::steady_clock::time_point nextFollowRepair;
        std::chrono::steady_clock::time_point deadRecoveryStarted;
        std::chrono::steady_clock::time_point nextDeadRecoveryAttempt;
        std::chrono::steady_clock::time_point freeTimeUntil;
        std::chrono::steady_clock::time_point hearthStarted;
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
    std::chrono::steady_clock::time_point nextPartyDiscovery;
};

#define sPlayerbotRendezvousManager PlayerbotRendezvousManager::instance()

#endif
