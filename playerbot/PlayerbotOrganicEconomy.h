#ifndef _PLAYERBOT_ORGANIC_ECONOMY_H
#define _PLAYERBOT_ORGANIC_ECONOMY_H

#include "Common.h"

#include <chrono>
#include <future>
#include <map>
#include <string>

class Player;

class PlayerbotOrganicEconomy
{
public:
    static PlayerbotOrganicEconomy& instance();
    void Update();
    std::string CurrentGoalType(uint32 characterGuid) const;
    bool IsAuctionPostingEnabled() const { return policy.mode == "active" && policy.posting; }

private:
    struct Policy
    {
        std::string mode = "observe";
        bool careers = false;
        bool posting = false;
        bool buying = false;
        bool commissions = false;
        bool advertising = false;
        uint32 cadenceSeconds = 600;
        uint32 botAdCooldownSeconds = 3600;
        uint32 channelAdCooldownSeconds = 600;
    };

    struct Profile
    {
        bool career = false;
        uint32 intendedOne = 0;
        uint32 intendedTwo = 0;
        std::string currentGoalId;
        std::string currentGoalType;
        std::string currentGoalState;
    };

    PlayerbotOrganicEconomy() = default;
    Policy LoadPolicy();
    std::map<uint32, Profile> LoadProfiles();
    bool Submit(const Policy& policy);
    void ApplyPlans(const std::string& response, const Policy& policy);
    void ProcessActiveGoals(const Policy& policy, std::chrono::steady_clock::time_point now);
    bool ExecuteGoal(Player* bot, Profile& profile, const Policy& policy, std::string& failureReason);
    bool SafeForEconomy(Player* bot) const;
    bool Advertise(Player* bot, uint32 itemEntry, const Policy& policy);

    std::future<std::string> pendingPlans;
    std::chrono::steady_clock::time_point nextSubmit;
    std::chrono::steady_clock::time_point nextPolicyLoad;
    std::chrono::steady_clock::time_point lastChannelAd;
    std::chrono::steady_clock::time_point nextExecutionSweep;
    std::map<uint32, std::chrono::steady_clock::time_point> actionCooldowns;
    std::map<uint32, std::chrono::steady_clock::time_point> retryCooldowns;
    std::map<uint32, std::chrono::steady_clock::time_point> adCooldowns;
    uint32 executionCursor = 0;
    std::map<uint32, Profile> profiles;
    Policy policy;
};

#define sPlayerbotOrganicEconomy PlayerbotOrganicEconomy::instance()

#endif
