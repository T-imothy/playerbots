"""Exercise the production escape action with different bot/hazard path origins."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/DungeonActions.cpp').read_text()
methods='\n'.join(block(source, signature) for signature in ('bool MoveAwayFromHazard::Execute(', 'bool MoveAwayFromHazard::IsHazardNearby('))
code=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <list>
#include <vector>
#include <iostream>
using uint8=uint8_t;using int8=int8_t;
constexpr float M_PI=3.14159265358979323846f,M_PI_F=M_PI;constexpr int TEMPSPAWN_TIMED_DESPAWN=0;
float frand(float a,float b){return (a+b)/2;}unsigned urand(unsigned a,unsigned){return a;}
struct Unit{float x=0,y=0,z=0;};
struct Player:Unit{bool world=true,alive=true,charmed=false,teleport=false;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}
 unsigned GetMapId(){return 1;}float GetCollisionHeight(){return 1;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 bool IsWithinLOS(float,float,float){return true;}void SummonCreature(unsigned,float,float,float,float,unsigned,float){}
};
static std::vector<float> pathOrigins;static bool allowBot=true,allowCenter=false;
struct WorldPosition{unsigned map=1;float x=0,y=0,z=0;
 WorldPosition()=default;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Unit*u):x(u->x),y(u->y),z(u->z){}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}unsigned getMapId()const{return map;}
 void setZ(float a){z=a;}float getHeight()const{return 0;}
 WorldPosition operator+(const WorldPosition&o)const{return {map,x+o.x,y+o.y,z+o.z};}
 float distance(const WorldPosition&o)const{return std::sqrt((x-o.x)*(x-o.x)+(y-o.y)*(y-o.y)+(z-o.z)*(z-o.z));}
 float getAngleTo(const WorldPosition&o)const{return std::atan2(o.y-y,o.x-x);}
 bool canPathTo(const WorldPosition&,Player*bot)const{pathOrigins.push_back(x);return x==bot->x?allowBot:allowCenter;}
};
using HazardPosition=std::pair<WorldPosition,float>;
enum class BotState{BOT_STATE_COMBAT};
struct PlayerbotAI{Player*bot;std::list<HazardPosition>hazards;bool canMove=true;
 bool HasStrategy(const char*,BotState){return false;}bool CanMove(){return canMove;}
 template<class T>T Value(const char*){if constexpr(std::is_same_v<T,Unit*>)return nullptr;else return hazards;}
};
struct Event{};struct MoveAwayFromHazard{PlayerbotAI*ai;Player*bot;unsigned moves=0;float waited=0;
 bool Execute(Event&);bool IsHazardNearby(const WorldPosition&,const std::list<HazardPosition>&)const;
 bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++moves;return true;}
 bool IsReaction(){return true;}void WaitForReach(float distance){waited=distance;}
};
#define AI_VALUE(type,name) ai->Value<type>(name)
__METHODS__
int main(){
 Player bot;bot.x=4;PlayerbotAI ai{&bot};ai.hazards={{{1,0,0,0},8}};
 MoveAwayFromHazard action{&ai,&bot};Event event;
 // A path from the center is blocked; the bot itself has an escape route.
 assert(action.Execute(event)&&action.moves==1);assert(pathOrigins.front()==4);
 allowBot=false;allowCenter=true;pathOrigins.clear();assert(!action.Execute(event)&&action.moves==1);
 assert(pathOrigins.size()==10);for(float x:pathOrigins)assert(x==4); // bounded attempts
 allowBot=true;ai.canMove=false;assert(!action.Execute(event));ai.canMove=true;
 for(bool Player::*flag:{&Player::charmed,&Player::teleport}){bot.*flag=true;assert(!action.Execute(event));bot.*flag=false;}
 bot.world=false;assert(!action.Execute(event));bot.world=true;bot.alive=false;assert(!action.Execute(event));bot.alive=true;
 ai.hazards={{{2,0,0,0},8}};assert(!action.Execute(event));
 ai.hazards.clear();assert(!action.Execute(event));
 std::cout<<"PASS: hazard escape uses bot origin, bounded paths and lifecycle/map guards\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-hazard-origin-') as folder:
 tmp=Path(folder);(tmp/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
