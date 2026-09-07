"""Native Deathwhisper repeated pull setup and duplicate phase notification tests."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root.parent/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/icecrown_citadel/boss_lady_deathwhisper.cpp').read_text()
fixture=r'''
#include <cassert>
#include <list>
#include <vector>
#include <map>
#include <iostream>
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned n=0):id(n){}void Clear(){id=0;}operator unsigned()const{return id;}};
using GuidList=std::list<ObjectGuid>;using GuidVector=std::vector<ObjectGuid>;
enum{NPC_DEATHWHISPER_SPAWN_STALKER,SAY_PHASE_TWO,DEATHWHISPER_CULTIST_SUMMON,DEATHWHISPER_SHADOW_BOLT,
DEATHWHISPER_INSIGNIFICANCE,DEATHWHISPER_FROSTBOLT,DEATHWHISPER_FROSTBOLT_VOLLEY,DEATHWHISPER_SUMMON_SPIRIT};
bool roll_chance_i(unsigned){return true;}void script_error_log(const char*,unsigned){}
struct Unit{};struct Creature;struct Map{std::map<unsigned,Creature*>actors;Creature*GetCreature(unsigned id){auto i=actors.find(id);return i==actors.end()?nullptr:i->second;}};
struct Motion{unsigned chases=0;void Clear(bool,bool){}void MoveChase(Unit*u){assert(u);++chases;}};
struct Creature{unsigned guid=0;Map*map=nullptr;float x=0,y=0,z=0;bool alive=true,combat=true;Unit*victim=nullptr;Motion motion;
 ObjectGuid GetObjectGuid(){return guid;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 Map*GetMap(){return map;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}Unit*GetVictim(){return victim;}
 Motion*GetMotionMaster(){return &motion;}void SetWalk(bool){}};
using CreatureList=std::list<Creature*>;
struct CombatAI{void Reset(){}};
struct AI:CombatAI{Creature*m_creature;bool m_bIsPhaseOne=true,m_bIsLeftSideSummon=true,m_bIsHeroicMode=false;
 GuidList m_lCultistSpawnedGuidList;GuidVector m_vLeftStalkersGuidVector,m_vRightStalkersGuidVector;ObjectGuid m_middleStalkerGuid;
 unsigned announcements=0;std::map<unsigned,unsigned>timers;std::vector<unsigned>disabled;
 void DoScriptText(unsigned,Creature*){++announcements;}void SetCombatMovement(bool){}void SetMeleeEnabled(bool){}
 void ResetCombatAction(unsigned id,unsigned delay){timers[id]=delay;}void DisableCombatAction(unsigned id){disabled.push_back(id);}
 __METHODS__
};
int main(){
 Map map;Creature boss;boss.map=&map;Creature stalkers[7];GuidList guids;
 for(unsigned i=0;i<7;++i){stalkers[i].guid=i+1;stalkers[i].x=float(7-i);stalkers[i].y=i<3?2200.f:2230.f;stalkers[i].z=i==6?65.f:50.f;map.actors[i+1]=&stalkers[i];guids.push_back(i+1);}
 AI ai{};ai.m_creature=&boss;
 for(unsigned pull=0;pull<100;++pull){ai.DoSortSummoningStalkers(guids);assert(ai.m_vLeftStalkersGuidVector.size()==3&&ai.m_vRightStalkersGuidVector.size()==3&&unsigned(ai.m_middleStalkerGuid)==7);}
 assert(unsigned(ai.m_vLeftStalkersGuidVector[0])==3&&unsigned(ai.m_vRightStalkersGuidVector[0])==6);
 guids.clear();ai.DoSortSummoningStalkers(guids);assert(ai.m_vLeftStalkersGuidVector.empty()&&ai.m_vRightStalkersGuidVector.empty()&&!unsigned(ai.m_middleStalkerGuid));
 ai.m_lCultistSpawnedGuidList.push_back(99);ai.Reset();assert(ai.m_lCultistSpawnedGuidList.empty()&&ai.m_bIsPhaseOne);
 boss.alive=false;ai.DoStartSecondPhase();assert(ai.announcements==0&&ai.m_bIsPhaseOne);boss.alive=true;boss.combat=false;ai.DoStartSecondPhase();assert(ai.announcements==0);boss.combat=true;
 ai.DoStartSecondPhase();assert(ai.announcements==1&&!ai.m_bIsPhaseOne&&boss.motion.chases==0&&ai.timers.size()==4);
 ai.timers[DEATHWHISPER_FROSTBOLT]=123;ai.DoStartSecondPhase();assert(ai.announcements==1&&ai.timers[DEATHWHISPER_FROSTBOLT]==123);
 Unit tank;boss.victim=&tank;ai.Reset();ai.m_bIsHeroicMode=true;ai.disabled.clear();ai.DoStartSecondPhase();
 assert(boss.motion.chases==1&&ai.disabled.size()==1&&ai.disabled[0]==DEATHWHISPER_SHADOW_BOLT);
 std::cout<<"PASS: Deathwhisper 100 pull setups, empty setup/reset, phase lifecycle, missing victim and duplicate callbacks\n";
}
'''
methods='\n'.join(block(source,name).replace(' override','') for name in ('void Reset(', 'void DoSortSummoningStalkers(', 'static bool sortFromNorthToSouth(', 'void DoStartSecondPhase('))
with tempfile.TemporaryDirectory(prefix='deathwhisper-lifecycle-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(fixture.replace('__METHODS__',methods))
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
assert 'bool m_bIsHeroicMode = false;' in source and 'uint8 m_uiMindControlCount = 0;' in source
