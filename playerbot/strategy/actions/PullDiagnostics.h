#pragma once

namespace ai
{
    enum class PullFailure
    {
        None, NoTarget, InvalidTarget, StrategyDisabled, NoAction, NoRangedWeapon,
        NoAmmo, OutOfRange, NoLineOfSight, NotKnown, NotReady, InvalidState, Unavailable
    };
    PullFailure GetPullReadiness(PlayerbotAI* ai, Unit* target);
    const char* PullFailureReason(PullFailure failure);
}
