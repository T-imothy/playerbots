
#include "playerbot/playerbot.h"
#include "MageActions.h"
#include "playerbot/ServerFacade.h"
#include "Spells/SpellAuras.h"
#include "Spells/SpellMgr.h"

using namespace ai;

bool CastSpellstealAction::HasStealableAura(PlayerbotAI* ai, Unit* target, const SpellEntry* spell)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        !target || target == bot || !target->IsInWorld() || !target->IsAlive() ||
        !bot->IsInMap(target) || !spell || !bot->CanAttackSpell(target, spell)) return false;
    uint32 mask = 0;
    for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        if (spell->Effect[effect] == SPELL_EFFECT_STEAL_BENEFICIAL_BUFF &&
            spell->EffectMiscValue[effect] >= 0 && spell->EffectMiscValue[effect] <= DISPEL_ZG_TICKET)
            mask |= GetDispellMask(DispelType(spell->EffectMiscValue[effect]));
    if (!mask) return false;
    // Match native EffectStealBeneficialBuff's holder predicate. Ordinary
    // dispellability alone does not mean a buff can be stolen. Native CheckCast
    // does not test this pool, so a no-op cast can otherwise consume mana/GCD.
    for (const auto& aura : target->GetSpellAuraHolderMap())
    {
        const SpellAuraHolder* holder = aura.second;
        if (!holder || !holder->IsPositive() || holder->IsPassive()) continue;
        const SpellEntry* entry = holder->GetSpellProto();
        if (!entry || entry->Dispel > DISPEL_ZG_TICKET || !(mask & (1u << entry->Dispel)) ||
            entry->HasAttribute(SPELL_ATTR_EX4_CANNOT_BE_STOLEN)) continue;
        const int32 remaining = holder->GetAuraDuration();
        if (sPlayerbotAIConfig.dispelAuraDuration && remaining > 0 &&
            remaining < (int32)sPlayerbotAIConfig.dispelAuraDuration) continue;
        return true;
    }
#endif
    return false;
}

bool CastSpellstealAction::isUseful()
{
    return CastSpellAction::isUseful() && HasStealableAura(ai, GetTarget(), sServerFacade.LookupSpellInfo(GetSpellID()));
}

bool CastSpellstealAction::Execute(Event& event)
{
    RefreshSpellId();
    return HasStealableAura(ai, GetTarget(), sServerFacade.LookupSpellInfo(GetSpellID())) && CastSpellAction::Execute(event);
}
