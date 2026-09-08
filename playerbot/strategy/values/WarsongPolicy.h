#pragma once

namespace ai
{
    enum class WarsongFlagState { Base, Carried, Dropped };
    enum class WarsongGoal { None, Fetch, Recover, Return, Intercept, Escort, Capture, Hold };

    // Decide from native flag state; job assignment is independent of route choice.
    inline WarsongGoal SelectWarsongGoal(WarsongFlagState own, WarsongFlagState enemy,
        bool carrying, bool support, bool alone)
    {
        if (carrying)
            return own == WarsongFlagState::Base ? WarsongGoal::Capture : WarsongGoal::Hold;
        if (own == WarsongFlagState::Dropped && (support || alone || enemy == WarsongFlagState::Carried))
            return WarsongGoal::Return;
        if (enemy == WarsongFlagState::Dropped)
            return WarsongGoal::Recover;
        if (own == WarsongFlagState::Carried && (!support || alone))
            return WarsongGoal::Intercept;
        if (enemy == WarsongFlagState::Carried)
            return WarsongGoal::Escort;
        return WarsongGoal::Fetch;
    }
}
