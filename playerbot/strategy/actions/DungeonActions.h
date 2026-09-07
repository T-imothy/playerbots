#pragma once
#include "MovementActions.h"
#include "playerbot/strategy/values/VashjCoreValue.h"
#include "AttackAction.h"
#include "GenericSpellActions.h"
#include "UseItemAction.h"
#include "playerbot/strategy/values/HazardsValue.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"


namespace ai
{
    class RotatingBeamAction : public MovementAction
    {
    public:
        RotatingBeamAction(PlayerbotAI* ai) : MovementAction(ai, "avoid rotating beam") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan, encounter::RotatingBeam& beam);
    };
    class VashjCoreAction : public MovementAction
    {
    public:
        VashjCoreAction(PlayerbotAI* ai) : MovementAction(ai, "vashj core relay") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        static bool GetPlan(PlayerbotAI* ai, VashjCorePlan& plan);
    };
    class InnerDemonAction : public CastSpellAction
    {
    public:
        InnerDemonAction(PlayerbotAI* ai);
        std::string getName() override { return "fight own inner demon"; }
        bool isUseful() override;
        bool Execute(Event& event) override;
        static Unit* GetDemon(PlayerbotAI* ai);
    protected:
        Unit* GetTarget() override;
    };
    class EadricRadianceAction : public Action
    {
    public:
        EadricRadianceAction(PlayerbotAI* ai) : Action(ai, "eadric face away") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
        static Unit* GetBoss(PlayerbotAI* ai);
    };
    class MoamManaControlAction : public CastSpellAction
    {
    public:
        MoamManaControlAction(PlayerbotAI* ai);
        std::string getName() override { return "moam mana control"; }
        bool isUseful() override;
        bool Execute(Event& event) override;
    };
    class ViscidusFrostAction : public Action
    {
    public:
        ViscidusFrostAction(PlayerbotAI* ai) : Action(ai, "viscidus frost") {}
        ActionThreatType getThreatType() override { return ActionThreatType::ACTION_THREAT_SINGLE; }
        uint32 GetFrostSpell();
        bool isUseful() override;
        bool Execute(Event& event) override;
    };
    class HeiganDanceAction : public MovementAction
    {
    public:
        HeiganDanceAction(PlayerbotAI* ai) : MovementAction(ai, "heigan dance") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };
    class NajentusSpineAction : public MovementAction
    {
    public:
        NajentusSpineAction(PlayerbotAI* ai) : MovementAction(ai, "najentus spine rescue") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override { return true; }
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };
    class NajentusShieldAction : public UseItemIdAction
    {
    public:
        NajentusShieldAction(PlayerbotAI* ai) : UseItemIdAction(ai, "najentus break shield") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override { return false; }
    protected:
        Unit* GetTarget() override;
        uint32 GetItemId() override { return 32408; }
    };
    class ArchimondeTearsAction : public UseItemIdAction
    {
    public:
        ArchimondeTearsAction(PlayerbotAI* ai) : UseItemIdAction(ai, "archimonde tears") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override { return true; }
    protected:
        uint32 GetItemId() override { return 24494; }
    };
    class LinkedBurstAction : public MovementAction
    {
    public:
        LinkedBurstAction(PlayerbotAI* ai) : MovementAction(ai, "separate linked burst") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };
    class AkilzonStormAction : public MovementAction
    {
    public:
        AkilzonStormAction(PlayerbotAI* ai) : MovementAction(ai, "akilzon storm shelter") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };
    class ColdMovementAction : public JumpAction
    {
    public:
        ColdMovementAction(PlayerbotAI* ai) : JumpAction(ai, "move against cold") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
        bool ShouldReactionInterruptCast() const override;
        uint32 GetColdStacks() const;
    };
    class HakkarPoisonAction : public MovementAction
    {
    public:
        HakkarPoisonAction(PlayerbotAI* ai) : MovementAction(ai, "hakkar acquire poison") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override { return false; }
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };
    class OssirianCrystalAction : public MovementAction
    {
    public:
        OssirianCrystalAction(PlayerbotAI* ai) : MovementAction(ai, "ossirian crystal") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };
    class BossCoverAction : public MovementAction
    {
    public:
        BossCoverAction(PlayerbotAI* ai) : MovementAction(ai, "boss seek cover") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class DungeonAddTargetAction : public AttackAction
    {
    public:
        DungeonAddTargetAction(PlayerbotAI* ai) : AttackAction(ai, "dungeon priority add") {}
        Unit* GetTarget() override;
        bool isUseful() override;
        Unit* GetThekalTarget();
        Unit* GetGluthTarget();
        Unit* GetSummonObjectiveTarget();
        Unit* GetRaidTotemTarget();
        Unit* GetTwinEmperorTarget();
        Unit* GetIcecrownAddTarget();
    };

    class MagtheridonCubeAction : public MovementAction
    {
    public:
        MagtheridonCubeAction(PlayerbotAI* ai) : MovementAction(ai, "magtheridon cube") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool isPossible() override;
        bool ShouldReactionInterruptCast() const override;
        static Unit* GetBoss(PlayerbotAI* ai);
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class GruulSpreadAction : public MovementAction
    {
    public:
        GruulSpreadAction(PlayerbotAI* ai) : MovementAction(ai, "gruul shatter spread") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class BossCastPositionAction : public MovementAction
    {
    public:
        BossCastPositionAction(PlayerbotAI* ai) : MovementAction(ai, "boss cast safe position") {}
        bool Execute(Event& event) override;
        bool isUseful() override;
        bool ShouldReactionInterruptCast() const override;
        static bool GetPlan(PlayerbotAI* ai, EncounterPosition& plan);
    };

    class MoveAwayFromHazard : public MovementAction
    {
    public:
        MoveAwayFromHazard(PlayerbotAI* ai, std::string name = "move away from hazard") : MovementAction(ai, name) {}
        bool Execute(Event& event) override;
        bool isPossible() override;

#ifdef GenerateBotHelp
        virtual std::string GetHelpName() { return "move away from hazard"; }
        virtual std::string GetHelpDescription()
        {
            return "This action makes the bot move away from hazardous areas in dungeons.\n"
                   "It identifies dangerous positions and navigates to a safer location.";
        }
        virtual std::vector<std::string> GetUsedActions() { return {}; }
        virtual std::vector<std::string> GetUsedValues() { return {"hazards"}; }
#endif 

    private:
        bool IsHazardNearby(const WorldPosition& point, const std::list<HazardPosition>& hazards) const;
    };

    class MoveAwayFromCreature : public MovementAction
    {
    public:
        MoveAwayFromCreature(PlayerbotAI* ai, std::string name, uint32 creatureID, float range, bool ignoreVictim = false, bool healersSafe = false) : MovementAction(ai, name), creatureID(creatureID), range(range), ignoreVictim(ignoreVictim), healersSafe(healersSafe) {}
        bool Execute(Event& event) override;
        bool isPossible() override;

#ifdef GenerateBotHelp
        virtual std::string GetHelpName() { return "move away from creature"; }
        virtual std::string GetHelpDescription()
        {
            return "This action makes the bot move away from a specific creature in dungeons.\n"
                   "It maintains a safe distance from the specified creature ID within a defined range.";
        }
        virtual std::vector<std::string> GetUsedActions() { return {}; }
        virtual std::vector<std::string> GetUsedValues() { return {"hazards"}; }
#endif 

    protected:
        bool IsValidPoint(const WorldPosition& point, const std::list<Creature*>& creatures, const std::list<HazardPosition>& hazards);
        bool HasCreaturesNearby(const WorldPosition& point, const std::list<Creature*>& creatures) const;
        bool IsHazardNearby(const WorldPosition& point, const std::list<HazardPosition>& hazards) const;
        bool CreatureSearchHelperFunction(Event& event, uint32 creatureId);
        bool CreatureSearchHelperFunction(Event& event, const std::set<uint32>& creatureIds);

    protected:
        uint32 creatureID;
        float range;
        bool ignoreVictim;
        bool healersSafe;
    };

    class MoveAwayFromSpecificCreatures : public MoveAwayFromCreature
    {
    public:
        MoveAwayFromSpecificCreatures(PlayerbotAI* ai, float range, bool ignoreVictim = true, std::string name = "move away from specific creatures") : MoveAwayFromCreature(ai, name, 0, range, ignoreVictim) {}
        bool Execute(Event& event) override;

#ifdef GenerateBotHelp
        virtual std::string GetHelpName() { return "move away from specific creatures"; }
        virtual std::string GetHelpDescription()
        {
            return "This action makes the bot move away from specific creatures defined by the avoid creature list.\n"
                   "It maintains a safe distance from the specified creature IDs within a defined range.";
        }
        virtual std::vector<std::string> GetUsedActions() { return {}; }
        virtual std::vector<std::string> GetUsedValues() { return {"hazards"}; }
#endif 
    };
}
