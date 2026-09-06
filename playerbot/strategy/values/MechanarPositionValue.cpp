#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

EncounterPosition MechanarPositionValue::Calculate()
{
    EncounterPosition plan;
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 554 || !bot->IsInCombat()) return plan;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->GetEntry() == 19219 && unit->IsInWorld() && unit->GetMap() == bot->GetMap() &&
            unit->IsAlive() && unit->IsInCombat()) { boss = unit; break; }
    }
    if (!boss) return plan;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId(); plan.boss = boss->GetObjectGuid();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    std::vector<encounter::Circle> threats;
    const auto add = [&](Unit* center, float radius) {
        if (radius > 0 && radius <= 25 && std::fabs(center->GetPositionZ() - here.z) < 8)
            threats.push_back({{center->GetPositionX(), center->GetPositionY(), center->GetPositionZ()}, radius + 2});
    };
    // The native heroic script assigns these auras. Normal mode and uncharged
    // players do not acquire synthetic polarity or a made-up stacking bonus.
    const uint32 opposite = bot->HasAura(39088) ? 39091 : bot->HasAura(39091) ? 39088 : 0;
    if (opposite && bot->GetGroup())
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member != bot && member->IsInWorld() && member->GetMap() == bot->GetMap() &&
                member->IsAlive() && member->HasAura(opposite)) add(member, NativeEncounterSpellRadius(opposite));
        }
    // Charges are native creature summons, not DynamicObjects. Their lifetime
    // and explosion radius come from the actual timer/pulse spells.
    const float radius = std::max(NativeEncounterSpellRadius(35151), NativeEncounterSpellRadius(37670));
    std::list<Unit*> charges;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, 20405, 40.0f);
    MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(charges, check);
    Cell::VisitAllObjects(bot, searcher, 40.0f);
    for (Unit* charge : charges)
        if (charge && charge->IsInWorld() && charge->GetMap() == bot->GetMap() && charge->IsAlive() &&
            charge->HasAura(37670)) add(charge, radius);
    if (threats.empty()) return plan;
    bool relevant = false;
    for (const auto& circle : threats)
        relevant = relevant || encounter::Distance2d(here, circle.center) < circle.radius + 5;
    if (!relevant) return plan;
    unsigned checked = 0;
    for (const auto& point : encounter::EscapeCircles(here, threats))
    {
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan)) return plan;
    }
    plan.active = false;
#endif
    return plan;
}
