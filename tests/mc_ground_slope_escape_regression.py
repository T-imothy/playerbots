"""Replay a native Gehennas rejected segment without weakening other hazards."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
methods='\n'.join(block(source,s) for s in ('inline bool IsFiniteMovementPoint(', 'inline bool IsHazardSafeSegment('))
signature='inline bool IsMoltenCoreGroundEscapeSegment('
methods+=('\n'+block(source,signature) if signature in source else '''
bool IsMoltenCoreGroundEscapeSegment(const WorldPosition&a,const WorldPosition&b,const std::list<HazardPosition>&h,const std::list<HazardPosition>&){return IsHazardSafeSegment(a,b,h);}
''')
code=r'''
#include <cassert>
#include <algorithm>
#include <cmath>
#include <limits>
#include <list>
#include <iostream>
using uint32=unsigned;
struct WorldPosition{unsigned map;float x,y,z;unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
__METHODS__
int main(){
 // Native raid1616645, healer140903: floor0.135 below the spell center.
 WorldPosition a{409,871.155f,-595.898f,-203.63f},b{409,878.546f,-592.836f,-202.724f};
 std::list<HazardPosition> fire{{{409,871.155f,-595.898f,-203.495f},11}};
 assert(!IsHazardSafeSegment(a,b,fire));
#ifdef MANGOSBOT_ZERO
 assert(IsMoltenCoreGroundEscapeSegment(a,b,fire,fire));
#else
 assert(!IsMoltenCoreGroundEscapeSegment(a,b,fire,fire));
#endif
 assert(!IsMoltenCoreGroundEscapeSegment(a,b,fire,{})); // provenance required
 auto foreign=fire;foreign.front().first.x+=1;assert(!IsMoltenCoreGroundEscapeSegment(a,b,fire,foreign));
 // Native Magmadar23202783: generic hazards retain the spell's 5yd radius,
 // while the verified same ground object adds body+3yd clearance. Both must
 // admit the same tiny uphill projection while leaving the fire horizontally.
 WorldPosition ma{409,1096.71f,-995.424f,-187.718f},mb{409,1104.71f,-995.784f,-186.258f};
 std::list<HazardPosition> nativeMag{{{409,1096.71f,-995.424f,-187.383f},8.208f}};
 auto bothMag=nativeMag;bothMag.push_back({nativeMag.front().first,5.0f});
 assert(!IsHazardSafeSegment(ma,mb,bothMag));
#ifdef MANGOSBOT_ZERO
 assert(IsMoltenCoreGroundEscapeSegment(ma,mb,bothMag,nativeMag));
#else
 assert(!IsMoltenCoreGroundEscapeSegment(ma,mb,bothMag,nativeMag));
#endif
 auto larger=bothMag;larger.back().second=9;
 assert(!IsMoltenCoreGroundEscapeSegment(ma,mb,larger,nativeMag));
 auto displaced=bothMag;displaced.back().first.x+=.01f;
 assert(!IsMoltenCoreGroundEscapeSegment(ma,mb,displaced,nativeMag));
 assert(!IsMoltenCoreGroundEscapeSegment(ma,mb,bothMag,{}));
 std::list<HazardPosition> overlap=fire;overlap.push_back({{409,875,-594,-203},1});
 assert(!IsMoltenCoreGroundEscapeSegment(a,b,overlap,fire)); // never enter a new area
 std::list<HazardPosition> centered{{{409,0,0,0},11}};
 assert(!IsMoltenCoreGroundEscapeSegment({409,2,0,0},{409,-4,0,0},centered,centered));
 assert(!IsMoltenCoreGroundEscapeSegment({409,0,0,1},{409,0.1f,0,0},centered,centered)); // real inward fall
 assert(!IsMoltenCoreGroundEscapeSegment({409,0,0,4},{409,8,0,-4},centered,centered)); // another floor
 assert(!IsMoltenCoreGroundEscapeSegment({409,-12,0,0},{409,12,0,0},centered,centered));
 assert(!IsMoltenCoreGroundEscapeSegment(a,{409,NAN,0,0},fire,fire));
 assert(!IsMoltenCoreGroundEscapeSegment(a,{469,b.x,b.y,b.z},fire,fire));
 for(unsigned map:{0,1,229,489,529,30,469,249,309,509,531,533}){
  a.map=b.map=map;fire.front().first.map=map;
  assert(!IsMoltenCoreGroundEscapeSegment(a,b,fire,fire));
 }
 assert(IsMoltenCoreGroundEscapeSegment({409,2,0,0},{409,12,0,0},centered,centered));
 std::cout<<"PASS: native ground slope escape with source, map, era, overlap, inward and floor guards\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-ground-slope-') as directory:
  p=Path(directory);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
