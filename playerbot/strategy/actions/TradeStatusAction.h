#pragma once
#include "QueryItemUsageAction.h"

namespace ai
{
    class TradeStatusAction : public QueryItemUsageAction
    {
    public:
        TradeStatusAction(PlayerbotAI* ai) : QueryItemUsageAction(ai, "accept trade") {}
        virtual bool Execute(Event& event) override;

    private:
        void BeginTrade(bool listInventory = true);
        bool CheckTrade();
        int32 CalculateCost(Player *player, bool sell);
    };
}
