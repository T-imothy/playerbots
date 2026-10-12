
#include "playerbot/playerbot.h"
#include "KarazhanDungeonStrategies.h"
#include "DungeonMultipliers.h"

using namespace ai;

void KarazhanDungeonStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("karazhan priority target",
        NextAction::array(0, new NextAction("karazhan priority target", 90.0f), NULL)));
    triggers.push_back(new TriggerNode("aran hold position",
        NextAction::array(0, new NextAction("aran hold position", 110.0f), NULL)));
	triggers.push_back(new TriggerNode(
		"start netherspite fight",
		NextAction::array(0, new NextAction("enable netherspite fight strategy", 100.0f), NULL)));

	triggers.push_back(new TriggerNode(
		"start prince malchezaar fight",
		NextAction::array(0, new NextAction("enable prince malchezaar fight strategy", 100.0f), NULL)));
}

void KarazhanDungeonStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode("aran hold position",
        NextAction::array(0, new NextAction("aran hold position", 110.0f), NULL)));
}

void KarazhanDungeonStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveKarazhanTargetMultiplier(ai));
    multipliers.push_back(new PreserveAranFlameWreathMultiplier(ai));
}

void KarazhanDungeonStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveAranFlameWreathMultiplier(ai));
}

void NetherspiteFightStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"void zone too close",
		NextAction::array(0, new NextAction("move away from void zone", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "netherspite beam position",
        NextAction::array(0, new NextAction("netherspite beam position", 90.0f), NULL)));
}

void NetherspiteFightStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new PreserveNetherspitePositionMultiplier(ai));
}

void NetherspiteFightStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"end netherspite fight",
		NextAction::array(0, new NextAction("disable netherspite fight strategy", 100.0f), NULL)));
}

void NetherspiteFightStrategy::InitDeadTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"end netherspite fight",
		NextAction::array(0, new NextAction("disable netherspite fight strategy", 100.0f), NULL)));
}

void PrinceMalchezaarFightStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"netherspite infernal too close",
		NextAction::array(0, new NextAction("move away from netherspite infernal", 100.0f), NULL)));
		
	triggers.push_back(new TriggerNode(
		"prince malchezaar too close",
		NextAction::array(0, new NextAction("move away from prince malchezaar", 100.0f), NULL)));
}

void PrinceMalchezaarFightStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"end prince malchezaar fight",
		NextAction::array(0, new NextAction("disable prince malchezaar fight strategy", 100.0f), NULL)));
}

void PrinceMalchezaarFightStrategy::InitDeadTriggers(std::list<TriggerNode*>& triggers)
{
	triggers.push_back(new TriggerNode(
		"end prince malchezaar fight",
		NextAction::array(0, new NextAction("disable prince malchezaar fight strategy", 100.0f), NULL)));
}


void ShadeOfAranFightStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "shade of aran casting flame wreath",
        NextAction::array(0, new NextAction("start aran fire phase", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "shade of aran casting arcane explosion",
        NextAction::array(0, new NextAction("start aran arcane phase", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "shade of aran elementals out",
        NextAction::array(0, new NextAction("start aran elementals", 100.0f), NULL)));
}

void ShadeOfAranFightStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "end shade of aran fight",
        NextAction::array(0, new NextAction("disable shade of aran fight strategy", 100.0f), NULL)));
}

void ShadeOfAranFightStrategy::InitDeadTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "end shade of aran fight",
        NextAction::array(0, new NextAction("disable shade of aran fight strategy", 100.0f), NULL)));
}

void ShadeOfAranFightStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "shade of aran casting blizzard",
        NextAction::array(0, new NextAction("start aran frost phase", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "shade of aran done casting arcane explosion",
        NextAction::array(0, new NextAction("end aran arcane phase", 100.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "shade of aran casting arcane explosion",
        NextAction::array(0, new NextAction("move away from shade of aran", 100.0f), NULL)));
}

void ShadeOfAranFightStrategy::OnStrategyAdded(BotState state)
{
    if (!Get(ai)->GetBossGuid())
    {
        // Find Shade of aran and store him
        std::list<Unit*> creatures;
        MaNGOS::AllCreaturesOfEntryInRangeCheck u_check(ai->GetBot(), 16524, 100);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(creatures, u_check);
        Cell::VisitAllObjects(ai->GetBot(), searcher, 100);

        if (creatures.empty())
            return;

        Unit* target = creatures.front();

        ShadeOfAranFightStrategy* strategy = ShadeOfAranFightStrategy::Get(ai);
        if (strategy)
        {
            if (target && target->GetEntry() == 16524)
            {
                strategy->SetBossGuid(target->GetObjectGuid());
                // fight starts with unknown phase
                strategy->SetPhase(AranPhase::PHASE_NONE);
                strategy->SetRangedBot(ai->IsRanged(ai->GetBot()));
                if (target->GetHealthPercent() <= 40.0f && !strategy->GetElementals())
                    strategy->SetElementals(true);
                else
                    strategy->SetElementals(false);
                if (ai->GetRange("flee") < 5.0f)
                    ai->GetAiObjectContext()->GetValue<float>("range", "flee")->Set(20.0f);

            }
        }
    }
}

void BigBadWolfFightStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "big bad wolf too close",
        NextAction::array(0, new NextAction("move away from big bad wolf", 100.0f), NULL)));
}

void BigBadWolfFightStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "end big bad wolf fight",
        NextAction::array(0, new NextAction("disable big bad wolf fight strategy", 100.0f), NULL)));
}

void BigBadWolfFightStrategy::InitDeadTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "end big bad wolf fight",
        NextAction::array(0, new NextAction("disable big bad wolf fight strategy", 100.0f), NULL)));
}
