#pragma once

class Player;
class PlayerbotMgr;
class ChatHandler;
class PerformanceMonitorOperation;

#include <memory>

class PlayerbotAIBase
{
public:
    PlayerbotAIBase();

public:
    bool IsActive() const;
    virtual void UpdateAI(uint32 elapsed);
    // Advance the inexpensive AI wake-up timer on the owning map thread.
    // Returning false lets the map avoid allocating and dispatching a worker
    // for an idle bot whose passive AI is not due yet.
    bool AdvanceMinimalUpdateDelay(uint32 elapsed);
    void ScheduleNextMinimalUpdate(uint32 salt, uint32 jitterMs);
    
    uint32 GetAIInternalUpdateDelay() const { return aiInternalUpdateDelay; }

protected:
    virtual void UpdateAIInternal(uint32 elapsed, bool minimal = false);
    bool CanUpdateAIInternal() const { return aiInternalUpdateDelay < 100U; }
    void SetAIInternalUpdateDelay(const uint32 delay);
    void ResetAIInternalUpdateDelay() { aiInternalUpdateDelay = 0U; }
    void IncreaseAIInternalUpdateDelay(uint32 delay);
    void YieldAIInternalThread(bool minimal = false);
    
protected:
	uint32 aiInternalUpdateDelay;

    std::unique_ptr<PerformanceMonitorOperation> totalPmo;
};
