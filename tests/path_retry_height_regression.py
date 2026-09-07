"""Actual failure-key and recording statements distinguish stacked floors."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
state=block((root/'playerbot/strategy/values/LastMovementValue.h').read_text(),'class LastMovement')+';'
method=block((root/'playerbot/strategy/actions/MovementActions.cpp').read_text(),'bool MovementAction::MoveTo2(')
key=method[method.index('int32 const destinationCellX'):method.index('    if (sameFailedRequest')]
record=method[method.index('lastMove.failedPathMap = endPos'):method.index('        ai->StopMoving();',method.index('lastMove.failedPathMap = endPos'))]
code=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <vector>
using uint32=uint32_t;using int32=int32_t;using ObjectGuid=unsigned;
struct WorldPosition {unsigned map=1;float x=20,y=20,z=0;
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
struct Unit{};struct Event{};struct TravelPath{void clear(){}};
struct Player {unsigned instance=1;unsigned GetInstanceId(){return instance;}};
struct AI {unsigned generation=1;unsigned GetTransitionGeneration(){return generation;}};
struct WorldTimer {static unsigned getMSTime(){return 100;}};
struct Config{unsigned pathFailureRetryMs=3000;}sPlayerbotAIConfig;
__STATE__
bool same(LastMovement& lastMove,const WorldPosition& endPos,Player* bot,AI* ai){__KEY__ return sameFailedRequest;}
void remember(LastMovement& lastMove,const WorldPosition& endPos,Player* bot,AI* ai){__KEY__ __RECORD__}
int main(){Player bot;AI ai;WorldPosition target;LastMovement last;
 assert(!same(last,target,&bot,&ai));remember(last,target,&bot,&ai);assert(same(last,target,&bot,&ai));
 target.z=24;assert(!same(last,target,&bot,&ai)); // same X/Y, different floor is a new request
 target.z=0;target.x=21;assert(same(last,target,&bot,&ai)); // small motion retains backoff
 target.x=40;assert(!same(last,target,&bot,&ai));target.x=20;
 ++bot.instance;assert(!same(last,target,&bot,&ai));--bot.instance;
 ++ai.generation;assert(!same(last,target,&bot,&ai));--ai.generation;
 target.z=-24;remember(last,target,&bot,&ai);LastMovement copied(last);assert(same(copied,target,&bot,&ai));
 copied.clear();assert(!same(copied,target,&bot,&ai));
 std::cout<<"PASS: production retry key preserves backoff but distinguishes floors, instances and transitions\n";
}
'''.replace('__STATE__',state).replace('__KEY__',key).replace('__RECORD__',record)
with tempfile.TemporaryDirectory(prefix='mantech-retry-height-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
