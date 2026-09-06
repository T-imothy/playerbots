"""Compile actual AoE selection/position code, including stale-GUID transitions."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/values/AoeValues.cpp').read_text()
methods = '\n'.join(block(source, marker) for marker in (
    'bool IsCurrentAoeTarget(',
    'std::list<ObjectGuid> AoeCountValue::FindMaxDensity(',
    'WorldLocation AoePositionValue::Calculate(',
    'uint8 AoeCountValue::Calculate('))
fixture = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <vector>
using uint8=unsigned char;
using ObjectGuid=unsigned;
constexpr float CONTACT_DISTANCE=0.5f;
struct Unit {
 bool world=true,alive=true;unsigned map=409,instance=1,phase=1;float x=0,y=0,z=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
};
struct PlayerbotAI;
struct Player:Unit {
 PlayerbotAI* ai=nullptr;int heightChecks=0;
 bool IsInMap(Unit* u){return world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 PlayerbotAI* GetPlayerbotAI(){return ai;}unsigned GetMapId(){return map;}
 void UpdateAllowedPositionZ(float,float,float& height){++heightChecks;height=7.0f;}
};
struct Context {
 std::list<ObjectGuid> possible;
 template<class T>T* GetValue(const char*){return &possible;}
};
struct PlayerbotAI {
 Context context;std::map<unsigned,Unit*> units;unsigned lookups=0,expireAfter=0,expireGuid=0;
 Context* GetAiObjectContext(){return &context;}
 Unit* GetUnit(unsigned id){++lookups;if(expireAfter&&lookups>expireAfter&&(!expireGuid||expireGuid==id))return nullptr;
  auto it=units.find(id);return it==units.end()?nullptr:it->second;}
};
struct Facade {
 float GetDistance2d(Unit* a,Unit* b){return std::hypot(a->x-b->x,a->y-b->y);}
 bool IsDistanceLessOrEqualThan(float a,float b){return a<=b;}
} sServerFacade;
struct {float aoeRadius=100.0f;} sPlayerbotAIConfig;
struct WorldLocation {
 bool valid=false;unsigned map=0;float x=0,y=0,z=0;
 WorldLocation()=default;
 WorldLocation(unsigned m,float a,float b,float c,float):valid(true),map(m),x(a),y(b),z(c){}
};
namespace ai {
 struct AoeCountValue {Player* bot;static std::list<ObjectGuid> FindMaxDensity(Player*,float=100.0f);uint8 Calculate();};
 struct AoePositionValue {Player* bot;WorldLocation Calculate();};
}
using namespace ai;
__METHODS__
int main(){
 Player bot;PlayerbotAI ai;bot.ai=&ai;AoePositionValue pos{&bot};AoeCountValue count{&bot};
 assert(!pos.Calculate().valid);assert(count.Calculate()==0);assert(AoeCountValue::FindMaxDensity(nullptr).empty());
 Unit first,second;first.x=-20;first.y=10;second.x=20;second.y=30;
 ai.units={{1,&first},{2,&second}};ai.context.possible={1,2};
 auto p=pos.Calculate();assert(p.valid&&p.x==0&&p.y==20&&p.z==7&&p.map==409);
 // Density resolves six times for two targets, then position resolves the
 // selected GUIDs again. The first target vanishes exactly between those steps.
 ai.lookups=0;ai.expireAfter=6;ai.expireGuid=1;
 p=pos.Calculate();assert(p.valid&&p.x==20&&p.y==30);
 ai.lookups=0;ai.expireGuid=0;int checks=bot.heightChecks;
 assert(!pos.Calculate().valid&&bot.heightChecks==checks); // all GUIDs disappear
 ai.expireAfter=0;ai.context.possible={99,1,2}; // already-stale GUID
 assert(count.Calculate()==2);
 first.alive=false;assert(count.Calculate()==1);first.alive=true;
 first.world=false;assert(count.Calculate()==1);first.world=true;
 first.instance=2;assert(count.Calculate()==1);first.instance=1;
 first.phase=2;assert(count.Calculate()==1);first.phase=1;
 first.map=0;assert(count.Calculate()==1);first.map=409;
 first.x=1000;assert(count.Calculate()==1);first.x=-20;
 bot.world=false;assert(!pos.Calculate().valid&&count.Calculate()==0);bot.world=true;
 // A large pack cannot wrap the uint8 count to zero and disable AoE decisions.
 std::vector<Unit> many(256);ai.units.clear();ai.context.possible.clear();
 for(unsigned i=0;i<many.size();++i){ai.units[i+1]=&many[i];ai.context.possible.push_back(i+1);}
 assert(count.Calculate()==255);
 std::cout<<"PASS: actual AoE stale-first/all, lifecycle, instance/phase, bounds, count saturation\n";
}
'''.replace('__METHODS__', methods)
for expansion in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-aoe-lifetime-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(fixture)
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/W4', f'/DMANGOSBOT_{expansion}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
