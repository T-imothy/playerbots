#include "playerbot/playerbot.h"
#include "WarriorCombatPolicy.h"
#include "playerbot/ServerFacade.h"

std::string ai::WarriorStancePrerequisite(PlayerbotAI* ai, const SpellEntry* spell)
{
    Player* bot = ai->GetBot();
    if (bot->getClass() != CLASS_WARRIOR || !spell || !spell->Stances ||
        GetErrorAtShapeshiftedCast(spell, bot->GetShapeshiftForm()) == SPELL_CAST_OK)
        return "";
    // Read this expansion's native form rules; do not copy spell IDs between eras.
    const uint32 forms[] = { FORM_BATTLESTANCE, FORM_DEFENSIVESTANCE, FORM_BERSERKERSTANCE };
    const char* names[] = { "battle stance", "defensive stance", "berserker stance" };
    for (unsigned i = 0; i < 3; ++i)
        if (GetErrorAtShapeshiftedCast(spell, forms[i]) == SPELL_CAST_OK &&
            ai->HasSpell(names[i]) && ai->CanCastSpell(names[i], bot, 0))
            return names[i];
    return "";
}

bool ai::CanPlanWarriorSpell(PlayerbotAI* ai, const std::string& name, Unit* target)
{
    if (!target) return false;
    SpellCastResult reason = SPELL_CAST_OK;
    if (ai->CanCastSpell(name, target, 0, nullptr, true, false, false, &reason))
        return true;
    if (ai->GetBot()->getClass() != CLASS_WARRIOR ||
        (reason != SPELL_FAILED_ONLY_SHAPESHIFT && reason != SPELL_FAILED_NOT_SHAPESHIFT))
        return false;
    const uint32 id = ai->GetAiObjectContext()->GetValue<uint32>("spell id", name)->Get();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
    // Native CheckCast tests form before reactive/proc state. Do not stance-dance
    // toward Overpower/Revenge unless their native reactive state exists.
    if (!spell || (spell->CasterAuraState && !ai->GetBot()->HasAuraState(AuraState(spell->CasterAuraState))))
        return false;
    if (spell->powerType == POWER_RAGE)
    {
        Player* bot = ai->GetBot();
        uint32 retained = 0;
        if (bot->GetShapeshiftForm() == FORM_DEFENSIVESTANCE)
            if (Aura* aura = bot->GetOverrideScript(831))
                retained += aura->GetModifier()->m_amount * 10;
#ifdef MANGOSBOT_ZERO
        for (Aura* aura : bot->GetAurasByType(SPELL_AURA_OVERRIDE_CLASS_SCRIPTS))
        {
            const int script = aura->GetModifier()->m_miscvalue;
            if (script >= 831 && script <= 835)
            {
                retained += (script - 830) * 50;
                break;
            }
        }
#else
        for (const auto& entry : bot->GetSpellMap())
        {
            if (entry.second.state == PLAYERSPELL_REMOVED) continue;
            const SpellEntry* passive = sServerFacade.LookupSpellInfo(entry.first);
            if (passive && passive->SpellFamilyName == SPELLFAMILY_WARRIOR && passive->SpellIconID == 139)
                retained += bot->CalculateSpellEffectValue(bot, passive, EFFECT_INDEX_0) * 10;
        }
#endif
        if (std::min(bot->GetPower(POWER_RAGE), retained) < Spell::CalculatePowerCost(spell, bot))
            return false;
    }
    return !WarriorStancePrerequisite(ai, spell).empty();
}
