
#include "playerbot/playerbot.h"
#include "playerbot/RaidLabTrace.h"
#include "InvalidTargetValue.h"
#include "PossibleTargetsValue.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "playerbot/strategy/actions/DungeonActions.h"
#include "playerbot/strategy/actions/BlackwingLairDungeonActions.h"
#include "playerbot/strategy/actions/ClassicRaidActions.h"
#include "PossibleAttackTargetsValue.h"
#include "EnemyPlayerValue.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

bool InvalidTargetValue::Calculate()
{
    Unit* target = ai->GetUnit(AI_VALUE(ObjectGuid, qualifier));
    if (!PossibleTargetsValue::IsValid(target, bot, true))
    {
        return RaidLabMovementResult(bot, "invalid_target:basic", target ? target->GetEntry() : 0, true);
    }
    if (MeleeCcCheck(ai).Protected(target))
        return RaidLabMovementResult(bot, "invalid_target:cc", target->GetEntry(), true);

    Unit* duelTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "duel target"));
    if (duelTarget && duelTarget == target)
    {
        return false;
    }

    if (qualifier == "current target")
    {
        if (target->GetObjectGuid() != bot->GetSelectionGuid())
        {
            return RaidLabMovementResult(bot, "invalid_target:selection", target->GetEntry(), true);
        }
    }

    // Incoming Kel'Thuzad waves likewise need interception before acquiring a victim.
    if (qualifier == "current target" && bot->GetMapId() == 533)
    {
        Unit* incoming=KelthuzadOpeningTarget(ai);
#ifdef MANTECH_RAID_LAB
        if (target->GetEntry()==16427 || target->GetEntry()==16428 || target->GetEntry()==16429)
            RaidLab::Count(bot,"kt_invalid_election",target->GetObjectGuid().GetCounter(),
                incoming==target?1:0,incoming?incoming->GetObjectGuid().GetRawValue():0);
#endif
        if (incoming == target) return false;
    }

    // Healing wards have no hostile victim of their own. Keep the exact active
    // dungeon objective instead of rejecting it as a non-threatening creature.
    const bool nativeWard=(bot->GetMapId() == 209 && target->GetEntry() == 8179) ||
         (bot->GetMapId() == 70 && target->GetEntry() == 3560)
#ifdef MANGOSBOT_ZERO
         // Jin'do's totems and the engaged Voodoo Slave's ward likewise
         // have no hostile victim. Re-elect the exact owner-validated
         // objective below; do not accept arbitrary idle room creatures.
         || (bot->GetMapId() == 309 && (target->GetEntry() == 14987 ||
             target->GetEntry() == 15112 || target->GetEntry() == 10218))
#endif
         ;
    if (qualifier == "current target" && nativeWard &&
        ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT))
    {
        DungeonAddTargetAction priority(ai);
        if (priority.GetTarget() == target) return false;
    }

    // A room assignment can begin beyond ordinary sight range. Keep only the
    // freshly elected, engaged add while native movement closes that distance.
    // The world, hostility, CC and selection checks above still apply.
    if (qualifier == "current target")
    {
        bool defense = false;
        Unit* assigned = RazorgoreDefenseTarget(ai, defense);
        if (defense && assigned == target) return false;
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

    return RaidLabMovementResult(bot, "invalid_target:attackable", target->GetEntry(), !validTarget);
}
