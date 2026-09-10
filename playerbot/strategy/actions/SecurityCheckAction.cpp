
#include "playerbot/playerbot.h"
#include "playerbot/RandomPlayerbotMgr.h"
#include "SecurityCheckAction.h"

using namespace ai;

bool SecurityCheckAction::isUseful()
{
    // Living WoW treats mixed-party bots as ordinary party members. The
    // upstream guild-only loot policy must not override a human leader's
    // selected loot method or force bots into passive/stay behavior.
    return false;
}

bool SecurityCheckAction::Execute(Event& event)
{
    return false;
}
