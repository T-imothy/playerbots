"""Execute the lab's actual native binding and post-kill lifecycle methods.

These are telemetry/fixture tests, not encounter acceptance.
"""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
core=root.parent/'classic/src/game/World/RaidLab.cpp'
command=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <mutex>
#include <string>
#include <iostream>
using uint64=uint64_t;using uint32=uint32_t;
struct Guid {uint64 value=0;uint64 GetRawValue()const{return value;}explicit operator bool()const{return value!=0;}};
struct Map {};
struct Unit {bool world=true,alive=true;uint32 entry=15989;Guid guid{10};Map* map=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}uint32 GetEntry(){return entry;}
 Guid GetObjectGuid(){return guid;}Map* GetMap(){return map;}};
struct Player:Unit {};
struct TestContext {Guid focusMobGuid{10};uint32 raidLabPostKillStarted=0;};
struct WorldTimer {static uint32 now;static uint32 getMSTime(){return now;}};uint32 WorldTimer::now=100;
namespace RaidLab {
struct Attempt {uint64 target=0,bossEvadeAt=0,bossResetAt=0;uint32 boss=15989;bool bossDied=false;} attempt;
uint64 now=100;uint64 Clock(){return now;}
Map nativeMap,wrongMap;bool enabled=true;int writes=0,events=0;std::recursive_mutex guard;
bool Enabled(){return enabled;}Attempt* Find(Map*m){return m==&nativeMap?&attempt:nullptr;}
void Write(Attempt&,std::string const&){++writes;}
void Event(Unit*,char const*,uint64=0,uint64=0){++events;}
'''
code+=block(core.read_text(),'bool BindNativeBoss(')+'\n'
code+=block(core.read_text(),'bool BossDied(')+'\n'
code+=block(core.read_text(),'void ObserveBossReset(')+'\n'
code+=block(core.read_text(),'bool BossResetObserved(')+'\n}\n'
code+='struct MonitorRaidLabDeath {bool IsConditionMet(const std::string&,Player*,TestContext&)const;};\n'
code+=block(command,'bool MonitorRaidLabDeath::IsConditionMet(')
code+=r'''
int main(){
 using namespace RaidLab;Unit boss;boss.map=&nativeMap;
 enabled=false;assert(!BindNativeBoss(&boss));enabled=true;
 assert(!BindNativeBoss(nullptr));boss.world=false;assert(!BindNativeBoss(&boss));boss.world=true;
 boss.alive=false;assert(!BindNativeBoss(&boss));boss.alive=true;
 boss.map=&wrongMap;assert(!BindNativeBoss(&boss));boss.map=&nativeMap;
 boss.entry=123;assert(!BindNativeBoss(&boss));boss.entry=15989;
 assert(writes==0&&attempt.target==0);
 assert(BindNativeBoss(&boss));assert(attempt.target==10&&writes==1);
 assert(!BindNativeBoss(&boss));boss.guid.value=11;assert(!BindNativeBoss(&boss));
 assert(attempt.target==10&&writes==1); // retry/other spawn never replaces bound native identity
 Player leader;leader.map=&nativeMap;TestContext ctx;MonitorRaidLabDeath monitor;
 assert(!monitor.IsConditionMet("",&leader,ctx));assert(ctx.raidLabPostKillStarted==0&&events==0);
 attempt.bossDied=true;ctx.focusMobGuid.value=11;
 assert(!monitor.IsConditionMet("",&leader,ctx));ctx.focusMobGuid.value=10;
 assert(!monitor.IsConditionMet("",&leader,ctx));assert(ctx.raidLabPostKillStarted==100&&events==1);
 WorldTimer::now=30099;assert(!monitor.IsConditionMet("",&leader,ctx));
 WorldTimer::now=30100;assert(monitor.IsConditionMet("",&leader,ctx));assert(events==1);
 leader.map=&wrongMap;assert(!monitor.IsConditionMet("",&leader,ctx));
 attempt.bossDied=false;now=100;
 ObserveBossReset(attempt,10,"script:Reset",0,0,now);assert(!attempt.bossResetAt); // phase/reset alone is not an evade
 ObserveBossReset(attempt,11,"evade_state",2,0,now);assert(!attempt.bossEvadeAt); // unrelated actor
 ObserveBossReset(attempt,10,"evade_state",2,0,now);
 ObserveBossReset(attempt,10,"script:Reset",0,0,1200);assert(!attempt.bossResetAt); // stale transition
 ObserveBossReset(attempt,10,"evade_state",2,0,2000);
 ObserveBossReset(attempt,10,"script:Reset",0,0,2001);assert(attempt.bossResetAt==2001);
 now=32000;assert(!BossResetObserved(&nativeMap,10));now=32001;assert(BossResetObserved(&nativeMap,10));
 assert(!BossResetObserved(&wrongMap,10)&&!BossResetObserved(&nativeMap,11));
 attempt.bossDied=true;assert(!BossResetObserved(&nativeMap,10));
 std::cout<<"PASS native identity binding, duplicate rejection and 30-second post-kill/reset observations\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raidlab-lifecycle-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode()
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
