"""Execute native timer branches with success, every failure and absent targets."""
from pathlib import Path
import re, subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
fixture = r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum {CAST_OK=0,ATTACKING_TARGET_RANDOM,SELECT_FLAG_PLAYER,
 SPELL_DOMINATEMIND,SPELL_SHADE_SOUL_CHANNEL,SPELL_HOLY_SMITE,
 SPELL_HOLY_FIRE,SPELL_HOLY_NOVA,SPELL_BERSERK,SAY_BERSERK};
unsigned urand(unsigned lo,unsigned){return lo;}
struct Unit{};
struct Creature:Unit {Unit*target=nullptr;template<class... T>Unit*SelectAttackingTarget(T...){return target;}};
struct AI {
 Creature* m_creature;unsigned result=0,calls=0,resets=0,emotes=0;
 unsigned timer=1,m_uiBanishTimer=1,m_uiBerserkTimer=1;
 unsigned m_uiHolySmiteTimer=1,m_uiHolyFireTimer=1,m_uiHolyNovaTimer=1;
 unsigned DoCastSpellIfCan(Unit*,unsigned){++calls;return result;}
 void ResetCombatAction(unsigned,unsigned value){++resets;timer=value;}
 void DoScriptText(unsigned,Creature*){++emotes;}
 void tick(unsigned uiDiff=2){__BODY__}
};
int main(){
 Creature creature;Unit target;creature.target=&target;
 for(unsigned result=0;result<=12;++result){
  AI ai{&creature};ai.result=result;ai.tick();assert(ai.calls==1);
  if(result==CAST_OK){__SUCCESS__}else{__FAILURE__}
 }
 __NO_TARGET__
 std::cout<<"PASS: __LABEL__ native success/failure timer branches\n";
}
'''
for era in ('classic','tbc','wotlk'):
    scripts = root.parent / f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    source = (scripts/'eastern_kingdoms/scarlet_monastery/boss_mograine_and_whitemane.cpp').read_text()
    actor = block(source,'struct boss_high_inquisitor_whitemaneAI')
    action = block(actor,'void ExecuteAction(')
    branch = block(action,'case WHITEMANE_ACTION_DOMINATE_MIND:')
    branch = branch[branch.index('{'):]
    cases = [('Whitemane', 'unsigned action=0;'+branch,
        'assert(ai.resets==1&&ai.timer>=20000);', 'assert(ai.resets==0&&ai.timer==1);',
        'creature.target=nullptr;AI absent{&creature};absent.tick();assert(absent.calls==0&&absent.resets==0);')]
    if era != 'classic':
        source = (scripts/'outland/black_temple/boss_shade_of_akama.cpp').read_text()
        actor = block(source,'struct mob_ashtongue_channelerAI')
        branch = block(actor,'if (m_uiBanishTimer)')
        cases.append(('Akama channeler',branch,'assert(ai.m_uiBanishTimer==0);','assert(ai.m_uiBanishTimer==1);',''))
    if era == 'wotlk':
        source = (scripts/'northrend/crusaders_coliseum/trial_of_the_champion/boss_argent_challenge.cpp').read_text()
        for timer in ('HolySmite','HolyFire','HolyNova'):
            field = 'm_ui'+timer+'Timer'
            branch = block(source, f'if ({field} < uiDiff)')
            absent = '' if timer == 'HolyNova' else f'creature.target=nullptr;AI absent{{&creature}};absent.tick();assert(absent.calls==0&&absent.{field}==1);'
            cases.append(('Paletress '+timer,branch,f'assert(ai.{field}>=1000);',f'assert(ai.{field}==1);',absent))
        source = (scripts/'northrend/icecrown_citadel/icecrown_citadel/boss_lord_marrowgar.cpp').read_text()
        branch = block(source,'if (m_uiBerserkTimer)')
        cases.append(('Marrowgar',branch,'assert(ai.m_uiBerserkTimer==0&&ai.emotes==1);','assert(ai.m_uiBerserkTimer==1&&ai.emotes==0);',''))
    # CAST_OK is natively zero in every era; fixtures deliberately use it.
    assert re.search(r'CAST_OK\s*=\s*0', (scripts.parents[1]/'BaseAI/UnitAI.h').read_text())
    for label,body,success,failure,absent in cases:
        code=fixture.replace('__BODY__',body).replace('__SUCCESS__',success).replace('__FAILURE__',failure).replace('__NO_TARGET__',absent).replace('__LABEL__',era+' '+label)
        with tempfile.TemporaryDirectory(prefix='mantech-cast-result-') as folder:
            tmp=Path(folder);(tmp/'test.cpp').write_text(code)
            subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
            subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
