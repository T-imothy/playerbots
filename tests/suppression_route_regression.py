"""Execute the production trap approach, including actual segment geometry."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
method=block(source,'bool MoveToSuppressionDeviceAction::Execute(').replace('state.device.Clear()','state.device = 0')
geometry=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
geometry=geometry[geometry.index('namespace ai'):]
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{PATHFIND_NORMAL=1,FORCED_MOVEMENT_RUN=1,UNIT_STAND_STATE_STAND=0};
struct Point{float x=0,y=0,z=0;};
struct Spline{bool done=true;Point end;bool Finalized(){return done;}Point FinalDestination(){return end;}};
struct Motion{unsigned moves=0;std::vector<Point> dispatched;void MovePath(std::vector<Point>& p,unsigned,bool,bool=false){++moves;dispatched=p;}};
struct Unit{float x=0,y=0,z=0;unsigned map=469,instance=1,guid=1;bool world=true,alive=true,combat=false,charmed=false,hostile=true;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool CanAttackOnSight(Unit*){return hostile;}float GetAttackDistance(Unit*){return 2;}unsigned GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}};
struct Player:Unit{bool casting=false;Spline spline;Spline* movespline=&spline;Motion motion;
 bool IsNonMeleeSpellCasted(bool){return casting;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit* u){return map==u->map&&instance==u->instance;}void SetStandState(unsigned){}Motion* GetMotionMaster(){return &motion;}};
struct GameObject:Unit{};
struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Unit* u):map(u->map),x(u->x),y(u->y),z(u->z){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}};
using HazardPosition=std::pair<WorldPosition,float>;
__GEOMETRY__
using namespace ai;
struct SuppressionDuty{unsigned device=1;std::map<unsigned,unsigned> rejected;};
struct Value{SuppressionDuty state;SuppressionDuty Get(){return state;}void Set(SuppressionDuty s){state=s;}};
struct Context{Value value;template<class T>Value* GetValue(const char*){return &value;}};
struct PlayerbotAI{Player* bot;bool movable=true;Context context;std::map<unsigned,Unit*> units;std::list<unsigned> nearby;std::list<HazardPosition> hazards;
 bool CanMove(){return movable;}Context* GetAiObjectContext(){return &context;}Unit* GetUnit(unsigned id){return units[id];}void StopMoving(){bot->spline.done=true;}};
struct WorldTimer{static unsigned getMSTime(){return 1000;}};
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
__METHOD__
int main(){
 Player bot;PlayerbotAI ai{&bot};MoveToSuppressionDeviceAction action{&ai,&bot};Event event;device.x=12;
 assert(action.Execute(event)&&bot.motion.moves==1&&bot.motion.dispatched.size()==2);
 Unit enemy;enemy.x=6;enemy.guid=2;ai.units[2]=&enemy;ai.nearby={2};
 assert(!action.Execute(event)&&bot.motion.moves==1&&ai.context.value.state.rejected.count(1));
 enemy.combat=true;assert(action.Execute(event));enemy.combat=false;
 route={{0,0,0},{0,7,0},{12,7,0},{12,0,0}};assert(action.Execute(event)); // whole checked detour
 route={{0,0,0},{12,0,0}};enemy.instance=2;assert(action.Execute(event));enemy.instance=1;
 enemy.hostile=false;assert(action.Execute(event));enemy.hostile=true;
 ai.nearby.clear();ai.hazards.emplace_back(WorldPosition(469,6,0,0),2);assert(!action.Execute(event));ai.hazards.clear();
 pathType=2;assert(!action.Execute(event));pathType=1;pathOk=false;assert(!action.Execute(event));pathOk=true;
 route={{0,0,0},{100,0,0},{12,0,0}};assert(!action.Execute(event));route={{0,0,0},{12,0,0}};
 bot.casting=true;assert(!action.Execute(event));bot.casting=false;ai.movable=false;assert(!action.Execute(event));ai.movable=true;
 bot.spline.done=false;bot.spline.end={12,0,0};auto moves=bot.motion.moves;assert(action.Execute(event)&&bot.motion.moves==moves);
 bot.spline.end={20,0,0};assert(action.Execute(event)&&bot.motion.moves==moves+1); // replace unrelated route
 inRange=true;assert(!action.Execute(event));inRange=false;assigned=false;assert(!action.Execute(event));
}
'''.replace('__GEOMETRY__',geometry).replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='bwl-route-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
