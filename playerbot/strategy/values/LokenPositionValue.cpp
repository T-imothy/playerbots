#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"

using namespace ai;

bool ai::IsLokenClosePhase(Player* bot, Unit* boss)
{
#ifdef MANGOSBOT_TWO
    return bot && boss && bot->GetMapId() == 602 && boss->GetEntry() == 28923 &&
        bot->IsInWorld() && bot->IsAlive() && bot->IsInCombat() && !bot->IsBeingTeleported() && !bot->HasCharmer() &&
        boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && !boss->HasCharmer() && bot->IsInMap(boss) &&
        boss->GetVictim() != bot && !CurrentBossEscapeSpell(bot, boss) &&
        (boss->GetSpellAuraHolder(52961, boss->GetObjectGuid()) || boss->GetSpellAuraHolder(59836, boss->GetObjectGuid()));
#else
    return false;
#endif
}

bool ai::PlanLokenClosePosition(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!IsLokenClosePhase(bot, boss)) return false;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    const encounter::Point center{boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()};
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.spell = 59414;
    unsigned checked = 0;
    if (encounter::Distance2d(here, center) <= 5)
    {
        plan.destination = here;
        ++checked;
        if (ValidateEncounterDestination(ai, plan)) return true;
    }
    // Pulsing Shockwave scales with distance. Return after Nova, without
    // moving the active tank or requiring a particular position in the room.
    const float angle = std::atan2(here.y - center.y, here.x - center.x);
    for (unsigned step = 0; checked < 8; ++step, ++checked)
    {
        const float candidate = angle + step * 0.7853981633974483f;
        plan.destination = {center.x + 3 * std::cos(candidate), center.y + 3 * std::sin(candidate), center.z};
        if (ValidateEncounterDestination(ai, plan)) return true;
    }
    plan.active = false;
    return false;
}
