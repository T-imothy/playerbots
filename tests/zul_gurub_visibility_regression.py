"""Exercise real common target admission when Jin'do's Delusions expires."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
method = block((root / 'playerbot/strategy/values/PossibleTargetsValue.cpp').read_text(),
               'bool PossibleTargetsValue::IsAttackable(')
code = r'''
#include <cassert>
#include <iostream>
enum {UNIT_FIELD_FLAGS,UNIT_FLAG_NOT_ATTACKABLE_1=1,UNIT_FLAG_UNTARGETABLE=2,
      UNIT_FLAG_UNINTERACTIBLE=4,SPELL_AURA_SPIRIT_OF_REDEMPTION=8};
struct Unit {unsigned entry=14986,flags=0;bool visible=true,spirit=false;
 unsigned GetEntry(){return entry;}bool HasFlag(int,unsigned f){return flags&f;}
 bool HasAuraType(int){return spirit;}
 bool IsVisibleForOrDetect(Unit*,Unit*,bool){return visible;}};
struct AI{bool vehicle=false;bool IsInVehicle(){return vehicle;}};
struct Player:Unit {unsigned map=309;bool delusions=true,canAttack=true;AI ai;
 struct Camera{Unit*GetBody(){return nullptr;}}camera;Camera&GetCamera(){return camera;}
 unsigned GetMapId(){return map;}bool HasAura(unsigned id){assert(id==24306);return delusions;}
 AI*GetPlayerbotAI(){return &ai;}bool CanAttack(Unit*){return canAttack;}};
struct PossibleTargetsValue{static bool IsAttackable(Unit*,Player*);};
__METHOD__
int main(){
 Player bot;Unit shade;
 assert(PossibleTargetsValue::IsAttackable(&shade,&bot));
 bot.delusions=false;assert(!PossibleTargetsValue::IsAttackable(&shade,&bot)); // Cached combat target loses permission.
 bot.delusions=true;shade.visible=false;assert(!PossibleTargetsValue::IsAttackable(&shade,&bot));
 shade.visible=true;shade.flags=UNIT_FLAG_NOT_ATTACKABLE_1;assert(!PossibleTargetsValue::IsAttackable(&shade,&bot));
 shade.flags=0;bot.canAttack=false;assert(!PossibleTargetsValue::IsAttackable(&shade,&bot));bot.canAttack=true;
 bot.delusions=false;shade.entry=15163;assert(PossibleTargetsValue::IsAttackable(&shade,&bot));
 shade.entry=14986;bot.map=1;assert(PossibleTargetsValue::IsAttackable(&shade,&bot));
 std::cout<<"PASS: Jin'do shade visibility, curse expiry, native admission and unrelated targets\n";
}
'''.replace('__METHOD__', method)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-zg-visibility-') as directory:
        tmp = Path(directory)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', '/DMANGOSBOT_' + era,
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], check=True)
