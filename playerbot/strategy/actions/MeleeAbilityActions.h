#pragma once
#include "GenericActions.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"

namespace ai
{
    class CastSafeMeleeAreaAction : public CastSpellAction
    {
    public:
        CastSafeMeleeAreaAction(PlayerbotAI* ai, const char* spell, float radius, unsigned targets = 1)
            : CastSpellAction(ai, spell), radius(radius), targets(targets) {}
        bool isUseful() override
        {
            if (!ai->IsStateActive(BotState::BOT_STATE_COMBAT) || !CastSpellAction::isUseful() ||
                SafeMeleeTargetCount(ai, radius) < targets) return false;
            Unit* enemy = AI_VALUE(Unit*, "current target");
            if (!MeleeCombatTarget(ai, enemy)) return false;
            const SpellEntry* spell = sServerFacade.LookupSpellInfo(GetDecisionSpellId());
            if (ShouldAvoidEncounterOffense(bot, bot, spell, enemy)) return false;
            for (Aura* aura : enemy->GetAurasByType(SPELL_AURA_DAMAGE_SHIELD))
                if (aura->GetModifier()->m_amount >= bot->GetMaxHealth() * 0.10f) return false;
            return true;
        }
        bool Execute(Event& event) override { return isUseful() && CastSpellAction::Execute(event); }
        ActionThreatType getThreatType() override { return ActionThreatType::ACTION_THREAT_AOE; }
    protected:
        std::string GetTargetName() override { return "self target"; }
        float radius;
        unsigned targets;
    };

#ifndef MANGOSBOT_ZERO
    class CastShamanisticRageAction : public CastBuffSpellAction
    {
    public:
        CastShamanisticRageAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "shamanistic rage") {}
        bool isUseful() override
        {
            return MeleeOpportunity(ai) && AI_VALUE2(uint8, "mana", "self target") < 50 &&
                CastBuffSpellAction::isUseful();
        }
    };

    class CastMaimAction : public CastMeleeSpellAction
    {
    public:
        CastMaimAction(PlayerbotAI* ai) : CastMeleeSpellAction(ai, "maim") {}
        bool isUseful() override
        {
            Unit* target = GetTarget();
            // Spend combo points for an actual interrupt, not a damage finisher.
            return MeleeCombatTarget(ai, target) && target->IsNonMeleeSpellCasted(false) &&
                bot->GetComboTargetGuid() == target->GetObjectGuid() && bot->GetComboPoints() &&
                !target->HasAuraType(SPELL_AURA_MOD_STUN) && CastMeleeSpellAction::isUseful();
        }
    };

    class CastDeadlyThrowAction : public CastSpellAction
    {
    public:
        CastDeadlyThrowAction(PlayerbotAI* ai) : CastSpellAction(ai, "deadly throw") {}
        bool isUseful() override
        {
            Unit* target = GetTarget();
            return MeleeCombatTarget(ai, target) && !bot->CanReachWithMeleeAttack(target) &&
                bot->GetComboTargetGuid() == target->GetObjectGuid() && bot->GetComboPoints() &&
                !target->HasAuraType(SPELL_AURA_MOD_DECREASE_SPEED) && CastSpellAction::isUseful();
        }
    };

    class CastShivAction : public CastMeleeSpellAction
    {
    public:
        CastShivAction(PlayerbotAI* ai) : CastMeleeSpellAction(ai, "shiv") {}
        bool isUseful() override
        {
            Unit* target = GetTarget();
            if (!MeleeCombatTarget(ai, target) || !CastMeleeSpellAction::isUseful()) return false;
            Item* weapon = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND);
            const auto enchant = weapon ? sSpellItemEnchantmentStore.LookupEntry(weapon->GetEnchantmentId(TEMP_ENCHANTMENT_SLOT)) : nullptr;
            if (!enchant) return false;
            for (unsigned i = 0; i < 3; ++i)
            {
                const SpellEntry* poison = sServerFacade.LookupSpellInfo(enchant->spellid[i]);
                if (!poison || poison->Dispel != DISPEL_POISON) continue;
                std::string name = poison->SpellName[0];
                strToLower(name);
                if (name.find("crippling poison") != std::string::npos &&
                    !target->HasAuraType(SPELL_AURA_MOD_DECREASE_SPEED)) return true;
                if (name.find("mind-numbing poison") != std::string::npos && target->IsNonMeleeSpellCasted(false) &&
                    !ai->HasAura("mind-numbing poison", target)) return true;
                if (name.find("wound poison") != std::string::npos && target->IsPlayer() &&
                    !ai->HasAura("wound poison", target)) return true;
            }
            return false;
        }
    };
#endif

#ifdef MANGOSBOT_TWO
    class CastMaelstromLightningAction : public CastSpellAction
    {
    public:
        CastMaelstromLightningAction(PlayerbotAI* ai) : CastSpellAction(ai, "lightning bolt") {}
        bool isUseful() override
        {
            Aura* proc = ai->GetAura(53817, bot);
            return proc && proc->GetStackAmount() >= 5 && CastSpellAction::isUseful();
        }
        bool Execute(Event& event) override { return isUseful() && CastSpellAction::Execute(event); }
    };

    class CastShadowDanceAction : public CastBuffSpellAction
    {
    public:
        CastShadowDanceAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "shadow dance") {}
        bool isUseful() override
        {
            return MeleeOpportunity(ai) && !ai->HasAura("stealth", bot) &&
                bot->GetPower(POWER_ENERGY) >= 60 && bot->GetComboPoints() <= 2 &&
                (ai->HasSpell("ambush") || ai->HasSpell("garrote") || ai->HasSpell("cheap shot")) &&
                CastBuffSpellAction::isUseful();
        }
    };

    class CastShadowDanceOpenerAction : public CastMeleeSpellAction
    {
    public:
        CastShadowDanceOpenerAction(PlayerbotAI* ai) : CastMeleeSpellAction(ai, "ambush") {}
        bool isUseful() override
        {
            Unit* target = GetTarget();
            if (!ai->HasAura("shadow dance", bot) || !MeleeCombatTarget(ai, target) || bot->GetComboPoints() >= 5)
                return false;
            // Native checks choose an available opener, including facing,
            // weapon requirements, immunity, energy and the Dance aura.
            for (const char* spell : { "ambush", "garrote", "cheap shot" })
            {
                if (ai->HasAura(spell, target)) continue;
                if (ai->CanCastSpell(spell, target, 0))
                {
                    SetSpellName(spell);
                    return CastMeleeSpellAction::isUseful();
                }
            }
            return false;
        }
        bool Execute(Event& event) override { return isUseful() && CastMeleeSpellAction::Execute(event); }
    };

    class CastHysteriaAction : public CastBuffSpellAction
    {
    public:
        CastHysteriaAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "hysteria") {}
        bool isUseful() override
        {
            // Conservative self-use: never impose the health drain on a player.
            return ai->HasStrategy("boost", BotState::BOT_STATE_COMBAT) && MeleeOpportunity(ai) && AI_VALUE2(uint8, "health", "self target") >= 90 &&
                !ai->IsTank(bot) && CastBuffSpellAction::isUseful();
        }
    };

    class CastLichborneAction : public CastBuffSpellAction
    {
    public:
        CastLichborneAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "lichborne") {}
        bool isUsefulWhenStunned() override { return true; }
        bool isUseful() override
        {
            return (bot->HasAuraType(SPELL_AURA_MOD_FEAR) || bot->HasAuraType(SPELL_AURA_MOD_CHARM) ||
                bot->HasAuraType(SPELL_AURA_MOD_CONFUSE)) && CastBuffSpellAction::isUseful();
        }
    };
#endif
}
