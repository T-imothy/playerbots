
#include "playerbot/playerbot.h"
#include "KarazhanDungeonActions.h"
#include "playerbot/strategy/Action.h"

using namespace ai;

bool AranFlameWreathValue::Calculate()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 532 || !bot->IsInCombat()) return false;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->GetEntry() == 16524 && unit->IsInWorld() && bot->IsInMap(unit) &&
            unit->IsAlive() && unit->IsInCombat()) { boss = unit; break; }
    }
    if (!boss) return false;
    // Stop during the native cast, before a moving bot can cross the new ring.
    const Spell* spell = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
    if (spell && spell->m_spellInfo->Id == 30004 && spell->getState() != SPELL_STATE_FINISHED) return true;
    if (bot->HasAura(29946)) return true;
    if (bot->GetGroup())
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() && bot->IsInMap(member) &&
                member->HasAura(29946)) return true;
        }
#endif
    return false;
}

bool AranFlameWreathHoldAction::IsHolding(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    return bot->IsInWorld() && bot->IsAlive() && !bot->HasCharmer() && !bot->IsBeingTeleported() &&
        bot->GetMapId() == 532 && bot->IsInCombat() &&
        ai->GetAiObjectContext()->GetValue<bool>("aran flame wreath")->Get();
}

bool AranFlameWreathHoldAction::isUseful()
{
    return IsHolding(ai) && (!bot->IsStopped() ||
        bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool AranFlameWreathHoldAction::Execute(Event& event)
{
    if (!IsHolding(ai)) return false;
    // Native movement cancellation only. Keep valid stationary casts/heals;
    // never cancel the wreath aura or alter the core's crossing/explosion rule.
    ai->StopMoving();
    SetDuration(100);
    return true;
}

bool NetherspitePositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetMapId() != 532 || !bot->IsInCombat()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("netherspite position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    Unit* portal = ai->GetUnit(plan.source);
    if (!boss || !portal || !boss->IsInWorld() || !portal->IsInWorld() ||
        !bot->IsInMap(boss) || !bot->IsInMap(portal) ||
        !boss->IsAlive() || !boss->IsInCombat() || !portal->IsAlive() || boss->HasAura(38542)) return false;
    const float oldZ = plan.destination.z;
    bot->UpdateAllowedPositionZ(plan.destination.x, plan.destination.y, plan.destination.z);
    return std::isfinite(plan.destination.z) && std::fabs(plan.destination.z - oldZ) < 6.0f;
}

bool NetherspitePositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f;
}

bool NetherspitePositionAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !ValidateEncounterDestination(ai, plan)) return false;
    // Use ordinary pathfinding and the native portal SpellScript. No aura
    // grants, removals, boss weakening, teleportation or no-path movement.
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
