#pragma once
#include "playerbot/strategy/triggers/GenericTriggers.h"

namespace ai
{
#ifdef MANGOSBOT_TWO
    class EmpowerRuneWeaponTrigger : public Trigger
    {
    public:
        EmpowerRuneWeaponTrigger(PlayerbotAI* ai) : Trigger(ai, "empower weapon", 2) {}
        bool IsActive() override
        {
            if (!bot->IsInCombat() || !ai->HasSpell("empower rune weapon") || bot->GetPower(POWER_RUNIC_POWER) > 600) return false;
            unsigned depleted = 0;
            for (uint8 rune = 0; rune < 6; ++rune) if (bot->GetRuneCooldown(rune) >= 3000) ++depleted;
            return depleted >= 4 && ai->CanCastSpell("empower rune weapon", bot, 0);
        }
    };
#endif
    
    BUFF_TRIGGER(HornOfWinterTrigger, "horn of winter");
    BUFF_TRIGGER(BoneShieldTrigger, "bone shield");
    BUFF_TRIGGER(ImprovedIcyTalonsTrigger, "improved icy talons");
    class PlagueStrikeDebuffTrigger : public DebuffTrigger
    {
    public:
        PlagueStrikeDebuffTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "blood plague", 1, true) {}
        std::string getName() override { return "plague strike"; }
    };
    class IcyTouchDebuffTrigger : public DebuffTrigger
    {
    public:
        IcyTouchDebuffTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "frost fever", 1, true) {}
        std::string getName() override { return "icy touch"; }
    };

		class PlagueStrikeDebuffOnAttackerTrigger : public DebuffOnAttackerTrigger
	{
	public:
        PlagueStrikeDebuffOnAttackerTrigger(PlayerbotAI* ai) : DebuffOnAttackerTrigger(ai, "blood plague") { checkIsOwner = true; }
        std::string getName() override { return "plague strike on attacker"; }
        Value<Unit*>* GetTargetValue() override { return context->GetValue<Unit*>("attacker without my aura", "blood plague"); }
	};
		class IcyTouchDebuffOnAttackerTrigger : public DebuffOnAttackerTrigger
	{
	public:
        IcyTouchDebuffOnAttackerTrigger(PlayerbotAI* ai) : DebuffOnAttackerTrigger(ai, "frost fever") { checkIsOwner = true; }
        std::string getName() override { return "icy touch on attacker"; }
        Value<Unit*>* GetTargetValue() override { return context->GetValue<Unit*>("attacker without my aura", "frost fever"); }
	};

    class DKPresenceTrigger : public BuffTrigger {
    public:
        DKPresenceTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "blood presence") {}
        virtual bool IsActive() override;
    };

	class BloodTapTrigger : public BuffTrigger {
	public:
		BloodTapTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "blood tap") {}
	};

	class RaiseDeadTrigger : public BuffTrigger {
	public:
		RaiseDeadTrigger(PlayerbotAI* ai) : BuffTrigger(ai, "raise dead") {}
	};


	class RuneStrikeTrigger : public SpellCanBeCastedTrigger {
	public:
		RuneStrikeTrigger(PlayerbotAI* ai) : SpellCanBeCastedTrigger(ai, "rune strike") {}
	};

	class DeathCoilTrigger : public SpellCanBeCastedTrigger {
	public:
		DeathCoilTrigger(PlayerbotAI* ai) : SpellCanBeCastedTrigger(ai, "death coil") {}
	};

	class PestilenceTrigger : public DebuffTrigger {
	public:
		PestilenceTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "pestilence") {}
	};

	class BloodStrikeTrigger : public DebuffTrigger {
	public:
		BloodStrikeTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "blood strike") {}
	};


	class HowlingBlastTrigger : public DebuffTrigger {
	public:
		HowlingBlastTrigger(PlayerbotAI* ai) : DebuffTrigger(ai, "howling blast") {}
	};

    class MindFreezeInterruptSpellTrigger : public InterruptSpellTrigger
    {
    public:
		MindFreezeInterruptSpellTrigger(PlayerbotAI* ai) : InterruptSpellTrigger(ai, "mind freeze") {}
    };

	class StrangulateInterruptSpellTrigger : public InterruptSpellTrigger
	{
	public:
		StrangulateInterruptSpellTrigger(PlayerbotAI* ai) : InterruptSpellTrigger(ai, "strangulate") {}
	};

    class KillingMachineTrigger : public HasAuraTrigger
    {
    public:
        KillingMachineTrigger(PlayerbotAI* ai) : HasAuraTrigger(ai, "killing machine") {}
        bool IsActive() override;
    };

    class MindFreezeOnEnemyHealerTrigger : public InterruptEnemyHealerTrigger
    {
    public:
		MindFreezeOnEnemyHealerTrigger(PlayerbotAI* ai) : InterruptEnemyHealerTrigger(ai, "mind freeze") {}
    };

	class ChainsOfIceSnareTrigger : public SnareTargetTrigger
	{
	public:
		ChainsOfIceSnareTrigger(PlayerbotAI* ai) : SnareTargetTrigger(ai, "chains of ice") {}
	};

	class StrangulateOnEnemyHealerTrigger : public InterruptEnemyHealerTrigger
	{
	public:
		StrangulateOnEnemyHealerTrigger(PlayerbotAI* ai) : InterruptEnemyHealerTrigger(ai, "strangulate") {}
	};

    class AutoRuneForgeTrigger : public Trigger {
    public:
        AutoRuneForgeTrigger(PlayerbotAI* ai) : Trigger(ai, "auto runeforge") {}
        virtual bool IsActive() override {
			if (AI_VALUE2(time_t, "manual time", "next runeforge check") > time(0))
				return false;

            return AI_VALUE(bool, "should runeforge");
        }
    };
}
