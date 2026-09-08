"""Run native Black Knight damage, resurrection, reset and spell callbacks."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/crusaders_coliseum/trial_of_the_champion/boss_black_knight.cpp').read_text()
methods='\n'.join(block(source,s).replace(' override','') for s in (
    '    void Reset() override','    void DamageTaken(', '    void ReceiveAIEvent(', '    void UpdateResurrection(', '    void UpdateArmy('))
effect=block(source[source.index('struct BlackKnightRes'):],'    void OnEffectExecute(').replace(' override','')
update=block(source,'    void UpdateAI(')
assert update.index('UpdateResurrection(uiDiff);')<update.index('SelectHostileTarget()')
code=r'''
#include <cassert>
#include <set>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;using AIEventType=unsigned;using DamageEffectType=unsigned;using SpellEffectIndex=unsigned;
struct SpellEntry{};
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,TRIGGERED_NONE=0,UNIT_FIELD_FLAGS=0,UNIT_FLAG_UNINTERACTIBLE=1,
 UNIT_STAND_STATE_DEAD=1,UNIT_STAND_STATE_STAND=0,AURA_STATE_HEALTHLESS_20_PERCENT=0,AURA_STATE_HEALTHLESS_35_PERCENT=1,
 AI_EVENT_CUSTOM_A=1,EQUIP_UNEQUIP=0,EQUIP_NO_CHANGE=1};
__ENUMS__
unsigned urand(unsigned a,unsigned){return a;}
struct Unit;struct FakeAI{unsigned events=0;void SendAIEvent(unsigned,Unit*,Unit*){++events;}};
struct Unit{FakeAI*ai=nullptr;FakeAI*AI(){return ai;}};
struct Creature;struct Map{Creature*GetCreature(unsigned){return nullptr;}};
struct Motion{unsigned chases=0;void Clear(){}void MoveIdle(){}void MoveChase(Unit*victim){assert(victim);++chases;}};
struct Creature:Unit{
 bool alive=true,combat=true;unsigned health=100,flags=0,stand=0,display=0;Unit*victim=nullptr;Map map;Motion motion;std::set<unsigned>auras;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}unsigned GetHealth(){return health;}unsigned GetMaxHealth(){return 100;}
 void SetHealth(unsigned v){health=v;}Map*GetMap(){return &map;}Motion*GetMotionMaster(){return &motion;}Unit*GetVictim(){return victim;}
 void SetFlag(unsigned,unsigned v){flags|=v;}void RemoveFlag(unsigned,unsigned v){flags&=~v;}void SetStandState(unsigned v){stand=v;}
 void SetDisplayId(unsigned v){display=v;}unsigned GetNativeDisplayId(){return 999;}
 bool HasAura(unsigned id){return auras.count(id);}void RemoveAllAurasOnDeath(){auras.clear();}
 void InterruptNonMeleeSpells(bool){}void StopMoving(){}void ClearComboPointHolders(){}void ClearAllReactives(){}void ModifyAuraState(unsigned,bool){}
 void CastSpell(Creature*,unsigned,unsigned){}
};
void DoScriptText(int,Creature*){}
struct Boss{
 Creature*m_creature;unsigned m_uiPhase=255,m_uiNextPhase=255,m_uiResurrectionTimer=255,m_uiArmyTimer=0,m_ghoulGuid=0;
 unsigned m_uiDeathsRespiteTimer=0,m_uiIcyTouchTimer=0,m_uiObliterateTimer=0,m_uiPlagueStrikeTimer=0,m_uiDesecrationTimer=0,
 m_uiGhoulExplodeTimer=0,m_uiDeathsBiteTimer=0,m_uiMarkedDeathTimer=0;
 unsigned casts=0,threat=0;std::set<unsigned>failed;
 unsigned DoCastSpellIfCan(Creature*,unsigned id,unsigned=0){++casts;if(failed.count(id))return CAST_FAIL;
  if(id==SPELL_FULL_HEAL)m_creature->health=100;if(id==SPELL_FEIGN_DEATH)m_creature->auras.insert(id);return CAST_OK;}
 void DoResetThreat(){++threat;}void SetEquipmentSlots(bool,unsigned=0,unsigned=0,unsigned=0){}
 __METHODS__
};
struct Spell{Unit*caster=nullptr,*target=nullptr;Unit*GetCaster(){return caster;}Unit*GetUnitTarget(){return target;}};
struct ResSpell{__EFFECT__};
int main(){
 Creature creature;Boss boss{&creature};boss.Reset();assert(boss.m_uiPhase==PHASE_DEATH_KNIGHT&&boss.m_uiNextPhase==PHASE_DEATH_KNIGHT&&!boss.m_uiResurrectionTimer);
 // Wrong/early callbacks do not consume an uninitialized next phase or reset threat.
 Unit foreign;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);assert(boss.m_uiPhase==PHASE_DEATH_KNIGHT&&boss.threat==0);
 boss.failed={SPELL_FEIGN_DEATH};unsigned damage=100;boss.DamageTaken(nullptr,damage,0,nullptr);
 assert(damage==0&&boss.m_uiPhase==PHASE_TRANSITION&&boss.m_uiNextPhase==PHASE_SKELETON&&creature.health==100);
 damage=1;boss.DamageTaken(nullptr,damage,0,nullptr);assert(damage==0); // Already-launched small hit, not just a lethal hit.
 boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&foreign,0);assert(boss.m_uiPhase==PHASE_TRANSITION);
 unsigned casts=boss.casts;boss.UpdateResurrection(5999);assert(boss.casts==casts);
 boss.UpdateResurrection(1);assert(boss.m_uiResurrectionTimer==500&&!creature.HasAura(SPELL_FEIGN_DEATH));
 boss.failed.clear();boss.UpdateResurrection(500);assert(boss.m_uiResurrectionTimer==6000&&creature.HasAura(SPELL_FEIGN_DEATH));
 casts=boss.casts;boss.UpdateResurrection(6000);assert(boss.casts==casts&&boss.m_uiResurrectionTimer==1000); // Do not restart a still-active aura.
 creature.auras.clear();boss.failed={SPELL_ARMY_OF_THE_DEAD};boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);
 assert(boss.m_uiPhase==PHASE_SKELETON&&boss.threat==1&&!boss.m_uiResurrectionTimer&&!creature.flags&&creature.motion.chases==0);
 casts=boss.casts;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);assert(boss.casts==casts&&boss.threat==1);
 assert(boss.m_uiArmyTimer==500);boss.UpdateArmy(499);assert(boss.casts==casts);boss.UpdateArmy(1);assert(boss.m_uiArmyTimer==500);
 boss.failed.clear();boss.UpdateArmy(500);assert(!boss.m_uiArmyTimer);casts=boss.casts;boss.UpdateArmy(10000);assert(boss.casts==casts);
 // A rejected initial full heal cannot release the next phase at zero health.
 boss.failed={SPELL_FULL_HEAL};damage=100;boss.DamageTaken(nullptr,damage,0,nullptr);assert(creature.health==0&&boss.m_uiPhase==PHASE_TRANSITION);
 creature.auras.clear();boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);assert(boss.m_uiPhase==PHASE_TRANSITION&&boss.m_uiResurrectionTimer==500);
 boss.failed.clear();creature.victim=&foreign;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);
 assert(boss.m_uiPhase==PHASE_GHOST&&creature.health==100&&creature.motion.chases==1);
 damage=100;boss.DamageTaken(nullptr,damage,0,nullptr);assert(damage==100); // Final death is unchanged.
 boss.Reset();casts=boss.casts;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);boss.UpdateResurrection(6000);assert(boss.casts==casts);
 boss.m_uiPhase=PHASE_TRANSITION;boss.m_uiNextPhase=PHASE_SKELETON;creature.combat=false;
 boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&creature,0);boss.UpdateResurrection(6000);assert(boss.casts==casts);
 FakeAI ai;Unit target;target.ai=&ai;Spell spell{&creature,nullptr};ResSpell script;script.OnEffectExecute(&spell,0);assert(ai.events==0);
 spell.target=&target;script.OnEffectExecute(&spell,0);assert(ai.events==1);target.ai=nullptr;script.OnEffectExecute(&spell,0);assert(ai.events==1);
 std::cout<<"PASS: Black Knight transition damage, native resurrection retry, heal failure, stale/null callbacks and final death\n";
}
'''.replace('__ENUMS__',block(source,'enum\n')+';').replace('__METHODS__',methods).replace('__EFFECT__',effect)
with tempfile.TemporaryDirectory(prefix='black-knight-resurrection-') as directory:
    path=Path(directory);(path/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
    subprocess.run([str(path/'test.exe')],cwd=path,check=True)
