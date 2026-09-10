#ifndef _PLAYERBOT_SOCIAL_ACTION_BROKER_H
#define _PLAYERBOT_SOCIAL_ACTION_BROKER_H

#include <chrono>
#include <map>
#include <set>
#include <string>

class Player;
class ObjectGuid;
struct ChatDirectorActionProposal;
struct ChatDirectorCandidate;
struct ChatDirectorEvent;

class PlayerbotSocialActionBroker
{
public:
    static PlayerbotSocialActionBroker& instance();
    bool Supports(const std::string& type) const;
    bool Create(const ChatDirectorActionProposal& proposal, const ChatDirectorEvent& event);
    bool CanUseSharedObject(Player* bot, Player* player, ObjectGuid guid);
    void AddSharedObjectCapabilities(Player* bot, Player* player, ChatDirectorCandidate& candidate);
    uint32 PreferredQuest(uint32 botGuid) const;
    void Update();

private:
    struct Action
    {
        std::string actionId;
        std::string eventId;
        std::string proposalId;
        std::string type;
        std::string capabilityRef;
        uint32 botGuid = 0;
        uint32 playerGuid = 0;
        uint32 groupId = 0;
        uint32 questId = 0;
        uint8 initialBagUsage = 0;
        uint8 sellAttempts = 0;
        std::string maintenanceType;
        bool outboundRelocated = false;
        bool restoreFollow = false;
        std::string state;
        std::string failureReason;
        std::chrono::steady_clock::time_point expires;
        std::chrono::steady_clock::time_point stateSince;
        std::chrono::steady_clock::time_point lastSellAttempt;
        std::chrono::steady_clock::time_point completedAt;
    };

    struct SharedObjectOffer
    {
        uint32 botGuid = 0;
        uint32 playerGuid = 0;
        uint32 groupId = 0;
        uint64 objectGuid = 0;
        uint32 objectEntry = 0;
        uint32 skillId = 0;
        uint32 requiredSkill = 0;
        std::string nodeName;
        std::string objectKind;
        std::string state;
        std::chrono::steady_clock::time_point expires;
    };

    bool ValidateCommon(Player* bot, Player* player) const;
    bool HasActiveVendorTrip(uint32 botGuid) const;
    bool StartVendorTrip(Player* bot, Player* player, const std::string& actionId,
        const std::string& eventId, const std::string& proposalId, bool announce);
    bool SetMaintenanceTarget(Player* bot, const std::string& maintenanceType) const;
    void QueuePartyReturn(Action& action, Player* bot, Player* player,
        const std::string& reason, bool success);
    void Report(const Action& action) const;
    std::map<std::string, Action> actions;
    std::map<uint32, std::pair<uint32, std::chrono::steady_clock::time_point>> preferredQuests;
    std::map<uint32, std::chrono::steady_clock::time_point> vendorCooldowns;
    std::set<uint32> vendorPressureNotified;
    std::map<uint32, SharedObjectOffer> sharedObjectOffers;
    std::chrono::steady_clock::time_point nextVendorScan;
};

#define sPlayerbotSocialActionBroker PlayerbotSocialActionBroker::instance()

#endif
