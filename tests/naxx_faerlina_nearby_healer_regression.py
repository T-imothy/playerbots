"""Actual Faerlina local spacing search; mocked terrain admission is not a native raid pass."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <vector>
#include <iostream>
#include "__GEOMETRY__"
using namespace ai;
constexpr float M_PI_F=3.14159265358979323846f;
namespace classicraid{bool Dragon(unsigned entry){return entry==15989;}}
struct Unit{unsigned map=533,entry=15953;float x=0,y=0,z=0,orientation=0;
 unsigned GetMapId(){return map;}unsigned GetEntry(){return entry;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return orientation;}
 float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}
 float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}};
using Player=Unit;
struct PlayerbotAI{Player bot;bool heal=true;Player*GetBot(){return &bot;}bool IsHeal(Player*){return heal;}};
struct EncounterPosition{encounter::Point destination;};
bool floorOk=true,pathOk=true,losOk=true,hazardOk=true;unsigned paths=0;
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&,bool walking){assert(!walking);return floorOk&&hazardOk;}
bool PositionLegal(PlayerbotAI*,Unit* anchor,EncounterPosition&p,float maximum){++paths;return pathOk&&losOk&&hazardOk&&anchor->GetDistance(p.destination.x,p.destination.y,p.destination.z)<=maximum;}
__HELPER__
int main(){
 PlayerbotAI ai;ai.bot.x=15;Unit boss;EncounterPosition p;std::vector<encounter::Point> neighbors{{15,0,0}};
 auto find=[&](bool front=false){paths=0;return FaerlinaNearbyHealerStation(&ai,&boss,&boss,&boss,38,front,neighbors,p);};
 assert(find());assert(encounter::Distance2d(p.destination,{15,0,0})>=5&&encounter::Distance2d(p.destination,{15,0,0})<6.01);
 assert(std::hypot(p.destination.x,p.destination.y)<22); // no walk to the outer 38-yard ring
 for(bool* admission:{&floorOk,&pathOk,&losOk,&hazardOk}){*admission=false;assert(!find());assert(paths<=8);*admission=true;}
 pathOk=false;assert(!find()&&paths==8);pathOk=true;
 // Native frontal exclusion is retained even when a close point exists.
 assert(!find(true));ai.bot.x=-15;neighbors={{-15,0,0}};assert(find(true)&&p.destination.x<=0);
 ai.bot.x=39;neighbors={{39,0,0}};assert(find());assert(boss.GetDistance(p.destination.x,p.destination.y,p.destination.z)<=40);
 ai.heal=false;assert(!find());ai.heal=true;ai.bot.map=409;assert(!find());ai.bot.map=533;
 boss.entry=15989;assert(!find());boss.entry=15953;
 assert(!FaerlinaNearbyHealerStation(&ai,nullptr,&boss,&boss,38,false,neighbors,p));
 assert(!FaerlinaNearbyHealerStation(&ai,&boss,nullptr,&boss,38,false,neighbors,p));
 assert(!FaerlinaNearbyHealerStation(&ai,&boss,&boss,nullptr,38,false,neighbors,p));
 assert(!FaerlinaNearbyHealerStation(&ai,&boss,&boss,&boss,NAN,false,neighbors,p));
 assert(!FaerlinaNearbyHealerStation(&ai,&boss,&boss,&boss,0,false,neighbors,p));
 std::cout<<"PASS nearby Faerlina healer spacing, range/front/floor/path/LOS/hazard refusals, bounded paths, role/map/encounter guards\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__HELPER__',block(source,'    bool FaerlinaNearbyHealerStation('))
with tempfile.TemporaryDirectory(prefix='faerlina-nearby-healer-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(p/'test.exe')],cwd=p,check=True)
