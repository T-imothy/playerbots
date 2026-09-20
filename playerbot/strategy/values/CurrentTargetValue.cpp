
#include "playerbot/playerbot.h"
#include "CurrentTargetValue.h"

#include "playerbot/ServerFacade.h"
using namespace ai;

ObjectGuid CurrentTargetValue::Get()
{
    if (selection.IsEmpty())
        return ObjectGuid();

    Unit* unit = sObjectAccessor.GetUnit(*bot, selection);
    if (unit && !bot->IsWithinDistInMap(unit, sPlayerbotAIConfig.sightDistance))
        return ObjectGuid();

    // Distance was the only test here, so a target kept once was kept for good -
    // a player who stealthed after being targeted stayed targeted. This asks the
    // same question the target list asks before picking anyone: can the bot still
    // see them. It covers stealth, invisibility and visibility state and does not
    // involve line of sight, so a target behind a pillar is not lost.
    if (unit && unit != bot &&
        !unit->IsVisibleForOrDetect(bot, bot->GetCamera().GetBody(), true))
        return ObjectGuid();

    return unit ? unit->GetObjectGuid() : ObjectGuid();
}

void CurrentTargetValue::Set(ObjectGuid unitGuid)
{
    selection = unitGuid;
}
