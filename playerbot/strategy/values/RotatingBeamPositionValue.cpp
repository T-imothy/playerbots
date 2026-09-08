#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "Spells/SpellMgr.h"

using namespace ai;

bool ai::ReadRotatingBeam(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan, encounter::RotatingBeam& beam)
{
    beam = encounter::RotatingBeam();
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || !bot->GetGroup() ||
        bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT) || !boss || !boss->IsInWorld() ||
        !boss->IsAlive() || !boss->IsInCombat() || boss->HasCharmer() || !bot->IsInMap(boss) || bot->GetDistance(boss) > 100) return false;
    uint32 left = 0, right = 0, payload = 0;
    float step = 0;
    if (bot->GetMapId() == 531 && boss->GetEntry() == 15589)
    { left = 26009; right = 26136; payload = 26029; step = M_PI_F / 35; }
#ifndef MANGOSBOT_ZERO
    else if (bot->GetMapId() == 548 && boss->GetEntry() == 21217)
    {
        left = 37429; right = 37430; payload = 37433; step = 2 * M_PI_F / 72;
        // This is the native CheckTarget exemption, not merely feet in water.
        beam.shelteredInWater = bot->IsInWater() && bot->IsInHighLiquid();
    }
#endif
#ifdef MANGOSBOT_TWO
    else if (bot->GetMapId() == 632 && boss->GetEntry() == 36502)
    {
        // Native Wailing Souls rotates by 0.09 radians each 500 ms aura tick.
        // Both difficulties use the same cone/radius; spell damage stays native.
        left = 68875; right = 68876; payload = 68873; step = 0.09f;
    }
#endif
    else return false;
    const bool turnsLeft = boss->GetSpellAuraHolder(left, boss->GetObjectGuid()) != nullptr;
    const bool turnsRight = boss->GetSpellAuraHolder(right, boss->GetObjectGuid()) != nullptr;
    if (turnsLeft == turnsRight) return false;
    const uint32 aura = turnsLeft ? left : right;
    const SpellEntry* rotation = sSpellTemplate.LookupEntry<SpellEntry>(aura);
    if (!rotation || !rotation->EffectAmplitude[EFFECT_INDEX_0]) return false;
    const float period = rotation->EffectAmplitude[EFFECT_INDEX_0] / 1000.0f;
    const SpellCone* cone = sSpellCones.LookupEntry<SpellCone>(sSpellMgr.GetFirstSpellInChain(payload));
    const float degrees = cone ? float(cone->coneAngle) : 60.0f;
    const float radius = NativeEncounterSpellRadius(payload);
    if (!std::isfinite(degrees) || degrees <= 0 || degrees >= 180 ||
        !std::isfinite(radius) || radius <= 0 || radius > 150 || period <= 0) return false;
    beam.origin = {boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()};
    beam.orientation = boss->GetOrientation();
    beam.halfAngle = degrees * M_PI_F / 360;
    // Include a complete native tick plus cache/reaction lead. Keep the actual
    // rotation direction; treating the beam as a radial explosion is incorrect.
    beam.angularSpeed = (turnsLeft ? step : -step) / period;
    beam.sweep = beam.angularSpeed * (2.5f + period);
    beam.radius = radius;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.spell = aura;
    return true;
}

bool ai::ValidateRotatingBeamDestination(PlayerbotAI* ai, EncounterPosition& plan, const encounter::RotatingBeam& beam)
{
    Player* bot = ai->GetBot();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    if (beam.shelteredInWater && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1)
        return ValidateEncounterDestination(ai, plan);
    if (!encounter::OutsideRotatingBeam(plan.destination, beam) || !ValidateEncounterDestination(ai, plan)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1) return true;
    const WorldPosition destination(plan.map, plan.destination.x, plan.destination.y, plan.destination.z);
    const auto path = destination.getPathStepFrom(WorldPosition(bot), bot, true);
    if (path.size() < 2 || path.size() > 256 || !destination.isPathTo(path, 1.0f, 2.0f)) return false;
    std::vector<encounter::Point> points;
    for (const WorldPosition& point : path) points.push_back({point.getX(), point.getY(), point.getZ()});
    return encounter::RotatingBeamRouteSafe(here, points, beam, bot->GetSpeed(MOVE_RUN));
}

EncounterPosition RotatingBeamPositionValue::Calculate()
{
    EncounterPosition plan;
    uint32 entry = bot->GetMapId() == 531 ? 15589 : 0;
#ifndef MANGOSBOT_ZERO
    if (bot->GetMapId() == 548) entry = 21217;
#endif
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 632) entry = 36502;
#endif
    if (!entry || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || !bot->GetGroup()) return plan;
    std::list<Unit*> bosses;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, entry, 100.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(bosses, check);
    Cell::VisitAllObjects(bot, searcher, 100.0f);
    Unit* selected = nullptr;
    encounter::RotatingBeam beam;
    for (Unit* boss : bosses)
    {
        EncounterPosition candidate;
        encounter::RotatingBeam current;
        if (!ReadRotatingBeam(ai, boss, candidate, current)) continue;
        if (selected) return EncounterPosition();
        selected = boss; plan = candidate; beam = current;
    }
    if (!selected) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    plan.destination = here;
    if ((beam.shelteredInWater || encounter::OutsideRotatingBeam(here, beam)) &&
        ValidateRotatingBeamDestination(ai, plan, beam)) return plan;
    if (!ai->CanMove()) return EncounterPosition();
    const float speed = bot->GetSpeed(MOVE_RUN);
    if (!std::isfinite(speed) || speed <= 0) return EncounterPosition();
    std::vector<encounter::Point> candidates;
    for (float distance : {4.0f, 8.0f, 12.0f, 20.0f})
    {
        encounter::Point best;
        float bestMargin = -1;
        encounter::RotatingBeam arrival = beam;
        arrival.sweep += beam.angularSpeed * distance / speed;
        for (unsigned direction = 0; direction < 16; ++direction)
        {
            const float angle = 2 * M_PI_F * direction / 16;
            encounter::Point point{here.x + distance * std::cos(angle), here.y + distance * std::sin(angle), here.z};
            if (!encounter::OutsideRotatingBeam(point, arrival)) continue;
            const float margin = std::fabs(std::remainder(std::atan2(point.y - beam.origin.y, point.x - beam.origin.x) -
                beam.orientation - arrival.sweep / 2, 2 * M_PI_F));
            if (margin > bestMargin) { best = point; bestMargin = margin; }
        }
        // Try a distinct distance on each bounded native route attempt, rather
        // than spending the entire budget on adjacent points at one distance.
        if (bestMargin >= 0) candidates.push_back(best);
    }
    // Each candidate has a generic hazard route check plus a beam crossing
    // check. Four candidates therefore cap native path queries at eight.
    unsigned checked = 0;
    for (const auto& point : candidates)
    {
        if (++checked > 4) break;
        plan.destination = point;
        if (ValidateRotatingBeamDestination(ai, plan, beam)) return plan;
    }
    return EncounterPosition();
}
