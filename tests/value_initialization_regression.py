"""A first lazy lookup must calculate; constructors cannot fabricate a cached value."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/Value.h').read_text()
definitions='\n'.join(block(source,marker)+';' for marker in (
    'template<class T>\n    class CalculatedValue','class UnitCalculatedValue',
    'class ObjectGuidListCalculatedValue'))
code=r'''
#include <algorithm>
#include <cassert>
#include <ctime>
#include <iostream>
#include <list>
#include <string>
using uint32=unsigned;using ObjectGuid=unsigned;
time_t now=100;time_t fakeTime(time_t*){return now;}
#define time fakeTime
struct Unit{const char* GetName(){return "unit";}};
struct PlayerbotAI{};
struct AiNamedObject{std::string getName(){return "test";}};
struct UntypedValue:AiNamedObject {
 PlayerbotAI* ai;UntypedValue(PlayerbotAI* a,std::string):ai(a){}
 virtual void Reset(){}virtual bool Expired(){return false;}virtual bool Expired(uint32){return false;}
 virtual std::string Format(){return {};}
};
template<class T>struct Value{virtual T Get()=0;virtual T LazyGet()=0;virtual void Set(T)=0;};
constexpr int PERF_MON_VALUE=0;
struct{int start(int,std::string,PlayerbotAI*){return 0;}}sPerformanceMonitor;
__DEFINITIONS__
std::string ObjectGuidListCalculatedValue::Format(){return {};}
struct Target:UnitCalculatedValue {
 Unit* next=nullptr;unsigned calls=0;
 Target(int interval):UnitCalculatedValue(nullptr,"target",interval){value=nullptr;}
 Unit* Calculate()override{++calls;return next;}
};
struct Members:ObjectGuidListCalculatedValue {
 unsigned calls=0;Members():ObjectGuidListCalculatedValue(nullptr,"group members",2){}
 std::list<ObjectGuid> Calculate()override{++calls;return {1,2};}
};
int main(){
 Unit a,b;
 for(int interval:{1,2,10}){
   Target target(interval);target.next=&a;
   assert(target.LazyGet()==&a && target.calls==1);
   target.next=&b;assert(target.LazyGet()==&a && target.calls==1);
   target.Reset();assert(target.LazyGet()==&b && target.calls==2);
   now+=interval;assert(target.Get()==&b && target.calls==3);
 }
 Members members;assert(members.LazyGet().size()==2 && members.calls==1);
 members.Reset();assert(members.LazyGet().size()==2 && members.calls==2);
 std::cout<<"PASS: first lazy target/list reads calculate; cached and reset reads retain intended cadence\n";
}
'''.replace('__DEFINITIONS__',definitions)
with tempfile.TemporaryDirectory(prefix='mantech-value-init-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
