#include "playerbot/playerbot.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "EncounterSpellPolicy.h"

namespace
{
    bool HasPoisonDispel(const SpellEntry* spell)
    {
        if (!spell) return false;
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            if (spell->Effect[effect] == SPELL_EFFECT_DISPEL &&
                spell->EffectMiscValue[effect] >= 0 && spell->EffectMiscValue[effect] <= DISPEL_ZG_TICKET &&
                (GetDispellMask(DispelType(spell->EffectMiscValue[effect])) & (1u << DISPEL_POISON))) return true;
        return false;
    }

    bool ShouldPreserveHakkarPoison(PlayerbotAI* ai, const SpellEntry* spell, Unit* target)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
            bot->HasCharmer() || bot->GetMapId() != 309 || !spell) return false;
        const bool direct = HasPoisonDispel(spell);
        bool periodic = false;
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            if (spell->Effect[effect] == SPELL_EFFECT_APPLY_AURA &&
                spell->EffectApplyAuraName[effect] == SPELL_AURA_PERIODIC_TRIGGER_SPELL &&
                HasPoisonDispel(sServerFacade.LookupSpellInfo(spell->EffectTriggerSpell[effect]))) periodic = true;
        // Classic/TBC use Poison Cleansing Totem; Wrath merges poison and
        // disease into Cleansing Totem. Preserve the native era's actual spell.
#ifdef MANGOSBOT_TWO
        const bool totem = spell->Id == 8170;
#else
        const bool totem = spell->Id == 8166;
#endif
        if (!direct && !periodic && !totem) return false;
        bool engaged = false;
        for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
        {
            Unit* boss = ai->GetUnit(guid);
            if (boss && boss->GetEntry() == 14834 && boss->IsInWorld() && bot->IsInMap(boss) &&
                boss->IsAlive() && boss->IsInCombat()) { engaged = true; break; }
        }
        if (!engaged) return false;
        // Native BloodSiphon chooses damage 24323 instead of healing 24322
        // only while the player still has Poisonous Blood 24321.
        if (direct && target && target->IsInWorld() && bot->IsInMap(target) &&
            sServerFacade.IsFriendlyTo(bot, target) && target->HasAura(24321)) return true;
        // A continuing cleanse would remove the poison after it is acquired.
        // Existing effects and human actions are not removed or rewritten.
        return periodic || totem;
    }

    bool HasDiseaseDispel(const SpellEntry* spell)
    {
        if (!spell) return false;
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            if (spell->Effect[effect] == SPELL_EFFECT_DISPEL &&
                spell->EffectMiscValue[effect] >= 0 && spell->EffectMiscValue[effect] <= DISPEL_ZG_TICKET &&
                (GetDispellMask(DispelType(spell->EffectMiscValue[effect])) & (1u << DISPEL_DISEASE))) return true;
        return false;
    }

    bool HasPeriodicDiseaseDispel(const SpellEntry* spell)
    {
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            if (spell->Effect[effect] == SPELL_EFFECT_APPLY_AURA &&
                spell->EffectApplyAuraName[effect] == SPELL_AURA_PERIODIC_TRIGGER_SPELL &&
                HasDiseaseDispel(sServerFacade.LookupSpellInfo(spell->EffectTriggerSpell[effect]))) return true;
        return false;
    }
}

bool ai::IsProtectedEncounterDispel(Unit* target, uint32 dispelType)
{
    // The native Grobbulus OnApply(false) explicitly detonates on dispel. The
    // normal core dispel pool is random, so another disease does not make a
    // disease-removal spell safe while this aura remains on the same target.
    return target && target->IsInWorld() && target->GetMapId() == 533 &&
        dispelType <= DISPEL_ZG_TICKET && (GetDispellMask(DispelType(dispelType)) & (1u << DISPEL_DISEASE)) &&
        target->HasAura(28169);
}

bool ai::ShouldAvoidEncounterDispel(PlayerbotAI* ai, const SpellEntry* spell, Unit* target)
{
    if (ShouldPreserveHakkarPoison(ai, spell, target)) return true;
    Player* bot = ai->GetBot();
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 533 || !spell) return false;
    const bool direct = HasDiseaseDispel(spell);
    const bool periodic = HasPeriodicDiseaseDispel(spell);
    // Native 8170 summons entry 5924 in all three eras. In Wrath it also cleanses
    // poison; its renamed spell still must not auto-detonate an injection.
    const bool cleansingTotem = spell->Id == 8170;
    if (!direct && !periodic && !cleansingTotem) return false;
    if (target && target->IsInWorld() && bot->IsInMap(target) &&
        sServerFacade.IsFriendlyTo(bot, target) && IsProtectedEncounterDispel(target, DISPEL_DISEASE)) return true;
    if (!periodic && !cleansingTotem) return false;

    // Do not prepare a continuing cleanse that will remove the next injection.
    // This only withholds new automatic casts: no existing human aura/totem is
    // deleted and manual spell commands retain their separate native path.
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* enemy = ai->GetUnit(guid);
        if (enemy && enemy->IsInWorld() && bot->IsInMap(enemy) && enemy->IsAlive() &&
            enemy->IsInCombat() && enemy->GetEntry() == 15931) return true;
    }
    if (Group* group = bot->GetGroup())
        for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() &&
                !member->HasCharmer() && bot->IsInMap(member) && member->HasAura(28169)) return true;
        }
    return false;
}
