"""Compile each core's actual paralysis branch with depleted target lists."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
for era in ('classic','tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/ruins_of_ahnqiraj/boss_ayamiss.cpp').read_text()
    branch=block(source,'case AYAMISS_PARALYZE:')
    code=r'''
#include <cassert>
#include <iostream>
#include <vector>
using uint32=unsigned;
enum{AYAMISS_PARALYZE=3,ATTACKING_TARGET_RANDOM,SPELL_PARALYZE=25725,SELECT_FLAG_PLAYER,SPELL_SUMMON_LARVA_1=26538,SPELL_SUMMON_LARVA_2=26539,TRIGGERED_OLD_TRIGGERED,CAST_OK=0};
struct Unit{unsigned guid;unsigned GetObjectGuid(){return guid;}};
struct Creature{Unit* secondary=nullptr;Unit* fallback=nullptr;std::vector<unsigned> selections;unsigned summons=0;
 Unit* SelectAttackingTarget(unsigned,unsigned skip,unsigned spell,unsigned flags){assert(spell==SPELL_PARALYZE&&flags==SELECT_FLAG_PLAYER);selections.push_back(skip);return skip?secondary:fallback;}
 void CastSpell(Unit*,unsigned id,unsigned){assert(id==SPELL_SUMMON_LARVA_1||id==SPELL_SUMMON_LARVA_2);++summons;}};
unsigned urand(unsigned,unsigned){return 1;}
struct Boss{Creature* m_creature;unsigned m_paralyzeTarget=999,casts=0,resets=0;bool castOK=true;Unit* castTarget=nullptr;
 unsigned DoCastSpellIfCan(Unit* target,unsigned){++casts;castTarget=target;return castOK?CAST_OK:1;}
 void ResetCombatAction(unsigned,unsigned interval){assert(interval==15000);++resets;}
 void Execute(unsigned action){switch(action){__BRANCH__}}
};
int main(){Creature creature;Boss boss{&creature};
 boss.Execute(AYAMISS_PARALYZE);assert(creature.selections==std::vector<unsigned>({1,0}));
 assert(!boss.casts&&!boss.resets&&!creature.summons&&boss.m_paralyzeTarget==999);
 Unit secondary{5},fallback{6};creature.secondary=&secondary;creature.fallback=&fallback;creature.selections.clear();
 boss.Execute(AYAMISS_PARALYZE);assert(creature.selections==std::vector<unsigned>({1}));
 assert(boss.castTarget==&secondary&&boss.m_paralyzeTarget==5&&creature.summons==1);
 creature.secondary=nullptr;boss.Execute(AYAMISS_PARALYZE);assert(boss.castTarget==&fallback&&boss.m_paralyzeTarget==6&&creature.summons==2);
 boss.castOK=false;creature.secondary=&secondary;boss.Execute(AYAMISS_PARALYZE);assert(boss.m_paralyzeTarget==6&&creature.summons==2&&boss.resets==2);
 std::cout<<"PASS: actual Ayamiss secondary/fallback/empty target and failed cast branches\n";
}
'''.replace('__BRANCH__',branch)
    with tempfile.TemporaryDirectory(prefix='mantech-ayamiss-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
