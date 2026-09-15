#pragma once
#include "playerbot/BotReliabilityPolicy.h"
#include "playerbot/BotIncidentHistory.h"
#include "playerbot/strategy/Value.h"

namespace ai
{
struct BotReliabilityState
{
    PursuitProgress pursuit;
    UnreachableTargets unreachable;
    BotIncidentState incidents;
};

class BotReliabilityValue : public ManualSetValue<BotReliabilityState&>
{
public:
    BotReliabilityValue(PlayerbotAI* ai) : ManualSetValue<BotReliabilityState&>(ai, state, "bot reliability") {}
    ~BotReliabilityValue() override { BotIncidentHistory::Close(state.incidents); }
private:
    BotReliabilityState state;
};

bool ObserveUnreachableTarget(PlayerbotAI* ai, Unit* target);
bool IsUnreachableTarget(PlayerbotAI* ai, Unit* target);
}
