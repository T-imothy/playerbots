#pragma once
#include "MovementActions.h"

namespace ai
{
	class ReviveFromCorpseAction : public MovementAction 
    {
	public:
		bool RequiresWorldOwner() const override { return true; }
        ReviveFromCorpseAction(PlayerbotAI* ai) : MovementAction(ai, "revive from corpse") {}
        virtual bool Execute(Event& event) override;
    };

    class FindCorpseAction : public MovementAction 
    {
    public:
        bool RequiresWorldOwner() const override { return true; }
        FindCorpseAction(PlayerbotAI* ai) : MovementAction(ai, "find corpse") {}
        virtual bool Execute(Event& event) override;
        virtual bool isUseful() override;
    };

	class SpiritHealerAction : public MovementAction
    {
	public:
	    bool RequiresWorldOwner() const override { return true; }
        SpiritHealerAction(PlayerbotAI* ai, std::string name = "spirit healer") : MovementAction(ai,name) {}
        virtual bool Execute(Event& event) override;
        virtual bool isUseful() override;
    };
}
