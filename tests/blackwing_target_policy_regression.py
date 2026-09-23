"""Compile actual BWL phase admission and add-priority functions with fixtures.
This requires a compiler; the source-only audit does not run this script.
"""
from pathlib import Path
import tempfile
import subprocess
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
methods=block(source,'unsigned BwlAddPriority(')+'\n'+block(source,'bool ai::IsProtectedBlackwingTarget(')
code=r'''
#include <cassert>
#include <set>
#include <iostream>
using uint32=unsigned;
constexpr unsigned SPECIAL=4;
struct InstanceData{unsigned state=1;unsigned GetData(unsigned key){assert(key==0);return state;}};
struct Map{InstanceData* data=nullptr;InstanceData* GetInstanceData(){return data;}};
struct PlayerbotAI{bool real=false;bool IsRealPlayer(){return real;}};
struct Unit{bool world=true;unsigned entry=0;Map* map=nullptr;std::set<unsigned> auras;
 bool IsInWorld(){return world;}unsigned GetEntry(){return entry;}bool HasAura(unsigned id){return auras.count(id);}};
struct Player:Unit{bool alive=true;unsigned mapId=469;PlayerbotAI* ai=nullptr;
 bool IsAlive(){return alive;}unsigned GetMapId(){return mapId;}Map* GetMap(){return map;}
 bool IsInMap(Unit* unit){return unit&&map==unit->map;}PlayerbotAI* GetPlayerbotAI(){return ai;}};
namespace ai{bool IsProtectedBlackwingTarget(Player*,Unit*);}
using namespace ai;
__METHODS__
int main(){
 InstanceData instance;Map map{&instance},other;PlayerbotAI ai;Player bot;bot.map=&map;bot.ai=&ai;
 Unit boss;boss.map=&map;boss.entry=12435;
 assert(IsProtectedBlackwingTarget(&bot,&boss));
 instance.state=SPECIAL;assert(!IsProtectedBlackwingTarget(&bot,&boss));
 instance.state=0;assert(IsProtectedBlackwingTarget(&bot,&boss));
 ai.real=true;assert(!IsProtectedBlackwingTarget(&bot,&boss));ai.real=false;
 bot.mapId=409;assert(!IsProtectedBlackwingTarget(&bot,&boss));bot.mapId=469;
 boss.map=&other;assert(!IsProtectedBlackwingTarget(&bot,&boss));boss.map=&map;
 boss.world=false;assert(!IsProtectedBlackwingTarget(&bot,&boss));boss.world=true;
 map.data=nullptr;assert(!IsProtectedBlackwingTarget(&bot,&boss));map.data=&instance;
 assert(!IsProtectedBlackwingTarget(nullptr,&boss)&&!IsProtectedBlackwingTarget(&bot,nullptr));
 boss.entry=10162;assert(!IsProtectedBlackwingTarget(&bot,&boss));boss.auras.insert(22663);
 assert(IsProtectedBlackwingTarget(&bot,&boss));boss.entry=11583;assert(!IsProtectedBlackwingTarget(&bot,&boss));
 assert(BwlAddPriority(12420)>BwlAddPriority(12416));
 assert(BwlAddPriority(14605)>BwlAddPriority(14261));
 assert(!BwlAddPriority(12435)&&!BwlAddPriority(11583)&&!BwlAddPriority(1));
 std::cout<<"PASS BWL native-phase target admission and add priority policy\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-bwl-target-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
