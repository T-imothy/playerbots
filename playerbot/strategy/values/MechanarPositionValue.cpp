#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool ai::MechanarThreats(PlayerbotAI* ai, EncounterPosition& plan,
    std::vector<encounter::Circle>& threats)
{
    Player* bot = ai->GetBot();
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 554 || !bot->IsInCombat()) return false;
    Unit* boss = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && (unit->GetEntry() == 19219 || unit->GetEntry() == 19221 || unit->GetEntry() == 19220) &&
            unit->IsInWorld() && bot->IsInMap(unit) &&
            unit->IsAlive() && unit->IsInCombat()) { boss = unit; break; }
    }
    if (!boss) return false;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId(); plan.boss = boss->GetObjectGuid();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    const auto add = [&](Unit* center, float radius) {
        if (radius > 0 && radius <= 25 && std::fabs(center->GetPositionZ() - here.z) < 8)
            threats.push_back({{center->GetPositionX(), center->GetPositionY(), center->GetPositionZ()}, radius + 2});
    };
    // The native heroic script assigns these auras. Normal mode and uncharged
    // players do not acquire synthetic polarity or a made-up stacking bonus.
    const uint32 opposite = bot->HasAura(39088) ? 39091 : bot->HasAura(39091) ? 39088 : 0;
    if (boss->GetEntry() == 19219 && opposite && bot->GetGroup())
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member != bot && member->IsInWorld() && !member->IsBeingTeleported() && bot->IsInMap(member) &&
                member->IsAlive() && member->HasAura(opposite)) add(member, NativeEncounterSpellRadius(opposite));
        }
    // Charges are native creature summons, not DynamicObjects. Their lifetime
    // and explosion radius come from the actual timer/pulse spells.
    if (boss->GetEntry() == 19219 || boss->GetEntry() == 19221)
    {
        const bool flames = boss->GetEntry() == 19221;
        const float radius = flames ? NativeEncounterSpellRadius(35281) :
            std::max(NativeEncounterSpellRadius(35151), NativeEncounterSpellRadius(37670));
        std::list<Unit*> hazards;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, flames ? 20481 : 20405, 40.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(hazards, check);
        Cell::VisitAllObjects(bot, searcher, 40.0f);
        for (Unit* hazard : hazards)
            if (hazard && hazard->IsInWorld() && bot->IsInMap(hazard) && hazard->IsAlive() &&
                hazard->HasAura(flames ? 35281 : 37670))
            {
                // Inferno's periodic payload is dispatched by native SpellAuras,
                // not EffectTriggerSpell: its damage radius exceeds the trail.
                const float activeRadius = flames && (hazard->HasAura(35268) || hazard->HasAura(39346)) ?
                    std::max(radius, NativeEncounterSpellRadius(35283)) : radius;
                // Raging Flames fixates and retargets in the native script. A
                // chased bot needs a running buffer, not a threat reset or taunt.
                const float lead = flames && hazard->GetVictim() == bot ? 6.0f : 0.0f;
                add(hazard, activeRadius > 0 ? activeRadius + lead : 0);
            }
    }
    else if (boss->GetVictim() != bot && (ai->IsRanged(bot) || ai->IsHeal(bot)))
    {
        // Stay outside native close-range silence/explosion while still casting.
        // Do not make the tank or melee run away from Pathaleon to avoid damage.
        float radius = NativeEncounterSpellRadius(36022);
        if (!bot->GetMap()->IsRegularDifficulty()) radius = std::max(radius, NativeEncounterSpellRadius(15453));
        add(boss, radius);
    }
    if (threats.empty()) return false;
    bool relevant = false;
    for (const auto& circle : threats)
        relevant = relevant || encounter::Distance2d(here, circle.center) < circle.radius + 5;
    return relevant;
#else
    return false;
#endif
}

EncounterPosition MechanarPositionValue::Calculate()
{
    EncounterPosition plan;
    std::vector<encounter::Circle> threats;
    if (!MechanarThreats(ai, plan, threats)) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    unsigned checked = 0;
    for (const auto& point : encounter::EscapeCircles(here, threats))
    {
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
    }
    plan.active = false;
    return plan;
}
