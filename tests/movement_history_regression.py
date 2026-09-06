"""Check the actual stuck-distance reader against a bounded position history."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root = Path(__file__).resolve().parents[1]
method = block((root/'playerbot/strategy/values/StuckValues.cpp').read_text(),
               'uint32 DistanceMovedSinceValue::Calculate(')
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <ctime>
#include <iostream>
#include <list>
#include <string>
#include <utility>
using uint32=unsigned;
time_t clockNow=2000;time_t fakeTime(time_t*){return clockNow;}
#define time fakeTime
struct Player {float x=0;};
struct WorldPosition {float x=0;float sqDistance(Player* p)const{return (x-p->x)*(x-p->x);}};
struct UntypedValue {virtual ~UntypedValue()=default;};
template<class T>struct LogCalculatedValue:UntypedValue {
 unsigned reads=0;std::list<std::pair<T,time_t>> history;
 T Get(){++reads;return T{};}auto ValueLog(){return history;}
};
struct Context {LogCalculatedValue<WorldPosition>* value;UntypedValue* GetUntypedValue(std::string){return value;}};
struct DistanceMovedSinceValue {
 Player* bot;Context* context;std::string qualifier="600";
 std::string getQualifier(){return qualifier;}uint32 Calculate();
};
__METHOD__
int main(){
 Player bot;LogCalculatedValue<WorldPosition> history;Context ctx{&history};DistanceMovedSinceValue reader{&bot,&ctx};
 history.history={{{500},100},{{0},1000},{{0},1500}};
 assert(reader.Calculate()==0); // BEFORE FIX: movement long before this window still counts
 assert(history.reads==1); // refresh the functional value before reading its log
 history.history={{{500},100},{{0},1000},{{20},1500}};assert(reader.Calculate()==20);
 history.history={{{50},1399},{{20},1500}};assert(reader.Calculate()==50); // latest sample at/before cutoff
 history.history={{{50},1400},{{20},1500}};assert(reader.Calculate()==50); // exact cutoff is valid
 history.history={{{50},1401},{{20},1500}};assert(reader.Calculate()==0); // not enough history yet
 history.history={{{0},100}};assert(reader.Calculate()==0); // long stationary history
 history.history.clear();assert(reader.Calculate()==0);
 ctx.value=nullptr;assert(reader.Calculate()==0);
 std::cout<<"PASS: actual movement-history window, old-sample exclusion, refresh and insufficient-history guards\n";
}
'''.replace('__METHOD__', method)
for expansion in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-movement-history-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
