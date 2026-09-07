"""Execute native Anzu wave scheduling and bird activation on poisoned storage."""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
selected=sys.argv[1] if len(sys.argv)>1 else 'all'
assert selected in ('all','waves','spirits')
for era in ('tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/auchindoun/sethekk_halls/boss_anzu.cpp').read_text()
    constants=block(source,'enum\n{')+';\n'+block(source,'enum AnzuActions')+';'
    boss=block(source,'struct boss_anzuAI')
    actions=block(boss,'void Reset() override')+'\n'+block(boss,'void ExecuteAction(uint32 i) override')
    bird=block(source,'struct npc_anzu_bird_spiritAI')+';'
    code=r'''
#include <cassert>
#include <cstring>
#include <iostream>
#include <new>
#include <vector>
using uint32=unsigned;
enum AIEventType{AI_EVENT_CUSTOM_A,AI_EVENT_CUSTOM_B,AI_EVENT_CUSTOM_C};
enum{CAST_TRIGGERED=1,CAST_AURA_NOT_PRESENT=2,CAST_OK=0,CAST_FAIL=1};
__CONSTANTS__
struct Unit{};
struct Creature:Unit{unsigned entry=0;float health=100;std::vector<unsigned>removed;
 unsigned GetEntry(){return entry;}float GetHealthPercent(){return health;}
 void RemoveAurasDueToSpell(unsigned spell){removed.push_back(spell);}};
struct ScriptedAI{Creature*m_creature;std::vector<unsigned>casts,emotes;explicit ScriptedAI(Creature*c):m_creature(c){}
 virtual void Reset(){};virtual void ReceiveAIEvent(AIEventType,Unit*,Unit*,uint32){};virtual void UpdateAI(uint32){};
 int DoCastSpellIfCan(Unit*,unsigned spell,unsigned=0){assert(spell);casts.push_back(spell);return CAST_OK;}
 void DoBroadcastText(unsigned text,Creature*){emotes.push_back(text);}};
struct CombatAI{virtual void Reset(){};virtual void ExecuteAction(uint32){};};
struct boss_anzuAI:CombatAI{Creature*m_creature;float m_healthBroodCheck=0,m_healthBanishCheck=0;
 unsigned waves=0,attempts=0,banishes=0,timers=0;bool canExecute=true,castSuccess=true,melee=true;
 explicit boss_anzuAI(Creature*c):m_creature(c){Reset();}
 bool CanExecuteCombatAction(){return canExecute;}void DoSummonBroodsOfAnzu(){++waves;}
 int DoCastSpellIfCan(Unit*,unsigned spell){assert(spell==SPELL_BANISH_SELF);++attempts;if(castSuccess){++banishes;return CAST_OK;}return CAST_FAIL;}
 void DoBroadcastText(unsigned text,Creature*){assert(text==SAY_BANISH);}
 void SetMeleeEnabled(bool value){melee=value;}
 void ResetTimer(unsigned timer,unsigned duration){assert(timer==ANZU_BROOD_ATTACK&&duration==15000);++timers;}
 __ACTIONS__
};
__BIRD__
int main(){
#ifndef SPIRITS_ONLY
 Creature boss;boss_anzuAI ai(&boss);
 assert(ai.m_healthBroodCheck==73&&ai.m_healthBanishCheck==70);
 boss.health=73;ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);assert(ai.waves==0);
 boss.health=72;ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);assert(ai.waves==1&&ai.m_healthBroodCheck==33);
 for(unsigned i=0;i<20;++i)ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);
 assert(ai.waves==1);ai.ExecuteAction(ANZU_ACTION_BANISH);assert(ai.banishes==0);
 boss.health=69;ai.castSuccess=false;
 for(unsigned i=0;i<20;++i){ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);ai.ExecuteAction(ANZU_ACTION_BANISH);}
 assert(ai.waves==1&&ai.banishes==0&&ai.m_healthBanishCheck==70);
 ai.canExecute=false;ai.castSuccess=true;unsigned attempts=ai.attempts;
 ai.ExecuteAction(ANZU_ACTION_BANISH);assert(ai.attempts==attempts);
 ai.canExecute=true;ai.ExecuteAction(ANZU_ACTION_BANISH);
 assert(ai.banishes==1&&ai.m_healthBanishCheck==30&&ai.timers==1&&!ai.melee);
 boss.health=33;ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);assert(ai.waves==1);
 boss.health=32;ai.canExecute=false;ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);assert(ai.waves==1);
 ai.canExecute=true;ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);assert(ai.waves==2&&ai.m_healthBroodCheck==-7);
 boss.health=29;ai.ExecuteAction(ANZU_ACTION_BANISH);assert(ai.banishes==2&&ai.m_healthBanishCheck==-10&&ai.timers==2);
 boss.health=1;for(unsigned i=0;i<20;++i){ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);ai.ExecuteAction(ANZU_ACTION_BANISH);}
 assert(ai.waves==2&&ai.banishes==2);
 ai.Reset();assert(ai.m_healthBroodCheck==73&&ai.m_healthBanishCheck==70);
 boss.health=72;ai.ExecuteAction(ANZU_ACTION_SPAWN_BROODS);assert(ai.waves==3);
#endif
#ifndef WAVES_ONLY
 for(unsigned entry:{NPC_HAWK_SPIRIT,NPC_FALCON_SPIRIT,NPC_EAGLE_SPIRIT}){
  Creature creature;creature.entry=entry;
  alignas(npc_anzu_bird_spiritAI) unsigned char storage[sizeof(npc_anzu_bird_spiritAI)];
  std::memset(storage,0xa5,sizeof(storage));
  auto*spirit=new(storage)npc_anzu_bird_spiritAI(&creature);
  spirit->UpdateAI(100);assert(spirit->casts.empty());
  spirit->ReceiveAIEvent(AI_EVENT_CUSTOM_B,nullptr,nullptr,0);
  assert((spirit->casts==std::vector<unsigned>{SPELL_FREEZE_ANIM,SPELL_SPIRIT_STONEFORM}));
  spirit->casts.clear();spirit->ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,nullptr,6000);
  spirit->UpdateAI(1);assert(spirit->casts==std::vector<unsigned>{spirit->GetSpellId()});
  assert((creature.removed==std::vector<unsigned>{SPELL_FREEZE_ANIM,SPELL_SPIRIT_STONEFORM}));
  spirit->UpdateAI(1999);assert(spirit->casts.size()==1);spirit->UpdateAI(1);assert(spirit->casts.size()==2);
  spirit->ReceiveAIEvent(AI_EVENT_CUSTOM_A,nullptr,nullptr,1000);assert(spirit->m_duration==3999);
  spirit->UpdateAI(3999);assert(spirit->m_duration==0&&spirit->casts.size()==4);
  assert(spirit->casts[2]==SPELL_FREEZE_ANIM&&spirit->casts[3]==SPELL_SPIRIT_STONEFORM);
  spirit->UpdateAI(5000);assert(spirit->casts.size()==4);
  spirit->~npc_anzu_bird_spiritAI();
 }
#endif
 std::cout<<"PASS: native Anzu independent wave thresholds and initialized bird pulse timing\n";
}
'''.replace('__CONSTANTS__',constants).replace('__ACTIONS__',actions).replace('__BIRD__',bird)
    with tempfile.TemporaryDirectory(prefix=f'mantech-anzu-{era}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        flags=[] if selected=='all' else ['/D'+selected.upper()+'_ONLY']
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*flags,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
