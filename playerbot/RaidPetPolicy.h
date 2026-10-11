#pragma once

namespace ai
{
    inline bool RaidPetThreatSpell(const SpellEntry* spell)
    {
        if (!spell) return false;
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            if (spell->Effect[effect] == SPELL_EFFECT_ATTACK_ME ||
                (spell->Effect[effect] == SPELL_EFFECT_APPLY_AURA &&
                    spell->EffectApplyAuraName[effect] == SPELL_AURA_MOD_TAUNT) ||
                (spell->Effect[effect] == SPELL_EFFECT_THREAT && spell->EffectBasePoints[effect] >= 0))
                return true;
        return false;
    }

    inline bool RaidPetThreatBlocked(PlayerbotAI* ai, const SpellEntry* spell)
    {
        Player* bot = ai->GetBot();
        return !ai->IsRealPlayer() && bot->IsInWorld() && !bot->IsBeingTeleported() &&
            (bot->GetMap()->IsRaid() || (bot->GetGroup() && bot->GetGroup()->IsRaidGroup())) &&
            RaidPetThreatSpell(spell);
    }
}
