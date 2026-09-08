
#include "playerbot/playerbot.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "playerbot/strategy/values/AttackersValue.h"
#include "PullActions.h"
#include "PullDiagnostics.h"
#include "BotCommandAccess.h"
#include "playerbot/strategy/values/PositionValue.h"

using namespace ai;

const char* ai::PullFailureReason(PullFailure failure)
{
    switch (failure)
    {
        case PullFailure::None: return "ready";
        case PullFailure::NoTarget: return "no hostile target selected";
        case PullFailure::InvalidTarget: return "target cannot be pulled";
        case PullFailure::StrategyDisabled: return "pull strategy is disabled";
        case PullFailure::NoAction: return "no pull action is available";
        case PullFailure::NoRangedWeapon: return "no usable ranged weapon";
        case PullFailure::NoAmmo: return "ammunition is required";
        case PullFailure::OutOfRange: return "target is outside pull range";
        case PullFailure::NoLineOfSight: return "no line of sight";
        case PullFailure::NotKnown: return "pull spell is not known";
        case PullFailure::NotReady: return "pull spell is on cooldown";
        case PullFailure::InvalidState: return "current state prevents the pull";
        default: return "configured pull action is unavailable";
    }
}

PullFailure ai::GetPullReadiness(PlayerbotAI* ai, Unit* target)
{
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (!strategy) return PullFailure::StrategyDisabled;
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer())
        return PullFailure::InvalidState;
    if (!target) return PullFailure::NoTarget;
    if (!AttackersValue::IsValid(target, bot, nullptr, false)) return PullFailure::InvalidTarget;
    // Match the existing request gate; this diagnostic does not change which
    // classes currently require the ranged equipment slot to be populated.
    if (bot->getClass() != CLASS_DRUID && bot->getClass() != CLASS_PALADIN &&
        !bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_RANGED))
        return PullFailure::NoRangedWeapon;
    if (strategy->GetPullActionName().empty() ||
        !ai->GetAiObjectContext()->GetAction(strategy->GetPullActionName())) return PullFailure::NoAction;
    SpellCastResult result = SPELL_CAST_OK;
    const bool possible = ai->CanCastSpell(strategy->GetSpellName(), target, 0, nullptr, false, false, false, &result);
    switch (result)
    {
        case SPELL_FAILED_NEED_AMMO:
        case SPELL_FAILED_NO_AMMO: return PullFailure::NoAmmo;
        case SPELL_FAILED_EQUIPPED_ITEM:
        case SPELL_FAILED_EQUIPPED_ITEM_CLASS: return PullFailure::NoRangedWeapon;
        case SPELL_FAILED_OUT_OF_RANGE:
        case SPELL_FAILED_TOO_CLOSE: return PullFailure::OutOfRange;
        case SPELL_FAILED_LINE_OF_SIGHT: return PullFailure::NoLineOfSight;
        case SPELL_FAILED_NOT_KNOWN: return PullFailure::NotKnown;
        case SPELL_FAILED_NOT_READY: return PullFailure::NotReady;
        case SPELL_CAST_OK: return possible ? PullFailure::None : PullFailure::Unavailable;
        default: return PullFailure::InvalidState;
    }
}

bool PullRequestAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    auto fail = [&](PullFailure reason) {
        if ((event.getSource() == "pull" || event.getSource() == "pull rti") && CanManageBotCommands(ai, requester))
            ai->TellPlayerNoFacing(requester, std::string("Pull failed: ") + PullFailureReason(reason) + ".");
        return false;
    };
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (!strategy)
    {
        return fail(PullFailure::StrategyDisabled);
    }

    Unit* target = GetTarget(event);
    if (!target)
    {
        return fail(PullFailure::NoTarget);
    }

    const float maxPullDistance = sPlayerbotAIConfig.reactDistance * 3;
    const float distanceToPullTarget = target->GetDistance(ai->GetBot());
    if (distanceToPullTarget > maxPullDistance)
    {
        return fail(PullFailure::OutOfRange);
    }

    if (!AttackersValue::IsValid(target, bot, nullptr, false))
    {
        return fail(PullFailure::InvalidTarget);
    }

    if (!strategy->CanDoPullAction(target))
    {
        const PullFailure reason = GetPullReadiness(ai, target);
        return fail(reason == PullFailure::None ? PullFailure::Unavailable : reason);
    }

    //Set position to return to after pulling.
    PositionMap& posMap = AI_VALUE(PositionMap&, "position");
    PositionEntry pullPosition = posMap["pull"];

    pullPosition.Set(bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ(), bot->GetMapId());
    posMap["pull"] = pullPosition;

    strategy->RequestPull(target);

    // Force change combat state to have a faster reaction time
    ai->OnCombatStarted();

    return true;
}

Unit* PullMyTargetAction::GetTarget(Event& event)
{
    Unit* target = nullptr;

    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    if (event.getSource() == "attack anything")
    {
        ObjectGuid guid = event.getObject();
        target = ai->GetCreature(guid);
    }
    else if (requester)
    {
        target = ai->GetUnit(requester->GetSelectionGuid());
    }

    return target;
}

Unit* PullRTITargetAction::GetTarget(Event& event)
{
    return AI_VALUE(Unit*, "rti target");
}

bool PullStartAction::Execute(Event& event)
{
    bool result = false;
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (strategy)
    {
        Unit* target = strategy->GetTarget();
        if (target)
        {
            if (strategy->GetPreActionName().empty())
                result = true;
            else
            {
                result = ai->DoSpecificAction(strategy->GetPreActionName(), event, true);
                if(result)
                    SetDuration(3000);
            }

            // Set the pet on passive mode during the pull
            Pet* pet = bot->GetPet();
            if (pet)
            {
                UnitAI* creatureAI = ((Creature*)pet)->AI();
                if (creatureAI)
                {
                    strategy->SetPetReactState(creatureAI->GetReactState());
                    creatureAI->SetReactState(REACT_PASSIVE);
                }
            }

            strategy->OnPullStarted();
        }
    }

    return result;
}


PullAction::PullAction(PlayerbotAI* ai, std::string name) : CastSpellAction(ai, name)
{
    InitPullAction();
}

bool PullAction::Execute(Event& event)
{
    InitPullAction();

    PullStrategy* strategy = PullStrategy::Get(ai);
    if (strategy)
    {
        Unit* target = strategy->GetTarget();
        if (target)
        {
            // Check if we are on pull range
            const float distanceToTarget = target->GetDistance(bot);
            if (distanceToTarget <= strategy->GetRange())
            {
                if (sServerFacade.isMoving(bot))
                {
                    // Force stop
                    ai->StopMoving();
                    strategy->RequestPull(target, false);
                    return false;
                }

                std::string actionName = strategy->GetPullActionName();

                // Execute the pull action
                SET_AI_VALUE(Unit*, "current target", GetTarget());
                if (ai->DoSpecificAction(actionName, event, true))
                {
                    strategy->RequestPull(target); //extend pull timer to walk back.
                    return true;
                }
                else
                    return false;
            }
            else
            {
                // Retry the reach pull action
                strategy->RequestPull(target, false);
            }
        }
    }

    return false;
}

bool PullAction::isPossible()
{
    InitPullAction();

    PullStrategy* strategy = PullStrategy::Get(ai);
    if (strategy)
    {
        std::string spellName = strategy->GetSpellName();
        Unit* target = strategy->GetTarget();
        if (!spellName.empty() && target)
        {
            if (!ai->CanCastSpell(spellName, target, 0, nullptr, true))
            {
                return false;
            }
        }
    }

    return true;
}

void PullAction::InitPullAction()
{
    // Get the pull action spell name from the strategy
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (strategy)
    {
        std::string spellName = strategy->GetSpellName();
        if (!spellName.empty())
        {
            SetSpellName(spellName);

            float spellRange;
            if (ai->GetSpellRange(spellName, &spellRange))
            {
                range = spellRange;
            }
        }
    }
}

bool PullEndAction::Execute(Event& event)
{
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (strategy)
    {
        // Restore the pet react state
        Pet* pet = bot->GetPet();
        if (pet)
        {
            UnitAI* creatureAI = ((Creature*)pet)->AI();
            if (creatureAI)
            {
                creatureAI->SetReactState(strategy->GetPetReactState());
                Unit* target = AI_VALUE(Unit*, "current target");
                if (creatureAI->GetReactState() != REACT_PASSIVE && target)
                    creatureAI->AttackStart(target);
            }
        }

        // Remove the saved pull position
        AiObjectContext* context = ai->GetAiObjectContext();
        PositionMap& posMap = AI_VALUE(PositionMap&, "position");
        PositionEntry stayPosition = posMap["pull"];
        if (stayPosition.isSet())
        {
            posMap.erase("pull");
        }

        strategy->OnPullEnded();
        return true;
    }

    return false;
}
