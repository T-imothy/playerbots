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
helpers='\n'.join(block(safety,n) for n in ('inline bool IsFiniteMovementPoint(', 'inline bool IsHazardSafeSegment(', 'inline bool IsMoltenCoreGroundEscapeSegment(', 'inline bool IsHazardSafeGroundProjection(', 'inline bool IsOnyxiaBreathSafeSegment('))
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
 bool pursuit=false,combat=true;bool IsInCombat(){return combat;}bool IsInMap(Player*u){return u&&u->map==map&&u->instance==instance;}
 unsigned entry=0;bool cloud=false;unsigned GetEntry(){return entry;}bool HasAura(unsigned id){return id==29350&&cloud;}float GetCombatReach(){return 1.5f;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 void UpdateAllowedPositionZ(float,float,float& z){z+=adjust;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}};
using Unit=Player;
struct WorldPosition {unsigned map=542;float x=0,y=0,z=0;static std::vector<WorldPosition> path;static bool legacyPath,liquid;
 WorldPosition()=default;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Player* b):map(b->map),x(b->x),y(b->y),z(b->z){}
 bool isInWater()const{return liquid;}bool isUnderWater()const{return false;}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}
 bool canPathTo(const WorldPosition&,Player*)const{return legacyPath;}
 std::vector<WorldPosition> getPathStepFrom(const WorldPosition&,Player*,bool normal)const{assert(normal);return path;}
 bool isPathTo(const std::vector<WorldPosition>& p,float xy,float zz)const{
  if(p.empty())return false;const auto& q=p.back();return q.map==map&&std::hypot(q.x-x,q.y-y)<xy&&std::fabs(q.z-z)<zz;}
};
std::vector<WorldPosition> WorldPosition::path;bool WorldPosition::legacyPath=true;bool WorldPosition::liquid=false;
using HazardPosition=std::pair<WorldPosition,float>;
struct Stored {std::list<HazardPosition> hazards;std::list<HazardPosition> Get(){return hazards;}};
struct Context {Stored stored;template<class T>Stored* GetValue(const char*){return &stored;}};
enum class BotState {BOT_STATE_COMBAT};
struct PlayerbotAI {bool tank=false,healer=false,ranged=false;bool IsTank(Player*){return tank;}bool IsHeal(Player*){return healer;}bool IsRanged(Player*){return ranged;}bool magmadar=false;bool HasStrategy(const char*,BotState){return magmadar;}Player bot;Unit*pursuer=nullptr;Unit*GetUnit(unsigned){return pursuer;}Context context;Player* GetBot(){return &bot;}Context* GetAiObjectContext(){return &context;}};
namespace ai {bool RaidLabMovementResult(Player*,const char*,unsigned,bool r){return r;}
struct Point {float x=0,y=0,z=0;};struct EncounterPosition {bool active=true;unsigned map=542,instance=1,boss=0,spell=0;Point destination{10,0,0};};
unsigned CurrentBossPursuitSpell(Player*,Unit*b){return b->pursuit?24646:0;}
float BossEscapeDistance(Player*,Unit*,unsigned){return 14;}
float NativeEncounterSpellRadius(unsigned id){assert(id==29310||id==30122);return id==29310?25:20;}
namespace encounter {struct Circle {Point center;float radius;};}
std::list<HazardPosition> ground;
void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>& out){out.insert(out.end(),ground.begin(),ground.end());}
void AppendBlackwingGroundHazards(PlayerbotAI*,std::list<HazardPosition>&){}
std::vector<encounter::Circle> whirlwinds;
std::vector<encounter::Circle> onyxiaBreath;
bool OnyxiaBreathThreats(unsigned id,std::vector<encounter::Circle>& out){if(id!=17086)return false;out=onyxiaBreath;return !out.empty();}
bool AQWhirlwindThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>& out){out=whirlwinds;return !out.empty();}
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&,bool requireWalkingPath=true);
bool LavaTrashRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&){return true;}
bool bwlRouteSafe=true;
bool BlackwingMovementRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&){return bwlRouteSafe;}
bool MadnessFormationRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&,Unit*){return true;}
bool domoRouteSafe=true;bool MajordomoFormationRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&,Unit*){return domoRouteSafe;}
__HELPERS__
}
using namespace ai;
__METHOD__
int main(){
 PlayerbotAI ai;EncounterPosition plan;auto& path=WorldPosition::path;auto& hazards=ai.context.stored.hazards;
 path={{542,0,0,0},{542,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 ai.bot.map=plan.map=409;path={{409,0,0,0},{409,10,0,0}};
 domoRouteSafe=false;assert(!ValidateEncounterDestination(&ai,plan));assert(!ValidateEncounterDestination(&ai,plan,false));
 domoRouteSafe=true;assert(ValidateEncounterDestination(&ai,plan));
 ai.bot.map=plan.map=542;path={{542,0,0,0},{542,10,0,0}};
 // A safe destination is not enough if its actual route crosses ground damage.
 hazards={{{542,5,0,0},2}};assert(!ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,0,5,0},{542,10,5,0},{542,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 // Outward escape from the current hazard is permitted, inward travel is not.
 hazards={{{542,-1,0,0},3}};path={{542,0,0,0},{542,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{542,0,0,0},{542,-2,0,0},{542,10,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 hazards.clear();path.clear();assert(!ValidateEncounterDestination(&ai,plan));
 assert(ValidateEncounterDestination(&ai,plan,false)); // landing admission does not imply a legal walk
 hazards={{{542,10,0,0},2}};assert(!ValidateEncounterDestination(&ai,plan,false));hazards.clear();
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
 // Newly spawned MC fire participates before the cached general hazards refresh.
 ai.bot.map=plan.map=409;plan.destination={10,0,0};ground={{{409,5,0,0},2}};
 path={{409,0,0,0},{409,10,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 path={{409,0,0,0},{409,0,5,0},{409,10,5,0},{409,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 ground.clear();path={{409,0,0,0},{409,10,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 ai.bot.map=plan.map=469;path={{469,0,0,0},{469,10,0,0}};bwlRouteSafe=false;
 assert(!ValidateEncounterDestination(&ai,plan));
 plan.destination={0.5f,0,0};assert(!ValidateEncounterDestination(&ai,plan)); // Short movement still checks fresh packs.
 bwlRouteSafe=true;plan.destination={10,0,0};assert(ValidateEncounterDestination(&ai,plan));
 ai.bot.map=plan.map=409;path={{409,0,0,0},{409,10,0,0}};
 plan.spell=21155;WorldPosition::liquid=true;assert(!ValidateEncounterDestination(&ai,plan,false));
 WorldPosition::liquid=false;assert(ValidateEncounterDestination(&ai,plan,false));plan.spell=0;
 // Uncached Sartura/guard auras must constrain the whole route as well.
 ai.bot.map=plan.map=531;plan.destination={30,0,0};
 whirlwinds={{{-1,0,0},12},{{15,0,0},12}};
 path={{531,0,0,0},{531,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 path={{531,0,0,0},{531,0,15,0},{531,30,15,0},{531,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 // The endpoint needs its two-yard margin, even when the route is empty.
 plan.destination={26.5f,0,0};assert(!ValidateEncounterDestination(&ai,plan));
 whirlwinds.pop_back();plan.destination={30,0,0};
 path={{531,0,0,0},{531,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{531,0,0,0},{531,-2,0,0},{531,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 whirlwinds.clear();assert(ValidateEncounterDestination(&ai,plan));
 // Chased players cannot take a path through the pursuer to a clear endpoint.
 ai.bot.map=plan.map=309;Unit pursuer;pursuer.map=309;pursuer.x=-3;pursuer.pursuit=true;
 ai.pursuer=&pursuer;plan.boss=1;plan.spell=24646;
 path={{309,0,0,0},{309,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{309,0,0,0},{309,-4,0,0},{309,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 pursuer.pursuit=false;assert(ValidateEncounterDestination(&ai,plan));pursuer.pursuit=true;
 pursuer.x=15;assert(!ValidateEncounterDestination(&ai,plan));
 path={{309,0,0,0},{309,0,15,0},{309,30,15,0},{309,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
#ifdef MANGOSBOT_ZERO
 // A safe Heigan platform endpoint across his aura must not admit a route
 // through the boss. Outward escape is legal; tanks retain melee admission.
 ai.pursuer=&pursuer;pursuer.pursuit=false;pursuer.map=ai.bot.map=plan.map=533;
 pursuer.entry=15936;pursuer.x=0;ai.bot.x=-10;ai.ranged=true;plan.spell=30116;plan.destination={30,0,0};
 path={{533,-10,0,0},{533,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 plan.destination={-30,0,0};path={{533,-10,0,0},{533,-30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{533,-10,0,0},{533,-9,0,0},{533,-30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.x=-30;plan.destination={30,0,0};path={{533,-30,0,0},{533,-30,30,0},{533,30,30,0},{533,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{533,-30,0,0},{533,30,0,0}};ai.tank=true;assert(ValidateEncounterDestination(&ai,plan));
 pursuer.cloud=true;assert(!ValidateEncounterDestination(&ai,plan));pursuer.cloud=false;
 ai.tank=false;pursuer.entry=15989;assert(ValidateEncounterDestination(&ai,plan));
 pursuer.entry=15936;pursuer.instance=2;assert(ValidateEncounterDestination(&ai,plan));pursuer.instance=1;
 ai.ranged=false;ai.bot.x=0;pursuer.entry=0;
 ai.pursuer=nullptr;ai.bot.map=plan.map=249;plan.spell=17086;plan.destination={30,0,0};
 onyxiaBreath={{{15,0,0},10}};path={{249,0,0,0},{249,30,0,0}};
 assert(!ValidateEncounterDestination(&ai,plan)); // clear endpoint, unsafe crossing
 path={{249,0,0,0},{249,0,15,0},{249,30,15,0},{249,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 onyxiaBreath={{{-1,0,0},10}};path={{249,0,0,0},{249,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{249,0,0,0},{249,-2,0,0},{249,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 // Native Onyxia trace: initial nav-floor projection must not cancel an outward breath escape.
 ai.bot.z=0.067f;onyxiaBreath={{{-1,0,0},10}};
 path={{249,0,0,0},{249,30,0,0}};assert(ValidateEncounterDestination(&ai,plan));
 path={{249,0,0,0},{249,-2,0,0},{249,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.z=3;path={{249,0,0,0},{249,30,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.z=0;
 // The whole native breath union, including the observed healer escape leg.
 ai.bot.x=-34.8508f;ai.bot.y=-223.422f;ai.bot.z=-84.2187f;
 onyxiaBreath={{{-37.7285f,-188.617f,-88.0749f},32},{{-37.0673f,-195.759f,-87.7458f},32},
  {{-36.6117f,-202.685f,-85.6538f},32},{{-32.0816f,-214.917f,-88.3274f},32},
  {{-34.0457f,-224.715f,-85.5295f},32},{{-35.8053f,-232.029f,-87.7492f},32},
  {{-37.7439f,-243.668f,-88.2177f},32}};
 plan.destination={-73,-224,-85};
 path={{249,ai.bot.x,ai.bot.y,ai.bot.z},{249,-50.8349f,-224.135f,-85.0933f},{249,-73,-224,-85}};
 assert(ValidateEncounterDestination(&ai,plan));
 hazards={{{249,-60,-224,-85},3}};assert(!ValidateEncounterDestination(&ai,plan));hazards.clear();
 path={{249,ai.bot.x,ai.bot.y,ai.bot.z},{249,-34.0457f,-224.715f,-85.5295f},{249,-73,-224,-85}};
 assert(!ValidateEncounterDestination(&ai,plan)); // inward leg still rejected
 plan.destination={-50,-224,-85};assert(!ValidateEncounterDestination(&ai,plan,false)); // unsafe endpoint
 ai.bot.x=ai.bot.y=ai.bot.z=0;
#endif
 ai.pursuer=nullptr;onyxiaBreath.clear();ground.clear();hazards={{{409,0,0,0},5}};
 ai.bot.map=plan.map=409;ai.bot.x=4;ai.bot.y=0;ai.bot.z=1;plan.spell=0;plan.destination={10,0,0};
 path={{409,4,0,0},{409,10,0,0}};
 assert(!ValidateEncounterDestination(&ai,plan)); // other MC encounters retain original policy
 ai.magmadar=true;assert(ValidateEncounterDestination(&ai,plan));
 path={{409,4,0,0},{409,2,0,0},{409,10,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.map=plan.map=531;hazards={{{531,0,0,0},5}};path={{531,4,0,0},{531,10,0,0}};
 assert(!ValidateEncounterDestination(&ai,plan)); // strategy alone cannot enable on another map
 plan.spell=7393;
#ifdef MANGOSBOT_ZERO
 assert(ValidateEncounterDestination(&ai,plan)); // native Twin ground projection, then outward escape
#else
 assert(!ValidateEncounterDestination(&ai,plan));
#endif
 path={{531,4,0,0},{531,2,0,0},{531,10,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 // Native Jeklik trial167606151: same-XY nav-floor projection while already
 // inside the ground hazard, followed by an outward walking escape.
 ai.bot.map=plan.map=309;ai.bot.x=4;ai.bot.z=.614f;plan.spell=0;plan.destination={20,0,0};
 hazards={{{309,0,0,0},11}};path={{309,4,0,0},{309,20,0,0}};
#ifdef MANGOSBOT_ZERO
 assert(ValidateEncounterDestination(&ai,plan));
#else
 assert(!ValidateEncounterDestination(&ai,plan));
#endif
 path={{309,4,0,0},{309,2,0,0},{309,20,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.z=3;path={{309,4,0,0},{309,20,0,0}};assert(!ValidateEncounterDestination(&ai,plan));
 ai.bot.z=.614f;hazards.push_back({{309,4,0,-2},2.5f});assert(!ValidateEncounterDestination(&ai,plan));
 // Native Gehennas path: floor projection then an uphill escape from beneath
 // the fire center. The endpoint still has to leave every hazard completely.
 ai.magmadar=false;ai.bot.map=plan.map=409;ai.bot.x=871.155f;ai.bot.y=-595.898f;ai.bot.z=-203.495f;
 plan.spell=0;plan.destination={888,-590,-201};hazards.clear();
 ground={{{409,871.155f,-595.898f,-203.495f},11}};
 path={{409,871.155f,-595.898f,-203.63f},{409,878.546f,-592.836f,-202.724f},{409,888,-590,-201}};
#ifdef MANGOSBOT_ZERO
 assert(ValidateEncounterDestination(&ai,plan));
#else
 assert(!ValidateEncounterDestination(&ai,plan));
#endif
 hazards=ground;ground.clear();assert(!ValidateEncounterDestination(&ai,plan)); // no live ground provenance
 ground=hazards;hazards.push_back({{409,883,-591,-202},3});assert(!ValidateEncounterDestination(&ai,plan));
 std::cout<<"PASS: actual encounter endpoint and bounded route validation, crossing/outward hazards and lifecycle gates\n";
}
'''.replace('__HELPERS__',helpers).replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-encounter-path-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],check=True)
