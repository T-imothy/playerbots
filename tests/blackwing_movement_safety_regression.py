"""Execute actual BWL route, native path admission, command provenance and dispatch bodies."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
assert 'virtual ObjectGuid Get() override' in (root/'playerbot/strategy/values/CurrentTargetValue.h').read_text()
assert 'dynamic_cast<Value<T>*>(GetUntypedValue(name))' in (root/'playerbot/strategy/AiObjectContext.h').read_text()
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
#include "__GEOMETRY__"
using uint32=uint32_t;using int32=int32_t;using ObjectGuid=unsigned;
enum {TYPEID_UNIT=1,TYPEID_PLAYER=2,IN_PROGRESS=1,DONE=3,SPELL_AURA_MOD_STEALTH=1,SPELL_AURA_MOD_STALKED=2,SPELL_AURA_DETECT_STEALTH=3,UNIT_FIELD_FLAGS=0,UNIT_FLAG_PLAYER_CONTROLLED=1,UNIT_STAND_STATE_STAND=0,FORCED_MOVEMENT_RUN=0,PATHFIND_NORMAL=1,EFFECT_MOTION_TYPE=9};
static time_t clockNow=100;
time_t fakeTime(void*){return clockNow;}
#define time fakeTime
struct Vector3{float x=0,y=0,z=0;};
using Position=Vector3;
struct Spline {std::vector<Vector3> points;int last()const{return int(points.size())-1;}Vector3 getPoint(int i)const{return points.at(i);}};
struct MoveSpline {bool done=true;int index=0;float speed=2.5f;Spline spline;float Speed(){return speed;}bool Finalized(){return done;}auto FinalDestination(){return spline.points.back();}const Spline& _Spline(){return spline;}int _currentSplineIdx(){return index;}};
struct MotionMaster {int clears=0,moves=0,type=0;int GetCurrentMovementGeneratorType(){return type;}void Clear(bool=false,bool=false){++clears;}void MovePath(std::vector<Vector3>&,int,bool,bool=false){++moves;}};
struct InstanceData {int state=0;int GetData(int id){assert(id==2);return state;}};
struct Map {InstanceData instance;bool visible=true;bool IsInLineOfSight(float,float,float,float,float,float,bool){return visible;}InstanceData* GetInstanceData(){return &instance;}};
struct WorldObject {virtual ~WorldObject()=default;unsigned map=469,instance=1,entry=0,id=0;float x=0,y=0,z=445;bool world=true;
 unsigned GetMapId()const{return map;}unsigned GetInstanceId()const{return instance;}unsigned GetEntry()const{return entry;}unsigned GetObjectGuid()const{return id;}
 float GetPositionX()const{return x;}float GetPositionY()const{return y;}float GetPositionZ()const{return z;}
 bool IsInWorld()const{return world;}bool IsInMap(const WorldObject* other)const{return other&&map==other->map&&instance==other->instance;}};
struct ThreatReference{unsigned guid=0;unsigned getUnitGuid()const{return guid;}};
struct ThreatManager{std::vector<ThreatReference*> refs;auto& getThreatList(){return refs;}};
struct Unit:WorldObject {bool alive=true,combat=false,charmed=false,hostile=true,canAttack=true,visible=true,corner=false,detect=false;float aggro=10,reach=0;Unit* master=nullptr;Unit* victim=nullptr;std::list<Unit*> attackers;ThreatManager threats;
 float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}void GetFirstCollisionPosition(Position&p,float radius,float angle){p={x+radius*std::cos(angle),y+radius*std::sin(angle),z};}
 MoveSpline* movespline=nullptr;Map objectMap;Map* GetMap(){return &objectMap;}float GetCollisionHeight(){return 2;}
 virtual bool IsPlayer()const{return false;}int GetTypeId()const{return IsPlayer()?TYPEID_PLAYER:TYPEID_UNIT;}
 bool IsAlive()const{return alive;}bool IsInCombat()const{return combat;}bool HasCharmer()const{return charmed;}
 bool CanInitiateAttack()const{return canAttack;}bool CanAttackOnSight(Unit*)const{return hostile;}float GetAttackDistance(Unit*)const{return aggro;}float GetCombatReach()const{return reach;}
 Unit* GetMaster(){return master;}Unit* GetVictim(){return victim;}auto& getAttackers(){return attackers;}auto& getThreatManager(){return threats;}
 bool HasAuraType(int aura)const{return aura==SPELL_AURA_DETECT_STEALTH&&detect;}
 bool IsWithinLOS(float px,float,float,bool)const{return visible&&(!corner||px>5);}};
struct Group{};
struct Visibility {float distance=1;float GetStealthVisibilityDistance(Unit*,bool){return distance;}};
struct Player:Unit {Group* group=nullptr;bool real=false,teleport=false,transport=false,stealth=false,stalked=false,casting=false,standing=true;Map worldMap;Visibility visibility;MoveSpline* movespline=nullptr;MotionMaster motion;
 float GetSpeed(int){return 7;}
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
constexpr int MOVE_RUN=1;
struct Context {ObjectGuid target=0;bool targetAvailable=true;std::list<HazardPosition> hazards;template<class T>struct Value{T* value;T Get(){return *value;}};Value<std::list<HazardPosition>> value{&hazards};Value<ObjectGuid>targetValue{&target};template<class T>Value<T>* GetValue(const char*){if constexpr(std::is_same_v<T,ObjectGuid>)return targetAvailable?&targetValue:nullptr;else if constexpr(std::is_same_v<T,std::list<HazardPosition>>)return &value;else return nullptr;}};
struct PlayerbotAI;
namespace ai {
struct EncounterPosition{unsigned map=0,instance=0,spell=0;ObjectGuid boss=0,source=0;};
bool BlackwingPatrolThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
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
bool BlackwingMovementSafetyActive(PlayerbotAI*);
bool RaidUnpulledPackMovementActive(PlayerbotAI*);
bool RaidUnpulledPackRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&);
bool MadnessFormationRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&,Unit*);
bool MajordomoFormationRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&,Unit*);
bool MoltenCoreTrashChargeSafe(PlayerbotAI*);
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
 assert(BlackwingMovementRouteSafe(&ai,route(5)));enemy.reach=4;bot.reach=1;
#ifdef MANGOSBOT_ZERO
 assert(BlackwingMovementRouteSafe(&ai,route(5))); // native centre-distance aggro excludes melee reach
#else
 assert(!BlackwingMovementRouteSafe(&ai,route(5)));
#endif
 enemy.reach=bot.reach=0;
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
 // The adjacent dragon must remain protected outside the suppression room.
 nearbyDevices.clear();bot.combat=true;
#ifdef MANGOSBOT_ZERO
 assert(BlackwingMovementSafetyActive(&ai));assert(!BlackwingMovementRouteSafe(&ai,route(40)));
 enemy.combat=true;enemy.victim=&member;assert(BlackwingMovementRouteSafe(&ai,route(40)));
 enemy.combat=false;enemy.victim=nullptr;
 bot.map=30;assert(!BlackwingMovementSafetyActive(&ai));bot.map=0;assert(!BlackwingMovementSafetyActive(&ai));bot.map=469;
 bot.teleport=true;assert(!BlackwingMovementSafetyActive(&ai));bot.teleport=false;
 ai.real=true;assert(!BlackwingMovementSafetyActive(&ai));ai.real=false;
#else
 assert(!BlackwingMovementSafetyActive(&ai));assert(BlackwingMovementRouteSafe(&ai,route(40)));
#endif
 bot.combat=false;assert(!BlackwingMovementSafetyActive(&ai));nearbyDevices={&device};
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
 // The same native aggro geometry protects only engaged Classic Madness
 // formation. It does not activate elsewhere or alter the BWL dispatch.
 Unit madness;madness.entry=15083;madness.combat=true;madness.victim=&member;
 bot.map=member.map=enemy.map=madness.map=309;enemy.x=20;enemy.aggro=10;enemy.combat=false;enemy.victim=nullptr;enemy.threats.refs.clear();enemy.attackers.clear();
 bot.x=0;bot.y=0;bot.stealth=false;enemy.visible=true;enemy.corner=false;ai.pull.started=false;ai.wait.orderedTarget=0;
 std::vector<WorldPosition> unsafeMadness{{309,40,0,445}},safeMadness{{309,0,30,445}};
#ifdef MANGOSBOT_ZERO
 assert(!MadnessFormationRouteSafe(&ai,unsafeMadness,&madness));
 assert(MadnessFormationRouteSafe(&ai,safeMadness,&madness));
 madness.combat=false;assert(MadnessFormationRouteSafe(&ai,unsafeMadness,&madness));madness.combat=true;
 madness.instance=2;assert(MadnessFormationRouteSafe(&ai,unsafeMadness,&madness));madness.instance=1;
 madness.entry=14517;assert(MadnessFormationRouteSafe(&ai,unsafeMadness,&madness));madness.entry=15083;
 member.group=&foreign;assert(MadnessFormationRouteSafe(&ai,unsafeMadness,&madness));member.group=&group;
#else
 assert(MadnessFormationRouteSafe(&ai,unsafeMadness,&madness));
#endif
 // Recorded ZG pull: a moving target changes the approach after staging.
 // Only a bounded, human-authorized Classic ZG pull activates this admission.
 {
 Player puller,requester;puller.map=requester.map=309;
 puller.id=901;requester.id=902;requester.real=true;
 puller.group=requester.group=&group;
 Unit intended,unpulled;intended.map=unpulled.map=309;
 intended.id=903;intended.x=40;unpulled.id=904;unpulled.x=20;
 PlayerbotAI guarded{&puller};guarded.owner=&requester;
 guarded.units={{902,&requester},{903,&intended}};
 guarded.pull={true,true,100,&intended,902};
 nearbyDevices.clear();nearbyUnits={&intended};
 assert(!BlackwingMovementSafetyActive(&guarded));
 assert(!BlackwingSuppressionMovementActive(&guarded));
 std::vector<WorldPosition> approach{{309,40,0,445}};
#ifdef MANGOSBOT_ZERO
 assert(RaidUnpulledPackMovementActive(&guarded));
 assert(BlackwingMovementRouteSafe(&guarded,approach));
 nearbyUnits.push_back(&unpulled);
 assert(!BlackwingMovementRouteSafe(&guarded,approach));
 MovementAction approaching{&guarded,&puller};puller.casting=true;
 assert(!approaching.MoveBlackwingPath(approach.back()));
 assert(puller.casting&&guarded.interrupts==0&&puller.motion.moves==0);
 MoveSpline oldRoute;oldRoute.done=false;
 oldRoute.spline.points={{0,0,445},{40,0,445}};puller.movespline=&oldRoute;
 assert(StopUnsafeBlackwingMovement(&guarded)&&oldRoute.done);
 unpulled.y=40;assert(BlackwingMovementRouteSafe(&guarded,approach));
 // The same destination becomes unsafe again after a patrol changes position.
 unpulled.y=0;assert(!BlackwingMovementRouteSafe(&guarded,approach));
 guarded.allowed=false;assert(!RaidUnpulledPackMovementActive(&guarded));guarded.allowed=true;
 requester.instance=2;assert(!RaidUnpulledPackMovementActive(&guarded));requester.instance=1;
 requester.group=&foreign;assert(!RaidUnpulledPackMovementActive(&guarded));requester.group=&group;
 requester.teleport=true;assert(!RaidUnpulledPackMovementActive(&guarded));requester.teleport=false;
 intended.alive=false;assert(!RaidUnpulledPackMovementActive(&guarded));intended.alive=true;
 clockNow=116;assert(!RaidUnpulledPackMovementActive(&guarded));clockNow=100;
 guarded.pull.allowed=false;assert(!RaidUnpulledPackMovementActive(&guarded));guarded.pull.allowed=true;
 guarded.real=true;assert(!RaidUnpulledPackMovementActive(&guarded));guarded.real=false;
 puller.teleport=true;assert(!RaidUnpulledPackMovementActive(&guarded));puller.teleport=false;
 puller.charmed=true;assert(!RaidUnpulledPackMovementActive(&guarded));puller.charmed=false;
 puller.transport=true;assert(!RaidUnpulledPackMovementActive(&guarded));puller.transport=false;
 // Pull completion must not turn off combat admission. The actual route
 // still admits engaged targets but rejects a fresh neighbor after expiry.
 guarded.pull.started=false;puller.combat=true;intended.combat=true;intended.victim=&requester;
 assert(RaidUnpulledPackMovementActive(&guarded));
 assert(!BlackwingMovementRouteSafe(&guarded,approach));
 // Stealth cannot justify a combat endpoint that becomes unsafe on Cheap Shot.
 puller.stealth=true;puller.visibility.distance=1;
 assert(!BlackwingMovementRouteSafe(&guarded,approach));puller.stealth=false;
 unpulled.y=40;assert(BlackwingMovementRouteSafe(&guarded,approach));unpulled.y=0;
 guarded.real=true;assert(!RaidUnpulledPackMovementActive(&guarded));guarded.real=false;
 puller.teleport=true;assert(!RaidUnpulledPackMovementActive(&guarded));puller.teleport=false;
 puller.group=nullptr;assert(!RaidUnpulledPackMovementActive(&guarded));puller.group=&group;
 puller.combat=false;assert(!RaidUnpulledPackMovementActive(&guarded));
#else
 assert(!RaidUnpulledPackMovementActive(&guarded));
 nearbyUnits.push_back(&unpulled);assert(BlackwingMovementRouteSafe(&guarded,approach));
#endif
 for(unsigned map:{0u,1u,30u,489u,529u,229u,409u,533u}) {
   puller.map=requester.map=intended.map=map;
   assert(!RaidUnpulledPackMovementActive(&guarded));
 }
 nearbyUnits={&enemy};nearbyDevices={&device};
 }
 // Recorded Ebonroc caster leg: the current patrol location was clear, but
 // Flamegor's native spline entered the route before the caster arrived.
 bot.map=enemy.map=469;bot.x=-7384.81f;bot.y=-1010.20f;bot.z=477.115f;
 enemy.x=-7411.59f;enemy.y=-1029.91f;enemy.z=477.165f;enemy.aggro=21;
 WorldPosition end(469,-7387.45f,-1037.50f,477.32f);
 assert(!VisibleAggroCrossing(&bot,&enemy,23,WorldPosition(&bot),end));
 MoveSpline patrol;patrol.done=false;patrol.spline.points={{enemy.x,enemy.y,enemy.z},{-7400.97f,-1033.27f,477.187f}};enemy.movespline=&patrol;
#ifdef MANGOSBOT_ZERO
 assert(!RaidUnpulledPackRouteSafe(&ai,{end}));
 enemy.objectMap.visible=false;assert(RaidUnpulledPackRouteSafe(&ai,{end}));enemy.objectMap.visible=true;
 patrol.done=true;assert(RaidUnpulledPackRouteSafe(&ai,{end}));patrol.done=false;
 patrol.spline.points.back()={-7430.f,-1033.27f,477.187f};assert(RaidUnpulledPackRouteSafe(&ai,{end}));
 patrol.speed=NAN;assert(!RaidUnpulledPackRouteSafe(&ai,{end}));patrol.speed=2.5f;
 std::vector<WorldPosition> prediction;assert(RaidPatrolLookahead(&enemy,100,prediction));assert(prediction.size()<=32);
 for(auto point:prediction)assert(WorldPosition(&enemy).distance(point)<=12.51f); // native 2.5yd/s, bounded five seconds
#else
 assert(RaidUnpulledPackRouteSafe(&ai,{end}));
#endif
 // Stationary Ebonroc caster: Firemaw's patrol reaches the caster while
 // ordinary route admission correctly rejects moves further into the patrol.
 {
 Player stationary;stationary.group=&group;stationary.combat=true;
 stationary.x=-7419.78f;stationary.y=-1009.36f;stationary.z=477.707f;
 Unit engaged,idle;engaged.id=501;engaged.entry=14601;engaged.combat=true;engaged.victim=&stationary;
 engaged.x=-7420;engaged.y=-980;engaged.z=477;
 idle.id=502;idle.entry=11981;idle.x=-7408;idle.y=-1035;idle.z=477;idle.aggro=21;
 MoveSpline approaching;approaching.done=false;approaching.speed=2.5f;
 approaching.spline.points={{idle.x,idle.y,idle.z},{-7408,-1015,477}};idle.movespline=&approaching;
 PlayerbotAI watcher{&stationary};nearbyUnits={&engaged,&idle};
 EncounterPosition plan;std::vector<encounter::Circle> threats;
 auto predicted=[&](){plan={};threats.clear();return BlackwingPatrolThreats(&watcher,plan,threats);};
#ifdef MANGOSBOT_ZERO
 assert(predicted()&&plan.boss==501&&plan.source==502&&plan.spell==0&&threats.size()==2);
 idle.objectMap.visible=false;assert(!predicted());idle.objectMap.visible=true;
 approaching.done=true;assert(!predicted());approaching.done=false;
 approaching.spline.points.back()={-7408,-1055,477};assert(!predicted());approaching.spline.points.back()={-7408,-1015,477};
 idle.combat=true;assert(!predicted());idle.combat=false;
 idle.instance=2;assert(!predicted());idle.instance=1;
 stationary.combat=false;assert(!predicted());stationary.combat=true;
 stationary.map=0;assert(!predicted());stationary.map=469;
 stationary.teleport=true;assert(!predicted());stationary.teleport=false;
 engaged.victim=nullptr;assert(!predicted());engaged.victim=&stationary;
 idle.entry=12465;assert(!predicted());idle.entry=11981;
 assert(predicted());
 // Native retry 57787900: the threatened hunter stood 0.319yd above
 // navigation floor. That first vertical projection rejected every escape.
 stationary.x=-7413.39f;stationary.y=-1007.95f;stationary.z=477.484f;
 idle.x=-7409.82f;idle.y=-1030.41f;idle.z=477.165f;
 approaching.spline.points={{idle.x,idle.y,idle.z},{-7406.33f,-1028.42f,477.21f}};
 const WorldPosition projected(469,stationary.x,stationary.y,477.165f);
 const WorldPosition escape(469,stationary.x,-990,477.165f);
 const WorldPosition inward(469,stationary.x,-1020,477.165f);
 assert(VisibleAggroCrossing(&stationary,&idle,23,WorldPosition(&stationary),projected));
 assert(!VisibleAggroCrossing(&stationary,&idle,23,WorldPosition(&stationary),projected,nullptr,true));
 assert(!RaidUnpulledPackRouteSafe(&watcher,{projected})); // No standalone projection exemption.
 assert(RaidUnpulledPackRouteSafe(&watcher,{projected,escape}));
 assert(!RaidUnpulledPackRouteSafe(&watcher,{projected,inward}));
 stationary.map=idle.map=engaged.map=409;
 assert(VisibleAggroCrossing(&stationary,&idle,23,WorldPosition(&stationary),WorldPosition(409,stationary.x,stationary.y,477.165f),nullptr,true));
#else
 assert(!predicted());
#endif
 }
 // Recorded MC off-tank intercept: giant 29yd ahead, idle Firelord 42yd
 // ahead/right. Use the actual native charge endpoint and route admission.
 Player chargeBot;Group chargeGroup;chargeBot.group=&chargeGroup;chargeBot.map=409;chargeBot.z=0;
 Unit giant,firelord;giant.map=firelord.map=409;giant.z=firelord.z=0;
 giant.entry=11658;giant.x=28.8f;giant.reach=3;giant.combat=true;giant.victim=&chargeBot;
 firelord.entry=11668;firelord.x=42;firelord.y=-5;firelord.aggro=20;
 PlayerbotAI chargeAI{&chargeBot};chargeAI.context.target=77;chargeAI.units[77]=&giant;nearbyUnits={&giant,&firelord};nativePath.clear();navOkay=true;navType=PATHFIND_NORMAL;
#ifdef MANGOSBOT_ZERO
 assert(chargeAI.context.GetValue<Unit*>("current target")==nullptr); // native typed-context contract
 chargeAI.context.targetAvailable=false;assert(MoltenCoreTrashChargeSafe(&chargeAI));chargeAI.context.targetAvailable=true;
 chargeAI.context.target=0;assert(MoltenCoreTrashChargeSafe(&chargeAI));
 chargeAI.context.target=999;assert(MoltenCoreTrashChargeSafe(&chargeAI));chargeAI.context.target=77;
 assert(!MoltenCoreTrashChargeSafe(&chargeAI));
 firelord.combat=true;firelord.victim=&chargeBot;assert(MoltenCoreTrashChargeSafe(&chargeAI)); // existing double pull still recoverable
 firelord.combat=false;firelord.victim=nullptr;giant.x=15;assert(MoltenCoreTrashChargeSafe(&chargeAI)); // let native pull approach first
 navOkay=false;assert(!MoltenCoreTrashChargeSafe(&chargeAI));navOkay=true;
 nativePath={{0,0,0},{1,0,0}};assert(!MoltenCoreTrashChargeSafe(&chargeAI));nativePath.clear();
 giant.x=28.8f;firelord.instance=2;assert(MoltenCoreTrashChargeSafe(&chargeAI));firelord.instance=1;
#else
 assert(MoltenCoreTrashChargeSafe(&chargeAI));
#endif
 for(unsigned boss:{12057u,12056u,11982u}){giant.entry=boss;assert(MoltenCoreTrashChargeSafe(&chargeAI));}
 giant.entry=11658;for(unsigned map:{0u,30u,469u,533u}){chargeBot.map=giant.map=firelord.map=map;assert(MoltenCoreTrashChargeSafe(&chargeAI));}
 std::cout<<"PASS: actual BWL native route admission, patrol lookahead, Madness scope, MC trash native charge route, engagement/provenance, walls, floor and dispatch\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__SAFETY__',safety).replace('__ORDERS__',orders).replace('__HELPER__',helper).replace('__MOVEMENT__',movement)
with tempfile.TemporaryDirectory(prefix='mantech-bwl-movement-') as tmp:
 tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
