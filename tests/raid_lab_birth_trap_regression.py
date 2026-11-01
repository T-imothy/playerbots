"""Compile the actual local staging admission against controlled native failures."""
from pathlib import Path
import subprocess
import tempfile
import math,re
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
registration=(root/'playerbot/strategy/tests/RegisterInstance.cpp').read_text()
staging=re.search(r'\{533,15989,40,"533;([^;]+);([^;]+);([^;]+);[^\"]+","trap 181356"\}',registration)
assert staging,'Native Sapphiron proximity fixture missing'
x,y,z=map(float,staging.groups())
# Actual native GO181356 center/radius from the isolated database. GM-on does
# not prevent activation: even the initial scout must remain outside40yd.
assert math.hypot(x-3522.57,y+5236.76)>48 and abs(z-137.63)<2
code = r'''
#include <cassert>
#include <cmath>
#include <string>
#include <vector>
#include <map>
#include <iostream>
using uint32=unsigned;
constexpr float INVALID_HEIGHT=-10000;
enum class TestResult{PASS,PENDING,IMPOSSIBLE};
struct TestContext{};
struct Creature{bool alive=true;unsigned entry=1;bool IsInWorld(){return true;}bool IsAlive(){return alive;}
 unsigned GetEntry(){return entry;}float GetAttackDistance(void*){return 20;}float GetDistance(float,float,float){return 1;}};
struct Store{std::map<int,Creature*> creatures;template<class T>auto begin(){return creatures.begin();}template<class T>auto end(){return creatures.end();}};
struct Map{float floor=137.63f;Store store;float GetHeight(float,float,float){return floor;}Store&GetObjectsStore(){return store;}};
struct Player{Map map;unsigned teleports=0;float x=0,y=0,z=0;bool allowTeleport=true;
 unsigned GetMapId(){return 533;}float GetObjectBoundingRadius(){return .5f;}Map*GetMap(){return &map;}float GetOrientation(){return 0;}
 bool TeleportTo(unsigned,float a,float b,float c,float){if(!allowTeleport)return false;++teleports;x=a;y=b;z=c;return true;}};
struct GameObject{struct Info{struct Trap{unsigned diameter=80;}trap;} info;bool spawned=true;
 bool IsSpawned(){return spawned;}Info*GetGOInfo(){return &info;}};
GameObject object;bool hasTrap=true,hasReference=true,warm=true,bodyRisk=false,envelope=false;
GameObject*RaidLabBirthTrap(Player*){return hasTrap?&object:nullptr;}
Player*RaidLabAggroReference(Player*p){return hasReference?p:nullptr;}
struct Config{float raidFollowDistance=10;}sPlayerbotAIConfig;
bool RaidLabWarmPreparationGrid(Player*,TestContext&,const std::string&,float,float,std::string&){return warm;}
bool RaidLabBodyPullRisk(Creature*,Player*,bool){return bodyRisk;}
float RaidLabLandingRadius(float,float,float){return 35;}
bool RaidLabInsideWanderEnvelope(Creature*,float,float,float,float){return envelope;}
bool RaidLabInsidePatrolEnvelope(Creature*,float,float,float,float){return envelope;}
bool RaidLabFormationVisible(Creature*,Player*,float,float,float,float){return true;}
struct Log{template<class...T>void outString(const char*,T...){}}sLog;
struct WorldPosition{unsigned map=533;float x=3522.57f,y=-5236.76f,z=137.63f;
 static bool complete,finite,same;static unsigned count;
 WorldPosition(){}WorldPosition(GameObject*){}WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 std::vector<WorldPosition>getPathStepFrom(WorldPosition,Player*,bool fresh){assert(fresh);WorldPosition p;p.x=finite?x:NAN;p.map=same?533:469;return std::vector<WorldPosition>(count,p);}
 bool isPathTo(const std::vector<WorldPosition>&,float,float){return complete;}};
bool WorldPosition::complete=true,WorldPosition::finite=true,WorldPosition::same=true;unsigned WorldPosition::count=2;
'''
code += block(source, 'bool RaidLabSapphironFixture(')
code += block(source, 'TestResult RaidLabStageBirthTrap(')
code += r'''
int main(){
 assert(RaidLabSapphironFixture(533,15989,"raidlab_533_15989_leader_event"));
 assert(RaidLabSapphironFixture(533,15989,"raidlab_533_15989_leader_event_prepared"));
 assert(!RaidLabSapphironFixture(533,15989,"raidlab_533_15989_leader_event_prepared_extra"));
 assert(!RaidLabSapphironFixture(469,15989,"raidlab_533_15989_leader_event"));
 assert(!RaidLabSapphironFixture(533,15990,"raidlab_533_15989_leader_event"));
 assert(!RaidLabSapphironFixture(533,15989,"other"));
 Player p;TestContext ctx;std::string message;auto run=[&](){return RaidLabStageBirthTrap(&p,ctx,message);};
 auto refuse=[&](){assert(run()==TestResult::IMPOSSIBLE);assert(p.teleports==0);};
 hasTrap=false;refuse();hasTrap=true;hasReference=false;refuse();hasReference=true;
 object.spawned=false;refuse();object.spawned=true;
 object.info.trap.diameter=0;refuse();object.info.trap.diameter=240;refuse();object.info.trap.diameter=80;
 warm=false;assert(run()==TestResult::PENDING&&p.teleports==0);warm=true;
 p.map.floor=NAN;refuse();p.map.floor=160;refuse();p.map.floor=137.63f;
 WorldPosition::complete=false;refuse();WorldPosition::complete=true;
 WorldPosition::finite=false;refuse();WorldPosition::finite=true;
 WorldPosition::same=false;refuse();WorldPosition::same=true;
 WorldPosition::count=257;refuse();WorldPosition::count=2;
 Creature c;c.entry=15989;p.map.store.creatures[1]=&c;refuse();
 c.entry=1;bodyRisk=true;refuse();bodyRisk=false;p.map.store.creatures.clear();
 p.allowTeleport=false;refuse();p.allowTeleport=true;
 assert(run()==TestResult::PASS&&p.teleports==1);
 const float distance=std::hypot(p.x-3522.57f,p.y+5236.76f);
 assert(distance>58.4f&&distance<58.6f); // entire 10yd formation clears real 40yd trap
 assert(object.info.trap.diameter==80&&object.spawned); // native trigger never changed
 std::cout<<"PASS native trap staging: formation clears trigger; unsafe floor/path/aggro/activation refused without mutation\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-birth-trap-') as folder:
    path=Path(folder)
    (path/'test.cpp').write_text(code)
    result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/D_USE_MATH_DEFINES','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
    if result.returncode:
        print(result.stdout,result.stderr)
    result.check_returncode()
    subprocess.run([str(path/'test.exe')],check=True)
