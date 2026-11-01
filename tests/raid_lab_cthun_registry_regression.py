"""Actual native registry fallback with bounded identity/range/lifecycle gates."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
start=s.index(' if(bot->GetMapId()==531 && entry==15727 && kind=="phase" && activator==15589)')
end=s.index(' if(ctx.raidLabEventStarted)',start)
body=s[start:end]
code=r'''
#include <cassert>
#include <string>
#include <iostream>
using uint32=unsigned;
struct Creature{unsigned entry=15727;bool world=true,alive=true,same=true;float distance=110;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}};
struct InstanceData{virtual ~InstanceData()=default;};
struct ScriptedInstance:InstanceData{Creature body,eye;ScriptedInstance(){eye.entry=15589;}
 Creature* GetSingleCreatureFromStorage(unsigned id,bool){return id==15727?&body:id==15589?&eye:nullptr;}};
struct Map{InstanceData* instance=nullptr;InstanceData* GetInstanceData(){return instance;}};
struct Player{Map map;unsigned id=531;unsigned GetMapId(){return id;}Map* GetMap(){return &map;}
 bool IsInMap(Creature*c){return c->same;}float GetDistance(Creature*c){return c->distance;}};
void resolve(Player* bot,unsigned entry,const std::string& kind,unsigned activator,Creature*& boss,Creature*& pullTarget){
'''+body+r'''
}
int main(){
 Player player;ScriptedInstance instance;player.map.instance=&instance;Creature* boss=nullptr,*pull=nullptr;
 auto run=[&](unsigned entry=15727,const std::string& kind="phase",unsigned activator=15589){
  boss=pull=nullptr;resolve(&player,entry,kind,activator,boss,pull);
 };
 run();assert(boss==&instance.body&&pull==&instance.eye); // valid 110-yard corridor
 instance.body.distance=150;run();assert(boss);instance.body.distance=150.01f;run();assert(!boss&&pull);
 instance.body.distance=110;
 for(bool* state:{&instance.body.alive,&instance.body.world,&instance.body.same}){
  *state=false;run();assert(!boss&&pull);*state=true;
 }
 instance.eye.entry=1;run();assert(boss&&!pull);instance.eye.entry=15589;
 player.id=469;run();assert(!boss&&!pull);player.id=531;
 run(15928);assert(!boss&&!pull);run(15727,"gossip");assert(!boss&&!pull);
 run(15727,"phase",15930);assert(!boss&&!pull);
 player.map.instance=nullptr;run();assert(!boss&&!pull);player.map.instance=&instance;
 Creature existing;boss=pull=&existing;resolve(&player,15727,"phase",15589,boss,pull);assert(boss==&existing&&pull==&existing);
 std::cout<<"PASS Cthun native registry identity, bounded corridor, same map, world/alive and phase-only gates\n";
}
'''
event=block(s,'TestResult CommandRaidLabEvent::Execute(')
assert 'phase trial requires untouched native encounter actors' in event
assert '!=NOT_STARTED' in event
assert 'tank->GetPlayerbotAI()->HandleCommand(CHAT_MSG_WHISPER,"pull",*bot)' in event
with tempfile.TemporaryDirectory(prefix='cthun-registry-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
