"""Run the native LK phase dispatcher at transitions, retries and victim loss."""
from pathlib import Path
import re,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/icecrown_citadel/boss_the_lich_king.cpp').read_text(encoding='utf-8')
constants=source[source.index('enum\n'):source.index('struct boss_the_lich_king_iccAI')]
members='\n'.join(re.findall(r'    uint32 m_\w+;',source))
methods='\n'.join(block(source,s).replace(' override','') for s in ('    void Reset()', '    void MovementInform(', '    void UpdateAI('))
code=r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32=unsigned;
enum {POINT_MOTION_TYPE=1,MINUTE=60,IN_MILLISECONDS=1000,CAST_OK=0,CAST_TRIGGERED=1,ATTACKING_TARGET_RANDOM=0,SELECT_FLAG_PLAYER=1};
unsigned urand(unsigned a,unsigned){return a;}
__CONSTANTS__
struct Unit{};struct Motion{unsigned points=0,chases=0,clears=0;void Clear(){++clears;}void MovePoint(unsigned,float,float,float){++points;}void MoveChase(Unit*p){assert(p);++chases;}};
struct Creature:Unit{bool alive=true;float hp=100;Unit*victim=nullptr;Motion motion;unsigned stops=0;
 bool IsAlive(){return alive;}bool SelectHostileTarget(){return victim!=nullptr;}Unit*GetVictim(){return victim;}
 float GetHealthPercent(){return hp;}Motion*GetMotionMaster(){return &motion;}void StopMoving(){++stops;}
 Unit*SelectAttackingTarget(unsigned,unsigned,unsigned,unsigned){return victim;}};
struct Instance{bool heroic=true;bool IsHeroicDifficulty(){return heroic;}};
void DoScriptText(int,Creature*){}
struct Boss{Creature*m_creature;Instance*m_pInstance;bool moving=true;unsigned melee=0,fail=0;std::map<unsigned,unsigned>casts;
 __MEMBERS__
 void SetCombatMovement(bool value){moving=value;}void DoMeleeAttackIfReady(){++melee;}
 unsigned DoCastSpellIfCan(Unit*,unsigned id,unsigned=0){++casts[id];return id==fail?1:CAST_OK;}
 __METHODS__
};
int main(){
 Creature c;Unit victim;c.victim=&victim;Instance instance;Boss b;b.m_creature=&c;b.m_pInstance=&instance;
 b.Reset();assert(b.moving&&b.m_uiPhaseTimer==0&&b.m_uiFrostmournePhaseTimer==0);
 // Neither transition can execute old-phase spells or melee after movement begins.
 for(unsigned phase:{PHASE_ONE,PHASE_TWO}){
  b.Reset();b.m_uiPhase=phase;c.hp=phase==PHASE_ONE?70:40;b.m_uiSoulReaperTimer=0;b.m_uiInfestTimer=0;b.m_uiNecroticPlagueTimer=0;
  b.casts.clear();unsigned melee=b.melee;b.UpdateAI(1);
  assert(b.m_uiPhase==(phase==PHASE_ONE?PHASE_RUNNING_WINTER_ONE:PHASE_RUNNING_WINTER_TWO)&&!b.moving&&b.casts.empty()&&b.melee==melee);
 }
 // Quake success ends the old dispatch immediately, including triggered Raging Spirit.
 b.Reset();c.hp=100;b.m_uiPhase=PHASE_TRANSITION_ONE;b.m_uiPhaseTimer=0;b.m_uiRagingSpiritTimer=0;b.casts.clear();
 b.UpdateAI(1);assert(b.m_uiPhase==PHASE_QUAKE_ONE&&b.casts[SPELL_QUAKE]==1&&b.casts[SPELL_RAGING_SPIRIT]==0);
 b.moving=false;b.m_uiPhaseTimer=0;b.UpdateAI(1);assert(b.m_uiPhase==PHASE_TWO&&b.moving&&c.motion.chases==1);
 b.Reset();b.m_uiPhase=PHASE_TRANSITION_TWO;b.m_uiPhaseTimer=0;b.fail=SPELL_QUAKE;b.UpdateAI(1);assert(b.m_uiPhase==PHASE_TRANSITION_TWO);
 b.fail=0;b.UpdateAI(1);assert(b.m_uiPhase==PHASE_QUAKE_TWO);b.m_uiPhaseTimer=0;b.UpdateAI(1);assert(b.m_uiPhase==PHASE_THREE&&b.moving);
 // Entering heroic Harvest cannot also cast Vile Spirits or swing in that update.
 for(bool heroic:{false,true}){
  b.Reset();instance.heroic=heroic;b.m_uiPhase=PHASE_THREE;c.hp=30;
  b.m_uiHarvestSoulTimer=0;b.m_uiVileSpiritsTimer=0;b.casts.clear();unsigned melee=b.melee;
  b.UpdateAI(1);
  assert(b.casts[heroic?SPELL_HARVEST_SOULS:SPELL_HARVEST_SOUL]==1);
  if(heroic){assert(b.m_uiPhase==PHASE_IN_FROSTMOURNE&&!b.moving&&b.melee==melee&&b.casts[SPELL_VILE_SPIRITS]==0&&b.m_uiVileSpiritsTimer==0);}
  else assert(b.m_uiPhase==PHASE_THREE&&b.casts[SPELL_VILE_SPIRITS]==1);
 }
 instance.heroic=true;
 // Heroic realm hold must expire even when every local victim has disappeared.
 b.Reset();b.m_uiPhase=PHASE_IN_FROSTMOURNE;b.moving=false;b.m_uiFrostmournePhaseTimer=47000;c.victim=nullptr;
 for(unsigned i=0;i<48;++i)b.UpdateAI(1000);
 assert(b.m_uiPhase==PHASE_THREE&&b.moving);
 // Ordinary ground phases retain the victim requirement and cannot cast blind.
 b.casts.clear();b.m_uiSoulReaperTimer=0;b.UpdateAI(1000);assert(b.casts.empty());
 // Late movement callbacks cannot restart a phase after the creature dies.
 c.alive=false;b.m_uiPhase=PHASE_RUNNING_WINTER_ONE;b.MovementInform(POINT_MOTION_TYPE,POINT_CENTER_LAND);assert(b.m_uiPhase==PHASE_RUNNING_WINTER_ONE);
 c.alive=true;b.MovementInform(POINT_MOTION_TYPE,POINT_CENTER_LAND);assert(b.m_uiPhase==PHASE_TRANSITION_ONE);
 b.moving=false;b.Reset();assert(b.moving&&b.m_uiPhase==PHASE_INTRO);
 std::cout<<"PASS native LK phase exclusivity, failed Quake retry, movement reset, missing-victim realm timer and dead callback guard\n";
}
'''.replace('__CONSTANTS__',constants).replace('__MEMBERS__',members).replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='lich-king-phase-') as td:
 p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
