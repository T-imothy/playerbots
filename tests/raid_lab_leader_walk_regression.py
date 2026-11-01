"""Actual local leader walk: native control, fight pauses and route refusal.

This tests the fixture, not follower combat/raid acceptance.
"""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include <cmath>
#include <string>
#include <vector>
#include <iostream>
using uint64=unsigned long long;
enum class TestResult{PENDING,PASS,IMPOSSIBLE};
constexpr float INVALID_HEIGHT=-10000;constexpr int FORCED_MOVEMENT_RUN=1;
struct Point{float x=10,y=0,z=0;};
struct Spline{bool done=true;Point end;bool Finalized(){return done;}Point FinalDestination(){return end;}};
struct Map{float height=0;float GetHeight(float,float,float){return height;}};
struct Motion{unsigned clears=0,moves=0;void Clear(bool,bool){++clears;}template<class T>void MovePath(T&,int mode,bool,bool){assert(mode==1);++moves;}};
struct Player;
struct Ref{Player*p;Ref*n=nullptr;Player*getSource(){return p;}Ref*next(){return n;}};
struct Group{Ref*head;Ref*GetFirstMember(){return head;}};
struct Player{bool alive=true,tp=false,charm=false,transport=false,combat=false,world=true,stopped=true,same=true;
 float distance=10;unsigned stops=0;Group*group=nullptr;Map map;Motion motion;Spline spline;Spline*movespline=&spline;
 bool IsAlive(){return alive;}bool IsBeingTeleported(){return tp;}bool HasCharmer(){return charm;}bool GetTransport(){return transport;}
 float GetDistance(float,float,float){return distance;}bool IsStopped(){return stopped;}void StopMoving(){++stops;stopped=true;}
 bool IsInCombat(){return combat;}Group*GetGroup(){return group;}bool IsInWorld(){return world;}bool IsInMap(Player*){return same;}
 Map*GetMap(){return &map;}unsigned GetMapId(){return 509;}Motion*GetMotionMaster(){return &motion;}};
struct PlayerbotAI{bool canMove=true;bool CanMove(){return canMove;}};
struct WorldPosition{unsigned map=509;float x=0,y=0,z=0;static bool complete,finite,same;static unsigned count;
 WorldPosition(){}WorldPosition(Player*){}WorldPosition(unsigned m,float x,float y,float z):map(m),x(x),y(y),z(z){}
 std::vector<WorldPosition>getPathStepFrom(WorldPosition,Player*,bool fresh){assert(fresh);WorldPosition point;point.x=finite?1:NAN;point.map=same?509:469;return std::vector<WorldPosition>(count,point);}
 bool isPathTo(const std::vector<WorldPosition>&,float,float){return complete;}unsigned getMapId()const{return map;}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 auto toPointsArray(const std::vector<WorldPosition>&v){return v;}};
bool WorldPosition::complete=true,WorldPosition::finite=true,WorldPosition::same=true;unsigned WorldPosition::count=2;
namespace RaidLab{unsigned events=0;void Event(Player*,const char*,uint64){++events;}}
'''
code+=block((root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text(),'TestResult RaidLabLeaderWalk(')
code+=r'''
int main(){
 Player p,friendBot;Ref friendRef{&friendBot},self{&p,&friendRef};Group group{&self};p.group=&group;PlayerbotAI ai;std::string message;
 auto run=[&](){return RaidLabLeaderWalk(&p,&ai,10,0,0,message);};
 ai.canMove=false;p.stopped=false;p.distance=1;assert(run()==TestResult::PENDING&&p.stops==0&&p.motion.moves==0);
 ai.canMove=true;p.distance=10;friendBot.combat=true;assert(run()==TestResult::PENDING&&p.stops==1&&p.motion.moves==0);
 friendBot.combat=false;p.spline.done=false;assert(run()==TestResult::PENDING&&p.motion.moves==0); // retain current route
 p.spline.done=true;p.map.height=8;assert(run()==TestResult::IMPOSSIBLE&&p.motion.moves==0);p.map.height=0;
 WorldPosition::complete=false;assert(run()==TestResult::IMPOSSIBLE&&p.motion.moves==0);WorldPosition::complete=true;
 WorldPosition::count=257;assert(run()==TestResult::IMPOSSIBLE&&p.motion.moves==0);WorldPosition::count=2;
 WorldPosition::finite=false;assert(run()==TestResult::IMPOSSIBLE&&p.motion.moves==0);WorldPosition::finite=true;
 WorldPosition::same=false;assert(run()==TestResult::IMPOSSIBLE&&p.motion.moves==0);WorldPosition::same=true;
 assert(run()==TestResult::PENDING&&p.motion.moves==1&&RaidLab::events==1);
 friendBot.combat=true;
 assert(RaidLabLeaderWalk(&p,&ai,10,0,0,message,true)==TestResult::PENDING&&p.motion.moves==2);
 friendBot.combat=false;
 p.distance=1;p.stopped=false;assert(run()==TestResult::PASS&&p.stops==2);
 std::cout<<"PASS local leader walk retains native control, pauses for group combat, retains route, rejects invalid/partial paths, requires actual arrival\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-leader-walk-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
