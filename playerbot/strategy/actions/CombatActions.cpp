
#include "playerbot/playerbot.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/strategy/values/LastMovementValue.h"
#include "CombatActions.h"

using namespace ai;

bool SwitchToMeleeAction::isUseful()
{
    return ai->HasStrategy("ranged", BotState::BOT_STATE_COMBAT);
}

bool SwitchToMeleeAction::Execute(Event &event)
{
    if (Unit* target = ai->GetUnit(AI_VALUE(ObjectGuid, "current target")))
    {
        if (!bot->HasUnitState(UNIT_STAT_MELEE_ATTACKING))
        {
            bot->AddUnitState(UNIT_STAT_MELEE_ATTACKING);
            bot->SendMeleeAttackStart(target);
        }
        return ChangeCombatStrategyAction::Execute(event);
    }
    return false;
}

bool SwitchToRangedAction::isUseful()
{

    return ai->HasStrategy("close", BotState::BOT_STATE_COMBAT);
}

bool SwitchToRangedAction::Execute(Event &event)
{
    if (Unit* target = ai->GetUnit(AI_VALUE(ObjectGuid, "current target")))
    {
        if (bot->HasUnitState(UNIT_STAT_MELEE_ATTACKING))
        {
            bot->ClearUnitState(UNIT_STAT_MELEE_ATTACKING);
            bot->InterruptSpell(CURRENT_MELEE_SPELL);
            bot->SendMeleeAttackStop(target);
        }
        return ChangeCombatStrategyAction::Execute(event);
    }
    return false;
}
