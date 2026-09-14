#pragma once
#include "Objects/TemporarySummon.h"
#include "Objects/Pet.h"
#include "Objects/Totem.h"
#include "Spells/Spell.h"
namespace ai
{
inline ObjectGuid NativeSpawnerGuid(Unit const* unit)
{
    if (auto summon = dynamic_cast<TemporarySummon const*>(unit)) return summon->GetSummonerGuid();
    if (dynamic_cast<Pet const*>(unit) || dynamic_cast<Totem const*>(unit)) return unit->GetOwnerGuid();
    return ObjectGuid();
}
inline int32 NativeReflectChance(Unit const* target, SpellSchoolMask school)
{
    int32 chance = target->GetTotalAuraModifier(SPELL_AURA_REFLECT_SPELLS);
    for (Aura const* aura : target->GetAurasByType(SPELL_AURA_REFLECT_SPELLS_SCHOOL))
        if (aura->GetModifier()->m_miscvalue & school) chance += aura->GetModifier()->m_amount;
    return chance;
}
inline bool HasInterruptibleNativeCast(Unit* target)
{
    // Same damage-interrupt flags that native EffectInterruptCast checks.
    for (CurrentSpellTypes slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
        if (Spell* spell = target->GetCurrentSpell(slot))
            if (spell->CanBeInterrupted() &&
                ((slot == CURRENT_GENERIC_SPELL && (spell->m_spellInfo->InterruptFlags & SPELL_INTERRUPT_FLAG_DAMAGE)) ||
                 (slot == CURRENT_CHANNELED_SPELL && (spell->m_spellInfo->ChannelInterruptFlags & CHANNEL_FLAG_INTERRUPT)))) return true;
    return false;
}
}
inline bool IsReflectableSpell(SpellEntry const* info) { return info && info->IsReflectableSpell(); }

inline bool IsAuraApplyEffect(SpellEntry const* spellInfo, SpellEffectIndex effecIdx)
{
    switch (spellInfo->Effect[effecIdx])
    {
        case SPELL_EFFECT_APPLY_AURA:
        case SPELL_EFFECT_PERSISTENT_AREA_AURA:
        case SPELL_EFFECT_APPLY_AREA_AURA_PARTY:
        case SPELL_EFFECT_APPLY_AREA_AURA_PET:
            return true;
    }
    return false;
}

inline bool IsSpellEffectTriggerSpell(const SpellEntry* entry, SpellEffectIndex effIndex)
{
    if (!entry)
        return false;

    switch (entry->Effect[effIndex])
    {
        case SPELL_EFFECT_TRIGGER_MISSILE:
        case SPELL_EFFECT_TRIGGER_SPELL:
            return true;
    }
    return false;
}

inline bool IsSpellEffectTriggerSpellByAura(const SpellEntry* entry, SpellEffectIndex effIndex)
{
    if (!entry || !IsAuraApplyEffect(entry, effIndex))
        return false;

    switch (entry->EffectApplyAuraName[effIndex])
    {
        case SPELL_AURA_PERIODIC_TRIGGER_SPELL:
        case SPELL_AURA_PROC_TRIGGER_SPELL:
        case SPELL_AURA_PROC_TRIGGER_DAMAGE:
            return true;
    }
    return false;
}

inline bool IsSpellEffectDamage(SpellEntry const& spellInfo, SpellEffectIndex i)
{
    if (!spellInfo.EffectApplyAuraName[i])
    {
        // If its not an aura effect, check for damage effects
        switch (spellInfo.Effect[i])
        {
            case SPELL_EFFECT_SCHOOL_DAMAGE:
            case SPELL_EFFECT_ENVIRONMENTAL_DAMAGE:
            case SPELL_EFFECT_HEALTH_LEECH:
            case SPELL_EFFECT_WEAPON_DAMAGE_NOSCHOOL:
            case SPELL_EFFECT_WEAPON_PERCENT_DAMAGE:
            case SPELL_EFFECT_WEAPON_DAMAGE:
            //   SPELL_EFFECT_POWER_BURN: deals damage for power burned, but its either full damage or resist?
            case SPELL_EFFECT_NORMALIZED_WEAPON_DMG:
                return true;
        }
    }
    else
    {
        // If its an aura effect, check for DoT auras
        switch (spellInfo.EffectApplyAuraName[i])
        {
            case SPELL_AURA_PERIODIC_DAMAGE:
            case SPELL_AURA_PERIODIC_LEECH:
            //   SPELL_AURA_POWER_BURN_MANA: deals damage for power burned, but not really a DoT?
            case SPELL_AURA_PERIODIC_MANA_LEECH: // confirmed via 31447
            case SPELL_AURA_PERIODIC_DAMAGE_PERCENT:
                return true;
        }
    }
    return false;
}
