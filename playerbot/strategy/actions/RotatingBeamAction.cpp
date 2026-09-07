#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool RotatingBeamAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan, encounter::RotatingBeam& beam)
{
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 531 && bot->GetMapId() != 548) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("rotating beam position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    EncounterPosition current;
    if (!ReadRotatingBeam(ai, ai->GetUnit(plan.boss), current, beam) || current.spell != plan.spell) return false;
    return (beam.shelteredInWater && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1) ||
        encounter::OutsideRotatingBeam(plan.destination, beam);
}

bool RotatingBeamAction::isUseful()
{
    EncounterPosition plan;
    encounter::RotatingBeam beam;
    return GetPlan(ai, plan, beam) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1 ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool RotatingBeamAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    encounter::RotatingBeam beam;
    return GetPlan(ai, plan, beam) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1;
}

bool RotatingBeamAction::Execute(Event& event)
{
    EncounterPosition plan;
    encounter::RotatingBeam beam;
    if (!GetPlan(ai, plan, beam) || !ValidateRotatingBeamDestination(ai, plan, beam)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1)
    {
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
    if (!ai->CanMove()) return false;
    if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
