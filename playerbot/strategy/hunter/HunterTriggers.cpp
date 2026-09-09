
#include "playerbot/playerbot.h"
#include "HunterTriggers.h"
#include "HunterActions.h"

using namespace ai;

bool HunterNoStingsActiveTrigger::IsActive()
{
	Unit* target = AI_VALUE(Unit*, "current target");
    return MeleeCombatTarget(ai, target) &&
        !ai->HasMyAura("serpent sting", target) &&
        !ai->HasMyAura("scorpid sting", target) &&
        !ai->HasMyAura("viper sting", target);
}

bool HuntersPetDeadTrigger::IsActive()
{
    return AI_VALUE(bool, "pet dead") && !AI_VALUE2(bool, "mounted", "self target");
}

bool HuntersPetLowHealthTrigger::IsActive()
{
    Unit* pet = AI_VALUE(Unit*, "pet target");
    return pet && AI_VALUE2(uint8, "health", "pet target") < 40 &&
        !AI_VALUE2(bool, "dead", "pet target") && !AI_VALUE2(bool, "mounted", "self target");
}

bool HunterPetNotHappy::IsActive()
{
    return !AI_VALUE(bool, "pet happy") && !AI_VALUE2(bool, "mounted", "self target");
}

bool ViperStingOnAttackerTrigger::IsActive()
{
    Unit* target = GetTarget();
    if (target)
    {
        const bool noStings = !ai->HasMyAura("serpent sting", target) &&
                              !ai->HasMyAura("scorpid sting", target) &&
                              !ai->HasMyAura("viper sting", target);
        if (noStings)
        {
            if (HunterWantsViperSting(ai, target))
            {
                return DebuffOnAttackerTrigger::IsActive();
            }
        }
    }

    return false;
}

bool SerpentStingOnAttackerTrigger::IsActive()
{
    Unit* target = GetTarget();
    if (target)
    {
        const bool noStings = !ai->HasMyAura("serpent sting", target) &&
                              !ai->HasMyAura("scorpid sting", target) &&
                              !ai->HasMyAura("viper sting", target);
        if (noStings)
        {
            if (!HunterWantsViperSting(ai, target))
            {
                return DebuffOnAttackerTrigger::IsActive();
            }
        }
    }

    return false;
}
