"""Execute native replacement-crystal selection, including the last candidate."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <algorithm>
#include <cassert>
#include <map>
#include <random>
#include <vector>
#include <iostream>
using uint32=unsigned;using GuidVector=std::vector<unsigned>;
enum{NPC_OSSIRIAN_TRIGGER=15590};
struct Creature;
struct Map{std::map<unsigned,Creature*>units;Creature*GetCreature(unsigned id){return units.count(id)?units[id]:nullptr;}};
struct Creature{Map*map=nullptr;bool alive=false;unsigned respawns=0;Map*GetMap(){return map;}bool IsAlive(){return alive;}void Respawn(){alive=true;++respawns;}};
struct Instance{GuidVector guids;void GetCreatureGuidVectorFromStorage(unsigned id,GuidVector&out){assert(id==NPC_OSSIRIAN_TRIGGER);out=guids;}};
std::mt19937 randomEngine(73);std::mt19937*GetRandomGenerator(){return &randomEngine;}
struct boss_ossirianAI{Creature*m_creature;Instance*m_instance;
 __METHODS__
};
int main(){Map map;Creature boss{&map},first{&map},one{&map},two{&map};map.units={{1,&first},{2,&one},{3,&two}};
 Instance instance;boss_ossirianAI ai{&boss,&instance};
 instance.guids={1,2};ai.DoSpawnNextCrystal(1);assert(one.respawns==1&&first.respawns==0); // One remaining candidate used to be skipped.
 one.alive=false;ai.DoSpawnNextCrystal(0);assert(one.respawns==1&&!one.alive);
 instance.guids={1,2,3};ai.DoSpawnNextCrystal(2);assert(one.respawns==2&&two.respawns==1&&first.respawns==0);
 ai.DoSpawnNextCrystal(2);assert(one.respawns==2&&two.respawns==1); // Alive crystals untouched.
 instance.guids={1,99,3};two.alive=false;ai.DoSpawnNextCrystal(2);assert(two.respawns==2); // Stale GUID doesn't hide the final valid one.
 instance.guids={};ai.DoSpawnNextCrystal(1);ai.RespawnFirstCrystal();
 instance.guids={1};ai.DoSpawnNextCrystal(1);assert(first.respawns==0);
 instance.guids={1,2};ai.RespawnFirstCrystal();assert(first.respawns==1);ai.RespawnFirstCrystal();assert(first.respawns==1);
 ai.m_instance=nullptr;ai.DoSpawnNextCrystal(1);ai.RespawnFirstCrystal();
 std::cout<<"PASS: native Ossirian single/final candidate, quota, live/stale GUIDs and missing instance\n";
}
'''
for era in ('classic','tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/ruins_of_ahnqiraj/boss_ossirian.cpp').read_text()
    methods='\n'.join(block(source,name) for name in ('void DoSpawnNextCrystal(', 'void RespawnFirstCrystal()'))
    code=fixture.replace('__METHODS__',methods)
    with tempfile.TemporaryDirectory(prefix='mantech-ossirian-crystals-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
