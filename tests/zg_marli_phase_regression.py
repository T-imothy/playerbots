"""Exercise each native Mar'li phase/evade implementation against her spell-list contract."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
fixture = r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32 = unsigned;
constexpr unsigned TYPE_MARLI=3,FAIL=0,CAST_OK=0,ATTACKING_TARGET_RANDOM=0,SELECT_FLAG_PLAYER=1;
struct Unit{};
struct Creature {unsigned list=1451001,removed=0;Unit* target=nullptr;
 void SetSpellList(unsigned id){list=id;}void RemoveAurasDueToSpell(unsigned id){removed=id;}
 Unit* SelectAttackingTarget(unsigned,unsigned,unsigned,unsigned){return target;}};
struct ScriptedInstance{unsigned state=999;void SetData(unsigned,unsigned value){state=value;}};
struct CombatAI{virtual void Reset(){};virtual void JustReachedHome(){};virtual void ExecuteAction(uint32){}};
void DoScriptText(int,Creature*){}
__ENUMS__
struct Subject:CombatAI {
 Creature* m_creature;ScriptedInstance* m_instance;bool m_phaseTwo=false;
 unsigned castResult=CAST_OK,lastCast=0,resets=0,threatResets=0,disabled=999;
 std::map<unsigned,unsigned> timers;
 unsigned DoCastSpellIfCan(Unit*,unsigned spell){lastCast=spell;return castResult;}
 void DoResetThreat(){++threatResets;}
 void ResetCombatAction(unsigned action,unsigned duration){timers[action]=duration;++resets;}
 void DisableCombatAction(unsigned action){disabled=action;}
 __METHODS__
};
int main(){
 static_assert(SPELL_LIST_PHASE_1==1451001 && SPELL_LIST_PHASE_2==1451002);
 Creature marli;ScriptedInstance instance;Subject ai;ai.m_creature=&marli;ai.m_instance=&instance;
 ai.Reset();assert(!ai.m_phaseTwo);
 ai.castResult=1;ai.ExecuteAction(MARLI_PHASE_CHANGE);
 assert(!ai.m_phaseTwo && marli.list==1451001 && !ai.resets && !ai.threatResets);
 ai.castResult=CAST_OK;
 for(unsigned cycle=0;cycle<4;++cycle){
  ai.ExecuteAction(MARLI_PHASE_CHANGE);
  assert(ai.m_phaseTwo && marli.list==1451002 && ai.lastCast==SPELL_SPIDER_FORM);
  assert(ai.timers[MARLI_PHASE_CHANGE]==60000 && ai.threatResets==cycle+1);
  ai.castResult=1;ai.ExecuteAction(MARLI_PHASE_CHANGE);
  assert(ai.m_phaseTwo && marli.list==1451002);ai.castResult=CAST_OK;
  ai.ExecuteAction(MARLI_PHASE_CHANGE);
  assert(!ai.m_phaseTwo && marli.list==1451001 && ai.lastCast==SPELL_TRANSFORM_BACK);
  assert(marli.removed==SPELL_SPIDER_FORM && ai.timers[MARLI_PHASE_CHANGE]==60000);
 }
 ai.ExecuteAction(MARLI_PHASE_CHANGE);ai.Reset();ai.JustReachedHome();
 assert(!ai.m_phaseTwo && marli.list==1451001 && instance.state==FAIL);
 ai.m_instance=nullptr;ai.JustReachedHome();assert(marli.list==1451001);
 ai.ExecuteAction(MARLI_CHARGE);assert(ai.disabled==999);
 Unit tank;marli.target=&tank;ai.ExecuteAction(MARLI_CHARGE);assert(ai.disabled==MARLI_CHARGE);
 std::cout<<"PASS: native Marli phase lists, repeated transitions, cast failure, wipe reset and charge\n";
}
'''
for era in ('classic','tbc','wotlk'):
    native = (root.parent/era/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/zulgurub/boss_marli.cpp').read_text()
    enums = native[native.index('enum\n'):native.index('struct boss_marliAI')]
    methods = '\n'.join(block(native, name) for name in ('void Reset()', 'void JustReachedHome()', 'void ExecuteAction('))
    code = fixture.replace('__ENUMS__', enums).replace('__METHODS__', methods)
    with tempfile.TemporaryDirectory(prefix='mantech-marli-'+era+'-') as folder:
        temp = Path(folder)
        (temp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'], cwd=temp, check=True)
        subprocess.run([str(temp/'test.exe')], cwd=temp, check=True)
    print(era, 'native Marli PASS')
