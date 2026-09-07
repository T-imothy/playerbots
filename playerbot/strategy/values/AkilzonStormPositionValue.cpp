#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "Entities/DynamicObject.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

Unit* ai::AkilzonStormBoss(Player* bot, DynamicObject* eye)
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || bot->GetMapId() != 568 || !bot->GetGroup() || !eye || !eye->IsInWorld() ||
        !bot->IsInMap(eye) || eye->GetSpellId() != 44007 || !eye->GetDuration() ||
        !std::isfinite(eye->GetRadius()) || eye->GetRadius() <= 1 || eye->GetRadius() > 20) return nullptr;
    Unit* caster = eye->GetCaster();
    if (!caster || !caster->IsPlayer() || !caster->IsInWorld() || !caster->IsAlive() ||
        !bot->IsInMap(caster) || caster->HasCharmer()) return nullptr;
    Player* member = static_cast<Player*>(caster);
    if (member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported()) return nullptr;
    const SpellAuraHolder* storm = member->GetSpellAuraHolder(43648);
    Unit* boss = storm ? storm->GetCaster() : nullptr;
    return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && !boss->HasCharmer() &&
        bot->IsInMap(boss) && boss->GetEntry() == 23574 ? boss : nullptr;
#else
    return nullptr;
#endif
}

EncounterPosition AkilzonStormPositionValue::Calculate()
{
    EncounterPosition plan;
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 568 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return plan;
    DynamicObject* eye = nullptr;
    Unit* boss = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member)) continue;
        DynamicObject* candidate = member->GetDynObject(44007);
        Unit* source = AkilzonStormBoss(bot, candidate);
        if (!source) continue;
        if (eye && eye != candidate) return plan;
        eye = candidate; boss = source;
    }
    if (!eye || bot->GetDistance(eye) > 60) return plan;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.source = eye->GetObjectGuid(); plan.spell = 44007;
    // Use the actual ground eye, not the lifted player's current altitude.
    plan.destination = bot->GetDistance(eye) <= eye->GetRadius() - 1 ?
        encounter::Point{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()} :
        encounter::Point{eye->GetPositionX(), eye->GetPositionY(), eye->GetPositionZ()};
    plan.active = ValidateEncounterDestination(ai, plan) &&
        eye->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= eye->GetRadius() - 1;
#endif
    return plan;
}
