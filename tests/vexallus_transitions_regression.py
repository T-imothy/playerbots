"""Run native Vexallus threshold/heroic-half/overload retries and reset."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <set>
#include <vector>
#include <iostream>
using uint8=uint8_t;using uint32=unsigned;using GuidVector=std::vector<unsigned>;
enum{CAST_OK=0,CAST_TRIGGERED=1,ATTACKING_TARGET_RANDOM,SELECT_FLAG_IN_LOS=4,SELECT_FLAG_PLAYER=8,
 SPELL_CHAIN_LIGHTNING=44318,SPELL_CHAIN_LIGHTNING_H=46380,SPELL_ARCANE_SHOCK=44319,SPELL_ARCANE_SHOCK_H=46381,
 SPELL_SUMMON_PURE_ENERGY=44322,SPELL_SUMMON_PURE_ENERGY1_H=46154,SPELL_SUMMON_PURE_ENERGY2_H=46159,SPELL_OVERLOAD=44352,
 SAY_ENERGY=1,EMOTE_DISCHARGE_ENERGY,SAY_OVERLOAD,EMOTE_OVERLOAD};
enum{VEXALLUS_OVERLOAD,VEXALLUS_SUMMON_PURE_ENERGY,VEXALLUS_ACTION_CHAIN_LIGHTNING,VEXALLUS_ACTION_SHOCK};
struct Unit{float hp=100;float GetHealthPercent(){return hp;}};
struct Creature:Unit{template<class... T>Unit*SelectAttackingTarget(T...){return nullptr;}};
struct CombatAI{void Reset(){}};
struct AI:CombatAI{
 Creature*m_creature;bool m_isRegularMode=true;float m_intervalHealthAmount=85;uint8 m_energySummons=0;GuidVector m_sparks;
 std::set<unsigned>fail,disabled;std::map<unsigned,unsigned>attempts,success;unsigned emotes=0;
 int DoCastSpellIfCan(Unit*,unsigned spell,int=0){++attempts[spell];if(fail.count(spell))return 1;++success[spell];return CAST_OK;}
 void SetActionReadyStatus(unsigned action,bool ready){assert(!ready);disabled.insert(action);}
 void SetCombatMovement(bool){}void DespawnGuids(GuidVector&g){g.clear();}
 void DoScriptText(unsigned,Creature*){++emotes;}void ResetCombatAction(unsigned,unsigned){}
 unsigned GetSubsequentActionTimer(unsigned){return 8000;}
 __METHODS__
 void Tick(unsigned action){if(!disabled.count(action))ExecuteAction(action);}
};
int main(){Creature boss;boss.hp=85;
 for(bool regular:{true,false})for(unsigned failed:{44322u,46154u,46159u}){
  if(regular!=(failed==44322))continue;
  AI ai;ai.m_creature=&boss;ai.m_isRegularMode=regular;ai.fail.insert(failed);
  ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);
  assert(ai.m_intervalHealthAmount==85&&ai.emotes==0&&ai.disabled.empty());
  if(!regular){unsigned other=failed==46154?46159:46154;assert(ai.attempts[other]==1&&ai.success[other]==1);}
  ai.fail.clear();ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);
  assert(ai.m_intervalHealthAmount==70&&ai.emotes==2&&ai.m_energySummons==0);
  assert(ai.success[regular?44322:46154]==1);if(!regular)assert(ai.success[46159]==1);
  ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);assert(ai.m_intervalHealthAmount==70); // No early next wave.
  boss.hp=25;for(unsigned i=0;i<10;++i)ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);
  assert(ai.m_intervalHealthAmount==10&&ai.disabled.count(VEXALLUS_SUMMON_PURE_ENERGY)&&ai.emotes==10);
  assert(ai.success[regular?44322:46154]==5);if(!regular)assert(ai.success[46159]==5);
  boss.hp=85;
 }
 AI ai;ai.m_creature=&boss;ai.m_isRegularMode=false;ai.fail={46159};ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);
 assert(ai.m_energySummons==1);ai.m_sparks={1,2};ai.Reset();
 assert(ai.m_energySummons==0&&ai.m_intervalHealthAmount==85&&ai.m_sparks.empty());
 ai.fail.clear();ai.Tick(VEXALLUS_SUMMON_PURE_ENERGY);assert(ai.success[46154]==2&&ai.success[46159]==1);
 AI overload;overload.m_creature=&boss;overload.Tick(VEXALLUS_OVERLOAD);assert(overload.attempts.empty());
 boss.hp=20;overload.fail={44352};overload.Tick(VEXALLUS_OVERLOAD);
 assert(overload.disabled.empty()&&overload.emotes==0&&overload.success.empty());
 overload.fail.clear();overload.Tick(VEXALLUS_OVERLOAD);overload.Tick(VEXALLUS_OVERLOAD);
 assert(overload.success[44352]==1&&overload.emotes==2&&overload.disabled.count(VEXALLUS_OVERLOAD));
 std::cout<<"PASS: Vexallus normal/heroic partial retries, five thresholds, reset and Overload\n";
}
'''
for era in ('tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/magisters_terrace/boss_vexallus.cpp').read_text()
    actor=block(source,'struct boss_vexallusAI')
    methods='\n'.join(block(actor,name).replace(' override','') for name in ('void Reset()', 'void ExecuteAction('))
    with tempfile.TemporaryDirectory(prefix='mantech-vexallus-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(fixture.replace('__METHODS__',methods))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
