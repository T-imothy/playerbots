#ifndef _PLAYERBOT_ACTION_BROKER_H
#define _PLAYERBOT_ACTION_BROKER_H

#include <chrono>
#include <map>
#include <string>
#include <vector>

class Player;

struct ChatDirectorEvent;

struct ChatDirectorActionProposal
{
    std::string proposalId;
    uint32 botGuid = 0;
    uint32 targetGuid = 0;
    std::string type;
    std::string capabilityRef;
    uint32 quantity = 0;
    std::string delivery;
    std::string intent;
};

class PlayerbotActionBroker
{
public:
    static PlayerbotActionBroker& instance();
    bool Create(const ChatDirectorActionProposal& proposal, const ChatDirectorEvent& event);
    bool Authorizes(Player* bot, Player* trader) const;
    bool PopulateTrade(Player* bot, Player* trader);
    bool ValidateTrade(Player* bot, Player* trader);
    void CompleteTrade(Player* bot, Player* trader);
    void CancelTrade(Player* bot, Player* trader, const std::string& reason);
    void Update();

private:
    struct Transaction
    {
        std::string transactionId;
        std::string eventId;
        std::string proposalId;
        uint32 botGuid = 0;
        uint32 playerGuid = 0;
        uint32 itemEntry = 0;
        uint32 itemGuid = 0;
        uint32 spellId = 0;
        uint32 quantity = 0;
        uint32 priceCopper = 0;
        std::string type;
        std::string delivery;
        std::string state;
        std::string failureReason;
        std::chrono::steady_clock::time_point expires;
        std::chrono::steady_clock::time_point preparingSince;
        std::chrono::steady_clock::time_point lastMeetingMove;
        std::chrono::steady_clock::time_point lastTradeRefresh;
    };

    Transaction* Find(uint32 botGuid, uint32 playerGuid);
    const Transaction* Find(uint32 botGuid, uint32 playerGuid) const;
    void Report(const Transaction& transaction) const;
    std::map<std::string, Transaction> transactions;
    std::map<uint32, std::string> reservedItems;
    std::map<uint32, uint32> reservedMoney;
    std::map<uint32, std::vector<std::chrono::steady_clock::time_point>> giftHistory;
};

#define sPlayerbotActionBroker PlayerbotActionBroker::instance()

#endif
