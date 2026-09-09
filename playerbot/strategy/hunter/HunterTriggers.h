#pragma once

#include "playerbot/strategy/triggers/GenericTriggers.h"
#include "HunterCombatPolicy.h"

namespace ai
{
#ifdef MANGOSBOT_TWO
    // Native CheckCast supplies the execute-health, range and cooldown rules.
    CAN_CAST_TRIGGER(KillShotTrigger, "kill shot");
#endif
    HAS_AURA_TRIGGER_TIME(FeignDeathTrigger, "feign death", 2);

    BEGIN_TRIGGER(HunterNoStingsActiveTrigger, Trigger)
    END_TRIGGER()

    class AspectOfTheHawkTrigger : public BuffTrigger
    {
    public:
        AspectOfTheHawkTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the hawk") {}
        bool IsActive() override { return BuffTrigger::IsActive() && !HunterWantsViper(ai); }
    };

    class AspectOfTheWildTrigger : public BuffTrigger
    {
    public:
        AspectOfTheWildTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the wild") {}
    };

    class AspectOfTheViperTrigger : public BuffTrigger
    {
    public:
        AspectOfTheViperTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the viper") {}
    };

    class AspectOfThePackTrigger : public BuffTrigger
    {
    public:
        AspectOfThePackTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the pack") {}
    };

    class AspectOfTheMonkeyTrigger : public BuffTrigger
    {
    public:
        AspectOfTheMonkeyTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the monkey") {}
    };

    class AspectOfTheBeastTrigger : public BuffTrigger
    {
    public:
        AspectOfTheBeastTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the beast") {}
    };

    class AspectOfTheCheetahTrigger : public BuffTrigger
    {
    public:
        AspectOfTheCheetahTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the cheetah") {}
    };

    class AspectOfTheDragonhawkTrigger : public BuffTrigger
    {
    public:
        AspectOfTheDragonhawkTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "aspect of the dragonhawk") {}
    
        bool IsActive() override
        {
            return BuffTrigger::IsActive() && !HunterWantsViper(ai);
        }
    };

    BEGIN_TRIGGER(HuntersPetDeadTrigger, Trigger)
    END_TRIGGER()

    BEGIN_TRIGGER(HuntersPetLowHealthTrigger, Trigger)
    END_TRIGGER()

    class BlackArrowTrigger : public DebuffTrigger
    {
    public:
        BlackArrowTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "black arrow") {}
    };

    SNARE_TRIGGER(BlackArrowSnareTrigger, "black arrow");

    class HuntersMarkTrigger : public DebuffTrigger
    {
    public:
        HuntersMarkTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "hunter's mark") {}
    };

    class FreezingTrapTrigger : public HasCcTargetTrigger
    {
    public:
        FreezingTrapTrigger(PlayerbotAI* ai) : HasCcTargetTrigger(ai, "freezing trap") {}

#ifdef MANGOSBOT_ZERO
        bool IsActive() override
        {
            // Check if feign death not on cooldown
            if (sServerFacade.IsSpellReady(bot, 5384))
            {
                return HasCcTargetTrigger::IsActive();
            }

            return false;
        }
#endif
    };

    class FrostTrapTrigger : public MeleeLightAoeTrigger
    {
    public:
        FrostTrapTrigger(PlayerbotAI* ai, std::string spell = "frost trap") : MeleeLightAoeTrigger(ai)
        {
            trapName = spell;
        }

        bool IsActive() override
        {
#ifdef MANGOSBOT_ZERO
            // Check if feign death not on cooldown
            if (!sServerFacade.IsSpellReady(bot, 5384))
            {
                return false;
            }
#endif

            const uint32 spellId = HunterSpell(ai, trapName);
            return spellId && ai->HasSpell(spellId) && sServerFacade.IsSpellReady(bot, spellId) && MeleeLightAoeTrigger::IsActive();
        }

    private:
        std::string trapName;
    };

    class ExplosiveTrapTrigger : public RangedMediumAoeTrigger
    {
    public:
        ExplosiveTrapTrigger(PlayerbotAI* ai, std::string spell = "explosive trap") : RangedMediumAoeTrigger(ai)
        {
            trapName = spell;
        }

        bool IsActive() override
        {
#ifdef MANGOSBOT_ZERO
            // Check if feign death not on cooldown
            if (!sServerFacade.IsSpellReady(bot, 5384))
            {
                return false;
            }
#endif

            const uint32 spellId = HunterSpell(ai, trapName);
            return spellId && ai->HasSpell(spellId) && sServerFacade.IsSpellReady(bot, spellId) && RangedMediumAoeTrigger::IsActive();
        }

    private:
        std::string trapName;
    };

    class RapidFireTrigger : public BuffTrigger
    {
    public:
        RapidFireTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "rapid fire") {}
        bool IsActive() override { return BuffTrigger::IsActive() && HunterInShotRange(ai, AI_VALUE(Unit*, "current target")); }
    };

    class TrueshotAuraTrigger : public BuffTrigger
    {
    public:
        TrueshotAuraTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "trueshot aura") {}
    };

    class SerpentStingOnAttackerTrigger : public DebuffOnAttackerTrigger
    {
    public:
        SerpentStingOnAttackerTrigger(PlayerbotAI* ai) : DebuffOnAttackerTrigger(ai, "serpent sting") {}
        virtual bool IsActive() override;
    };

    class ViperStingOnAttackerTrigger : public DebuffOnAttackerTrigger
    {
    public:
        ViperStingOnAttackerTrigger(PlayerbotAI* ai) : DebuffOnAttackerTrigger(ai, "viper sting") {}
        virtual bool IsActive() override;
    };

    BEGIN_TRIGGER(HunterPetNotHappy, Trigger)
    END_TRIGGER()

    class ConsussiveShotSnareTrigger : public SnareTargetTrigger
    {
    public:
        ConsussiveShotSnareTrigger(PlayerbotAI* ai) : SnareTargetTrigger(ai, "concussive shot") {}
    };

    SNARE_TRIGGER(ScatterShotSnareTrigger, "scatter shot");

    class ScareBeastTrigger : public HasCcTargetTrigger
    {
    public:
        ScareBeastTrigger(PlayerbotAI* ai) : HasCcTargetTrigger(ai, "scare beast") {}
    };

    class HunterLowAmmoTrigger : public AmmoCountTrigger
    {
    public:
        HunterLowAmmoTrigger(PlayerbotAI* ai) : AmmoCountTrigger(ai, "ammo", 1, 30) {}
        virtual bool IsActive() override { return bot->GetGroup() && (AI_VALUE2(uint32, "item count", "ammo") < 100) && (AI_VALUE2(uint32, "item count", "ammo") > 0); }
    };

    class HunterNoAmmoTrigger : public Trigger
    {
    public:
        HunterNoAmmoTrigger(PlayerbotAI* ai) : Trigger(ai, "no ammo", 3) {}
        bool IsActive() override { return !HunterAmmoReady(ai) && HunterAmmoReserve(ai); }
    };
    class HunterHasAmmoTrigger : public AmmoCountTrigger
    {
    public:
        HunterHasAmmoTrigger(PlayerbotAI* ai) : AmmoCountTrigger(ai, "ammo", 1, 10) {}
        virtual bool IsActive() override { return HunterAmmoReady(ai); }
    };

    class SwitchToRangedTrigger : public Trigger
    {
    public:
        SwitchToRangedTrigger(PlayerbotAI* ai) : Trigger(ai, "switch to ranged", 1) {}
        bool IsActive() override
        {
            Unit* target = AI_VALUE(Unit*, "current target");
            return ai->HasStrategy("close", BotState::BOT_STATE_COMBAT) && HunterAmmoReady(ai) &&
                MeleeCombatTarget(ai, target) && (HunterInShotRange(ai, target, 1.0f) ||
                target->GetVictim() != bot || target->IsImmobilizedState());
        }
    };

    class SwitchToMeleeTrigger : public Trigger
    {
    public:
        SwitchToMeleeTrigger(PlayerbotAI* ai) : Trigger(ai, "switch to melee", 1) {}
        bool IsActive() override
        {
            Unit* target = AI_VALUE(Unit*, "current target");
            if (!ai->HasStrategy("ranged", BotState::BOT_STATE_COMBAT) || !MeleeCombatTarget(ai, target)) return false;
            if (!HunterAmmoReady(ai)) return !HunterAmmoReserve(ai);
            const auto bounds = HunterShotRange(ai, target);
            return target->GetVictim() == bot && !target->IsImmobilizedState() &&
                target->GetSpeed(MOVE_RUN) > bot->GetSpeed(MOVE_RUN) * 0.5f &&
                bot->GetDistance(target, true, DIST_CALC_NONE) < bounds.first * bounds.first;
        }
    };

    CAN_CAST_TRIGGER(ChimeraShotCanCastTrigger, "chimera shot");
    CAN_CAST_TRIGGER(ExplosiveShotCanCastTrigger, "explosive shot");
    CAN_CAST_TRIGGER(MultishotCanCastTrigger, "multi-shot");
    CAN_CAST_TRIGGER(SteadyShotCanCastTrigger, "steady shot");
    CAN_CAST_TRIGGER(ArcaneShotTrigger, "arcane shot");
#ifdef MANGOSBOT_TWO
    BOOST_TRIGGER(KillCommandBoostTrigger, "kill command");
#else
    CAN_CAST_TRIGGER(KillCommandBoostTrigger, "kill command");
#endif
    SNARE_TRIGGER(IntimidationSnareTrigger, "intimidation");
    CAN_CAST_TRIGGER(CounterattackCanCastTrigger, "counterattack");
    SNARE_TRIGGER(WybernStingSnareTrigger, "wyvern sting");
    CAN_CAST_TRIGGER(MongooseBiteCastTrigger, "mongoose bite");
    BOOST_TRIGGER(BestialWrathBoostTrigger, "bestial wrath");

    INTERRUPT_TRIGGER(SilencingShotInterruptTrigger, "silencing shot");
    INTERRUPT_HEALER_TRIGGER(SilencingShotInterruptHealerTrigger, "silencing shot");

    class ViperStingTrigger : public DebuffTrigger
    {
    public:
        ViperStingTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "viper sting") {}

        virtual bool IsActive() override
        {
            return DebuffTrigger::IsActive() && AI_VALUE2(bool, "has mana", "current target") &&
                AI_VALUE2(uint8, "mana", "current target") >= 10;
        }
    };

    class AimedShotTrigger : public Trigger
    {
    public:
        AimedShotTrigger(PlayerbotAI* ai) : Trigger(ai, "aimed shot", 1) {}
        bool IsActive() override
        {
            Unit* target = AI_VALUE(Unit*, "current target");
            if (!MeleeCombatTarget(ai, target) || !HunterAmmoReady(ai)) return false;
#ifndef MANGOSBOT_TWO
            if (sServerFacade.isMoving(bot) || (target->GetVictim() == bot && !target->IsImmobilizedState())) return false;
#endif
            return ai->CanCastSpell("aimed shot", target, 0);
        }
    };

    class HunterNoPet : public Trigger
    {
    public:
        HunterNoPet(PlayerbotAI* ai) : Trigger(ai, "no pet", 3) {}
        bool IsActive() override
        {
            return !bot->GetPet() && !AI_VALUE2(bool, "mounted", "self target") &&
                ai->CanCastSpell("call pet", bot, 0);
        }
    };

    class HunterActionReadyTrigger : public Trigger
    {
    public:
        HunterActionReadyTrigger(PlayerbotAI* ai, std::string key) : Trigger(ai, key, 1), key(key) {}
        bool IsActive() override
        {
            Action* action = context->GetAction(key);
            return action && action->isUseful() && action->isPossible();
        }
    private:
        std::string key;
    };

    class HunterViperRecoveryTrigger : public Trigger
    {
    public:
        HunterViperRecoveryTrigger(PlayerbotAI* ai) : Trigger(ai, "hunter recover mana", 2) {}
        bool IsActive() override { return HunterWantsViper(ai) && !ai->HasAura("aspect of the viper", bot); }
    };

    class HunterAmmoExhaustedTrigger : public Trigger
    {
    public:
        HunterAmmoExhaustedTrigger(PlayerbotAI* ai) : Trigger(ai, "hunter ammo exhausted", 30) {}
        bool IsActive() override { return bot->GetWeaponForAttack(RANGED_ATTACK) && !HunterAmmoReady(ai) && !HunterAmmoReserve(ai); }
    };

    class StealthedNearbyTrigger : public Trigger 
    {
    public:
        StealthedNearbyTrigger(PlayerbotAI* ai) : Trigger(ai, "stealthed nearby", 5) {}
        virtual bool IsActive() override
        {
            if (!bot->HasSpell(1543))
                return false;

            Unit* target = AI_VALUE(Unit*, "nearest stealthed unit");
            return target;
        }
    };
}

