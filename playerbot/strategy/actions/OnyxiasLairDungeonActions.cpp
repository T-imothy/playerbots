#include "playerbot/playerbot.h"
#include "playerbot/RaidLabTrace.h"
#include "OnyxiasLairDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "Movement/MoveSpline.h"
#include "playerbot/strategy/actions/MovementPathSafety.h"

using namespace ai;

namespace
{
    bool IsOnyxiaAddEntry(uint32 entry)
    {
        if (entry == 11262) return true;
#ifdef MANGOSBOT_TWO
        // Wrath's native summon 68968 creates entry 36561. The level-60
        // Classic/TBC encounter does not have these phase-two lair guards.
        if (entry == 36561) return true;
#endif
        return false;
    }
}

bool OnyxiaPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetMapId() != 249 || !bot->IsInCombat()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("onyxia position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    if (!boss || !boss->IsInWorld() || !bot->IsInMap(boss) || !boss->IsAlive() || !boss->IsInCombat() ||
        boss->HasCharmer() || boss->GetEntry() != 10184) return false;
    // An off-tank assigned to adds must be allowed to chase them, not get
    // dragged back to the boss's flank. A breath escape still takes precedence.
    Unit* current = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
#ifdef MANGOSBOT_ZERO
    if (plan.spell == 18392)
    {
        // Landing releases air stations immediately, even within the value
        // cache interval. Live whelp work can resume without waiting for a tick.
        if (!(boss->IsLevitating() || boss->GetPositionZ() - bot->GetPositionZ() > 10)) return false;
        if (plan.source != bot->GetObjectGuid() && OnyxiaMeleeAirAdd(ai, boss)) return false;
    }
#endif
    if (!plan.exclusive && current && current != boss) return false;
    if (!plan.exclusive)
    {
        // A fear/knockback or threat change can occur inside the value-cache
        // interval. Never execute the previous flank move on the new tank.
        if (boss->GetVictim() == bot || boss->IsLevitating() || boss->GetPositionZ() - bot->GetPositionZ() > 10) return false;
        const float angle = std::atan2(plan.destination.y - boss->GetPositionY(), plan.destination.x - boss->GetPositionX());
        if (std::fabs(std::cos(angle - boss->GetOrientation())) >= 0.70710678f) return false;
    }
#ifdef MANGOSBOT_TWO
    if (plan.spell == 68958)
    {
        Unit* guard = ai->GetUnit(plan.source);
        if (!guard || !guard->IsInWorld() || !bot->IsInMap(guard) || !guard->IsAlive() ||
            !guard->IsInCombat() || guard->HasCharmer() || guard->GetEntry() != 36561) return false;
        const Spell* cast = guard->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (!cast || !cast->m_spellInfo || cast->getState() == SPELL_STATE_FINISHED || cast->m_spellInfo->Id != 68958) return false;
    }
#endif
    const float oldZ = plan.destination.z;
    bot->UpdateAllowedPositionZ(plan.destination.x, plan.destination.y, plan.destination.z);
    return std::isfinite(plan.destination.z) && std::fabs(plan.destination.z - oldZ) < 8;
}

bool OnyxiaPositionAction::isUseful()
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan)) return false;
#ifdef MANGOSBOT_ZERO
    // Routine spacing waits for the current cast/channel. Breath and targeted
    // Fireball escape may interrupt; a safe stationary hold never does.
    if (plan.spell == 18392 && plan.source != bot->GetObjectGuid() && bot->IsNonMeleeSpellCasted(false)) return false;
#endif
    return (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f ||
        (plan.exclusive && EncounterMovementRequired(bot, plan.destination, 1.5f)));
}

bool OnyxiaPositionAction::ShouldReactionInterruptCast() const
{
#ifdef MANGOSBOT_ZERO
    // The native route dispatcher interrupts only after admitting the route.
    if (bot->GetMapId() == 249) return false;
#endif
    EncounterPosition plan;
    if (!GetPlan(ai, plan)) return false;
#ifdef MANGOSBOT_ZERO
    if (plan.spell == 18392 && plan.source != bot->GetObjectGuid()) return false;
#endif
    return bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool OnyxiaPositionAction::ShouldReactionInterruptMovement() const
{
#ifdef MANGOSBOT_ZERO
    // Repeated breath reactions must reach Execute with the existing spline
    // intact so it can retain it, rather than stop/restart it every AI tick.
    if (bot->GetMapId() == 249) return false;
#endif
    return MovementAction::ShouldReactionInterruptMovement();
}

bool OnyxiaPositionAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan)) return RaidLabMovementResult(bot,"ony_position_execute",1,false);
    if (!ai->CanMove()) return RaidLabMovementResult(bot,"ony_position_execute",2,false);
    if (!ValidateEncounterDestination(ai, plan)) return RaidLabMovementResult(bot,"ony_position_execute",3,false);
#ifdef MANGOSBOT_ZERO
    if (plan.spell == 18392 && plan.source != bot->GetObjectGuid() && bot->IsNonMeleeSpellCasted(false)) return false;
#endif
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1.5f)
    {
        if (!plan.exclusive) return false;
#ifdef MANGOSBOT_ZERO
        if (!EncounterMovementRequired(bot, plan.destination, 1.5f)) return false;
#endif
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
#ifdef MANGOSBOT_ZERO
    // Keep the encounter route intact. Generic travel detours were rejecting
    // destinations already admitted by the native encounter path validator.
    // This dispatch is restricted to Classic Onyxia; other movement keeps its
    // existing policy. Recheck the actual path against the current breath.
    if (bot->GetTransport()) return RaidLabMovementResult(bot,"ony_direct_route",1,false);
    const WorldPosition destination(plan.map,plan.destination.x,plan.destination.y,plan.destination.z);
    const auto path=destination.getPathStepFrom(WorldPosition(bot),bot,true);
    if(path.size()<2 || path.size()>256 || !destination.isPathTo(path,1.0f,2.0f))
        return RaidLabMovementResult(bot,"ony_direct_route",2,false);
    auto hazards=ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Get();
    std::vector<encounter::Circle> breath;
    std::list<HazardPosition> breathHazards;
    if(plan.spell && plan.spell!=18392 && OnyxiaBreathThreats(plan.spell,breath))
        for(const auto& circle:breath)
            breathHazards.emplace_back(WorldPosition(plan.map,circle.center.x,circle.center.y,circle.center.z),circle.radius-1);
    WorldPosition previous(bot);
    bool firstPoint = true;
    for(const auto& point:path) {
        if(!(firstPoint && !breath.empty() ? IsHazardSafeGroundProjection(previous,point,hazards) :
             IsHazardSafeSegment(previous,point,hazards)))
            return RaidLabMovementResult(bot,"ony_direct_route",3,false);
        if (!breathHazards.empty() && !IsOnyxiaBreathSafeSegment(previous,point,breathHazards,firstPoint))
            return RaidLabMovementResult(bot,"ony_direct_route",6,false);
        previous=point;
        firstPoint=false;
    }
    if(bot->movespline && !bot->movespline->Finalized()) {
        const auto end=bot->movespline->FinalDestination();
        if(std::hypot(end.x-plan.destination.x,end.y-plan.destination.y)<=1.5f &&
           std::fabs(end.z-plan.destination.z)<=1.5f) {
            SetDuration(100);return RaidLabMovementResult(bot,"ony_direct_route",4,true);
        }
    }
    bot->SetStandState(UNIT_STAND_STATE_STAND);
    if(bot->IsNonMeleeSpellCasted(false,false,true)) bot->InterruptNonMeleeSpells(false);
    auto& motion=*bot->GetMotionMaster();
    motion.Clear(false,true);
    auto points=WorldPosition().toPointsArray(path);
    motion.MovePath(points,FORCED_MOVEMENT_RUN,false,false);
    SetDuration(100);
    return RaidLabMovementResult(bot,"ony_direct_route",5,true);
#else
    return RaidLabMovementResult(bot,"ony_position_execute",4,MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true));
#endif
}

Unit* OnyxiaAddsAction::GetTarget()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 249 || !bot->IsInCombat() || ai->IsHeal(bot)) return nullptr;
    Unit* boss = FindOnyxiaBoss(ai);
    if (!boss) return nullptr;
    const bool airborne = boss->IsLevitating() || boss->GetPositionZ() - bot->GetPositionZ() > 10;
#ifdef MANGOSBOT_ZERO
    if (!airborne && boss->GetVictim() == bot) return nullptr;
#else
    if (boss->GetVictim() == bot) return nullptr;
#endif
    if (!airborne && !ai->IsTank(bot)) return nullptr;
    auto validOrder = [this](Unit* unit)
    {
        return unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() &&
            PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true);
    };
    if (validOrder(ai->GetUnit(AI_VALUE(ObjectGuid, "attack target")))) return nullptr;
    Unit* marked = ai->GetUnit(AI_VALUE(ObjectGuid, "rti target"));
    if (!validOrder(marked)) marked = nullptr;
    if (marked && !IsOnyxiaAddEntry(marked->GetEntry())) return nullptr;
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    Unit* nearest = nullptr;
    Unit* retained = nullptr;
    Unit* rescue = nullptr;
    Unit* markedAdd = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !bot->IsInMap(unit) || !unit->IsAlive() || !unit->IsInCombat()) continue;
        // Shared target lists can reintroduce CC targets as a last resort.
        // Encounter add priority must not turn that into an instruction to break CC.
        if (!IsOnyxiaAddEntry(unit->GetEntry()) || PossibleAttackTargetsValue::HasBreakableCC(unit, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot) ||
            !PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true)) continue;
        if (unit == marked)
        {
            if (!ai->IsTank(bot)) return unit;
            markedAdd = unit;
        }
        // Retaining a safely held whelp must not suppress the tank assist
        // rescue that this encounter action replaces while adds are alive.
        Player* victim = dynamic_cast<Player*>(unit->GetVictim());
        if (ai->IsTank(bot) && victim && victim != bot && victim->IsInWorld() && victim->IsAlive() &&
            bot->IsInMap(victim) && bot->GetGroup() && victim->GetGroup() == bot->GetGroup() && !ai->IsTank(victim) &&
            (!rescue || bot->GetDistance(unit) < bot->GetDistance(rescue))) rescue = unit;
        if (unit == current) retained = unit;
        if (!nearest || bot->GetDistance(unit) < bot->GetDistance(nearest)) nearest = unit;
    }
    return rescue ? rescue : markedAdd ? markedAdd : retained ? retained : nearest;
}

bool OnyxiaAddsAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
}
