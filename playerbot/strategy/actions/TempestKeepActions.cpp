#include "playerbot/playerbot.h"
#include "TempestKeepActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

bool SolarianPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 550 || !bot->GetGroup() || !ai->CanMove()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("solarian burst position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() || plan.spell != 42783 ||
        !std::isfinite(plan.destination.x) || !std::isfinite(plan.destination.y) || !std::isfinite(plan.destination.z))
        return false;
    Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
    if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !carrier->IsAlive() || !bot->IsInMap(carrier) ||
        carrier->HasCharmer() || !carrier->HasAura(42783)) return false;
    Player* player = static_cast<Player*>(carrier);
    if (player->IsBeingTeleported() || player->GetGroup() != bot->GetGroup()) return false;
    EncounterPosition current;
    std::vector<encounter::Circle> threats;
    return SolarianBurstThreats(ai, current, threats) && encounter::OutsideCircles(plan.destination, threats);
#else
    return false;
#endif
}

bool SolarianPositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool SolarianPositionAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool SolarianPositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan) ||
        !SolarianBurstThreats(ai, current, threats) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1.5f)
    {
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}

Unit* SolarianPriorityTargetAction::GetTarget()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 550 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;
    auto valid = [this](Unit* unit)
    {
        return unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && !unit->HasCharmer() &&
            PossibleTargetsValue::IsValid(unit, bot, false) &&
            PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, false) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) && !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    if (valid(ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"))) || valid(AI_VALUE(Unit*, "rti target"))) return nullptr;
    Unit* boss = nullptr;
    Unit* selected = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible targets"))
    {
        Unit* add = ai->GetUnit(guid);
        if (!add || (add->GetEntry() != 18806 && add->GetEntry() != 18925) || !valid(add) || !add->IsInCombat()) continue;
        // The split boss is invisible and may not be in the attackers cache.
        // Wild summons record the physical caster, not the original-caster
        // callback recipient: add -> spotlight -> Solarian in these cores.
        Unit* owner = ai->GetUnit(add->GetSpawnerGuid());
        if (owner && owner->IsInWorld() && owner->IsAlive() && bot->IsInMap(owner) && !owner->HasCharmer() &&
            owner->GetEntry() == 18928) owner = ai->GetUnit(owner->GetSpawnerGuid());
        if (!owner || !owner->IsInWorld() || !bot->IsInMap(owner) || !owner->IsAlive() || !owner->IsInCombat() ||
            owner->HasCharmer() || owner->GetEntry() != 18805 || owner->GetVictim() == bot) continue;
        if (boss && boss != owner) return nullptr;
        boss = owner;
        const bool priest = add->GetEntry() == 18806;
        const bool chosenPriest = selected && selected->GetEntry() == 18806;
        if (!selected || (priest && !chosenPriest) || (priest == chosenPriest &&
            (add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected))))) selected = add;
    }
    return selected;
#else
    return nullptr;
#endif
}

bool SolarianPriorityTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != AI_VALUE(Unit*, "current target");
}
