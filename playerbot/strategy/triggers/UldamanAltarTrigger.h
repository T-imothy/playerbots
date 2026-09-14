#pragma once
#include "playerbot/strategy/Trigger.h"
#include "playerbot/strategy/actions/UldamanAltarAction.h"

namespace ai
{
    class AssistUldamanAltarTrigger : public Trigger
    {
    public:
        AssistUldamanAltarTrigger(PlayerbotAI* ai) : Trigger(ai, "assist uldaman altar", 1) {}
        bool IsActive() override { AssistUldamanAltarAction action(ai); return action.isUseful(); }
    };
}
