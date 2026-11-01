"""Exercise the local fixture's deferred native-grid admission, including clock wrap."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <string>
#include <vector>
using uint32=uint32_t;
struct WorldTimer {static uint32 now;static uint32 getMSTime(){return now;}};uint32 WorldTimer::now=100;
struct Map {std::vector<std::pair<float,float>> loads;void ForceLoadGrid(float x,float y){loads.emplace_back(x,y);}};
struct Player {Map map;uint32 id=509;Map*GetMap(){return &map;}uint32 GetMapId(){return id;}};
struct TestContext {int pc=7;std::map<std::string,uint32> raidLabGridWarmups;};
struct Log {template<class...T>void outString(const char*,T...) {}}sLog;
'''+block(source,'bool RaidLabWarmPreparationGrid(')+r'''
int main(){
 Player player;TestContext ctx;std::string reason;
 assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",-8824,1629,reason));
 assert(player.map.loads.size()==9&&!reason.empty());
 WorldTimer::now=2099;assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",-8824,1629,reason));
 assert(player.map.loads.size()==9);
 WorldTimer::now=2100;assert(RaidLabWarmPreparationGrid(&player,ctx,"landing",-8824,1629,reason));
 // A distinct stage cannot borrow readiness from an earlier map/location.
 assert(!RaidLabWarmPreparationGrid(&player,ctx,"pack",-8824,1629,reason));
 ++ctx.pc;assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",-8824,1629,reason));
 player.id=409;assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",-8824,1629,reason));
 assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",-8600,1629,reason));
 ctx.raidLabGridWarmups.clear();WorldTimer::now=UINT32_MAX-1000;
 assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",0,0,reason));
 WorldTimer::now=998;assert(!RaidLabWarmPreparationGrid(&player,ctx,"landing",0,0,reason));
 WorldTimer::now=999;assert(RaidLabWarmPreparationGrid(&player,ctx,"landing",0,0,reason));
}
'''
for name in ('CommandRaidLabLanding','CommandRaidLabStaging','CommandRaidLabPack'):
    body=block(source,'TestResult '+name+'::Execute(')
    assert 'RaidLabWarmPreparationGrid' in body
helper=block(source,'bool RaidLabWarmPreparationGrid(')
assert 'Spawn(' not in helper and 'Respawn(' not in helper and '->Update(' not in helper
assert 'raidLabGridWarmups.clear()' in (root/'playerbot/strategy/tests/TestContext.cpp').read_text()
with tempfile.TemporaryDirectory(prefix='raid-grid-warmup-') as directory:
    path=Path(directory);(path/'test.cpp').write_text(code)
    result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
    if result.returncode:print(result.stdout,result.stderr)
    result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
print('PASS native grid warmup: bounded load, deferred admission, stage/map/location isolation, clock wrap, reset')
