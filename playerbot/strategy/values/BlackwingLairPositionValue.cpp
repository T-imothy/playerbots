#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

uint32 ai::BurningAdrenalineAura(Unit* unit)
{
    if (!unit) return 0;
    if (unit->HasAura(18173)) return 18173;
    return unit->HasAura(23620) ? 23620 : 0;
}

EncounterPosition BlackwingLairPositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
        bot->HasCharmer() || bot->GetMapId() != 469 || !bot->GetGroup()) return plan;

    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() &&
            unit->IsInCombat() && unit->GetEntry() == 13020) { boss = unit; break; }
    }
    // Do not drag the dragon through the raid. The active tank retains normal
    // positioning; other players avoid that carrier. Once native threat changes
    // the victim, the former tank can separate without a fabricated taunt.
    if (boss && boss->GetVictim() == bot) return plan;

    const uint32 ownAura = BurningAdrenalineAura(bot);
    // The explosion is in Aura::HandlePeriodicTriggerSpell's removal hook,
    // not EffectTriggerSpell of the debuff (which points at its health drain).
    const float radius = NativeEncounterSpellRadius(23478);
    if (!std::isfinite(radius) || radius <= 0 || radius > 45) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    std::vector<encounter::Circle> threats;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    if (boss) plan.boss = boss->GetObjectGuid();
    if (ownAura) { plan.spell = ownAura; plan.source = bot->GetObjectGuid(); }
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
            member->IsBeingTeleported() || member->HasCharmer() || !bot->IsInMap(member) ||
            std::fabs(member->GetPositionZ() - here.z) >= 8) continue;
        const uint32 aura = BurningAdrenalineAura(member);
        if (!ownAura && !aura) continue;
        threats.push_back({{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()}, radius + 2});
        if (!ownAura && (plan.source.IsEmpty() || member->GetObjectGuid() < plan.source))
        { plan.spell = aura; plan.source = member->GetObjectGuid(); }
    }
    if (threats.empty()) return plan;
    bool relevant = ownAura != 0;
    for (const auto& threat : threats)
        relevant = relevant || encounter::Distance2d(here, threat.center) < threat.radius + 8;
    if (!relevant) return plan;

    unsigned checked = 0;
    for (const auto& point : encounter::EscapeCircles(here, threats))
    {
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan)) return plan;
    }
    plan.active = false;
    return plan;
}
