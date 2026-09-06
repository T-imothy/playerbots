"""Exercise real encounter destination and whole-route hazard validation."""
from pathlib import Path
import subprocess,sys,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
p='playerbot/strategy/values/EncounterPositionValue.cpp'
source=(r/p).read_text()
if '--before' in sys.argv:
 source=subprocess.check_output(['git','-c','safe.directory='+r.as_posix(),'-C',str(r),'show','ae802751:'+p],text=True)
method=block(source,'bool ai::ValidateEncounterDestination(')
safety=(r/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
helpers='\n'.join(block(safety,n) for n in ('inline bool IsFiniteMovementPoint(', 'inline bool IsHazardSafeSegment('))
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <vector>
#include <algorithm>
#include <limits>
#include <iostream>
using uint32=unsigned;
struct Player {unsigned map=542,instance=1;float x=0,y=0,z=0,adjust=0;bool world=true,alive=true,teleport=false,charmed=false;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 void UpdateAllowedPositionZ(float,float,float& z){z+=adjust;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}};
struct WorldPosition {unsigned map=542;float x=0,y=0,z=0;static std::vector<WorldPosition> path;static bool legacyPath;
 WorldPosition()=default;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Player* b):map(b->map),x(b->x),y(b->y),z(b->z){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}
 bool canPathTo(const WorldPosition&,Player*)const{return legacyPath;}
 std::vector<WorldPosition> getPathStepFrom(const WorldPosition&,Player*,bool normal)const{assert(normal);return path;}
 bool isPathTo(const std::vector<WorldPosition>& p,float xy,float zz)const{
  if(p.empty())return false;const auto& q=p.back();return q.map==map&&std::hypot(q.x-x,q.y-y)<xy&&std::fabs(q.z-z)<zz;}
};
std::vector<WorldPosition> WorldPosition::path;bool WorldPosition::legacyPath=true;
using HazardPosition=std::pair<WorldPosition,float>;
struct Stored {std::list<HazardPosition> hazards;std::list<HazardPosition> Get(){return hazards;}};
struct Context {Stored stored;template<class T>Stored* GetValue(const char*){return &stored;}};
struct PlayerbotAI {Player bot;Context context;Player* GetBot(){return &bot;}Context* GetAiObjectContext(){return &context;}};
namespace ai {struct Point {float x=0,y=0,z=0;};struct EncounterPosition {bool active=true;unsigned map=542,instance=1;Point destination{10,0,0};};
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&);
__HELPERS__
}
using namespace ai;
__METHOD__
int main(){
 PlayerbotAI ai;EncounterPosition plan;auto& path=WorldPosition::path;auto& hazards=ai.context.stored.hazards;
 path={{542,0,0,0},{542,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 // A safe destination is not enough if its actual route crosses ground damage.
 hazards={{{542,5,0,0},2}};assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,0,5,0},{542,10,5,0},{542,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 // Outward escape from the current hazard is permitted, inward travel is not.
 hazards={{{542,-1,0,0},3}};path={{542,0,0,0},{542,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,-2,0,0},{542,10,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 hazards.clear();path.clear();assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,8,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{543,10,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 path.assign(257,WorldPosition(542,10,0,0));assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,std::numeric_limits<float>::quiet_NaN(),0,0},{542,10,0,0}};
 assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,10,0,0}};ai.bot.adjust=20;assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.adjust=0;plan.destination={10,0,0};ai.bot.teleport=true;assert(!ValidateEncounterDestination(&ai,plan));ai.bot.teleport=false;
 plan.instance=2;assert(!ValidateEncounterDestination(&ai,plan));plan.instance=1;
 plan.destination={0,0,0};path.clear();assert(ValidateEncounterDestination(&ai,plan));
 std::cout<<"PASS: actual encounter endpoint and bounded route validation, crossing/outward hazards and lifecycle gates\n";
}
'''.replace('__HELPERS__',helpers).replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-encounter-path-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
 subprocess.run([str(tmp/'test.exe')],check=True)
