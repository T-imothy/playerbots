#pragma once
#include <chrono>
#include <map>
#include <mutex>
#include <set>
#include <string>
#include <vector>

class Player;
struct ChatDirectorCandidate;

class PlayerbotPartyInvitationMgr
{
public:
    static PlayerbotPartyInvitationMgr& instance();
    // Opcode ingress only captures identities. World Update owns all mutations.
    bool Queue(Player* bot, Player* requester);
    bool Update(); // Whether this update consumed the one party dock-exit attempt.
    void AddCapabilities(Player* bot, Player* speaker, ChatDirectorCandidate& candidate);
    bool Vote(Player* bot, Player* speaker, const std::string& ref, bool approve);
private:
    struct Request
    {
        uint64 id = 0;
        uint32 bot = 0, requester = 0, source = 0, sourceLeader = 0;
        uint32 destination = 0, destinationLeader = 0;
        std::set<uint32> roster, humans;
        std::map<uint32, bool> votes;
        bool announced = false;
        std::chrono::steady_clock::time_point expires, nextAttempt;
    };
    std::mutex mutex;
    std::recursive_mutex stateMutex;
    std::vector<Request> incoming;
    std::map<uint32, Request> requests;
    uint64 sequence = 0;
};
#define sPlayerbotPartyInvitationMgr PlayerbotPartyInvitationMgr::instance()
