#pragma once
#include "DungeonTriggers.h"
#include "GenericTriggers.h"
#include "playerbot/strategy/actions/MechanarDungeonActions.h"

namespace ai
{
    class PathaleonAddsTrigger : public Trigger
    {
    public:
        PathaleonAddsTrigger(PlayerbotAI* ai) : Trigger(ai, "pathaleon attack adds", 1) {}
        bool IsActive() override { PathaleonAddsAction action(ai); return action.isUseful(); }
    };
    class MechanarPositionTrigger : public Trigger
    {
    public:
        MechanarPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "mechanar safe position", 1) {}
        bool IsActive() override { MechanarPositionAction action(ai); return action.isUseful(); }
    };
	class MechanarEnterDungeonTrigger : public EnterDungeonTrigger
	{
	public:
		MechanarEnterDungeonTrigger(PlayerbotAI* ai) : EnterDungeonTrigger(ai, "enter mechanar", "mechanar", 554) {}
	};

	class MechanarLeaveDungeonTrigger : public LeaveDungeonTrigger
	{
	public:
		MechanarLeaveDungeonTrigger(PlayerbotAI* ai) : LeaveDungeonTrigger(ai, "leave mechanar", "mechanar", 554) {}
	};

	class NethermancerSepethreaStartFightTrigger : public StartBossFightTrigger
	{
	public:
		NethermancerSepethreaStartFightTrigger(PlayerbotAI* ai) : StartBossFightTrigger(ai, "start nethermancer sepethrea fight", "nethermancer sepethrea", 19221) {}
	};

	class NethermancerSepethreaEndFightTrigger : public EndBossFightTrigger
	{
	public:
		NethermancerSepethreaEndFightTrigger(PlayerbotAI* ai) : EndBossFightTrigger(ai, "end nethermancer sepethrea fight", "nethermancer sepethrea", 19221) {}
	};

	class RagingFlamesTooCloseTrigger : public CloseToCreatureTrigger
	{
	public:
		RagingFlamesTooCloseTrigger(PlayerbotAI* ai) : CloseToCreatureTrigger(ai, "raging flames too close", 20481, 15.0f, true) {}
	};
}
