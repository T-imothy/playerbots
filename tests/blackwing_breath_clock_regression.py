"""Observed native breath cycles, bounded early warning, interruption and resets."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include "__HEADER__"
int main(){
 ai::ChromaggusBreathClock clock;
 for(int t=0;t<22;++t)assert(!clock.Observe(t,0));
 for(int t=22;t<=35;++t)assert(clock.Observe(t,0));
 assert(!clock.Observe(36,0)); // missed breath expires; never an indefinite hold
 for(int t=37;t<45;++t)assert(!clock.Observe(t,0));
 assert(clock.Observe(45,23313));assert(clock.Observe(46,23313));
 assert(clock.due[0]==105); // repeated cast observation cannot postpone warning
 assert(!clock.Observe(47,0));
 for(int t=48;t<67;++t)assert(!clock.Observe(t,0));
 for(int t=67;t<75;++t)assert(clock.Observe(t,0));
 assert(clock.Observe(75,23312));assert(clock.Observe(76,23312));assert(!clock.Observe(77,0));
 for(int t=78;t<97;++t)assert(!clock.Observe(t,0));
 assert(clock.Observe(97,0));assert(clock.Observe(98,23313));
 assert(clock.due[0]==158);assert(!clock.Observe(99,0)); // native cast re-synchronizes an early cycle
 assert(!clock.Observe(500,0));assert(clock.due[0]==530); // stale instance observation
 assert(!clock.Observe(1,0));assert(clock.due[0]==31); // backward time
 clock.Reset();assert(!clock.Observe(5,0));
 for(unsigned s:{23187u,23189u,23308u,23309u,23310u,23312u,23313u,23314u,23315u,23316u})assert(clock.IsBreath(s));
 assert(!clock.IsBreath(22276));
}
'''.replace('__HEADER__',(root/'playerbot/strategy/ChromaggusBreathClock.h').as_posix()).replace('#include <cassert>','#include <cassert>\n#include <initializer_list>')
with tempfile.TemporaryDirectory(prefix='chroma-warning-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: native observed breath cadence, bounded warning, cast synchronization and expiry')
