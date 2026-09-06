#pragma once
#include "DungeonTriggers.h"
#include "GenericTriggers.h"

namespace ai
{
    class KarazhanPriorityTargetTrigger : public Trigger
    {
    public:
        KarazhanPriorityTargetTrigger(PlayerbotAI* ai) : Trigger(ai, "karazhan priority target", 1) {}
        bool IsActive() override;
    };

    class AranFlameWreathTrigger : public Trigger
    {
    public:
        AranFlameWreathTrigger(PlayerbotAI* ai) : Trigger(ai, "aran hold position", 1) {}
        bool IsActive() override;
    };
	class KarazhanEnterDungeonTrigger : public EnterDungeonTrigger
	{
	public:
		KarazhanEnterDungeonTrigger(PlayerbotAI* ai) : EnterDungeonTrigger(ai, "enter karazhan", "karazhan", 532) {}
	};

	class KarazhanLeaveDungeonTrigger : public LeaveDungeonTrigger
	{
	public:
		KarazhanLeaveDungeonTrigger(PlayerbotAI* ai) : LeaveDungeonTrigger(ai, "leave karazhan", "karazhan", 532) {}
	};

	class NetherspiteStartFightTrigger : public StartBossFightTrigger
	{
	public:
		NetherspiteStartFightTrigger(PlayerbotAI* ai) : StartBossFightTrigger(ai, "start netherspite fight", "netherspite", 15689) {}
	};

	class NetherspiteEndFightTrigger : public EndBossFightTrigger
	{
	public:
		NetherspiteEndFightTrigger(PlayerbotAI* ai) : EndBossFightTrigger(ai, "end netherspite fight", "netherspite", 15689) {}
	};

	class VoidZoneTooCloseTrigger : public CloseToCreatureHazardTrigger
	{
	public:
		VoidZoneTooCloseTrigger(PlayerbotAI* ai) : CloseToCreatureHazardTrigger(ai, "void zone too close", 16697, 5.0f, 99999999.0f) {}
	};

    class NetherspiteBeamPositionTrigger : public Trigger
	{
	public:
        NetherspiteBeamPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "netherspite beam position", 1) {}
		bool IsActive() override;
	};

	class PrinceMalchezaarStartFightTrigger : public StartBossFightTrigger
	{
	public:
		PrinceMalchezaarStartFightTrigger(PlayerbotAI* ai) : StartBossFightTrigger(ai, "start prince malchezaar fight", "prince malchezaar", 15690) {}
	};

	class PrinceMalchezaarEndFightTrigger : public EndBossFightTrigger
	{
	public:
		PrinceMalchezaarEndFightTrigger(PlayerbotAI* ai) : EndBossFightTrigger(ai, "end prince malchezaar fight", "prince malchezaar", 15690) {}
	};

	class NetherspiteInfernalTooCloseTrigger : public CloseToCreatureTrigger
	{
	public:
		NetherspiteInfernalTooCloseTrigger(PlayerbotAI* ai) : CloseToCreatureTrigger(ai, "netherspite infernal too close", 17646, 21.0f) {}
	};

	class PrinceMalchezaarTooCloseTrigger : public CloseToCreatureTrigger
	{
	public:
		PrinceMalchezaarTooCloseTrigger(PlayerbotAI* ai) : CloseToCreatureTrigger(ai, "prince malchezaar too close", 15690, ai->HasStrategy("ranged", BotState::BOT_STATE_COMBAT) ? 30.0f : 32.0f, false, ai->HasStrategy("ranged", BotState::BOT_STATE_COMBAT) ? 2 : 1)  {}

		bool IsActive() override;

		bool MeleeWaitCheck(Unit* target);

		bool EnfeeblePart();
	};
}
