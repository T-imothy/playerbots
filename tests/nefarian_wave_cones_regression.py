"""Exercise actual all-drakonid cone and route geometry, not native fight acceptance."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
geometry=(root/'playerbot/strategy/EncounterGeometry.h').as_posix()
code='''
#include <cassert>
#include <cmath>
#include <algorithm>
#include <vector>
#include <iostream>
#include "'''+geometry+'''"
using namespace ai;
struct NefariusCone {encounter::Point center;float facing,radius;};
'''+block(s,'    bool NefariusConeContains(')+block(s,'    bool NefariusConeSegmentSafe(')+r'''
int main(){
 NefariusCone east{{0,0,0},0,16};
 assert(NefariusConeContains(east,{5,0,0}));
 assert(!NefariusConeContains(east,{-5,0,0}));
 assert(!NefariusConeContains(east,{17,0,0}));
 assert(!NefariusConeContains(east,{5,0,9}));
 assert(!NefariusConeSegmentSafe(east,{20,-20,0},{1,1,0}));
 assert(!NefariusConeSegmentSafe(east,{5,-20,0},{5,20,0})); // safe endpoints cross the cone
 assert(!NefariusConeSegmentSafe(east,{-10,0,0},{20,0,0}));
 assert(NefariusConeSegmentSafe(east,{-5,-20,0},{-5,20,0}));
 assert(NefariusConeSegmentSafe(east,{5,0,0},{20,0,0})); // outward escape
 assert(NefariusConeSegmentSafe(east,{5,0,0},{-5,0,0})); // rear boundary escape
 assert(NefariusConeSegmentSafe(east,{5,0,0},{5,20,0})); // sidestep
 assert(!NefariusConeSegmentSafe(east,{1,12,0},{2,5,0})); // deeper in both boundaries
 assert(NefariusConeSegmentSafe(east,{5,-20,9},{5,20,9}));
 assert(!NefariusConeSegmentSafe(east,{5,0,9},{5,0,0}));
 NefariusCone west{{30,0,0},3.14159265359f,16};
 assert(!NefariusConeContains(east,{20,0,0})&&NefariusConeContains(west,{20,0,0}));
 // Escaping one drakonid cannot enter the frontal of another.
 assert(NefariusConeSegmentSafe(east,{5,0,0},{20,0,0}));
 assert(!NefariusConeSegmentSafe(west,{5,0,0},{20,0,0}));
 std::cout<<"PASS cone range/facing/floor, multi-drakonid overlap, safe endpoint crossing, outward/rear escape, and rejected inward route\n";
}
'''
formation=block(s,'    bool NefariusWaveFormation(')
assert 'NefariusWaveTarget(ai,target) || ai->IsTank(bot)' in formation
assert 'for (ObjectGuid guid:nearby)' in formation
assert 'NefariusConeRoute(ai,p,cones)' in formation
assert 'PositionLegal(ai,anchor,p,' in formation
assert '++paths>8' in formation
assert 'safe(p.destination)' in formation
calculate=block(s,'ClassicRaidPlan ClassicRaidPlanValue::Calculate(')
assert calculate.index('NefariusWaveFormation(')<calculate.index('const bool waveCone')
with tempfile.TemporaryDirectory(prefix='nef-cones-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
