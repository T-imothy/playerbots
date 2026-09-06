#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool ai::GruulShatterThreats(PlayerbotAI* ai, EncounterPosition& plan,
    std::vector<encounter::Circle>& threats)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 565 || !bot->IsInCombat() || !bot->GetGroup()) return false;
    Unit* boss = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && unit->IsAlive() && unit->IsInCombat() && !unit->HasCharmer() &&
            bot->IsInMap(unit) && unit->GetEntry() == 19044)
        { if (boss && boss != unit) return false; boss = unit; }
    }
    if (!boss) return false;
    const float radius = NativeEncounterSpellRadius(33671);
    if (!std::isfinite(radius) || radius <= 0 || radius > 30) return false;
    const bool affected = bot->HasAura(33572) || bot->HasAura(33652);
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() || member->HasCharmer() ||
            member->IsBeingTeleported() || member->GetGroup() != bot->GetGroup() || !bot->IsInMap(member) ||
            std::fabs(member->GetPositionZ() - bot->GetPositionZ()) >= 8) continue;
        if (!affected && !member->HasAura(33572) && !member->HasAura(33652)) continue;
        // The native damage falloff subtracts the bursting player's combat
        // reach. No fixed donor distance, aura removal or synthetic timer.
        const float reach = std::max(bot->GetCombatReach(), member->GetCombatReach());
        if (!std::isfinite(reach) || reach < 0 || reach > 10) continue;
        threats.push_back({{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()}, radius + reach + 1});
    }
    if (threats.empty()) return false;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.spell = 33671;
    return true;
#else
    return false;
#endif
}

EncounterPosition GruulPositionValue::Calculate()
{
    EncounterPosition plan;
    std::vector<encounter::Circle> threats;
    // Knockback/falling and Stoned remain native movement restrictions.
    if (!GruulShatterThreats(ai, plan, threats) || !ai->CanMove()) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    const float overlap = encounter::SpreadOverlap(here, threats);
    unsigned checked = 0;
    if (overlap > 0)
        for (const auto& point : encounter::SpreadCandidates(here, threats, bot->GetObjectGuid().GetRawValue()))
        {
            // A small improvement threshold avoids chasing floating-point
            // changes or changing course as another player moves inches.
            if (encounter::SpreadOverlap(point, threats) + 1 >= overlap) continue;
            if (++checked > 8) break;
            plan.active = true; plan.destination = point;
            if (ValidateEncounterDestination(ai, plan) &&
                encounter::SpreadOverlap(plan.destination, threats) + 1 < overlap) return plan;
        }
    // Hold the current reachable point during this short native phase, so an
    // old chase cannot immediately undo separation. Do not hold in a hazard.
    plan.active = true; plan.destination = here;
    plan.active = ValidateEncounterDestination(ai, plan);
    return plan;
}
