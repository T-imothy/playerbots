"""Run actual Broodlord formation planner against geometry and native admission fixtures."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BroodlordFormation.cpp').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <vector>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr float M_PI=3.14159265358979323846f;
enum{CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_HUNTER=3,CLASS_PRIEST=5,CLASS_DRUID=11,CLASS_SHAMAN=7,CLASS_PALADIN=2};
struct Group{};struct Unit{
 virtual ~Unit()=default;float x=-7573.89f,y=-1035.25f,z=449.25f,o=1.965f;
 bool world=true,alive=true,combat=true,charm=false,player=false,los=true;unsigned map=469,instance=2,entry=12017,guid=10;Unit*victim=nullptr;
 bool IsPlayer(){return player;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}unsigned GetEntry(){return entry;}Unit*GetVictim(){return victim;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return o;}
 float GetCombatReach(){return 1.5f;}unsigned GetObjectGuid(){return guid;}
 float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 bool IsWithinLOS(float,float,float,bool){return los;}
};
struct Player:Unit{Group*group=nullptr;unsigned cls=CLASS_MAGE;bool teleport=false;
 Player(){player=true;guid=20;}bool IsInMap(Unit*u){return u&&u->map==map&&u->instance==instance;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned getClass(){return cls;}
 bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}float GetCollisionHeight(){return 2;}
};
namespace ai{
struct WorldPosition{unsigned map=469;float x=0,y=0,z=449.2f;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Unit*u):WorldPosition(u->map,u->x,u->y,u->z){}unsigned getMapId()const{return map;}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition&p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}};
using HazardPosition=std::pair<WorldPosition,float>;
struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination{};};
struct ClassicRaidPlan{EncounterPosition position;bool emergency=false,holdDamage=false;};
}
struct PlayerbotAI{Player*bot;bool real=false,ranged=true,heal=false,valid=true,path=true,lowPath=false,throughBoss=false;float range=40,min=0,adjust=0;unsigned checked=0;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return heal;}
 float GetRange(const char*){return range;}bool GetSpellRange(const char*,float*max,float*minimum){*max=range;*minimum=min;return true;}};
namespace ai{
float NativeEncounterSpellRadius(unsigned id){assert(id==23331);return 20;}
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){++a->checked;p.destination.z+=a->adjust;return a->valid;}
bool BuildBlackwingMovementPath(PlayerbotAI*a,const WorldPosition&d,std::vector<WorldPosition>&p){p={d};if(a->lowPath)p.insert(p.begin(),{469,d.x,d.y,448.5f});if(a->throughBoss)p.insert(p.begin(),{469,-7573.89f,-1035.25f,449.25f});return a->path;}
bool BroodlordFormationPlan(PlayerbotAI*,Unit*,Unit*,ClassicRaidPlan&);
__SEGMENTS__
}
__SOURCE__
int main(){
 Group group;Player bot,tank;bot.group=tank.group=&group;Unit boss;boss.victim=&tank;
 tank.x=-7576.969727f;tank.y=-1027.872070f;tank.z=449.541107f;
 bot.x=-7569.050293f;bot.y=-1030.786621f;bot.z=449.154907f;
 PlayerbotAI ai{&bot};ClassicRaidPlan plan;
 auto run=[&](){plan={};return BroodlordFormationPlan(&ai,&boss,&boss,plan);};
 assert(run()&&plan.position.active&&plan.position.spell==12017);
 auto p=plan.position.destination;
 assert(std::hypot(p.x-boss.x,p.y-boss.y)>=22);
 assert(boss.GetDistance(p.x,p.y,p.z)<=39);
 assert(std::cos(std::atan2(p.y-boss.y,p.x-boss.x)-boss.o)<=0); // Never stack in cleave.
 ai.range=23.6f;assert(run()&&plan.position.active);ai.adjust=7;
 assert(run()&&!plan.position.active);ai.adjust=0;ai.range=40; // Recheck cast range after floor projection.
 auto first=p;bot.x=p.x;bot.y=p.y;bot.z=p.z;assert(run());
 assert(ai::encounter::Distance2d(first,plan.position.destination)<0.01f); // Stable stack, no roster-driven spread.
 ai.heal=true;assert(run()&&plan.position.active&&plan.position.source==tank.guid);
 assert(tank.GetDistance(plan.position.destination.x,plan.position.destination.y,plan.position.destination.z)<=39);ai.heal=false;
 bot.cls=CLASS_HUNTER;ai.min=8;ai.range=35;assert(run()&&plan.position.active);
 assert(boss.GetDistance(plan.position.destination.x,plan.position.destination.y,plan.position.destination.z)>=8.5f);
 ai.range=15;assert(run()&&plan.position.active&&std::hypot(plan.position.destination.x-bot.x,plan.position.destination.y-bot.y)<0.01f);
 ai.range=40;ai.min=0; // No legal ranged cast station must not fall back to charging into Blast Wave.
 ai.ranged=false;assert(run()&&plan.position.active);
 assert(boss.GetDistance(plan.position.destination.x,plan.position.destination.y,plan.position.destination.z)<=3);
 boss.victim=&bot;assert(run()&&plan.position.active);
 assert(ai::encounter::Distance2d(plan.position.destination,{-7576.969727f,-1027.872070f,449.541107f})<0.01f);
 boss.victim=&tank;ai.ranged=true;ai.valid=false;assert(run()&&!plan.position.active);ai.valid=true;
 bot.x=-7569.050293f;bot.y=-1030.786621f;
 auto holdingHere=[&](){return plan.position.active&&std::hypot(plan.position.destination.x-bot.x,plan.position.destination.y-bot.y)<0.01f;};
 ai.path=false;assert(run()&&holdingHere());ai.path=true;
 ai.lowPath=true;assert(run()&&holdingHere());ai.lowPath=false;
 ai.throughBoss=true;assert(run()&&holdingHere()); // Safe endpoint never licenses crossing Blast Wave.
 ai.ranged=false;assert(run()&&holdingHere());ai.ranged=true;ai.throughBoss=false;
 ai.adjust=-2;assert(run()&&!plan.position.active);ai.adjust=0;
 boss.los=false;assert(run()&&holdingHere());boss.los=true;
 bot.teleport=true;assert(!run());bot.teleport=false;boss.alive=false;assert(!run());boss.alive=true;
 bot.instance=99;assert(!run());bot.instance=2;bot.map=409;assert(!run());bot.map=469;
 ai.real=true;assert(!run());ai.real=false;boss.entry=12468;assert(!run());boss.entry=12017;
 bot.z=448;assert(run()&&!plan.position.active);
 std::cout<<"PASS: actual Broodlord fixed tank station, stable safe ranged stack, native range, rear melee, floor/path/leash and lifecycle admission\n";
}
'''.replace('__SOURCE__',source).replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
safety=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
code=code.replace('__SEGMENTS__','\n'.join(block(safety,m) for m in ('inline bool IsFiniteMovementPoint(', 'inline bool IsHazardSafeSegment(')))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-broodlord-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
