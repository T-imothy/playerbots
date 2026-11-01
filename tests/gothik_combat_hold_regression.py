"""Keep Gothik's native gate-side plan with threat but no active boss victim."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
s=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
marker='    GameObject* GothikClosedGate('
method=block(s,marker) if marker in s else 'GameObject* GothikClosedGate(PlayerbotAI*,Unit* = nullptr){return nullptr;}'
method += '\n' + block(s,'    bool GothikCrossGateApproach(')
method += '\n' + block(s,'float PreserveGothikGate::GetValue(')
strategy=(Path(__file__).resolve().parents[1]/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for state in ('Combat','NonCombat','Reaction'):
 assert 'new PreserveGothikGate(ai)' in block(strategy,'void DungeonStrategy::Init'+state+'Multipliers(')
getplan=block(s,'bool ClassicRaidPositionAction::GetPlan(')
assert getplan.index('GothikClosedGate(ai, boss)') < getplan.index('if (!Engaged(')
multiplier=block(s,'float PreserveClassicRaidPlan::GetValue(')
assert multiplier.index('GothikCrossGateApproach(ai, action->GetTarget())') < multiplier.index('if (ReachTargetAction* reach')
code=r'''
#include <cassert>
#include <iostream>
#include <string>
enum{IN_PROGRESS=1,GO_STATE_READY=1};
struct Unit{bool world=true,alive=true,combat=true;unsigned entry=16060,instance=1;float y=-20;Unit*victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 unsigned GetEntry(){return entry;}float GetPositionY(){return y;}};
struct GameObject:Unit{unsigned state=1;unsigned GetGoState(){return state;}};
struct InstanceData{virtual ~InstanceData()=default;};
struct ScriptedInstance:InstanceData{Unit*boss=nullptr;GameObject*gate=nullptr;unsigned state=1;
 unsigned GetData(unsigned id){assert(id==7);return state;}
 Unit*GetSingleCreatureFromStorage(unsigned id,bool quiet){assert(id==16060&&quiet);return boss;}
 GameObject*GetSingleGameObjectFromStorage(unsigned id){assert(id==181170);return gate;}};
struct Map{InstanceData*data=nullptr;InstanceData*GetInstanceData(){return data;}};
struct Player:Unit{unsigned mapId=533;Map map;bool transferring=false,charmed=false,group=true;unsigned GetMapId(){return mapId;}Map*GetMap(){return &map;}
 bool IsBeingTeleported(){return transferring;}bool HasCharmer(){return charmed;}bool GetGroup(){return group;}
 bool IsInMap(Unit*u){return u&&instance==u->instance;}};
struct PlayerbotAI{Player bot;bool ready=true,real=false;Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}};
struct Action{virtual ~Action()=default;Unit*target=nullptr;std::string name;Unit*GetTarget(){return target;}std::string getName(){return name;}};
struct ReachTargetAction:Action{};struct AttackAction:Action{};
struct PreserveGothikGate{PlayerbotAI*ai;float GetValue(Action*);};
bool Ready(PlayerbotAI*ai){return ai->ready;}
bool nativeThreat=true;bool NaxxramasEncounterEngaged(Player*b,Unit*u){return nativeThreat&&u&&u->world&&u->alive&&u->combat&&b->IsInMap(u);}
__METHOD__
int main(){PlayerbotAI ai;Unit boss,wrong;GameObject gate;gate.y=0;ScriptedInstance instance;instance.boss=&boss;instance.gate=&gate;ai.bot.map.data=&instance;
 assert(!boss.victim&&GothikClosedGate(&ai,&boss)==&gate); // Native recorded condition: positive raid threat, victim cleared.
 assert(GothikClosedGate(&ai)==&gate);assert(!GothikClosedGate(&ai,&wrong));
 Unit target;target.y=20;assert(GothikCrossGateApproach(&ai,&target));
 // Recorded native gap: boss in combat, hunter not in combat, cross-side reach.
 ai.bot.combat=false;assert(GothikCrossGateApproach(&ai,&target));
 PreserveGothikGate guard{&ai};ReachTargetAction reach;reach.name="reach spell";reach.target=&target;
 AttackAction attack;attack.target=&target;Action heal;heal.name="greater heal";heal.target=&target;
#ifdef MANGOSBOT_ZERO
 assert(guard.GetValue(&reach)==0);assert(guard.GetValue(&attack)==0);
 reach.name="reach party member to heal";assert(guard.GetValue(&reach)==0);
#else
 assert(guard.GetValue(&reach)==1);assert(guard.GetValue(&attack)==1);
#endif
 assert(guard.GetValue(&heal)==1);assert(guard.GetValue(nullptr)==1);
 target.y=-10;assert(guard.GetValue(&reach)==1);target.y=20;
 gate.state=0;assert(guard.GetValue(&reach)==1);gate.state=1;
 target.y=-10;assert(!GothikCrossGateApproach(&ai,&target));
 target.y=20;target.instance=2;assert(!GothikCrossGateApproach(&ai,&target));target.instance=1;
 target.world=false;assert(!GothikCrossGateApproach(&ai,&target));target.world=true;
 target.alive=false;
#ifdef MANGOSBOT_ZERO
 assert(GothikCrossGateApproach(&ai,&target));assert(guard.GetValue(&reach)==0);
 heal.name="rebirth";assert(guard.GetValue(&heal)==1);
 target.y=-10;assert(guard.GetValue(&reach)==1);target.y=20;
 gate.state=0;assert(guard.GetValue(&reach)==1);gate.state=1;
#else
 assert(!GothikCrossGateApproach(&ai,&target));assert(guard.GetValue(&reach)==1);
#endif
 target.alive=true;
 gate.state=0;assert(!GothikCrossGateApproach(&ai,&target));gate.state=1;
 nativeThreat=false;assert(!GothikClosedGate(&ai,&boss));nativeThreat=true;
 gate.state=0;assert(!GothikClosedGate(&ai,&boss));gate.state=1;
 gate.world=false;assert(!GothikClosedGate(&ai,&boss));gate.world=true;
 gate.instance=2;assert(!GothikClosedGate(&ai,&boss));gate.instance=1;
 boss.combat=false;assert(!GothikClosedGate(&ai,&boss));boss.combat=true;
 instance.state=4;assert(!GothikClosedGate(&ai,&boss));instance.state=1;
 instance.boss=nullptr;assert(!GothikClosedGate(&ai,&boss));instance.boss=&boss;
 instance.gate=nullptr;assert(!GothikClosedGate(&ai,&boss));instance.gate=&gate;
 ai.bot.world=false;assert(!GothikClosedGate(&ai,&boss));ai.bot.world=true;
 ai.bot.alive=false;assert(!GothikClosedGate(&ai,&boss));ai.bot.alive=true;
 ai.bot.transferring=true;assert(!GothikClosedGate(&ai,&boss));ai.bot.transferring=false;
 ai.bot.charmed=true;assert(!GothikClosedGate(&ai,&boss));ai.bot.charmed=false;
 ai.bot.group=false;assert(!GothikClosedGate(&ai,&boss));ai.bot.group=true;
 ai.real=true;assert(!GothikClosedGate(&ai,&boss));ai.real=false;
 for(unsigned m:{0u,409u,469u,489u}){ai.bot.mapId=m;assert(!GothikClosedGate(&ai,&boss));}ai.bot.mapId=533;
 std::cout<<"PASS closed native Gothik gate with victimless boss, threat ownership, reset/open/map/instance guards\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='gothik-combat-hold-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
