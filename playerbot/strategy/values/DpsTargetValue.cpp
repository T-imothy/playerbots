
#include "playerbot/playerbot.h"
#include "DpsTargetValue.h"
#include "LeastHpTargetValue.h"
#include "PossibleAttackTargetsValue.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"

using namespace ai;


ObjectGuid DpsTargetValue::Calculate()
{
    Unit* rti = ai->GetUnit(RtiTargetValue::Calculate());
    if (rti && PossibleAttackTargetsValue::IsPossibleTarget(rti, bot, sPlayerbotAIConfig.sightDistance, true) &&
        !MeleeCcCheck(ai).Protected(rti)) return rti->GetObjectGuid();

    FindLeastHpTargetStrategy strategy(ai);
    Unit* target = TargetValue::FindTarget(&strategy);
    return target ? target->GetObjectGuid() : ObjectGuid();
}

class FindMaxHpTargetStrategy : public FindTargetStrategy
{
public:
    FindMaxHpTargetStrategy(PlayerbotAI* ai) : FindTargetStrategy(ai)
    {
        maxHealth = 0;
    }

public:
    virtual void CheckAttacker(Unit* attacker, ThreatManager* threatManager) override
    {
        if (!PossibleAttackTargetsValue::IsPossibleTarget(attacker, ai->GetBot(), sPlayerbotAIConfig.sightDistance, true) ||
            MeleeCcCheck(ai).Protected(attacker)) return;
        Group* group = ai->GetBot()->GetGroup();
        if (group)
        {
            uint64 guid = group->GetTargetIcon(4);
            if (guid && attacker->GetObjectGuid() == ObjectGuid(guid))
                return;
        }
        if (!result || result->GetHealth() < attacker->GetHealth())
            result = attacker;
    }

protected:
    float maxHealth;
};

ObjectGuid DpsAoeTargetValue::Calculate()
{
    Unit* rti = ai->GetUnit(RtiTargetValue::Calculate());
    if (rti && PossibleAttackTargetsValue::IsPossibleTarget(rti, bot, sPlayerbotAIConfig.sightDistance, true) &&
        !MeleeCcCheck(ai).Protected(rti)) return rti->GetObjectGuid();

    FindMaxHpTargetStrategy strategy(ai);
    Unit* target = TargetValue::FindTarget(&strategy);
    return target ? target->GetObjectGuid() : ObjectGuid();
}
