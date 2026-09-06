"""Actual movement dispatch preserves verified hazard routes and rejects failed navigation."""
from pathlib import Path
import subprocess
import tempfile
import sys
from behavior_regression import block

repo=Path(__file__).resolve().parents[1]
source=(repo/'playerbot/strategy/actions/MovementActions.cpp').read_text()
if '--before-empty-move' in sys.argv:
    source=subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),
        'show','8e74916a:playerbot/strategy/actions/MovementActions.cpp'],text=True)
methods='\n'.join(block(source, marker) for marker in ('bool MovementAction::BuildSafeHazardPath(', 'bool MovementAction::DispatchMovement('))
safety=(repo/'playerbot/strategy/actions/MovementPathSafety.h').read_text().replace('#pragma once','').replace('#include "playerbot/strategy/values/HazardsValue.h"','')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <list>
#include <vector>
using uint32=uint32_t;
namespace G3D {struct Vector3{float x=0,y=0,z=0;};}
struct Position {float x,y,z,o;Position(float a,float b,float c,float d):x(a),y(b),z(c),o(d){}};
enum ForcedMovement{FORCED_MOVEMENT_WALK,FORCED_MOVEMENT_RUN,FORCED_MOVEMENT_FLIGHT};
enum{MOVE_FLIGHT,PATHFIND_NORMAL=1,PATHFIND_NOPATH=2};
struct MotionMaster {unsigned clears=0,points=0,paths=0;bool generated=false;std::vector<G3D::Vector3> route;
 void Clear(){++clears;}void MovePath(std::vector<G3D::Vector3>& p,ForcedMovement,bool,bool=false){++paths;route=p;}
 void MovePoint(unsigned,float x,float y,float z,ForcedMovement,bool gen){++points;generated=gen;route={{x,y,z}};}
 void MovePoint(unsigned,Position p,ForcedMovement,float,bool gen){++points;generated=gen;route={{p.x,p.y,p.z}};}};
struct Unit {float x=-10,y=0,z=0;unsigned map=1;bool flying=false,transport=false,navFail=false,navEmpty=false,navShort=false;MotionMaster motion;
 unsigned GetMapId()const{return map;}void* GetTransport(){return transport?this:nullptr;}
 bool IsFlying(){return flying;}bool IsFreeFlying(){return flying;}float GetSpeed(int){return 7;}
 MotionMaster* GetMotionMaster(){return &motion;}};
namespace ai {
struct WorldPosition {unsigned map=1;float x=0,y=0,z=0;
 WorldPosition()=default;WorldPosition(Unit* p):map(p->map),x(p->x),y(p->y),z(p->z){}
 WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 G3D::Vector3 getVector3()const{return {x,y,z};}
 float distance(const WorldPosition& p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}
 bool isPathTo(const std::vector<WorldPosition>& path)const{return !path.empty()&&path.back().map==map&&distance(path.back())<0.1f;}
 float getPathLength(const std::vector<WorldPosition>& p){float sum=0;for(size_t i=1;i<p.size();++i)sum+=p[i-1].distance(p[i]);return sum;}
 std::vector<G3D::Vector3> toPointsArray(const std::vector<WorldPosition>& p){std::vector<G3D::Vector3> out;for(auto& point:p)out.push_back(point.getVector3());return out;}};
using HazardPosition=std::pair<WorldPosition,float>;
struct TravelPath {std::vector<WorldPosition> path;std::vector<WorldPosition> getPointPath(){return path;}};
struct PlayerbotAI {std::list<HazardPosition> hazards;};
struct MovementAction {PlayerbotAI* ai;Unit* bot;Unit* mover;bool detour=false;float waited=0;
 Unit* GetMover(Unit*){return mover;}void WaitForReach(float distance){waited=distance;}
 bool GeneratePathAvoidingHazards(std::vector<WorldPosition>& path){if(detour&&path.size()>2){path[1].y=3;return true;}return false;}
 bool BuildSafeHazardPath(std::vector<WorldPosition>&,Unit*);
 bool DispatchMovement(TravelPath,bool,bool);};
}
using namespace ai;
struct PathFinder {Unit* unit;std::vector<G3D::Vector3> path;PathFinder(Unit* u):unit(u){}
 bool calculate(G3D::Vector3 start,G3D::Vector3 end,bool force){assert(!force);path={start,end};if(unit->navEmpty)path.clear();else if(unit->navShort)path.back()=start;return end.x < 50000;}
 int getPathType(){return unit->navFail?PATHFIND_NOPATH:PATHFIND_NORMAL;}
 std::vector<G3D::Vector3>& getPath(){return path;}};
#define AI_VALUE(type,name) ai->hazards
__SAFETY__
__METHODS__
int main(){
 PlayerbotAI ai;Unit bot;MovementAction action{&ai,&bot,&bot};
 TravelPath route{{{1,-10,0,0},{1,0,0,0},{1,10,0,0}}};
 assert(!action.DispatchMovement({},true,false));assert(bot.motion.clears==0);
 TravelPath invalid=route;invalid.path.back().x=std::numeric_limits<float>::quiet_NaN();
 assert(!action.DispatchMovement(invalid,true,false));invalid=route;invalid.path.back().map=2;
 assert(!action.DispatchMovement(invalid,true,false));assert(bot.motion.clears==0);
 // Clipping can leave only the current position although the original target
 // was distant. Do not dispatch a zero-length native spline for that result.
 TravelPath clipped{{{1,-10,0,0}}};assert(!action.DispatchMovement(clipped,true,false));
 clipped.path.back().x=-9.99f;assert(!action.DispatchMovement(clipped,true,false));
 assert(bot.motion.clears==0&&bot.motion.points==0);
 assert(action.DispatchMovement(route,true,false));assert(bot.motion.points==1&&bot.motion.generated&&bot.motion.paths==0);
 ai.hazards={{{1,0,0,0},2}};action.detour=true;
 assert(action.DispatchMovement(route,true,false));assert(bot.motion.paths==1&&bot.motion.route.size()==3&&bot.motion.route[1].y==3);
 auto clears=bot.motion.clears;bot.navFail=true;
 assert(!action.DispatchMovement(route,true,false));assert(bot.motion.clears==clears);bot.navFail=false;
 bot.navEmpty=true;assert(!action.DispatchMovement(route,true,false));bot.navEmpty=false;
 bot.navShort=true;assert(!action.DispatchMovement(route,true,false));bot.navShort=false;
 bot.transport=true;assert(!action.DispatchMovement(route,true,false));bot.transport=false;
 auto overBudget=route;overBudget.path.resize(65,{1,10,0,0});assert(!action.DispatchMovement(overBudget,true,false));
 auto originalX=bot.x;bot.x=std::numeric_limits<float>::quiet_NaN();assert(!action.DispatchMovement(route,true,false));bot.x=originalX;
 auto outsideMap=route;outsideMap.path.back().x=50000;assert(!action.DispatchMovement(outsideMap,true,false)); // Native calculate can reject finite out-of-map coordinates.
 action.detour=false;assert(!action.DispatchMovement(route,true,false));assert(bot.motion.clears==clears); // Unsafe route is not forced through the hazard.
 assert(action.DispatchMovement(route,false,false));assert(!bot.motion.generated); // Preserve explicit non-navmesh movement.
 assert(!IsHazardSafeSegment({1,-10,0,0},{1,10,0,0},ai.hazards));
 assert(IsHazardSafeSegment({1,-10,0,10},{1,10,0,10},ai.hazards)); // Different floor.
 assert(IsHazardSafeSegment({1,1,0,0},{1,3,0,0},ai.hazards));
 assert(!IsHazardSafeSegment({1,1,0,0},{1,-3,0,0},ai.hazards)); // Escape must not cut through the center.
 assert(IsHazardSafeSegment({2,-10,0,0},{2,10,0,0},ai.hazards));
 Unit vehicle;action.mover=&vehicle;ai.hazards.clear();
 assert(action.DispatchMovement(route,true,false));assert(vehicle.motion.points==1);
 action.mover=nullptr;assert(!action.DispatchMovement(route,true,false));
 std::cout<<"PASS: native detour dispatch, empty/nonfinite/map guards, failed navigation, whole-segment hazards and selected mover\n";
}
'''.replace('__SAFETY__',safety).replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-movement-dispatch-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
