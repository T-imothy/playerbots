
#include "playerbot/playerbot.h"
#include "StuckValues.h"

using namespace ai;

uint32 TimeSinceLastChangeValue::Calculate()
{
    UntypedValue* val = context->GetUntypedValue(qualifier);

    if (!val)
        return 0;

    return val->LastChangeDelay();
}

uint32 DistanceMovedSinceValue::Calculate()
{
    uint32 minTimePassed = stoi(getQualifier());

    LogCalculatedValue<WorldPosition>* posVal = dynamic_cast<LogCalculatedValue<WorldPosition>*>(context->GetUntypedValue("current position"));
    if (!posVal)
        return 0;

    posVal->Get();
    const auto history = posVal->ValueLog();
    const time_t cutoff = time(0) - minTimePassed;
    bool hasEnoughData = false;
    float maxSqDistance = 0.0f;

    // Walk back only as far as the last known position at the window boundary.
    // Older movement must not hide a bot that has been stuck since then.
    for (auto i = history.rbegin(); i != history.rend(); ++i)
    {
        float distance = i->first.sqDistance(bot);
        if (distance > maxSqDistance)
            maxSqDistance = distance;

        if (i->second <= cutoff)
        {
            hasEnoughData = true;
            break;
        }
    }

    if (!hasEnoughData)
        return 0;

    return static_cast<uint32>(sqrt(maxSqDistance));
}
