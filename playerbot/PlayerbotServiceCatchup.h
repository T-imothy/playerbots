#ifndef LIVING_WOW_SERVICE_CATCHUP_H
#define LIVING_WOW_SERVICE_CATCHUP_H

// A close service may still require an unexpectedly long detour. Give that
// ordinary approach a short opportunity, then allow the same catch-up as a
// distant or cross-map service. The last few yards always remain local.
inline bool LivingWowServiceCatchupNeeded(bool sameMap, float distance,
    long elapsedSeconds, unsigned triggerSeconds, unsigned maximumSeconds)
{
    return !sameMap || distance > 7.0f * triggerSeconds ||
        (elapsedSeconds >= long(maximumSeconds) && distance > 35.0f);
}

#endif
