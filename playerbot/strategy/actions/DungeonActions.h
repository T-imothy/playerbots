#pragma once
#include "MovementActions.h"
#include "playerbot/strategy/values/HazardsValue.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"


namespace ai
{
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
