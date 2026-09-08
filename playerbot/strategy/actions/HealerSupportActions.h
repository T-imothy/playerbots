#pragma once
#include "GenericSpellActions.h"

namespace ai
{
    bool HasHealingPressure(PlayerbotAI* ai, uint32 healthThreshold);
    Unit* SelectHealerSupportTarget(PlayerbotAI* ai, const std::string& spell, float range);

    // Single-target maintained buffs must not be moved every time another
    // party member lacks the aura. The native spell still enforces all limits.
    class CastMaintainedHealerBuffAction : public CastBuffSpellAction
    {
    public:
        CastMaintainedHealerBuffAction(PlayerbotAI* ai, std::string spell) : CastBuffSpellAction(ai, spell) {}
        Unit* GetTarget() override { return SelectHealerSupportTarget(ai, GetSpellName(), range); }
    };

    class CastUrgentHealingBuffAction : public CastBuffSpellAction
    {
    public:
        CastUrgentHealingBuffAction(PlayerbotAI* ai, std::string spell) : CastBuffSpellAction(ai, spell) {}
        bool isUseful() override;
    };

    class CastSelfAndPartyHealingAction : public CastHealingSpellAction
    {
    public:
        CastSelfAndPartyHealingAction(PlayerbotAI* ai, std::string spell) : CastHealingSpellAction(ai, spell) {}
        std::string GetTargetName() override { return "party member to heal"; }
        bool isUseful() override
        {
            return GetTarget() && GetTarget() != bot && bot->GetHealthPercent() < sPlayerbotAIConfig.mediumHealth &&
                CastHealingSpellAction::isUseful();
        }
    };

    // A learned, ready Nature's Swiftness enables this emergency alternative;
    // ordinary heals remain independently available when it is on cooldown.
    class CastNaturesSwiftnessHealAction : public CastHealingSpellAction
    {
    public:
        CastNaturesSwiftnessHealAction(PlayerbotAI* ai, std::string heal, bool party) :
            CastHealingSpellAction(ai, heal), party(party) {}
        std::string getName() override { return party ? "nature's swiftness heal on party" : "nature's swiftness heal"; }
        std::string GetTargetName() override { return party ? "party member to heal" : "self target"; }
        bool isUseful() override;
        NextAction** getPrerequisites() override;
    private:
        bool party;
    };

#ifdef MANGOSBOT_TWO
    class CastHymnOfHopeAction : public CastBuffSpellAction
    {
    public:
        CastHymnOfHopeAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "hymn of hope") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    };

    class StopHymnOfHopeAction : public Action
    {
    public:
        StopHymnOfHopeAction(PlayerbotAI* ai) : Action(ai, "stop hymn of hope") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    };
#endif
}
