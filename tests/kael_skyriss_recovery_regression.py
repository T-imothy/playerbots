"""Execute native summon-stage retries and Gravity Lapse target bounds."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('tbc','wotlk'):
    scripts=root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    skyriss=(scripts/'outland/tempest_keep/arcatraz/boss_harbinger_skyriss.cpp').read_text()
    kael=(scripts/'eastern_kingdoms/magisters_terrace/boss_felblood_kaelthas.cpp').read_text()
    skyriss_method=block(skyriss,'    void ExecuteAction(uint32 action)').replace(' override','')
    gravity=block(kael,'    void HandleGravityLapse()')
    cases='\n'.join(block(kael,'            case '+case+':') for case in ('KAEL_ACTION_ENERGY_FEEDBACK','KAEL_ACTION_GRAVITY_LAPSE'))
    effect=block(kael[kael.index('struct spell_gravity_lapse_mgt'):],'    void OnEffectExecute(').replace(' override','')
    # The native reset and each new Gravity Lapse start reset the partial summon count.
    assert 'm_gravityLapseSummons = 0;' in block(kael,'    void Reset() override')
    code=r'''
#include <cassert>
#include <deque>
#include <map>
#include <set>
#include <vector>
#include <iostream>
using uint32=unsigned;using SpellEffectIndex=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,SKYRISS_66=0,SKYRISS_33=1,SPELL_66_ILLUSION=36931,SPELL_33_ILLUSION=36932,
 SPELL_BLINK_VISUAL=36937,SAY_IMAGE=19821,MAX_ARCANE_SPHERES=3,
 SPELL_ARCANE_SPHERE_SUMMON=44265,SPELL_GRAVITY_LAPSE_VISUAL=44251,KAEL_GRAVITY_LAPSE_SCRIPT=10,
 KAEL_ACTION_ENERGY_FEEDBACK=0,KAEL_ACTION_GRAVITY_LAPSE=1,SPELL_POWER_FEEDBACK=44233,SPELL_POWER_FEEDBACK_H=47109,
 SAY_TIRED=100,SAY_GRAVITY_LAPSE=101,SAY_RECAST_GRAVITY=102,SPELL_GRAVITY_LAPSE=44224,
 SPELL_GRAVITY_LAPSE_FLY=44227,SPELL_GRAVITY_LAPSE_DOT_N=49887,SPELL_GRAVITY_LAPSE_DOT_H=44226,TRIGGERED_OLD_TRIGGERED};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Unit{Map map;std::vector<unsigned>casts;Map*GetMap(){return &map;}
 void CastSpell(Unit*,unsigned id,unsigned){casts.push_back(id);}};
struct Creature:Unit{float hp=65;float GetHealthPercent(){return hp;}
 struct Position{float o=0;};Position GetRespawnPosition(){return {};}
 void SetFacingTo(float){}void SetTarget(Unit*){}};
unsigned texts=0;void DoScriptText(int,Creature*){++texts;}void DoBroadcastText(int,Creature*){++texts;}
struct Common{
 Creature*m_creature;std::deque<unsigned>results;std::vector<unsigned>casts;std::set<unsigned>disabled;bool script=true,melee=false;
 std::map<unsigned,unsigned>timers;std::map<unsigned,bool>ready;
 unsigned DoCastSpellIfCan(Unit*,unsigned id){casts.push_back(id);if(results.empty())return CAST_OK;
  unsigned result=results.front();results.pop_front();return result;}
 void DisableCombatAction(unsigned id){disabled.insert(id);}void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}
 void SetCombatScriptStatus(bool v){script=v;}void SetMeleeEnabled(bool v){melee=v;}void SetActionReadyStatus(unsigned id,bool v){ready[id]=v;}
};
struct Skyriss:Common{__SKYRISS__};
struct Kael:Common{
 unsigned m_gravityLapseStage=0,m_gravityLapseSummons=0;bool m_isRegularMode=true,m_firstGravityLapse=true;
 __GRAVITY__
 void ExecuteAction(unsigned action){switch(action){__CASES__}}
};
struct Spell{Unit*target=nullptr,*caster=nullptr;unsigned index=0;
 Unit*GetUnitTarget(){return target;}Unit*GetCaster(){return caster;}
 unsigned GetScriptValue(){return index;}void SetScriptValue(unsigned v){index=v;}};
struct GravitySpell{__EFFECT__};
int main(){
 Creature creature;Skyriss sky;sky.m_creature=&creature;
 for(unsigned action:{SKYRISS_66,SKYRISS_33}){
  creature.hp=action==SKYRISS_66?65:32;sky.results={CAST_FAIL};sky.ExecuteAction(action);
  assert(!sky.disabled.count(action));sky.results={CAST_OK,CAST_FAIL};sky.ExecuteAction(action);
  assert(sky.disabled.count(action)); // Cosmetic blink failure cannot repeat the accepted summon.
 }
 creature.hp=100;unsigned casts=sky.casts.size();sky.ExecuteAction(SKYRISS_66);assert(sky.casts.size()==casts);
 Kael boss;boss.m_creature=&creature;
 for(unsigned cycle=0;cycle<100;++cycle){
  boss.results={CAST_OK};boss.ExecuteAction(KAEL_ACTION_GRAVITY_LAPSE);
  assert(boss.m_gravityLapseStage==0&&boss.m_gravityLapseSummons==0&&boss.script);
  assert(boss.timers.at(KAEL_GRAVITY_LAPSE_SCRIPT)==4500);
  unsigned successes=0;
  for(unsigned failedSlot=0;failedSlot<3;++failedSlot){
   boss.results={CAST_FAIL};boss.HandleGravityLapse();
   assert(boss.m_gravityLapseStage==0&&boss.m_gravityLapseSummons==successes);
   assert(boss.timers.at(KAEL_GRAVITY_LAPSE_SCRIPT)==500);
   boss.results={CAST_OK,CAST_FAIL};boss.HandleGravityLapse();++successes;
   assert(boss.m_gravityLapseSummons==successes);
  }
  assert(boss.m_gravityLapseStage==1&&boss.timers.at(KAEL_GRAVITY_LAPSE_SCRIPT)==1500);
  boss.results={CAST_FAIL};boss.HandleGravityLapse();assert(boss.m_gravityLapseStage==1&&boss.script);
  boss.results={CAST_OK};boss.HandleGravityLapse();assert(boss.m_gravityLapseStage==2&&!boss.script&&boss.melee);
  casts=boss.casts.size();boss.HandleGravityLapse();assert(boss.casts.size()==casts&&boss.m_gravityLapseSummons==3);
 }
 for(bool regular:{true,false}){
  boss.m_isRegularMode=regular;boss.ready[KAEL_ACTION_ENERGY_FEEDBACK]=true;boss.results={CAST_FAIL};
  boss.ExecuteAction(KAEL_ACTION_ENERGY_FEEDBACK);assert(boss.ready[KAEL_ACTION_ENERGY_FEEDBACK]);
  boss.results={CAST_OK};boss.ExecuteAction(KAEL_ACTION_ENERGY_FEEDBACK);assert(!boss.ready[KAEL_ACTION_ENERGY_FEEDBACK]);
  assert(boss.casts.back()==(regular?SPELL_POWER_FEEDBACK:SPELL_POWER_FEEDBACK_H));
  Unit target,caster;target.map.regular=regular;Spell spell{&target,&caster};GravitySpell handler;
  for(unsigned n=0;n<5;++n){handler.OnEffectExecute(&spell,0);assert(spell.index==n+1&&caster.casts.back()==44219+n);}
  assert(target.casts.size()==10&&target.casts.back()==(regular?SPELL_GRAVITY_LAPSE_DOT_N:SPELL_GRAVITY_LAPSE_DOT_H));
  for(unsigned invalid:{5u,6u,0xffffffffu}){spell.index=invalid;handler.OnEffectExecute(&spell,0);assert(caster.casts.size()==5&&target.casts.size()==10);}
  spell.target=nullptr;handler.OnEffectExecute(&spell,0);
 }
 std::cout<<"PASS: Skyriss cast retry;100 Kael partial-summon cycles, channel/feedback retries and five-target bounds\n";
}
'''.replace('__SKYRISS__',skyriss_method).replace('__GRAVITY__',gravity).replace('__CASES__',cases).replace('__EFFECT__',effect)
    with tempfile.TemporaryDirectory(prefix='kael-skyriss-recovery-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
