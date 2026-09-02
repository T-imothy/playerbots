
#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotAIConfig.h"

using namespace ai;

PlayerbotAIBase::PlayerbotAIBase() : aiInternalUpdateDelay(0)
{
}

void PlayerbotAIBase::UpdateAIInternal(uint32 elapsed, bool minimal)
{
}

void PlayerbotAIBase::UpdateAI(uint32 elapsed)
{
    totalPmo.reset();
    totalPmo = sPerformanceMonitor.start(PERF_MON_TOTAL, "PlayerbotAIBase::FullTick");
    
    if (aiInternalUpdateDelay > elapsed)
        aiInternalUpdateDelay -= elapsed;
    else
        aiInternalUpdateDelay = 0;

    if (!CanUpdateAIInternal())
        return;

    UpdateAIInternal(elapsed);
    YieldAIInternalThread();
}

bool PlayerbotAIBase::AdvanceMinimalUpdateDelay(uint32 elapsed)
{
    if (aiInternalUpdateDelay > elapsed)
    {
        aiInternalUpdateDelay -= elapsed;
        return false;
    }

    aiInternalUpdateDelay = 0;
    return true;
}

void PlayerbotAIBase::ScheduleNextMinimalUpdate(uint32 salt, uint32 jitterMs)
{
    uint32 const baseDelay = std::max<uint32>(sPlayerbotAIConfig.passiveDelay, sPlayerbotAIConfig.reactDelay * 10);
    uint32 const jitter = jitterMs ? ((salt * 2654435761u) % (jitterMs + 1)) : 0;
    aiInternalUpdateDelay = std::max<uint32>(aiInternalUpdateDelay, baseDelay + jitter);
}

void PlayerbotAIBase::SetAIInternalUpdateDelay(const uint32 delay)
{
    if (aiInternalUpdateDelay < delay)
        sLog.outDebug("Setting lesser ai internal update delay %d -> %d", aiInternalUpdateDelay, delay);

    aiInternalUpdateDelay = delay;

    if (aiInternalUpdateDelay > sPlayerbotAIConfig.globalCoolDown)
        sLog.outDebug( "Set ai internal update delay: %d", aiInternalUpdateDelay);
}

void PlayerbotAIBase::IncreaseAIInternalUpdateDelay(uint32 delay)
{
    aiInternalUpdateDelay += delay;

    if (aiInternalUpdateDelay > sPlayerbotAIConfig.globalCoolDown)
        sLog.outDebug( "Increase ai internal update delay: %d", aiInternalUpdateDelay);
}

void PlayerbotAIBase::YieldAIInternalThread(bool minimal)
{
    if (aiInternalUpdateDelay < sPlayerbotAIConfig.reactDelay)
        aiInternalUpdateDelay = minimal ? std::max<uint32>(sPlayerbotAIConfig.passiveDelay, sPlayerbotAIConfig.reactDelay * 10) : sPlayerbotAIConfig.reactDelay;
}

bool PlayerbotAIBase::IsActive() const
{
    return (int)aiInternalUpdateDelay < (int)sPlayerbotAIConfig.maxWaitForMove;
}
