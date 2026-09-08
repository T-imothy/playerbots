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
        !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    uint32 entry = 19044, damage = 33671, slow = 33572, stoned = 33652;
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 599)
    {
        entry = 27977;
        damage = bot->GetMap()->IsRegularDifficulty() ? 50811 : 61547;
        slow = 50836; stoned = 50812;
    }
    else
#endif
    if (bot->GetMapId() != 565) return false;
    Unit* boss = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && unit->IsAlive() && unit->IsInCombat() && !unit->HasCharmer() &&
            bot->IsInMap(unit) && unit->GetEntry() == entry)
        { if (boss && boss != unit) return false; boss = unit; }
    }
    if (!boss) return false;
    const float radius = NativeEncounterSpellRadius(damage);
    if (!std::isfinite(radius) || radius <= 0 || radius > 30) return false;
    const bool affected = bot->HasAura(slow) || (stoned && bot->HasAura(stoned));
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() || member->HasCharmer() ||
            member->IsBeingTeleported() || member->GetGroup() != bot->GetGroup() || !bot->IsInMap(member) ||
            std::fabs(member->GetPositionZ() - bot->GetPositionZ()) >= 8) continue;
        float clearance = affected || member->HasAura(slow) || (stoned && member->HasAura(stoned)) ? radius : 0.0f;
        if (clearance <= 0) continue;
        // Preserve separation beyond the actual native spell radius.
        const float reach = std::max(bot->GetCombatReach(), member->GetCombatReach());
        if (!std::isfinite(reach) || reach < 0 || reach > 10) continue;
        threats.push_back({{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()}, clearance + reach + 1});
    }
    if (threats.empty()) return false;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.spell = damage;
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
