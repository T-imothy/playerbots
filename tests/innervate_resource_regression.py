"""Run both actual Innervate eligibility paths at mana boundaries."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]/'playerbot/strategy/druid'
definitions='\n'.join(block((root/file).read_text(), marker)+';' for file,marker in (
    ('DruidActions.h','class CastInnervateAction'),('DruidTriggers.h','class InnervateTrigger')))
code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
using uint32=uint32_t;using uint64=uint64_t;
enum{POWER_MANA};
struct Unit {uint32 current=0,maximum=100;bool valid=true;
 uint32 GetPower(int){return current;}uint32 GetMaxPower(int){return maximum;}};
struct PlayerbotAI{};
struct SpellTargetTrigger {
 SpellTargetTrigger(PlayerbotAI*,const char*,const char*,bool,bool){}
 virtual std::string GetTargetName(){return {};}
 virtual bool IsTargetValid(Unit* unit){return unit&&unit->valid;}
};
using CastSpellTargetAction=SpellTargetTrigger;
struct{uint32 lowMana=20;}sPlayerbotAIConfig;
__DEFINITIONS__
int main(){
 PlayerbotAI ai;CastInnervateAction action(&ai);InnervateTrigger trigger(&ai);Unit target;
 auto check=[&](bool expected){assert(action.IsTargetValid(&target)==expected);assert(trigger.IsTargetValid(&target)==expected);};
 target.current=90;check(false); // BEFORE: integer division treated 90% as zero.
 target.current=0;check(true);target.current=19;check(true);target.current=20;check(false);
 target.current=100;check(false);target.current=1;target.maximum=0;check(false);
 target.current=0;target.maximum=0;check(false);target.maximum=100;target.valid=false;check(false);
 assert(!action.IsTargetValid(nullptr)&&!trigger.IsTargetValid(nullptr));
 target.valid=true;target.maximum=std::numeric_limits<uint32>::max();target.current=target.maximum/10;check(true);
 target.current=target.maximum/2;check(false);
 std::cout<<"PASS: Innervate trigger/action agree at empty, low, threshold, full and zero-capacity mana\n";
}
'''.replace('__DEFINITIONS__',definitions)
with tempfile.TemporaryDirectory(prefix='mantech-innervate-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
