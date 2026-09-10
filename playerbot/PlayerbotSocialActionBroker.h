#ifndef _PLAYERBOT_SOCIAL_ACTION_BROKER_H
#define _PLAYERBOT_SOCIAL_ACTION_BROKER_H

#include <chrono>
#include <map>
#include <string>

class Player;
struct ChatDirectorActionProposal;
struct ChatDirectorEvent;

class PlayerbotSocialActionBroker
{
public:
    static PlayerbotSocialActionBroker& instance();
    bool Supports(const std::string& type) const;
    bool Create(const ChatDirectorActionProposal& proposal, const ChatDirectorEvent& event);
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
        std::string state;
        std::string failureReason;
        std::chrono::steady_clock::time_point expires;
        std::chrono::steady_clock::time_point completedAt;
    };

    bool ValidateCommon(Player* bot, Player* player) const;
    void Report(const Action& action) const;
    std::map<std::string, Action> actions;
    std::map<uint32, std::pair<uint32, std::chrono::steady_clock::time_point>> preferredQuests;
};

#define sPlayerbotSocialActionBroker PlayerbotSocialActionBroker::instance()

#endif
