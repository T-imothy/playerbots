#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "HazardsValue.h"
#include "playerbot/ServerFacade.h"
#include "Spells/SpellMgr.h"
#include "playerbot/strategy/actions/MovementPathSafety.h"

using namespace ai;

float ai::NativeEncounterSpellRadius(uint32 id, unsigned depth)
{
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
    if (!spell) return 0;
    float radius = 0;
    for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
    {
        radius = std::max(radius, GetSpellRadius(sSpellRadiusStore.LookupEntry(spell->EffectRadiusIndex[effect])));
        if (depth < 2 && spell->EffectTriggerSpell[effect] && spell->EffectTriggerSpell[effect] != id)
            radius = std::max(radius, NativeEncounterSpellRadius(spell->EffectTriggerSpell[effect], depth + 1));
    }
    return radius;
}

bool ai::ValidateEncounterDestination(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    auto& point = plan.destination;
    if (!plan.active || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() ||
        !std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z)) return false;
    const float originalZ = point.z;
    bot->UpdateAllowedPositionZ(point.x, point.y, point.z);
    if (!std::isfinite(point.z) || std::fabs(point.z - originalZ) > 8.0f ||
        bot->GetDistance(point.x, point.y, point.z) > 60) return false;
    const WorldPosition destination(plan.map, point.x, point.y, point.z);
    auto hazards = ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Get();
    if (plan.map == 531)
    {
        EncounterPosition current;
        std::vector<encounter::Circle> whirlwinds;
        AQWhirlwindThreats(ai, current, whirlwinds);
        // Keep one yard of route clearance and two at the endpoint. These
        // moving native auras need not have entered the stored hazard cache.
        for (const auto& circle : whirlwinds)
            hazards.emplace_back(WorldPosition(plan.map, circle.center.x, circle.center.y, circle.center.z), circle.radius - 1);
    }
    for (const auto& hazard : hazards)
        if (destination.distance(hazard.first) < hazard.second + 1) return false;
    if (bot->GetDistance(point.x, point.y, point.z) <= 1.0f) return true;
    // A safe endpoint can still require crossing a void zone. Check one bounded
    // native normal route; incomplete/shortcut paths cannot establish safety.
    const auto path = destination.getPathStepFrom(WorldPosition(bot), bot, true);
    if (path.size() < 2 || path.size() > 256 || !destination.isPathTo(path, 1.0f, 2.0f)) return false;
    WorldPosition previous(bot);
    for (const WorldPosition& waypoint : path)
    {
        if (!IsHazardSafeSegment(previous, waypoint, hazards)) return false;
        previous = waypoint;
    }
    return true;
}

EncounterPosition NetherspitePositionValue::Calculate()
{
    EncounterPosition result;
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 532 || !bot->IsInCombat() || !bot->GetGroup()) return result;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && bot->IsInMap(unit) &&
            unit->GetEntry() == 15689 && unit->IsAlive() && unit->IsInCombat()) { boss = unit; break; }
    }
    // The native shadowform marks banish, when there are no beams to intercept.
    if (!boss || boss->HasAura(38542)) return result;
    const std::array<uint32, 3> entries{{17369, 17368, 17367}};
    const std::array<uint32, 3> buffs{{30421, 30423, 30422}};
    const std::array<uint32, 3> exhaustion{{38637, 38639, 38638}};
    std::array<Unit*, 3> portals{{nullptr, nullptr, nullptr}};
    std::array<bool, 3> present{{false, false, false}};
    const encounter::Point bossPoint{boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()};
    std::array<encounter::Point, 3> portalPoints;
    for (unsigned color = 0; color < 3; ++color)
    {
        std::list<Unit*> nearby;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, entries[color], 100.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(nearby, check);
        Cell::VisitAllObjects(bot, searcher, 100.0f);
        for (Unit* portal : nearby)
            if (portal && portal->IsInWorld() && bot->IsInMap(portal) && portal->IsAlive() &&
                portal->GetSpawnerGuid() == boss->GetObjectGuid())
            {
                portals[color] = portal;
                portalPoints[color] = {portal->GetPositionX(), portal->GetPositionY(), portal->GetPositionZ()};
                present[color] = encounter::Distance2d(portalPoints[color], bossPoint) > 5;
                break;
            }
    }
    if (!present[0] && !present[1] && !present[2]) return result;
    std::vector<encounter::BeamMember> members;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* player = ref->getSource();
        if (!player || !player->IsInWorld() || !bot->IsInMap(player) ||
            !player->IsAlive() || player->IsBeingTeleported() || !player->GetSession() ||
            player->GetGroup() != bot->GetGroup() ||
            player->GetDistance(boss) > 100 || player->HasCharmer()) continue;
        encounter::BeamMember member;
        member.guid = player->GetObjectGuid().GetRawValue();
        member.human = !player->GetPlayerbotAI() || player->GetPlayerbotAI()->IsRealPlayer();
        member.tank = ai->IsTank(player);
        member.healer = ai->IsHeal(player);
        member.caster = ai->IsRanged(player) && !member.healer && player->getClass() != CLASS_HUNTER;
        member.noMana = player->GetMaxPower(POWER_MANA) == 0;
        const encounter::Point position{player->GetPositionX(), player->GetPositionY(), player->GetPositionZ()};
        for (unsigned color = 0; color < 3; ++color)
        {
            member.exhausted[color] = player->HasAura(exhaustion[color]);
            if (Aura* aura = ai->GetAura(buffs[color], player)) member.stacks[color] = aura->GetStackAmount();
            member.inside[color] = present[color] && encounter::InBeam(position, portalPoints[color], bossPoint);
        }
        members.push_back(member);
    }
    const auto assigned = encounter::AssignBeams(members, present);
    const uint64 self = bot->GetObjectGuid().GetRawValue();
    auto own = std::find_if(members.begin(), members.end(), [self](const encounter::BeamMember& member) { return member.guid == self; });
    if (own == members.end() || own->human) return result;
    int chosen = -1;
    float side = 0;
    for (unsigned color = 0; color < 3; ++color)
        if (assigned[color] == self) { chosen = color; break; }
    if (chosen < 0)
        for (unsigned color = 0; color < 3; ++color)
            if (present[color] && (own->inside[color] || own->stacks[color]))
            {
                chosen = color;
                // Step aside; native expiration applies Exhaustion. Never remove
                // the buff or exhaustion ourselves, including when no relief exists.
                const auto plus = encounter::BeamPoint(portalPoints[color], bossPoint, 18, 5);
                const auto minus = encounter::BeamPoint(portalPoints[color], bossPoint, 18, -5);
                const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
                side = encounter::Distance2d(here, plus) <= encounter::Distance2d(here, minus) ? 5 : -5;
                break;
            }
    if (chosen < 0) return result;
    const float reach = std::max(3.0f, std::min(8.0f, boss->GetCombatReach() + bot->GetCombatReach() - 1.0f));
    result.destination = encounter::BeamPoint(portalPoints[chosen], bossPoint, chosen == 0 ? reach : 18.0f, side);
    result.active = true;
    result.map = bot->GetMapId();
    result.instance = bot->GetInstanceId();
    result.boss = boss->GetObjectGuid();
    result.source = portals[chosen]->GetObjectGuid();
    if (!ValidateEncounterDestination(ai, result))
    {
        // A void zone can occupy the normal point. Try another actual point
        // along the beam; never stand in the damage or force a straight path.
        bool found = false;
        for (const float distance : {12.0f, 24.0f, 6.0f})
        {
            result.destination = encounter::BeamPoint(portalPoints[chosen], bossPoint, distance, side);
            if (ValidateEncounterDestination(ai, result)) { found = true; break; }
        }
        result.active = found;
    }
#endif
    return result;
}
