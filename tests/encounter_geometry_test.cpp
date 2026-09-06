#include "../playerbot/strategy/EncounterGeometry.h"
#include <cassert>
#include <iostream>
using namespace ai::encounter;

int main()
{
    const Point portal{0, 0, 0}, boss{30, 0, 0};
    assert(InBeam({15, 1, 0}, portal, boss));
    assert(!InBeam({15, 3, 0}, portal, boss));
    assert(!InBeam({-1, 0, 0}, portal, boss));
    assert(!InBeam({31, 0, 0}, portal, boss));
    assert(!InBeam({15, 0, 10}, portal, boss));
    assert(!InBeam({0, 0, 0}, portal, portal));
    assert(InBeam(BeamPoint(portal, boss, 8), portal, boss));
    assert(!InBeam(BeamPoint(portal, boss, 8, 5), portal, boss));
    assert(!InBeam(BeamPoint(portal, boss, 8, -5), portal, boss));
    for (unsigned direction = 0; direction < 8; ++direction)
    {
        const float angle = direction * 3.14159265358979323846f / 4;
        const Point origin{19, -37, -85}, player{13, -28, -87};
        for (int side : {-1, 1})
        {
            const Point escape = OutsideLine(player, origin, angle, 23, side);
            assert(std::fabs(LineDistance(escape, origin, angle) - 23) < 0.0001f);
            assert(escape.z == player.z); // Never copy the flying boss's altitude.
            const float alongBefore = (player.x-origin.x)*std::cos(angle) + (player.y-origin.y)*std::sin(angle);
            const float alongAfter = (escape.x-origin.x)*std::cos(angle) + (escape.y-origin.y)*std::sin(angle);
            assert(std::fabs(alongBefore - alongAfter) < 0.0001f);
        }
    }

    const std::vector<Circle> circles{{{0,0,0},20},{{20,0,0},18}};
    const auto escapes = EscapeCircles({0,0,-85},circles);
    assert(!escapes.empty());
    float previous = 0;
    for (const auto& point : escapes)
    {
        assert(OutsideCircles(point,circles));
        assert(point.z == -85);
        const float distance = Distance2d({0,0,-85},point);
        assert(distance >= previous); previous = distance;
    }
    assert(EscapeCircles({0,0,0}, {{{0,0,0},100}}).empty()); // No fabricated nearby safe point.
    const auto alreadySafe = EscapeCircles({50,50,0}, circles);
    assert(alreadySafe.size()==1 && Distance2d(alreadySafe.front(),{50,50,0})==0);

    BeamMember tank, caster, healer, spare;
    tank.guid = 1; tank.tank = true;
    caster.guid = 2; caster.caster = true;
    healer.guid = 3; healer.healer = true;
    spare.guid = 4; spare.tank = true;
    std::vector<BeamMember> group{healer, spare, tank, caster};
    const std::array<bool, 3> all{{true, true, true}};
    auto plan = AssignBeams(group, all);
    assert((plan == std::array<uint64_t, 3>{{1, 2, 3}}));
    std::reverse(group.begin(), group.end());
    assert(AssignBeams(group, all) == plan); // independent of group iteration order
    tank.exhausted[0] = true;
    assert(AssignBeams({tank, spare, caster, healer}, all)[0] == 4);
    tank.exhausted[0] = false; tank.stacks[0] = 30;
    assert(AssignBeams({tank, spare, caster, healer}, all)[0] == 4);
    tank.stacks[0] = 0; spare.stacks[0] = 10; spare.inside[0] = true;
    assert(AssignBeams({tank, spare, caster, healer}, all)[0] == 4); // retain blocker
    spare.human = true;
    assert(AssignBeams({tank, spare, caster, healer}, all)[0] == 4);
    spare.inside[0] = false;
    assert(AssignBeams({tank, spare, caster, healer}, all)[0] == 1); // never move human
    caster.healer = true;
    assert(AssignBeams({tank, caster}, all)[2] == 0); // no double assignment
    assert((AssignBeams(group, {{false, false, false}}) == std::array<uint64_t, 3>{{0, 0, 0}}));
    caster.stacks[1] = 25;
    assert(AssignBeams({tank, caster, healer}, all)[1] == 0); // no forced exhaustion bypass
    healer.noMana = true; healer.stacks[2] = 40;
    assert(AssignBeams({healer}, all)[2] == 3);
    std::cout << "PASS: finite beam geometry, role assignment, stable ownership, human reservation, exhaustion, stacks, no double assignment and phase cleanup\n";
}
