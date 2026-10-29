"""Execute the production trap approach, including actual segment geometry."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
method=block(source,'bool MoveToSuppressionDeviceAction::Execute(').replace('state.device.Clear()','state.device = 0')
ownership=block(source,'bool ai::SuppressionDutyOwnsMovement(')
strategy=(root/'playerbot/strategy/generic/BlackwingLairDungeonStrategies.cpp').read_text()
multiplier=block(strategy,'class PreserveSuppressionDutyMovementMultiplier : public Multiplier')+';'
geometry=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
geometry=geometry[geometry.index('namespace ai'):]
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <list>
#include <string>
#include <map>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{IN_PROGRESS=1,DONE=3,PATHFIND_NORMAL=1,FORCED_MOVEMENT_RUN=1,UNIT_STAND_STATE_STAND=0,SPELL_AURA_MOD_STEALTH=16,SPELL_AURA_MOD_STALKED=151,SPELL_AURA_DETECT_STEALTH=228,UNIT_FIELD_FLAGS=0,UNIT_FLAG_PLAYER_CONTROLLED=1};
struct Point{float x=0,y=0,z=0;};
struct Spline{unsigned id=1;unsigned GetId(){return id;}bool done=true;Point end;bool Finalized(){return done;}Point FinalDestination(){return end;}};
struct Motion{Spline* spline;unsigned moves=0;std::vector<Point> dispatched;void MovePath(std::vector<Point>& p,unsigned,bool,bool=false){++moves;dispatched=p;spline->done=false;spline->end=p.back();++spline->id;}};
struct Unit{float x=0,y=0,z=0;unsigned map=469,instance=1,guid=1,entry=0;unsigned GetEntry(){return entry;}bool world=true,alive=true,combat=false,charmed=false,hostile=true;
 bool stealth=false,detect=false,stalked=false;std::vector<unsigned> attackers;
 bool HasAuraType(unsigned a){return a==SPELL_AURA_MOD_STEALTH?stealth:detect;}
 bool HasAuraTypeWithCaster(unsigned,unsigned){return stalked;}const auto& getAttackers(){return attackers;}
 bool HasFlag(unsigned,unsigned){return true;}struct Visibility{float GetStealthVisibilityDistance(Unit*,bool){return 0.5f;}} visibility;
 Visibility& GetVisibilityData(){return visibility;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool CanAttackOnSight(Unit*){return hostile;}float GetAttackDistance(Unit*){return 2;}unsigned GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}};
struct InstanceData{unsigned phase=0;unsigned GetData(unsigned){return phase;}};
struct Map{InstanceData instance;InstanceData* GetInstanceData(){return &instance;}};
struct Player:Unit{Map mapData;bool group=true;Map* GetMap(){return &mapData;}Player* GetGroup(){return group?this:nullptr;}bool casting=false;Spline spline;Spline* movespline=&spline;Motion motion{&spline};
 bool IsNonMeleeSpellCasted(bool){return casting;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}bool teleport=false;bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit* u){return map==u->map&&instance==u->instance;}void SetStandState(unsigned){}Motion* GetMotionMaster(){return &motion;}};
struct GameObject:Unit{};
struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Unit* u):map(u->map),x(u->x),y(u->y),z(u->z){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}};
using HazardPosition=std::pair<WorldPosition,float>;
__GEOMETRY__
using namespace ai;
struct SuppressionDuty{unsigned device=1,instance=1,generation=1,movingDevice=0,splineId=0,recoveryAt=0;bool routeOwned=false,routeStealthed=false,returning=false;float originX=0,originY=0,originZ=0;std::map<unsigned,unsigned> rejected;};
struct Value{SuppressionDuty state;SuppressionDuty Get(){return state;}void Set(SuppressionDuty s){state=s;}};
struct Context{Value value;template<class T>Value* GetValue(const char*){return &value;}};
struct PlayerbotAI{Player* bot;bool movable=true;Context context;std::map<unsigned,Unit*> units;std::list<unsigned> nearby;std::list<HazardPosition> hazards;
 bool real=false;unsigned generation=1;Player* GetBot(){return bot;}unsigned GetTransitionGeneration(){return generation;}bool IsRealPlayer(){return real;}bool CanMove(){return movable;}Context* GetAiObjectContext(){return &context;}Unit* GetUnit(unsigned id){return units[id];}void StopMoving(){bot->spline.done=true;}};
unsigned tick=1000;struct WorldTimer{static unsigned getMSTime(){return tick;}static unsigned getMSTimeDiff(unsigned a,unsigned b){return b-a;}};
std::vector<Point> route={{0,0,0},{12,0,0}};bool pathOk=true;unsigned pathType=PATHFIND_NORMAL;
struct PathFinder{PathFinder(Player*){}bool calculate(float,float,float,bool){return pathOk;}unsigned getPathType(){return pathType;}std::vector<Point>& getPath(){return route;}};
GameObject device;bool assigned=true,inRange=false;
GameObject* AssignedSuppressionDevice(PlayerbotAI*){return assigned?&device:nullptr;}
bool SuppressionDeviceInCastRange(PlayerbotAI*,GameObject*){return inRange;}
void AppendBlackwingGroundHazards(PlayerbotAI*,std::list<HazardPosition>&){}
struct Event{};
struct MoveToSuppressionDeviceAction{PlayerbotAI* ai;Player* bot;bool Execute(Event&);void SetDuration(unsigned){}};
#define AI_VALUE(type,key) ai->hazards
#define AI_VALUE2(type,key,qualifier) ai->nearby
namespace ai{bool SuppressionDutyOwnsMovement(PlayerbotAI*);}
__OWNERSHIP__
class Action; // Native headers also forward-declare a distinct global Action.
namespace ai { struct Action{std::string name;std::string getName(){return name;}}; }
struct Multiplier{PlayerbotAI* ai;Multiplier(PlayerbotAI* a,const char*):ai(a){}virtual float GetValue(ai::Action*){return 1;}};
__MULTIPLIER__
__METHOD__
int main(){
 Player bot;PlayerbotAI ai{&bot};MoveToSuppressionDeviceAction action{&ai,&bot};Event event;device.x=12;
 auto fresh=[&](){ai.context.value.state={};bot.spline.done=true;return action.Execute(event);};
 assert(fresh()&&bot.motion.moves==1&&bot.motion.dispatched.size()==2);
 PreserveSuppressionDutyMovementMultiplier preserve(&ai);ai::Action follow{"follow"},attack{"melee"},heal{"flash heal"},escape{"move away from hazard"},defense{"vanish"};
 assert(preserve.GetValue(&follow)==0 && preserve.GetValue(&attack)==1 && preserve.GetValue(&heal)==1 && preserve.GetValue(&escape)==1 && preserve.GetValue(&defense)==1);
 Unit enemy;enemy.x=6;enemy.guid=2;ai.units[2]=&enemy;ai.nearby={2};
 assert(!fresh()&&bot.motion.moves==1&&ai.context.value.state.rejected.count(1));
 enemy.combat=true;assert(fresh());
 enemy.entry=12468;assert(!fresh()); // Engaged Growing Flames still breaks stealth: do not route through it.
 enemy.entry=0;enemy.combat=false;
 route={{0,0,0},{0,7,0},{12,7,0},{12,0,0}};assert(fresh()); // whole checked detour
 route={{0,0,0},{0,3,0},{12,3,0},{12,0,0}};assert(!fresh());
 bot.stealth=true;assert(fresh()); // native stealth range, not ordinary aggro
 bot.stalked=true;assert(!fresh());bot.stalked=false;
 bot.attackers={2};assert(!fresh());bot.attackers.clear();
#ifndef MANGOSBOT_ZERO
 enemy.detect=true;assert(!fresh());enemy.detect=false;
#endif
 bot.stealth=false;
 route={{0,0,0},{12,0,0}};enemy.instance=2;assert(fresh());enemy.instance=1;
 enemy.hostile=false;assert(fresh());enemy.hostile=true;
 ai.nearby.clear();ai.hazards.emplace_back(WorldPosition(469,6,0,0),2.0f);assert(!fresh());ai.hazards.clear();
 pathType=2;assert(!fresh());pathType=1;pathOk=false;assert(!fresh());pathOk=true;
 route={{0,0,0},{100,0,0},{12,0,0}};assert(!fresh());route={{0,0,0},{12,0,0}};
 bot.casting=true;assert(!fresh());bot.casting=false;ai.movable=false;assert(!fresh());ai.movable=true;
 assert(fresh());auto moves=bot.motion.moves;assert(action.Execute(event)&&bot.motion.moves==moves);
 // Emergency/native replacement movement is never cancelled or overwritten.
 ++bot.spline.id;bot.spline.end={20,0,0};assert(!action.Execute(event)&&bot.motion.moves==moves&&!bot.spline.done);
 assert(!ai.context.value.state.routeOwned&&ai.context.value.state.rejected.count(1));assert(preserve.GetValue(&follow)==1);
 inRange=true;assert(!fresh());inRange=false;assigned=false;assert(!fresh());assigned=true;
 // A leader-change return request stops the old outbound leg even while casting.
 bot.stealth=true;assert(fresh());bot.x=6;ai.context.value.state.returning=true;ai.context.value.state.recoveryAt=tick;
 bot.casting=true;assert(!action.Execute(event)&&bot.spline.done&&bot.casting&&!ai.context.value.state.routeOwned);
 bot.casting=false;bot.x=0;
 // Lost stealth/assignment stops the old outbound spline before a safe return.
 bot.stealth=true;assert(fresh());bot.x=6;bot.stealth=false;assigned=false;
 route={{6,0,0},{0,0,0}};assert(action.Execute(event));
 assert(ai.context.value.state.returning&&ai.context.value.state.rejected.count(1)&&bot.spline.end.x==0);
 assert(SuppressionDutyOwnsMovement(&ai));
 // A finished return cannot leave a persistent duty lock.
 bot.x=0;bot.spline.done=true;assert(!action.Execute(event));assert(!ai.context.value.state.returning);
 assigned=true;route={{0,0,0},{12,0,0}};bot.stealth=true;assert(fresh());
 bot.x=6;bot.stealth=false;assigned=false;bot.casting=true;
 assert(!action.Execute(event)&&bot.spline.done&&bot.casting); // cancellation does not stop a cast
 bot.casting=false;route={{6,0,0},{0,0,0}};enemy.x=3;ai.nearby={2};
 assert(!action.Execute(event)&&bot.spline.done&&!ai.context.value.state.returning); // unsafe return yields to combat
 ai.nearby.clear();bot.x=0;assigned=true;bot.stealth=true;route={{0,0,0},{12,0,0}};assert(fresh());
 bot.x=6;assigned=false;bot.stealth=false;route={{6,0,0},{0,0,0}};assert(action.Execute(event));
 tick+=8001;assert(!action.Execute(event)&&!ai.context.value.state.returning&&bot.spline.done); // bounded recovery
 bot.x=0;assigned=true;route={{0,0,0},{12,0,0}};assert(fresh());
 bot.teleport=true;assert(!action.Execute(event)&&!ai.context.value.state.routeOwned);bot.teleport=false;
 assert(fresh());bot.mapData.instance.phase=IN_PROGRESS;assert(!action.Execute(event)&&bot.spline.done&&!ai.context.value.state.returning);
 bot.mapData.instance.phase=0;assert(fresh());bot.group=false;assert(!action.Execute(event)&&bot.spline.done);bot.group=true;
 assert(fresh());++ai.generation;assert(!SuppressionDutyOwnsMovement(&ai));assert(!action.Execute(event));

}
'''.replace('__GEOMETRY__',geometry).replace('__MULTIPLIER__',multiplier).replace('__OWNERSHIP__',ownership).replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='bwl-route-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
