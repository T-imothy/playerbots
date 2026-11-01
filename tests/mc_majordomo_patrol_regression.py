"""Majordomo-only formation delegates native route/patrol protection, not global AI."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingMovementSafety.cpp').read_text()
code=r'''
#include <cassert>
#include <vector>
#include <initializer_list>
#include <iostream>
struct WorldPosition{};
struct Unit{unsigned entry=12018,map=409,instance=1;bool world=true,alive=true,charm=false,engaged=true;
unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charm;}};
struct Player:Unit{bool group=true,teleport=false;unsigned GetMapId(){return map;}bool GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}
bool IsInMap(Unit*u){assert(world&&u->world);return map==u->map&&instance==u->instance;}};
struct PlayerbotAI{Player*bot;bool real=false;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}};
bool safe=false;unsigned checks=0;bool RoomEnemyEngaged(PlayerbotAI*,Unit*u){return u->engaged;}
namespace ai{bool MajordomoFormationRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&,Unit*);
bool RaidUnpulledPackRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&){++checks;return safe;}}
__METHOD__
int main(){Player bot;Unit boss;PlayerbotAI brain{&bot};std::vector<WorldPosition>path(2);
auto allowed=[&](){return ai::MajordomoFormationRouteSafe(&brain,path,&boss);};
#ifdef MANGOSBOT_ZERO
assert(!allowed()&&checks==1);safe=true;assert(allowed()&&checks==2);safe=false;
for(unsigned entry:{11982u,12056u,11988u,11664u}){boss.entry=entry;assert(allowed()&&checks==2);}boss.entry=12018;
for(bool*flag:{&bot.world,&bot.alive,&bot.group,&boss.world,&boss.alive,&boss.engaged}){*flag=false;assert(allowed()&&checks==2);*flag=true;}
for(bool*flag:{&bot.teleport,&bot.charm,&brain.real,&boss.charm}){*flag=true;assert(allowed()&&checks==2);*flag=false;}
boss.instance=2;assert(allowed()&&checks==2);boss.instance=1;bot.map=0;assert(allowed()&&checks==2);bot.map=409;
assert(ai::MajordomoFormationRouteSafe(&brain,path,nullptr)&&checks==2);assert(!allowed()&&checks==3);
#else
assert(allowed()&&checks==0);
#endif
std::cout<<"PASS: only engaged Classic Majordomo formation consumes native unpulled-patrol route admission\n";
}
'''.replace('__METHOD__',block(source,'bool ai::MajordomoFormationRouteSafe('))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-domo-patrol-')as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
