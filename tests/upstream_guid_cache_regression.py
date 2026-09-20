"""Exercise actual GUID cache classes and native target visibility/reset code."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
v=(r/'playerbot/strategy/Value.h').read_text()
classes='\n'.join(block(v,k)+';' for k in ['class UntypedValue :','template<class T>\n    class Value','template<class T>\n    class CalculatedValue','class UnitCalculatedValue :','template<class T>\n    class ManualSetValue','class UnitManualSetValue :'])
classes+='\n'+block((r/'playerbot/strategy/values/CurrentTargetValue.h').read_text(),'class CurrentTargetValue :')+';'
methods='\n'.join(block((r/'playerbot/strategy/Value.cpp').read_text(),k) for k in ['std::string UnitCalculatedValue::Format','std::string UnitManualSetValue::Format'])
methods+='\n'+'\n'.join(block((r/'playerbot/strategy/values/CurrentTargetValue.cpp').read_text(),k) for k in ['ObjectGuid CurrentTargetValue::Get','void CurrentTargetValue::Set'])
code=r'''
#include <cassert>
#include <ctime>
#include <map>
#include <string>
#include <iostream>
using uint32=unsigned;
struct ObjectGuid { unsigned n=0; ObjectGuid()=default; explicit ObjectGuid(unsigned n):n(n){} bool IsEmpty() const{return !n;} bool operator<(ObjectGuid b) const{return n<b.n;} bool operator==(ObjectGuid b) const{return n==b.n;} };
struct Player;struct Unit { ObjectGuid guid;ObjectGuid GetObjectGuid(){return guid;}bool visible=true,near=true; const char* GetName(){return "target";} bool IsVisibleForOrDetect(Player*,void*,bool){return visible;} };
struct Camera{void* GetBody(){return nullptr;}};
struct Player:Unit {Camera camera;bool IsWithinDistInMap(Unit* u,float){return u->near;} Camera& GetCamera(){return camera;}};
struct PlayerbotAI{Player* bot;std::map<ObjectGuid,Unit*> units; Unit* GetUnit(ObjectGuid g){auto i=units.find(g);return i==units.end()?nullptr:i->second;}};
struct Accessor{PlayerbotAI* ai;Unit* GetUnit(Player&,ObjectGuid g){return ai->GetUnit(g);}}sObjectAccessor;
struct Config{float sightDistance=100;}sPlayerbotAIConfig;
struct AiNamedObject{PlayerbotAI* ai;Player* bot;std::string name;AiNamedObject(PlayerbotAI* a,std::string n):ai(a),bot(a->bot),name(n){} const char* getName(){return name.c_str();}};
struct Perf{int start(int,const char*,PlayerbotAI*){return 0;}}sPerformanceMonitor;
#define PERF_MON_VALUE 0
#define MANTECH_DIAG_SCOPE(...)
static time_t clockNow=100;
#define time(x) clockNow
__CLASSES__
__METHODS__
struct Probe:UnitCalculatedValue {ObjectGuid result;unsigned calls=0;Probe(PlayerbotAI* a,int interval):UnitCalculatedValue(a,"test",interval){} ObjectGuid Calculate() override{++calls;return result;}};
int main(){
 Player bot;PlayerbotAI ai{&bot};sObjectAccessor.ai=&ai;
 Unit unit;unit.guid=ObjectGuid(42);ai.units[unit.guid]=&unit;
 Probe probe(&ai,10);probe.result=unit.guid;
 assert(probe.Get()==unit.guid&&probe.calls==1);
 ai.units.erase(unit.guid);assert(ai.GetUnit(probe.Get())==nullptr&&probe.calls==1);
 assert(ai.GetUnit(probe.LazyGet())==nullptr&&probe.calls==1);
 Unit replacement;replacement.guid=ObjectGuid(43);ai.units[replacement.guid]=&replacement;
 probe.result=replacement.guid;clockNow+=5;assert(probe.Get()==replacement.guid&&probe.calls==2);
 Probe fresh(&ai,0);fresh.result=replacement.guid;assert(fresh.Get()==replacement.guid&&fresh.calls==1);
 CurrentTargetValue target(&ai);target.Set(replacement.guid);assert(target.Get()==replacement.guid);assert(target.LazyGet()==replacement.guid);
 replacement.visible=false;assert(target.Get().IsEmpty());replacement.visible=true;
 replacement.near=false;assert(target.Get().IsEmpty());replacement.near=true;
 target.Reset();assert(target.Get().IsEmpty()&&target.LazyGet().IsEmpty());
 target.Set(replacement.guid);ai.units.clear();assert(target.Get().IsEmpty());
 std::cout<<"PASS: GUID cache expiry/removal, fresh zero-interval calculation, target visibility/range, virtual lazy/reset\n";
}
'''.replace('__CLASSES__',classes).replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='turtle-guid-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
