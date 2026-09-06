"""Exercise the native Hellmaw event handler in TBC and Wrath."""
from pathlib import Path
import subprocess,sys,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
relative='src/game/AI/ScriptDevAI/scripts/outland/auchindoun/shadow_labyrinth/boss_ambassador_hellmaw.cpp'
for era in ('tbc','wotlk'):
    core=root.parent/('mangos-'+era+'-behavior')
    source=(core/relative).read_text()
    if '--before' in sys.argv:
        before={'tbc':'5c2a3e71047c04730749e08874a65681e16d96d2','wotlk':'9a51149f64fff0114747076b99a06f77a3d28d52'}[era]
        source=subprocess.check_output(['git','-c','safe.directory='+core.as_posix(),'-C',str(core),'show',before+':'+relative],text=True)
    method=block(source,'void ReceiveAIEvent(')
    code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum AIEventType{AI_EVENT_CUSTOM_A=10,AI_EVENT_CUSTOM_B,AI_EVENT_CUSTOM_C,AI_EVENT_CUSTOM_D};
struct Unit{};
constexpr unsigned AMBASSADOR_HELLMAW_UNBANISH_CHECK=1;
struct NativeInterface{virtual void ReceiveAIEvent(AIEventType,Unit*,Unit*,uint32){}};
struct Hellmaw:NativeInterface{
 unsigned unbanish=0,timers=0;
 void Unbanish(){++unbanish;}
 void ResetTimer(unsigned id,unsigned ms){assert(id==AMBASSADOR_HELLMAW_UNBANISH_CHECK&&ms==2000);++timers;}
 __METHOD__
};
int main(){Hellmaw boss;
 boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,nullptr,0);assert(boss.unbanish==1&&boss.timers==0);
 boss.ReceiveAIEvent(AI_EVENT_CUSTOM_B,nullptr,nullptr,0);assert(boss.unbanish==1&&boss.timers==1);
 for(auto event:{AI_EVENT_CUSTOM_C,AI_EVENT_CUSTOM_D})boss.ReceiveAIEvent(event,nullptr,nullptr,0);
 assert(boss.unbanish==1&&boss.timers==1);
 boss.ReceiveAIEvent(AI_EVENT_CUSTOM_B,nullptr,nullptr,0);assert(boss.timers==2);
 std::cout<<"PASS: native Hellmaw unbanish and respawn events ignore unrelated notifications\n";
}
'''.replace('__METHOD__',method)
    with tempfile.TemporaryDirectory(prefix='mantech-hellmaw-') as directory:
        directory=Path(directory);(directory/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=directory,check=True)
        subprocess.run([str(directory/'test.exe')],check=True)
