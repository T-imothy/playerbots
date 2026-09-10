#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetRaidTotemTarget()
{
    uint32 entry = 0;
    if (bot->GetMapId() == 209) entry = 8179; // Greater Healing Ward (spell 11899).
#ifndef MANGOSBOT_ZERO
    else if (bot->GetMapId() == 548) entry = 22091;
    else if (bot->GetMapId() == 568) entry = 24224;
#endif
    else return nullptr;
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || !bot->GetGroup() ||
        bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    auto live = [this](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer();
    };
    Unit* selected = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible targets"))
    {
        Unit* totem = ai->GetUnit(guid);
        if (!live(totem) || totem->GetEntry() != entry ||
            !PossibleTargetsValue::IsValid(totem, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(totem, bot, sPlayerbotAIConfig.sightDistance, false)) continue;
        // Native Totem::GetSpawnerGuid resolves its owner. Karathress inherits
        // Spitfire after Tidalvess dies, so either real owner can identify it.
        Unit* owner = ai->GetUnit(totem->GetSpawnerGuid());
        if (!live(owner) || !owner->IsInCombat() || owner->GetDistance(totem) > 100 ||
            (entry == 8179 && owner->GetEntry() != 5650) ||
            (entry == 22091 && owner->GetEntry() != 21965 && owner->GetEntry() != 21214) ||
            (entry == 24224 && owner->GetEntry() != 23577)) continue;
        Unit* victim = owner->GetVictim();
        if (!live(victim) || (entry != 8179 && victim == bot) || !victim->IsPlayer() ||
            static_cast<Player*>(victim)->IsBeingTeleported() ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) continue;
        if (!selected || totem == current || (selected != current && bot->GetDistance(totem) < bot->GetDistance(selected)))
            selected = totem;
    }
    return selected;
}
