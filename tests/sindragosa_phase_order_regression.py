"""Execute native Sindragosa update and arrival callbacks at phase boundaries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/icecrown_citadel/boss_sindragosa.cpp').read_text()
methods='\n'.join(block(source,s).replace(' override','') for s in ('    void Reset()', '    void MovementInform(', '    void UpdateAI('))
enums='\n'.join(block(source,s)+';' for s in ('enum\n','enum SindragosaPhase','enum SindragosaPoint','static const float SindragosaPosition'))
code=r'''
#include <cassert>
#include <map>
#include <vector>
#include <iostream>
using uint32=unsigned;
enum {POINT_MOTION_TYPE=1,MINUTE=60,IN_MILLISECONDS=1000,CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=1,
 ATTACKING_TARGET_RANDOM=0,SELECT_FLAG_PLAYER=1,TYPE_SINDRAGOSA=0,IN_PROGRESS=1};
const float M_PI_F=3.14159265f;
__ENUMS__
unsigned urand(unsigned a,unsigned){return a;}
struct Unit{};
enum {CURRENT_GENERIC_SPELL,SPELL_STATE_FINISHED};
struct SpellEntry{unsigned Id;};struct Spell{SpellEntry*m_spellInfo;unsigned state=2;unsigned getState()const{return state;}};
struct Motion{std::vector<unsigned>points;unsigned chases=0;void MovePoint(unsigned id,float,float,float){points.push_back(id);}
 void MoveChase(Unit*p){assert(p);++chases;}};
struct Creature:Unit{Spell*current=nullptr;Spell*GetCurrentSpell(unsigned){return current;}bool alive=true;float hp=100;Unit*victim=nullptr;Motion motion;
 bool IsAlive(){return alive;}bool SelectHostileTarget(){return victim!=nullptr;}Unit*GetVictim(){return victim;}
 Unit*SelectAttackingTarget(unsigned,unsigned,unsigned,unsigned){return victim;}
 float GetHealthPercent(){return hp;}Motion*GetMotionMaster(){return &motion;}void SetOrientation(float){}
};
struct Instance{unsigned starts=0;void SetData(unsigned,unsigned){++starts;}};
void DoScriptText(int,Creature*){}
struct Boss{
 Creature*m_creature;Instance*m_pInstance=nullptr;bool flying=false,moving=false,m_airTombPending=false;unsigned bombs=0,melee=0,fail=0;
 uint32 m_uiPhase=0,m_uiPhaseTimer=0,m_uiBerserkTimer=0,m_uiCleaveTimer=0,m_uiFrostBreathTimer=0,m_uiTailSmashTimer=0,
 m_uiIcyGripTimer=0,m_uiBlisteringColdTimer=0,m_uiUnchainedMagicTimer=0,m_uiFrostBombTimer=0,m_uiIceTombSingleTimer=0;
 std::map<unsigned,unsigned>casts;
 unsigned DoCastSpellIfCan(Unit*,unsigned id,unsigned=0){++casts[id];return id==fail?CAST_FAIL:CAST_OK;}
 void SetFlying(bool v){flying=v;}void SetCombatMovement(bool v){moving=v;}
 void DoMeleeAttackIfReady(){++melee;}void DoFrostBomb(){++bombs;}
 __METHODS__
};
int main(){
 Creature c;Unit victim;c.victim=&victim;Instance instance;Boss b;b.m_creature=&c;b.m_pInstance=&instance;
 // Grip -> delay -> retryable Cold, without intervening melee or phase changes.
 b.Reset();b.m_uiPhase=SINDRAGOSA_PHASE_GROUND;b.m_uiIcyGripTimer=0;b.UpdateAI(1);
 assert(b.m_uiBlisteringColdTimer==1000);auto melee=b.melee;
 b.UpdateAI(999);assert(b.m_uiBlisteringColdTimer==1&&b.melee==melee);
 b.fail=SPELL_BLISTERING_COLD;b.UpdateAI(1);assert(b.m_uiBlisteringColdTimer==1&&b.melee==melee);
 c.hp=30;b.fail=0;b.UpdateAI(1);assert(b.m_uiBlisteringColdTimer==0&&b.m_uiPhase==SINDRAGOSA_PHASE_GROUND);
 SpellEntry cold{SPELL_BLISTERING_COLD};Spell cast{&cold};c.current=&cast;
 for(unsigned id:{70123u,71047u,71048u,71049u}){cold.Id=id;b.UpdateAI(6000);assert(b.m_uiPhase==SINDRAGOSA_PHASE_GROUND&&b.melee==melee);}
 c.current=nullptr;b.UpdateAI(1);assert(b.m_uiPhase==SINDRAGOSA_PHASE_THREE);
 // Boundary: the same update crosses 30% and expires takeoff.
 for(unsigned tick:{1u,50u,1000u}){
  b.Reset();b.m_uiPhase=SINDRAGOSA_PHASE_GROUND;b.m_uiPhaseTimer=tick;c.hp=30;c.motion.points.clear();
  b.UpdateAI(tick);assert(b.m_uiPhase==SINDRAGOSA_PHASE_THREE&&c.motion.points.empty());
  for(unsigned point:{SINDRAGOSA_POINT_GROUND_CENTER,SINDRAGOSA_POINT_AIR_CENTER,SINDRAGOSA_POINT_AIR_PHASE_2,SINDRAGOSA_POINT_AIR_EAST,SINDRAGOSA_POINT_AIR_WEST}){
   b.MovementInform(POINT_MOTION_TYPE,point);assert(b.m_uiPhase==SINDRAGOSA_PHASE_THREE&&c.motion.points.empty());
  }
 }
 // Normal takeoff becomes a transition immediately; no additional ground attacks.
 b.Reset();c.hp=100;b.m_uiPhase=SINDRAGOSA_PHASE_GROUND;b.m_uiPhaseTimer=1;b.m_uiCleaveTimer=0;c.motion.points.clear();
 auto cleaves=b.casts[SPELL_CLEAVE];b.UpdateAI(1);assert(b.m_uiPhase==SINDRAGOSA_PHASE_FLYING_TO_AIR&&b.casts[SPELL_CLEAVE]==cleaves);
 b.UpdateAI(1000);assert(c.motion.points.size()==1);
 b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_GROUND_CENTER);assert(b.flying&&c.motion.points.back()==SINDRAGOSA_POINT_AIR_CENTER);
 b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_CENTER);assert(c.motion.points.back()==SINDRAGOSA_POINT_AIR_PHASE_2);
 b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_PHASE_2);assert(b.m_uiPhase==SINDRAGOSA_PHASE_AIR);
 auto tombs=b.casts[SPELL_ICE_TOMB];b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_PHASE_2);assert(b.casts[SPELL_ICE_TOMB]==tombs);
 // Rejected air selector retries without consuming the phase or bomb timers.
 b.fail=SPELL_ICE_TOMB;auto phaseTime=b.m_uiPhaseTimer,bombTime=b.m_uiFrostBombTimer;
 for(unsigned attempt=0;attempt<10;++attempt){b.UpdateAI(100);assert(b.m_airTombPending&&b.m_uiPhaseTimer==phaseTime&&b.m_uiFrostBombTimer==bombTime);}
 b.fail=0;b.UpdateAI(1);assert(!b.m_airTombPending);tombs=b.casts[SPELL_ICE_TOMB];b.UpdateAI(1);assert(b.casts[SPELL_ICE_TOMB]==tombs);
 b.m_uiPhaseTimer=1;b.m_uiFrostBombTimer=0;auto bombs=b.bombs;b.UpdateAI(1);
 assert(b.m_uiPhase==SINDRAGOSA_PHASE_FLYING_TO_GROUND&&b.bombs==bombs);
 b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_CENTER);b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_GROUND_CENTER);
 assert(b.m_uiPhase==SINDRAGOSA_PHASE_GROUND&&!b.flying&&b.moving);
 // Initial patrol and landing still work; dead/OOC callbacks cannot enter combat phases.
 b.Reset();c.motion.points.clear();b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_EAST);assert(c.motion.points.back()==SINDRAGOSA_POINT_AIR_WEST);
 b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_PHASE_2);assert(b.m_uiPhase==SINDRAGOSA_PHASE_OOC);
 b.m_uiPhase=SINDRAGOSA_PHASE_AGGRO;b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_CENTER);
 b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_GROUND_CENTER);assert(instance.starts==1&&b.m_uiPhase==SINDRAGOSA_PHASE_GROUND);
 c.alive=false;b.m_uiPhase=SINDRAGOSA_PHASE_FLYING_TO_AIR;b.MovementInform(POINT_MOTION_TYPE,SINDRAGOSA_POINT_AIR_PHASE_2);
 assert(b.m_uiPhase==SINDRAGOSA_PHASE_FLYING_TO_AIR);
 // Phase three uses the explicit single-target spell, and retries only that spell.
 c.alive=true;b.Reset();b.m_uiPhase=SINDRAGOSA_PHASE_THREE;b.m_uiIceTombSingleTimer=0;
 tombs=b.casts[SPELL_ICE_TOMB];auto single=b.casts[SPELL_ICE_TOMB_SINGLE];b.fail=SPELL_ICE_TOMB_SINGLE;
 b.UpdateAI(1);assert(b.m_uiIceTombSingleTimer==0&&b.casts[SPELL_ICE_TOMB_SINGLE]==single+1&&b.casts[SPELL_ICE_TOMB]==tombs);
 b.fail=0;b.UpdateAI(1);assert(b.m_uiIceTombSingleTimer==15000&&b.casts[SPELL_ICE_TOMB]==tombs);
 std::cout<<"PASS: Sindragosa final-phase/takeoff arbitration, full flight route, stale/dead arrival guards and landing bomb cutoff\n";
}
'''.replace('__ENUMS__',enums).replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='sindragosa-phase-') as directory:
    path=Path(directory);(path/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
    subprocess.run([str(path/'test.exe')],cwd=path,check=True)
