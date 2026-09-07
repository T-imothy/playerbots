#include "playerbot/playerbot.h"
#include "EncounterSpellPolicy.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

bool ai::HasEncounterDamagePause(Player* bot)
{
    if (HasHakkarPoisonPreparation(bot)) return true;
#ifdef MANGOSBOT_TWO
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->HasCharmer() || bot->IsBeingTeleported() || !bot->GetPlayerbotAI() ||
        bot->GetPlayerbotAI()->IsRealPlayer()) return false;
    uint32 entry = 0;
    if (bot->GetMapId() == 575) entry = 26861; // King Ymiron
    else if (bot->GetMapId() == 632) entry = 36502; // Devourer of Souls
    else return false;

    // Use native objects, without reading another unit's mutable AI context.
    // These two rooms require a brief offensive pause, including untargeted
    // AoE that could otherwise hit the protected boss while attacking an add.
    std::list<Unit*> candidates;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, entry, 100.0f);
    MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(candidates, check);
    Cell::VisitAllObjects(bot, searcher, 100.0f);
    for (Unit* boss : candidates)
    {
        if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() ||
            boss->HasCharmer() || !bot->IsInMap(boss) || boss->GetEntry() != entry ||
            bot->GetDistance(boss) > 100.0f || std::fabs(bot->GetPositionZ() - boss->GetPositionZ()) > 8.0f)
            continue;
        if (entry == 26861 && (boss->HasAura(48294) || boss->HasAura(59301))) return true;
        // Native Mirrored Soul puts 69023 on the boss, cast by the linked player.
        if (entry == 36502 && boss->HasAura(69023)) return true;
    }
#endif
    return false;
}

bool ai::HasEncounterThreatPause(Player* bot)
{
    if (!bot || bot->GetMapId() != 309 || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        !bot->GetPlayerbotAI() || bot->GetPlayerbotAI()->IsRealPlayer()) return false;
    const SpellAuraHolder* gaze = bot->GetSpellAuraHolder(24314);
    Unit* boss = gaze ? gaze->GetCaster() : nullptr;
    // Native Mandokir compares the watched player's threat when this aura ends.
    // Its real caster identifies the encounter even if the bot has moved away.
    return boss && boss->GetEntry() == 11382 && boss->IsInWorld() && boss->IsAlive() &&
        boss->IsInCombat() && !boss->HasCharmer() && bot->IsInMap(boss);
}

bool ai::ShouldAvoidEncounterOffense(Player* bot, Unit* caster, const SpellEntry* spell, Unit* target)
{
    if (!caster || !spell) return false;
    const bool positive = IsPositiveSpell(spell, caster, target);
    if (!positive && HasEncounterDamagePause(bot)) return true;
    if (caster == bot && HasEncounterSpellBomb(bot))
    {
        // A melee ability can still apply a bleed: later periodic ticks use a
        // different proc mask. Treat triggered payloads conservatively as well.
        for (uint32 index = 0; index < MAX_EFFECT_INDEX; ++index)
        {
            const SpellEffectIndex effect = SpellEffectIndex(index);
            if (IsSpellEffectTriggerSpell(spell, effect) || IsSpellEffectTriggerSpellByAura(spell, effect) ||
                (IsAuraApplyEffect(spell, effect) && IsSpellEffectDamage(*spell, effect))) return true;
        }
        // The native mask excludes plain melee abilities and ranged auto
        // attacks (including wands), and respects caster-proc suppression.
        if (!spell->HasAttribute(SPELL_ATTR_EX3_SUPPRESS_CASTER_PROCS) &&
            spell->DmgClass != SPELL_DAMAGE_CLASS_MELEE &&
            !(spell->HasAttribute(SPELL_ATTR_EX2_AUTO_REPEAT) &&
                (spell->DmgClass == SPELL_DAMAGE_CLASS_RANGED || !positive))) return true;
    }
    if (caster != bot || !HasEncounterThreatPause(bot)) return false;
    // Helpful spells with these flags bypass native threatAssist. Harmful
    // NO_THREAT spells can still add to an existing threat reference.
    return !positive || !(spell->HasAttribute(SPELL_ATTR_EX_NO_THREAT) ||
        spell->HasAttribute(SPELL_ATTR_EX2_NO_INITIAL_THREAT) ||
        spell->HasAttribute(SPELL_ATTR_EX4_NO_HELPFUL_THREAT));
}

bool ai::HasEncounterSpellBomb(Player* bot)
{
#ifndef MANGOSBOT_ZERO
    if (!bot || bot->GetMapId() != 556 || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        !bot->GetPlayerbotAI() || bot->GetPlayerbotAI()->IsRealPlayer()) return false;
    const SpellAuraHolder* bomb = bot->GetSpellAuraHolder(40303);
    Unit* boss = bomb ? bomb->GetCaster() : nullptr;
    return boss && boss->GetEntry() == 23035 && boss->IsInWorld() && boss->IsAlive() &&
        boss->IsInCombat() && !boss->HasCharmer() && bot->IsInMap(boss);
#endif
    return false;
}

bool ai::HasUnsafeEncounterOffense(Player* bot)
{
    const bool stopAttacks = HasEncounterDamagePause(bot) || HasEncounterThreatPause(bot);
    if (!stopAttacks && !HasEncounterSpellBomb(bot)) return false;
    if (stopAttacks && bot->hasUnitState(UNIT_STAT_MELEE_ATTACKING)) return true;
    for (CurrentSpellTypes slot : {CURRENT_MELEE_SPELL, CURRENT_GENERIC_SPELL, CURRENT_AUTOREPEAT_SPELL, CURRENT_CHANNELED_SPELL})
    {
        const Spell* cast = bot->GetCurrentSpell(slot);
        if (cast && cast->CanBeInterrupted() && cast->m_spellInfo &&
            ShouldAvoidEncounterOffense(bot, bot, cast->m_spellInfo, cast->m_targets.getUnitTarget())) return true;
    }
    return false;
}

bool ai::StopUnsafeEncounterOffense(Player* bot, Unit* caster)
{
    if (!caster || !caster->IsInWorld() || !bot || !bot->IsInMap(caster)) return false;
    const bool stopAttacks = HasEncounterDamagePause(bot) || (caster == bot && HasEncounterThreatPause(bot));
    if (!stopAttacks && !(caster == bot && HasEncounterSpellBomb(bot))) return false;
    bool stopped = false;
    if (stopAttacks && caster->hasUnitState(UNIT_STAT_MELEE_ATTACKING))
    {
        caster->AttackStop();
        stopped = true;
    }
    for (CurrentSpellTypes slot : {CURRENT_MELEE_SPELL, CURRENT_GENERIC_SPELL, CURRENT_AUTOREPEAT_SPELL, CURRENT_CHANNELED_SPELL})
    {
        Spell* cast = caster->GetCurrentSpell(slot);
        // Do not attempt to recall missiles that have already launched.
        if (!cast || cast->getState() == SPELL_STATE_FINISHED || cast->getState() == SPELL_STATE_TRAVELING ||
            !cast->m_spellInfo || !cast->CanBeInterrupted() ||
            !ShouldAvoidEncounterOffense(bot, caster, cast->m_spellInfo, cast->m_targets.getUnitTarget())) continue;
        const uint32 spellId = cast->m_spellInfo->Id;
        caster->InterruptSpell(slot);
        if (caster == bot) bot->GetPlayerbotAI()->SpellInterrupted(spellId);
        stopped = true;
    }
    return stopped;
}
