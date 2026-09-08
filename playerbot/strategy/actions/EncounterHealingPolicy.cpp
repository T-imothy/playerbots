#include "playerbot/playerbot.h"
#include "GenericSpellActions.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/PlayerbotAIConfig.h"

using namespace ai;

uint32 ai::RemainingHealingAbsorb(Unit* target)
{
#ifdef MANGOSBOT_TWO
    if (!target || !target->IsInWorld() || !target->IsAlive()) return 0;
    uint64 remaining = 0;
    // Native CalculateHealAbsorb consumes positive amounts before restoring
    // health, including when the recipient already has full health.
    for (const Aura* aura : target->GetAurasByType(SPELL_AURA_HEAL_ABSORB))
        if (aura->GetModifier()->m_amount > 0)
            remaining += uint32(aura->GetModifier()->m_amount);
    return uint32(std::min<uint64>(remaining, uint64(UINT32_MAX)));
#else
    return 0;
#endif
}

bool ai::NeedsFullHealingToRemoveAura(Unit* target)
{
#ifndef MANGOSBOT_ZERO
    if (!target || !target->IsInWorld() || !target->IsAlive() ||
        !target->GetMaxHealth() || target->GetHealth() >= target->GetMaxHealth()) return false;
    // The native periodic-damage handler removes these exact wounds only at
    // full health. Finishing the heal is useful even when most of it overheals.
    for (uint32 id : {43093u, 31956u, 38801u, 35321u, 38363u, 39215u, 48920u})
        if (target->HasAura(id)) return true;
#endif
    return false;
}

uint32 ai::UpcomingEncounterHealingWindow(Player* bot, Unit* target)
{
#ifdef MANGOSBOT_TWO
    if (!bot || !target || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->GetMapId() != 533 || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target)) return 0;
    const SpellAuraHolder* aura = target->GetSpellAuraHolder(55593);
    Unit* boss = aura ? aura->GetCaster() : nullptr;
    if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() ||
        !bot->IsInMap(boss) || boss->HasCharmer() || boss->GetEntry() != 16011 ||
        aura->GetAuraDuration() <= 0 || aura->GetAuraDuration() > 3000) return 0;
    for (const Aura* modifier : target->GetAurasByType(SPELL_AURA_MOD_HEALING_PCT))
        if (modifier->GetId() != 55593 && modifier->GetModifier()->m_amount <= -100) return 0;
    return uint32(aura->GetAuraDuration());
#else
    return 0;
#endif
}

bool ai::CanPrecastEncounterHeal(Player* bot, Unit* target, const SpellEntry* spell)
{
    const uint32 remaining = UpcomingEncounterHealingWindow(bot, target);
    if (!remaining || !spell || IsChanneledSpell(spell) || !IsSpellHaveEffect(spell, SPELL_EFFECT_HEAL)) return false;
    // Native haste/talents determine completion. Leave 100 ms after aura expiry
    // and stay inside the three-second healing interval in both raid modes.
    const uint32 castTime = GetSpellCastTime(spell, bot);
    return castTime >= remaining + 100 && castTime <= remaining + 2800;
}

bool CastHealingSpellAction::isUseful()
{
    RefreshSpellId();
    Unit* target = GetTarget();
    if (target && target->GetMaxNegativeAuraModifier(SPELL_AURA_MOD_HEALING_PCT) <= -100 &&
        !CanPrecastEncounterHeal(bot, target, sServerFacade.LookupSpellInfo(GetSpellID()))) return false;
    // Regrowth and Riptide also heal immediately. Their existing HoT must not
    // prevent a needed direct heal; pure HoTs still avoid redundant refreshes.
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(GetSpellID());
    // Stack/expiry-aware actions such as Lifebloom select their own refreshes.
    if (allowAuraRefresh || (target && target->GetHealthPercent() < sPlayerbotAIConfig.lowHealth &&
        spell && IsSpellHaveEffect(spell, SPELL_EFFECT_HEAL)))
        return CastSpellAction::isUseful();
    return CastAuraSpellAction::isUseful();
}

bool CastHealingSpellAction::Execute(Event& event)
{
    RefreshSpellId();
    Unit* target = GetTarget();
    // A queued heal can outlive the opening or its original target. Preserve
    // ordinary native cast execution only while the landing is still useful.
    if (target && target->GetMaxNegativeAuraModifier(SPELL_AURA_MOD_HEALING_PCT) <= -100 &&
        !CanPrecastEncounterHeal(bot, target, sServerFacade.LookupSpellInfo(GetSpellID()))) return false;
    return CastAuraSpellAction::Execute(event);
}
