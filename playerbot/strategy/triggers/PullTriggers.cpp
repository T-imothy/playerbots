
#include "playerbot/playerbot.h"
#include "playerbot/strategy/Action.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "PullTriggers.h"
#include "playerbot/strategy/values/PositionValue.h"

using namespace ai;

bool PullStartTrigger::IsActive()
{
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (!strategy || !strategy->HasTarget()) return false;
    Unit* target = strategy->GetTarget();
    if (strategy->HasPullActionIssued() && !bot->IsNonMeleeSpellCasted(true) &&
        !target->IsInCombat() && !bot->IsInCombat() &&
        time(nullptr) - strategy->GetPullActionTime() >= 3 &&
        time(nullptr) - strategy->GetPullStartTime() < strategy->GetMaxPullTime())
        strategy->RetryPullAction(); // A miss/interruption never restarts the command deadline.
    return strategy->IsPullPendingToStart();
}

bool PullActionTrigger::IsActive()
{
    const PullStrategy* strategy = PullStrategy::Get(ai);
    if (!strategy || !strategy->HasPullStarted() || strategy->IsPullPendingToStart() ||
        strategy->HasPullActionIssued() || bot->IsNonMeleeSpellCasted(true)) return false;
    Unit* target = strategy->GetTarget();
    // Moving, a failed cast, or an engine reinitialization can consume the
    // queued shot. Keep scheduling it without repeating preparation or
    // resetting the original command deadline.
    return target && target->IsAlive() && target->IsInWorld() && bot->IsInMap(target) &&
        time(nullptr) - strategy->GetPullStartTime() < strategy->GetMaxPullTime();
}

bool PullEndTrigger::IsActive()
{
    const PullStrategy* strategy = PullStrategy::Get(ai);
    if (!strategy || !strategy->HasPullStarted()) return false;
    Unit* target = strategy->GetTarget();
    if (!target || !target->IsAlive() || !target->IsInWorld() || !bot->IsInMap(target)) return true;
    if (bot->IsNonMeleeSpellCasted(true)) return false;
    if (time(nullptr) - strategy->GetPullStartTime() >= strategy->GetMaxPullTime()) return true;
    if (!target->IsInCombat()) return false;

    // A party member taking the pull must not wait ten seconds for tank combat.
    Unit* victim = target->GetVictim();
    if (victim && victim != bot && bot->IsInGroup(victim)) return true;

    const float meleeRange = ATTACK_DISTANCE + BASE_MELEERANGE_OFFSET + 1;
    if (target->GetDistance(bot) <= meleeRange) return true;
    if (!ai->HasStrategy("pull back", BotState::BOT_STATE_COMBAT)) return true;

    PositionEntry pullPosition = AI_VALUE(PositionMap&, "position")["pull"];
    if (!pullPosition.isSet()) return true;
    return bot->GetDistance(pullPosition.x, pullPosition.y, pullPosition.z) <= ai->GetRange("follow");
}
