"""Compile actual raid registration and activation under every era macro."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
actions = (root / 'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
generic = (root / 'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
bwl = (root / 'playerbot/strategy/generic/BlackwingLairDungeonStrategies.cpp').read_text()
parts = '\n'.join(block(source, 'void ' + cls + '::' + method + '(')
    for source, cls in ((generic, 'DungeonStrategy'), (bwl, 'BlackwingLairDungeonStrategy'))
    for method in ('InitCombatTriggers', 'InitReactionTriggers', 'InitNonCombatTriggers'))
code = r'''
#include <cassert>
#include <list>
#include <string>
#include <map>
#include <iostream>
#include "__POLICY__"
using namespace ai;
constexpr float ACTION_EMERGENCY=100, ACTION_MOVE=50, ACTION_DISPEL=40, ACTION_HIGH=30;
struct NextAction { std::string name; float priority; NextAction(const char* n,float p):name(n),priority(p){}
 static NextAction* array(int,NextAction* a,void*){return a;} };
struct TriggerNode {std::string name;NextAction* action;TriggerNode(const char*n,NextAction*a):name(n),action(a){} };
struct DungeonStrategy {void InitCombatTriggers(std::list<TriggerNode*>&);void InitReactionTriggers(std::list<TriggerNode*>&);void InitNonCombatTriggers(std::list<TriggerNode*>&);};
struct BlackwingLairDungeonStrategy {void InitCombatTriggers(std::list<TriggerNode*>&);void InitReactionTriggers(std::list<TriggerNode*>&);void InitNonCombatTriggers(std::list<TriggerNode*>&);};
struct Player {unsigned map=533;bool world=true,alive=true,combat=true,transfer=false,charmed=false,group=true;
 unsigned GetMapId(){return map;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charmed;}bool GetGroup(){return group;}
 float GetPositionX(){return -36;}float GetPositionY(){return -164;}float GetPositionZ(){return -90;}};
struct PlayerbotAI {Player bot;bool real=false;Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}};
struct ClassicRaidPlan {bool emergency=true;struct {int destination=0;}position;};
struct ClassicRaidPositionAction {ClassicRaidPositionAction(PlayerbotAI*){}bool isUseful(){return true;}static bool GetPlan(PlayerbotAI*,ClassicRaidPlan&){return true;}};
struct ClassicRaidCloakAction {PlayerbotAI*ai;ClassicRaidCloakAction(PlayerbotAI*a):ai(a){}bool isUseful(){return ai->bot.map==469;}};
struct ClassicRaidPauseAction {ClassicRaidPauseAction(PlayerbotAI*){}bool isUseful(){return true;}};
struct ClassicRaidTargetAction {ClassicRaidTargetAction(PlayerbotAI*){}bool isUseful(){return true;}};
struct ClassicRaidSupportAction {ClassicRaidSupportAction(PlayerbotAI*){}bool isUseful(){return true;}};
struct ClassicRaidControlAction {ClassicRaidControlAction(PlayerbotAI*){}bool isUseful(){return true;}};
struct ClassicRaidTrigger {PlayerbotAI*ai;Player*bot;std::string name;std::string getName(){return name;}bool IsActive();};
bool EncounterMovementRequired(Player*,int){return true;}
__READY__
__TRIGGER__
__REGISTRATIONS__
int main(){
 DungeonStrategy dungeon;BlackwingLairDungeonStrategy bwl;
 std::list<TriggerNode*> combat,reaction,idle;
 dungeon.InitCombatTriggers(combat);bwl.InitCombatTriggers(combat);
 dungeon.InitReactionTriggers(reaction);bwl.InitReactionTriggers(reaction);
 dungeon.InitNonCombatTriggers(idle);bwl.InitNonCombatTriggers(idle);
 auto count=[](const auto& nodes,const std::string& name){unsigned n=0;for(auto*x:nodes)if(x->name==name)++n;return n;};
 for(const char* name:{"classic raid position","classic raid support","classic raid target","classic raid control","classic raid pause","classic raid egg hazard"})assert(count(combat,name)==1);
 for(const char* name:{"classic raid emergency","classic raid pause","classic raid egg hazard"})assert(count(reaction,name)==1);
 assert(count(idle,"classic raid cloak")==1);
 PlayerbotAI ai;ClassicRaidTrigger trigger{&ai,&ai.bot,"classic raid position"};
 for(unsigned map:{249u,309u,469u,509u,531u,533u,409u,532u,631u}){
  ai.bot.map=map;
#ifdef MANGOSBOT_ZERO
  bool active=classicraid::Map(map);
#elif defined(MANGOSBOT_ONE)
  bool active=map==249||map==309||map==469||map==533;
#else
  bool active=map==309||map==469||map==533;
#endif
  assert(trigger.IsActive()==active);
 }
 ai.bot.map=469;
 for(const char*name:{"classic raid position","classic raid support","classic raid emergency","classic raid cloak"}){trigger.name=name;assert(trigger.IsActive());}
 for(const char*name:{"classic raid target","classic raid pause","classic raid control"}){trigger.name=name;
#ifdef MANGOSBOT_ZERO
 assert(trigger.IsActive());
#else
 assert(!trigger.IsActive()); // unchanged BWL action set in later eras
#endif
 }
 ai.bot.map=309;trigger.name="classic raid position";
 ai.bot.transfer=true;assert(!trigger.IsActive());ai.bot.transfer=false;
 ai.bot.group=false;assert(!trigger.IsActive());ai.bot.group=true;
 ai.bot.world=false;assert(!trigger.IsActive());ai.bot.world=true;
 ai.bot.alive=false;assert(!trigger.IsActive());ai.bot.alive=true;
 ai.bot.charmed=true;assert(!trigger.IsActive());ai.bot.charmed=false;
 ai.real=true;assert(!trigger.IsActive());
 std::cout<<"PASS native era activation, unique registration, unchanged BWL action set and lifecycle guards\n";
}
'''.replace('__POLICY__', (root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix())
code = code.replace('__READY__', block(actions, '    bool Ready('))
code = code.replace('__TRIGGER__', block(actions, 'bool ClassicRaidTrigger::IsActive('))
code = code.replace('__REGISTRATIONS__', parts)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='raid-activation-') as folder:
        p = Path(folder)
        (p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'], cwd=p, check=True)
        subprocess.run([str(p/'test.exe')], cwd=p, check=True)

for method in ('InitCombatMultipliers', 'InitReactionMultipliers'):
    assert block(generic, 'void DungeonStrategy::'+method+'(').count('new PreserveClassicRaidPlan(ai)') == 1
    assert 'PreserveClassicRaidPlan' not in block(bwl, 'void BlackwingLairDungeonStrategy::'+method+'(')
