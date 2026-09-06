#include "playerbot/playerbot.h"
#include "EncounterSpellPolicy.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

bool ai::HasEncounterDamagePause(Player* bot)
{
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

bool ai::ShouldAvoidEncounterOffense(Player* bot, Unit* caster, const SpellEntry* spell, Unit* target)
{
    return caster && spell && !IsPositiveSpell(spell, caster, target) && HasEncounterDamagePause(bot);
}

bool ai::HasUnsafeEncounterOffense(Player* bot)
{
    if (!HasEncounterDamagePause(bot)) return false;
    if (bot->hasUnitState(UNIT_STAT_MELEE_ATTACKING)) return true;
    for (CurrentSpellTypes slot : {CURRENT_MELEE_SPELL, CURRENT_GENERIC_SPELL, CURRENT_AUTOREPEAT_SPELL, CURRENT_CHANNELED_SPELL})
    {
        const Spell* cast = bot->GetCurrentSpell(slot);
        if (cast && cast->CanBeInterrupted() && cast->m_spellInfo &&
            !IsPositiveSpell(cast->m_spellInfo, bot, cast->m_targets.getUnitTarget())) return true;
    }
    return false;
}

bool ai::StopUnsafeEncounterOffense(Player* bot, Unit* caster)
{
    if (!caster || !caster->IsInWorld() || !bot || !bot->IsInMap(caster) || !HasEncounterDamagePause(bot)) return false;
    bool stopped = false;
    if (caster->hasUnitState(UNIT_STAT_MELEE_ATTACKING))
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
            IsPositiveSpell(cast->m_spellInfo, caster, cast->m_targets.getUnitTarget())) continue;
        const uint32 spellId = cast->m_spellInfo->Id;
        caster->InterruptSpell(slot);
        if (caster == bot) bot->GetPlayerbotAI()->SpellInterrupted(spellId);
        stopped = true;
    }
    return stopped;
}
