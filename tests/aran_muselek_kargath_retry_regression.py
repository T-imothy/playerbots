"""Run native partial summon, health-threshold trap and post-dance charge actions."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('tbc','wotlk'):
    scripts=root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    sources={
        'aran':(scripts/'eastern_kingdoms/karazhan/boss_shade_of_aran.cpp').read_text(),
        'muselek':(scripts/'outland/coilfang_reservoir/underbog/boss_swamplord_muselek.cpp').read_text(),
        'kargath':(scripts/'outland/hellfire_citadel/shattered_halls/boss_warchief_kargath_bladefist.cpp').read_text(),
    }
    assert 'm_elementalSummons = 0;' in block(sources['aran'],'    void Reset()')
    classes=[]
    for name,action_enum,actions,fields in (
        ('aran','AranActions',('ARAN_ACTION_ELEMENTALS','ARAN_ACTION_DRAGONS_BREATH'),'unsigned m_elementalSummons=0;'),
        ('muselek','MuselekActions',('MUSELEK_TRAP_ONE','MUSELEK_TRAP_TWO'),''),
        ('kargath','WarchiefKargathActions',('WARCHIEF_KARGATH_CHARGE',),'')):
        source=sources[name]
        enums=block(source,'enum\n')+';\n'+block(source,'enum '+action_enum)+';'
        cases='\n'.join(block(source,'            case '+a+':') for a in actions)
        classes.append('namespace '+name+'{'+enums+'\nstruct Boss:Base{'+fields+'void ExecuteAction(unsigned action){switch(action){'+cases+'}}};}')
    code=r'''
#include <cassert>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,TRIGGERED_NONE=0,ATTACKING_TARGET_RANDOM=0,SELECT_FLAG_PLAYER=1,SELECT_FLAG_IN_MELEE_RANGE=2};
struct Unit{};struct Creature:Unit{float hp=30;Unit*victim=nullptr;float GetHealthPercent(){return hp;}
 Unit*GetVictim(){return victim;}Unit*SelectAttackingTarget(unsigned,unsigned,unsigned,unsigned){return victim;}
 Unit*SelectAttackingTarget(unsigned,unsigned,std::nullptr_t,unsigned){return victim;}};
unsigned urand(unsigned a,unsigned){return a;}unsigned texts=0;void DoScriptText(int,Creature*){++texts;}
struct Base{Creature*m_creature;unsigned failSpell=0,distances=0;std::map<unsigned,unsigned>accepted,attempts,timers,delays;
 std::map<unsigned,bool>ready;std::set<unsigned>disabled;
 unsigned DoCastSpellIfCan(Unit*,unsigned id,unsigned=0){++attempts[id];if(id==failSpell)return CAST_FAIL;++accepted[id];return CAST_OK;}
 void SetActionReadyStatus(unsigned id,bool state){ready[id]=state;}void DisableCombatAction(unsigned id){disabled.insert(id);}
 void ResetTimer(unsigned id,unsigned time){timers[id]=time;}void DelayCombatAction(unsigned id,unsigned time){delays[id]=time;}
 void DistanceYourself(){++distances;}
};
__CLASSES__
int main(){
 Creature creature;Unit victim;creature.victim=&victim;
 aran::Boss aran;aran.m_creature=&creature;aran.ready[aran::ARAN_ACTION_ELEMENTALS]=true;
 for(unsigned id:{aran::SPELL_SUMMON_WATER_ELEM_1,aran::SPELL_SUMMON_WATER_ELEM_2,aran::SPELL_SUMMON_WATER_ELEM_3,aran::SPELL_SUMMON_WATER_ELEM_4}){
  aran.failSpell=id;aran.ExecuteAction(aran::ARAN_ACTION_ELEMENTALS);assert(aran.ready.at(aran::ARAN_ACTION_ELEMENTALS)&&aran.accepted[id]==0);
 }
 aran.failSpell=0;aran.ExecuteAction(aran::ARAN_ACTION_ELEMENTALS);assert(!aran.ready.at(aran::ARAN_ACTION_ELEMENTALS)&&aran.m_elementalSummons==15&&texts==1);
 for(unsigned id:{aran::SPELL_SUMMON_WATER_ELEM_1,aran::SPELL_SUMMON_WATER_ELEM_2,aran::SPELL_SUMMON_WATER_ELEM_3,aran::SPELL_SUMMON_WATER_ELEM_4})assert(aran.accepted[id]==1);
 aran.failSpell=aran::SPELL_DRAGONS_BREATH;aran.ExecuteAction(aran::ARAN_ACTION_DRAGONS_BREATH);assert(aran.disabled.empty()&&aran.delays.empty());
 aran.failSpell=0;aran.ExecuteAction(aran::ARAN_ACTION_DRAGONS_BREATH);assert(aran.disabled.count(aran::ARAN_ACTION_DRAGONS_BREATH)&&aran.delays.at(aran::ARAN_ACTION_SUPERSPELL)==6000);
 muselek::Boss muselek;muselek.m_creature=&creature;
 for(unsigned action:{muselek::MUSELEK_TRAP_ONE,muselek::MUSELEK_TRAP_TWO}){
  creature.hp=action==muselek::MUSELEK_TRAP_ONE?69:29;muselek.ready[action]=true;muselek.failSpell=muselek::SPELL_THROW_FREEZING_TRAP;
  unsigned distance=muselek.distances,marks=muselek.accepted[muselek::SPELL_HUNTERS_MARK];muselek.ExecuteAction(action);
  assert(muselek.ready[action]&&muselek.distances==distance&&muselek.accepted[muselek::SPELL_HUNTERS_MARK]==marks);
  muselek.failSpell=0;muselek.ExecuteAction(action);assert(!muselek.ready[action]&&muselek.distances==distance+1);
 }
 kargath::Boss kargath;kargath.m_creature=&creature;kargath.failSpell=kargath::SPELL_CHARGE_H;
 kargath.ExecuteAction(kargath::WARCHIEF_KARGATH_CHARGE);assert(kargath.disabled.empty());
 kargath.failSpell=0;kargath.ExecuteAction(kargath::WARCHIEF_KARGATH_CHARGE);assert(kargath.disabled.count(kargath::WARCHIEF_KARGATH_CHARGE));
 creature.victim=nullptr;kargath.disabled.clear();kargath.ExecuteAction(kargath::WARCHIEF_KARGATH_CHARGE);assert(kargath.disabled.empty());
 std::cout<<"PASS: four distinct Aran summons survive partial failure; breath/trap/charge actions retry without advancing\n";
}
'''.replace('__CLASSES__','\n'.join(classes))
    with tempfile.TemporaryDirectory(prefix='aran-muselek-kargath-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
