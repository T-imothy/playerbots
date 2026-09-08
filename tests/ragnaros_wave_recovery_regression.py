"""Run native Ragnaros wave tracking, old death callbacks and phase retries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('classic','tbc','wotlk'):
    source=(root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core/boss_ragnaros.cpp').read_text()
    enums=block(source,'enum\n')+';\n'+block(source,'enum RagnarosActions')+';'
    methods='\n'.join(block(source,s).replace(' override','') for s in (
        '    void HandlePhaseTransition()', '    void SummonedCreatureJustDied(', '    void JustSummoned(Creature*'))
    assert 'm_activeSons.clear();' in block(source,'    void Reset() override')
    code=r'''
#include <cassert>
#include <map>
#include <set>
#include <vector>
#include <iostream>
using uint32=unsigned;using GuidSet=std::set<unsigned>;using GuidVector=std::vector<unsigned>;
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,CAST_AURA_NOT_PRESENT=4,TRIGGERED_OLD_TRIGGERED=8,
 UNIT_FIELD_FLAGS=1,UNIT_FLAG_UNINTERACTIBLE=2,UNIT_STAND_STATE_CUSTOM=3,UNIT_STAND_STATE_STAND=0,MINUTE=60,IN_MILLISECONDS=1000};
__ENUMS__
unsigned urand(unsigned a,unsigned){return a;}
struct Unit{};
struct AI{unsigned DoCastSpellIfCan(Unit*,unsigned,unsigned){return CAST_OK;}void AttackClosestEnemy(){}};
struct Creature:Unit{unsigned guid=0,entry=NPC_SON_OF_FLAME,flags=0,stand=0;AI ai;
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}AI*GetAI(){return &ai;}
 auto AI()->struct AI*{return &ai;}void SetInCombatWithZone(){}
 void CastSpell(Unit*,unsigned,unsigned,void*,void*,unsigned){}
 void SetStandState(unsigned v){stand=v;}void SetFlag(unsigned,unsigned v){flags|=v;}void RemoveFlag(unsigned,unsigned v){flags&=~v;}
 void RemoveAurasDueToSpell(unsigned){}
};
void DoScriptText(int,Creature*){}
struct Boss{
 Creature*m_creature;GuidSet m_activeSons;GuidVector m_spawns;unsigned m_phase=PHASE_EMERGED,nextGuid=1,summonCount=8,reductions=0;
 bool m_bHasSubmergedOnce=false,melee=true;std::map<unsigned,unsigned>timers;std::set<unsigned>failed,disabled;
 unsigned DoCastSpellIfCan(Unit*,unsigned id,unsigned=0){
  if(failed.count(id))return CAST_FAIL;
  if(id==SPELL_SUMMON_SONS_FLAME)for(unsigned n=0;n<summonCount;++n){Creature son;son.guid=nextGuid++;JustSummoned(&son);}
  return CAST_OK;}
 void ResetCombatAction(unsigned id,unsigned time){timers[id]=time;}void ReduceTimer(unsigned id,unsigned time){++reductions;timers[id]=time;}
 void DisableCombatAction(unsigned id){disabled.insert(id);}void SetMeleeEnabled(bool v){melee=v;}
 __METHODS__
};
int main(){
 Creature creature;creature.entry=11502;Boss boss;boss.m_creature=&creature;
 boss.failed={SPELL_SUMMON_SONS_FLAME};boss.HandlePhaseTransition();
 assert(boss.m_phase==PHASE_EMERGED&&boss.melee&&!creature.flags&&boss.m_activeSons.empty()&&boss.disabled.empty());
 assert(boss.timers.at(RAGNAROS_PHASE_TRANSITION)==500);
 boss.failed.clear();boss.HandlePhaseTransition();assert(boss.m_phase==PHASE_SUBMERGING&&boss.m_activeSons.size()==8&&!boss.melee);
 auto firstWave=boss.m_activeSons;
 boss.failed={SPELL_RAGNA_SUBMERGE};boss.HandlePhaseTransition();assert(boss.m_phase==PHASE_SUBMERGING&&boss.m_activeSons.size()==8);
 boss.failed.clear();boss.HandlePhaseTransition();assert(boss.m_phase==PHASE_SUBMERGED&&boss.timers.at(RAGNAROS_PHASE_TRANSITION)==90000);
 // Timeout can leave survivors. Their later death must not count toward a new wave.
 boss.HandlePhaseTransition();assert(boss.m_phase==PHASE_EMERGING);
 boss.failed={SPELL_RAGNA_EMERGE};boss.HandlePhaseTransition();assert(boss.m_phase==PHASE_EMERGING&&!boss.melee&&creature.flags);
 boss.failed.clear();boss.HandlePhaseTransition();assert(boss.m_phase==PHASE_EMERGED&&boss.melee&&!creature.flags);
 boss.summonCount=3;boss.HandlePhaseTransition();assert(boss.m_activeSons.size()==3);boss.HandlePhaseTransition();
 for(unsigned guid:firstWave){Creature old;old.guid=guid;boss.SummonedCreatureJustDied(&old);}
 assert(boss.m_activeSons.size()==3&&boss.reductions==0);
 auto secondWave=boss.m_activeSons;
 for(unsigned guid:secondWave){Creature son;son.guid=guid;boss.SummonedCreatureJustDied(&son);boss.SummonedCreatureJustDied(&son);}
 assert(boss.m_activeSons.empty()&&boss.reductions==1&&boss.timers.at(RAGNAROS_PHASE_TRANSITION)==1000);
 // Zero/partial/full waves killed during the three-second animation still emerge promptly.
 for(unsigned count:{0u,1u,3u,8u}){
  boss.m_phase=PHASE_EMERGED;boss.summonCount=count;boss.HandlePhaseTransition();assert(boss.m_activeSons.size()==count);
  auto wave=boss.m_activeSons;unsigned reductions=boss.reductions;
  for(unsigned guid:wave){Creature son;son.guid=guid;boss.SummonedCreatureJustDied(&son);}
  assert(boss.reductions==reductions);boss.HandlePhaseTransition();
  assert(boss.m_phase==PHASE_SUBMERGED&&boss.timers.at(RAGNAROS_PHASE_TRANSITION)==1000);
 }
 std::cout<<"PASS: Ragnaros actual wave ownership, duplicate/old deaths, early clears and rejected phase casts\n";
}
'''.replace('__ENUMS__',enums).replace('__METHODS__',methods)
    with tempfile.TemporaryDirectory(prefix='ragnaros-wave-recovery-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
