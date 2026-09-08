"""Execute Ingvar and Annhylde failure recovery and summon ownership guards."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/utgarde_keep/utgarde_keep/boss_ingvar.cpp').read_text()
enums=block(source,'enum\n')+';\n'+block(source,'enum IngvarActions')+';'
boss=source[source.index('struct boss_ingvarAI'):source.index('struct npc_annhyldeAI')]
methods='\n'.join(block(boss,s).replace(' override','') for s in ('    void DamageTaken(', '    void ReceiveAIEvent(', '    void HandleTransform()'))
ann=block(source[source.index('struct npc_annhyldeAI'):],'    void UpdateAI(').replace(' override','')
assert 'AddCustomAction(INGVAR_ACTION_TRANSFORM, true' in boss and 'HandleTransform();' in boss
code=r'''
#include <cassert>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;using AIEventType=unsigned;using DamageEffectType=unsigned;
struct SpellEntry{};
enum{CAST_OK=0,CAST_FAIL=1,SPELL_CAST_OK=255,CAST_TRIGGERED=2,CAST_AURA_NOT_PRESENT=4,TRIGGERED_OLD_TRIGGERED=8,TRIGGERED_NONE=0,
 UNIT_FIELD_FLAGS=1,UNIT_FLAG_SPAWNING=2,VIRTUAL_ITEM_SLOT_0=0,AI_EVENT_CUSTOM_A=1,AI_EVENT_CUSTOM_B=2,
 TYPE_INGVAR=1,NPC_INGVAR=23954,IN_PROGRESS=1,FAIL=2};
__ENUMS__
unsigned urand(unsigned a,unsigned){return a;}
struct Motion{unsigned moves=0;void MovePoint(unsigned,float,float,float){++moves;}};
struct Unit{unsigned entry=0,guid=0,spawner=0;
 unsigned GetEntry(){return entry;}unsigned GetSpawnerGuid(){return spawner;}unsigned GetObjectGuid(){return guid;}};
struct Creature:Unit{
 bool alive=true,combat=true;unsigned health=100,flags=0,result=SPELL_CAST_OK,casts=0,despawns=0,equipment=0;std::set<unsigned>auras;Motion motion;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}unsigned GetHealth(){return health;}
 void SetFlag(unsigned,unsigned v){flags|=v;}void RemoveFlag(unsigned,unsigned v){flags&=~v;}void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}
 void SetTarget(Unit*){}void SetVirtualItem(unsigned,unsigned){++equipment;}
 unsigned CastSpell(Unit*,unsigned,unsigned){++casts;return result;}
 void ForcedDespawn(unsigned=0){++despawns;}Motion*GetMotionMaster(){return &motion;}
 float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 10;}
};
void DoScriptText(int,Creature*){}
struct Common{Creature*m_creature;unsigned result=CAST_OK,casts=0,threatResets=0;bool script=false;
 std::map<unsigned,unsigned>timers,combatTimers;std::set<unsigned>disabled;
 unsigned DoCastSpellIfCan(Unit*,unsigned,unsigned=0){++casts;return result;}
 void SetCombatScriptStatus(bool v){script=v;}void DisableCombatAction(unsigned id){disabled.insert(id);}
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}void ResetCombatAction(unsigned id,unsigned delay){combatTimers[id]=delay;}
 void DoResetThreat(){++threatResets;}
};
struct Boss:Common{bool m_bIsResurrected=false,m_bIsFakingDeath=false,m_isRegularMode=true;__METHODS__};
struct Instance{unsigned state=IN_PROGRESS;Creature*boss=nullptr;unsigned GetData(unsigned){return state;}
 Creature*GetSingleCreatureFromStorage(unsigned id){assert(id==NPC_INGVAR);return boss;}};
Boss*recipient=nullptr;unsigned events=0;
void SendAIEvent(unsigned event,Creature*sender,Creature*target){++events;assert(target==recipient->m_creature);recipient->ReceiveAIEvent(event,sender,nullptr,0);}
struct Annhylde:Common{Instance*m_pInstance;unsigned m_uiResurrectTimer=1;uint8 m_uiResurrectPhase=0;__ANN__};
int main(){
 Creature creature,angel;creature.guid=1;creature.entry=NPC_INGVAR;angel.guid=2;angel.entry=NPC_ANNHYLDE;angel.spawner=1;
 Boss boss;boss.m_creature=&creature;recipient=&boss;
 unsigned damage=100;boss.result=CAST_FAIL;boss.DamageTaken(nullptr,damage,0,nullptr);
 assert(damage==0&&!boss.m_bIsFakingDeath&&!boss.script&&boss.disabled.empty());
 boss.result=CAST_OK;damage=100;boss.DamageTaken(nullptr,damage,0,nullptr);
 assert(damage==0&&boss.m_bIsFakingDeath&&boss.script&&boss.disabled.size()==4);
 unsigned casts=boss.casts;damage=100;boss.DamageTaken(nullptr,damage,0,nullptr);assert(damage==0&&boss.casts==casts);
 Instance instance;instance.boss=&creature;Annhylde ann;ann.m_creature=&angel;ann.m_pInstance=&instance;
 // Missing boss or failed channel keeps the current phase and a bounded retry timer.
 instance.boss=nullptr;ann.UpdateAI(1);assert(ann.m_uiResurrectPhase==0&&ann.m_uiResurrectTimer==500&&ann.casts==0);
 instance.boss=&creature;ann.result=CAST_FAIL;ann.UpdateAI(500);assert(ann.m_uiResurrectPhase==0&&ann.m_uiResurrectTimer==500);
 ann.result=CAST_OK;ann.UpdateAI(500);assert(ann.m_uiResurrectPhase==1&&ann.m_uiResurrectTimer==3000);
 for(unsigned phase:{1u,2u}){
  creature.result=1;ann.UpdateAI(10000);assert(ann.m_uiResurrectPhase==phase&&ann.m_uiResurrectTimer==500);
  creature.result=SPELL_CAST_OK;ann.UpdateAI(500);assert(ann.m_uiResurrectPhase==phase+1);
 }
 // Foreign, null or prematurely delivered callbacks cannot transform/reset threat.
 angel.spawner=99;casts=boss.casts;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_B,&angel,nullptr,0);assert(boss.casts==casts);
 boss.ReceiveAIEvent(AI_EVENT_CUSTOM_B,nullptr,nullptr,0);assert(boss.casts==casts);angel.spawner=1;
 // Transformation can retry after the helper has departed.
 boss.result=CAST_FAIL;ann.UpdateAI(10000);assert(events==1&&angel.despawns==1&&ann.m_uiResurrectTimer==0);
 assert(boss.m_bIsFakingDeath&&!boss.m_bIsResurrected&&boss.timers.at(INGVAR_ACTION_TRANSFORM)==500);
 boss.result=CAST_OK;boss.HandleTransform();assert(boss.m_bIsResurrected&&!boss.m_bIsFakingDeath&&!boss.script&&boss.threatResets==1);
 casts=boss.casts;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_B,&angel,nullptr,0);assert(boss.casts==casts&&boss.threatResets==1);
 damage=100;boss.DamageTaken(nullptr,damage,0,nullptr);assert(damage==100); // Real phase-two death remains possible.
 // Native owned axe return still re-arms abilities; another boss's axe does not.
 angel.entry=NPC_THROW_DUMMY;boss.combatTimers.clear();boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&angel,nullptr,0);assert(boss.combatTimers.size()==3);
 boss.combatTimers.clear();angel.spawner=99;boss.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&angel,nullptr,0);assert(boss.combatTimers.empty());
 // Wipe stops the helper. A late transformation timer cannot revive the encounter.
 instance.state=FAIL;ann.m_uiResurrectTimer=1;ann.UpdateAI(1);assert(ann.m_uiResurrectTimer==0&&angel.despawns==2);
 boss.m_bIsResurrected=false;boss.m_bIsFakingDeath=true;creature.combat=false;casts=boss.casts;boss.HandleTransform();assert(boss.casts==casts);
 std::cout<<"PASS: Ingvar rejected summon, helper cast/missing-boss retries, transform retry, ownership and wipe guards\n";
}
'''.replace('__ENUMS__',enums).replace('__METHODS__',methods).replace('__ANN__',ann)
with tempfile.TemporaryDirectory(prefix='ingvar-recovery-') as directory:
    path=Path(directory);(path/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
    subprocess.run([str(path/'test.exe')],cwd=path,check=True)
