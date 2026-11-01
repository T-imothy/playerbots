"""Explicit local Madness boss-only staging, preserving native activation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <map>
#include <string>
#include <vector>
#include <iostream>
using uint32=unsigned;
enum class TestResult{PASS,PENDING,IMPOSSIBLE};
struct Guid{std::string GetString(){return "test";}};
struct Creature{unsigned entry;float distance=10;bool world=true,alive=true,combat=false;unsigned removed=0,delay=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 unsigned GetEntry(){return entry;}Guid GetObjectGuid(){return {};}
 void SetRespawnDelay(unsigned n,bool){delay=n;}void ForcedDespawn(){++removed;}};
struct Store{std::map<unsigned,Creature*> creatures;template<class T>auto begin(){return creatures.begin();}template<class T>auto end(){return creatures.end();}};
struct Map{Store store;Store&GetObjectsStore(){return store;}};
struct Player{bool world=true,transfer=false,gm=true,combat=false;unsigned id=309;Map map;
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool IsGameMaster(){return gm;}bool IsInCombat(){return combat;}
 unsigned GetMapId(){return id;}Map*GetMap(){return &map;}float GetPositionX(){return 0;}float GetPositionY(){return 0;}};
struct TestContext{std::string testName="raidlab_309_15082_leader_event_prepared";};
struct GameObject{bool world=true,spawned=true;bool IsInWorld(){return world;}bool IsSpawned(){return spawned;}float GetDistance(Creature*c){return c->distance;}} brazier;
bool found=true,warm=true;
namespace MaNGOS{
 struct NearestGameObjectEntryInObjectRangeCheck{NearestGameObjectEntryInObjectRangeCheck(Player&,unsigned id,float range){assert(id==180327&&range==5);}};
 template<class T>struct GameObjectLastSearcher{GameObject*&out;GameObjectLastSearcher(GameObject*&o,T&):out(o){}};
}
namespace Cell{template<class T>void VisitGridObjects(Player*,T&s,float range){assert(range==5);s.out=found?&brazier:nullptr;}}
namespace RaidLab{bool enabled=true;bool Enabled(){return enabled;}}
bool RaidLabWarmPreparationGrid(Player*,TestContext&,const char*,float,float,std::string&){return warm;}
struct Logger{template<class...T>void outString(const char*,T...){}}sLog;
__POLICY__
__STAGE__
int main(){
 Player p;TestContext ctx;std::string message;
 Creature servant{15111},voidwalker{15146},priest{11340},other{11371},far{15111,65},boss{15082};
 p.map.store.creatures={{1,&servant},{2,&voidwalker},{3,&priest},{4,&other},{5,&far}};
 auto run=[&](){return RaidLabStageMadnessRoom(&p,ctx,15082,message);};
 auto untouched=[&](){assert(!servant.removed&&!voidwalker.removed&&!priest.removed&&!other.removed&&!far.removed);};
 RaidLab::enabled=false;assert(run()==TestResult::IMPOSSIBLE);RaidLab::enabled=true;
 p.gm=false;assert(run()==TestResult::IMPOSSIBLE);p.gm=true;
 p.transfer=true;assert(run()==TestResult::IMPOSSIBLE);p.transfer=false;
 p.combat=true;assert(run()==TestResult::IMPOSSIBLE);p.combat=false;
 p.id=409;assert(run()==TestResult::IMPOSSIBLE);p.id=309;
 ctx.testName="raidlab_309_15082_leader_event";assert(run()==TestResult::IMPOSSIBLE);ctx.testName+="_prepared";
 warm=false;assert(run()==TestResult::PENDING);warm=true;
 found=false;assert(run()==TestResult::IMPOSSIBLE);found=true;
 brazier.spawned=false;assert(run()==TestResult::IMPOSSIBLE);brazier.spawned=true;
 priest.combat=true;assert(run()==TestResult::IMPOSSIBLE);priest.combat=false;
 p.map.store.creatures[6]=&boss;assert(run()==TestResult::IMPOSSIBLE);p.map.store.creatures.erase(6);
 for(unsigned i=10;i<60;++i)p.map.store.creatures[i]=&servant;
 assert(run()==TestResult::IMPOSSIBLE);for(unsigned i=10;i<60;++i)p.map.store.creatures.erase(i);
 untouched();assert(run()==TestResult::PASS);
 assert(servant.removed==1&&voidwalker.removed==1&&priest.removed==1&&servant.delay==3600);
 assert(!other.removed&&!far.removed&&!boss.removed);
 assert(!RaidLabMadnessRoomActor(15111,NAN)&&!RaidLabMadnessRoomActor(15111,-1));
 for(unsigned entry:{15082u,15083u,15084u,15085u,11380u})assert(!RaidLabMadnessRoomActor(entry,0));
 std::cout<<"PASS explicit local Madness room, exact trash/distance, zero-mutation refusals and native boss/brazier preservation\n";
}
'''.replace('__POLICY__',block(source,'bool RaidLabMadnessRoomActor(')).replace('__STAGE__',block(source,'TestResult RaidLabStageMadnessRoom('))
with tempfile.TemporaryDirectory(prefix='raid-madness-room-') as directory:
    p=Path(directory);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
