#include "playerbot/playerbot.h"
#include "RighteousDefenseTargetValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/actions/EncounterSpellPolicy.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

Unit* RighteousDefenseTargetValue::Calculate()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !bot->GetGroup() || !ai->IsTank(bot)) return nullptr;
    Unit* enemy = AI_VALUE(Unit*, "current target");
    if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !enemy->IsInCombat() || enemy->IsPlayer() ||
        enemy->HasCharmer() || !bot->IsInMap(enemy)) return nullptr;
    Unit* victim = enemy->GetVictim();
    if (!victim || victim == bot || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
        victim->HasCharmer() || !bot->IsInMap(victim)) return nullptr;
    Player* member = static_cast<Player*>(victim);
    if (member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || !member->GetSession() ||
        member->GetSession()->isLogingOut() || (ai->IsTank(member) && !ShouldSwapEncounterTank(ai, enemy))) return nullptr;
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(31789);
    // Both native scripts select up to three attackers OF A FRIENDLY UNIT.
    // Sending the enemy itself is not equivalent to taunting that enemy.
    return spell && bot->CanAssistSpell(member, spell) && member->getAttackers().count(enemy) ? member : nullptr;
#else
    return nullptr;
#endif
}
