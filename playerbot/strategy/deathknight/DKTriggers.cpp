
#include "playerbot/playerbot.h"
#include "DKTriggers.h"
#include "DKActions.h"

using namespace ai;

bool KillingMachineTrigger::IsActive()
{
#ifdef MANGOSBOT_TWO
    return bot->HasAura(51124); // The proc consumed by the native core.
#else
    return false;
#endif
}

bool DKPresenceTrigger::IsActive()
{
    Unit* target = GetTarget();
    return !ai->HasAura("blood presence", target) &&
        !ai->HasAura("unholy presence", target) &&
        !ai->HasAura("frost presence", target);
}
