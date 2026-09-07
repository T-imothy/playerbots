"""Execute native Hellfire death-count and repeated setup paths in both cores."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <vector>
#include <list>
#include <map>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;using ObjectGuid=unsigned;
using GuidVector=std::vector<ObjectGuid>;using GuidList=std::list<ObjectGuid>;
enum{NETHEKURSE_PEON_RP_CD,NETHEKURSE_TAUNT_PEONS,NETHEKURSE_START_FIGHT,
REACT_AGGRESSIVE,EMOTE_STATE_APPLAUD,SAY_PEON_DIE_1,SAY_PEON_DIE_2,SAY_PEON_DIE_3,
SPELL_EVOCATION,KELIDAN_SETUP_ADDS,UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE,
UNIT_FLAG_IMMUNE_TO_NPC,AI_EVENT_CUSTOM_A};
unsigned urand(unsigned lo,unsigned){return lo;}
struct Creature;
struct Motion {void PauseWaypoints(unsigned){}};
struct Combat {bool evading=false;bool IsEvadingHome(){return evading;}};
struct AddAI {unsigned events=0;void SendAIEvent(unsigned,Creature*,Creature*){++events;}};
struct Creature {unsigned guid=0;bool alive=true;Motion motion;Combat combat;AddAI ai;
 Motion*GetMotionMaster(){return &motion;}void SetFacingTo(float){}void HandleEmoteState(unsigned){}
 float GetAngle(Creature*other){return float(other->guid);}unsigned GetObjectGuid(){return guid;}
 Combat&GetCombatManager(){return combat;}bool IsAlive(){return alive;}void Respawn(){alive=true;}
 AddAI*AI(){return &ai;}void SetFlag(unsigned,unsigned){}
};
using CreatureList=std::list<Creature*>;
struct Instance{Instance*instance=this;GuidList guids;std::map<unsigned,Creature*> creatures;
 void GetKelidanAddList(GuidList&out){out=guids;}
 Creature*GetCreature(unsigned guid){auto i=creatures.find(guid);return i==creatures.end()?nullptr:i->second;}
};
struct CombatAI{void Reset(){}};
struct Nethekurse:CombatAI{Creature*m_creature;uint8 m_peonKilledCount=0;bool m_peonRPCD=false;
 unsigned lines=0,starts=0,react=0;std::map<unsigned,unsigned> timers;
 void DoBroadcastText(unsigned,Creature*){++lines;}void SetCombatMovement(bool){}
 void ResetTimer(unsigned timer,unsigned delay){timers[timer]=delay;if(timer==NETHEKURSE_START_FIGHT)++starts;}
 void DisableTimer(unsigned timer){timers.erase(timer);}void SetReactState(unsigned state){react=state;}
 __NETHEKURSE__
 __RESET__
};
struct Kelidan{Creature*m_creature;Instance*m_instance;GuidVector m_vAddGuids;uint8 m_uiKilledAdds=0;
 std::map<unsigned,unsigned>timers;void DoCastSpellIfCan(void*,unsigned){}
 void ResetTimer(unsigned timer,unsigned delay){timers[timer]=delay;}
 __KELIDAN__
};
int main(){
 Creature boss;
 for(bool alreadyTalking:{false,true}){
  Nethekurse ai{};ai.m_creature=&boss;ai.m_peonRPCD=alreadyTalking;
  for(unsigned i=0;i<4;++i)ai.DoYellForPeonDeath();
  assert(ai.m_peonKilledCount==4&&ai.starts==1&&ai.react==REACT_AGGRESSIVE);
  assert(ai.lines==(alreadyTalking?0u:1u));assert(ai.timers[NETHEKURSE_START_FIGHT]==4000);
  ai.DoYellForPeonDeath();assert(ai.starts==1&&ai.m_peonKilledCount==4);
  ai.Reset();assert(ai.m_peonKilledCount==0&&!ai.m_peonRPCD);
 }
 Instance instance;Creature adds[5];
 for(unsigned i=0;i<5;++i){adds[i].guid=i+1;instance.guids.push_back(i+1);instance.creatures[i+1]=&adds[i];}
 Kelidan ai{&boss,&instance};
 for(unsigned reset=0;reset<100;++reset){
  ai.m_uiKilledAdds=4;ai.DoSetupAdds();assert(ai.m_vAddGuids.size()==5&&ai.m_uiKilledAdds==0);
  for(unsigned i=0;i<5;++i)assert(ai.m_vAddGuids[i]==i+1&&adds[i].ai.events==reset+1);
 }
 adds[0].combat.evading=true;ai.DoSetupAdds();assert(ai.m_vAddGuids.size()==5&&ai.timers[KELIDAN_SETUP_ADDS]==3000);
 adds[0].combat.evading=false;adds[0].alive=false;ai.DoSetupAdds();assert(adds[0].alive&&ai.m_vAddGuids.size()==5);
 instance.guids.clear();ai.DoSetupAdds();assert(ai.m_vAddGuids.empty());
 ai.m_instance=nullptr;ai.DoSetupAdds();
 std::cout<<"PASS: peon deaths during dialogue, cooldown reset, 100 channeler resets and evade retry\n";
}
'''
for era in ('tbc','wotlk'):
    scripts=root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/hellfire_citadel'
    n=(scripts/'shattered_halls/boss_nethekurse.cpp').read_text()
    k=(scripts/'blood_furnace/boss_kelidan_the_breaker.cpp').read_text()
    code=fixture.replace('__NETHEKURSE__',block(n,'void DoYellForPeonDeath(')).replace('__RESET__',block(n,'void Reset(').replace(' override','')).replace('__KELIDAN__',block(k,'void DoSetupAdds('))
    assert 'if (!legionnaire->IsAlive())\n                        continue;' in n
    with tempfile.TemporaryDirectory(prefix='hellfire-reset-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
