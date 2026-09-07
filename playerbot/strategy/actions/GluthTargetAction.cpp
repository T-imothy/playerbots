#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetGluthTarget()
{
    if (bot->GetMapId() != 533 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    const auto nearby = AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1");
    auto live = [this](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer();
    };
    Unit* boss = nullptr;
    for (const auto& guid : nearby)
    {
        Unit* candidate = ai->GetUnit(guid);
        if (!live(candidate) || candidate->GetEntry() != 15932 || !candidate->IsInCombat() ||
            bot->GetDistance(candidate) > 100) continue;
        Unit* victim = candidate->GetVictim();
        if (!live(victim) || !victim->IsPlayer() || victim == bot ||
            static_cast<Player*>(victim)->IsBeingTeleported() ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) continue;
        if (boss && boss != candidate) return nullptr;
        boss = candidate;
    }
    if (!boss) return nullptr;
    Unit* closest = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    bool currentValid = false;
    for (const auto& guid : nearby)
    {
        Unit* chow = ai->GetUnit(guid);
        // Decimate leaves five percent, with integer rounding in native damage.
        // Healthy zombies retain their normal kiting/CC behavior.
        if (!live(chow) || chow->GetEntry() != 16360 || !chow->GetMaxHealth() ||
            chow->GetHealth() > chow->GetMaxHealth() / 20 + 1 ||
            chow->GetUInt32Value(UNIT_CREATED_BY_SPELL) != 28217 || chow->GetDistance(boss) > 100) continue;
        Unit* trigger = ai->GetUnit(chow->GetSpawnerGuid());
        if (!live(trigger) || trigger->GetEntry() != 15384 || trigger->GetDistance(boss) > 100) continue;
        // The native trigger summons these; Gluth is not their spawner. Wrath
        // clears their attack victim after Decimate, so do not require one.
        if (!PossibleTargetsValue::IsValid(chow, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(chow, bot, sPlayerbotAIConfig.sightDistance, true) ||
            PossibleAttackTargetsValue::HasBreakableCC(chow, bot)) continue;
        if (chow == current) currentValid = true;
        if (!closest || chow->GetDistance(boss) < closest->GetDistance(boss) ||
            (chow->GetDistance(boss) == closest->GetDistance(boss) && chow->GetObjectGuid() < closest->GetObjectGuid()))
            closest = chow;
    }
    // Finish a valid current zombie unless another is appreciably nearer Gluth.
    if (closest && currentValid && current->GetDistance(boss) <= closest->GetDistance(boss) + 3) return current;
    return closest;
}
