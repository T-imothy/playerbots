"""Compile the actual calculated-value templates against a deterministic clock.

The first assertion reproduces the inverted history append condition without
deliberately dereferencing the old empty list. No realm or database is started.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/Value.h').read_text()
templates = '\n'.join(block(source, marker) + ';' for marker in (
    'template<class T>\n    class CalculatedValue',
    'template<class T> class MemoryCalculatedValue',
    'template<class T> class LogCalculatedValue'))
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <ctime>
#include <iostream>
#include <list>
#include <string>
#include <utility>
using uint32=unsigned;using uint8=unsigned char;
time_t clockNow=100;
time_t fakeTime(time_t*){return clockNow;}
#define time fakeTime
struct PlayerbotAI {};
struct AiNamedObject {std::string getName(){return "fixture";}};
struct UntypedValue:AiNamedObject {
 PlayerbotAI* ai;
 UntypedValue(PlayerbotAI* a,std::string):ai(a){}
 virtual void Reset(){}virtual bool Expired(){return false;}virtual bool Expired(uint32){return false;}
 virtual bool Protected(){return false;}virtual uint32 LastChangeDelay(){return 0;}
};
template<class T>struct Value {virtual T Get()=0;virtual T LazyGet()=0;virtual void Set(T)=0;};
constexpr int PERF_MON_VALUE=0;
struct {int start(int,std::string,PlayerbotAI*){return 0;}} sPerformanceMonitor;
__TEMPLATES__
struct History:LogCalculatedValue<float> {
 float next=5;bool resetDuringCalculate=false;unsigned calculates=0;
 History(unsigned interval=1):LogCalculatedValue(nullptr){minChangeInterval=interval;}
 float Calculate()override{++calculates;if(resetDuringCalculate){Reset();resetDuringCalculate=false;}return next;}
 bool EqualToLast(float v)override{return v==lastValue;}
};
int main(){
 History h;assert(h.Get()==5);
 assert(h.ValueLog().size()==1); // BEFORE FIX: first actual change is incorrectly skipped
 assert(h.GetLastTime()==100&&h.GetLastValue()==5);
 for(unsigned i=0;i<100;++i)h.Get();
 assert(h.ValueLog().size()==1); // unchanged hot reads cannot displace all useful history
 clockNow=101;h.next=7;h.Get();assert(h.ValueLog().size()==1); // existing min-change interval retained
 clockNow=102;h.Get();assert(h.ValueLog().size()==2);
 assert(h.GetLogOn(99).first==5&&h.GetLogOn(102).first==7);
 assert(h.GetValueOn(102)==7&&h.GetTimeOn(102)==102);
 clockNow=104;h.next=13;assert(std::abs(h.GetDelta(5)-2.0f)<0.001f);
 assert(h.ValueLog().size()==3);
 clockNow=110;h.resetDuringCalculate=true;h.next=200;
 assert(h.GetDelta(5)==0); // a new target cannot inherit the previous target's slope
 assert(h.ValueLog().size()==1&&h.GetLastValue()==200);
 h.Reset();assert(h.ValueLog().empty());assert(h.GetDelta(5)==0&&h.ValueLog().size()==1);
 History firstDelta;assert(firstDelta.GetDelta(5)==0); // debug may request delta before Get
 History firstLookup;assert(firstLookup.GetLogOn(1).first==5); // empty lookup safely samples
 for(unsigned i=0;i<25;++i){clockNow+=2;h.next+=2;h.Get();}
 assert(h.ValueLog().size()==10); // existing bounded history, not a growing cache
 // The same template also serves position history; retain its long interval.
 History position(60);position.Get();clockNow+=30;position.next=20;position.Get();
 assert(position.ValueLog().size()==1);clockNow+=31;position.Get();assert(position.ValueLog().size()==2);
 History setValue;setValue.Set(42);assert(setValue.ValueLog().size()==1);
 setValue.Reset();setValue.Set(43);assert(setValue.GetLastValue()==43&&setValue.ValueLog().size()==1);
 clockNow-=500;assert(h.GetDelta(5)==0); // wall-clock rollback cannot divide by nonpositive time
 std::cout<<"PASS: actual value history initialization, sampling, reset, target switch, bounds and clock guards\n";
}
'''.replace('__TEMPLATES__', templates)
for expansion in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-value-history-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', f'/DMANGOSBOT_{expansion}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
