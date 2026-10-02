#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetOperaDuoTarget()
{
#ifndef MANGOSBOT_ZERO
    if (bot->GetMapId() != 532 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    Unit* julianne = nullptr;
    Unit* romulo = nullptr;
    bool engaged = false;
    for (const auto& guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit) ||
            unit->HasCharmer() || !unit->GetMaxHealth()) continue;
        Unit** actor = unit->GetEntry() == 17534 ? &julianne : unit->GetEntry() == 17533 ? &romulo : nullptr;
        if (!actor) continue;
        if (*actor && *actor != unit) return nullptr;
        *actor = unit;
        Unit* victim = unit->GetVictim();
        if (unit->IsInCombat() && victim && victim->IsInWorld() && victim->IsAlive() && victim->IsPlayer() &&
            bot->IsInMap(victim) && !victim->HasCharmer() && !static_cast<Player*>(victim)->IsBeingTeleported() &&
            static_cast<Player*>(victim)->GetGroup() == bot->GetGroup()) engaged = true;
    }
    // Julianne summons this exact Romulo. Include fake-dead actors when
    // identifying the pair; normal native attackability excludes them below.
    if (!engaged || !julianne || !romulo || romulo->GetSpawnerGuid() != julianne->GetObjectGuid() ||
        julianne->GetDistance(romulo) > 100 || julianne->GetVictim() == bot || romulo->GetVictim() == bot) return nullptr;
    auto valid = [this](Unit* unit) {
        return unit->IsInCombat() && PossibleTargetsValue::IsValid(unit, bot, false) &&
            PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, false) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot);
    };
    const bool julianneValid = valid(julianne), romuloValid = valid(romulo);
    if (!julianneValid) return romuloValid ? romulo : nullptr;
    if (!romuloValid) return julianne;
    // Both active means the final phase. Balance before beginning the native
    // ten-second resurrection deadline, then finish the healer first. This
    // also recovers naturally after a missed deadline and a native full heal.
    Unit* highest = julianne->GetHealthPercent() >= romulo->GetHealthPercent() ? julianne : romulo;
    if (highest->GetHealthPercent() <= 10) return julianne;
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    if ((current == julianne || current == romulo) && current->GetHealthPercent() + 5 >= highest->GetHealthPercent())
        return current;
    return highest;
#else
    return nullptr;
#endif
}
