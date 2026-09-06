"""Execute native fall request and final dispatch guards for each core."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
for era in ('classic','tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior'
    motion=(core/'src/game/MotionGenerators/MotionMaster.cpp').read_text()
    source=(core/'src/game/Movement/MoveSplineInit.cpp').read_text()
    method=block(motion,'bool MotionMaster::MoveFall(')
    marker='if (args.flags.falling &&'
    guard=block(source,marker) if marker in source else ''
    if guard:
        assert source.index('args.path[0] = real_position;')<source.index(marker)<source.index('args.flags.enter_cycle =')
    code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr float INVALID_HEIGHT=-100000.0f,g_moveFallMinFallDistance=0.5f;
constexpr unsigned EVENT_FALL=19;
#define DEBUG_LOG(...) ((void)0)
struct Map{float floor=0;unsigned queries=0,lastPhase=0;unsigned GetId(){return 1;}
 float GetHeight(float x,float y,float z){assert(std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z));++queries;return floor;}
 float GetHeight(unsigned phase,float x,float y,float z){lastPhase=phase;return GetHeight(x,y,z);}};
struct Unit{float x=2,y=3,z=10;Map map;unsigned phase=8;float GetPositionX(){return x;}float GetPositionY(){return y;}
 float GetPositionZ(){return z;}Map*GetMap(){return &map;}unsigned GetPhaseMask(){return phase;}};
struct Point{float x=0,y=0,z=0;};
namespace Movement{
 struct MoveSplineInit{Point end;bool falling=false;explicit MoveSplineInit(Unit&){}
  void MoveTo(float x,float y,float z){end={x,y,z};}void SetFall(){falling=true;}};
}
struct FallMovementGenerator{Movement::MoveSplineInit init;unsigned event;bool flag;ObjectGuid guid;unsigned relay;
 FallMovementGenerator(Movement::MoveSplineInit i,unsigned e,bool f,ObjectGuid g,unsigned r):init(i),event(e),flag(f),guid(g),relay(r){}};
struct MotionMaster{Unit*m_owner;unsigned mutations=0;Point end;ObjectGuid guid=0;unsigned relay=0;
 bool MoveFall(ObjectGuid guid=0,unsigned relayId=0);
 void Mutate(FallMovementGenerator*g){assert(g->init.falling&&g->event==EVENT_FALL&&!g->flag);++mutations;
  end=g->init.end;guid=g->guid;relay=g->relay;delete g;}};
__METHOD__
struct Dispatch{struct Args{struct Flags{bool falling=false;}flags;std::vector<Point>path;}args;
 Point real_position;unsigned stops=0,launches=0;
 void Stop(bool force){assert(force);++stops;}
 int Launch(){args.path[0]=real_position;__GUARD__ ++launches;return 1;}};
int main(){
 Unit unit;MotionMaster motion{&unit};
 for(float floor:{10.0f,9.75f,10.75f,50.0f,INVALID_HEIGHT,INVALID_HEIGHT-1}){
  unit.map.floor=floor;assert(!motion.MoveFall(7,23));assert(motion.mutations==0);
 }
 for(float bad:{std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),-std::numeric_limits<float>::infinity()}){
  unit.map.floor=bad;assert(!motion.MoveFall());assert(motion.mutations==0);
  unit.map.floor=0;
  for(float Unit::*field:{&Unit::x,&Unit::y,&Unit::z}){
   const float previous=unit.*field;unit.*field=bad;const unsigned queries=unit.map.queries;
   assert(!motion.MoveFall()&&unit.map.queries==queries&&motion.mutations==0);unit.*field=previous;
  }
 }
 // Real descending falls retain the original threshold, destination and callback.
 unit.map.floor=9.5f;assert(motion.MoveFall(7,23)&&motion.mutations==1);
 assert(motion.end.x==2&&motion.end.y==3&&motion.end.z==9.5f&&motion.guid==7&&motion.relay==23);
 unit.map.floor=-10;assert(motion.MoveFall()&&motion.mutations==2);
 __PHASE__
 // The map position can lag the active spline. Reject an up/level fall after
 // launch replaces the first vertex with the mover's actual current position.
 for(float actualZ:{9.0f,9.5f,9.505f}){
  Dispatch dispatch;dispatch.args.flags.falling=true;dispatch.args.path={{2,3,10},{2,3,9.5f}};
  dispatch.real_position={4,5,actualZ};assert(dispatch.Launch()==0&&dispatch.stops==1&&dispatch.launches==0);
 }
 {Dispatch dispatch;dispatch.args.flags.falling=true;dispatch.args.path={{2,3,10},{2,3,9.5f}};
  dispatch.real_position={4,5,10};assert(dispatch.Launch()==1&&dispatch.stops==0&&dispatch.launches==1);}
 for(float actualZ:{9.0f,9.5f,10.0f}){
  Dispatch dispatch;dispatch.args.path={{2,3,10},{2,3,9.5f}};dispatch.real_position={4,5,actualZ};
  assert(dispatch.Launch()==1&&dispatch.stops==0); // Ordinary horizontal/uphill movement is unaffected.
 }
 std::cout<<"PASS: native falling rejects above-ground, invalid and stale destinations; valid falls preserve callbacks\n";
}
'''.replace('__METHOD__',method).replace('__GUARD__',guard).replace('__PHASE__',
        'assert(unit.map.lastPhase==unit.phase);' if era=='wotlk' else 'assert(unit.map.lastPhase==0);')
    with tempfile.TemporaryDirectory(prefix=f'mantech-fall-{era}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
