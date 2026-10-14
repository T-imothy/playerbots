#include "playerbot/playerbot.h"
#include "GroupBuffPolicy.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"

namespace
{
    const std::pair<const char*, const char*>* BuffFamily(const std::string& name)
    {
        static const std::pair<const char*, const char*> families[] = {
            {"power word: fortitude", "prayer of fortitude"},
            {"divine spirit", "prayer of spirit"},
            {"shadow protection", "prayer of shadow protection"},
            {"arcane intellect", "arcane brilliance"},
            {"mark of the wild", "gift of the wild"}
        };
        for (const auto& family : families)
            if (name == family.first || name == family.second) return &family;
        return nullptr;
    }
}

bool ai::HasEquivalentGroupBuff(PlayerbotAI* ai, const std::string& name, Unit* target)
{
    if (!ai || !target) return false;
    const auto* family = BuffFamily(name);
    return family ? ai->HasAura(family->first, target) || ai->HasAura(family->second, target) : ai->HasAura(name, target);
}

bool ai::AutomaticGroupBuffAllowed(PlayerbotAI* ai, const std::string& name, Unit* target)
{
    const auto* family = BuffFamily(name);
    if (!family) return true; // Shields, HoTs, totems, cooldowns and blessings keep their own policy.
    Player* bot = ai ? ai->GetBot() : nullptr;
    if (!bot || !target || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target) || target->HasCharmer() ||
        !sServerFacade.IsFriendlyTo(bot, target)) return false;
    // Check the full family again at execution time. Cached party targets and
    // a queued single/group variant must not replace an equivalent active buff.
    if (HasEquivalentGroupBuff(ai, name, target)) return false;
    if (target == bot || !bot->GetGroup() || !target->IsPlayer() || ai->IsRealPlayer()) return true;
    Player* patient = static_cast<Player*>(target);
    if (patient->IsBeingTeleported() || patient->GetGroup() != bot->GetGroup()) return true;
    if (name == family->second)
    {
        unsigned missing = 0;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || !member->IsInWorld() || !member->IsAlive() || member->IsBeingTeleported() ||
                member->HasCharmer() || !bot->IsInMap(member) || member->GetGroup() != bot->GetGroup() ||
#ifndef MANGOSBOT_TWO
                member->GetSubGroup() != patient->GetSubGroup() ||
#endif
#ifdef MANGOSBOT_ZERO
                ((name == "arcane brilliance" || name == "prayer of spirit") && member->GetPowerType() != POWER_MANA) ||
#endif
                ai->HasAura(family->first, member) || ai->HasAura(family->second, member) ||
                !ai->CanCastSpell(name, member, 0)) continue;
            if (++missing >= 3) break;
        }
        // Rebuff one or two missing players with the ordinary variant rather
        // than spending a group spell's mana/reagent on an almost-full group.
        if (missing < 3) return false;
    }

    struct Provider { Player* player; int32 strength; };
    std::vector<Provider> providers;
    int32 strongest = -1;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* caster = ref->getSource();
        if (!caster || !caster->IsInWorld() || !caster->IsAlive() || !bot->IsInMap(caster) ||
            caster->IsBeingTeleported() || caster->HasCharmer() || caster->duel || caster->GetGroup() != bot->GetGroup()) continue;
        // Respect an already-started matching player/bot cast, including an
        // area buff whose explicit target is another member of this subgroup.
        Spell* pending = caster->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (caster != bot && pending && pending->m_spellInfo && pending->getState() != SPELL_STATE_FINISHED)
        {
            std::string castName = pending->m_spellInfo->SpellName[0];
            strToLower(castName);
            Unit* explicitTarget = pending->m_targets.getUnitTarget();
            if (castName == family->first || castName == family->second)
            {
                if (explicitTarget == target) return false;
                if (castName == family->second && explicitTarget && explicitTarget->IsPlayer() &&
                    explicitTarget->IsInWorld() && bot->IsInMap(explicitTarget))
                {
                    Player* areaTarget = static_cast<Player*>(explicitTarget);
                    if (areaTarget->GetGroup() == bot->GetGroup() &&
#ifdef MANGOSBOT_TWO
                        true)
#else
                        areaTarget->GetSubGroup() == patient->GetSubGroup())
#endif
                        return false;
                }
            }
        }
        PlayerbotAI* other = caster->GetPlayerbotAI();
        if (!other || other->IsRealPlayer() ||
            (!other->HasStrategy("buff", BotState::BOT_STATE_NON_COMBAT) &&
             !other->HasStrategy("buff", BotState::BOT_STATE_COMBAT))) continue;
        int32 strength = -1;
        for (const char* variant : {family->first, family->second})
        {
            uint32 id = other->GetAiObjectContext()->GetValue<uint32>("spell id", variant)->Get();
            const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
            if (!id || !spell || !caster->HasSpell(id) || IsPassiveSpell(spell) ||
                !other->CanCastSpell(id, target, 0)) continue;
            // Includes native rank and improved-buff talent modifiers, without
            // consuming modifier charges during this planning query.
            strength = std::max(strength, caster->CalculateSpellEffectValue(target, spell, EFFECT_INDEX_0, nullptr, true, false));
        }
        if (strength < 0) continue;
        strongest = std::max(strongest, strength);
        providers.push_back({caster, strength});
    }
    providers.erase(std::remove_if(providers.begin(), providers.end(),
        [strongest](const Provider& provider) { return provider.strength != strongest; }), providers.end());
    if (providers.empty()) return true; // Let native admission reject an unavailable own spell normally.
    std::sort(providers.begin(), providers.end(), [](const Provider& a, const Provider& b) {
        return a.player->GetObjectGuid() < b.player->GetObjectGuid();
    });
    // Equal-capability priests/mages/druids divide raid subgroups. An absent,
    // dead, disabled, out-of-range or resource-blocked provider drops out.
    return providers[patient->GetSubGroup() % providers.size()].player == bot;
}
