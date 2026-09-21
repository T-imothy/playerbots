
#include "playerbot/playerbot.h"
#include "DpsTargetValue.h"
#include "LeastHpTargetValue.h"
#include "PossibleAttackTargetsValue.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "playerbot/strategy/actions/DungeonActions.h"

using namespace ai;


ObjectGuid DpsTargetValue::Calculate()
{
    Unit* healer = nullptr;
    std::set<ObjectGuid> engagedHealers;
    if (bot->IsInWorld() && !bot->IsBeingTeleported() && bot->GetMap()->IsDungeon() &&
        bot->GetMapId() != 230 && bot->GetGroup() && !ai->IsHeal(bot) && !ai->IsTank(bot))
    {
        const auto attackers = AI_VALUE(std::list<ObjectGuid>, "attackers");
        for (ObjectGuid guid : attackers)
        {
            Unit* unit = ai->GetUnit(guid);
            if (!unit || !unit->IsCreature() || !unit->IsInWorld() || !unit->IsAlive() ||
                !bot->IsInMap(unit) || !unit->IsInCombat() || unit->HasCharmer()) continue;

            bool heals = observedHealers.count(guid) != 0;
            for (CurrentSpellTypes slot : { CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL })
                if (Spell* spell = unit->GetCurrentSpell(slot))
                    if (PlayerbotAI::IsHealSpell(spell->m_spellInfo)) heals = true;
            if (!heals) continue;
            engagedHealers.insert(guid);

            if (!PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, true) ||
                PossibleAttackTargetsValue::HasBreakableCC(unit, bot) ||
                PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot) || MeleeCcCheck(ai).Protected(unit)) continue;
            if (!healer || unit->GetHealth() < healer->GetHealth() ||
                (unit->GetHealth() == healer->GetHealth() && guid < healer->GetObjectGuid())) healer = unit;
        }
    }
    observedHealers.swap(engagedHealers);

    // Encounter objectives (wards, rescue adds, BRD policy) retain priority.
    // Share their choice with DPS assist so it cannot immediately undo it.
    if (bot->IsInWorld() && !bot->IsBeingTeleported() && bot->GetMap()->IsDungeon())
    {
        DungeonAddTargetAction action(ai);
        if (Unit* target = action.GetTarget()) return target->GetObjectGuid();
    }
    Unit* rti = ai->GetUnit(RtiTargetValue::Calculate());
    if (rti && PossibleAttackTargetsValue::IsPossibleTarget(rti, bot, sPlayerbotAIConfig.sightDistance, true) &&
        !MeleeCcCheck(ai).Protected(rti)) return rti->GetObjectGuid();

    Unit* commanded = ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"));
    if (healer && !(commanded && commanded->IsInWorld() && commanded->IsAlive() &&
        bot->IsInMap(commanded) && !sServerFacade.IsFriendlyTo(bot, commanded) &&
        bot->IsWithinDistInMap(commanded, sPlayerbotAIConfig.sightDistance)))
        return healer->GetObjectGuid();

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
