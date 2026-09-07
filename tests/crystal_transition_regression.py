"""Execute native Selin approach geometry and Kalithresh missing-distiller transition."""
from pathlib import Path
import subprocess, tempfile, sys
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
selected=sys.argv[1] if len(sys.argv)>1 else 'all'
assert selected in ('all','selin','kalithresh')
for era in ('tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior'
    scripts=core/'src/game/AI/ScriptDevAI/scripts'
    selin=(scripts/'eastern_kingdoms/magisters_terrace/boss_selin_fireheart.cpp').read_text()
    kalithresh=(scripts/'outland/coilfang_reservoir/steam_vault/boss_warlord_kalithresh.cpp').read_text()
    contact=block((core/'src/game/Entities/Object.h').read_text(),'inline void GetContactPoint(')
    code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr float CONTACT_DISTANCE=0.5f,INTERACTION_DISTANCE=5;
enum{NPC_FEL_CRYSTAL=1,NPC_NAGA_DISTILLER=2,SAY_DRAIN_1=3,SAY_DRAIN_2=4,SAY_REGEN=5,
 POINT_CRYSTAL=6,POINT_MOVE_DISTILLER=7,FORCED_MOVEMENT_RUN=8,WARLORD_KALITHRESH_ACTION_WARLORDS_RAGE=9};
unsigned urand(unsigned a,unsigned){return a;}
struct WorldObject {
 float x=0,y=0,z=0;
 float GetObjectBoundingRadius()const{return 1;}
 float GetAngle(const WorldObject*other)const{return std::atan2(other->y-y,other->x-x);}
 void GetNearPoint(const WorldObject*,float&px,float&py,float&pz,float,float distance,float angle)const{
  px=x+std::cos(angle)*distance;py=y+std::sin(angle)*distance;pz=z;
 }
 __CONTACT__
};
struct Motion {unsigned moves=0,point=0;float x=0,y=0,z=0;
 void MovePoint(unsigned id,float px,float py,float pz,unsigned=0,bool=false){++moves;point=id;x=px;y=py;z=pz;}};
struct Creature:WorldObject {
 ObjectGuid guid=1;bool casting=false,walking=true,targetCleared=false;Motion motion;
 bool IsNonMeleeSpellCasted(bool){return casting;}ObjectGuid GetObjectGuid(){return guid;}
 Motion*GetMotionMaster(){return &motion;}void SetWalk(bool value,bool){walking=value;}
 void SetTarget(Creature*p){assert(!p);targetCleared=true;}
};
Creature*available=nullptr;unsigned searches=0,speeches=0;
Creature*GetClosestCreatureWithEntry(Creature*,unsigned entry,float range){
 assert((entry==NPC_FEL_CRYSTAL&&range==60)||(entry==NPC_NAGA_DISTILLER&&range==100));++searches;return available;
}
void DoScriptText(unsigned,Creature*){++speeches;}void DoBroadcastText(unsigned,Creature*){++speeches;}
struct Base {
 Creature*m_creature;bool scripted=false,melee=true,movement=true;unsigned timers=0;
 explicit Base(Creature*c):m_creature(c){}
 virtual void ExecuteAction(unsigned){}
 void SetCombatScriptStatus(bool v){scripted=v;}void SetMeleeEnabled(bool v){melee=v;}void SetCombatMovement(bool v){movement=v;}
 void ResetCombatAction(unsigned action,unsigned timer){assert(action==WARLORD_KALITHRESH_ACTION_WARLORDS_RAGE&&timer==40000);++timers;}
 unsigned GetSubsequentActionTimer(unsigned){return 40000;}
};
struct Selin:Base {using Base::Base;ObjectGuid m_crystalGuid=0;__SELIN__};
struct Kalithresh:Base {using Base::Base;ObjectGuid m_distillerGuid=0;__KALITHRESH__};
int main(){
#ifndef KALITHRESH_ONLY
 {
  Creature boss,crystal;crystal.x=40;crystal.y=12;crystal.z=6;crystal.guid=10;
  Selin ai(&boss);available=&crystal;searches=speeches=0;
  assert(ai.DoSelectNearestCrystal());
  assert(std::hypot(boss.motion.x-crystal.x,boss.motion.y-crystal.y)<10);
  assert(std::hypot(boss.motion.x-boss.x,boss.motion.y-boss.y)>20&&boss.motion.z==crystal.z);
  assert(ai.m_crystalGuid==10&&ai.scripted&&!ai.melee&&boss.targetCleared&&boss.motion.point==POINT_CRYSTAL);
 }
 {Creature boss;Selin ai(&boss);available=nullptr;assert(!ai.DoSelectNearestCrystal());
  assert(!ai.scripted&&ai.melee&&boss.motion.moves==0);}
 {Creature boss,crystal;boss.casting=true;Selin ai(&boss);available=&crystal;searches=0;
  assert(!ai.DoSelectNearestCrystal()&&searches==0&&!ai.scripted&&ai.melee);}
#endif
#ifndef SELIN_ONLY
 {
  Creature boss;Kalithresh ai(&boss);available=nullptr;speeches=0;
  ai.ExecuteAction(WARLORD_KALITHRESH_ACTION_WARLORDS_RAGE);
  assert(!ai.scripted&&ai.melee&&ai.movement&&boss.motion.moves==0);
  assert(ai.timers==1&&speeches==0);
  ai.ExecuteAction(999);assert(ai.timers==1);
 }
 {
  Creature boss,distiller;distiller.x=40;distiller.y=12;distiller.z=6;distiller.guid=11;
  Kalithresh ai(&boss);available=&distiller;speeches=0;
  ai.ExecuteAction(WARLORD_KALITHRESH_ACTION_WARLORDS_RAGE);
  assert(ai.scripted&&!ai.melee&&!ai.movement&&ai.timers==1&&speeches==1&&!boss.walking);
  assert(ai.m_distillerGuid==11&&boss.motion.point==POINT_MOVE_DISTILLER);
  assert(std::hypot(boss.motion.x-distiller.x,boss.motion.y-distiller.y)<10&&boss.motion.z==distiller.z);
 }
#endif
 std::cout<<"PASS: native crystal approach and missing-distiller combat continuity\n";
}
'''.replace('__CONTACT__',contact).replace('__SELIN__',block(selin,'bool DoSelectNearestCrystal(')).replace('__KALITHRESH__',block(kalithresh,'void ExecuteAction('))
    with tempfile.TemporaryDirectory(prefix=f'mantech-crystal-{era}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        flags=[] if selected=='all' else ['/D'+selected.upper()+'_ONLY']
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*flags,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
