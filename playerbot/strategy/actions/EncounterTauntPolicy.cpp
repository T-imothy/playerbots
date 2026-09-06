#include "playerbot/playerbot.h"
#include "EncounterSpellPolicy.h"

namespace
{
    Player* EbonrocTank(PlayerbotAI* ai, Unit* enemy)
    {
        Player* bot = ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            bot->GetMapId() != 469 || !bot->GetGroup() || !enemy || !enemy->IsInWorld() || !enemy->IsAlive() ||
            !enemy->IsInCombat() || enemy->HasCharmer() || !bot->IsInMap(enemy) || enemy->GetEntry() != 14601) return nullptr;
        Unit* victim = enemy->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
            victim->HasCharmer() || !bot->IsInMap(victim)) return nullptr;
        Player* tank = static_cast<Player*>(victim);
        return tank->GetGroup() == bot->GetGroup() && !tank->IsBeingTeleported() && ai->IsTank(tank) ? tank : nullptr;
    }
}

bool ai::ShouldSwapEncounterTank(PlayerbotAI* ai, Unit* enemy)
{
    Player* tank = EbonrocTank(ai, enemy);
    Player* bot = ai->GetBot();
    // The existing lose-aggro trigger normally (correctly) avoids stealing
    // another tank's enemy. Native Shadow of Ebonroc is an explicit exception:
    // a clean tank should use its ordinary learned taunt, not modify threat.
    return tank && tank != bot && ai->IsTank(bot) && !bot->HasAura(23340) &&
        tank->GetSpellAuraHolder(23340, enemy->GetObjectGuid());
}

bool ai::ShouldAvoidEncounterTaunt(PlayerbotAI* ai, const SpellEntry* spell, Unit* enemy)
{
    if (!spell || !EbonrocTank(ai, enemy)) return false;
    bool taunt = false;
    for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        taunt |= spell->Effect[effect] == SPELL_EFFECT_ATTACK_ME ||
            (spell->Effect[effect] == SPELL_EFFECT_APPLY_AURA && spell->EffectApplyAuraName[effect] == SPELL_AURA_MOD_TAUNT);
    // Recheck at actual dispatch, after another tank may already have landed
    // its taunt. Do not bounce the boss back to an afflicted/previous tank.
    return taunt && !ShouldSwapEncounterTank(ai, enemy);
}
