#include "playerbot/playerbot.h"
#include "OnyxiasLairDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

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
    EncounterPosition plan;
    if (!GetPlan(ai, plan)) return false;
#ifdef MANGOSBOT_ZERO
    if (plan.spell == 18392 && plan.source != bot->GetObjectGuid()) return false;
#endif
    return bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool OnyxiaPositionAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !ValidateEncounterDestination(ai, plan)) return false;
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
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
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
