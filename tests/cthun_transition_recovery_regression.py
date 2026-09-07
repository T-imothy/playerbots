"""Actual native C'Thun callbacks preserve successful phase work and flesh slots."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <algorithm>
#include <list>
#include <set>
#include <map>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned n=0):id(n){}void Clear(){id=0;}bool IsEmpty()const{return !id;}
 bool operator==(ObjectGuid g)const{return id==g.id;}bool operator!=(ObjectGuid g)const{return id!=g.id;}};
enum{MAX_FLESH_TENTACLES=2,CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,CAST_AURA_NOT_PRESENT=4,CAST_INTERRUPT_PREVIOUS=8,
 CTHUN_FLESH_RETRY=10,CTHUN_WEAKENED_START,CTHUN_WEAKENED_END,CTHUN_EMERGE,CTHUN_CLAWTENTACLEDELAY,CTHUN_EYETENTACLEDELAY,
 SPELL_TRANSFORM=100,SPELL_CARAPACE_CTHUN,SPELL_CTHUN_VULNERABLE,SPELL_CHECK_RESET_AURA,
 SPELL_GIANT_EYE_TENTACLES_1,SPELL_SUMMON_EYE_TENTACLES_P2,SPELL_SUMMON_GIANT_HOOKS_1,SPELL_SUMMON_MOUTH_TENTACLES_1,
 NPC_FLESH_TENTACLE,UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE,REACT_PASSIVE,REACT_AGGRESSIVE,TEMPSPAWN_DEAD_DESPAWN,EMOTE_WEAKENED,IN_MILLISECONDS=1000};
__POSITIONS__;
struct Creature{unsigned guid=1,entry=0,nextGuid=100;bool alive=true,combat=true,flag=true;std::set<unsigned>auras;
 std::set<unsigned>failSlots;unsigned attempts[2]{},spawns[2]{};std::list<Creature>children;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}ObjectGuid GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}
 bool HasAura(unsigned id){return auras.count(id);}void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}
 void SetFlag(unsigned,unsigned){flag=true;}void RemoveFlag(unsigned,unsigned){flag=false;}void SetInCombatWithZone(){combat=true;}
 Creature*SummonCreature(unsigned id,float x,float,float,float,unsigned,unsigned){assert(id==NPC_FLESH_TENTACLE);
  unsigned slot=x==cthunLocations[0][0]?0:1;++attempts[slot];if(failSlots.count(slot))return nullptr;
  children.emplace_back();Creature&c=children.back();c.guid=nextGuid++;c.entry=id;++spawns[slot];return &c;}};
struct CombatAI{void Reset(){}};
struct AI:CombatAI{Creature*m_creature;uint8 m_fleshTentaclesKilled=0;ObjectGuid m_fleshTentacleGuids[2];bool m_fleshTentaclesDead[2]{};bool m_fleshWaveActive=false;
 std::list<ObjectGuid>m_playersInStomachList;std::map<unsigned,unsigned>timers,casts;std::set<unsigned>failed;unsigned emotes=0;int react=0;
 unsigned DoCastSpellIfCan(Creature*,unsigned spell,unsigned=0){++casts[spell];if(failed.count(spell))return CAST_FAIL;m_creature->auras.insert(spell);return CAST_OK;}
 void ResetTimer(unsigned id,unsigned ms){timers[id]=ms;}void DisableTimer(unsigned id){timers.erase(id);}
 void ResetCombatAction(unsigned id,unsigned ms){timers[id]=ms;}void DisableCombatAction(unsigned id){timers.erase(id);}void SetCombatMovement(bool){}void SetMeleeEnabled(bool){}
 void SetReactState(int r){react=r;}void DoBroadcastText(unsigned,Creature*){++emotes;}
 __METHODS__
};
int main(){
 for(unsigned failed:{SPELL_TRANSFORM,SPELL_CARAPACE_CTHUN}){
  Creature boss;AI ai{ };ai.m_creature=&boss;ai.failed={failed};ai.HandleEmerge();
  assert(boss.flag&&ai.timers[CTHUN_EMERGE]==1000&&ai.react!=REACT_AGGRESSIVE);
  ai.failed.clear();ai.HandleEmerge();assert(!boss.flag&&ai.react==REACT_AGGRESSIVE&&boss.HasAura(SPELL_TRANSFORM)&&boss.HasAura(SPELL_CARAPACE_CTHUN));
  assert(ai.casts[SPELL_TRANSFORM]==(failed==SPELL_TRANSFORM?2u:1u));
 }
 for(unsigned missing:{0u,1u}){
  Creature boss;AI ai{};ai.m_creature=&boss;ai.Reset();boss.failSlots={missing};ai.DoSpawnTentacles();
  assert(ai.m_fleshWaveActive&&boss.children.size()==1&&ai.timers[CTHUN_FLESH_RETRY]==1000);
  Creature*first=&boss.children.front();ai.SummonedCreatureJustDied(first);ai.SummonedCreatureJustDied(first);
  assert(ai.m_fleshTentaclesKilled==1&&ai.emotes==0);ai.SummonMissingFleshTentacles();assert(boss.children.size()==1);
  boss.failSlots.clear();ai.SummonMissingFleshTentacles();assert(boss.children.size()==2&&boss.spawns[0]==1&&boss.spawns[1]==1);
  Creature*second=&boss.children.back();Creature foreign;foreign.entry=NPC_FLESH_TENTACLE;foreign.guid=999;
  ai.SummonedCreatureJustDied(&foreign);assert(ai.m_fleshTentaclesKilled==1);
  ai.failed={SPELL_CTHUN_VULNERABLE};ai.SummonedCreatureJustDied(second);
  assert(ai.m_fleshTentaclesKilled==2&&ai.m_fleshWaveActive&&ai.timers[CTHUN_WEAKENED_START]==1000);
  ai.SummonedCreatureJustDied(second);assert(ai.m_fleshTentaclesKilled==2);
  ai.failed.clear();ai.HandleWeaken();assert(!ai.m_fleshWaveActive&&ai.emotes==1&&ai.timers[CTHUN_WEAKENED_END]==45000);
  assert(!ai.timers.count(CTHUN_FLESH_RETRY)&&!ai.timers.count(CTHUN_WEAKENED_START));
  assert(!ai.timers.count(CTHUN_CLAWTENTACLEDELAY)&&!ai.timers.count(CTHUN_EYETENTACLEDELAY));
  ai.HandleWeaken();ai.SummonedCreatureJustDied(first);assert(ai.emotes==1&&ai.m_fleshTentaclesKilled==2);
  // Ending the phase keeps an already restored carapace across a later aura failure.
  boss.auras.erase(SPELL_CTHUN_VULNERABLE);ai.failed={SPELL_CHECK_RESET_AURA};ai.HandleEndWeaken();
  assert(!ai.m_fleshWaveActive&&boss.children.size()==2&&ai.timers[CTHUN_WEAKENED_END]==1000);
  const unsigned carapace=ai.casts[SPELL_CARAPACE_CTHUN];ai.failed.clear();ai.HandleEndWeaken();
  assert(ai.m_fleshWaveActive&&boss.children.size()==4&&ai.m_fleshTentaclesKilled==0&&ai.casts[SPELL_CARAPACE_CTHUN]==carapace);
  ai.SummonedCreatureJustDied(first);assert(ai.m_fleshTentaclesKilled==0); // Previous-wave death cannot weaken the new one.
  ai.Reset();assert(!ai.m_fleshWaveActive&&!ai.m_fleshTentaclesKilled);
  for(unsigned i=0;i<2;++i)assert(ai.m_fleshTentacleGuids[i].IsEmpty()&&!ai.m_fleshTentaclesDead[i]);
  ai.SummonMissingFleshTentacles();assert(boss.children.size()==4);
  boss.alive=false;ai.HandleEmerge();ai.HandleWeaken();ai.HandleEndWeaken();assert(boss.children.size()==4);
 }
 std::cout<<"PASS: native CThun partial phases, per-slot summon retries, duplicate/old deaths and reset\n";
}
'''
for era in ('classic','tbc','wotlk'):
    p=root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/temple_of_ahnqiraj/boss_cthun.cpp'
    source=p.read_text();actor=block(source,'struct boss_cthunAI')
    names=('void Reset(', 'void SummonedCreatureJustDied(', 'void SummonMissingFleshTentacles(', 'void DoSpawnTentacles(',
           'void StopSpawningTentacles(', 'void HandleEmerge(', 'void HandleWeaken(', 'void HandleEndWeaken(')
    methods='\n'.join(block(actor,name).replace(' override','') for name in names)
    positions=block(source,'static const float cthunLocations')
    code=fixture.replace('__METHODS__',methods).replace('__POSITIONS__',positions)
    with tempfile.TemporaryDirectory(prefix='cthun-recovery-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
    assert 'AddCustomAction(CTHUN_WEAKENED_START, true, [&]() { HandleWeaken(); }, TIMER_COMBAT_COMBAT)' in actor
    assert 'AddCustomAction(CTHUN_FLESH_RETRY, true, [&]() { SummonMissingFleshTentacles(); }, TIMER_COMBAT_COMBAT)' in actor
