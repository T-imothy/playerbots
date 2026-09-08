
#include "playerbot/playerbot.h"
#include "DruidTriggers.h"
#include "DruidActions.h"

using namespace ai;

bool EntanglingRootsKiteTrigger::IsActive() 
{ 
	if (!DebuffTrigger::IsActive())
		return false;

    if (AI_VALUE(uint8, "attackers count") > 3)
        return false;

    Unit* target = GetTarget();
    if (!target)
        return false;
    // PvE retains its existing selection. PvP roots should help against melee
    // pursuit, not depend on the opposing class having a mana bar.
    if (target->IsPlayer())
    {
        if (target->GetVictim() != bot || target->IsImmobilizedState() ||
            !bot->IsWithinDistInMap(target, 20.0f))
            return false;
    }
    else if (!target->HasMana())
        return false;

    std::list<ObjectGuid> attackers = context->GetValue<std::list<ObjectGuid>>("attackers")->Get();
    for (std::list<ObjectGuid>::iterator i = attackers.begin(); i != attackers.end(); i++)
    {
        Unit* unit = ai->GetUnit(*i);
        if (!unit || !sServerFacade.IsAlive(unit))
            continue;

        if (ai->HasMyAura("entangling roots", unit))
            return false;
    }

    return !HasMaxDebuffs();
}

Value<Unit*>* LifebloomTankTrigger::GetTargetValue()
{
    return context->GetValue<Unit*>("party tank without lifebloom", "lifebloom");
}