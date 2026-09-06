"""Exercise native CalculatedValue Get timing, replacing only its clock source.

Keep legacy framework semantics: interval 2, not 1, caches for one second.
"""
from pathlib import Path
import re
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/Value.h').read_text()
getter=block(value,'virtual T Get() override').replace('time(0)','fakeNow')
header=(root/'playerbot/strategy/values/EncounterPositionValue.h').read_text()
names=('Solarian','Magtheridon','Gruul','Naxxramas','BlackwingLair','BossCast')
for name in names:
    definition=block(header,f'class {name}PositionValue')
    assert re.search(r'CalculatedValue\(ai, "[^"]+", 2\)',definition),name
# Victim/target lookups remain fresh, and this correction does not alter the
# shared framework's legacy immediate evaluation of other combat values.
fresh=(root/'playerbot/strategy/values/RighteousDefenseTargetValue.h').read_text()
assert '"righteous defense target", 0' in fresh
code=r'''
#include <cassert>
#include <iostream>
#include <string>
using time_t=long long;time_t fakeNow=100;
struct Monitor{int start(int,std::string,void*){return 0;}}sPerformanceMonitor;
enum{PERF_MON_VALUE};
struct AiNamedObject{std::string getName(){return "planner";}};
template<class T>struct Value{virtual T Get()=0;};
template<class T>struct CalculatedValue:Value<T>,AiNamedObject{
 int checkInterval;time_t lastCheckTime=0;T value{};void* ai=nullptr;int calls=0;
 CalculatedValue(int interval):checkInterval(interval){}
 T Calculate(){++calls;return T(calls);}
 __GETTER__
};
int main(){
 CalculatedValue<int> old(1),planner(2),fresh(0);
 for(int i=0;i<10;++i){old.Get();planner.Get();fresh.Get();}
 assert(old.calls==10&&planner.calls==1&&fresh.calls==10);
 ++fakeNow;for(int i=0;i<10;++i)planner.Get();assert(planner.calls==2);
 planner.lastCheckTime=0;planner.Get();assert(planner.calls==3);
 std::cout<<"PASS: actual legacy Get timing; encounter path/grid plans cache one second; fresh target semantics unchanged\n";
}
'''.replace('__GETTER__',getter)
with tempfile.TemporaryDirectory(prefix='mantech-planner-cache-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
