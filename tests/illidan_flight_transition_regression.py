"""Execute native lift-off stages against absent targets and failed glaive casts."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <vector>
#include <list>
#include <map>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;using GuidVector=std::vector<ObjectGuid>;
enum{CAST_OK=0,CAST_FAIL,CAST_TRIGGERED,PHASETRANSITION_LIFTOFF,PHASETRANSITION_NONE,
PHASE_2_FLIGHT,ILLIDAN_ACTION_PHASE_TRANSITION,EMOTE_ONESHOT_LIFTOFF,
UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE,SAY_TAKEOFF,DIST_CALC_NONE,
POINT_ILLIDAN_FLIGHT,POINT_ILLIDAN_FLIGHT_RANDOM,FORCED_MOVEMENT_RUN,
SPELL_THROW_GLAIVE_VISUAL,SPELL_THROW_GLAIVE,EQUIP_UNEQUIP,EQUIP_NO_CHANGE};
unsigned urand(unsigned lo,unsigned){return lo;}
struct Position{float x=0,y=0,z=0;};Position illidanFlightPos[4];
struct Creature;struct Map{std::map<unsigned,Creature*>actors;
 Creature*GetCreature(unsigned id){auto i=actors.find(id);return i==actors.end()?nullptr:i->second;}};
struct Motion{unsigned moves=0;void Clear(bool,bool){}void MoveIdle(){}
 void MovePoint(unsigned,float,float,float,unsigned){++moves;}};
struct Creature{Map*map;Motion motion;float distance=1;
 Map*GetMap(){return map;}Motion*GetMotionMaster(){return &motion;}
 float GetDistance(Creature*,bool,unsigned){return distance;}void GetPosition(float&x,float&y,float&z){x=y=z=0;}
 void RemoveAllAuras(){}void HandleEmote(unsigned){}void SetLevitate(bool){}void SetHover(bool){}
 void SetFacingTo(float){}void SetTarget(void*){}void SetFlag(unsigned,unsigned){}
};
struct Instance{GuidVector lower,targets;GuidVector&GetIllidanTriggersLower(){return lower;}
 void GetGlaiveTargetGuidVector(GuidVector&out){out=targets;}};
struct AI{Creature*m_creature;Instance*m_instance;unsigned m_phaseTransitionStage=2,m_currentTransition=PHASETRANSITION_LIFTOFF,m_phase=0,m_curEyeBlastLoc=0;
 std::map<unsigned,unsigned>timers;bool fail=false;unsigned casts=0,equipment=0,prepared=0;
 void ResetTimer(unsigned id,unsigned ms){timers[id]=ms;}void SetCombatMovement(bool){}void SetMeleeEnabled(bool){}
 void DoScriptText(unsigned,Creature*){}unsigned DoCastSpellIfCan(Creature*,unsigned,unsigned=0){++casts;return fail?CAST_FAIL:CAST_OK;}
 void SetEquipmentSlots(bool,unsigned,unsigned,unsigned){++equipment;}void PreparePhaseTimers(){++prepared;}
 void HandlePhaseTransition(){unsigned nextTimer=0;switch(m_currentTransition){__LIFTOFF__}
 if(nextTimer)ResetTimer(ILLIDAN_ACTION_PHASE_TRANSITION,nextTimer);}
};
int main(){
 Map map;Creature boss{&map},near{&map},far{&map};near.distance=1;far.distance=5;Instance instance;
 AI ai{&boss,&instance};
 ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==2&&ai.timers[ILLIDAN_ACTION_PHASE_TRANSITION]==1000&&boss.motion.moves==0);
 instance.lower={1,2};ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==2&&boss.motion.moves==0);
 map.actors[1]=&far;map.actors[2]=&near;ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==3&&boss.motion.moves==1);
 ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==3&&ai.casts==0); // Empty target vector.
 instance.targets={9};ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==3&&ai.casts==0); // Unloaded target.
 map.actors[9]=&near;ai.fail=true;ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==3&&ai.casts==1&&ai.equipment==0);
 ai.fail=false;ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==4&&ai.timers[ILLIDAN_ACTION_PHASE_TRANSITION]==2000);
 ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==4&&ai.casts==2); // Missing second target.
 instance.targets.push_back(10);ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==4&&ai.casts==2);
 map.actors[10]=&far;ai.fail=true;ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==4&&ai.equipment==0&&ai.prepared==0);
 ai.fail=false;ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==5&&ai.m_phase==PHASE_2_FLIGHT&&ai.equipment==1&&ai.prepared==1);
 ai.m_instance=nullptr;ai.m_currentTransition=PHASETRANSITION_LIFTOFF;ai.m_phaseTransitionStage=2;
 ai.HandlePhaseTransition();assert(ai.m_phaseTransitionStage==2&&ai.timers[ILLIDAN_ACTION_PHASE_TRANSITION]==1000);
 std::cout<<"PASS: Illidan missing trigger, zero/one/unloaded glaive targets and failed throw retries\n";
}
'''
for era in ('tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/black_temple/boss_illidan.cpp').read_text()
    method=block(source,'void HandlePhaseTransition(')
    code=fixture.replace('__LIFTOFF__',block(method,'case PHASETRANSITION_LIFTOFF:'))
    with tempfile.TemporaryDirectory(prefix='illidan-flight-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
