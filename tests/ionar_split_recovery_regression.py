"""Execute native Ionar transition and callback handling with failed/partial casts."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root.parent/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/ulduar/halls_of_lightning/boss_ionar.cpp').read_text()
actor=block(source,'struct boss_ionarAI')
methods='\n'.join(block(actor,name) for name in ('void RegisterSparkAtHome(', 'bool HaveSparksReturned(', 'void UpdateAI(')).replace(' override','')
effect=block(block(source,'struct DisperseIonar'),'void OnEffectExecute(').replace(' override','')
code=r'''
#include <cassert>
#include <algorithm>
#include <list>
#include <map>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;using ObjectGuid=unsigned;using GuidList=std::list<ObjectGuid>;using SpellEffectIndex=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,VISIBILITY_ON=1,VISIBILITY_OFF=0,CHASE_MOTION_TYPE=1,
 ATTACKING_TARGET_RANDOM,CAST_INTERRUPT_PREVIOUS,SPELL_DISPERSE,SPELL_SPARK_DESPAWN,SPELL_SUMMON_SPARK,
 SPELL_STATIC_OVERLOAD_N,SPELL_STATIC_OVERLOAD_H,SPELL_BALL_LIGHTNING_N,SPELL_BALL_LIGHTNING_H,
 SAY_SPLIT_1,SAY_SPLIT_2,TRIGGERED_OLD_TRIGGERED,NPC_IONAR=28546,MAX_SPARKS=5};
unsigned urand(unsigned lo,unsigned){return lo;}
struct Unit{virtual ~Unit()=default;virtual unsigned GetEntry(){return NPC_IONAR;}virtual unsigned GetVisibility(){return VISIBILITY_ON;}
 virtual void CastSpell(Unit*,unsigned,unsigned){}virtual void AttackStop(){}virtual void SetVisibility(unsigned){}
 struct Motion{unsigned kind=CHASE_MOTION_TYPE,chases=0,expires=0;unsigned GetCurrentMovementGeneratorType(){return kind;}
  void MoveChase(Unit*){++chases;kind=CHASE_MOTION_TYPE;}void MovementExpired(){++expires;kind=0;}}motion;
 Motion*GetMotionMaster(){return &motion;}};
struct Creature;
struct Map{std::map<unsigned,Creature*>units;Creature*GetCreature(unsigned id){return units.count(id)?units[id]:nullptr;}};
struct Creature:Unit{Map*map=nullptr;bool alive=true,casting=false,hostile=true;unsigned visibility=VISIBILITY_ON,entry=NPC_IONAR,summons=0;float health=79;Unit*victim=nullptr;
 bool IsAlive(){return alive;}Map*GetMap(){return map;}bool SelectHostileTarget(){return hostile;}Unit*GetVictim(){return victim;}
 bool IsNonMeleeSpellCasted(bool){return casting;}float GetHealthPercent(){return health;}unsigned GetVisibility()override{return visibility;}
 void SetVisibility(unsigned v)override{visibility=v;}Unit*SelectAttackingTarget(unsigned,unsigned){return victim;}
 unsigned GetEntry()override{return entry;}void CastSpell(Unit*,unsigned spell,unsigned)override{assert(spell==SPELL_SUMMON_SPARK);++summons;}
 void AttackStop()override{victim=nullptr;}};
struct Spell{Unit*caster;Unit*GetCaster(){return caster;}};
struct AI{Creature*m_creature;GuidList m_lSparkGUIDList,m_lReturnedSparkGUIDList;
 bool m_bIsRegularMode=true,m_bIsDesperseCasting=false,m_bIsSplitPhase=true;
 unsigned m_uiSplitTimer=25000,m_uiStaticOverloadTimer=100000,m_uiBallLightningTimer=100000,m_uiHealthAmountModifier=1;
 unsigned result=CAST_OK,casts=0,returns=0,melee=0,emotes=0,lastSpell=0;
 unsigned DoCastSpellIfCan(Unit*,unsigned spell,unsigned=0){++casts;lastSpell=spell;
  if(result==CAST_OK&&spell==SPELL_DISPERSE)m_creature->casting=true;return result;}
 void CallBackSparks(){++returns;}void DoScriptText(unsigned,Unit*){++emotes;}void DoMeleeAttackIfReady(){++melee;}
 __METHODS__
};
struct Effect{__EFFECT__};
int main(){
 Map map;Creature boss,spark1,spark2;Unit tank;boss.map=&map;boss.victim=&tank;map.units={{1,&spark1},{2,&spark2}};
 AI ai{&boss};ai.m_lSparkGUIDList={1,2};boss.visibility=VISIBILITY_OFF;ai.m_bIsSplitPhase=false;
 assert(!ai.HaveSparksReturned());ai.RegisterSparkAtHome(99);assert(ai.m_lReturnedSparkGUIDList.empty());
 ai.RegisterSparkAtHome(1);ai.RegisterSparkAtHome(1);assert(ai.m_lReturnedSparkGUIDList.size()==1&&!ai.HaveSparksReturned());
 ai.RegisterSparkAtHome(2);assert(ai.HaveSparksReturned());
 ai.m_lReturnedSparkGUIDList.clear();spark1.alive=false;map.units.erase(2);assert(ai.HaveSparksReturned());
 spark1.alive=true;map.units[2]=&spark2;assert(!ai.HaveSparksReturned());
 ai.m_lSparkGUIDList.clear();assert(ai.HaveSparksReturned()); // All attempted summons failed.
 ai.m_lSparkGUIDList={1};ai.m_bIsSplitPhase=true;ai.RegisterSparkAtHome(1);assert(ai.m_lReturnedSparkGUIDList.empty());
 ai.m_bIsSplitPhase=false;boss.visibility=VISIBILITY_ON;ai.RegisterSparkAtHome(1);assert(ai.m_lReturnedSparkGUIDList.empty());
 // Failed cast does not consume the health threshold; successful cast does once.
 AI cast{&boss};cast.result=CAST_FAIL;cast.UpdateAI(1);assert(cast.m_uiHealthAmountModifier==1&&!cast.m_bIsDesperseCasting);
 cast.result=CAST_OK;cast.UpdateAI(1);assert(cast.m_uiHealthAmountModifier==2&&cast.m_bIsDesperseCasting&&cast.emotes==1);
 const unsigned calls=cast.casts;cast.UpdateAI(1);assert(cast.casts==calls&&cast.m_uiHealthAmountModifier==2);
 // An interrupted cast is retried at that same threshold.
 boss.casting=false;cast.result=CAST_FAIL;cast.UpdateAI(1);assert(cast.m_uiHealthAmountModifier==1&&!cast.m_bIsDesperseCasting);
 cast.result=CAST_OK;cast.UpdateAI(1);assert(cast.m_uiHealthAmountModifier==2&&cast.m_bIsDesperseCasting);
 // Actual script hides once and creates exactly one set, even if called again.
 Effect effect;Spell spell{&boss};effect.OnEffectExecute(&spell,0);assert(boss.visibility==VISIBILITY_OFF&&boss.summons==MAX_SPARKS);
 effect.OnEffectExecute(&spell,0);assert(boss.summons==MAX_SPARKS);boss.victim=&tank;boss.casting=false;
 // One successful summon, rather than five, is the complete returning set.
 AI merge{&boss};merge.m_bIsSplitPhase=false;merge.m_bIsDesperseCasting=true;merge.m_uiHealthAmountModifier=2;
 merge.m_lSparkGUIDList={1};merge.RegisterSparkAtHome(1);merge.m_uiSplitTimer=0;
 merge.result=CAST_FAIL;merge.UpdateAI(1);assert(boss.visibility==VISIBILITY_OFF&&merge.m_bIsDesperseCasting);
 merge.result=CAST_OK;merge.UpdateAI(2501);assert(boss.visibility==VISIBILITY_ON&&!merge.m_bIsDesperseCasting&&merge.m_bIsSplitPhase);
 assert(merge.m_uiHealthAmountModifier==2&&merge.lastSpell==SPELL_SPARK_DESPAWN);
 boss.health=59;merge.UpdateAI(1);assert(merge.m_uiHealthAmountModifier==3); // Next threshold still works.
 std::cout<<"PASS: Ionar native partial summons, duplicate/foreign callbacks, cast failure, interruption and merge retries\n";
}
'''.replace('__METHODS__',methods).replace('__EFFECT__',effect)
with tempfile.TemporaryDirectory(prefix='ionar-split-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
assert 'RegisterSparkAtHome(m_creature->GetObjectGuid())' in source
assert 'm_lReturnedSparkGUIDList.clear()' in block(actor,'void DespawnSpark(')
assert 'm_lReturnedSparkGUIDList.clear()' in block(actor,'void Reset(')
