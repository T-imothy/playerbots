"""Execute actual Classic tank station planner: hold, cloud escape, hold again."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <list>
#include <iostream>
#include "__GEOMETRY__"
using namespace ai;
struct Unit{unsigned map=533,entry=15931;float x=0,y=0,z=0;bool ranged=false,healer=false,melee=true;Unit*victim=nullptr;
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return 1;}unsigned GetEntry(){return entry;}
 unsigned GetObjectGuid(){return entry;}Unit*GetVictim(){return victim;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(Unit* other){return std::hypot(x-other->x,y-other->y);}
 float GetCombatReach(){return 2;}bool CanReachWithMeleeAttack(Unit*){return melee;}};
using Player=Unit;
struct WorldPosition{float x,y,z;float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
struct PlayerbotAI{Player bot;Player*GetBot(){return &bot;}bool IsRanged(Player*p){return p->ranged;}bool IsHeal(Player*p){return p->healer;}};
std::vector<Player*> members;
std::vector<Player*> Members(PlayerbotAI*){return members;}
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,boss=0,spell=0;encounter::Point destination;};
std::list<HazardPosition>clouds;
void AppendGrobbulusCloudHazards(PlayerbotAI*,std::list<HazardPosition>&out){out=clouds;}
bool legal=true;unsigned checks=0;
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&){++checks;return legal;}
__HELPER__
int main(){
 PlayerbotAI ai;Unit boss;boss.victim=&ai.bot;EncounterPosition p;
 assert(GrobbulusTankStation(&ai,&boss,p));
 assert(p.active&&p.spell==28137&&p.destination.x==0&&p.destination.y==0); // no continuous circle in a safe room
 clouds.push_back({{30,0,0},10});assert(GrobbulusTankStation(&ai,&boss,p)&&p.destination.x==0); // distant cloud doesn't move tank
 clouds={{ {0,0,0},1.3f }};assert(GrobbulusTankStation(&ai,&boss,p));
 assert(std::hypot(p.destination.x,p.destination.y)>3.3f); // actual cloud needs bounded escape
 ai.bot.x=p.destination.x;ai.bot.y=p.destination.y;
 assert(GrobbulusTankStation(&ai,&boss,p));
 assert(p.destination.x==ai.bot.x&&p.destination.y==ai.bot.y); // stop after clearing cloud, let boss catch up
 clouds.front().second=10.3f;assert(GrobbulusTankStation(&ai,&boss,p));
 assert(std::hypot(p.destination.x,p.destination.y)>12.3f); // native growth requires another step
 legal=false;checks=0;assert(!GrobbulusTankStation(&ai,&boss,p)&&!p.active&&checks<=12); // no invalid-path movement
 legal=true;clouds.clear();assert(GrobbulusTankStation(&ai,&boss,p));
 ai.bot.x=2;ai.bot.y=0;Player healer;healer.x=25;healer.healer=true;members={&ai.bot,&healer};
 assert(GrobbulusTankStation(&ai,&boss,p)&&p.destination.x<0); // turn away from the exposed healing group
 ai.bot.x=p.destination.x;ai.bot.y=p.destination.y;
 assert(GrobbulusTankStation(&ai,&boss,p)&&p.destination.x==ai.bot.x&&p.destination.y==ai.bot.y); // stable safe facing
 ai.bot.x=2;ai.bot.y=0;ai.bot.melee=false;
 assert(GrobbulusTankStation(&ai,&boss,p)&&p.destination.x==2); // don't kite before contact
 ai.bot.melee=true;legal=false;
 assert(!GrobbulusTankStation(&ai,&boss,p)); // blocked relocation never accepted
 legal=true;healer.x=60;
 assert(GrobbulusTankStation(&ai,&boss,p)&&p.destination.x==2); // distant/unrelated members do not turn the boss
 members.clear();
 boss.victim=nullptr;assert(!GrobbulusTankStation(&ai,&boss,p));boss.victim=&ai.bot;
 boss.entry=15932;assert(!GrobbulusTankStation(&ai,&boss,p));boss.entry=15931;
 ai.bot.map=409;assert(!GrobbulusTankStation(&ai,&boss,p));
 std::cout<<"PASS actual Grobbulus hold/escape/growth/hold, route refusal and encounter scope\n";
}
'''
code=code.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
code=code.replace('__HELPER__',block(source,'    bool GrobbulusTankStation('))
with tempfile.TemporaryDirectory(prefix='grobbulus-station-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
