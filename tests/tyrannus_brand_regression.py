"""Execute native Brand proc routing and Rimefang handoff/recovery callbacks."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/frozen_halls/pit_of_saron/boss_scourgelord_tyrannus.cpp').read_text()
brand=block(source,'struct OverlordsBrand').replace(' override','')+';'
rime=block(source,'struct boss_rimefang_posAI')
methods='\n'.join(block(rime,s).replace(' override','') for s in ('    void Reset()', '    void ReceiveAIEvent(', '    void ExecuteAction('))
mark=block(source,'    void SpellHitTarget(').replace(' override','')
code=r'''
#include <cassert>
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
using uint32=uint32_t;using uint64=uint64_t;using int32=int32_t;
enum{EFFECT_INDEX_0,AI_EVENT_CUSTOM_A,IN_PROGRESS,TYPE_TYRANNUS,NPC_TYRANNUS=36658,NPC_RIMEFANG=36661,
 ATTACKING_TARGET_RANDOM,CAST_OK,CAST_FAILED};
enum SpellAuraProcResult{SPELL_AURA_PROC_OK,SPELL_AURA_PROC_CANT_TRIGGER};
using AIEventType=int;
__ENUM__
__RIME_ENUM__
struct ObjectGuid{unsigned value=0;void Clear(){value=0;}operator unsigned()const{return value;}};
struct SpellEntry{unsigned Id;};
struct Unit;
struct Map{std::map<unsigned,Unit*>units;Unit*GetUnit(ObjectGuid g){return units[g];}};
struct Unit{
 bool player=true,alive=true,combat=true,world=true;unsigned entry=0,instance=1,phase=1;ObjectGuid guid{1};
 Unit*victim=nullptr;Map*map=nullptr;std::set<unsigned>auras;
 bool IsPlayer(){return player;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 unsigned GetEntry(){return entry;}Unit*GetVictim(){return victim;}ObjectGuid GetObjectGuid(){return guid;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&instance==u->instance&&phase==u->phase;}
 bool HasAura(unsigned id){return auras.count(id);}Map*GetMap(){return map;}
 Unit*SelectAttackingTarget(int,int){return victim;}
};using Creature=Unit;
struct Aura{Unit*target,*caster;Unit*GetTarget(){return target;}Unit*GetCaster(){return caster;}};
struct ProcExecutionData{
 bool isVictim=false;Unit*source=nullptr;unsigned damage=100;SpellEntry*spellInfo=nullptr;bool isHeal=false;
 std::array<int32,3>basepoints{};unsigned triggeredSpellId=0;Unit*triggerTarget=nullptr;
};struct AuraScript{};
__BRAND__
struct Instance{unsigned state=IN_PROGRESS;Unit*boss=nullptr;Unit*rime=nullptr;
 unsigned GetData(unsigned){return state;}Unit*GetSingleCreatureFromStorage(unsigned id){return id==NPC_TYRANNUS?boss:rime;}};
struct CombatAI{unsigned resets=0;void Reset(){++resets;}};
unsigned announced=0;void DoScriptText(int,Unit*,Unit*){++announced;}
struct Rime:CombatAI{Unit*m_creature;Instance*m_instance;ObjectGuid m_hoarfrostTarget;bool enabled=false;
 unsigned castResult=CAST_OK,attempts=0,lastSpell=0;Unit*lastTarget=nullptr;
 unsigned DoCastSpellIfCan(Unit*t,unsigned id){++attempts;lastSpell=id;lastTarget=t;return castResult;}
 void DisableCombatAction(unsigned){enabled=false;}void ResetCombatAction(unsigned,unsigned){enabled=true;}
 __METHODS__
};
struct Boss{Instance*m_instance;unsigned events=0;Unit*lastInvoker=nullptr;
 void SendAIEvent(int,Unit*t,Unit*){++events;lastInvoker=t;}
 __MARK__
};
int main(){
 Unit player,boss,tank,other;boss.entry=NPC_TYRANNUS;boss.player=false;boss.victim=&tank;
 Aura aura{&player,&boss};OverlordsBrand script;ProcExecutionData data;data.source=&player;
 assert(script.OnCheckProc(&aura,data));assert(script.OnProc(&aura,data)==SPELL_AURA_PROC_OK);
 assert(data.triggeredSpellId==69189&&data.triggerTarget==&tank&&data.basepoints[0]==100);
 boss.victim=&other;data.damage=1;script.OnProc(&aura,data);assert(data.triggerTarget==&other&&data.basepoints[0]==1);
 data.isHeal=true;data.damage=101;script.OnProc(&aura,data);
 assert(data.triggeredSpellId==69190&&data.triggerTarget==&boss&&data.basepoints[0]==555);
 data.damage=0xffffffff;script.OnProc(&aura,data);assert(data.basepoints[0]==0x7fffffff);
 data.isHeal=false;script.OnProc(&aura,data);assert(data.basepoints[0]==0x7fffffff);
 auto rejected=[&](){assert(script.OnProc(&aura,data)==SPELL_AURA_PROC_CANT_TRIGGER);};
 data.damage=0;rejected();data.damage=100;data.isVictim=true;rejected();data.isVictim=false;
 data.source=&other;rejected();data.source=&player;
 for(unsigned id:{69189u,69190u}){SpellEntry payload{id};data.spellInfo=&payload;rejected();}data.spellInfo=nullptr;
 boss.alive=false;rejected();boss.alive=true;boss.combat=false;rejected();boss.combat=true;
 boss.world=false;rejected();boss.world=true;boss.phase=2;rejected();boss.phase=1;
 boss.instance=2;rejected();boss.instance=1;boss.entry=1;rejected();boss.entry=NPC_TYRANNUS;
 aura.caster=nullptr;rejected();aura.caster=&boss;boss.victim=nullptr;rejected();boss.victim=&tank;
 tank.alive=false;rejected();tank.alive=true;player.player=false;rejected();player.player=true;
 player.alive=false;rejected();player.alive=true;
 // Mark handoff occurs after the native hit and requires its live aura.
 Unit dragon;Map map;dragon.map=&map;map.units[1]=&player;Instance instance;instance.boss=&boss;instance.rime=&dragon;
 Boss controller{&instance};SpellEntry mark{SPELL_MARK_OF_RIMEFANG},wrong{1};
 controller.SpellHitTarget(&player,&mark);assert(controller.events==0);
 player.auras.insert(SPELL_MARK_OF_RIMEFANG);controller.SpellHitTarget(&player,&wrong);assert(controller.events==0);
 controller.SpellHitTarget(&player,&mark);assert(controller.events==1&&controller.lastInvoker==&player);
 player.alive=false;controller.SpellHitTarget(&player,&mark);assert(controller.events==1);player.alive=true;
 instance.state=0;controller.SpellHitTarget(&player,&mark);assert(controller.events==1);instance.state=IN_PROGRESS;
 Rime rime;rime.m_creature=&dragon;rime.m_instance=&instance;
 rime.ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,&player,0);assert(!rime.enabled);
 rime.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,nullptr,0);assert(!rime.enabled);
 rime.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&other,&player,0);assert(!rime.enabled);
 rime.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&player,0);assert(rime.enabled&&rime.m_hoarfrostTarget==1);
 rime.castResult=CAST_FAILED;rime.ExecuteAction(RIMEFANG_POS_HOARFROST);assert(rime.enabled&&announced==0);
 rime.castResult=CAST_OK;rime.ExecuteAction(RIMEFANG_POS_HOARFROST);
 assert(!rime.enabled&&!rime.m_hoarfrostTarget&&announced==1&&rime.lastTarget==&player);
 for(unsigned condition=0;condition<6;++condition){
  rime.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&player,0);assert(rime.enabled);unsigned attempts=rime.attempts;
  if(condition==0)map.units[1]=nullptr;
  if(condition==1)player.alive=false;
  if(condition==2)player.phase=2;
  if(condition==3)player.auras.clear();
  if(condition==4)instance.state=0;
  if(condition==5)rime.m_instance=nullptr;
  rime.ExecuteAction(RIMEFANG_POS_HOARFROST);
  assert(!rime.enabled&&!rime.m_hoarfrostTarget&&rime.attempts==attempts);
  map.units[1]=&player;player.alive=true;player.phase=1;player.auras.insert(SPELL_MARK_OF_RIMEFANG);
  instance.state=IN_PROGRESS;rime.m_instance=&instance;
 }
 rime.m_hoarfrostTarget={1};rime.Reset();assert(!rime.m_hoarfrostTarget&&rime.resets==1);
 std::cout<<"PASS: Brand damage/heal routing, tank changes, recursion/ownership/expiry guards; Mark hit, retries and stale Hoarfrost cleanup\n";
}
'''.replace('__ENUM__',block(source,'enum\n')+';').replace('__RIME_ENUM__',block(source,'enum RimefangPoSActions')+';').replace('__BRAND__',brand).replace('__METHODS__',methods).replace('__MARK__',mark)
with tempfile.TemporaryDirectory(prefix='tyrannus-brand-') as directory:
    p=Path(directory);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
