"""Exercise real GUID-backed target values through their shared value interface."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1] / 'playerbot/strategy'
values = (root / 'Value.h').read_text()
definitions = '\n'.join(block(values, marker) + ';' for marker in (
    'template<class T>\n    class ManualSetValue', 'class UnitManualSetValue'))
definitions += '\n' + block((root / 'values/CurrentTargetValue.h').read_text(), 'class CurrentTargetValue') + ';'
definitions += '\n' + block((root / 'values/TargetValue.h').read_text(), 'class PullTargetValue') + ';'
for file, markers in (
    ('CurrentTargetValue.cpp', ('Unit* CurrentTargetValue::Get(', 'void CurrentTargetValue::Set(')),
    ('TargetValue.cpp', ('Unit* PullTargetValue::Get(', 'void PullTargetValue::Set('))):
    text = (root / 'values' / file).read_text()
    definitions += '\n' + '\n'.join(block(text, marker) for marker in markers)
code = r'''
#include <cassert>
#include <iostream>
#include <map>
#include <string>
struct ObjectGuid { unsigned id=0; bool IsEmpty()const{return id==0;} };
struct Unit {
    ObjectGuid guid; bool inMap=true;
    ObjectGuid GetObjectGuid(){return guid;}
    bool IsWithinDistInMap(Unit* unit,float){return unit && unit->inMap;}
    const char* GetName(){return "target";}
};
struct PlayerbotAI{Unit* bot;};
struct UntypedValue {
    Unit* bot;
    UntypedValue(PlayerbotAI* ai,std::string):bot(ai->bot){}
    virtual void Reset(){} virtual std::string Format(){return {};}
};
template<class T>struct Value {
    virtual T Get()=0;virtual T LazyGet()=0;virtual void Set(T)=0;virtual void Reset()=0;
};
struct {float sightDistance=100;}sPlayerbotAIConfig;
struct Accessor {
    std::map<unsigned,Unit*> units;
    Unit* GetUnit(Unit&,ObjectGuid guid){return units[guid.id];}
}sObjectAccessor;
__DEFINITIONS__
template<class T>void check(PlayerbotAI* ai,Unit* first,Unit* second){
    T target(ai);Value<Unit*>* base=&target;
    base->Set(first);assert(base->Get()==first);
    base->Reset();assert(base->Get()==nullptr); // Reset must clear GUID, not unused pointer storage.
    base->Set(first);assert(base->LazyGet()==first);
    sObjectAccessor.units.erase(first->guid.id);
    assert(base->LazyGet()==nullptr); // Resolve again after despawn/logout.
    sObjectAccessor.units[first->guid.id]=first;
    base->Set(second);assert(base->LazyGet()==second);
    base->Reset();base->Reset();assert(!base->Get() && !base->LazyGet());
}
int main(){
    Unit bot{{1}},first{{2}},second{{3}};PlayerbotAI ai{&bot};
    sObjectAccessor.units={{2,&first},{3,&second}};
    check<CurrentTargetValue>(&ai,&first,&second);
    check<PullTargetValue>(&ai,&first,&second);
    UnitManualSetValue direct(&ai,&first);
    direct.Set(&second);direct.Reset();assert(direct.Get()==&first);
    std::cout<<"PASS: current/pull targets clear on reset and resolve fresh on lazy reads\n";
}
'''.replace('__DEFINITIONS__', definitions)
with tempfile.TemporaryDirectory(prefix='mantech-target-reset-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
