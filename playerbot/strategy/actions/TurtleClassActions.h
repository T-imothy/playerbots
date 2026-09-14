#pragma once
#include "GenericSpellActions.h"
#include "UseItemAction.h"
namespace ai
{
    enum class TurtleAbility
    {
        Icicles, ArcaneRupture, MasterStrike, SurpriseAttack, NoxiousAssault,
        SmokeBomb, ShadowOfDeath, MarkForDeath, Enlighten, Ascendance,
        Earthquake, AncestralSwiftness, SpiritLink, LightningStrike,
        TreeOfLife, DarkHarvest, PowerOverwhelming, Carve, Bulwark,
        ArcaneSurge, PainSpike, SearingShot, EarthshakerSlam, SavageBite, FeralBarkskin, LightOfAnshe, Detection, Reshift
    };
    class TurtleClassSpellAction : public CastSpellAction
    {
    public:
        TurtleClassSpellAction(PlayerbotAI* ai, std::string name, TurtleAbility ability)
            : CastSpellAction(ai, name), ability(ability) {}
        bool isUseful() override;
        ActionThreatType getThreatType() override;
    protected:
        std::string GetTargetName() override;
        std::string GetReachActionName() override;
    private:
        bool IsMelee() const;
        TurtleAbility ability;
    };
    class TurtleCreateStoneAction : public CastSpellAction
    {
    public:
        TurtleCreateStoneAction(PlayerbotAI* ai, std::string name) : CastSpellAction(ai, name) {}
        bool isUseful() override;
    protected:
        std::string GetTargetName() override { return "self target"; }
    };
    class TurtleUseStoneAction : public UseItemIdAction
    {
    public:
        TurtleUseStoneAction(PlayerbotAI* ai, std::string stone) : UseItemIdAction(ai, "use " + stone), stone(stone) {}
        bool isUseful() override;
    protected:
        uint32 GetItemId() override;
        Unit* GetTarget() override { return bot; }
    private:
        std::string stone;
    };
}
