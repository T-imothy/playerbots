
#include "playerbot/playerbot.h"
#include "MoltenCoreDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

namespace
{
    unsigned MoltenCoreTargetPriority(uint32 boss, uint32 target)
    {
        // These entries and native mechanics match all three CMaNGOS scripts.
        // Garr's banish/explosion assignments are not represented here.
        switch (boss)
        {
            case 12118: return target == 12119 ? 1 : 0; // Lucifron's protectors
            case 12259: return target == 11661 ? 1 : 0; // Gehennas's flamewakers
            case 12098: return target == 11662 ? 1 : 0; // Sulfuron's healing priests
            case 12018: // Majordomo ends on add deaths; the boss has death prevention.
                return target == 11663 ? 2 : (target == 11664 ? 1 : 0);
            case 11988: return target == 11988 ? 1 : 0; // Core Ragers cannot die while Golemagg lives.
            case 11502: return target == 12143 ? 1 : 0; // Ragnaros's native Sons of Flame.
            default: return 0;
        }
    }
}

Unit* MoltenCorePriorityTargetAction::GetTarget()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;

    Unit* boss = nullptr;
    bool ragSons = false;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !bot->IsInMap(unit) || !unit->IsAlive() || !unit->IsInCombat()) continue;
        const uint32 entry = unit->GetEntry();
        if (entry == 12143) ragSons = true;
        if (entry != 12118 && entry != 12259 && entry != 12098 && entry != 12018 && entry != 11988 && entry != 11502) continue;
        // Ambiguous multi-boss pulls should retain ordinary player/assist policy.
        if (boss && boss != unit) return nullptr;
        boss = unit;
    }
    if (boss && (boss->GetVictim() == bot || (ragSons && boss->GetEntry() != 11502))) return nullptr;
    // Submerged Ragnaros is correctly absent from attackable-target values.
    // His live, engaged sons identify the add wave without bypassing the
    // native submerged flag, guessing a phase timer or scanning the world.
    const uint32 bossEntry = boss ? boss->GetEntry() : (ragSons ? 11502 : 0);
    if (!bossEntry) return nullptr;

    auto valid = [this](Unit* unit)
    {
        return unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && unit->IsInCombat() &&
            PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    // Manual attack commands and configured raid marks remain authoritative.
    Unit* commanded = ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"));
    if (valid(commanded)) return nullptr;
    Unit* marked = AI_VALUE(Unit*, "rti target");
    if (valid(marked)) return nullptr;

    Unit* current = AI_VALUE(Unit*, "current target");
    Unit* selected = nullptr;
    unsigned priority = 0;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit) continue;
        const unsigned candidatePriority = MoltenCoreTargetPriority(bossEntry, unit->GetEntry());
        if (!candidatePriority || !valid(unit)) continue;
        if (!selected || candidatePriority > priority || (candidatePriority == priority &&
            (unit == current || (selected != current && bot->GetDistance(unit) < bot->GetDistance(selected)))))
        {
            selected = unit;
            priority = candidatePriority;
        }
    }
    return selected;
}

bool MoltenCorePriorityTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != AI_VALUE(Unit*, "current target");
}

bool MoltenCorePositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    if (plan.spell == 20475 && !plan.source.IsEmpty())
    {
        Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
        if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !bot->IsInMap(carrier) ||
            !carrier->IsAlive() || !carrier->HasAura(20475) || carrier->HasCharmer()) return false;
        Player* member = static_cast<Player*>(carrier);
        return !member->IsBeingTeleported() && member->GetGroup() && member->GetGroup() == bot->GetGroup();
    }
    Unit* boss = ai->GetUnit(plan.boss);
    return boss && boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() && boss->IsInCombat();
}

bool MoltenCorePositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool MoltenCorePositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !MoltenCoreThreats(ai, current, threats) ||
        !ValidateEncounterDestination(ai, plan) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
