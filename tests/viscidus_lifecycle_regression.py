"""Run native Viscidus wave creation, duplicate callbacks and summon bounds."""
from pathlib import Path
import re,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <list>
#include <vector>
#include <iostream>
using uint8=uint8_t;using uint32=unsigned;using ObjectGuid=unsigned;using GuidList=std::list<unsigned>;
enum{NPC_GLOB_OF_VISCIDUS=15667,POINT_MOTION_TYPE=1,REACT_PASSIVE=0,PHASE_NORMAL=1,PHASE_EXPLODED=5,PHASE_REJOIN=6,
 MAX_VISCIDUS_GLOBS=20,SPELL_REJOIN_VISCIDUS=25896,SPELL_SUMMON_GLOBS=25885,SPELL_VISCIDUS_SHRINKS_2=27934,
 SPELL_INVIS_SELF=25905,SPELL_INVIS_STALKER=27933,SPELL_STUN_SELF=25900,SPELL_MEMBRANE_VISCIDUS=25994,
 SPELL_VISCIDUS_WEAKNESS=25926,CAST_TRIGGERED=1,TRIGGERED_OLD_TRIGGERED=2,TRIGGERED_IGNORE_GCD=4,SPELL_CAST_OK=0};
enum SpellEffectIndex{EFFECT_INDEX_0,EFFECT_INDEX_1};
struct Unit{float hp=100;std::vector<unsigned>casts;bool fail=false;
 float GetHealthPercent(){return hp;}int CastSpell(Unit*,unsigned spell,int){casts.push_back(spell);return fail?1:SPELL_CAST_OK;}
 void RemoveAurasDueToSpell(unsigned){}void GetRespawnCoord(float&x,float&y,float&z){x=y=z=0;}};
struct Spell{Unit*target;Unit*GetUnitTarget(){return target;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,SpellEffectIndex)const{}};
struct Creature:Unit{unsigned entry=NPC_GLOB_OF_VISCIDUS,guid=1,despawns=0;
 struct MobAI{void SetReactState(int){}}brain;struct Motion{void MovePoint(int,float,float,float){}}motion;
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}MobAI*AI(){return &brain;}Motion*GetMotionMaster(){return &motion;}
 void ForcedDespawn(unsigned){++despawns;}};
struct CombatAI{void Reset(){}};
struct boss_viscidusAI:CombatAI{
 Creature*m_creature;uint8 m_phase=PHASE_NORMAL,m_aliveGlobs=0;uint32 m_hitCount=0;GuidList m_lGlobesGuidList;
 unsigned waves=0,phaseChanges=0;Creature spawned;void SetDeathPrevention(bool){}
 void SetPhase(uint8 p){m_phase=p;++phaseChanges;}
 void DoCastSpellIfCan(Creature*,unsigned spell,int flags){
  if(spell==SPELL_SUMMON_GLOBS){assert(flags==CAST_TRIGGERED);++waves;JustSummoned(&spawned);JustSummoned(&spawned);}
 }
 __METHODS__
};
struct CheckedSpellList{std::array<unsigned,20>spells;unsigned operator[](unsigned index)const{assert(index<spells.size());return spells[index];}};
const CheckedSpellList auiGlobSummonSpells{{__SPELLS__}};
__SUMMON__;
int main(){
 Unit unit;Spell spell{&unit};ViscidusSummonGlobs summon;
 for(float hp:{0.f,5.f,49.f,50.f,95.f,99.99f,100.f}){
  unit.hp=hp;unit.casts.clear();summon.OnEffectExecute(&spell,EFFECT_INDEX_0);
  unsigned expected=std::min(20u,unsigned(std::floor(hp/5))+1);assert(unit.casts.size()==expected*2);
  for(unsigned i=0;i<expected;++i){assert(unit.casts[i*2]==25865+i);assert(unit.casts[i*2+1]==27934);}
 }
 unit.fail=true;unit.casts.clear();summon.OnEffectExecute(&spell,EFFECT_INDEX_0);assert(unit.casts.size()==20);unit.fail=false;
 unit.casts.clear();summon.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(unit.casts.empty());spell.target=nullptr;summon.OnEffectExecute(&spell,EFFECT_INDEX_0);
 Creature boss,one,two;one.guid=1;two.guid=2;boss_viscidusAI ai;ai.m_creature=&boss;
 ai.m_aliveGlobs=10;ai.m_lGlobesGuidList={9,10};ai.HandleExplode();
 assert(ai.waves==1&&ai.m_aliveGlobs==1&&ai.m_lGlobesGuidList==GuidList{1});
 ai.JustSummoned(&two);assert(ai.m_aliveGlobs==2&&ai.m_lGlobesGuidList.size()==2);
 ai.m_phase=PHASE_EXPLODED;ai.SummonedCreatureJustDied(&one);assert(ai.m_aliveGlobs==1&&ai.phaseChanges==0);
 ai.SummonedCreatureJustDied(&one);assert(ai.m_aliveGlobs==1); // Duplicate death cannot underflow or alter surviving count.
 ai.SummonedMovementInform(&one,POINT_MOTION_TYPE,1);assert(one.casts.empty()); // Death then stale arrival.
 ai.SummonedMovementInform(&two,POINT_MOTION_TYPE,0);assert(two.casts.empty());
 ai.SummonedMovementInform(&two,POINT_MOTION_TYPE,1);assert(two.casts.size()==1&&two.despawns==1&&ai.m_aliveGlobs==1&&ai.phaseChanges==1);
 ai.SummonedMovementInform(&two,POINT_MOTION_TYPE,1);ai.SummonedCreatureJustDied(&two);
 assert(two.casts.size()==1&&ai.m_aliveGlobs==1&&ai.phaseChanges==1); // Rejoined glob remains a survivor.
 ai.Reset();assert(ai.m_aliveGlobs==0&&ai.m_lGlobesGuidList.empty());ai.SummonedCreatureJustDied(&two);assert(ai.m_aliveGlobs==0);
 ai.m_phase=PHASE_EXPLODED;ai.JustSummoned(&one);ai.SummonedCreatureJustDied(&one);assert(ai.m_aliveGlobs==0&&ai.m_phase==PHASE_REJOIN);
 std::cout<<"PASS: native Viscidus bounded summons, one wave, callback idempotence and reset\n";
}
'''
for era in ('classic','tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/temple_of_ahnqiraj/boss_viscidus.cpp').read_text()
    ai_source=block(source,'struct boss_viscidusAI')
    methods='\n'.join(block(ai_source,start).replace(' override','') for start in (
        'void Reset()', 'void JustSummoned(', 'void SummonedCreatureJustDied(', 'void SummonedMovementInform(', 'void HandleExplode()'))
    spell_list=re.search(r'auiGlobSummonSpells\[MAX_VISCIDUS_GLOBS\]\s*=\s*\{([^}]+)',source)[1]
    code=fixture.replace('__METHODS__',methods).replace('__SPELLS__',spell_list).replace('__SUMMON__',block(source,'struct ViscidusSummonGlobs'))
    with tempfile.TemporaryDirectory(prefix=f'mantech-viscidus-{era}-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
