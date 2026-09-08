"""Run native Whitemane callbacks with rejected, interrupted and successful casts."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('classic','tbc','wotlk'):
    source=(root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/scarlet_monastery/boss_mograine_and_whitemane.cpp').read_text()
    whitemane=source[source.index('struct boss_high_inquisitor_whitemaneAI'):]
    enums=block(source,'enum\n')+';\n'+block(source,'enum WhitemaneActions')+';'
    methods='\n'.join(block(whitemane,s).replace(' override','') for s in (
        '    void HandleResurrection()', '    void HandleResurrectionCombat()',
        '    void ExecuteAction(uint32 action)'))
    code=r'''
#include <cassert>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;
enum {CAST_OK,CAST_FAIL,CAST_INTERRUPT_PREVIOUS,NOT_STARTED,IN_PROGRESS,SPECIAL,FAIL,DONE,
 TYPE_MOGRAINE_AND_WHITE_EVENT,NPC_MOGRAINE,ATTACKING_TARGET_RANDOM,SELECT_FLAG_PLAYER,FORCED_MOVEMENT_RUN};
constexpr float INTERACTION_DISTANCE=5;
__ENUMS__
unsigned urand(unsigned a,unsigned){return a;}
struct Unit{};
struct Motion{unsigned clears=0,moves=0;void Clear(){++clears;}void MovePoint(unsigned id,float,float,float,unsigned){assert(id==2);++moves;}};
struct Creature:Unit{
 bool alive=true,combat=true;float hp=50;Motion motion;unsigned stops=0,targets=0;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}float GetHealthPercent(){return hp;}
 Motion*GetMotionMaster(){return &motion;}void SetTarget(Unit*){++targets;}void AttackStop(bool){++stops;}
 void GetContactPoint(Creature*,float&x,float&y,float&z,float){x=y=z=0;}
 Unit*GetVictim(){return nullptr;}Unit*SelectAttackingTarget(unsigned,unsigned,unsigned,unsigned){return nullptr;}
};
struct Instance{unsigned state=IN_PROGRESS;Creature*mograine=nullptr;
 unsigned GetData(unsigned id){assert(id==TYPE_MOGRAINE_AND_WHITE_EVENT);return state;}
 Creature*GetSingleCreatureFromStorage(unsigned id){assert(id==NPC_MOGRAINE);return mograine;}
};
unsigned texts=0;void DoScriptText(int,Creature*){++texts;}
struct Boss{
 Instance*m_instance;Creature*m_creature;bool script=true,movement=false,melee=false,preventDeath=true;
 unsigned result=CAST_OK,casts=0,lastSpell=0;std::map<unsigned,unsigned>timers,combatTimers;std::set<unsigned>disabled;
 bool GetCombatScriptStatus(){return script;}void SetCombatScriptStatus(bool v){script=v;}
 void SetCombatMovement(bool v,bool=false){movement=v;}void SetMeleeEnabled(bool v){melee=v;}void SetDeathPrevention(bool v){preventDeath=v;}
 unsigned DoCastSpellIfCan(Unit*,unsigned spell,unsigned=0){++casts;lastSpell=spell;return result;}
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}void ResetCombatAction(unsigned id,unsigned delay){combatTimers[id]=delay;}
 void DisableCombatAction(unsigned id){disabled.insert(id);}unsigned GetSubsequentActionTimer(unsigned){return 100;}
 Unit*DoSelectLowestHpFriendly(float){return nullptr;}
 __METHODS__
};
int main(){
 Creature white,mograine;Instance instance;instance.mograine=&mograine;Boss boss{&instance,&white};
 // Failure leaves the normal phase/action ready, including absent target/instance.
 boss.script=false;boss.movement=boss.melee=true;boss.result=CAST_FAIL;
 boss.ExecuteAction(WHITEMANE_ACTION_DEEP_SLEEP);
 assert(!boss.script&&boss.movement&&boss.melee&&boss.disabled.empty()&&!white.motion.moves);
 boss.result=CAST_OK;instance.mograine=nullptr;unsigned casts=boss.casts;
 boss.ExecuteAction(WHITEMANE_ACTION_DEEP_SLEEP);assert(boss.casts==casts&&!boss.script);
 boss.m_instance=nullptr;boss.ExecuteAction(WHITEMANE_ACTION_DEEP_SLEEP);assert(boss.casts==casts);
 boss.m_instance=&instance;instance.mograine=&mograine;mograine.alive=false;
 boss.ExecuteAction(WHITEMANE_ACTION_DEEP_SLEEP);assert(boss.casts==casts);mograine.alive=true;
 boss.ExecuteAction(WHITEMANE_ACTION_DEEP_SLEEP);
 assert(boss.script&&!boss.movement&&!boss.melee&&white.motion.moves==1&&white.stops==1);
 assert(boss.disabled.count(WHITEMANE_ACTION_DEEP_SLEEP));
 // A rejected resurrection re-arms only its own one-shot timer.
 boss.result=CAST_FAIL;boss.HandleResurrection();
 assert(boss.timers.size()==1&&boss.timers.at(WHITEMANE_ACTION_SCARLET_RESURRECTION)==1000&&texts==0);
 boss.timers.clear();boss.result=CAST_OK;boss.HandleResurrection();
 assert(boss.timers.size()==2&&boss.timers.at(WHITEMANE_ACTION_SALUTE)==3400);
 assert(boss.timers.at(WHITEMANE_ACTION_SCARLET_RESURRECTION_ENTER_COMBAT)==5700&&texts==1);
 // Accepted but interrupted cast: no SPECIAL callback, so no premature phase change.
 boss.timers.clear();boss.HandleResurrectionCombat();
 assert(boss.preventDeath&&boss.script&&boss.combatTimers.empty());
 assert(boss.timers.at(WHITEMANE_ACTION_SCARLET_RESURRECTION)==1000);
 instance.state=SPECIAL;boss.HandleResurrectionCombat();
 assert(!boss.preventDeath&&!boss.script&&boss.movement&&boss.melee&&boss.combatTimers.size()==4);
 // Delayed callbacks after wipe, death, combat end or completed transition do nothing.
 for(unsigned state:{NOT_STARTED,FAIL,DONE}){
  instance.state=state;boss.script=true;boss.timers.clear();casts=boss.casts;
  boss.HandleResurrection();boss.HandleResurrectionCombat();assert(boss.timers.empty()&&boss.casts==casts);
 }
 instance.state=IN_PROGRESS;
 for(unsigned mode=0;mode<4;++mode){
  boss.m_instance=mode==0?nullptr:&instance;white.alive=mode!=1;white.combat=mode!=2;boss.script=mode!=3;
  boss.timers.clear();casts=boss.casts;boss.HandleResurrection();boss.HandleResurrectionCombat();
  assert(boss.timers.empty()&&boss.casts==casts);
 }
 std::cout<<"PASS: Whitemane rejected sleep/resurrection, interrupted cast, completion and stale callbacks\n";
}
'''.replace('__ENUMS__',enums).replace('__METHODS__',methods)
    with tempfile.TemporaryDirectory(prefix='whitemane-recovery-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
