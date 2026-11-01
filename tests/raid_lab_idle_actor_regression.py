"""Idle native diagnostics are bounded to the affected encounter actors."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
from native_core_paths import core_path
source=(core_path('classic',Path(__file__).resolve().parents[2]/'classic')/'src/game/World/RaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <initializer_list>
using uint32=unsigned;
__BODY__
int main(){
 for(unsigned boss:{11981u,11983u,14601u})for(unsigned entry:{11981u,11983u,14601u})assert(ObserveIdleRaidActor(469,boss,entry));
 for(unsigned entry:{15929u,15930u})assert(ObserveIdleRaidActor(533,15928,entry));
 assert(ObserveIdleRaidActor(409,12018,12101));assert(!ObserveIdleRaidActor(409,11982,12101));
 for(unsigned map:{0u,409u,249u,531u})assert(!ObserveIdleRaidActor(map,14601,11981));
 for(unsigned entry:{12460u,16124u,16060u,11669u})assert(!ObserveIdleRaidActor(469,14601,entry));
 assert(!ObserveIdleRaidActor(469,12017,11981));assert(!ObserveIdleRaidActor(533,16060,15929));
}
'''.replace('__BODY__',block(source,'bool ObserveIdleRaidActor('))
body=block(source,'void BodyPull(')
assert 'if(!Enabled()' in body and 'IsInMap(target)' in body and 'if(!a)return' in body
assert 'Clock()-a->last<1000' in block(source,'void Snapshot(')
with tempfile.TemporaryDirectory(prefix='raid-native-observer-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: bounded native actor diagnostics and initial-pull records')
