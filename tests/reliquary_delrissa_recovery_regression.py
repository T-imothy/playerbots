"""Actual native transition callbacks: failed casts, reset and duplicate deaths."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
reliquary=r'''
#include <cassert>
#include <map>
#include <vector>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;using GuidVector=std::vector<unsigned>;
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,CAST_AURA_NOT_PRESENT=4,
 PHASE_0_NOT_BEGUN=0,PHASE_1_SUFFERING=1,PHASE_2_DESIRE=2,PHASE_3_ANGER=3,
 SPELL_SUMMON_ESSENCE_SUFFERING=10,SPELL_SUMMON_ESSENCE_DESIRE,SPELL_SUMMON_ESSENCE_ANGER,
 SPELL_SUBMERGE_VISUAL,SPELL_SUMMON_ENSLAVED_SOUL,RELIQUARY_ACTION_SUBMERGE,RELIQUARY_ACTION_SUMMON_SOUL,
 UNIT_STAND_STATE_SLEEP,REACT_PASSIVE,POINT_MOTION_TYPE,NPC_ESSENCE_SUFFERING,NPC_ESSENCE_DESIRE,
 SUFF_SAY_AFTER,DESI_SAY_AFTER,NPC_RELIQUARY_COMBAT_TRIGGER,MAX_ENSLAVED_SOULS=21};
struct Creature{unsigned entry=0,despawns=0,removes=0;void RemoveAurasDueToSpell(unsigned){++removes;}
 void SetStandState(unsigned){}unsigned GetEntry(){return entry;}void ForcedDespawn(){++despawns;}void SetInCombatWithZone(){}};
struct Instance{GuidVector souls{1,2,3};GuidVector&GetEnslavedSouls(){return souls;}Creature*GetSingleCreatureFromStorage(unsigned){return nullptr;}};
struct AI{Creature*m_creature;Instance*m_instance;unsigned m_phase=0,m_soulDeathCount=0,m_soulSummonedCount=0;bool m_submerged=false;
 std::vector<unsigned>results;std::vector<unsigned>spells;unsigned resets=0,cleanups=0,emotes=0;std::map<unsigned,unsigned>timers;
 unsigned DoCastSpellIfCan(Creature*,unsigned id,unsigned=0){spells.push_back(id);unsigned result=results.empty()?0:results.front();if(!results.empty())results.erase(results.begin());return result;}
 void ResetTimer(unsigned id,unsigned time){timers[id]=time;++resets;}void DisableTimer(unsigned id){timers.erase(id);}
 void DespawnGuids(GuidVector&guids){++cleanups;guids.clear();}void SetCombatMovement(bool){}void SetReactState(unsigned){}
 void DoScriptText(unsigned,Creature*){++emotes;}
 void essence()__ESSENCE__
 void wave()__WAVE__
 __RESET__
 __MOVEMENT__
};
int main(){
 Creature boss,essence;Instance instance;
 for(unsigned phase=1;phase<=3;++phase){
  AI ai{&boss,&instance};ai.m_phase=phase;ai.results={CAST_FAIL};instance.souls={1,2,3};ai.essence();
  assert(!ai.m_submerged&&ai.tim ers[RELIQUARY_ACTION_SUBMERGE]==1000&&ai.cleanups==0&&instance.souls.size()==3);
  ai.results={CAST_OK,CAST_OK};ai.timers[RELIQUARY_ACTION_SUMMON_SOUL]=1;ai.essence();
  assert(ai.m_submerged&&ai.cleanups==1&&instance.souls.empty()&&!ai.timers.count(RELIQUARY_ACTION_SUMMON_SOUL));
  const unsigned calls=ai.spells.size();ai.essence();ai.wave();assert(ai.spells.size()==calls);
 }
 AI wave{&boss,&instance};wave.m_phase=2;wave.results={0,1,0};wave.wave();
 assert(wave.m_soulSummonedCount==2&&wave.tim ers[RELIQUARY_ACTION_SUMMON_SOUL]==2400);
 wave.results={1,1,1};wave.wave();assert(wave.m_soulSummonedCount==2);wave.wave();assert(wave.m_soulSummonedCount==5);
 wave.m_soulSummonedCount=20;wave.spells.clear();wave.wave();assert(wave.spells.size()==1&&wave.m_soulSummonedCount==21);
 wave.wave();assert(wave.spells.size()==1);
 wave.m_submerged=true;wave.m_soulDeathCount=17;wave.Reset();assert(!wave.m_submerged&&wave.m_phase==0&&wave.m_soulDeathCount==0&&wave.m_soulSummonedCount==0);
 wave.spells.clear();wave.wave();wave.essence();assert(wave.spells.empty());
 wave.m_instance=nullptr;wave.Reset();wave.m_phase=1;wave.wave();wave.essence();assert(wave.spells.empty());
 // Only the current essence can advance the phase. A delayed duplicate cannot restart the intermission.
 AI transition{&boss,&instance};transition.m_phase=1;essence.entry=NPC_ESSENCE_SUFFERING;
 transition.SummonedMovementInform(&essence,POINT_MOTION_TYPE,1);assert(transition.m_phase==2&&transition.resets==2&&essence.despawns==1);
 transition.SummonedMovementInform(&essence,POINT_MOTION_TYPE,1);assert(transition.resets==2&&essence.despawns==1);
 essence.entry=999;transition.SummonedMovementInform(&essence,POINT_MOTION_TYPE,1);assert(transition.resets==2);
 essence.entry=NPC_ESSENCE_DESIRE;transition.SummonedMovementInform(&essence,POINT_MOTION_TYPE,1);assert(transition.m_phase==3&&transition.resets==4);
 std::cout<<"PASS: Reliquary failed essence, partial waves, stale movement callbacks and reset\n";
}
'''.replace('tim ers','timers')
delrissa=r'''
#include <cassert>
#include <algorithm>
#include <list>
#include <vector>
#include <iostream>
using uint32=unsigned;using GuidList=std::list<unsigned>;
enum{MAX_DELRISSA_ADDS=4,SPELL_PERMANENT_FEIGN_DEATH=1,SPELL_SUICIDE=2,TRIGGERED_OLD_TRIGGERED=3};
unsigned aDelrissaAddDeath[4]={10,11,12,13};
struct Creature{unsigned guid=10,owner=10,entry=0,casts=0;bool feign=false;
 unsigned GetObjectGuid(){return guid;}unsigned GetSpawnerGuid(){return owner;}unsigned GetEntry(){return entry;}
 bool HasAura(unsigned){return feign;}void CastSpell(Creature*,unsigned id,unsigned){assert(id==SPELL_SUICIDE);++casts;}};
struct AI{Creature*m_creature;std::vector<unsigned>m_vuiLackeyEnties{1,2,3,4,5,6,7,8};GuidList m_deadCompanionGuids;unsigned m_summonsKilled=0,lines=0;
 void DoScriptText(unsigned line,Creature*){assert(line>=10&&line<=13);++lines;}
 __METHOD__
};
int main(){
 Creature boss,companion;AI ai{&boss};companion.guid=20;companion.entry=1;
 ai.SummonedCreatureJustDied(nullptr);companion.owner=99;ai.SummonedCreatureJustDied(&companion);assert(ai.m_summonsKilled==0);
 companion.owner=10;companion.entry=5;ai.SummonedCreatureJustDied(&companion);assert(ai.m_summonsKilled==0);
 companion.entry=1;ai.SummonedCreatureJustDied(&companion);ai.SummonedCreatureJustDied(&companion);assert(ai.m_summonsKilled==1&&ai.lines==1);
 for(unsigned i=2;i<=3;++i){companion.guid=20+i;companion.entry=i;ai.SummonedCreatureJustDied(&companion);}
 boss.feign=true;companion.guid=24;companion.entry=4;ai.SummonedCreatureJustDied(&companion);
 assert(ai.m_summonsKilled==4&&ai.lines==3&&boss.casts==1);
 for(unsigned i=0;i<10;++i){companion.guid++;ai.SummonedCreatureJustDied(&companion);}
 assert(ai.m_summonsKilled==4&&ai.lines==3&&boss.casts==1);
 AI empty{&boss};empty.m_vuiLackeyEnties.clear();empty.SummonedCreatureJustDied(&companion);assert(empty.m_summonsKilled==0);
 std::cout<<"PASS: Delrissa selected companion ownership, duplicate deaths and bounded completion\n";
}
'''
for era in ('tbc','wotlk'):
    scripts=root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    source=(scripts/'outland/black_temple/boss_reliquary_of_souls.cpp').read_text()
    actor=block(source,'struct boss_reliquary_of_soulsAI')
    def callback(name):
        value=block(actor,'AddCustomAction('+name+',')
        return value[value.index('{'):]
    code=reliquary.replace('__ESSENCE__',callback('RELIQUARY_ACTION_SUBMERGE')).replace('__WAVE__',callback('RELIQUARY_ACTION_SUMMON_SOUL'))
    code=code.replace('__RESET__',block(actor,'void Reset(').replace(' override','')).replace('__MOVEMENT__',block(actor,'void SummonedMovementInform(').replace(' override',''))
    source=(scripts/'eastern_kingdoms/magisters_terrace/boss_priestess_delrissa.cpp').read_text()
    actor=block(source,'struct boss_priestess_delrissaAI')
    companion=delrissa.replace('__METHOD__',block(actor,'void SummonedCreatureJustDied(').replace(' override',''))
    assert 'm_deadCompanionGuids.clear()' in block(actor,'void Reset(')
    for label,fixture in (('reliquary',code),('delrissa',companion)):
        with tempfile.TemporaryDirectory(prefix=label+'-') as folder:
            tmp=Path(folder);(tmp/'test.cpp').write_text(fixture)
            subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
            subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
