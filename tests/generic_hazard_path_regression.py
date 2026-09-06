"""Actual generic hazard waypoint editing, including failed and degenerate paths."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/actions/MovementActions.cpp').read_text()
methods = block(source, 'WorldPosition CalculatePerpendicularPoint(') + '\n' + block(source, 'bool MovementAction::GeneratePathAvoidingHazards(')
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <list>
#include <vector>
using uint8=uint8_t;using uint32=uint32_t;
struct WorldPosition {
 unsigned map=1;float coord_x=0,coord_y=0,coord_z=0;
 WorldPosition()=default;WorldPosition(unsigned m,float x,float y,float z):map(m),coord_x(x),coord_y(y),coord_z(z){}
 float getX()const{return coord_x;}float getY()const{return coord_y;}float getZ()const{return coord_z;}
 void setX(float x){coord_x=x;}void setY(float y){coord_y=y;}
 float size()const{return std::sqrt(coord_x*coord_x+coord_y*coord_y+coord_z*coord_z);}
 WorldPosition operator-(const WorldPosition& p)const{return {map,coord_x-p.coord_x,coord_y-p.coord_y,coord_z-p.coord_z};}
 WorldPosition operator+(const WorldPosition& p)const{return {map,coord_x+p.coord_x,coord_y+p.coord_y,coord_z+p.coord_z};}
 WorldPosition operator*(float f)const{return {map,coord_x*f,coord_y*f,coord_z*f};}
 WorldPosition operator/(float f)const{return *this*(1/f);}
 float distance(const WorldPosition& p)const{return (*this-p).size();}
 explicit operator bool()const{return size()!=0;}
};
using HazardPosition=std::pair<WorldPosition,float>;
enum class BotState{BOT_STATE_COMBAT};enum{TEMPSPAWN_TIMED_DESPAWN};
struct Player {unsigned GetMapId(){return 1;}void SummonCreature(unsigned,float,float,float,float,unsigned,float){}};
struct PlayerbotAI {std::list<HazardPosition> hazards;bool HasStrategy(const char*,BotState){return false;}};
#define AI_VALUE(type,name) ai->hazards
struct MovementAction {PlayerbotAI* ai;Player* bot;int allowed=0;
 bool IsValidPosition(const WorldPosition& p,const WorldPosition&){return allowed==0||(allowed==1&&p.getY()<0);}
 bool GeneratePathAvoidingHazards(std::vector<WorldPosition>&);
};
__METHODS__
int main(){
 Player bot;PlayerbotAI ai;MovementAction action{&ai,&bot};ai.hazards={{{1,0,0,0},2}};
 std::vector<WorldPosition> path={{1,-10,0,0},{1,0,0,0},{1,10,0,0}};
 assert(action.GeneratePathAvoidingHazards(path));assert(path[1].getY()>2); // The chosen waypoint must actually be saved.
 assert(path.front().getX()==-10&&path.back().getX()==10);
 action.allowed=1;path={{1,-10,0,0},{1,0,0,0},{1,10,0,0}};
 assert(action.GeneratePathAvoidingHazards(path));assert(path[1].getY() < -2); // Fall back to the valid side.
 action.allowed=2;path={{1,-10,0,0},{1,0,0,0},{1,10,0,0}};
 assert(!action.GeneratePathAvoidingHazards(path));assert(path[1].getY()==0);
 path.clear();assert(!action.GeneratePathAvoidingHazards(path));
 path={{1,0,0,0}};assert(!action.GeneratePathAvoidingHazards(path));
 path.push_back({1,10,0,0});assert(!action.GeneratePathAvoidingHazards(path));
 ai.hazards.clear();assert(!action.GeneratePathAvoidingHazards(path));
 std::cout<<"PASS: generic hazard waypoint retention, alternate side, blocked detours and empty/short paths\n";
}
'''.replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-generic-hazard-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
