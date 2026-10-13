
#include "playerbot/playerbot.h"
#include "CombatStrategy.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/actions/GenericSpellActions.h"
#include "playerbot/strategy/actions/BotCommandAccess.h"

using namespace ai;

void CombatStrategy::InitCombatTriggers(std::list<TriggerNode*> &triggers)
{
    triggers.push_back(new TriggerNode(
        "invalid target",
        NextAction::array(0, new NextAction("select new target", 89.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "mounted",
        NextAction::array(0, new NextAction("check mount state", 88.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "combat stuck",
        NextAction::array(0, new NextAction("unstuck", 0.7f), NULL)));

    triggers.push_back(new TriggerNode(
        "combat long stuck",
        NextAction::array(0, new NextAction("unstuck", 0.9f), NULL)));

    triggers.push_back(new TriggerNode(
        "often",
        NextAction::array(0, new NextAction("use trinket", 50.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "very often",
        NextAction::array(0, new NextAction("use lightwell", 80.0f), NULL)));
}

float AvoidAoeStrategyMultiplier::GetValue(Action* action)
{
    if (!action)
        return 1.0f;

    std::string name = action->getName();
    if (name == "follow" || name == "co" || name == "nc" || name == "react" || name == "select new target" || name == "flee")
        return 1.0f;

    uint32 spellId = AI_VALUE2(uint32, "spell id", name);
    const SpellEntry* const pSpellInfo = sServerFacade.LookupSpellInfo(spellId);
    if (!pSpellInfo) return 1.0f;

    if (spellId && pSpellInfo->Targets & TARGET_FLAG_DEST_LOCATION)
        return 1.0f;
    else if (spellId && pSpellInfo->Targets & TARGET_FLAG_SOURCE_LOCATION)
        return 1.0f;

    uint32 CastingTime = !IsChanneledSpell(pSpellInfo) ? GetSpellCastTime(pSpellInfo, bot) : GetSpellDuration(pSpellInfo);

    if (AI_VALUE2(bool, "has area debuff", "self target") && spellId && CastingTime > 0)
    {
        return 0.0f;
    }

    return 1.0f;
}

void AvoidAoeStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "has area debuff",
        NextAction::array(0, new NextAction("flee", ACTION_EMERGENCY + 5), NULL)));
}

void AvoidAoeStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    InitCombatTriggers(triggers);
}

void AvoidAoeStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new AvoidAoeStrategyMultiplier(ai));
}

void AvoidAoeStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    InitCombatMultipliers(multipliers);
}

void AvoidSpecificCreaturesStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "specific creature too close",
        NextAction::array(0, new NextAction("move away from specific creatures", ACTION_EMERGENCY + 5), NULL)));
}

void AvoidSpecificCreaturesStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    InitCombatTriggers(triggers);
}

void AvoidSpecificCreaturesStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new AvoidSpecificCreaturesStrategyMultiplier(ai));
}

void AvoidSpecificCreaturesStrategy::InitReactionMultipliers(std::list<Multiplier*>& multipliers)
{
    InitCombatMultipliers(multipliers);
}

void WaitForAttackStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "wait for attack safe distance",
        NextAction::array(0, new NextAction("wait for attack keep safe distance", 60.0f), NULL)));
}

void WaitForAttackStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new WaitForAttackMultiplier(ai));
}

WaitForAttackStrategy* WaitForAttackStrategy::Get(PlayerbotAI* ai)
{
    return ai ? ai->GetStrategy<WaitForAttackStrategy>("wait for attack", BotState::BOT_STATE_COMBAT) : nullptr;
}

void WaitForAttackStrategy::AllowExplicitAttack(PlayerbotAI* ai, Player* requester, Unit* target)
{
    Player* bot=ai->GetBot();
    if (ai->IsRealPlayer() || !CanManageBotCommands(ai,requester) || ai->GetMaster()!=requester ||
        !bot->GetGroup() || requester->GetGroup()!=bot->GetGroup() || !bot->IsInMap(requester) ||
        !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !target || !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target) ||
        sServerFacade.IsFriendlyTo(bot,target)) return;
    orderedOwner=requester->GetObjectGuid();orderedTarget=target->GetObjectGuid();
    orderedAt=time(0);orderedCombatStart=ai->GetCombatStartTime();
}

bool WaitForAttackStrategy::HasExplicitAttackOrder(PlayerbotAI* ai, time_t combatStart)
{
    Player* bot=ai->GetBot();Player* owner=ai->GetMaster();
    Unit* target=ai->GetUnit(orderedTarget);
    if (!orderedAt || !combatStart || !owner || owner->GetObjectGuid()!=orderedOwner ||
        !bot->GetGroup() || owner->GetGroup()!=bot->GetGroup() || !bot->IsInMap(owner) ||
        !target || !target->IsInWorld() || !target->IsAlive() || !target->IsInCombat() ||
        !bot->IsInMap(target) || sServerFacade.IsFriendlyTo(bot,target) || (target->GetEntry()==11669 && !ai->IsTank(bot))) return false;
    // Bind an order issued just before the pull to that first combat epoch.
    // A later pull or a changed controller cannot reuse the order.
    if (!orderedCombatStart && combatStart>=orderedAt && combatStart<=orderedAt+3)
        orderedCombatStart=combatStart;
    return orderedCombatStart && combatStart==orderedCombatStart;
}

bool WaitForAttackStrategy::ShouldWait(PlayerbotAI* ai)
{
    // Only check if the bot has the strategy enabled
    if (ai->HasStrategy("wait for attack", BotState::BOT_STATE_COMBAT))
    {
        // Only check if bot is in a group with a real player
        Player* bot = ai->GetBot();
        AiObjectContext* context = ai->GetAiObjectContext();
        if (bot->GetGroup() && ai->HasRealPlayerMaster())
        {
            // Don't wait if the current target is an enemy player
            bool enemyPlayer = false;
            PlayerbotAI* ai = bot->GetPlayerbotAI();
            Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
            if (target)
            {
                Player* player = dynamic_cast<Player*>(target);
                if (player)
                {
                    enemyPlayer = !sServerFacade.IsFriendlyTo(bot, player);
                }
            }

              if (bot->GetMap()->IsRaid() && bot->IsInWorld() && bot->IsAlive() &&
                  !bot->IsBeingTeleported() && !bot->HasCharmer() && !ai->IsRealPlayer())
              {
                  // Healers and tanks must support a live raid pull immediately.
                  // Damage still uses native threat/resource checks; the separate
                  // Flame Imp opening remains enforced for damage and AoE.
                  if (ai->IsHeal(bot) || ai->IsTank(bot)) return false;
                  if (target && target->IsInWorld() && target->IsAlive() && target->IsInCombat() &&
                      bot->IsInMap(target) && target->GetEntry()!=11669)
                      if (Unit* victim=target->GetVictim())
                          if (victim->IsPlayer() && victim->IsInWorld() && victim->IsAlive() && bot->IsInMap(victim))
                          {
                              Player* tank=static_cast<Player*>(victim);
                              if (!tank->IsBeingTeleported() && !tank->HasCharmer() &&
                                  tank->GetGroup()==bot->GetGroup() && ai->IsTank(tank)) return false;
                          }
              }

            if (!enemyPlayer)
            {
                // Check if bot is currently in combat
                const time_t combatStartTime = AI_VALUE(time_t, "combat start time");
                if (combatStartTime > 0)
                {
                    if (WaitForAttackStrategy* strategy=Get(ai))
                        if (strategy->HasExplicitAttackOrder(ai,combatStartTime)) return false;
                    // Check the amount of time elapsed from the combat start
                    const time_t elapsedTime = time(0) - combatStartTime;
                    return elapsedTime < GetWaitTime(ai);
                }
            }
        }
    }

    return false;
}

uint8 WaitForAttackStrategy::GetWaitTime(PlayerbotAI* ai)
{
    AiObjectContext* context = ai->GetAiObjectContext();
    return AI_VALUE(uint8, "wait for attack time");
}

float WaitForAttackMultiplier::GetValue(Action* action)
{
    if (!action) return 1.0f;
    // Waiting for the tank's opening threat must not block a rescue heal.
    if (dynamic_cast<CastHealingSpellAction*>(action))
        if (Unit* patient = action->GetTarget())
            if (patient->GetHealthPercent() < sPlayerbotAIConfig.lowHealth)
                return 1.0f;

    // Allow some movement and targeting actions and non threat actions (like cc!)
    const std::string& actionName = action->getName();
    if ((actionName != "wait for attack keep safe distance") &&
        (actionName != "dps assist") &&
        (actionName != "set facing") &&
        (actionName != "pull my target") &&
        (actionName != "pull rti target") &&
        (actionName != "pull start") &&
        (actionName != "pull action") &&
        (actionName != "pull end") &&
        (action->getThreatType() != ActionThreatType::ACTION_THREAT_NONE))
    {
        return WaitForAttackStrategy::ShouldWait(ai) ? 0.0f : 1.0f;
    }

    return 1.0f;
}

void HealInterruptStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "heal target full health",
        NextAction::array(0, new NextAction("interrupt current spell", ACTION_EMERGENCY), NULL)));
}

void HealInterruptStrategy::InitReactionTriggers(std::list<TriggerNode*>& triggers)
{
    InitCombatTriggers(triggers);
}
