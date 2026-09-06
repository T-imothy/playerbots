
#include "playerbot/playerbot.h"
#include "ThreatValues.h"

#include "playerbot/ServerFacade.h"
#include "Combat/ThreatManager.h"

#include <algorithm>
#include <cmath>

using namespace ai;

namespace
{
    Unit* ResolveThreatTarget(Player* player, Unit* target)
    {
        if (!player || !player->IsInWorld() || player->IsBeingTeleported() ||
            !target || !target->IsInWorld() || !player->IsInMap(target))
            return nullptr;

        if (target->GetTypeId() == TYPEID_PLAYER && static_cast<Player*>(target)->IsBeingTeleported())
            return nullptr;

        // A friendly selection is a proxy for its enemy, not a guarantee that
        // it still has one. Recheck native map/instance/phase after resolving.
        if (target->IsFriend(player))
            target = target->GetTarget();

        if (!target || !target->IsInWorld() || !target->IsAlive() || !player->IsInMap(target) ||
            target->GetObjectGuid().IsPlayer() || target->IsFriend(player))
            return nullptr;

        return target;
    }
}

float MyThreatValue::Calculate()
{
    Unit* target = ResolveThreatTarget(bot, AI_VALUE(Unit*, qualifier));
    const ObjectGuid targetGuid = target ? target->GetObjectGuid() : ObjectGuid();

    // Follow the actual enemy rather than the GUID of a friendly target proxy.
    if (targetGuid != lastTarget)
        LogCalculatedValue::Reset();

    lastTarget = targetGuid;
      
    return ThreatValue::GetThreat(bot, target);
}

float TankThreatValue::Calculate()
{
    Unit* target = AI_VALUE(Unit*, qualifier);

    return ThreatValue::GetTankThreat(ai, target);
}

uint8 ThreatValue::Calculate()
{
    if (qualifier == "aoe")
    {
        uint8 maxThreat = 0;
        std::list<ObjectGuid> attackers = context->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get();
        for (std::list<ObjectGuid>::iterator i = attackers.begin(); i != attackers.end(); i++)
        {
            Unit* unit = ai->GetUnit(*i);
            if (!unit || !sServerFacade.IsAlive(unit))
                continue;

            uint8 threat = Calculate(unit);
            if (!maxThreat || threat > maxThreat)
                maxThreat = threat;
        }

        return maxThreat;
    }

    return Calculate(AI_VALUE(Unit*, qualifier));
}

float ThreatValue::GetThreat(Player* player, Unit* target)
{
    target = ResolveThreatTarget(player, target);
    if (!target)
        return 0;

    float botThreat = sServerFacade.GetThreatManager(target).getThreat(player);

    return botThreat;
}

float ThreatValue::GetTankThreat(PlayerbotAI* ai, Unit* target)
{
    if (!ai)
        return 0;

    Player* bot = ai->GetBot();
    target = ResolveThreatTarget(bot, target);
    if (!target)
        return 0;

    Group* group = bot->GetGroup();
    if (!group)
        return 0;

    float maxThreat = -1.0f;

    for (GroupReference* gref = group->GetFirstMember(); gref; gref = gref->next())
    {
        Player* player = gref->getSource();
        if (!player || !player->IsInWorld() || !sServerFacade.IsAlive(player) || player->IsBeingTeleported() ||
            !bot->IsInMap(player) || player == bot)
            continue;

        if (ai->IsTank(player))
        {
            float threat = sServerFacade.GetThreatManager(target).getThreat(player);
            if (maxThreat < threat)
                maxThreat = threat;
        }
    }

    return maxThreat;
}

uint8 ThreatValue::Calculate(Unit* target)
{
    target = ResolveThreatTarget(bot, target);
    if (!target)
        return 0;

    Group* group = bot->GetGroup();
    if (!group)
        return 0;

    float botThreat, maxThreat;
    if (qualifier == "aoe")
    {
        botThreat = GetThreat(bot, target);
        maxThreat = GetTankThreat(ai, target);
    }
    else
    {
        botThreat = AI_VALUE2(float, "my threat", qualifier);
        maxThreat = AI_VALUE2(float, "tank threat", qualifier);
    }

    if (!std::isfinite(botThreat) || !std::isfinite(maxThreat) || maxThreat < 0)
        return 0;

    // calculate normal threat for fleeing targets
    bool fleeing = target->GetMotionMaster()->GetCurrentMovementGeneratorType() == FLEEING_MOTION_TYPE ||
        target->GetMotionMaster()->GetCurrentMovementGeneratorType() == TIMED_FLEEING_MOTION_TYPE;

    // return high threat if tank has no threat
    if (target->IsInCombat() && maxThreat == 0 && !fleeing)
        return 100;

    // return low threat if mob if fleeing
    if (fleeing || maxThreat == 0)
        return 0;

    // Preserve the existing byte-valued API without wrapping high threat back
    // below the high-threat threshold, or dividing by zero outside combat.
    return static_cast<uint8>(std::min(255.0, std::max(0.0, double(botThreat) * 100.0 / maxThreat)));
}
