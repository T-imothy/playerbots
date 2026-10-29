#include "playerbot/playerbot.h"
#include "BroodlordFormation.h"
#include "ClassicRaidActions.h"
#include "BlackwingMovementSafety.h"
#include "MovementPathSafety.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;
namespace
{
    // Player-supplied wall stations. Native floor/path/LOS admission still owns
    // each move; none of these coordinates permit a teleport or a lower floor.
    const encounter::Point tankStation{-7576.969727f, -1027.872070f, 449.541107f};
    const encounter::Point rangedStation{-7569.050293f, -1030.786621f, 449.154907f};
    float BroodlordSpellRange(PlayerbotAI* ai, Unit* anchor, float& minimum)
    {
        Player* bot = ai->GetBot();
        const bool healer = ai->IsHeal(bot);
        const char* spell = nullptr;
        switch (bot->getClass())
        {
            case CLASS_MAGE: spell = "frostbolt"; break;
            case CLASS_WARLOCK: spell = "shadow bolt"; break;
            case CLASS_HUNTER: spell = "auto shot"; break;
            case CLASS_PRIEST: spell = healer ? "flash heal" : "mind blast"; break;
            case CLASS_DRUID: spell = healer ? "healing touch" : "wrath"; break;
            case CLASS_SHAMAN: spell = healer ? "healing wave" : "lightning bolt"; break;
            case CLASS_PALADIN: spell = "flash of light"; break;
        }
        float maximum = ai->GetRange("spell"); minimum = 0;
        if (spell) ai->GetSpellRange(spell, &maximum, &minimum);
        if (!std::isfinite(maximum) || !std::isfinite(minimum) || minimum < 0) return 0;
        return std::min(45.0f, maximum) - 1.0f;
    }
}

bool ai::BroodlordFormationPlan(PlayerbotAI* ai, Unit* boss, Unit* target, ClassicRaidPlan& plan)
{
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 469 || !boss || boss->GetEntry() != 12017 || target != boss ||
        !bot->IsInWorld() || !bot->IsAlive() || !bot->GetGroup() || ai->IsRealPlayer() ||
        bot->IsBeingTeleported() || bot->HasCharmer() || !boss->IsInWorld() || !boss->IsAlive() ||
        !bot->IsInMap(boss) || !boss->IsInCombat() || boss->HasCharmer()) return false;
    // Only organize an already engaged fight in this room. Broodlord evades
    // below 448.60 in all three native scripts, even when a path is walkable.
    if (boss->GetDistance(tankStation.x, tankStation.y, tankStation.z) > 60 ||
        bot->GetPositionZ() < 448.60f) return true;
    const bool holding = boss->GetVictim() == bot;
    const bool ranged = !holding && (ai->IsRanged(bot) || ai->IsHeal(bot));
    Unit* anchor = boss;
    if (ranged && ai->IsHeal(bot))
    {
        Unit* victim = boss->GetVictim();
        if (victim && victim->IsPlayer() && victim->IsInWorld() && victim->IsAlive() && bot->IsInMap(victim) &&
            static_cast<Player*>(victim)->GetGroup() == bot->GetGroup()) anchor = victim;
    }
    float minimum = 0;
    const float maximum = ranged ? BroodlordSpellRange(ai, anchor, minimum) :
        std::max(2.0f, boss->GetCombatReach() + bot->GetCombatReach() - 1.0f);
    const float blast = ranged ? NativeEncounterSpellRadius(23331) : 0;
    if (ranged && (!std::isfinite(blast) || blast <= 0 || blast > 45 || maximum <= minimum)) return true;
    EncounterPosition p; p.active = true; p.exclusive = false; p.map = 469; p.instance = bot->GetInstanceId();
    p.boss = boss->GetObjectGuid(); p.source = anchor->GetObjectGuid(); p.spell = 12017;
    auto endpoint = [&](const encounter::Point& point, bool transit) {
        if (point.z < 448.60f || std::fabs(point.z - tankStation.z) > 3.0f) return false;
        const float angle = std::atan2(point.y - boss->GetPositionY(), point.x - boss->GetPositionX());
        if (!holding && !transit && std::cos(angle - boss->GetOrientation()) > 0) return false;
        if (ranged)
        {
            if (std::hypot(point.x - boss->GetPositionX(), point.y - boss->GetPositionY()) < blast + 2 ||
                anchor->GetDistance(point.x, point.y, point.z) < minimum + 0.5f ||
                anchor->GetDistance(point.x, point.y, point.z) > maximum ||
                !anchor->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), true)) return false;
        }
        else if (!holding && boss->GetDistance(point.x, point.y, point.z) > maximum + (transit ? 4 : 1)) return false;
        return true;
    };
    auto legal = [&](const encounter::Point& point, bool transit = false) {
        if (!endpoint(point, transit)) return false;
        p.destination = point;
        if (!ValidateEncounterDestination(ai, p) || !endpoint(p.destination, transit)) return false;
        // Preserve the leash over the entire route, not just its endpoint.
        if (bot->GetDistance(p.destination.x, p.destination.y, p.destination.z) > 1)
        {
            std::vector<WorldPosition> path;
            if (!BuildBlackwingMovementPath(ai, WorldPosition(469, p.destination.x, p.destination.y, p.destination.z), path)) return false;
            WorldPosition previous(bot);
            std::list<HazardPosition> avoid;
            if (!holding) avoid.emplace_back(WorldPosition(boss), ranged ? blast + 2 : 1.0f);
            auto frontalRisk = [&](const WorldPosition& point) {
                const float dx = point.getX() - boss->GetPositionX(), dy = point.getY() - boss->GetPositionY();
                return std::max(0.0f, std::cos(std::atan2(dy, dx) - boss->GetOrientation())) *
                    std::max(0.0f, maximum + 3 - std::hypot(dx, dy));
            };
            float risk = (!holding && !ranged) ? frontalRisk(previous) : 0;
            for (const auto& step : path)
            {
                if (step.getZ() < 448.60f || (!holding && !IsHazardSafeSegment(previous, step, avoid))) return false;
                // A melee already in front may leave, but a safe flank route
                // cannot cut across cleave just because its endpoint is behind.
                if (!holding && !ranged)
                {
                    const unsigned samples = std::max(1u, unsigned(std::ceil(previous.distance(step) / 0.5f)));
                    for (unsigned i = 1; i <= samples; ++i)
                    {
                        const float t = float(i) / samples;
                        WorldPosition sample(469, previous.getX() + (step.getX()-previous.getX())*t,
                            previous.getY() + (step.getY()-previous.getY())*t,
                            previous.getZ() + (step.getZ()-previous.getZ())*t);
                        const float next = frontalRisk(sample);
                        if (next > risk + 0.05f) return false;
                        risk = next;
                    }
                }
                previous = step;
            }
        }
        return true;
    };
    if (holding)
    {
        if (legal(tankStation)) plan.position = p;
        return true;
    }
    std::vector<encounter::Point> candidates;
    if (ranged) candidates.push_back(rangedStation);
    const float radius = ranged ? blast + 2.5f : maximum;
    const float back = boss->GetOrientation() + float(M_PI);
    for (unsigned i = 0; i < 17; ++i)
    {
        const float offset = i == 0 ? 0 : ((i + 1) / 2) * 0.17f * (i % 2 ? 1 : -1);
        candidates.push_back({boss->GetPositionX() + radius * std::cos(back + offset),
            boss->GetPositionY() + radius * std::sin(back + offset), tankStation.z});
    }
    if (ranged)
        std::stable_sort(candidates.begin(), candidates.end(), [](const encounter::Point& a, const encounter::Point& b) {
            return encounter::Distance2d(a, rangedStation) < encounter::Distance2d(b, rangedStation);
        });
    for (const auto& point : candidates)
        if (legal(point)) { plan.position = p; return true; }
    // Move around the edge in short checked legs when the direct rear route
    // crosses the boss. These are approach waypoints, not new stack locations.
    const float angle = boss->GetAngle(bot);
    const float transitRadius = ranged ? std::min(maximum - 1, std::max(blast + 4,
        std::hypot(bot->GetPositionX()-boss->GetPositionX(), bot->GetPositionY()-boss->GetPositionY()))) : maximum + 3;
    for (float turn : {0.35f, -0.35f, 0.7f, -0.7f})
    {
        encounter::Point point{boss->GetPositionX() + transitRadius*std::cos(angle+turn),
            boss->GetPositionY() + transitRadius*std::sin(angle+turn), tankStation.z};
        const float before = std::cos(angle-boss->GetOrientation());
        if (std::cos(angle+turn-boss->GetOrientation()) >= before) continue;
        if (legal(point, true)) { plan.position = p; return true; }
    }
    // Failed flank admission must not release generic chase straight through
    // the boss. This holds movement only; spells/attacks and emergency escapes
    // retain their own admission and priorities.
    p.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    if (ValidateEncounterDestination(ai, p) && p.destination.z >= 448.60f &&
        bot->GetDistance(p.destination.x, p.destination.y, p.destination.z) <= 1.0f) plan.position = p;
    return true;
}
