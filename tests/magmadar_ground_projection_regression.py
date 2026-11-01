"""Production hazard geometry: native floor projection must not deadlock escape."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
safety=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text().replace('#pragma once','').replace('#include "playerbot/strategy/values/HazardsValue.h"','')
code=r'''#include <cassert>
#include <cstdint>
#include <list>
#include <limits>
#include <iostream>
using uint32=uint32_t;
namespace ai {
struct WorldPosition {uint32 m;float x,y,z;uint32 getMapId()const{return m;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
}
__SAFETY__
using namespace ai;
int main(){
 // Captured Magmadar route: actor inside margin, first native point at same XY.
 WorldPosition a{409,1142.89f,-1007.55f,-185.347f},b{409,1142.89f,-1007.55f,-185.512f};
 std::list<HazardPosition> fire={{{409,1138.54f,-1012.86f,-186.025f},8.372f}};
 assert(!IsHazardSafeSegment(a,b,fire));assert(IsHazardSafeGroundProjection(a,b,fire));
 WorldPosition outward{409,1150,-1000,-185.5f};assert(IsHazardSafeSegment(b,outward,fire));
 WorldPosition inward{409,1140,-1009,-185.5f};assert(!IsHazardSafeGroundProjection(b,inward,fire));
 // Crossing, re-entry, map mismatch, nonfinite values and large vertical jumps remain rejected.
 std::list<HazardPosition> h={{{409,0,0,0},5}};
 assert(!IsHazardSafeGroundProjection({409,-10,0,0},{409,10,0,0},h));
 assert(!IsHazardSafeGroundProjection({409,4,0,4},{409,4,0,2},h));
 assert(!IsHazardSafeGroundProjection({409,1,0,4},{409,1,0,1},h));
 assert(!IsHazardSafeGroundProjection({409,1,0,1},{469,1,0,0},h));
 assert(!IsHazardSafeGroundProjection({409,1,0,1},{409,1,0,std::numeric_limits<float>::quiet_NaN()},h));
 h.push_back({{409,4,0,-4},4.5f});
 assert(!IsHazardSafeGroundProjection({409,4,0,1},{409,4,0,0},h)); // entering second overlapping hazard
 // Projection cannot legalize an inward segment later in the route.
 assert(!IsHazardSafeSegment({409,4,0,1},{409,4,0,0},{{{409,0,0,0},5}}));
 std::cout<<"PASS: captured floor projection, outward continuation, inward/crossing/new-hazard/invalid-path rejection\n";
}
'''.replace('__SAFETY__',safety)
with tempfile.TemporaryDirectory(prefix='mantech-ground-projection-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
