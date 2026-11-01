"""Execute the native encounter guard for a persistent aura that breaks Shadow Command CC."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <iostream>
struct Unit { bool world=true,alive=true,combat=true,barrier=true; unsigned entry=10162,instance=1;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 unsigned GetEntry(){return entry;}bool HasAura(unsigned id){assert(id==22663);return barrier;} };
struct InstanceData{virtual ~InstanceData()=default;};
struct ScriptedInstance:InstanceData{Unit*boss=nullptr;Unit*GetSingleCreatureFromStorage(unsigned id,bool quiet){assert(id==10162&&quiet);return boss;}};
struct Map{InstanceData*data=nullptr;InstanceData*GetInstanceData(){return data;}};
struct Player:Unit{unsigned mapId=469;Map map;unsigned GetMapId(){return mapId;}Map*GetMap(){return &map;}
 bool IsInMap(Unit*u){return instance==u->instance;}};
struct PlayerbotAI{Player bot;bool ready=true;Player*GetBot(){return &bot;}};
bool Ready(PlayerbotAI*ai){return ai->ready;}
__BODY__
int main(){PlayerbotAI ai;Unit boss;ScriptedInstance instance;instance.boss=&boss;ai.bot.map.data=&instance;
 assert(NefariusImmolationUnsafe(&ai));
 ai.ready=false;assert(!NefariusImmolationUnsafe(&ai));ai.ready=true;
 for(unsigned map:{0u,409u,489u,533u}){ai.bot.mapId=map;assert(!NefariusImmolationUnsafe(&ai));}ai.bot.mapId=469;
 ai.bot.map.data=nullptr;assert(!NefariusImmolationUnsafe(&ai));ai.bot.map.data=&instance;
 instance.boss=nullptr;assert(!NefariusImmolationUnsafe(&ai));instance.boss=&boss;
 boss.entry=11583;assert(!NefariusImmolationUnsafe(&ai));boss.entry=10162;
 boss.instance=2;assert(!NefariusImmolationUnsafe(&ai));boss.instance=1;
 boss.world=false;assert(!NefariusImmolationUnsafe(&ai));boss.world=true;
 boss.alive=false;assert(!NefariusImmolationUnsafe(&ai));boss.alive=true;
 boss.combat=false;assert(!NefariusImmolationUnsafe(&ai));boss.combat=true;
 boss.barrier=false;assert(!NefariusImmolationUnsafe(&ai));boss.barrier=true;
 assert(NefariusImmolationUnsafe(&ai));
 std::cout<<"PASS native phase-one immolation scope, inactive/phase-transition/instance/lifecycle guards\n";
}
'''.replace('__BODY__',block(source,'    bool NefariusImmolationUnsafe('))
with tempfile.TemporaryDirectory(prefix='nef-immolation-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
