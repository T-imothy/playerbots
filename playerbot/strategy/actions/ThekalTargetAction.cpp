#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetThekalTarget()
{
    if (bot->GetMapId() != 309 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    Unit* trio[3] = {};
    bool engaged = false;
    // Include native fake-death actors when identifying the trio. This existing
    // cached GUID value bypasses attackability; actual targets are checked below.
    for (const auto& guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit) ||
            unit->HasCharmer() || !unit->GetMaxHealth() || bot->GetDistance(unit) > 100) continue;
        int index = unit->GetEntry() == 14509 ? 0 : unit->GetEntry() == 11347 ? 1 : unit->GetEntry() == 11348 ? 2 : -1;
        if (index < 0) continue;
        if (trio[index] && trio[index] != unit) return nullptr;
        trio[index] = unit;
        Unit* victim = unit->GetVictim();
        if (unit->IsInCombat() && victim && victim->IsPlayer() && victim->IsAlive() && victim->IsInWorld() &&
            bot->IsInMap(victim) && !victim->HasCharmer() && !static_cast<Player*>(victim)->IsBeingTeleported() &&
            static_cast<Player*>(victim)->GetGroup() == bot->GetGroup()) engaged = true;
    }
    if (!engaged || !trio[0] || !trio[1] || !trio[2] || trio[0]->HasAura(24169)) return nullptr;
    std::vector<Unit*> targets;
    for (Unit* unit : trio)
        if (unit->IsInCombat() && PossibleTargetsValue::IsValid(unit, bot, false) &&
            PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, false) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) && !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot))
            targets.push_back(unit);
    if (targets.empty()) return nullptr;
    Unit* highest = *std::max_element(targets.begin(), targets.end(), [](Unit* a, Unit* b) {
        if (a->GetHealthPercent() != b->GetHealthPercent()) return a->GetHealthPercent() < b->GetHealthPercent();
        return a->GetObjectGuid() > b->GetObjectGuid();
    });
    if (highest->GetHealthPercent() <= 10)
    {
        // Once balanced, finish the healer, then Zath, then Thekal. Native
        // fake-death/ten-second resurrection and tiger transitions are untouched.
        for (unsigned index : {1u, 2u, 0u})
            if (std::find(targets.begin(), targets.end(), trio[index]) != targets.end()) return trio[index];
    }
    Unit* current = AI_VALUE(Unit*, "current target");
    if (std::find(targets.begin(), targets.end(), current) != targets.end() &&
        current->GetHealthPercent() + 5 >= highest->GetHealthPercent()) return current;
    return highest;
}
