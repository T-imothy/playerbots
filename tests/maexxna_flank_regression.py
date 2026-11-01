"""Actual Classic Maexxna rear-station search with native-admission refusals."""
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
struct Unit{unsigned map=533,entry=15952;float x=0,y=0,z=0,orientation=0;Unit*victim=nullptr;
 unsigned GetMapId(){return map;}unsigned GetEntry(){return entry;}Unit*GetVictim(){return victim;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return orientation;}};
using Player=Unit;
struct PlayerbotAI{Player bot;bool ranged=true,heal=false;Player*GetBot(){return &bot;}bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return heal;}};
struct EncounterPosition{encounter::Point destination;};
float groundLimit=100;bool nativePath=true;unsigned paths=0,grounds=0;
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&p,bool walking){assert(!walking);++grounds;return std::hypot(p.destination.x,p.destination.y)<=groundLimit;}
bool PositionLegal(PlayerbotAI*,Unit*,EncounterPosition&p,float maximum){++paths;assert(p.destination.x<=0.001f);return nativePath && std::hypot(p.destination.x,p.destination.y)<=maximum;}
__HELPER__
int main(){
 PlayerbotAI ai;Unit boss;EncounterPosition p;std::vector<encounter::Point> neighbors;
 assert(MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));assert(std::fabs(std::hypot(p.destination.x,p.destination.y)-38)<.01f);
 groundLimit=23;paths=0;assert(MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));
 assert(std::fabs(std::hypot(p.destination.x,p.destination.y)-22)<.01f&&paths==1); // outer wall never spends native walking checks
 groundLimit=15;assert(MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));assert(std::fabs(std::hypot(p.destination.x,p.destination.y)-14)<.01f);
 groundLimit=100;nativePath=false;paths=0;assert(!MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p)&&paths==12);
 nativePath=true;neighbors={{-38,0,0}};assert(MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));assert(encounter::Distance2d(p.destination,neighbors[0])>=5);
 ai.ranged=false;ai.heal=true;assert(MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));
 ai.heal=false;assert(!MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));ai.ranged=true;
 boss.victim=&ai.bot;assert(!MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));boss.victim=nullptr;
 boss.entry=15956;assert(!MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));boss.entry=15952;
 ai.bot.map=409;assert(!MaexxnaRangedFlank(&ai,&boss,&boss,38,neighbors,p));ai.bot.map=533;
 assert(!MaexxnaRangedFlank(&ai,&boss,&boss,NAN,neighbors,p));assert(!MaexxnaRangedFlank(&ai,&boss,&boss,8,neighbors,p));
 std::cout<<"PASS Maexxna max-range preference, grounded nearer rear fallback, spacing, bounded path refusal and role/map scope\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__HELPER__',block(source,'    bool MaexxnaRangedFlank('))
with tempfile.TemporaryDirectory(prefix='maexxna-flank-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(p/'test.exe')],cwd=p,check=True)
