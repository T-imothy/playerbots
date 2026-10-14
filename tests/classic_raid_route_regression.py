"""Actual native route admission for possessed worshippers and local tank lanes."""
from pathlib import Path
import tempfile,subprocess
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <vector>
#include <algorithm>
#include "__GEOMETRY__"
using namespace ai;using uint32=unsigned;constexpr float M_PI_F=3.14159265359f;constexpr unsigned PATHFIND_NORMAL=1,FORCED_MOVEMENT_RUN=1;
struct Spline{bool done=true;bool Finalized(){return done;}};
struct Motion{unsigned moves=0;void MovePoint(unsigned,float,float,float,unsigned,bool){++moves;}};
struct Unit{float x=0,y=0,z=0;bool near=false,los=true;Spline spline;Spline*movespline=&spline;Motion motion;
 bool IsWithinDistInMap(Unit*,float){return near;}bool IsWithinLOSInMap(Unit*){return los;}float GetAngle(Unit*){return 0;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}unsigned GetMapId(){return 533;}
 void UpdateAllowedPositionZ(float,float,float& height){height=z;}Motion*GetMotionMaster(){return &motion;}};
using Player=Unit;
struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}WorldPosition(Unit*u):WorldPosition(u->GetMapId(),u->x,u->y,u->z){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
struct Value{std::list<HazardPosition>hazards;auto Get(){return hazards;}};struct Context{Value value;template<class T>Value*GetValue(const char*){return &value;}};
struct PlayerbotAI{Player bot;Context context;Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}};
struct PathFinder{static bool accepted;static unsigned type;static std::vector<encounter::Point>points;Unit*unit;PathFinder(Unit*u):unit(u){}
 bool calculate(float,float,float,bool){return accepted;}unsigned getPathType(){return type;}auto&getPath(){return points;}};
bool PathFinder::accepted=true;unsigned PathFinder::type=PATHFIND_NORMAL;std::vector<encounter::Point>PathFinder::points={{0,0,0},{10,0,0}};
struct EncounterPosition{encounter::Point destination;};
__SEGMENT__
__HELPERS__
int main(){PlayerbotAI a;Unit charm,boss;boss.x=20;
 assert(!ControlledInRadius(&a,&charm,&boss,0));assert(charm.motion.moves==0);
 charm.near=true;assert(ControlledInRadius(&a,&charm,&boss,15));charm.near=false;
 charm.spline.done=false;assert(!ControlledInRadius(&a,&charm,&boss,15)&&charm.motion.moves==0);charm.spline.done=true;
 PathFinder::accepted=false;assert(!ControlledInRadius(&a,&charm,&boss,15)&&charm.motion.moves==0);PathFinder::accepted=true;
 PathFinder::type=2;assert(!ControlledInRadius(&a,&charm,&boss,15)&&charm.motion.moves==0);PathFinder::type=1;
 a.context.value.hazards.emplace_back(WorldPosition(533,5,0,0),2);assert(!ControlledInRadius(&a,&charm,&boss,15)&&charm.motion.moves==0);
 a.context.value.hazards.clear();assert(!ControlledInRadius(&a,&charm,&boss,15)&&charm.motion.moves==1); // movement submission is not arrival
 charm.near=true;charm.los=false;assert(!ControlledInRadius(&a,&charm,&boss,15));charm.los=true;assert(ControlledInRadius(&a,&charm,&boss,15));
 EncounterPosition p{{10,0,0}};std::vector<encounter::Circle> circles{{{5,0,0},2}};
 assert(!LocalCircleRoute(&a,p,circles));PathFinder::points={{0,0,0},{0,5,0},{10,5,0},{10,0,0}};assert(LocalCircleRoute(&a,p,circles));
 PathFinder::points={{5,0,0},{10,0,0}};a.bot.x=5;assert(LocalCircleRoute(&a,p,circles)); // outward egress
 PathFinder::points={{5,0,0},{4,0,0},{10,0,0}};assert(!LocalCircleRoute(&a,p,circles));
}
'''
path=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
code=code.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
code=code.replace('__SEGMENT__',block(path,'    inline bool IsFiniteMovementPoint(')+'\n'+block(path,'    inline bool IsHazardSafeSegment('))
code=code.replace('__HELPERS__',block(s,'    bool ControlledInRadius(')+'\n'+block(s,'    bool LocalCircleRoute('))
with tempfile.TemporaryDirectory(prefix='classic-routes-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS actual controlled approach and tank-route rejection/egress; submission waits for actual native arrival')
