
#include "playerbot/playerbot.h"
#include "TankTargetValue.h"
#include "PossibleAttackTargetsValue.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"

using namespace ai;

class FindTargetForTankStrategy : public FindNonCcTargetStrategy
{
public:
    FindTargetForTankStrategy(PlayerbotAI* ai) : FindNonCcTargetStrategy(ai)
    {
        minThreat = 0;
    }

public:
    bool HasRescueTarget() const { return rescueTarget; }

    virtual void CheckAttacker(Unit* creature, ThreatManager* threatManager) override
    {
        Player* bot = ai->GetBot();
        AiObjectContext* context = ai->GetAiObjectContext();

        if (!PossibleAttackTargetsValue::IsPossibleTarget(creature, bot, sPlayerbotAIConfig.sightDistance, true) ||
            MeleeCcCheck(ai).Protected(creature)) return;

        if (!PossibleAttackTargetsValue::IsValid(creature, bot))
        {
            std::list<ObjectGuid> attackers = AI_VALUE(std::list<ObjectGuid>, "possible attack targets");
            if (std::find(attackers.begin(), attackers.end(), creature->GetObjectGuid()) == attackers.end())
                return;
        }

        // Rescue a group member before building threat on another tank's enemy.
        // Tank rescue outranks a damage mark; DPS keep their marked target.
        Player* victim = dynamic_cast<Player*>(creature->GetVictim());
        const bool rescue = victim && victim != bot && victim->IsInWorld() && victim->IsAlive() &&
            bot->IsInMap(victim) && bot->GetGroup() && victim->GetGroup() == bot->GetGroup() &&
            !ai->IsTank(victim);
        float threat = threatManager->getThreat(bot);
        if (!result || (rescue && !rescueTarget) || (rescue == rescueTarget && (minThreat - threat) > 0.1f))
        {
            rescueTarget = rescue;
            minThreat = threat;
            result = creature;
        }
    }

protected:
    float minThreat;
    bool rescueTarget = false;
};


ObjectGuid TankTargetValue::Calculate()
{
    FindTargetForTankStrategy strategy(ai);
    Unit* target = FindTarget(&strategy);
    if (target && strategy.HasRescueTarget()) return target->GetObjectGuid();

    Unit* rti = ai->GetUnit(RtiTargetValue::Calculate());
    if (rti && PossibleAttackTargetsValue::IsPossibleTarget(rti, bot, sPlayerbotAIConfig.sightDistance, true) &&
        !MeleeCcCheck(ai).Protected(rti)) return rti->GetObjectGuid();

    return target ? target->GetObjectGuid() : ObjectGuid();
}
