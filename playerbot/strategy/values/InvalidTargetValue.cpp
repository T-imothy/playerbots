
#include "playerbot/playerbot.h"
#include "InvalidTargetValue.h"
#include "PossibleTargetsValue.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "playerbot/strategy/actions/DungeonActions.h"
#include "PossibleAttackTargetsValue.h"
#include "EnemyPlayerValue.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

bool InvalidTargetValue::Calculate()
{
    Unit* target = AI_VALUE(Unit*, qualifier);
    if (!PossibleTargetsValue::IsValid(target, bot, true) || MeleeCcCheck(ai).Protected(target))
    {
        return true;
    }

    Unit* duelTarget = AI_VALUE(Unit*, "duel target");
    if (duelTarget && duelTarget == target)
    {
        return false;
    }

    if (qualifier == "current target")
    {
        if (target->GetObjectGuid() != bot->GetSelectionGuid())
        {
            return true;
        }
    }

    // Healing wards have no hostile victim of their own. Keep the exact active
    // dungeon objective instead of rejecting it as a non-threatening creature.
    if (qualifier == "current target" && bot->GetMapId() == 209 && target->GetEntry() == 8179 &&
        ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT))
    {
        DungeonAddTargetAction priority(ai);
        if (priority.GetTarget() == target) return false;
    }

    const bool validTarget = PossibleAttackTargetsValue::IsValid(target, bot);
    if (!validTarget)
    {
        std::list<ObjectGuid> attackers = AI_VALUE(std::list<ObjectGuid>, "possible attack targets");
        if (std::find(attackers.begin(), attackers.end(), target->GetObjectGuid()) != attackers.end() &&
            PossibleAttackTargetsValue::IsPossibleTarget(target, bot, sPlayerbotAIConfig.sightDistance, true))
        {
            return false;
        }
    }

    return !validTarget;
}
