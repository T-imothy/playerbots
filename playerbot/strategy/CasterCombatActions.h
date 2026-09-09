#pragma once

#include "CasterCombatPolicy.h"
#include "playerbot/strategy/actions/GenericSpellActions.h"
#include "playerbot/strategy/triggers/GenericTriggers.h"
#include "Entities/GameObject.h"
#include "Entities/Totem.h"
#include "Spells/Spell.h"

namespace ai
{
    // Newly wired abilities retain the normal learned-spell/native cast checks.
    class CasterAbilityAction : public CastSpellAction
    {
    public:
        CasterAbilityAction(PlayerbotAI* ai, const std::string& spell) : CastSpellAction(ai, spell) {}

        ActionThreatType getThreatType() override
        {
            for (const char* utility : {"cyclone", "hex", "psychic horror", "slow", "focus magic", "health funnel", "fel domination",
                "elemental mastery", "demonic empowerment", "demonic circle: summon", "demonic circle: teleport"})
                if (GetSpellName() == utility) return ActionThreatType::ACTION_THREAT_NONE;
            return CastSpellAction::getThreatType();
        }

        std::string GetTargetName() override
        {
            const auto& spell = GetSpellName();
            if ((spell == "cyclone" || spell == "hex") && context->GetValue<Unit*>("cc target", spell)->Get()) return "cc target";
            if (spell == "health funnel" || spell == "demonic empowerment") return "pet target";
            for (const char* self : {"elemental mastery", "fel domination", "immolation aura", "hellfire", "thunderstorm",
                "demonic circle: summon", "demonic circle: teleport", "fire elemental totem", "earth elemental totem"})
                if (spell == self) return "self target";
            return "current target";
        }

        std::string GetTargetQualifier() override { return GetTargetName() == "cc target" ? GetSpellName() : ""; }
        std::string GetReachActionName() override
        {
            // Focus Magic's selection already requires an in-range ally. Escape
            // abilities must never walk toward the threat to become usable.
            for (const char* spell : {"focus magic", "typhoon", "thunderstorm", "shadowflame", "shadow cleave", "demon charge"})
                if (GetSpellName() == spell) return "";
            return CastSpellAction::GetReachActionName();
        }

        Unit* GetTarget() override
        {
            const auto& spell = GetSpellName();
            if (spell == "focus magic")
            {
                if (!bot->GetGroup()) return nullptr;
                for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
                    if (Player* member = ref->getSource())
                        if (member->IsInWorld() && bot->IsInMap(member) && ai->HasMyAura(spell, member)) return nullptr;
                for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
                {
                    Player* member = ref->getSource();
                    if (!member || member == bot || !member->IsAlive() || !member->IsInWorld() || !bot->IsInMap(member)) continue;
                    if (!member->HasMana() || !ai->IsRanged(member) || !bot->IsWithinDistInMap(member, 30.0f) || !bot->IsWithinLOSInMap(member)) continue;
                    if (!ai->HasAura(spell, member)) return member;
                }
                return nullptr;
            }
            if (spell == "cyclone" || spell == "hex")
            {
                Unit* marked = context->GetValue<Unit*>("cc target", spell)->Get();
                if (marked) return marked;
            }
            return CastSpellAction::GetTarget();
        }

        bool isUseful() override
        {
            if (!CastSpellAction::isUseful()) return false;
            const std::string& spell = GetSpellName();
            Unit* target = GetTarget();
            Unit* enemy = context->GetValue<Unit*>("current target")->Get();
            const bool combat = ai->IsStateActive(BotState::BOT_STATE_COMBAT);
            const bool pvp = enemy && enemy->IsPlayer();
            const float mana = bot->GetMaxPower(POWER_MANA) ? 100.0f * bot->GetPower(POWER_MANA) / bot->GetMaxPower(POWER_MANA) : 100.0f;
            if (spell == "focus magic") return !combat && !ai->HasAura(spell, target);
            if (spell == "health funnel")
                return target->IsAlive() && target->GetHealthPercent() < 40.0f && CasterHealthCostSafe(ai, spell);
            if (spell == "fel domination")
                return combat && (!bot->GetPet() || !bot->GetPet()->IsAlive()) && !ai->HasAura(spell, bot) && !CasterCarryingFlag(bot);
            if (spell == "demonic empowerment") return combat && target->IsAlive() && target->IsInCombat();
            if (spell == "elemental mastery") return combat && MeleeCombatTarget(ai, enemy) && !ai->HasAura(spell, bot);
            if (spell == "mind sear") return combat && SafeMeleeTargetCount(ai, 10.0f, target) >= 3;
            if (spell == "arcane barrage")
                return combat && MeleeCombatTarget(ai, target) && (bot->IsMoving() || !CasterSpell(ai, "arcane blast") ||
                    (!bot->IsSpellReady(CasterSpell(ai, "arcane blast")) && !ai->HasAura("missile barrage", bot)));
            if (spell == "slow") return pvp && target->GetVictim() == bot && !target->IsImmobilizedState() && !ai->HasAura(spell, target);
            if (spell == "psychic horror") return pvp && target->GetVictim() == bot && bot->GetHealthPercent() < 60.0f && !target->HasBreakableByDamageCrowdControlAura() && CasterControlAvailable(ai, spell, target);
            if (spell == "cyclone" || spell == "hex")
            {
                if (target->HasBreakableByDamageCrowdControlAura() || ai->HasAura(spell, target) || !CasterControlAvailable(ai, spell, target)) return false;
                if (spell == "hex" && (target->HasAuraType(SPELL_AURA_PERIODIC_DAMAGE) || target->HasAuraType(SPELL_AURA_PERIODIC_LEECH))) return false;
                if (context->GetValue<Unit*>("cc target", spell)->Get() == target) return true;
                return pvp && target->GetVictim() == bot && bot->GetHealthPercent() < 60.0f;
            }
            if (spell == "force of nature") return combat && MeleeCombatTarget(ai, target);
            if (spell == "thunderstorm")
                return combat && (mana < 60.0f || (pvp && CasterUnderAttack(ai))) &&
                    // Do not disrupt dungeon/raid positioning with a knockback.
                    (pvp || SafeMeleeTargetCount(ai, 12.0f) == 0 || bot->HasAura(62132));
            if (spell == "typhoon") return pvp && CasterUnderAttack(ai) && bot->IsWithinDistInMap(target, 20.0f);
            if (spell == "hellfire") return combat && CasterHealthCostSafe(ai, spell) && SafeMeleeTargetCount(ai, 10.0f) >= 4;
            if (spell == "shadowflame") return combat && MeleeCombatTarget(ai, target) && bot->IsWithinDistInMap(target, 8.0f);
            if (spell == "immolation aura") return combat && ai->HasAura("metamorphosis", bot) && !ai->HasAura(spell, bot) && SafeMeleeTargetCount(ai, 8.0f) >= 2;
            if (spell == "shadow cleave") return combat && ai->HasAura("metamorphosis", bot) && SafeMeleeTargetCount(ai, 5.0f) >= 2;
            if (spell == "demon charge")
                return combat && pvp && ai->HasAura("metamorphosis", bot) && !CasterCarryingFlag(bot) &&
                    bot->IsWithinDistInMap(target, 25.0f) && !bot->IsWithinDistInMap(target, 10.0f) && CasterAreaSafe(ai, target, 8.0f);
#ifdef MANGOSBOT_TWO
            if (spell == "demonic circle: summon")
                return combat && pvp && !bot->GetGameObject(48018) && !bot->IsMoving() && !bot->IsFalling() &&
                    !CasterCarryingFlag(bot) && !CasterUnderAttack(ai) && !bot->IsWithinDistInMap(enemy, 20.0f);
            if (spell == "demonic circle: teleport")
            {
                GameObject* circle = bot->GetGameObject(48018);
                return combat && pvp && circle && circle->IsInWorld() && bot->IsInMap(circle) &&
                    !CasterCarryingFlag(bot) && CasterUnderAttack(ai) && bot->IsWithinDistInMap(circle, 40.0f) &&
                    !bot->IsWithinDistInMap(circle, 8.0f) && bot->IsWithinLOSInMap(circle) &&
                    !enemy->IsWithinDistInMap(circle, 15.0f) &&
                    CasterAreaSafe(ai, circle->GetPositionX(), circle->GetPositionY(), circle->GetPositionZ(), 8.0f);
            }
#endif
#ifndef MANGOSBOT_ZERO
            if (spell == "fire elemental totem" || spell == "earth elemental totem")
            {
                if (!combat || !MeleeCombatTarget(ai, enemy)) return false;
                if (spell == "earth elemental totem")
                    return !bot->GetGroup() && bot->GetHealthPercent() < 35.0f && !bot->GetTotem(TOTEM_SLOT_EARTH) && CasterAreaSafe(ai, bot, 20.0f);
                for (const char* manual : {"totem fire nova", "totem fire flametongue", "totem fire resistance", "totem fire magma", "totem fire searing"})
                    if (ai->HasStrategy(manual, BotState::BOT_STATE_COMBAT)) return false;
                return !bot->GetTotem(TOTEM_SLOT_FIRE) && SafeMeleeTargetCount(ai, 20.0f) >= 3 && CasterAreaSafe(ai, bot, 20.0f);
            }
#endif
            return false;
        }

        bool Execute(Event& event) override
        {
            if (!isUseful() || !CastSpellAction::Execute(event)) return false;
            if (GetSpellName() == "hex" || GetSpellName() == "cyclone")
            {
                Unit* target = GetTarget();
                if (target && bot->GetVictim() == target) bot->AttackStop();
                if (bot->GetPet() && bot->GetPet()->GetVictim() == target) bot->GetPet()->AttackStop();
            }
            return true;
        }
    };

    class CasterAbilityTrigger : public Trigger
    {
    public:
        CasterAbilityTrigger(PlayerbotAI* ai, const std::string& spell) : Trigger(ai, spell, 2), spell(spell) {}
        bool IsActive() override { CasterAbilityAction action(ai, spell); return action.isUseful(); }
    private:
        std::string spell;
    };

    class CasterFallbackAction : public CastSpellAction
    {
    public:
        CasterFallbackAction(PlayerbotAI* ai) : CastSpellAction(ai, "caster fallback") {}
        bool isUseful() override
        {
            Unit* target = context->GetValue<Unit*>("current target")->Get();
            if (!MeleeCombatTarget(ai, target)) return false;
            std::vector<std::string> spells;
            switch (bot->getClass())
            {
                case CLASS_MAGE:
                    spells = ai->HasStrategy("arcane", BotState::BOT_STATE_COMBAT) ? std::vector<std::string>{"arcane missiles", "frostbolt", "fireball"} :
                        ai->HasStrategy("fire", BotState::BOT_STATE_COMBAT) ? std::vector<std::string>{"fireball", "frostbolt", "arcane missiles"} : std::vector<std::string>{"frostbolt", "fireball", "arcane missiles"}; break;
                case CLASS_WARLOCK:
                    spells = ai->HasStrategy("destruction", BotState::BOT_STATE_COMBAT) ? std::vector<std::string>{"incinerate", "shadow bolt", "searing pain"} : std::vector<std::string>{"shadow bolt", "incinerate", "searing pain"}; break;
                case CLASS_PRIEST:
                    if (!ai->HasStrategy("shadow", BotState::BOT_STATE_COMBAT)) return false;
                    spells = {"mind flay", "mind blast", "shoot"};
                    if (!ai->HasAura("shadowform", bot)) spells.push_back("smite");
                    break;
                case CLASS_DRUID:
                    if (!ai->HasStrategy("balance", BotState::BOT_STATE_COMBAT)) return false;
#ifdef MANGOSBOT_TWO
                    spells = ai->HasStrategy("balance raid", BotState::BOT_STATE_COMBAT) ? std::vector<std::string>{"starfire", "wrath"} : std::vector<std::string>{"wrath", "starfire"};
#else
                    spells = {"starfire", "wrath"};
#endif
                    break;
                case CLASS_SHAMAN:
                    if (!ai->HasStrategy("elemental", BotState::BOT_STATE_COMBAT)) return false;
                    spells = {"lightning bolt", "flame shock"}; break;
                default: return false;
            }
            for (size_t i = 0; i < spells.size(); ++i)
            {
                SetSpellName(spells[i]);
                if (!CastSpellAction::isUseful() || !ai->CanCastSpell(spells[i], target, 0)) continue;
                return i != 0; // Never replace an already-usable normal filler.
            }
            return false;
        }
        bool Execute(Event& event) override { return isUseful() && CastSpellAction::Execute(event); }
    };

    class CasterFallbackTrigger : public Trigger
    {
    public:
        CasterFallbackTrigger(PlayerbotAI* ai) : Trigger(ai, "caster fallback", 1) {}
        bool IsActive() override { CasterFallbackAction action(ai); return action.isUseful(); }
    };

    class CasterInstantAction : public CastSpellAction
    {
    public:
        CasterInstantAction(PlayerbotAI* ai) : CastSpellAction(ai, "caster instant spell") {}
        bool isUseful() override
        {
            if (!ai->HasAura("presence of mind", bot)) return false;
            Unit* target = context->GetValue<Unit*>("current target")->Get();
            if (!MeleeCombatTarget(ai, target)) return false;
            for (const char* spell : {"arcane blast", "fireball", "frostbolt"})
            {
                SetSpellName(spell);
                if (CastSpellAction::isUseful() && ai->CanCastSpell(spell, target, 0)) return true;
            }
            return false;
        }
        bool Execute(Event& event) override { return isUseful() && CastSpellAction::Execute(event); }
    };

    class CasterRecoverPetAction : public CastSpellAction
    {
    public:
        CasterRecoverPetAction(PlayerbotAI* ai) : CastSpellAction(ai, "recover demon") {}
        std::string GetTargetName() override { return "self target"; }
        bool isUseful() override
        {
            if ((bot->GetPet() && bot->GetPet()->IsAlive()) || !ai->HasAura("fel domination", bot) || CasterCarryingFlag(bot)) return false;
            std::vector<std::string> pets{"felguard", "felhunter", "succubus", "voidwalker", "imp"};
            for (const auto& pet : pets)
                if (ai->HasStrategy("pet " + pet, BotState::BOT_STATE_COMBAT)) { pets = {pet}; break; }
            for (const auto& pet : pets)
            {
                SetSpellName("summon " + pet);
                if (CastSpellAction::isUseful() && ai->CanCastSpell(GetSpellName(), bot, 0)) return true;
            }
            return false;
        }
        bool Execute(Event& event) override { return isUseful() && CastSpellAction::Execute(event); }
    };

    class CasterProcTrigger : public Trigger
    {
    public:
        CasterProcTrigger(PlayerbotAI* ai, const std::string& proc) : Trigger(ai, proc, 1) {}
        bool IsActive() override
        {
            if (name == "recover demon") { CasterRecoverPetAction action(ai); return action.isUseful(); }
            if (name == "caster instant spell") { CasterInstantAction action(ai); return action.isUseful(); }
#ifdef MANGOSBOT_TWO
            // Check active proc IDs, not same-name passive talent auras.
            if (name == "caster decimation") return bot->HasAura(63165) || bot->HasAura(63167);
            if (name == "caster molten core") return bot->HasAura(47383) || bot->HasAura(71162) || bot->HasAura(71165);
#endif
            return false;
        }
    };

    class CasterStopHealthChannelAction : public Action
    {
    public:
        CasterStopHealthChannelAction(PlayerbotAI* ai) : Action(ai, "stop unsafe health channel") {}
        bool isUseful() override
        {
            Spell* current = bot->GetCurrentSpell(CURRENT_CHANNELED_SPELL);
            if (!current) return false;
            uint32 id = current->m_spellInfo->Id;
            if (id == CasterSpell(ai, "hellfire")) return bot->GetHealthPercent() < 65.0f || CasterUnderAttack(ai) || !CasterSpellAreaSafe(ai, "hellfire", bot);
            if (id == CasterSpell(ai, "health funnel"))
                return bot->GetHealthPercent() < 60.0f || CasterUnderAttack(ai) || !bot->GetPet() || !bot->GetPet()->IsAlive() || bot->GetPet()->GetHealthPercent() >= 85.0f;
            return false;
        }
        bool Execute(Event&) override
        {
            if (!isUseful()) return false;
            uint32 id = bot->GetCurrentSpell(CURRENT_CHANNELED_SPELL)->m_spellInfo->Id;
            bot->InterruptSpell(CURRENT_CHANNELED_SPELL);
            ai->SpellInterrupted(id);
            return true;
        }
    };

    class CasterStopHealthChannelTrigger : public Trigger
    {
    public:
        CasterStopHealthChannelTrigger(PlayerbotAI* ai) : Trigger(ai, "stop unsafe health channel", 1) {}
        bool IsActive() override { CasterStopHealthChannelAction action(ai); return action.isUseful(); }
    };
}
