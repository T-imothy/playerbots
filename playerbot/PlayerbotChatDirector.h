#ifndef _PLAYERBOT_CHAT_DIRECTOR_H
#define _PLAYERBOT_CHAT_DIRECTOR_H

#include <chrono>
#include <future>
#include <map>
#include <mutex>
#include <string>
#include <vector>

class Player;
struct ChatDirectorActionProposal;

struct ChatDirectorCapability
{
    std::string capabilityRef;
    std::string type;
    std::string itemName;
    std::string itemKind;
    uint32 quantity = 0;
    uint32 minQuantity = 0;
    uint32 maxQuantity = 0;
    uint32 priceCopper = 0;
    uint32 valueCopper = 0;
    std::vector<std::string> deliveries;
};

struct ChatDirectorCandidate
{
    uint32 guid = 0;
    std::string name;
    uint8 race = 0;
    uint8 cls = 0;
    uint8 level = 1;
    uint32 zone = 0;
    uint32 subzone = 0;
    std::string zoneName;
    std::string subzoneName;
    std::string role;
    std::string currentActivity;
    std::string questLog;
    bool questLogTruncated = false;
    bool grouped = false;
    bool inCombat = false;
    bool available = true;
    std::vector<ChatDirectorCapability> actionCapabilities;
};

struct ChatDirectorEvent
{
    std::string key;
    std::string eventId;
    std::string channelType;
    std::string channelName;
    std::string speakerName;
    uint32 speakerGuid = 0;
    uint8 speakerLevel = 1;
    uint32 zone = 0;
    uint32 team = 0;
    std::string message;
    bool ambient = false;
    bool factualGrounding = false;
    std::map<uint32, ChatDirectorCandidate> candidates;
    std::chrono::steady_clock::time_point firstSeen;
};

struct ChatDirectorReply
{
    uint32 botGuid = 0;
    std::string text;
    uint32 delayMs = 2000;
    std::string requiresActionId;
};

class PlayerbotChatDirector
{
public:
    static PlayerbotChatDirector& instance();
    void Observe(Player* bot, uint32 msgType, uint32 speakerGuid, const std::string& speakerName,
        const std::string& message, const std::string& channelName);
    void Update();

private:
    struct ActiveRequest
    {
        ChatDirectorEvent event;
        std::future<std::string> response;
    };

    struct ScheduledReply
    {
        ChatDirectorEvent event;
        ChatDirectorReply reply;
        std::chrono::steady_clock::time_point due;
    };

    std::string ChannelType(uint32 msgType, const std::string& channelName) const;
    std::string BuildJson(const ChatDirectorEvent& event) const;
    std::vector<ChatDirectorReply> ParseReplies(const std::string& response) const;
    std::vector<ChatDirectorActionProposal> ParseActionProposals(const std::string& response) const;
    void Dispatch(const ScheduledReply& scheduled);
    void MaybeCreateAmbientEvent(std::chrono::steady_clock::time_point now);
    void MaybeReportBotHealth(std::chrono::steady_clock::time_point now);

    struct BotHealthState
    {
        float x = 0.0f;
        float y = 0.0f;
        std::chrono::steady_clock::time_point lastMoved;
        std::chrono::steady_clock::time_point completedQuestSince;
        std::chrono::steady_clock::time_point heightFaultSince;
        std::chrono::steady_clock::time_point lastRecovery;
        std::vector<std::chrono::steady_clock::time_point> recoveryAttempts;
        std::string recoveryResult;
        uint8 lastLevel = 0;
    };

    std::mutex mutex;
    std::map<std::string, ChatDirectorEvent> pending;
    std::vector<ActiveRequest> active;
    std::vector<ScheduledReply> scheduled;
    uint64 sequence = 0;
    std::chrono::steady_clock::time_point nextAmbient;
    std::chrono::steady_clock::time_point lastConversation;
    std::chrono::steady_clock::time_point nextHealthSample;
    std::map<uint32, BotHealthState> botHealth;
};

#define sPlayerbotChatDirector PlayerbotChatDirector::instance()

#endif
