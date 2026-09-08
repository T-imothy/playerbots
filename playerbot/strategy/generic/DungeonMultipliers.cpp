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
#include "playerbot/strategy/actions/TempestKeepActions.h"

using namespace ai;
float PreserveRotatingBeamMultiplier::GetValue(Action* action)
{
    if (!action || (ai->GetBot()->GetMapId() != 531 && ai->GetBot()->GetMapId() != 548 && ai->GetBot()->GetMapId() != 632) ||
        dynamic_cast<RotatingBeamAction*>(action) || dynamic_cast<MoveAwayFromHazard*>(action)) return 1.0f;
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!dynamic_cast<MovementAction*>(action) && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    encounter::RotatingBeam beam;
    return RotatingBeamAction::GetPlan(ai, plan, beam) ? 0.0f : 1.0f;
}

float PreserveVashjCoreMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 548 || dynamic_cast<VashjCoreAction*>(action) ||
        dynamic_cast<MoveAwayFromHazard*>(action)) return 1.0f;
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!dynamic_cast<MovementAction*>(action) && !(spell && spell->HasMovementEffect())) return 1.0f;
    VashjCorePlan plan;
    if (!VashjCoreAction::GetPlan(ai, plan) || plan.task == VashjCoreTask::Deliver) return 1.0f;
    return 0.0f;
}


float PreserveHeiganDanceMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 533) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<HeiganDanceAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return HeiganDanceAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveNajentusSpineMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 564) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<NajentusSpineAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return NajentusSpineAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveLinkedBurstMultiplier::GetValue(Action* action)
{
    if (!action) return 1.0f;
    const uint32 map = ai->GetBot()->GetMapId();
    if (map != 543 && map != 555 && map != 564) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<LinkedBurstAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action) &&
        !dynamic_cast<BossCastPositionAction*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return LinkedBurstAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveAkilzonStormMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 568) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<AkilzonStormAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return AkilzonStormAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveHakkarPoisonMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 309) return 1.0f;
    if (ai->IsHeal(ai->GetBot()))
        if (ReachTargetAction* reach = dynamic_cast<ReachTargetAction*>(action))
            if (Unit* target = reach->GetTarget())
                if (sServerFacade.IsFriendlyTo(ai->GetBot(), target)) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<HakkarPoisonAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return HakkarPoisonAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveOssirianCrystalMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 509) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<OssirianCrystalAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return OssirianCrystalAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveBossCoverMultiplier::GetValue(Action* action)
{
    if (!action || !IsBossCoverMap(ai->GetBot()->GetMapId())) return 1.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<BossCoverAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return BossCoverAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveDungeonAddTargetMultiplier::GetValue(Action* action)
{
    if (!action || action->getName() != "dps assist") return 1.0f;
    DungeonAddTargetAction priority(ai);
    return priority.GetTarget() ? 0.0f : 1.0f;
}

float PreserveSolarianPositionMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 550) return 1.0f;
    if (action->getName() == "dps assist")
    {
        SolarianPriorityTargetAction priority(ai);
        if (priority.GetTarget()) return 0.0f;
    }
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<SolarianPositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return SolarianPositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveMagtheridonCubeMultiplier::GetValue(Action* action)
{
    if (!action || ai->GetBot()->GetMapId() != 544 || dynamic_cast<MagtheridonCubeAction*>(action) ||
        dynamic_cast<MoveAwayFromHazard*>(action)) return 1.0f;
    // Let the cube action cancel the native channel after Nova/reset. During
    // it, neither class casts nor routine movement should cancel participation.
    if (HasMagtheridonChannel(ai->GetBot())) return 0.0f;
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return MagtheridonCubeAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveGruulSpreadMultiplier::GetValue(Action* action)
{
    if (!action) return 1.0f;
    const uint32 map = ai->GetBot()->GetMapId();
    if (map != 565
#ifdef MANGOSBOT_TWO
        && map != 599 && map != 631 && map != 624
#endif
    ) return 1.0f;
#ifdef MANGOSBOT_TWO
    // A cover destination already revalidates Beacon/Backlash clearance.
    // Allow that compatible action instead of making cover and spread veto
    // each other. Valid cover still has priority through its own multiplier.
    if (map == 631 && dynamic_cast<BossCoverAction*>(action)) return 1.0f;
#endif
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<GruulSpreadAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
    EncounterPosition plan;
    return GruulSpreadAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}

float PreserveKarazhanTargetMultiplier::GetValue(Action* action)
{
    if (!action || action->getName() != "dps assist") return 1.0f;
    KarazhanPriorityTargetAction priority(ai);
    return priority.GetTarget() ? 0.0f : 1.0f;
}

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
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<MechanarPositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
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
    const bool movement = dynamic_cast<MovementAction*>(action) && !dynamic_cast<AttackAction*>(action) &&
        !dynamic_cast<OnyxiaPositionAction*>(action) && !dynamic_cast<MoveAwayFromHazard*>(action);
    CastSpellAction* spell = dynamic_cast<CastSpellAction*>(action);
    if (!movement && !(spell && spell->HasMovementEffect())) return 1.0f;
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
