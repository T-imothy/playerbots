"""Execute the actual Classic Renataki AI vanish/return/reset callbacks."""
from pathlib import Path
import argparse,subprocess,tempfile
from behavior_regression import block
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);a=p.parse_args()
source=(a.core/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/zulgurub/boss_renataki.cpp').read_text()
code=r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <map>
using uint32=unsigned;using ObjectGuid=unsigned;using AIEventType=unsigned;
enum{AI_EVENT_CUSTOM_A=1,TRIGGERED_OLD_TRIGGERED=1,SPELL_CAST_OK=0,ATTACKING_TARGET_RANDOM=1,SELECT_FLAG_PLAYER=1};
struct Unit{unsigned guid=1,casts=0,lastSpell=0,result=0;bool alive=true,world=true,same=true;ObjectGuid GetObjectGuid(){return guid;}bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsInMap(Unit*u){return same&&u->same;}
 unsigned CastSpell(Unit*,unsigned spell,unsigned){++casts;lastSpell=spell;return result;}};
struct Map{std::map<unsigned,Unit*>units;Unit*GetUnit(unsigned g){return units[g];}};
struct Creature:Unit{Map map;Unit*fallback=nullptr;bool combat=true;unsigned removed=0;Map*GetMap(){return &map;}bool IsInCombat(){return combat;}
 Unit*SelectAttackingTarget(unsigned,unsigned,void*,unsigned){return fallback;}void RemoveAurasDueToSpell(unsigned spell){removed=spell;}};
struct CombatAI{Creature*m_creature;std::map<unsigned,std::function<void()>>callbacks;std::map<unsigned,unsigned>timers;bool scripted=false,melee=true,movement=true;
 CombatAI(Creature*c,unsigned):m_creature(c){}virtual void Reset(){}virtual void JustRespawned(){}virtual void ReceiveAIEvent(AIEventType,Unit*,Unit*,uint32){}
 void AddCustomAction(unsigned id,bool disabled,std::function<void()>f){assert(disabled);callbacks[id]=f;}void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}void DisableTimer(unsigned id){timers.erase(id);}
 void SetCombatScriptStatus(bool b){scripted=b;}void SetMeleeEnabled(bool b){melee=b;}void SetCombatMovement(bool b){movement=b;}void DoCastSpellIfCan(Unit*,unsigned){}
 void Advance(unsigned diff){auto copy=timers;for(auto row:copy){if(diff>=row.second){timers.erase(row.first);callbacks.at(row.first)();}else timers[row.first]-=diff;}}
};
'''+block(source,'enum\n')+';\n'+block(source,'enum RenatakiActions')+';\n'+block(source,'struct boss_renatakiAI')+';\n'+r'''
int main(){Creature boss;Unit target,backup;target.guid=2;backup.guid=3;boss.map.units[2]=&target;boss.fallback=&backup;boss_renatakiAI ai(&boss);ai.Reset();
 ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&target,0);
 assert(ai.scripted&&!ai.melee&&!ai.movement&&ai.timers[RENATAKI_VANISH_DELAY]==5000);
 ai.Advance(4999);assert(target.casts==0&&!ai.melee);ai.Advance(1);assert(target.casts==1&&target.lastSpell==24700&&ai.melee&&ai.movement&&!ai.scripted);
 ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&target,0);target.alive=false;ai.Advance(5000);assert(backup.casts==1&&target.casts==1);target.alive=true;
 ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&target,0);target.same=false;ai.Advance(5000);assert(backup.casts==2);target.same=true;
 ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,nullptr,0);boss.fallback=nullptr;ai.Advance(5000);assert(boss.removed==24699&&ai.melee&&!ai.scripted);
 boss.removed=0;target.result=1;ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&target,0);ai.Advance(5000);assert(boss.removed==24699&&ai.melee);target.result=0;
 ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&target,0);unsigned calls=target.casts;ai.Reset();ai.Advance(5000);assert(target.casts==calls&&ai.melee&&ai.movement&&!ai.scripted&&ai.m_vanishTarget==0);
 std::cout<<"PASS native vanish schedules return, preserves native payload, recovers missing/dead/foreign targets and cancels stale reset callback\n";
}
'''
with tempfile.TemporaryDirectory(prefix='renataki-vanish-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
