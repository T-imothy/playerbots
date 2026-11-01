"""Exercise the actual local native-trigger approach; no boss/timer bypass."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <string>
#include <iostream>
constexpr float INVALID_HEIGHT=-10000;
constexpr unsigned GAMEOBJECT_TYPE_TRAP=6;
enum class TestResult{PASS,PENDING,IMPOSSIBLE};
struct GameObject {bool world=true,spawned=true;unsigned type=6,entry=181356;float x=100,y=100,z=10;
 struct Info{struct Trap{float diameter=80;}trap;}info;
 bool IsInWorld(){return world;}bool IsSpawned(){return spawned;}unsigned GetGoType(){return type;}unsigned GetEntry(){return entry;}
 Info*GetGOInfo(){return &info;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
struct Map{float floor=10;float GetHeight(float,float,float){return floor;}};
struct Player{unsigned mapid=533;bool same=true;float x=160,y=100;Map map;
 bool IsInMap(GameObject*){return same;}unsigned GetMapId(){return mapid;}Map*GetMap(){return &map;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}};
struct PlayerbotAI{unsigned stops=0;void StopMoving(){++stops;}};
unsigned walks=0;float goalX=0,goalY=0,goalZ=0;bool nativeAllowed=true;
TestResult RaidLabLeaderWalk(Player*,PlayerbotAI*,float x,float y,float z,std::string&){++walks;goalX=x;goalY=y;goalZ=z;return nativeAllowed?TestResult::PENDING:TestResult::IMPOSSIBLE;}
__METHOD__
int main(){Player p;PlayerbotAI ai;GameObject trap;std::string msg;
 auto run=[&](){return RaidLabApproachBirthTrap(&p,&ai,&trap,msg);};
 assert(run()==TestResult::PENDING&&walks==1&&goalX==138&&goalY==100&&goalZ==10); // not center100
 nativeAllowed=false;assert(run()==TestResult::IMPOSSIBLE);nativeAllowed=true;
 p.x=138;assert(run()==TestResult::PASS&&ai.stops==1&&walks==2);
 p.x=100;p.y=160;assert(run()==TestResult::PENDING&&goalX==100&&goalY==138);
 trap.spawned=false;assert(run()==TestResult::PASS&&ai.stops==2);trap.spawned=true;
 auto refuse=[&](){auto before=walks;assert(run()==TestResult::IMPOSSIBLE&&walks==before);};
 p.same=false;refuse();p.same=true;p.mapid=469;refuse();p.mapid=533;
 trap.entry=1;refuse();trap.entry=181356;trap.type=1;refuse();trap.type=6;trap.world=false;refuse();trap.world=true;
 for(float invalid:{0.0f,6.0f,202.0f,NAN}){trap.info.trap.diameter=invalid;refuse();}trap.info.trap.diameter=80;
 p.x=NAN;refuse();p.x=100;p.map.floor=NAN;refuse();p.map.floor=25;refuse();
 assert(RaidLabApproachBirthTrap(&p,&ai,nullptr,msg)==TestResult::IMPOSSIBLE);
 assert(trap.info.trap.diameter==80&&trap.spawned);
 std::cout<<"PASS local birth approach: native edge, rejected floor/path/identity, stop on activation, no boss/trigger mutation\n";
}
'''.replace('__METHOD__',block(source,'TestResult RaidLabApproachBirthTrap('))
with tempfile.TemporaryDirectory(prefix='raid-birth-approach-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
