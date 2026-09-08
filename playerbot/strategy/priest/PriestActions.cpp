
#include "playerbot/playerbot.h"
#include "PriestActions.h"
#include "playerbot/strategy/values/ThreatValues.h"

using namespace ai;

bool CastFadeAction::isUseful()
{
    // A zero-threat tank can make the relative threat value read 100 at the
    // start of a pull. Fade is only useful if this priest has actual threat.
    return bot->GetGroup() && bot->IsInCombat() && CastBuffSpellAction::isUseful() &&
        ThreatValue::GetThreat(bot, AI_VALUE(Unit*, "current target")) > 0.0f;
}
