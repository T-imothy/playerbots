#include "playerbot/playerbot.h"
#include "DungeonMultipliers.h"
#include "playerbot/strategy/actions/DungeonActions.h"
#include "playerbot/strategy/actions/ReachTargetActions.h"
#include "playerbot/strategy/actions/KarazhanDungeonActions.h"
#include "playerbot/strategy/actions/AttackAction.h"
#include "playerbot/strategy/actions/OnyxiasLairDungeonActions.h"
#include "playerbot/strategy/actions/MoltenCoreDungeonActions.h"
#include "playerbot/strategy/actions/MechanarDungeonActions.h"
#include "playerbot/strategy/actions/GenericSpellActions.h"
#include "playerbot/strategy/actions/BlackwingLairDungeonActions.h"
#include "playerbot/strategy/actions/NaxxramasDungeonActions.h"

using namespace ai;

float PreserveNaxxramasPositionMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 533) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<NaxxramasPositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action) &&
        !dynamic_cast<VoidZoneMoveAwayAction*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return NaxxramasPositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveBlackwingLairPositionMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 469) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<BlackwingLairPositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return BlackwingLairPositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveBossCastPositionMultiplier::GetValue(Action* action)
{
    if (!action || !IsBossEscapeMap(ai->GetBot()->GetMapId())) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<BossCastPositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !spell) return 1.0f;
    EncounterPosition plan;
    if (!BossCastPositionAction::GetPlan(ai, plan)) return 1.0f;
    return movement || (spell && spell->HasMovementEffect()) ? 0.0f : 1.0f;
}

float PreserveAranFlameWreathMultiplier::GetValue(Action* action)
{
    if (!action || !AranFlameWreathHoldAction::IsHolding(ai)) return 1.0f;
    if (dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action)) return 0.0f;
    // Charge/Blink/Disengage are spell actions, not ordinary movement actions.
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    return spell && spell->HasMovementEffect() ? 0.0f : 1.0f;
}

float PreserveMechanarPositionMultiplier::GetValue(Action* action)
{
    if (action && (action->getName() == "dps assist" || action->getName() == "tank assist"))
    {
        PathaleonAddsAction adds(ai);
        if (adds.GetTarget()) return 0.0f;
    }
    if (!dynamic_cast<MovementAction*>(action) || dynamic_cast<AttackAction*>(action) ||
        dynamic_cast<MechanarPositionAction*>(action) || dynamic_cast<MoveAwayFromHazard*>(action)) return 1.0f;
    EncounterPosition plan;
    return MechanarPositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveMoltenCorePositionMultiplier::GetValue(Action* action)
{
    if (!action) return 1.0f;
    if (action && action->getName() == "dps assist")
    {
        MoltenCorePriorityTargetAction priority(ai);
        if (priority.GetTarget()) return 0.0f;
    }
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<MoltenCorePositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return MoltenCorePositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveOnyxiaPositionMultiplier::GetValue(Action* action)
{
    if (action && (action->getName() == "dps assist" || action->getName() == "tank assist"))
    {
        OnyxiaAddsAction adds(ai);
        if (adds.GetTarget()) return 0.0f;
    }
    if (!dynamic_cast<MovementAction*>(action) || dynamic_cast<AttackAction*>(action) ||
        dynamic_cast<OnyxiaPositionAction*>(action) || dynamic_cast<MoveAwayFromHazard*>(action)) return 1.0f;
    EncounterPosition plan;
    if (!OnyxiaPositionAction::GetPlan(ai, plan)) return 1.0f;
    if (!plan.exclusive) return dynamic_cast<SetBehindTargetAction*>(action) ? 0.0f : 1.0f;
    return 0.0f;
}

float PreserveNetherspitePositionMultiplier::GetValue(Action* action)
{
    // Class casts and hazard escapes remain available. Generic chasing/fleeing/
    // following must not fight the encounter position on the very next update.
    if (!action) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<NetherspitePositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action) &&
        !dynamic_cast<VoidZoneMoveAwayAction*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return NetherspitePositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreventMoveAwayFromCreatureOnReachToCastMultiplier::GetValue(Action* action)
{
    MoveAwayFromCreature* moveAwayAction = dynamic_cast<MoveAwayFromCreature*>(action);
    if (moveAwayAction)
    {
        const Action* lastExecutedAction = ai->GetLastExecutedAction(BotState::BOT_STATE_COMBAT);
        if (lastExecutedAction)
        {
            const ReachTargetAction* reachAction = dynamic_cast<const ReachTargetAction*>(lastExecutedAction);
            if (reachAction && !reachAction->GetSpellName().empty())
            {
                return 0.0f;
            }
        }
    }

    return 1.0f;
}
