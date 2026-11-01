"""Actual Classic Swarm/Web rescue selection, with native cast refusal boundaries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <algorithm>
#include <vector>
#include <set>
#include <iostream>
constexpr unsigned CLASS_PALADIN=2;
struct Unit{unsigned guid=1,entry=15956,map=533,cls=2;float hp=100,distance=10;bool tank=false;
std::set<unsigned>auras;Unit*victim=nullptr;
unsigned GetMapId(){return map;}unsigned getClass(){return cls;}unsigned GetObjectGuid(){return guid;}
bool HasAura(unsigned id){return auras.count(id);}float GetDistance(Unit*){return distance;}
float GetHealthPercent(){return hp;}Unit*GetVictim(){return victim;}};
using Player=Unit;
struct PlayerbotAI{Player bot;bool ready=true,castable=true;std::set<unsigned>refused;
Player*GetBot(){return &bot;}bool IsTank(Player*p){return p->tank;}
bool CanCastSpell(const char*,Unit*u,unsigned){return castable&&!refused.count(u->guid);}};
Unit* boss=nullptr;unsigned observed=28785;float clearance=32;std::vector<Player*>members;
bool Ready(PlayerbotAI*a){return a->ready;}
Unit*FindBoss(PlayerbotAI*,unsigned id){assert(id==15956);return boss;}
unsigned CurrentBossEscapeSpell(Player*,Unit*){return observed;}
float BossEscapeDistance(Player*,Unit*,unsigned id){assert(id==28785);return clearance;}
std::vector<Player*>Members(PlayerbotAI*){return members;}
__HELPER__
int main(){PlayerbotAI ai;Unit encounter;boss=&encounter;Player tank,healer,other;
tank.guid=2;tank.tank=true;healer.guid=3;other.guid=4;healer.hp=20;other.hp=50;
for(auto p:{&tank,&healer,&other})p->auras.insert(28991);
members={&other,&healer,&tank};encounter.victim=&tank;
assert(AnubrekhanRootRelief(&ai)==&tank);
tank.auras.insert(1044);assert(AnubrekhanRootRelief(&ai)==&healer); // other paladin already rescued tank
healer.distance=35;assert(AnubrekhanRootRelief(&ai)==&other); // outside Swarm needs no urgent rescue
ai.refused.insert(4);assert(!AnubrekhanRootRelief(&ai));ai.refused.clear();
other.auras.clear();assert(!AnubrekhanRootRelief(&ai));other.auras.insert(28991);
observed=0;assert(!AnubrekhanRootRelief(&ai));observed=28785;
clearance=0;assert(!AnubrekhanRootRelief(&ai));clearance=32;
boss=nullptr;assert(!AnubrekhanRootRelief(&ai));boss=&encounter;
ai.castable=false;assert(!AnubrekhanRootRelief(&ai));ai.castable=true;
ai.ready=false;assert(!AnubrekhanRootRelief(&ai));ai.ready=true;
ai.bot.map=409;assert(!AnubrekhanRootRelief(&ai));ai.bot.map=533;
ai.bot.cls=5;assert(!AnubrekhanRootRelief(&ai));ai.bot.cls=2;
assert(AnubrekhanRootRelief(&ai)==&other);
std::cout<<"PASS native Swarm/Web relief priority, completed rescue, range, cast refusal and scope\n";
}
'''.replace('__HELPER__',block(source,'    Unit* AnubrekhanRootRelief('))
with tempfile.TemporaryDirectory(prefix='anub-root-')as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
