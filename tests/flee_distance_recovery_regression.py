"""Exercise the production candidate loop with blocked outer escape positions."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

source = (Path(__file__).resolve().parents[1] / 'playerbot/FleeManager.cpp').read_text()
body = block(source, 'void FleeManager::calculatePossibleDestinations(')
start = body.index('    float distIncrement =')
loop = body[start:body.rfind('}')]

code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <vector>
constexpr float M_PI_F = 3.14159265f, CONTACT_DISTANCE = 0.5f;
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
struct { float followDistance = 2, tooCloseDistance = 2; } sPlayerbotAIConfig;
float radius(float x, float y) { return std::sqrt(x*x+y*y); }
std::vector<float> inspected;
bool blockOuter = true, blockEverywhere = false, water = false, checkEdges = true;
struct TerrainInfo { bool IsInWater(float, float, float) const { return water; } } terrain;
struct Position { const TerrainInfo* getTerrain() const { return &terrain; } } startPosition;
struct Unit {
    bool IsWithinLOS(float, float, float, bool) { return !blockEverywhere; }
} enemy;
struct Bot {
    void* GetPlayerbotAI() { return nullptr; }
    void UpdateAllowedPositionZ(float, float, float& z) { z = 0; }
    float GetCollisionHeight() { return 1; }
} instance;
struct { bool IsDistanceLessThan(float a, float b) { return a < b; }
    bool IsDistanceGreaterOrEqualThan(float a, float b) { return a >= b; }
    float GetDistance2d(Bot*, float x, float y) { return radius(x,y); }
} sServerFacade;
struct MoveStyleValue { static bool CheckForEdges(void*) { return checkEdges; } };
struct FleePoint {
    float x,y,z,minDistance=0;
    FleePoint(void*,float a,float b,float c):x(a),y(b),z(c){}
};
bool intersectsOri(float, std::list<float>&, float) { return false; }
void calculateDistanceToCreatures(FleePoint* point) { point->minDistance = 10; }
bool isTooCloseToEdge(float x,float y,float,float) {
    float r = radius(x,y); inspected.push_back(r);
    return blockEverywhere || (blockOuter && r > 6.1f);
}
std::list<FleePoint*> candidates(bool forceMaxDistance) {
    Bot* bot = &instance; Unit* target = &enemy;
    float botPosX=0,botPosY=0,botPosZ=0,maxAllowedDistance=10;
    FleePoint start(nullptr,0,0,0);
    std::list<float> enemyOri;
    std::list<FleePoint*> points;
    __LOOP__
    return points;
}
void discard(std::list<FleePoint*>& points) { for (auto p:points) delete p; points.clear(); }
int main() {
    auto points = candidates(false);
    assert(!points.empty()); // Outer positions blocked, shorter ones usable.
    for (auto p:points) assert(radius(p->x,p->y) <= 6.1f);
    for (float wanted : {10.0f,8.0f,6.0f,4.0f,2.0f})
        assert(std::any_of(inspected.begin(),inspected.end(),[=](float r){return std::fabs(r-wanted)<0.01f;}));
    discard(points);
    points = candidates(true); assert(points.empty()); // Full-distance request cannot use the short escape.
    blockOuter = false;
    points = candidates(false);
    assert(std::any_of(points.begin(),points.end(),[](FleePoint* p){return radius(p->x,p->y)>9.9f;}));
    discard(points);
    water = true; points = candidates(false); assert(points.empty()); water = false;
    blockEverywhere = true; points = candidates(false); assert(points.empty());
    checkEdges = false; points = candidates(false); assert(points.empty()); // LOS still blocks.
    std::cout << "PASS: shorter escape when outer ring blocked; maximum-range, edge, water and LOS restrictions retained\n";
}
'''.replace('__LOOP__', loop)

with tempfile.TemporaryDirectory(prefix='mantech-flee-distance-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    for expansion in ('ZERO', 'ONE', 'TWO'):
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/DMANGOSBOT_' + expansion,
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
