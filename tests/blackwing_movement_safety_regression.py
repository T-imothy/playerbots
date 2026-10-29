"""Execute actual BWL route, native path admission, command provenance and dispatch bodies."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
helper=(root/'playerbot/strategy/actions/BlackwingMovementSafety.cpp').read_text()
helper='\n'.join(line for line in helper.splitlines() if not line.startswith('#include'))
safety=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
safety='\n'.join(line for line in safety.splitlines() if not line.startswith('#include') and not line.startswith('#pragma'))
movement=block((root/'playerbot/strategy/actions/MovementActions.cpp').read_text(),'bool MovementAction::MoveBlackwingPath(')
combat=(root/'playerbot/strategy/generic/CombatStrategy.cpp').read_text()
orders='\n'.join(block(combat,m) for m in ('void WaitForAttackStrategy::AllowExplicitAttack(', 'bool WaitForAttackStrategy::HasExplicitAttackOrder(', 'Unit* WaitForAttackStrategy::GetExplicitAttackTarget('))
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <limits>
#include <list>
#include <map>
#include <vector>
using uint32=uint32_t;using int32=int32_t;using ObjectGuid=unsigned;
enum {TYPEID_UNIT=1,TYPEID_PLAYER=2,IN_PROGRESS=1,DONE=3,SPELL_AURA_MOD_STEALTH=1,SPELL_AURA_MOD_STALKED=2,SPELL_AURA_DETECT_STEALTH=3,UNIT_FIELD_FLAGS=0,UNIT_FLAG_PLAYER_CONTROLLED=1,UNIT_STAND_STATE_STAND=0,FORCED_MOVEMENT_RUN=0,PATHFIND_NORMAL=1,EFFECT_MOTION_TYPE=9};
static time_t clockNow=100;
time_t fakeTime(void*){return clockNow;}
#define time fakeTime
struct Vector3{float x=0,y=0,z=0;};
struct Spline {std::vector<Vector3> points;int last()const{return int(points.size())-1;}Vector3 getPoint(int i)const{return points.at(i);}};
struct MoveSpline {bool done=true;int index=0;Spline spline;bool Finalized(){return done;}auto FinalDestination(){return spline.points.back();}const Spline& _Spline(){return spline;}int _currentSplineIdx(){return index;}};
struct MotionMaster {int clears=0,moves=0,type=0;int GetCurrentMovementGeneratorType(){return type;}void Clear(bool=false,bool=false){++clears;}void MovePath(std::vector<Vector3>&,int,bool,bool=false){++moves;}};
struct InstanceData {int state=0;int GetData(int id){assert(id==2);return state;}};
struct Map {InstanceData instance;InstanceData* GetInstanceData(){return &instance;}};
struct WorldObject {virtual ~WorldObject()=default;unsigned map=469,instance=1,entry=0,id=0;float x=0,y=0,z=445;bool world=true;
 unsigned GetMapId()const{return map;}unsigned GetEntry()const{return entry;}unsigned GetObjectGuid()const{return id;}
 float GetPositionX()const{return x;}float GetPositionY()const{return y;}float GetPositionZ()const{return z;}
 bool IsInWorld()const{return world;}bool IsInMap(const WorldObject* other)const{return other&&map==other->map&&instance==other->instance;}};
struct ThreatReference{unsigned guid=0;unsigned getUnitGuid()const{return guid;}};
struct ThreatManager{std::vector<ThreatReference*> refs;auto& getThreatList(){return refs;}};
struct Unit:WorldObject {bool alive=true,combat=false,charmed=false,hostile=true,canAttack=true,visible=true,corner=false,detect=false;float aggro=10,reach=0;Unit* master=nullptr;Unit* victim=nullptr;std::list<Unit*> attackers;ThreatManager threats;
 virtual bool IsPlayer()const{return false;}int GetTypeId()const{return IsPlayer()?TYPEID_PLAYER:TYPEID_UNIT;}
 bool IsAlive()const{return alive;}bool IsInCombat()const{return combat;}bool HasCharmer()const{return charmed;}
 bool CanInitiateAttack()const{return canAttack;}bool CanAttackOnSight(Unit*)const{return hostile;}float GetAttackDistance(Unit*)const{return aggro;}float GetCombatReach()const{return reach;}
 Unit* GetMaster(){return master;}Unit* GetVictim(){return victim;}auto& getAttackers(){return attackers;}auto& getThreatManager(){return threats;}
 bool HasAuraType(int aura)const{return aura==SPELL_AURA_DETECT_STEALTH&&detect;}
 bool IsWithinLOS(float px,float,float,bool)const{return visible&&(!corner||px>5);}};
struct Group{};
struct Visibility {float distance=1;float GetStealthVisibilityDistance(Unit*,bool){return distance;}};
struct Player:Unit {Group* group=nullptr;bool real=false,teleport=false,transport=false,stealth=false,stalked=false,casting=false,standing=true;Map worldMap;Visibility visibility;MoveSpline* movespline=nullptr;MotionMaster motion;
 bool IsPlayer()const override{return true;}Group* GetGroup(){return group;}bool isRealPlayer(){return real;}bool IsBeingTeleported(){return teleport;}void* GetTransport(){return transport?this:nullptr;}Map* GetMap(){return &worldMap;}
 bool HasAuraType(int aura)const{return aura==SPELL_AURA_MOD_STEALTH&&stealth;}bool HasAuraTypeWithCaster(int,unsigned){return stalked;}
 bool HasFlag(int,int){return true;}auto& GetVisibilityData(){return visibility;}float GetCollisionHeight(){return 2;}
 void HandleEmoteState(int){}bool IsStandState(){return standing;}void SetStandState(int){standing=true;}bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}MotionMaster* GetMotionMaster(){return &motion;}};
struct GameObject:WorldObject{};
namespace ai {
struct WorldPosition {unsigned map=469;float x=0,y=0,z=445;WorldPosition()=default;WorldPosition(const WorldObject* o):map(o->map),x(o->x),y(o->y),z(o->z){}WorldPosition(unsigned m,float px,float py,float pz):map(m),x(px),y(py),z(pz){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}
 bool isPathTo(const std::vector<WorldPosition>& path,float,float)const{return !path.empty()&&map==path.back().map&&distance(path.back())<1;}
 std::vector<Vector3> toPointsArray(const std::vector<WorldPosition>& path){std::vector<Vector3> out;for(auto p:path)out.push_back({p.x,p.y,p.z});return out;}};
using HazardPosition=std::pair<WorldPosition,float>;
}
using namespace ai;
struct Context {std::list<HazardPosition> hazards;template<class T>struct Value{T* value;T Get(){return *value;}};Value<std::list<HazardPosition>> value{&hazards};template<class T>Value<T>* GetValue(const char*){return &value;}};
struct PlayerbotAI;
namespace ai {
struct PullStrategy {bool allowed=false,started=false;time_t at=100;Unit* target=nullptr;unsigned requester=0;static PullStrategy* Get(PlayerbotAI*);bool IsEncounterPreparationAllowed(){return allowed;}bool HasPullStarted(){return started;}time_t GetPullStartTime(){return at;}int GetMaxPullTime(){return 15;}unsigned GetRequester(){return requester;}Unit* GetTarget(){return target;}};
struct WaitForAttackStrategy {unsigned orderedOwner=0,orderedTarget=0;time_t orderedAt=0,orderedCombatStart=0;static WaitForAttackStrategy* Get(PlayerbotAI*);void AllowExplicitAttack(PlayerbotAI*,Player*,Unit*);bool HasExplicitAttackOrder(PlayerbotAI*,time_t);Unit* GetExplicitAttackTarget(PlayerbotAI*);};
}
struct PlayerbotAI {Player* bot;Player* owner=nullptr;bool allowed=true,real=false,tank=false;time_t combatStart=100;int stops=0,interrupts=0;std::map<unsigned,Unit*> units;Context context;PullStrategy pull;WaitForAttackStrategy wait;
 bool canMove=true;bool CanMove(){return canMove;}Player* GetBot(){return bot;}Player* GetMaster(){return owner;}bool IsRealPlayer(){return real;}bool IsTank(Player*){return tank;}time_t GetCombatStartTime(){return combatStart;}Unit* GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}Context* GetAiObjectContext(){return &context;}
 void StopMoving(){++stops;bot->motion.Clear();if(bot->movespline)bot->movespline->done=true;}void InterruptSpell(bool){++interrupts;bot->casting=false;}};
PullStrategy* PullStrategy::Get(PlayerbotAI* a){return &a->pull;}WaitForAttackStrategy* WaitForAttackStrategy::Get(PlayerbotAI*a){return &a->wait;}
bool CanManageBotCommands(PlayerbotAI*a,Player*p){return a->allowed&&p&&p->real;}
struct ServerFacade{bool IsFriendlyTo(Unit*,Unit*other){return !other->hostile;}}sServerFacade;
std::vector<Unit*> nearbyUnits;std::vector<GameObject*> nearbyDevices;float scannedRadius=0;
namespace MaNGOS {
struct GameObjectEntryInPosRangeCheck{WorldObject& bot;unsigned entry;float radius;GameObjectEntryInPosRangeCheck(WorldObject& b,unsigned e,float,float,float,float r):bot(b),entry(e),radius(r){}bool operator()(GameObject*p){return p->entry==entry&&WorldPosition(&bot).distance(WorldPosition(p))<=radius;}};
template<class C>struct GameObjectListSearcher{std::list<GameObject*>& out;C& check;GameObjectListSearcher(std::list<GameObject*>&o,C&c):out(o),check(c){}void visit(Player*,float){for(auto p:nearbyDevices)if(check(p))out.push_back(p);}};
template<class C>struct UnitListSearcher{std::list<Unit*>& out;C& check;UnitListSearcher(std::list<Unit*>&o,C&c):out(o),check(c){}void visit(Player*b,float r){scannedRadius=r;for(auto p:nearbyUnits)if(WorldPosition(b).distance(WorldPosition(p))<=r&&check(p))out.push_back(p);}};
}
namespace Cell{template<class S>void VisitAllObjects(Player*b,S&s,float r){s.visit(b,r);}}
std::vector<Vector3> nativePath;bool navOkay=true;int navType=PATHFIND_NORMAL;
struct PathFinder{Player* bot;std::vector<Vector3> path;PathFinder(Player*b):bot(b){}bool calculate(float x,float y,float z,bool forced){assert(!forced);path=nativePath.empty()?std::vector<Vector3>{{bot->x,bot->y,bot->z},{x,y,z}}:nativePath;return navOkay;}int getPathType(){return navType;}auto& getPath(){return path;}};
namespace ai {
bool BlackwingSuppressionMovementActive(PlayerbotAI*);bool BlackwingMovementRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&);bool BuildBlackwingMovementPath(PlayerbotAI*,const WorldPosition&,std::vector<WorldPosition>&);bool StopUnsafeBlackwingMovement(PlayerbotAI*);bool BlackwingActiveMovementUnsafe(PlayerbotAI*);
void AppendBlackwingGroundHazards(PlayerbotAI*,std::list<HazardPosition>&){}
struct MovementAction{PlayerbotAI* ai;Player* bot;unsigned duration=0;void UpdateMovementState(){}void SetDuration(unsigned n){duration=n;}void ClearIdleState(){}bool MoveBlackwingPath(const WorldPosition&);};
}
__SAFETY__
__ORDERS__
__HELPER__
__MOVEMENT__
int main(){
 Group group,foreign;Player bot,owner,member;bot.group=owner.group=member.group=&group;owner.real=true;owner.id=1;bot.id=2;member.id=3;
 PlayerbotAI ai{&bot};ai.owner=&owner;ai.units={{1,&owner},{2,&bot},{3,&member}};GameObject device;device.entry=179784;nearbyDevices={&device};
 Unit enemy;enemy.id=10;enemy.x=20;nearbyUnits={&enemy};ai.units[10]=&enemy;
 auto route=[&](float x,float y=0,float z=445){return std::vector<WorldPosition>{{469,x,y,z}};};
 assert(BlackwingSuppressionMovementActive(&ai));assert(!BlackwingMovementRouteSafe(&ai,route(40)));
 assert(BlackwingMovementRouteSafe(&ai,route(0,30)));assert(scannedRadius<=130);
 assert(BlackwingMovementRouteSafe(&ai,route(5)));enemy.reach=4;bot.reach=1;assert(!BlackwingMovementRouteSafe(&ai,route(5)));enemy.reach=bot.reach=0;
 enemy.combat=true;enemy.victim=&member;assert(BlackwingMovementRouteSafe(&ai,route(40)));
 member.group=&foreign;assert(!BlackwingMovementRouteSafe(&ai,route(40)));member.group=&group;
 Unit pet;pet.master=&member;enemy.victim=&pet;assert(BlackwingMovementRouteSafe(&ai,route(40)));
 enemy.victim=nullptr;ThreatReference ref{3};enemy.threats.refs={&ref};assert(BlackwingMovementRouteSafe(&ai,route(40)));
 member.instance=2;assert(!BlackwingMovementRouteSafe(&ai,route(40)));member.instance=1;enemy.threats.refs.clear();enemy.combat=false;
 enemy.visible=false;assert(BlackwingMovementRouteSafe(&ai,route(40)));enemy.visible=true;enemy.corner=true;assert(!BlackwingMovementRouteSafe(&ai,route(40)));enemy.corner=false;
 enemy.z=470;assert(BlackwingMovementRouteSafe(&ai,route(40)));enemy.z=445;
 bot.x=15;assert(BlackwingMovementRouteSafe(&ai,route(0)));assert(!BlackwingMovementRouteSafe(&ai,route(40)));bot.x=0;
 // A native detour farther than its endpoint still scans packs near every waypoint.
 enemy.x=110;enemy.aggro=20;assert(!BlackwingMovementRouteSafe(&ai,{{469,95,0,445},{469,70,0,445}}));enemy.x=20;enemy.aggro=10;
 assert(!BlackwingMovementRouteSafe(&ai,route(121)));assert(!BlackwingMovementRouteSafe(&ai,route(std::numeric_limits<float>::quiet_NaN())));
 assert(!BlackwingMovementRouteSafe(&ai,{{1,0,0,445}}));
 // Only the bounded explicitly authorized pull/attack target is exempt.
 ai.pull={true,true,100,&enemy,1};assert(BlackwingMovementRouteSafe(&ai,route(40)));
 Unit extra;extra.x=35;nearbyUnits.push_back(&extra);assert(!BlackwingMovementRouteSafe(&ai,route(40)));nearbyUnits.pop_back();
 ai.allowed=false;assert(!BlackwingMovementRouteSafe(&ai,route(40)));ai.allowed=true;clockNow=116;assert(!BlackwingMovementRouteSafe(&ai,route(40)));clockNow=100;ai.pull.started=false;
 ai.wait.AllowExplicitAttack(&ai,&owner,&enemy);assert(ai.wait.GetExplicitAttackTarget(&ai)==&enemy);assert(BlackwingMovementRouteSafe(&ai,route(40)));
 ai.combatStart=200;assert(!BlackwingMovementRouteSafe(&ai,route(40)));ai.combatStart=100;owner.teleport=true;assert(!BlackwingMovementRouteSafe(&ai,route(40)));owner.teleport=false;ai.wait={};
 // Stealth uses the native detection radius; stalking/detection restores normal aggro.
 bot.stealth=true;assert(BlackwingMovementRouteSafe(&ai,route(10)));bot.visibility.distance=0;assert(!BlackwingMovementRouteSafe(&ai,route(19)));bot.visibility.distance=1;bot.stalked=true;assert(!BlackwingMovementRouteSafe(&ai,route(10)));bot.stalked=false;
#ifndef MANGOSBOT_ZERO
 enemy.detect=true;assert(!BlackwingMovementRouteSafe(&ai,route(10)));enemy.detect=false;
#endif
 bot.stealth=false;
 // Native map/lifecycle, entrance and separated floor scope.
 device.x=62;device.z=457;assert(BlackwingSuppressionMovementActive(&ai));device.z=461;assert(!BlackwingSuppressionMovementActive(&ai));device.x=0;device.z=445;
 bot.worldMap.instance.state=IN_PROGRESS;assert(!BlackwingMovementRouteSafe(&ai,route(40)));bot.worldMap.instance.state=DONE;assert(!BlackwingMovementRouteSafe(&ai,route(40)));bot.worldMap.instance.state=0;
 bot.map=409;assert(BlackwingMovementRouteSafe(&ai,route(40)));bot.map=469;
 // Dispatch cannot cancel a spell merely because an unsafe destination was requested.
 MovementAction action{&ai,&bot};bot.casting=true;ai.canMove=false;int stops=ai.stops;assert(!action.MoveBlackwingPath({469,40,0,445})&&ai.stops==stops);ai.canMove=true;bot.motion.type=EFFECT_MOTION_TYPE;assert(!action.MoveBlackwingPath({469,40,0,445})&&ai.stops==stops);bot.motion.type=0;assert(!action.MoveBlackwingPath({469,40,0,445}));assert(bot.casting&&ai.interrupts==0&&bot.motion.moves==0&&ai.stops>0);
 nearbyUnits.clear();
 navOkay=false;assert(!action.MoveBlackwingPath({469,10,0,445}));assert(bot.casting&&ai.interrupts==0);navOkay=true;
 navType=2;assert(!action.MoveBlackwingPath({469,10,0,445}));navType=1;
 nativePath={{0,0,445},{5,0,445}};assert(!action.MoveBlackwingPath({469,10,0,445}));nativePath.clear();
 owner.instance=2;assert(!action.MoveBlackwingPath({469,10,0,445}));owner.instance=1;
 ai.context.hazards={{{469,5,0,445},2}};assert(!action.MoveBlackwingPath({469,10,0,445}));assert(ai.context.hazards.size()==1);ai.context.hazards.clear();
 assert(action.MoveBlackwingPath({469,10,0,445}));assert(ai.interrupts==1&&bot.motion.moves==1&&action.duration==250);
 // Retain a still-safe native spline; stop it when an unpulled pack moves onto its remaining route.
 MoveSpline spline;spline.done=false;spline.spline.points={{0,0,445},{10,0,445}};bot.movespline=&spline;
 assert(action.MoveBlackwingPath({469,10,0,445}));assert(bot.motion.moves==1);
 enemy.x=8;enemy.aggro=3;nearbyUnits={&enemy};ai.canMove=false;assert(!StopUnsafeBlackwingMovement(&ai));ai.canMove=true;bot.motion.type=EFFECT_MOTION_TYPE;assert(!StopUnsafeBlackwingMovement(&ai));bot.motion.type=0;assert(StopUnsafeBlackwingMovement(&ai));assert(spline.done);
 std::cout<<"PASS: actual BWL native route admission, engagement/provenance, escape, walls, floor, dispatch and stale spline\n";
}
'''.replace('__SAFETY__',safety).replace('__ORDERS__',orders).replace('__HELPER__',helper).replace('__MOVEMENT__',movement)
with tempfile.TemporaryDirectory(prefix='mantech-bwl-movement-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
