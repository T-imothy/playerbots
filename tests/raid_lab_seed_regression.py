"""Execute explicit local MC seed admission and native surrender monitoring."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <string>
#include <map>
#include <iostream>
using uint32=unsigned;enum class TestResult{PASS,IMPOSSIBLE};enum{NOT_STARTED,IN_PROGRESS,FAIL,DONE};
struct Creature{unsigned entry;bool alive=true,world=true;bool IsAlive(){return alive;}bool IsInWorld(){return world;}unsigned GetEntry(){return entry;}};
struct Store{std::map<unsigned,Creature*> creatures;template<class T>auto begin(){return creatures.begin();}template<class T>auto end(){return creatures.end();}};
struct ChatHandler{ChatHandler(void*){}};
struct InstanceData{unsigned state[10]={},calls=0;bool creates=true;Store store;Creature domo{12018},healer{11663},elite{11664};
 unsigned GetData(unsigned i){assert(i<10);return state[i];}
 void ExecuteChatCommand(ChatHandler*,char*args){++calls;std::string s=args;assert(s=="spawnmajordomo 0"||s=="spawnmajordomo 1");if(!creates)return;
 store.creatures[0]=&domo;if(s.back()=='0')for(unsigned i=0;i<4;++i){store.creatures[1+i]=&healer;store.creatures[5+i]=&elite;}}
};
struct Map{InstanceData instance;bool available=true;InstanceData*GetInstanceData(){return available?&instance:nullptr;}Store&GetObjectsStore(){return instance.store;}};
struct Player{bool world=true,gm=true,tp=false,combat=false;unsigned id=409;Map map;
 bool IsInWorld(){return world;}bool IsGameMaster(){return gm;}bool IsBeingTeleported(){return tp;}bool IsInCombat(){return combat;}
 unsigned GetMapId(){return id;}Map*GetMap(){return &map;}void*GetSession(){return nullptr;}
};struct PlayerbotAI{};
struct TestContext{std::string testName="raidlab_409_12018_leader_seeded";unsigned focusMobEntry=12018,focusMobGuid=1,raidLabPostKillStarted=0;};
struct WorldTimer{static unsigned now;static unsigned getMSTime(){return now;}};unsigned WorldTimer::now=100;
namespace RaidLab{bool enabled=true;unsigned events=0;bool Enabled(){return enabled;}void Event(Player*,const char*,unsigned){++events;}}
struct Logger{template<class...T>void outString(const char*,T...){}}sLog;
struct CommandRaidLabSeed{TestResult Execute(const std::string&,Player*,PlayerbotAI*,TestContext&,std::string&);};
struct MonitorRaidLabCompletion{bool IsConditionMet(const std::string&,Player*,TestContext&)const;};
'''
code+=block(source,'TestResult CommandRaidLabSeed::Execute(')
code+=block(source,'bool MonitorRaidLabCompletion::IsConditionMet(')
code+=r'''
int main(){Player p;TestContext ctx;std::string message;CommandRaidLabSeed seed;MonitorRaidLabCompletion monitor;
 auto run=[&](){return seed.Execute("majordomo",&p,nullptr,ctx,message);};
 RaidLab::enabled=false;assert(run()==TestResult::IMPOSSIBLE);RaidLab::enabled=true;
 p.gm=false;assert(run()==TestResult::IMPOSSIBLE);p.gm=true;p.tp=true;assert(run()==TestResult::IMPOSSIBLE);p.tp=false;
 p.id=469;assert(run()==TestResult::IMPOSSIBLE);p.id=409;
 ctx.testName="raidlab_409_12018_leader";assert(run()==TestResult::IMPOSSIBLE);ctx.testName+="_seeded";
 p.map.instance.state[0]=DONE;assert(run()==TestResult::IMPOSSIBLE);p.map.instance.state[0]=NOT_STARTED;
 assert(p.map.instance.calls==0&&run()==TestResult::PASS&&p.map.instance.calls==1&&p.map.instance.store.creatures.size()==9);
 assert(run()==TestResult::IMPOSSIBLE&&p.map.instance.calls==1);
 assert(!monitor.IsConditionMet("",&p,ctx));p.map.instance.state[8]=DONE;
 assert(!monitor.IsConditionMet("",&p,ctx)&&ctx.raidLabPostKillStarted==100&&RaidLab::events==1);
 WorldTimer::now=30099;assert(!monitor.IsConditionMet("",&p,ctx));WorldTimer::now=30100;assert(monitor.IsConditionMet("",&p,ctx));
 ctx.focusMobEntry=11502;assert(!monitor.IsConditionMet("",&p,ctx));ctx.focusMobEntry=12018;
 p.map.instance.state[8]=FAIL;assert(!monitor.IsConditionMet("",&p,ctx));
 Player summon;ctx.testName="raidlab_409_11502_leader_seeded_event";
 assert(seed.Execute("ragnaros",&summon,nullptr,ctx,message)==TestResult::PASS&&summon.map.instance.store.creatures.size()==1);
 Player broken;broken.map.instance.creates=false;assert(seed.Execute("ragnaros",&broken,nullptr,ctx,message)==TestResult::IMPOSSIBLE);
 std::cout<<"PASS explicit seed scope, untouched-instance requirement, duplicate refusal, native actors and surrender timing\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raidlab-seed-') as directory:
 path=Path(directory);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
