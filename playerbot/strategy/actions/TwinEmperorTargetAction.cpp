#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetTwinEmperorTarget()
{
    if (bot->GetMapId() != 531 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;

    // Hunters remain physical DPS despite their ranged strategy. Tank/healer
    // assignments and explicit attack/raid-icon commands are checked by GetTarget.
    const bool caster = ai->IsRanged(bot) && bot->getClass() != CLASS_HUNTER;
    const uint32 entry = caster ? 15276 : 15275;
    Unit* selected = nullptr;
    for (const auto& guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* twin = ai->GetUnit(guid);
        if (!twin || twin->GetEntry() != entry || !twin->IsInWorld() || !twin->IsAlive() ||
            !twin->IsInCombat() || !bot->IsInMap(twin) || twin->HasCharmer() || twin->HasAura(800)) continue;
        // Teleport clears threat and delays the next victim. Wait for the tank
        // to regain the boss instead of racing the native two-second recovery.
        Unit* victim = twin->GetVictim();
        if (!victim || victim == bot || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
            !bot->IsInMap(victim) || victim->HasCharmer() || static_cast<Player*>(victim)->IsBeingTeleported() ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) continue;
        if (!PossibleTargetsValue::IsValid(twin, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(twin, bot, sPlayerbotAIConfig.sightDistance, false) ||
            PossibleAttackTargetsValue::HasBreakableCC(twin, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(twin, bot)) continue;
        if (selected && selected != twin) return nullptr;
        selected = twin;
    }
    return selected;
}
