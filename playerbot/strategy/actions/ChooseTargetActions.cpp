#include "playerbot/strategy/Action.h"
#include "ChooseTargetActions.h"
#include "Spells/Spell.h"
#include "MotionGenerators/MovementGenerator.h"
#include "AI/BaseAI/CreatureAI.h"
#include "playerbot/TravelMgr.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "playerbot/strategy/values/FreeMoveValues.h"
#include "playerbot/strategy/values/PvpValues.h"

bool DpsAssistAction::isUseful()
{
    // if carry flag, do not start fight
    if (bot->HasAura(23333) || bot->HasAura(23335) || bot->HasAura(34976))
        return false;

    // Do not admit an assist action for a stale selection. This avoids repeatedly
    // asking AttackAction to reject targets retained across death, map changes or
    // group target switches.
    Unit* target = GetTarget();
    return target && target->IsInWorld() && target->GetMapId() == bot->GetMapId() &&
        !sServerFacade.UnitIsDead(target) && !sServerFacade.IsFriendlyTo(bot, target);
}

bool AttackAnythingAction::isUseful() 
{
    if (!ai->AllowActivity(GRIND_ACTIVITY)) //Bot not allowed to be active
        return false;

    if (!AI_VALUE(bool, "can move around"))
        return false;

    Unit* target = GetTarget();

    if (!target || !ai->IsSafe(target))
        return false;

    if (ai->ContainsStrategy(STRATEGY_TYPE_HEAL) && !ai->HasStrategy("offdps", BotState::BOT_STATE_COMBAT))
        return false;

    if(!target->IsPlayer() && bot->isInFront(target,target->GetAttackDistance(bot)*1.5f, M_PI_F*0.5f) && target->CanAttackOnSight(bot) && target->GetLevel() < bot->GetLevel() + 3.0) //Attack before being attacked.
        return true;

    if (AI_VALUE(bool, "travel target traveling") && CanFreeMoveValue::CanFreeMoveTo(ai, *AI_VALUE(TravelTarget*,"travel target")->GetPosition())) //Bot is traveling
        return false;

    return true;
}

bool ai::AttackAnythingAction::isPossible()
{
    return AttackAction::isPossible() && GetTarget();
}

bool ai::AttackAnythingAction::Execute(Event& event)
{
    bool result = AttackAction::Execute(event);
    if (result)
    {
        Unit* grindTarget = GetTarget();
        if (grindTarget)
        {
            std::string grindName = grindTarget->GetName();
            if (!grindName.empty())
            {
                sPlayerbotAIConfig.logEvent(ai, "AttackAnythingAction", grindName, std::to_string(grindTarget->GetEntry()));

                if (ai->HasStrategy("pull", BotState::BOT_STATE_COMBAT))
                {
                    if (PullStrategy* strategy = PullStrategy::Get(ai))
                    {
                        if (strategy->CanDoPullAction(grindTarget) && (ai->GetBot()->getClass() == CLASS_DRUID || ai->GetBot()->getClass() == CLASS_PALADIN || AI_VALUE2(uint32, "item count", "ammo")))
                        {
                            Event pullEvent("attack anything", grindTarget->GetObjectGuid());
                            bool doAction = ai->DoSpecificAction("pull my target", pullEvent, true);

                            if (doAction)
                            {
                                return true;
                            }
                        }
                    }
                }

                context->GetValue<ObjectGuid>("attack target")->Set(grindTarget->GetObjectGuid());
                ai->StopMoving();
            }
        }
    }

    return result;
}

bool AttackEnemyPlayerAction::isUseful()
{
    return !sPlayerbotAIConfig.IsInPvpProhibitedZone(sServerFacade.GetAreaId(bot));
}

bool AttackEnemyFlagCarrierAction::isUseful()
{
    Unit* target = AI_VALUE(Unit*, "enemy flag carrier");
    if (ActualBattlegroundType(bot) == BATTLEGROUND_WS && !ai->HasRealPlayerMaster() &&
        target != AI_VALUE(Unit*, "enemy player target")) return false;
    return target && target->IsInWorld() && target->IsAlive() && bot->IsInMap(target) &&
        !sServerFacade.IsFriendlyTo(bot, target) && !IsBattlegroundFlagCarrier(bot) &&
        target != AI_VALUE(Unit*, "current target") && bot->IsWithinDistInMap(target, 75.0f);
}

bool SelectNewTargetAction::Execute(Event& event)
{
    const ObjectGuid previousSelection = bot->GetSelectionGuid();
    Unit* victim = bot->GetVictim();
    Pet* activePet = bot->GetPet();
    const bool clearedSelection = previousSelection || victim ||
        (activePet && activePet->GetVictim()) || AI_VALUE(Unit*, "current target");
    Unit* target = AI_VALUE(Unit*, "current target");
    if (target && sServerFacade.UnitIsDead(target))
    {
        // Save the dead target for later looting
        ObjectGuid guid = target->GetObjectGuid();
        if (guid)
        {
            AI_VALUE(LootObjectStack*, "available loot")->Add(guid);
        }
    }

    // Clear the target variables
    ObjectGuid attackTarget = AI_VALUE(ObjectGuid, "attack target");
    std::list<ObjectGuid> possible = AI_VALUE(std::list<ObjectGuid>, "possible targets no los");
    if (attackTarget && find(possible.begin(), possible.end(), attackTarget) == possible.end())
    {
        SET_AI_VALUE(ObjectGuid, "attack target", ObjectGuid());
    }

    // Save the old target and clear the current target
    if(target)
    {
        SET_AI_VALUE(Unit*, "old target", target);
    }
    SET_AI_VALUE(Unit*, "current target", nullptr);
    
    // Stop attacking
    bot->SetSelectionGuid(ObjectGuid());
    // Preserve a heal/buff on an ally while abandoning an enemy. Include
    // hostile channels on the old target, which InterruptSpell() excludes.
    for (int type = CURRENT_MELEE_SPELL; type <= CURRENT_CHANNELED_SPELL; ++type)
    {
        Spell* spell = bot->GetCurrentSpell(static_cast<CurrentSpellTypes>(type));
        if (!spell || !spell->CanBeInterrupted() || IsPositiveSpell(spell->m_spellInfo)) continue;
        if (type != CURRENT_MELEE_SPELL && type != CURRENT_AUTOREPEAT_SPELL &&
            (!previousSelection || spell->m_targets.getUnitTargetGuid() != previousSelection)) continue;
        const uint32 spellId = spell->m_spellInfo->Id;
        bot->InterruptSpell(static_cast<CurrentSpellTypes>(type));
        ai->SpellInterrupted(spellId);
    }
    bot->AttackStop();
    // Stop pet attacking
    Pet* pet = bot->GetPet();
    if (pet)
    {
        UnitAI* creatureAI = ((Creature*)pet)->AI();
        if (creatureAI)
        {
            // Send pet action packet
            const ObjectGuid& petGuid = pet->GetObjectGuid();
            const ObjectGuid& targetGuid = ObjectGuid();
            const uint8 flag = ACT_COMMAND;
            const uint32 spellId = COMMAND_FOLLOW;
            const uint32 command = (flag << 24) | spellId;

            WorldPacket data(CMSG_PET_ACTION);
            data << petGuid;
            data << command;
            data << targetGuid;
            bot->GetSession()->HandlePetAction(data);
        }
    }

    // Invalidate ranked choices so the dead/controlled target cannot win again
    // merely because its previous selection is still cached.
    context->GetValue<Unit*>("dps target")->Reset();
    context->GetValue<Unit*>("dps aoe target")->Reset();
    context->GetValue<Unit*>("tank target")->Reset();
    context->GetValue<Unit*>("enemy player target")->Reset();

    bool selectedReplacement = false;
    if (AI_VALUE(bool, "has attackers"))
    {
        if ((ai->HasStrategy("pvp", BotState::BOT_STATE_COMBAT) ||
            ai->HasStrategy("duel", BotState::BOT_STATE_COMBAT)) &&
            AI_VALUE(bool, "has enemy player targets"))
        {
            if (ai->DoSpecificAction("attack enemy player", event, true)) return true;
        }

        // Recovery runs in combat. Tank role takes precedence if both assists are enabled.
        if (ai->HasStrategy("tank assist", BotState::BOT_STATE_COMBAT))
            selectedReplacement = ai->DoSpecificAction("tank assist", event, true);
        else if (ai->HasStrategy("dps assist", BotState::BOT_STATE_COMBAT))
            selectedReplacement = ai->DoSpecificAction("dps assist", event, true);
    }

    // Count actual cleanup as success, but an already-empty selection must
    // not consume every tick ahead of healing and other combat actions.
    return selectedReplacement || clearedSelection;
}
