#pragma once

#include "playerbot/RandomPlayerbotMgr.h"
#include "playerbot/strategy/Action.h"

#include "playerbot/BotSlots.h"
namespace ai
{
    class RandomBotUpdateAction : public Action
    {
    public:
        // This owner-local manual flag is also the full isUseful predicate.
        // Avoid handing an idle population-maintenance check to the world.
        bool RequiresWorldOwner() const override { return context->GetValue<bool>("random bot update")->Get(); }
        RandomBotUpdateAction(PlayerbotAI* ai) : Action(ai, "random bot update")
        {}

        virtual bool Execute(Event& event) override
        {
            if (!sRandomPlayerbotMgr.IsRandomBot(bot))
                return false;

            if (bot->GetGroup() && ai->GetGroupMaster() && (!GetBotAI(ai->GetGroupMaster()) || GetBotAI(ai->GetGroupMaster())->IsRealPlayer()))
                return true;

            if (ai->HasPlayerNearby())
                return true;

            return sRandomPlayerbotMgr.ProcessBot(bot);
        }

        virtual bool isUseful() override
        {
            return AI_VALUE(bool, "random bot update");
        }
    };

}
