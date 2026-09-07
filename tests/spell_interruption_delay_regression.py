"""Execute the production interruption scheduler at second boundaries."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/PlayerbotAI.cpp').read_text()
method = block(source, 'void PlayerbotAI::SpellInterrupted(')
code = r'''
#include <cassert>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <string>
using uint32=uint32_t;
static time_t controlledNow=100;
static time_t testTime(time_t*) { return controlledNow; }
struct LastSpellCast { uint32 id=1; time_t time=100; };
struct Value { LastSpellCast value; LastSpellCast& Get(){return value;} };
struct Context { Value value; template<class T> Value* GetValue(const char*){return &value;} };
struct Config { uint32 reactDelay=100; } sPlayerbotAIConfig;
struct PlayerbotAI {
 Context* aiObjectContext; uint32 delay=10000, writes=0, gcd=1500;
 uint32 CalculateGlobalCooldown(uint32){return gcd;}
 void SetAIInternalUpdateDelay(uint32 duration){delay=duration;++writes;}
 void SpellInterrupted(uint32);
};
#define time(x) testTime(x)
__METHOD__
#undef time
int main(){
 Context context; PlayerbotAI ai{&context}; auto& last=context.value.value;
 // The actual cast path saves time(0) and waits for the full cast duration.
 // Interrupting a ten-second cast in that same second must release that wait.
 ai.SpellInterrupted(1); assert(ai.delay==1500 && last.id==0 && ai.writes==1);
 ai.SpellInterrupted(1); assert(ai.writes==1); // duplicate packet is idempotent
 last={2,100}; ai.delay=10000; ai.writes=0;
 ai.SpellInterrupted(0); ai.SpellInterrupted(1); assert(ai.writes==0 && last.id==2);
 controlledNow=101; ai.SpellInterrupted(2); assert(ai.delay==500 && last.id==0);
 last={2,100}; controlledNow=102; ai.SpellInterrupted(2); assert(ai.delay==100 && last.id==0);
 last={2,100}; controlledNow=100; ai.gcd=0; ai.SpellInterrupted(2); assert(ai.delay==100 && last.id==0);
 // Preserve the existing protection against future timestamps/clock rollback.
 last={2,101}; ai.writes=0; ai.SpellInterrupted(2); assert(ai.writes==0 && last.id==2);
 std::cout<<"PASS: same-second, later, duplicate, unrelated and future interruption timing\n";
}
'''.replace('__METHOD__', method)
assert 'Set(spellId, target->GetObjectGuid(), time(0))' in source
assert 'SetAIInternalUpdateDelay(GetSpellCastDuration(spell))' in block(source, 'void PlayerbotAI::WaitForSpellCast(')
with tempfile.TemporaryDirectory(prefix='mantech-interrupt-delay-') as folder:
    tmp=Path(folder); (tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
