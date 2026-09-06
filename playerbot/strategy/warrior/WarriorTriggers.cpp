
#include "playerbot/playerbot.h"
#include "WarriorTriggers.h"
#include "WarriorActions.h"

using namespace ai;

bool SwordAndBoardTrigger::IsActive()
{
#ifdef MANGOSBOT_TWO
    return bot->HasAura(50227); // Proc, not the identically named passive talent.
#else
    return false;
#endif
}

bool SuddenDeathTrigger::IsActive()
{
#ifdef MANGOSBOT_TWO
    return bot->HasAura(52437);
#else
    return false;
#endif
}

bool TasteForBloodTrigger::IsActive()
{
#ifdef MANGOSBOT_TWO
    return bot->HasAura(60503);
#else
    return false;
#endif
}

bool BloodrageBuffTrigger::IsActive()
{
    return AI_VALUE2(uint8, "health", "self target") >= sPlayerbotAIConfig.mediumHealth &&
        AI_VALUE2(uint8, "rage", "self target") < 20;
}

bool SunderArmorDebuffTrigger::IsActive()
{
    Unit* target = GetTarget();
    if (!target)
        return false;

    if (ai->IsTank(bot) && !target->IsPlayer())
        return true;

    return !ai->HasAura("sunder armor", target, true) && !HasMaxDebuffs();
}

bool CommandingShoutTrigger::IsActive()
{
    uint32 comShout = AI_VALUE2(uint32, "spell id", "commanding shout");
    uint32 batShout = AI_VALUE2(uint32, "spell id", "battle shout");
    if (!(comShout || batShout))
        return false;

    if (bot->HasSpell(comShout))
        return !ai->HasAura("commanding shout", bot);

    if (bot->HasSpell(batShout))
        return !ai->HasAura("battle shout", bot);

    return false;
}
