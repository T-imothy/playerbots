#include "playerbot/playerbot.h"
#include "playerbot/ServerFacade.h"
#include "EncounterSpellPolicy.h"

namespace
{
    bool HasCorruptedHealing(Player* bot)
    {
        return bot && bot->getClass() == CLASS_PRIEST && bot->IsInWorld() &&
            bot->IsAlive() && !bot->IsBeingTeleported() && !bot->HasCharmer() &&
            bot->GetMapId() == 469 && bot->HasAura(23401);
    }

    bool HasDirectHealingPayload(const SpellEntry* spell)
    {
        if (!spell) return false;
        // Unit::HandleOverrideClassScriptAuraProc script 3656 uses this exact
        // effect predicate. Periodic healing (Renew) and absorbs do not match.
        if (IsSpellHaveEffect(spell, SPELL_EFFECT_HEAL)) return true;

        // Channels such as Wrath's healing Penance and Divine Hymn cast a
        // direct-heal payload on each tick. Inspect only their immediate native
        // tick spell: no recursive spell graph, aura scan or rank whitelist.
        if (IsChanneledSpell(spell))
            for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
                if (spell->Effect[effect] == SPELL_EFFECT_APPLY_AURA &&
                    spell->EffectApplyAuraName[effect] == SPELL_AURA_PERIODIC_TRIGGER_SPELL &&
                    spell->EffectTriggerSpell[effect])
                {
                    const SpellEntry* tick = sServerFacade.LookupSpellInfo(spell->EffectTriggerSpell[effect]);
                    if (tick && IsSpellHaveEffect(tick, SPELL_EFFECT_HEAL)) return true;
                }
        return false;
    }

    bool IsCorruptedHealingCast(Player* bot, Spell* cast)
    {
        // Never attempt to recall a projectile or modify a completed spell.
        return cast && (cast->getState() == SPELL_STATE_CASTING ||
            cast->getState() == SPELL_STATE_CHANNELING) &&
            ai::ShouldAvoidCorruptedHealing(bot, cast->m_spellInfo, cast->m_targets.getUnitTarget());
    }
}

bool ai::ShouldAvoidCorruptedHealing(Player* bot, const SpellEntry* spell, Unit* target)
{
    if (!HasCorruptedHealing(bot) || !spell) return false;

#ifdef MANGOSBOT_TWO
    // Spell::EffectDummy replaces Penance with the healing or damage channel
    // using this family flag and CanAssistSpell. Preserve offensive Penance.
    if (spell->SpellFamilyName == SPELLFAMILY_PRIEST &&
        (spell->SpellFamilyFlags & uint64(0x0080000000000000)) &&
        IsSpellHaveEffect(spell, SPELL_EFFECT_DUMMY))
        return target && target->IsInWorld() && bot->IsInMap(target) && bot->CanAssistSpell(target, spell);
#endif

    return HasDirectHealingPayload(spell);
}

bool ai::HasCorruptedHealingCast(Player* bot)
{
    if (!HasCorruptedHealing(bot)) return false;
    return IsCorruptedHealingCast(bot, bot->GetCurrentSpell(CURRENT_GENERIC_SPELL)) ||
        IsCorruptedHealingCast(bot, bot->GetCurrentSpell(CURRENT_CHANNELED_SPELL));
}

bool ai::InterruptCorruptedHealingCast(Player* bot)
{
    if (!HasCorruptedHealing(bot)) return false;
    bool interrupted = false;
    for (CurrentSpellTypes slot : { CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL })
        if (IsCorruptedHealingCast(bot, bot->GetCurrentSpell(slot)))
        {
            // Re-read each slot; interruption may mutate the current-spell set.
            bot->InterruptSpell(slot);
            interrupted = true;
        }
    return interrupted;
}

bool ai::HasUnsafeReflectedCast(Player* bot)
{
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->IsBeingTeleported() || bot->HasCharmer()) return false;
    const Spell* cast = bot->GetCurrentSpell(CURRENT_GENERIC_SPELL);
    // Reflection is determined by native spell handling. Do not recall a
    // launched projectile or cancel a channel that has already started.
    if (!cast || cast->getState() != SPELL_STATE_CASTING || !cast->m_spellInfo ||
        !IsReflectableSpell(cast->m_spellInfo)) return false;
    Unit* target = cast->m_targets.getUnitTarget();
    return target && target != bot && target->IsInWorld() && target->IsAlive() &&
        bot->IsInMap(target) && !sServerFacade.IsFriendlyTo(bot, target) &&
        target->GetReflectChance(GetSpellSchoolMask(cast->m_spellInfo)) >= 50.0f;
}

bool ai::InterruptUnsafeReflectedCast(Player* bot)
{
    // Recheck at execution: a queued reflection event can outlive the shield
    // or refer to a different cast after an earlier interruption.
    if (!HasUnsafeReflectedCast(bot)) return false;
    Spell* cast = bot->GetCurrentSpell(CURRENT_GENERIC_SPELL);
    if (!cast->CanBeInterrupted()) return false;
    const uint32 spell = cast->m_spellInfo->Id;
    bot->InterruptSpell(CURRENT_GENERIC_SPELL);
    if (PlayerbotAI* ai = bot->GetPlayerbotAI()) ai->SpellInterrupted(spell);
    return true;
}
