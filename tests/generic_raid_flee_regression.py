"""Native movement admission and generic flee execution across all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/actions/MovementActions.cpp').read_text()
follow=(r/'playerbot/strategy/actions/FollowActions.cpp').read_text()
for signature in ('bool FleeToMasterAction::Execute(', 'bool FleeToMasterAction::isUseful('):
 body=block(follow,signature)
 assert body.index('IsGenericRaidFleeBlocked()')<body.index('ai->')
methods='\n'.join(block(s,sig) for sig in ('bool MovementAction::IsGenericRaidFleeBlocked(', 'bool MovementAction::isPossible(', 'bool MovementAction::isUseful(', 'bool FleeAction::Execute(', 'bool FleeWithPetAction::Execute(', 'bool RunAwayAction::Execute('))
code=r'''
#include <cassert>
#include <string>
#include <iostream>
constexpr int REACT_PASSIVE=0;
struct Map{bool raid=true;bool IsRaid(){return raid;}};
struct Unit{};struct UnitAI{unsigned passive=0;void SetReactState(int){++passive;}};
struct Creature:Unit{UnitAI native;UnitAI*AI(){return &native;}};
struct Pet:Creature{unsigned stops=0;void AttackStop(){++stops;}};
struct Player{Map map;Pet pet;Map*GetMap(){return &map;}Pet*GetPet(){return &pet;}};
struct PlayerbotAI{bool move=true,stay=false;Unit target;bool CanMove(){return move;}bool HasStrategy(const char*,int){return stay;}int GetState(){return 0;}Unit*GetUnit(unsigned){return &target;}};
struct Event{};
struct MovementAction{PlayerbotAI*ai;Player*bot;std::string name;unsigned flees=0;
 std::string getName(){return name;}bool IsGenericRaidFleeBlocked();bool isPossible();bool isUseful();bool Flee(Unit*){++flees;return true;}};
struct FleeAction:MovementAction{bool Execute(Event&);};struct FleeWithPetAction:MovementAction{bool Execute(Event&);};struct RunAwayAction:MovementAction{bool Execute(Event&);};
#define AI_VALUE(type,name) 1U
__METHODS__
int main(){PlayerbotAI ai;Player bot;Event event;
 for(const char*n:{"flee","flee with pet","runaway","flee to master"}){
  MovementAction action{&ai,&bot,n};assert(!action.isUseful()&&!action.isPossible());
  bot.map.raid=false;assert(action.isUseful()&&action.isPossible());bot.map.raid=true;
 }
 FleeAction flee{{&ai,&bot,"flee"}};FleeWithPetAction petFlee{{&ai,&bot,"flee with pet"}};RunAwayAction runaway{{&ai,&bot,"runaway"}};
 assert(!flee.Execute(event)&&!petFlee.Execute(event)&&!runaway.Execute(event));
 assert(flee.flees==0&&petFlee.flees==0&&runaway.flees==0&&bot.pet.stops==0&&bot.pet.native.passive==0);
 for(const char*n:{"move away from hazard","molten core safe position","reach spell","reach melee","follow","flee encounter bomb"}){
  MovementAction action{&ai,&bot,n};assert(action.isPossible()&&action.isUseful());
  ai.move=false;assert(!action.isPossible());ai.move=true;ai.stay=true;assert(!action.isUseful());ai.stay=false;
 }
 bot.map.raid=false;assert(flee.Execute(event)&&petFlee.Execute(event)&&runaway.Execute(event));
 assert(flee.flees==1&&petFlee.flees==1&&runaway.flees==1&&bot.pet.stops==1&&bot.pet.native.passive==1);
 std::cout<<"PASS generic raid flee disabled in scheduling/direct execution; pets preserved, normal world flee and native mechanic/reach/healing movement unchanged\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='raid-no-flee-') as tmp:
  d=Path(tmp);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
