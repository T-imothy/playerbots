#include "PartyPositioningPolicy.h"
#include <cassert>
#include <iostream>

using namespace ai::party_positioning;
int main()
{
    const auto visible = [](const Point&) { return true; };
    const Point pack = {10, 0, 0};
    // Safe endpoints alone are insufficient: the middle of this path pulls.
    assert(CrossesBoundary({{0,0,0}, {20,0,0}}, pack, 3, visible));
    assert(!CrossesBoundary({{0,0,0}, {0,10,0}, {20,10,0}, {20,0,0}}, pack, 3, visible));
    // Shorter/sideways retreats can be safe even when the ideal retreat is not.
    assert(!CrossesBoundary({{0,0,0}, {4,0,0}}, pack, 3, visible));
    assert(CrossesBoundary({{0,0,0}, {8,0,0}}, pack, 3, visible));
    assert(!CrossesBoundary({{0,0,0}, {0,8,0}}, pack, 3, visible));
    // An existing danger must not trap the bot or allow it to move deeper.
    assert(!CrossesBoundary({{8,0,0}, {6,0,0}, {0,0,0}}, pack, 3, visible));
    assert(CrossesBoundary({{8,0,0}, {9,0,0}, {0,0,0}}, pack, 3, visible));
    assert(CrossesBoundary({{8,0,0}, {0,0,0}, {8,0,0}}, pack, 3, visible));
    // Walls/other floors do not become imaginary pulls. A corner becoming
    // visible during movement must be checked from the candidate position.
    assert(!CrossesBoundary({{0,0,0}, {20,0,0}}, pack, 3, [](const Point&) { return false; }));
    assert(!CrossesBoundary({{0,0,20}, {20,0,20}}, pack, 3, visible));
    assert(CrossesBoundary({{0,0,0}, {20,0,0}}, pack, 3, [](const Point& p) { return p.x > 8; }));
    // Patrol movement invalidates a formerly safe, committed route.
    const std::vector<Point> route = {{0,0,0}, {0,10,0}};
    assert(!CrossesBoundary(route, pack, 3, visible));
    assert(CrossesBoundary(route, {0,5,0}, 3, visible));
    // Aggro-disabled units have no boundary. Higher-level aggro radii matter.
    assert(!CrossesBoundary(route, {0,5,0}, 0, visible));
    assert(!CrossesBoundary(route, {12,5,0}, 5, visible));
    assert(CrossesBoundary(route, {12,5,0}, 15, visible));
    // Safety outranks a shorter route/ideal casting distance, including when
    // emergency choices must compare the number of additional enemies pulled.
    assert((Score{0, 100}.BetterThan(Score{1, 1})));
    assert((Score{1, 100}.BetterThan(Score{2, 1})));
    assert((Score{0, 5}.BetterThan(Score{0, 10})));
    // Hard ability minimums remain constraints; a suboptimal but usable range
    // is accepted, and retreat must actually improve separation.
    assert(!FitsRange(5, 8, 30, 3, true));
    assert(FitsRange(9, 8, 30, 3, true));
    assert(FitsRange(12, 0, 30, 35, false));
    assert(!FitsRange(31, 0, 30, 35, false));
    assert(!FitsRange(9, 0, 30, 10, true));
    assert(FitsRange(12, 0, 30, 10, true));
    // Deterministic geometry cross-check against the analytic closest point
    // on a segment, independent of the production sampling implementation.
    unsigned seed = 233;
    const auto coordinate = [&]()
    {
        seed = 1664525u * seed + 1013904223u;
        return float(seed % 40001) / 1000.0f - 20.0f;
    };
    for (unsigned i = 0; i < 10000; ++i)
    {
        const Point a = {coordinate(), coordinate(), coordinate()};
        const Point b = {coordinate(), coordinate(), coordinate()};
        if (DistanceSquared(a, pack) <= 12.25f)
            continue; // Starting outside the buffered boundary: no escape exemption.
        const Point direction = {b.x-a.x, b.y-a.y, b.z-a.z};
        const float lengthSq = DistanceSquared(a, b);
        if (lengthSq == 0)
            continue;
        const float t = std::max(0.0f, std::min(1.0f,
            ((pack.x-a.x)*direction.x + (pack.y-a.y)*direction.y + (pack.z-a.z)*direction.z) / lengthSq));
        if (DistanceSquared(Between(a, b, t), pack) < 9.0f)
            assert(CrossesBoundary({a,b}, pack, 3, visible));
    }
    std::cout << "25 party positioning scenarios and 10000 generated path checks passed\n";
}
